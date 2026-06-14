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
import shutil
import subprocess

from ..memory import MemoryHit

# Version figée = celle du serveur MCP claude-flow (cf. .mcp.json).
_DEFAULT_CLI: tuple[str, ...] = ("npx", "-y", "@claude-flow/cli@3.6.12")


class AgentDbMemory:
    """Backend mémoire adossé à claude-flow / AgentDB (via CLI subprocess)."""

    def __init__(
        self,
        cli: tuple[str, ...] = _DEFAULT_CLI,
        timeout: float = 120.0,
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
        """Exécute la CLI ; retourne stdout, ou None en cas d'échec (gracieux).

        Résout l'exécutable via `shutil.which` (cross-platform : sous Windows,
        `npx` est `npx.CMD` et n'est pas lançable par son seul nom).
        """
        exe = shutil.which(self._cli[0])
        if exe is None:  # CLI introuvable (ex. npx/claude-flow absent) -> no-op
            return None
        try:
            proc = subprocess.run(
                [exe, *self._cli[1:], *args],
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
    """Parse la sortie `memory search`.

    claude-flow 3.6 émet un tableau ASCII (Key | Score | Namespace | Preview),
    pas de JSON. On tente d'abord le JSON (versions futures), puis le tableau,
    puis en dernier recours les lignes brutes. NB : `value` porte le *Preview*
    du CLI, potentiellement tronqué — récupérer la valeur complète via `retrieve`
    si besoin.
    """
    try:
        data = json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return _parse_table(out, limit)

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


def _parse_table(out: str, limit: int) -> list[MemoryHit]:
    """Parse le tableau ASCII de claude-flow ; sinon, lignes brutes (compat)."""
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in out.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue  # ignore bordures (+---+), INFO, lignes vides
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        rows.append(dict(zip(header, cells)))

    if header is not None:  # c'était bien un tableau
        return [
            MemoryHit(
                key=r.get("key", ""),
                value=r.get("preview", r.get("value", "")),
                score=_as_float(r.get("score")),
            )
            for r in rows[:limit]
        ]

    lines = [ln for ln in out.splitlines() if ln.strip()]
    return [MemoryHit(key="", value=ln) for ln in lines[:limit]]


def _as_float(x: object) -> float | None:
    try:
        return float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
