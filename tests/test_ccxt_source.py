"""Tests de l'adapter CcxtSource — aucun appel réseau réel.

Tous les appels à ccxt sont mockés. On vérifie :
- Normalisation correcte des champs ccxt → Trade canonique.
- Mapping du côté agresseur ('buy' → Side.BUY, 'sell' → Side.SELL).
- Tri chronologique (ts croissant) imposé par l'adapter.
- Déduplication (même (ts, price, size, side) → une seule occurrence).
- Dégradation gracieuse dans tous les cas d'erreur.
"""

from __future__ import annotations

import sys
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from ninja_cat.adapters.ccxt_source import CcxtSource
from ninja_cat.ingestion import MarketDataPort
from ninja_cat.schema import Side, Trade


# ── Helpers : données ccxt synthétiques ──────────────────────────────────────

def _raw(
    ts: int = 1_700_000_000_000,
    price: float = 30_000.0,
    amount: float = 0.5,
    side: str = "buy",
) -> dict:
    """Construit un trade ccxt synthétique minimal."""
    return {"timestamp": ts, "price": price, "amount": amount, "side": side}


def _make_source(raw_trades: list[dict], exchange_id: str = "binance") -> CcxtSource:
    """Construit un CcxtSource dont l'exchange est mocké (fetch_trades retourne raw_trades)."""
    src = CcxtSource(exchange_id=exchange_id, symbol="BTC/USDT")
    exchange_mock = MagicMock()
    exchange_mock.fetch_trades.return_value = raw_trades
    # On mocke _build_exchange pour ne jamais déclencher un vrai import ccxt.
    src._build_exchange = lambda: exchange_mock  # type: ignore[method-assign]
    return src


# ── Conformité au protocole ───────────────────────────────────────────────────

def test_ccxt_source_is_a_marketdataport():
    """CcxtSource doit satisfaire le protocole MarketDataPort."""
    src = _make_source([])
    assert isinstance(src, MarketDataPort)


def test_ccxt_source_trades_returns_iterator():
    src = _make_source([])
    result = src.trades()
    assert hasattr(result, "__iter__") and hasattr(result, "__next__")


# ── Normalisation des champs ──────────────────────────────────────────────────

def test_normalisation_buy_trade():
    """Un trade ccxt 'buy' est normalisé en Trade avec Side.BUY."""
    raw = [_raw(ts=1_700_000_000_000, price=30_000.0, amount=0.5, side="buy")]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 1
    t = trades[0]
    assert t.ts == 1_700_000_000_000
    assert t.price == 30_000.0
    assert t.size == 0.5
    assert t.side is Side.BUY


def test_normalisation_sell_trade():
    """Un trade ccxt 'sell' est normalisé en Trade avec Side.SELL."""
    raw = [_raw(ts=1_700_000_001_000, price=30_001.0, amount=0.25, side="sell")]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 1
    assert trades[0].side is Side.SELL


def test_signed_size_buy_is_positive():
    trades = list(_make_source([_raw(side="buy", amount=1.0)]).trades())
    assert trades[0].signed_size > 0


def test_signed_size_sell_is_negative():
    trades = list(_make_source([_raw(side="sell", amount=1.0)]).trades())
    assert trades[0].signed_size < 0


def test_normalisation_preserves_all_fields():
    """Tous les champs scalaires sont mappés fidèlement."""
    raw = [_raw(ts=1_700_000_005_000, price=42_000.5, amount=2.123, side="sell")]
    t = list(_make_source(raw).trades())[0]
    assert t.ts == 1_700_000_005_000
    assert t.price == 42_000.5
    assert t.size == 2.123
    assert t.side is Side.SELL


# ── Tri chronologique ─────────────────────────────────────────────────────────

