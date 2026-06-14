"""Port mémoire — frontière hexagonale entre le moteur et le stockage.

Le moteur (cœur de doctrine) ne connaît que l'interface `MemoryPort`. Il ne sait
rien d'AgentDB, de claude-flow, ni d'aucun backend concret : ceux-ci sont des
*adapters* branchés derrière le port (cf. `ninja_cat.adapters`).

Conséquence voulue (ADR-001) : si le backend mémoire tombe ou est absent, le
moteur tourne **identique** — le fallback `NullMemory` ne fait rien, sans erreur.
La mémoire range et retrouve ce que le moteur produit ; elle ne calcule jamais
de doctrine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class MemoryHit:
    """Un résultat de recherche mémoire."""

    key: str
    value: str
    score: float | None = None  # pertinence (sémantique) si le backend la fournit


@runtime_checkable
class MemoryPort(Protocol):
    """Contrat minimal de persistance/recherche que le moteur attend.

    Volontairement étroit : `store` (écrire) + `search` (retrouver, sémantique
    quand le backend le permet). Tout adapter concret implémente ce protocole.
    """

    def store(self, namespace: str, key: str, value: str) -> bool:
        """Range `value` sous (`namespace`, `key`). Retourne True si stocké."""
        ...

    def search(self, namespace: str, query: str, limit: int = 5) -> list[MemoryHit]:
        """Retrouve jusqu'à `limit` entrées de `namespace` proches de `query`."""
        ...


class NullMemory:
    """Fallback no-op : n'écrit rien, ne retrouve rien — jamais d'erreur.

    Garantit que le moteur fonctionne à l'identique en l'absence de backend.
    """

    def store(self, namespace: str, key: str, value: str) -> bool:
        return False

    def search(self, namespace: str, query: str, limit: int = 5) -> list[MemoryHit]:
        return []


def get_memory(backend: str = "null") -> MemoryPort:
    """Fabrique l'implémentation du port mémoire.

    Par défaut `null` (no-op) — sûr, déterministe, sans effet de bord. Passer
    `agentdb` pour brancher claude-flow/AgentDB (import paresseux : le cœur n'est
    jamais couplé à l'adapter).
    """
    if backend == "agentdb":
        from .adapters.agentdb import AgentDbMemory

        return AgentDbMemory()
    if backend == "null":
        return NullMemory()
    raise ValueError(f"backend mémoire inconnu : {backend!r}")
