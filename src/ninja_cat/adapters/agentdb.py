"""Adapter mémoire AgentDB — parle à claude-flow via sa CLI.

Implémente `MemoryPort` en déléguant au paquet `@claude-flow/cli` (les commandes
`memory store` / `memory search`, documentées par le plugin ruflo-agentdb).

Dégradation gracieuse : si la CLI est absente, échoue ou expire, les opérations
retournent un résultat neutre (False / []) plutôt que de lever — le moteur n'est
jamais bloqué par l'indisponibilité du backend. C'est l'adapter qui se comporte
en no-op, pas le moteur qui doit s'en soucier.

NB : le format de sortie de `memory search` n'est pas figé tant que le serveur
n'est pas validé en live ; le parsing est donc *best-effort* (JSON si possible,
sinon lignes brutes). À affiner une fois claude-flow approuvé et connecté.
"""

from __future__ import annotations

import json
import subprocess

from ..memory import MemoryHit

# Version figée = celle du serveur MCP claude-flow (cf. .mcp.json).
_DEFAULT_CLI: tuple[str, ...] = ("npx", "-y", "@claude-flow/cli@3.6.12")


class AgentDbMemory:
    """Backend mémoire adossé à claude-flow / AgentDB (via CLI subprocess)."""

    def __init__(
        self,
        cli: tuple[str, ...] = _DEFAULT_CLI,
        timeout: float = 60.0,
    ) -> None:
        self._cli = cli
        self._timeout = timeout

    def store(self, namespace: str, key: str, value: str) -> bool:
        out = self._run(
            ["memory", "store", "--namespace", namespace, "--key", key, "--value", value]
        )
        return out is not None

    def search(self, namespace: str, query: str, limit: int = 5) -> list[MemoryHit]:
        out = self._run(
            ["memory", "search", "--namespace", namespace, "--query", query,
             "--limit", str(limit)]
        )
        if not out:
            return []
        return _parse_hits(out, limit)

    def _run(self, args: list[str]) -> str | None:
        """Exécute la CLI ; retourne stdout, ou None en cas d'échec (gracieux)."""
        try:
            proc = subprocess.run(
                [*self._cli, *args],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout


def _parse_hits(out: str, limit: int) -> list[MemoryHit]:
    """Parsing best-effort de la sortie `memory search`."""
    try:
        data = json.loads(out)
    except (json.JSONDecodeError, ValueError):
        lines = [ln for ln in out.splitlines() if ln.strip()]
        return [MemoryHit(key="", value=ln) for ln in lines[:limit]]

    rows = data if isinstance(data, list) else data.get("results", [])
    hits: list[MemoryHit] = []
    for row in rows[:limit]:
        if isinstance(row, dict):
            hits.append(
                MemoryHit(
                    key=str(row.get("key", "")),
                    value=str(row.get("value", row)),
                    score=_as_float(row.get("score")),
                )
            )
        else:
            hits.append(MemoryHit(key="", value=str(row)))
    return hits


def _as_float(x: object) -> float | None:
    try:
        return float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
