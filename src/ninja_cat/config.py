"""Configuration centrale — tous les scalaires calibrables vivent ici.

Règle : aucun nombre magique dans la logique. Les seuils sont *scale-free*
(relatifs au volume de la barre, à une fenêtre, ou à une convention standard).
Seul `tick_size` est par-symbole.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    # --- par-symbole (seul paramètre non scale-free) ---
    tick_size: float = 0.1  # ex. BTC Hyperliquid ~ 0.1

    # --- conventions standards (pas devinées) ---
    imbalance_ratio: float = 3.0          # déséquilibre diagonal 3:1
    volume_spike_mult: float = 1.0        # > moyenne mobile des N dernières barres
    volume_ma_window: int = 20            # N pour la moyenne mobile de volume

    # --- comparaisons sur N barres consécutives ---
    sequence_window: int = 3              # transition / surge: |delta| mono sur N

    # --- tolérances scale-free (fraction du volume de la barre) ---
    flip_absent_frac: float = 0.02        # "côté absent": extrême négligeable vs volume
    flip_burst_frac: float = 0.20         # "explosion": extrême opposé grand vs volume

    # --- géométrie POC ---
    poc_top_threshold: float = 2 / 3      # tiers haut = "en haut"
    poc_bottom_threshold: float = 1 / 3   # tiers bas = "en bas"

    # --- séquençage S/R ---
    sequence_min_levels: int = 4          # >= 4 niveaux à volume strictement croissant


DEFAULT_CONFIG = Config()