def test_trades_sorted_by_ts_ascending():
    """Les trades doivent être livrés en ordre de ts croissant, quelle que soit
    la réponse de l'exchange."""
    raw = [
        _raw(ts=1_700_000_002_000, price=30_002.0),
        _raw(ts=1_700_000_000_000, price=30_000.0),
        _raw(ts=1_700_000_001_000, price=30_001.0),
    ]
    trades = list(_make_source(raw).trades())
    ts_list = [t.ts for t in trades]
    assert ts_list == sorted(ts_list), f"ts non croissants : {ts_list}"


def test_already_sorted_unchanged():
    """Si l'exchange renvoie déjà un ordre croissant, le contenu n'est pas altéré."""
    raw = [
        _raw(ts=1_000, price=1.0),
        _raw(ts=2_000, price=2.0),
        _raw(ts=3_000, price=3.0),
    ]
    trades = list(_make_source(raw).trades())
    assert [t.price for t in trades] == [1.0, 2.0, 3.0]


# ── Déduplication ────────────────────────────────────────────────────────────

def test_dedup_identical_trades():
    """Deux trades identiques (même ts, price, size, side) → une seule occurrence."""
    raw_trade = _raw(ts=1_700_000_000_000, price=30_000.0, amount=0.5, side="buy")
    raw = [raw_trade, raw_trade]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 1


def test_dedup_keeps_distinct_trades():
    """Des trades distincts ne sont pas dédupliqués."""
    raw = [
        _raw(ts=1_000, price=1.0, amount=0.1, side="buy"),
        _raw(ts=1_000, price=1.0, amount=0.2, side="buy"),   # même ts+price mais size diff
        _raw(ts=2_000, price=2.0, amount=0.1, side="sell"),
    ]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 3


def test_dedup_after_sort():
    """Le dedup est appliqué après le tri : doublons de ts différents mais
    clés identiques (ts, price, size, side) sont aussi dédupliqués."""
    raw = [
        _raw(ts=2_000, price=1.0, amount=0.1, side="buy"),
        _raw(ts=1_000, price=1.0, amount=0.1, side="buy"),
        _raw(ts=2_000, price=1.0, amount=0.1, side="buy"),   # doublon du premier
    ]
    # ts=1_000 est distinct de ts=2_000 → 2 trades attendus
    trades = list(_make_source(raw).trades())
    assert len(trades) == 2
    assert trades[0].ts == 1_000
    assert trades[1].ts == 2_000


# ── Trades malformés ignorés silencieusement ──────────────────────────────────

def test_missing_timestamp_ignored():
    raw = [{"price": 30_000.0, "amount": 0.5, "side": "buy"}]  # pas de 'timestamp'
    assert list(_make_source(raw).trades()) == []


