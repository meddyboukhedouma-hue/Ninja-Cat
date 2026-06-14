"""Adapter d'exécution — Paper Trader de TradingView via le broker intégré.

Implémente `ExecutionPort` en pilotant le broker `Paper` de TradingView Desktop.
Seul ce module parle au navigateur. Le cœur (`execution.py`) n'importe jamais ce
fichier : il ne connaît que `ExecutionPort`.

Canal d'exécution (découvert en live, cf. mémoire projet) — l'API Broker
complète de TradingView est joignable dans la page :

    bottomWidgetBar._widgetControllers.get('paper_trading')
      ._trading.activeBroker()
      .placeOrder({ symbol, qty, side, type })   // side 1=buy / -1=sell, type 2=market

On atteint cette API en évaluant du JavaScript dans la page via le **Chrome
DevTools Protocol** (port 9223, ADR-006). NB : `tv_discover` ne voit PAS cette
API (sonde restreinte) ; `replay_trade` ne couvre que le mode Replay — d'où
l'accès direct au broker ici.

Transport injectable (clé de la testabilité) : le constructeur accepte un
`evaluator` — un callable `(js: str) -> objet` qui exécute le JS dans la page et
renvoie le résultat (promesse résolue). Par défaut, `_cdp_evaluate` ouvre une
connexion CDP en websocket. Les tests injectent un faux evaluator : aucun
navigateur, aucun réseau requis.

Dégradation gracieuse (miroir agentdb.py) : CDP injoignable, lib websocket
absente, page sans broker, exception JS — `submit`/`close` retournent `False`
sans lever. Le moteur n'est jamais bloqué, et aucun ordre n'est émis « à moitié ».

FRONTIÈRE : cet adapter **exécute** des ordres décidés ailleurs. Il ne décide
jamais quoi/quand trader (doctrine, hors périmètre infra — ADR-007).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from ninja_cat.execution import ExecutionPort, Order
from ninja_cat.schema import Side

logger = logging.getLogger(__name__)

# Préambule JS : résout l'objet broker actif du Paper Trader. `activeBroker` peut
# être une méthode et/ou un observable (.value()) — on couvre les deux formes,
# exactement comme la découverte live.
_BROKER_ACCESSOR = (
    "const tr = window.TradingView.bottomWidgetBar._widgetControllers"
    ".get('paper_trading')._trading;"
    " let b = tr.activeBroker; b = (typeof b==='function') ? b.call(tr) : b;"
    " if (b && typeof b.value==='function') b = b.value();"
)

_DEFAULT_CDP_URL = "http://localhost:9223"


class PaperTraderBroker:
    """Broker d'exécution adossé au Paper Trader de TradingView (via CDP).

    Paramètres
    ----------
    evaluator:
        Callable `(js) -> objet` exécutant du JS dans la page (promesse résolue).
        Injecté pour les tests ; `None` ⇒ transport CDP websocket par défaut.
    cdp_url:
        URL HTTP du endpoint CDP (défaut port 9223, ADR-006).
    timeout:
        Timeout réseau (s) pour la connexion CDP.
    """

    def __init__(
        self,
        evaluator: Optional[Callable[[str], Any]] = None,
        cdp_url: str = _DEFAULT_CDP_URL,
        timeout: float = 10.0,
    ) -> None:
        self._evaluator = evaluator
        self._cdp_url = cdp_url
        self._timeout = timeout

    # ------------------------------------------------------------------
    # ExecutionPort
    # ------------------------------------------------------------------

    def submit(self, order: Order) -> bool:
        """Passe `order` sur le Paper Trader. True si le broker accepte (placeOrder→true)."""
        side = 1 if order.side is Side.BUY else -1
        payload = json.dumps(
            {"symbol": order.symbol, "qty": order.qty, "side": side, "type": 2}
        )
        js = f"(() => {{ {_BROKER_ACCESSOR} return b.placeOrder({payload}); }})()"
        return self._evaluate(js) is True

    def close(self, symbol: str) -> bool:
        """Clôture la position ouverte sur `symbol` (recherche par symbole → closePosition)."""
        sym = json.dumps(symbol)
        js = (
            f"(async () => {{ {_BROKER_ACCESSOR}"
            f" const ps = await b.positions();"
            f" const pos = (ps || []).find(p => p.symbol === {sym});"
            f" if (!pos) return false;"
            f" await b.closePosition(pos.id);"
            f" return true; }})()"
        )
        return self._evaluate(js) is True

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _evaluate(self, expression: str) -> Any:
        """Délègue l'évaluation au transport (injecté ou CDP). Jamais d'exception."""
        evaluator = self._evaluator if self._evaluator is not None else self._cdp_evaluate
        try:
            return evaluator(expression)
        except Exception as exc:  # noqa: BLE001 — dégradation gracieuse inviolable
            logger.warning(
                "PaperTraderBroker : évaluation échouée — no-op (aucun ordre émis). %s",
                exc,
            )
            return None

    def _cdp_evaluate(self, expression: str) -> Any:
        """Évalue `expression` dans la page TradingView via CDP (websocket).

        Utilise `Runtime.evaluate` avec `awaitPromise=true` : les appels broker
        asynchrones (placeOrder/positions/closePosition) sont résolus côté CDP,
        puis la valeur est renvoyée par valeur. Retourne `None` si la cible CDP
        est absente ou si le JS lève (exceptionDetails).
        """
        import urllib.request as _url

        from websocket import create_connection  # lazy : extra [live]

        with _url.urlopen(self._cdp_url.rstrip("/") + "/json", timeout=self._timeout) as resp:
            targets = json.loads(resp.read())

        target = next(
            (
                t
                for t in targets
                if t.get("type") == "page"
                and "tradingview" in str(t.get("url", "")).lower()
            ),
            None,
        )
        if target is None:
            logger.warning("PaperTraderBroker : aucune cible CDP TradingView — no-op.")
            return None

        ws = create_connection(target["webSocketDebuggerUrl"], timeout=self._timeout)
        try:
            ws.send(
                json.dumps(
                    {
                        "id": 1,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": expression,
                            "awaitPromise": True,
                            "returnByValue": True,
                        },
                    }
                )
            )
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == 1:
                    break
        finally:
            ws.close()

        result = msg.get("result", {})
        if "exceptionDetails" in result:
            logger.warning("PaperTraderBroker : exception JS côté page — no-op.")
            return None
        return result.get("result", {}).get("value")


# ------------------------------------------------------------------
# Conformité protocole (vérification statique à l'import)
# ------------------------------------------------------------------
assert hasattr(PaperTraderBroker, "submit"), "PaperTraderBroker doit exposer submit()"
assert hasattr(PaperTraderBroker, "close"), "PaperTraderBroker doit exposer close()"
