"""Tests de la coquille EngineCore — neutre, sans doctrine.

On vérifie :
- Construction par défaut sûre (NullSource/NullMemory) → flux vide.
- Consommation d'un flux replay : comptage et fenêtre temporelle exacts.
- Le hook _on_trade se déclenche une fois par trade, dans l'ordre.
- Neutralité : le moteur ne modifie/réordonne/écarte aucun trade et n'écrit
  rien en mémoire de lui-même.
- Déterminisme : deux passages sur la même source donnent le même bilan.
- Le moteur consomme via le contrat MarketDataPort (duck-typing).
"""

from __future__ import annotations

from typing import Iterator

from ninja_cat.engine import EngineCore, RunStats
from ninja_cat.ingestion import NullSource, ReplaySource
from ninja_cat.memory import MemoryHit, NullMemory
from ninja_cat.schema import Side, Trade

# ── Fixtures ──────────────────────────────────────────────────────────────────

TRADE_A = Trade(ts=1_700_000_000_000, price=30_000.0, size=0.5, side=Side.BUY)
TRADE_B = Trade(ts=1_700_000_001_000, price=30_001.0, size=0.25, side=Side.SELL)
TRADE_C = Trade(ts=1_700_000_002_000, price=30_002.0, size=1.0, side=Side.BUY)


class _RecordingMemory:
    """Espion mémoire : implémente MemoryPort et enregistre tout appel à store."""

    def __init__(self) -> None:
        self.stored: list[tuple[str, str, str]] = []

    def store(self, namespace: str, key: str, value: str) -> bool:
        self.stored.append((namespace, key, value))
        return True

    def search(self, namespace: str, query: str, limit: int = 5) -> list[MemoryHit]:
        return []


class _CollectingEngine(EngineCore):
    """Sous-classe qui branche le hook _on_trade pour collecter les trades vus.

    Sert à prouver que la couture de doctrine se déclenche correctement — sans
    introduire de doctrine (collecter n'est pas décider).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.seen: list[Trade] = []

    def _on_trade(self, trade: Trade) -> None:
        self.seen.append(trade)


# ── Construction par défaut ───────────────────────────────────────────────────

def test_default_construction_uses_null_ports():
    """Sans argument, le moteur utilise NullSource/NullMemory (sûr, déterministe)."""
    engine = EngineCore()
    assert isinstance(engine.source, NullSource)
    assert isinstance(engine.memory, NullMemory)


def test_run_on_empty_source_returns_zeroed_stats():
    """Un flux vide → aucun trade traité, fenêtre temporelle None."""
    stats = EngineCore(NullSource()).run()
    assert stats == RunStats(processed=0, first_ts=None, last_ts=None)


# ── Consommation d'un flux replay ─────────────────────────────────────────────

def test_run_counts_all_trades():
    stats = EngineCore(ReplaySource([TRADE_A, TRADE_B, TRADE_C])).run()
    assert stats.processed == 3


def test_run_captures_time_window():
    """first_ts/last_ts reflètent le premier et le dernier trade consommés."""
    stats = EngineCore(ReplaySource([TRADE_A, TRADE_B, TRADE_C])).run()
    assert stats.first_ts == TRADE_A.ts
    assert stats.last_ts == TRADE_C.ts


def test_run_single_trade_window_collapses():
    """Avec un seul trade, first_ts == last_ts."""
    stats = EngineCore(ReplaySource([TRADE_B])).run()
    assert stats.processed == 1
    assert stats.first_ts == stats.last_ts == TRADE_B.ts


# ── Hook de doctrine (_on_trade) ──────────────────────────────────────────────

def test_on_trade_fires_once_per_trade_in_order():
    """Le hook se déclenche pour chaque trade, dans l'ordre exact de la source."""
    engine = _CollectingEngine(ReplaySource([TRADE_A, TRADE_B, TRADE_C]))
    engine.run()
    assert engine.seen == [TRADE_A, TRADE_B, TRADE_C]


def test_default_on_trade_is_noop():
    """Le hook par défaut ne fait rien et ne lève pas (neutralité)."""
    assert EngineCore()._on_trade(TRADE_A) is None


# ── Neutralité ────────────────────────────────────────────────────────────────

def test_engine_does_not_mutate_or_reorder_trades():
    """Les trades vus par le hook sont identiques et dans le même ordre (parité)."""
    recorded = [TRADE_C, TRADE_A, TRADE_B]  # ordre quelconque : le moteur ne trie pas
    engine = _CollectingEngine(ReplaySource(recorded))
    engine.run()
    assert engine.seen == recorded


def test_neutral_engine_writes_nothing_to_memory():
    """La coquille neutre n'écrit jamais en mémoire d'elle-même (rien à persister
    sans doctrine). Le port est détenu, pas utilisé.
    """
    spy = _RecordingMemory()
    EngineCore(ReplaySource([TRADE_A, TRADE_B, TRADE_C]), memory=spy).run()
    assert spy.stored == []


def test_memory_port_is_available_to_subclass_hook():
    """Le port mémoire est accessible via self.memory pour la doctrine future."""
    spy = _RecordingMemory()
    engine = EngineCore(NullSource(), memory=spy)
    assert engine.memory is spy


# ── Déterminisme ──────────────────────────────────────────────────────────────

def test_run_is_deterministic_across_calls():
    """Deux passages sur la même source produisent le même bilan."""
    engine = EngineCore(ReplaySource([TRADE_A, TRADE_B, TRADE_C]))
    assert engine.run() == engine.run()


# ── Conformité au contrat MarketDataPort (duck-typing) ────────────────────────

def test_run_consumes_any_marketdataport():
    """Le moteur consomme tout objet respectant trades() — pas seulement les
    sources connues (frontière hexagonale : il ne dépend que du protocole).
    """

    class _AdHocSource:
        def trades(self) -> Iterator[Trade]:
            yield TRADE_A
            yield TRADE_B

    stats = EngineCore(_AdHocSource()).run()
    assert stats.processed == 2
    assert stats.first_ts == TRADE_A.ts
    assert stats.last_ts == TRADE_B.ts
