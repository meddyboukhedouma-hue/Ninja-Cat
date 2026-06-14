"""Tests du port mémoire : fallback no-op, fabrique, et parsing de l'adapter."""

import pytest

from ninja_cat.adapters.agentdb import AgentDbMemory, _parse_hits
from ninja_cat.memory import MemoryHit, MemoryPort, NullMemory, get_memory


def test_nullmemory_is_a_memoryport():
    assert isinstance(NullMemory(), MemoryPort)


def test_nullmemory_is_noop():
    mem = NullMemory()
    assert mem.store("specs", "k", "v") is False
    assert mem.search("specs", "quoi que ce soit") == []


def test_get_memory_defaults_to_null():
    assert isinstance(get_memory(), NullMemory)


def test_get_memory_agentdb_is_a_memoryport():
    assert isinstance(get_memory("agentdb"), MemoryPort)


def test_get_memory_unknown_backend_raises():
    with pytest.raises(ValueError):
        get_memory("mystere")


def test_parse_hits_json_list():
    out = '[{"key": "ADR-001", "value": "doctrine", "score": 0.9}]'
    hits = _parse_hits(out, limit=5)
    assert hits == [MemoryHit(key="ADR-001", value="doctrine", score=0.9)]


def test_parse_hits_json_results_envelope_and_limit():
    out = '{"results": [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}]}'
    hits = _parse_hits(out, limit=1)
    assert len(hits) == 1
    assert hits[0].key == "a"


def test_parse_hits_non_json_falls_back_to_lines():
    out = "ligne 1\n\nligne 2\n"
    hits = _parse_hits(out, limit=5)
    assert [h.value for h in hits] == ["ligne 1", "ligne 2"]


def test_agentdb_search_graceful_when_cli_absent():
    # CLI bidon → le subprocess échoue → résultat neutre, jamais d'exception.
    mem = AgentDbMemory(cli=("ninjacat-cli-inexistant-xyz",), timeout=5.0)
    assert mem.search("specs", "q") == []
    assert mem.store("specs", "k", "v") is False
