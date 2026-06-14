"""Adapter CCXT — implémente MarketDataPort via fetch_trades REST synchrone.

Seul ce module parle à ccxt. Le cœur (ingestion.py, schema.py) n'importe
jamais ce fichier directement : il ne connaît que MarketDataPort.

Dégradation gracieuse (miroir d'agentdb.py) :
- ccxt absent à l'import           → trades() retourne un itérable vide, sans erreur.
- exchange_id inconnu de ccxt       → idem.
- fetch_trades lève (réseau, timeout, exchange down, rate-limit) → idem.
- Un trade ccxt malformé (timestamp ou side manquant/None) → ignoré silencieusement.
- Toute exception inattendue dans trades()                    → itérable vide.
Dans tous les cas le moteur n'est jamais bloqué par l'indisponibilité de la source.

Invariants du port garantis ici (ADR-004) :
1. Ordre chronologique (ts croissant) : on trie par ts avant de yield.
2. Déduplication :
   - Si le trade ccxt possède un champ 'id' non-None, on déduplique sur cet
     identifiant natif. C'est l'identité unique d'un trade côté exchange ; cela
     couvre exactement le cas de pagination partielle / rollover de fenêtre.
   - Sans 'id' disponible (None ou absent), on NE déduplique PAS sur le
     quadruplet (ts, price, size, side) : cela détruirait des trades réellement
     distincts qui partagent ce quadruplet. On logue un warning pour signaler
     que la dédup est désactivée. Le tri garantit la monotonicité.

Mapping CCXT → Trade canonique :
  ccxt['timestamp'] (int, ms UTC)      → Trade.ts
  ccxt['price']    (float)             → Trade.price
  ccxt['amount']   (float)             → Trade.size
  ccxt['side']     ('buy' | 'sell')    → Trade.side (Side agresseur natif de ccxt)

Côté agresseur : ccxt expose le côté agresseur nativement pour la majorité des
exchanges (`takerOrMaker` == 'taker'). On utilise directement ce champ 'side'
sans heuristique. ccxt renvoie ce champ en minuscules ('buy'/'sell') ; la
normalisation applique .lower() systématiquement pour garantir la cohérence
inter-adapters (cf. _normalize.py). Si 'side' est absent ou non reconnu, le
trade est **ignoré** — on ne devine jamais le côté (ADR-001).

Normalisation déléguée à ``ninja_cat.adapters._normalize.normalize_trade`` —
même contrat que FileReplaySource, invariant live == replay garanti.
"""

from __future__ import annotations

import logging
from typing import Iterator

from ninja_cat.adapters._normalize import normalize_trade
from ninja_cat.ingestion import MarketDataPort
from ninja_cat.schema import Trade

logger = logging.getLogger(__name__)


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
        - Déduplication sur l'id natif ccxt quand disponible (voir module
          docstring pour la politique complète).
        - Dégradation gracieuse inviolable : TOUTE exception inattendue est
          capturée ici — trades() ne peut jamais remonter d'exception au moteur.
        """
        try:
            yield from self._trades_inner()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "CcxtSource.trades() : exception inattendue interceptée — flux vide. %s",
                exc,
            )
            return

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _trades_inner(self) -> Iterator[Trade]:
        """Logique principale — appelée depuis trades() sous try/except global."""
        raw = self._fetch_raw()
        if not raw:
            return

        canonical: list[tuple[str | None, Trade]] = list(self._normalise(raw))
        if not canonical:
            return

        # 1. Tri par ts croissant — garantit la monotonicité avant dédup.
        canonical.sort(key=lambda pair: pair[1].ts)

        # 2. Déduplication par id natif ccxt quand disponible.
        #    Sans id : on ne déduplique pas sur le quadruplet (évite de perdre
        #    des trades réellement distincts qui partagent ts/price/size/side).
        has_ids = any(trade_id is not None for trade_id, _ in canonical)
        if not has_ids:
            logger.warning(
                "CcxtSource(%r, %r) : aucun 'id' natif disponible dans les trades ccxt "
                "— déduplication désactivée pour ne pas détruire de données.",
                self._exchange_id,
                self._symbol,
            )
            for _, trade in canonical:
                yield trade
            return

        seen_ids: set[str] = set()
        for trade_id, trade in canonical:
            if trade_id is not None:
                if trade_id in seen_ids:
                    continue
                seen_ids.add(trade_id)
            # trade_id is None parmi une liste qui a d'autres ids : on le passe
            # sans dédup (ne peut pas être identifié).
            yield trade

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

    def _normalise(self, raw: list[dict]) -> Iterator[tuple[str | None, Trade]]:
        """Convertit chaque dict ccxt en (trade_id, Trade) canonique.

        L'id natif du trade (raw_trade.get('id')) est extrait et porté pour
        permettre la déduplication par identité dans trades(). Il peut être None
        si l'exchange ne fournit pas ce champ.

        Un trade malformé (timestamp absent/None, side absent/inconnu, prix ou
        taille absent/None/non numérique, valeurs inf/NaN, price/size <= 0) est
        **ignoré silencieusement** — on ne propage jamais une donnée douteuse
        (ADR-001). La normalisation est déléguée à normalize_trade() (module
        _normalize) pour garantir la parité live == replay.
        """
        for raw_trade in raw:
            if not isinstance(raw_trade, dict):
                continue

            # Extrait l'id natif ccxt (peut être str, int, ou None).
            trade_id_raw = raw_trade.get("id")
            trade_id: str | None = str(trade_id_raw) if trade_id_raw is not None else None

            trade = normalize_trade(
                ts_raw=raw_trade.get("timestamp"),
                price_raw=raw_trade.get("price"),
                size_raw=raw_trade.get("amount"),  # ccxt nomme ce champ 'amount'
                side_raw=raw_trade.get("side"),
            )
            if trade is None:
                continue

            yield trade_id, trade


# ------------------------------------------------------------------
# Conformité protocole (vérification statique à l'import)
# ------------------------------------------------------------------
# On vérifie ici que CcxtSource satisfait MarketDataPort sans instanciation.
# isinstance(CcxtSource, MarketDataPort) n'est pas possible (c'est une classe,
# pas une instance) ; on le vérifiera en test. Cette assertion documente l'intent.
assert hasattr(CcxtSource, "trades"), "CcxtSource doit exposer trades()"