def test_none_timestamp_ignored():
    raw = [{"timestamp": None, "price": 30_000.0, "amount": 0.5, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_zero_timestamp_ignored():
    raw = [_raw(ts=0)]
    assert list(_make_source(raw).trades()) == []


def test_negative_timestamp_ignored():
    raw = [_raw(ts=-1)]
    assert list(_make_source(raw).trades()) == []


def test_missing_side_ignored():
    raw = [{"timestamp": 1_000, "price": 30_000.0, "amount": 0.5}]  # pas de 'side'
    assert list(_make_source(raw).trades()) == []


def test_none_side_ignored():
    raw = [{"timestamp": 1_000, "price": 30_000.0, "amount": 0.5, "side": None}]
    assert list(_make_source(raw).trades()) == []


def test_unknown_side_ignored():
    """On ne devine jamais le côté : un side non reconnu ('maker', 'taker', ...) est ignoré."""
    raw = [_raw(side="taker")]
    assert list(_make_source(raw).trades()) == []


def test_missing_price_ignored():
    raw = [{"timestamp": 1_000, "amount": 0.5, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_none_price_ignored():
    raw = [{"timestamp": 1_000, "price": None, "amount": 0.5, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_missing_amount_ignored():
    raw = [{"timestamp": 1_000, "price": 30_000.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_non_dict_entry_in_list_ignored():
    """Si ccxt retourne un élément non-dict dans la liste, il est ignoré."""
    raw = ["pas un dict", _raw(ts=1_000)]  # type: ignore[list-item]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 1


def test_mixed_valid_and_malformed():
    """Seuls les trades valides sont normalisés ; les malformés sont ignorés."""
    raw = [
        _raw(ts=1_000, price=10.0, amount=1.0, side="buy"),
        {"timestamp": None, "price": 10.0, "amount": 1.0, "side": "buy"},  # ts None
        _raw(ts=2_000, price=20.0, amount=2.0, side="sell"),
        {"timestamp": 3_000, "price": 30.0, "amount": 3.0, "side": "unknown"},  # side inconnu
    ]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 2
    assert trades[0].ts == 1_000
    assert trades[1].ts == 2_000


# ── Dégradation gracieuse ─────────────────────────────────────────────────────

def test_graceful_when_fetch_trades_raises():
    """Si fetch_trades lève une exception (réseau, timeout, etc.) → itérable vide."""
    src = CcxtSource(exchange_id="binance", symbol="BTC/USDT")
    exchange_mock = MagicMock()
    exchange_mock.fetch_trades.side_effect = Exception("connexion refusée")
    src._build_exchange = lambda: exchange_mock  # type: ignore[method-assign]
    result = list(src.trades())
    assert result == []


def test_graceful_when_fetch_trades_returns_none():
    """fetch_trades qui retourne None (hypothèse défensive) → itérable vide."""
    src = CcxtSource(exchange_id="binance", symbol="BTC/USDT")
    exchange_mock = MagicMock()
    exchange_mock.fetch_trades.return_value = None
    src._build_exchange = lambda: exchange_mock  # type: ignore[method-assign]
    assert list(src.trades()) == []


def test_graceful_when_build_exchange_returns_none():
    """Si _build_exchange retourne None → itérable vide, pas d'exception."""
    src = CcxtSource(exchange_id="exchange_inexistant", symbol="BTC/USDT")
    src._build_exchange = lambda: None  # type: ignore[method-assign]
    assert list(src.trades()) == []


def test_graceful_when_ccxt_absent(monkeypatch: pytest.MonkeyPatch):
    """Si ccxt n'est pas installé (ImportError), trades() retourne un itérable vide."""
    # On force l'import lazy à échouer en retirant ccxt du sys.modules
    # et en bloquant tout import futur.
    monkeypatch.setitem(sys.modules, "ccxt", None)  # type: ignore[arg-type]
    # On recrée l'objet pour que _build_exchange utilise le vrai chemin lazy.
    src = CcxtSource(exchange_id="binance", symbol="BTC/USDT")
    result = list(src.trades())
    assert result == []


def test_graceful_when_exchange_id_unknown(monkeypatch: pytest.MonkeyPatch):
    """Un exchange_id absent de ccxt → itérable vide, pas d'exception."""
    ccxt_mock = MagicMock()
    # getattr(ccxt_mock, 'exchange_fantome') retourne un MagicMock par défaut ;
    # on le remplace par None pour simuler un id inconnu.
    del ccxt_mock.exchange_fantome
    monkeypatch.setitem(sys.modules, "ccxt", ccxt_mock)
    src = CcxtSource(exchange_id="exchange_fantome", symbol="BTC/USDT")
    result = list(src.trades())
    assert result == []


def test_graceful_empty_list():
    """fetch_trades qui retourne une liste vide → itérable vide (normal)."""
    trades = list(_make_source([]).trades())
    assert trades == []


def test_graceful_multiple_calls_independent():
    """Chaque appel à trades() est indépendant et ne partage pas d'état."""
    raw = [_raw(ts=1_000)]
    src = _make_source(raw)
    first = list(src.trades())
    second = list(src.trades())
    assert first == second
    assert len(first) == 1
