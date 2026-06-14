"""Schéma canonique de la donnée de marché.

Tout flux entrant (CCXT, websocket exchange, fichiers) est normalisé vers ces
structures. Le reste du système ne voit que ce schéma. Horloge en UTC, epoch ms.

Convention agresseur : taker buy -> ASK (delta +) ; taker sell -> BID (delta -).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    """Côté agresseur (taker)."""

    BUY = "buy"    # taker buy  -> ask, delta +
    SELL = "sell"  # taker sell -> bid, delta -


@dataclass(frozen=True)
class Trade:
    """Un trade normalisé (côté agresseur natif quand la source le fournit)."""

    ts: int        # timestamp epoch ms (UTC, monotone)
    price: float
    size: float
    side: Side

    @property
    def signed_size(self) -> float:
        """Taille signée selon la convention agresseur (+ buy / - sell)."""
        return self.size if self.side is Side.BUY else -self.size


@dataclass(frozen=True)
class Bar:
    """Bougie footprint agrégée — primitives minimales par barre.

    `levels` : {prix: (bid_vol, ask_vol)} pour séquençage / imbalance.
    """

    ts_open: int
    ts_close: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    delta: float            # delta net (close du delta cumulé)
    delta_max: float        # pic du delta cumulé intra-barre
    delta_min: float        # creux du delta cumulé intra-barre
    poc_price: float        # niveau de plus gros volume
    poc_position: float     # position du POC dans [low, high] : 0 = bas, 1 = haut
    levels: dict[float, tuple[float, float]]
