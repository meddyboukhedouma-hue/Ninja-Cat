"""Tests de l'adapter CcxtSource — aucun appel réseau réel.

Tous les appels à ccxt sont mockés. On vérifie :
- Normalisation correcte des champs ccxt → Trade canonique.
- Mapping du côté agresseur ('buy' → Side.BUY, 'sell' → Side.SELL).
- Tri chronologique (ts croissant) imposé par l'adapter.
- Déduplication par id natif ccxt (pas sur le quadruplet — C1).
- Dégradation gracieuse dans tous les cas d'erreur.
- Gardes de finitude (NaN, inf) et rejet price/size <= 0 (C2/C4).
- Harmonisation de casse du side (C5).
"""

from __future__ import annotations

import math
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
    trade_id: str | None = None,
) -> dict:
    """Construit un trade ccxt synthétique minimal."""
    d = {"timestamp": ts, "price": price, "amount": amount, "side": side}
    if trade_id is not None:
        d["id"] = trade_id
    return d


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


# ── Déduplication par id natif ccxt (C1) ─────────────────────────────────────

def test_dedup_identical_trades_by_id():
    """Deux trades avec le même id ccxt natif → une seule occurrence (C1).

    Cas pagination : le même trade peut apparaître deux fois lors d'un rollover
    de fenêtre ou d'une pagination partielle ; la dédup par id natif le gère.
    """
    raw = [
        _raw(ts=1_000, price=10.0, amount=0.5, side="buy", trade_id="trade-abc"),
        _raw(ts=1_000, price=10.0, amount=0.5, side="buy", trade_id="trade-abc"),  # doublon id
    ]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 1


def test_dedup_distinct_ids_both_kept():
    """Deux trades distincts avec des ids différents sont TOUS DEUX conservés,
    même s'ils partagent le même quadruplet (ts, price, size, side) — bug C1 corrigé.
    """
    # Avant la correction C1, ces deux trades auraient été fusionnés à tort.
    raw = [
        _raw(ts=1_000, price=10.0, amount=0.5, side="buy", trade_id="trade-001"),
        _raw(ts=1_000, price=10.0, amount=0.5, side="buy", trade_id="trade-002"),
    ]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 2, (
        "Deux trades avec des ids distincts mais même quadruplet doivent être conservés"
    )


def test_dedup_pagination_scenario():
    """T1 — Scénario pagination : entrée désordonnée où deux occurrences du MÊME id
    sont séparées par d'autres trades puis rapprochées par le tri.

    Entrée (ordre exchange) : B, A, B (B est le doublon, séparé par A).
    Après tri par ts : A < B, B.
    Après dédup par id : A, B (le deuxième B est éliminé).
    """
    raw = [
        _raw(ts=2_000, price=20.0, amount=1.0, side="sell", trade_id="trade-B"),  # 1ère occ B
        _raw(ts=1_000, price=10.0, amount=0.5, side="buy",  trade_id="trade-A"),
        _raw(ts=2_000, price=20.0, amount=1.0, side="sell", trade_id="trade-B"),  # doublon B
    ]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 2
    assert trades[0].ts == 1_000   # A en premier après tri
    assert trades[1].ts == 2_000   # B une seule fois


def test_dedup_keeps_distinct_trades():
    """Des trades distincts (ids différents, quadruplets différents) ne sont pas dédupliqués."""
    raw = [
        _raw(ts=1_000, price=1.0, amount=0.1, side="buy",  trade_id="t1"),
        _raw(ts=1_000, price=1.0, amount=0.2, side="buy",  trade_id="t2"),  # size diff
        _raw(ts=2_000, price=2.0, amount=0.1, side="sell", trade_id="t3"),
    ]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 3


def test_dedup_after_sort():
    """La dédup est appliquée APRÈS le tri : le doublon d'id est bien détecté
    même quand les deux occurrences arrivent à des positions différentes."""
    raw = [
        _raw(ts=2_000, price=1.0, amount=0.1, side="buy", trade_id="dup"),
        _raw(ts=1_000, price=1.0, amount=0.1, side="buy", trade_id="uniq"),
        _raw(ts=2_000, price=1.0, amount=0.1, side="buy", trade_id="dup"),   # doublon
    ]
    # Après tri : ts=1_000 (uniq), ts=2_000 (dup), ts=2_000 (dup supprimé).
    trades = list(_make_source(raw).trades())
    assert len(trades) == 2
    assert trades[0].ts == 1_000
    assert trades[1].ts == 2_000


def test_no_dedup_without_id_logs_warning(caplog):
    """Sans id dans les trades, la dédup est désactivée et un warning est loggé."""
    import logging
    raw = [
        _raw(ts=1_000, price=10.0, amount=0.5, side="buy"),  # pas d'id
        _raw(ts=1_000, price=10.0, amount=0.5, side="buy"),  # même quadruplet, sans id
    ]
    with caplog.at_level(logging.WARNING, logger="ninja_cat.adapters.ccxt_source"):
        trades = list(_make_source(raw).trades())
    # Les deux trades sont conservés (pas de dédup destructrice).
    assert len(trades) == 2
    # Warning loggé.
    assert any("déduplication désactivée" in r.message for r in caplog.records)


# ── Monotonie (T2) ────────────────────────────────────────────────────────────

