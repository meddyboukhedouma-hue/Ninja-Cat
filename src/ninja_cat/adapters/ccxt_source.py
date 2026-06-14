"""Adapter CCXT — implémente MarketDataPort via fetch_trades REST synchrone.

Seul ce module parle à ccxt. Le cœur (ingestion.py, schema.py) n'importe
jamais ce fichier directement : il ne connaît que MarketDataPort.

Dégradation gracieuse (miroir d'agentdb.py) :
- ccxt absent à l'import           → trades() retourne un itérable vide, sans erreur.
- exchange_id inconnu de ccxt       → idem.
- fetch_trades lève (réseau, timeout, exchange down, rate-limit) → idem.
- Un trade ccxt malformé (timestamp ou side manquant/None) → ignoré silencieusement.
Dans tous les cas le moteur n'est jamais bloqué par l'indisponibilité de la source.

Invariants du port garantis ici (ADR-004) :
1. Ordre chronologique (ts croissant) : on trie par ts avant de yield.
2. Absence de doublons : on déduplique sur (ts, price, size, side) après le tri.
   ccxt peut renvoyer le même trade plusieurs fois en cas de pagination partielle
   ou de rollover de fenêtre ; le dedup est donc nécessaire.

Mapping CCXT → Trade canonique :
  ccxt['timestamp'] (int, ms UTC)      → Trade.ts
  ccxt['price']    (float)             → Trade.price
  ccxt['amount']   (float)             → Trade.size
  ccxt['side']     ('buy' | 'sell')    → Trade.side (Side agresseur natif de ccxt)

Fallback côté : ccxt expose le côté agresseur nativement pour la majorité des
exchanges (`takerOrMaker` == 'taker'). On utilise directement ce champ 'side'
sans heuristique. Si 'side' est absent ou None, le trade est **ignoré** — on ne
devine jamais le côté (règle portée par ADR-001 : zéro compromis sur la qualité).
"""

from __future__ import annotations

import logging
from typing import Iterator

from ninja_cat.ingestion import MarketDataPort
from ninja_cat.schema import Side, Trade

logger = logging.getLogger(__name__)

_SIDE_MAP: dict[str, Side] = {
    "buy": Side.BUY,
    "sell": Side.SELL,
}


