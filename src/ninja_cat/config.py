"""Configuration centrale — scalaires calibrables du système.

Règle : aucun nombre magique dans la logique ; tout scalaire vit ici, nommé et
justifié. Les seuils sont *scale-free* (relatifs au volume, à une fenêtre, ou à
une convention standard).

Volontairement quasi vide pour l'instant : aucune stratégie n'est définie, donc
aucun seuil de stratégie n'existe. Les scalaires seront ajoutés par l'architecte
au fil des specs. Seul `tick_size` est présent — c'est une métadonnée de marché
(granularité de prix), indépendante de toute stratégie.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # --- métadonnée marché (par-symbole, seul paramètre non scale-free) ---
    tick_size: float = 0.1  # granularité de prix ; ex. BTC Hyperliquid ~ 0.1


DEFAULT_CONFIG = Config()