def test_monotonicity_disordered_with_ties():
    """T2 — invariant monotonie sur >=5 trades vraiment désordonnés dont deux ex-aequo
    (même ts). Après tri : all(a.ts <= b.ts) ; l'ordre des ex-aequo est stable (tri stable).
    """
    raw = [
        _raw(ts=5_000, price=5.0, amount=1.0, side="sell", trade_id="t5"),
        _raw(ts=2_000, price=2.0, amount=1.0, side="buy",  trade_id="t2a"),
        _raw(ts=1_000, price=1.0, amount=1.0, side="buy",  trade_id="t1"),
        _raw(ts=2_000, price=2.1, amount=1.0, side="buy",  trade_id="t2b"),  # ex-aequo ts=2_000
        _raw(ts=3_000, price=3.0, amount=1.0, side="sell", trade_id="t3"),
    ]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 5
    ts_list = [t.ts for t in trades]
    # Monotonie croissante.
    assert all(a <= b for a, b in zip(ts_list, ts_list[1:])), f"ts non croissants : {ts_list}"
    # Les ex-aequo ts=2_000 sont présents (deux trades distincts).
    ties = [t for t in trades if t.ts == 2_000]
    assert len(ties) == 2
    # Tri stable : t2a (price=2.0) apparaît avant t2b (price=2.1) car ils
    # étaient dans cet ordre dans l'entrée après normalisation.
    assert ties[0].price == 2.0
    assert ties[1].price == 2.1


# ── Gardes de finitude, types, price/size <= 0 (T3/C2/C4) ───────────────────

def test_side_uppercase_accepted_after_harmonisation():
    """T3 — side 'BUY' (majuscule) : après harmonisation .lower() dans normalize_trade,
    il est accepté et normalisé en Side.BUY.
    """
    raw = [_raw(ts=1_000, price=10.0, amount=1.0, side="BUY")]
    trades = list(_make_source(raw).trades())
    assert len(trades) == 1
    assert trades[0].side is Side.BUY


def test_side_numeric_ignored():
    """T3 — side numérique (int 1) : rejeté car ce n'est pas une str."""
    raw = [{"timestamp": 1_000, "price": 10.0, "amount": 1.0, "side": 1}]
    assert list(_make_source(raw).trades()) == []


def test_side_empty_string_ignored():
    """T3 — side '' : non reconnu dans le mapping → ignoré."""
    raw = [{"timestamp": 1_000, "price": 10.0, "amount": 1.0, "side": ""}]
    assert list(_make_source(raw).trades()) == []


def test_price_non_numeric_ignored():
    """T3 — price non numérique ('abc') : ignoré (déclenche la branche except)."""
    raw = [{"timestamp": 1_000, "price": "abc", "amount": 1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_size_non_numeric_ignored():
    """T3 — size non numérique ('abc') : ignoré."""
    raw = [{"timestamp": 1_000, "price": 10.0, "amount": "abc", "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_ts_inf_ignored():
    """T3 — ts = inf : rejeté par garde isfinite, trades() ne lève jamais."""
    raw = [{"timestamp": float("inf"), "price": 10.0, "amount": 1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_ts_nan_ignored():
    """T3 — ts = NaN : rejeté par garde isfinite."""
    raw = [{"timestamp": float("nan"), "price": 10.0, "amount": 1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_price_inf_ignored():
    """T3 — price = inf : rejeté par garde isfinite."""
    raw = [{"timestamp": 1_000, "price": float("inf"), "amount": 1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_price_nan_ignored():
    """T3 — price = NaN : rejeté par garde isfinite."""
    raw = [{"timestamp": 1_000, "price": float("nan"), "amount": 1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_size_inf_ignored():
    """T3 — size = inf : rejeté par garde isfinite."""
    raw = [{"timestamp": 1_000, "price": 10.0, "amount": float("inf"), "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_size_nan_ignored():
    """T3 — size = NaN : rejeté par garde isfinite."""
    raw = [{"timestamp": 1_000, "price": 10.0, "amount": float("nan"), "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_price_zero_ignored():
    """C4 — price == 0 : rejeté (défaut qualité donnée)."""
    raw = [{"timestamp": 1_000, "price": 0.0, "amount": 1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_price_negative_ignored():
    """C4 — price < 0 : rejeté."""
    raw = [{"timestamp": 1_000, "price": -1.0, "amount": 1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_size_zero_ignored():
    """C4 — size == 0 : rejeté (défaut qualité donnée)."""
    raw = [{"timestamp": 1_000, "price": 10.0, "amount": 0.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_size_negative_ignored():
    """C4 — size < 0 : rejeté."""
    raw = [{"timestamp": 1_000, "price": 10.0, "amount": -1.0, "side": "buy"}]
    assert list(_make_source(raw).trades()) == []


def test_trades_never_raises_on_bad_data():
    """T3 — trades() ne lève jamais, même avec un mélange de ts/price/size = inf et NaN."""
    raw = [
        {"timestamp": float("inf"), "price": 10.0,           "amount": 1.0,          "side": "buy"},
        {"timestamp": 1_000,        "price": float("nan"),   "amount": 1.0,          "side": "buy"},
        {"timestamp": 1_000,        "price": 10.0,           "amount": float("inf"), "side": "buy"},
        {"timestamp": float("nan"), "price": float("nan"),   "amount": float("nan"), "side": "sell"},
        _raw(ts=2_000, price=20.0, amount=1.0, side="sell"),  # seul trade valide
    ]
    try:
        result = list(_make_source(raw).trades())
    except Exception as exc:
        pytest.fail(f"trades() a levé une exception inattendue : {exc!r}")
    assert len(result) == 1
    assert result[0].ts == 2_000


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
