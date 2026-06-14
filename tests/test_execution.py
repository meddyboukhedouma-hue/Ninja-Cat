"""Tests du port d'exécution et de l'adapter PaperTraderBroker — zéro navigateur.

On vérifie :
- Order canonique (champs, type market par défaut).
- NullBroker : no-op sûr (n'émet aucun ordre) + conformité au protocole.
- get_broker : défaut null, null explicite, backend inconnu, paper_tradingview.
- PaperTraderBroker via evaluator injecté : JS correct (placeOrder/closePosition,
  mapping side buy=1/sell=-1, symbole), parsing booléen strict, dégradation
  gracieuse (evaluator qui lève / renvoie None / autre que True).
"""

from __future__ import annotations

import pytest

from ninja_cat.adapters.paper_trader import PaperTraderBroker
from ninja_cat.execution import (
    ExecutionPort,
    NullBroker,
    Order,
    OrderType,
    get_broker,
)
from ninja_cat.schema import Side


# ── Order ─────────────────────────────────────────────────────────────────────

def test_order_defaults_to_market():
    o = Order(symbol="COINBASE:BTCUSD", qty=0.001, side=Side.BUY)
    assert o.type is OrderType.MARKET
    assert o.symbol == "COINBASE:BTCUSD"
    assert o.qty == 0.001
    assert o.side is Side.BUY


def test_order_is_frozen():
    o = Order(symbol="X", qty=1.0, side=Side.SELL)
    with pytest.raises(Exception):
        o.symbol = "Y"  # type: ignore[misc]


# ── NullBroker ────────────────────────────────────────────────────────────────

def test_nullbroker_is_an_executionport():
    assert isinstance(NullBroker(), ExecutionPort)


def test_nullbroker_submits_nothing():
    """Défaut sûr : NullBroker n'accepte aucun ordre (aucun ordre réel émis)."""
    assert NullBroker().submit(Order("X", 1.0, Side.BUY)) is False


def test_nullbroker_closes_nothing():
    assert NullBroker().close("X") is False


# ── get_broker (fabrique) ─────────────────────────────────────────────────────

def test_get_broker_defaults_to_null():
    assert isinstance(get_broker(), NullBroker)


def test_get_broker_null_explicit():
    assert isinstance(get_broker("null"), NullBroker)


def test_get_broker_paper_tradingview():
    assert isinstance(get_broker("paper_tradingview"), PaperTraderBroker)


def test_get_broker_unknown_raises():
    with pytest.raises(ValueError):
        get_broker("broker_fantome")


# ── PaperTraderBroker : transport injecté ─────────────────────────────────────

class _FakeEvaluator:
    """Faux transport : enregistre le JS reçu et renvoie une valeur programmée."""

    def __init__(self, return_value=True):
        self.calls: list[str] = []
        self._return_value = return_value

    def __call__(self, expression: str):
        self.calls.append(expression)
        return self._return_value


def test_paper_trader_is_an_executionport():
    assert isinstance(PaperTraderBroker(evaluator=_FakeEvaluator()), ExecutionPort)


def test_submit_returns_true_when_broker_accepts():
    broker = PaperTraderBroker(evaluator=_FakeEvaluator(return_value=True))
    assert broker.submit(Order("COINBASE:BTCUSD", 0.001, Side.BUY)) is True


def test_submit_builds_placeorder_js_with_buy_side():
    fake = _FakeEvaluator()
    PaperTraderBroker(evaluator=fake).submit(Order("COINBASE:BTCUSD", 0.001, Side.BUY))
    (js,) = fake.calls
    assert "placeOrder(" in js
    assert "COINBASE:BTCUSD" in js
    assert '"side": 1' in js          # BUY → 1
    assert '"type": 2' in js          # MARKET → 2
    assert '"qty": 0.001' in js


def test_submit_maps_sell_side_to_minus_one():
    fake = _FakeEvaluator()
    PaperTraderBroker(evaluator=fake).submit(Order("X", 2.0, Side.SELL))
    (js,) = fake.calls
    assert '"side": -1' in js         # SELL → -1


def test_submit_is_false_for_non_true_results():
    """Parsing strict : seul True compte comme accepté (None/False/autre → False)."""
    for value in (None, False, "true", 1, {}):
        broker = PaperTraderBroker(evaluator=_FakeEvaluator(return_value=value))
        assert broker.submit(Order("X", 1.0, Side.BUY)) is False


def test_submit_graceful_when_evaluator_raises():
    """Dégradation gracieuse : un transport qui lève → False, jamais d'exception."""
    def boom(_expr):
        raise RuntimeError("CDP down")

    broker = PaperTraderBroker(evaluator=boom)
    assert broker.submit(Order("X", 1.0, Side.BUY)) is False


def test_close_builds_closeposition_js_for_symbol():
    fake = _FakeEvaluator()
    PaperTraderBroker(evaluator=fake).close("COINBASE:BTCUSD")
    (js,) = fake.calls
    assert "closePosition(" in js
    assert "positions()" in js
    assert "COINBASE:BTCUSD" in js


def test_close_returns_true_when_evaluator_true():
    broker = PaperTraderBroker(evaluator=_FakeEvaluator(return_value=True))
    assert broker.close("X") is True


def test_close_graceful_when_evaluator_raises():
    def boom(_expr):
        raise RuntimeError("CDP down")

    assert PaperTraderBroker(evaluator=boom).close("X") is False


def test_default_cdp_transport_degrades_gracefully_when_unreachable():
    """Transport CDP réel mais endpoint injoignable → submit/close retournent
    False sans lever. On vise un port MORT exprès (127.0.0.1:1) — jamais le vrai
    CDP 9223, pour ne passer aucun ordre pendant les tests.
    """
    broker = PaperTraderBroker(cdp_url="http://127.0.0.1:1", timeout=0.5)
    assert broker.submit(Order("X", 1.0, Side.BUY)) is False
    assert broker.close("X") is False
