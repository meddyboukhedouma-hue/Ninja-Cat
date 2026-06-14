"""Tests du port d'ingestion : fallback no-op, replay, fabrique et conformité au protocole."""

import pytest

from ninja_cat.ingestion import MarketDataPort, NullSource, ReplaySource, get_source
from ninja_cat.schema import Side, Trade


# ── Fixtures ────────────────────────────────────────────────────────────────

TRADE_A = Trade(ts=1_700_000_000_000, price=30_000.0, size=0.5, side=Side.BUY)
TRADE_B = Trade(ts=1_700_000_001_000, price=30_001.0, size=0.25, side=Side.SELL)
TRADE_C = Trade(ts=1_700_000_002_000, price=30_002.0, size=1.0, side=Side.BUY)


# ── NullSource ───────────────────────────────────────────────────────────────

def test_nullsource_is_a_marketdataport():
    assert isinstance(NullSource(), MarketDataPort)


def test_nullsource_produces_no_trades():
    src = NullSource()
    assert list(src.trades()) == []


def test_nullsource_trades_is_iterable_multiple_times():
    """Chaque appel à trades() retourne un itérateur indépendant (pas d'état partagé)."""
    src = NullSource()
    assert list(src.trades()) == []
    assert list(src.trades()) == []


# ── ReplaySource ─────────────────────────────────────────────────────────────

def test_replaysource_is_a_marketdataport():
    assert isinstance(ReplaySource([]), MarketDataPort)


def test_replaysource_empty_list_produces_no_trades():
    src = ReplaySource([])
    assert list(src.trades()) == []


def test_replaysource_replays_exact_sequence():
    """Les trades sont émis dans l'ordre exact fourni à la construction."""
    src = ReplaySource([TRADE_A, TRADE_B, TRADE_C])
    result = list(src.trades())
    assert result == [TRADE_A, TRADE_B, TRADE_C]


def test_replaysource_preserves_all_fields():
    """Tous les champs du Trade canonique sont préservés à l'identique."""
    src = ReplaySource([TRADE_B])
    (trade,) = src.trades()
    assert trade.ts == TRADE_B.ts
    assert trade.price == TRADE_B.price
    assert trade.size == TRADE_B.size
    assert trade.side == TRADE_B.side


def test_replaysource_signed_size_consistent():
    """signed_size est cohérent avec le côté agresseur pour les trades rejoués."""
    src = ReplaySource([TRADE_A, TRADE_B])
    result = list(src.trades())
    assert result[0].signed_size > 0   # BUY → positif
    assert result[1].signed_size < 0   # SELL → négatif


def test_replaysource_each_call_produces_independent_iterator():
    """Deux appels successifs à trades() produisent chacun la séquence complète."""
    src = ReplaySource([TRADE_A, TRADE_B])
    first = list(src.trades())
    second = list(src.trades())
    assert first == second == [TRADE_A, TRADE_B]


# ── get_source (fabrique) ────────────────────────────────────────────────────

def test_get_source_defaults_to_null():
    assert isinstance(get_source(), NullSource)


def test_get_source_null_explicit():
    assert isinstance(get_source("null"), NullSource)


def test_get_source_unknown_backend_raises():
    with pytest.raises(ValueError):
        get_source("ccxt_fantome")


# ── Parité live == replay ────────────────────────────────────────────────────

def test_replay_parity_same_output_as_recorded_sequence():
    """Parité stricte : ReplaySource(sequence) produit exactement `sequence`.

    Cette propriété est le fondement de la reproductibilité : le replay DOIT
    produire la même sortie que le live sur les mêmes trades. Ici on vérifie
    que ReplaySource ne modifie, ne réordonne et n'écarte aucun trade.
    """
    recorded = [TRADE_A, TRADE_B, TRADE_C]
    src = ReplaySource(recorded)
    assert list(src.trades()) == recorded
