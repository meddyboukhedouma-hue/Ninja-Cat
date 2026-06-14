"""Schéma canonique de la donnée de marché.

Tout flux entrant (CCXT, websocket exchange, fichiers) est normalisé vers ces
structures. Le reste du système ne voit que ce schéma. Horloge en UTC, epoch ms.

Volontairement minimal : on ne modélise ici que la donnée de marché **brute**,
neutre vis-à-vis de toute stratégie. Les agrégats (type de barre, primitives
dérivées) sont des choix de méthodologie — ils seront définis par l'architecte
une fois une stratégie choisie, pas avant.

Convention : `side` = côté agresseur (taker) quand la source le fournit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    """Côté agresseur (taker)."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Trade:
    """Un trade normalisé — la primitive de marché brute, sans hypothèse de stratégie."""

    ts: int        # timestamp epoch ms (UTC, monotone)
    price: float
    size: float
    side: Side

    @property
    def signed_size(self) -> float:
        """Taille signée par le côté agresseur (+ buy / - sell)."""
        return self.size if self.side is Side.BUY else -self.size