class CcxtSource:
    """Source de marché REST synchrone via ccxt.fetch_trades.

    Paramètres
    ----------
    exchange_id:
        Identifiant ccxt de l'exchange (ex. 'binance', 'kraken', 'coinbase').
    symbol:
        Symbole ccxt unifié (ex. 'BTC/USDT').
    limit:
        Nombre maximum de trades à récupérer par appel fetch_trades.
        None signifie la valeur par défaut de l'exchange.
    since:
        Timestamp de début en ms UTC (None = pas de filtre).
    exchange_params:
        Paramètres arbitraires passés au constructeur ccxt de l'exchange
        (ex. {'apiKey': ..., 'secret': ..., 'timeout': 10000}).
    """

    def __init__(
        self,
        exchange_id: str,
        symbol: str,
        limit: int | None = None,
        since: int | None = None,
        exchange_params: dict | None = None,
    ) -> None:
        self._exchange_id = exchange_id
        self._symbol = symbol
        self._limit = limit
        self._since = since
        self._exchange_params = exchange_params or {}

    # ------------------------------------------------------------------
    # MarketDataPort
    # ------------------------------------------------------------------

    def trades(self) -> Iterator[Trade]:
        """Itère les trades normalisés depuis ccxt.fetch_trades.

        Respecte les invariants du port :
        - ts monotone croissant (tri sur ts avant yield).
        - Aucun doublon (déduplication sur (ts, price, size, side) après tri).
        - Dégradation gracieuse : tout échec produit un itérateur vide.
        """
        raw = self._fetch_raw()
        if not raw:
            return

        canonical = list(self._normalise(raw))
        if not canonical:
            return

        # 1. Tri par ts croissant — garantit la monotonicité avant dédup.
        canonical.sort(key=lambda t: t.ts)

        # 2. Déduplication : on conserve la première occurrence de chaque
        #    (ts, price, size, side). Un set de tuples suffit ; l'ordre est
        #    préservé car on itère après le tri.
        seen: set[tuple[int, float, float, Side]] = set()
        for trade in canonical:
            key = (trade.ts, trade.price, trade.size, trade.side)
            if key in seen:
                continue
            seen.add(key)
            yield trade

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _build_exchange(self) -> object | None:
        """Construit l'objet exchange ccxt. Retourne None si ccxt est absent
        ou si l'exchange_id est inconnu — jamais d'exception qui remonte.
        """
        try:
            import ccxt  # lazy import : le cœur n'est jamais impacté par l'absence de ccxt
        except ImportError:
            logger.warning("ccxt non disponible — CcxtSource retourne un flux vide.")
            return None

        exchange_class = getattr(ccxt, self._exchange_id, None)
        if exchange_class is None:
            logger.warning(
                "Exchange inconnu de ccxt : %r — CcxtSource retourne un flux vide.",
                self._exchange_id,
            )
            return None

        try:
            return exchange_class(self._exchange_params)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Impossible d'instancier l'exchange %r : %s", self._exchange_id, exc)
            return None

    def _fetch_raw(self) -> list[dict] | None:
        """Appelle fetch_trades sur l'exchange. Retourne None en cas d'échec."""
        exchange = self._build_exchange()
        if exchange is None:
            return None

        kwargs: dict = {}
        if self._limit is not None:
            kwargs["limit"] = self._limit
        if self._since is not None:
            kwargs["since"] = self._since

        try:
            result = exchange.fetch_trades(self._symbol, **kwargs)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "fetch_trades(%r, %r) a échoué : %s — flux vide retourné.",
                self._exchange_id,
                self._symbol,
                exc,
            )
            return None

        if not isinstance(result, list):
            logger.warning(
                "fetch_trades a retourné un type inattendu : %s — flux vide.",
                type(result).__name__,
            )
            return None

        return result

    def _normalise(self, raw: list[dict]) -> Iterator[Trade]:
        """Convertit chaque dict ccxt en Trade canonique.

        Un trade malformé (timestamp absent/None, side absent/inconnu, prix ou
        taille absent/None/non numérique) est **ignoré silencieusement** : il
        ne constitue pas une exception remontante mais il n'est pas transmis
        non plus — on ne propage jamais une donnée douteuse (ADR-001).
        """
        for raw_trade in raw:
            if not isinstance(raw_trade, dict):
                continue

            # --- timestamp ---
            ts_raw = raw_trade.get("timestamp")
            if ts_raw is None:
                continue
            try:
                ts = int(ts_raw)
            except (TypeError, ValueError):
                continue
            if ts <= 0:
                continue

            # --- price ---
            price_raw = raw_trade.get("price")
            if price_raw is None:
                continue
            try:
                price = float(price_raw)
            except (TypeError, ValueError):
                continue

            # --- size (ccxt: 'amount') ---
            size_raw = raw_trade.get("amount")
            if size_raw is None:
                continue
            try:
                size = float(size_raw)
            except (TypeError, ValueError):
                continue

            # --- side agresseur (ccxt le fournit nativement) ---
            # On n'utilise jamais d'heuristique : si le champ est absent ou non
            # reconnu, le trade est ignoré (règle ADR-001 / mission data-engineer).
            side_raw = raw_trade.get("side")
            side = _SIDE_MAP.get(side_raw) if isinstance(side_raw, str) else None
            if side is None:
                continue

            yield Trade(ts=ts, price=price, size=size, side=side)


# ------------------------------------------------------------------
# Conformité protocole (vérification statique à l'import)
# ------------------------------------------------------------------
# On vérifie ici que CcxtSource satisfait MarketDataPort sans instanciation.
# isinstance(CcxtSource, MarketDataPort) n'est pas possible (c'est une classe,
# pas une instance) ; on le vérifiera en test. Cette assertion documente l'intent.
assert hasattr(CcxtSource, "trades"), "CcxtSource doit exposer trades()"
