"""Fonction de normalisation partagée entre les adapters d'ingestion.

Ce module est **interne** au sous-paquet `adapters` (préfixe `_`). Il ne doit
jamais être importé depuis le cœur (`ingestion.py`, `schema.py`).

Rôle unique : convertir quatre valeurs brutes (ts, price, size, side) en un
``Trade`` canonique, ou retourner ``None`` si la ligne est invalide. En
centralisant cette logique ici, les deux adapters (`CcxtSource` et
`FileReplaySource`) appliquent **exactement** le même filtre — ce qui garantit
l'invariant parité live == replay : une même donnée brute produit le même
``Trade`` quel que soit l'adapter qui la consomme.

Règles de rejet (toute violation → ``None``, jamais d'exception) :
- ``ts_raw`` : doit être convertible en entier **exact** (pas de flottant
  fractionnaire comme 1000.5 ; seuls 1000.0 → 1000 est accepté) ; doit être
  > 0 ; doit être fini (NaN, inf, -inf rejetés via ``math.isfinite`` AVANT
  ``int()`` pour éviter OverflowError).
- ``price_raw`` : flottant fini, > 0. (price == 0 est un défaut de qualité de
  donnée ; si un cas légitime émerge — tick_size zéro, instrument exotique —
  c'est à l'architecte de le décider, pas à la couche données d'absorber en
  silence.)
- ``size_raw`` : flottant fini, > 0. (Même raisonnement que price : size == 0
  signifie un trade annulé ou un artefact feed ; on rejette plutôt que de
  propager une donnée ambiguë. Si un échange légitime requiert size == 0 un
  jour, l'architecte tranchera et documentera.)
- ``side_raw`` : converti en minuscules avant lookup dans ``_SIDE_MAP`` —
  cohérence garantie entre les adapters. ccxt renvoie déjà 'buy'/'sell' en
  minuscules (documenté dans la doc ccxt) ; le ``lower()`` est appliqué
  systématiquement pour absorber toute variation de casse sans heuristique.
  Si la valeur n'est pas une ``str`` (ex. int, None) → rejet immédiat.
  Si la valeur str n'est pas dans le mapping (ex. '', 'taker', 'maker') → rejet.

Heuristique de fallback côté agresseur : **aucune**. On ne devine jamais le
côté (règle ADR-001 / zéro compromis sur la qualité de la donnée).
"""

from __future__ import annotations

import math
from typing import Any

from ninja_cat.schema import Side, Trade

# Mapping texte → Side canonique. La clé est **toujours en minuscules** ;
# l'appelant doit appliquer .lower() avant le lookup (fait dans normalize_trade).
_SIDE_MAP: dict[str, Side] = {
    "buy": Side.BUY,
    "sell": Side.SELL,
}


def normalize_trade(
    ts_raw: Any,
    price_raw: Any,
    size_raw: Any,
    side_raw: Any,
) -> Trade | None:
    """Convertit quatre valeurs brutes en ``Trade`` canonique, ou ``None``.

    Paramètres
    ----------
    ts_raw:
        Timestamp brut (int, float, str…). Doit représenter un entier > 0 en
        epoch ms UTC. Un flottant *exact* (ex. 1000.0) est accepté et converti
        en int ; un flottant fractionnaire (ex. 1000.5) est rejeté — on préfère
        un rejet explicite à une troncature silencieuse qui biaise l'horodatage.
    price_raw:
        Prix brut (int, float, str…). Doit être convertible en float fini > 0.
    size_raw:
        Taille brute (int, float, str…). Doit être convertible en float fini > 0.
    side_raw:
        Côté agresseur brut. Doit être une ``str`` contenant 'buy' ou 'sell'
        (insensible à la casse). Toute autre valeur (None, int, 'taker'…) → None.

    Retourne
    --------
    Trade
        Instance canonique si toutes les gardes sont franchies.
    None
        Si l'une quelconque des valeurs est invalide (NaN, inf, hors-borne,
        type inattendu, side non reconnu, ts fractionnaire…).

    Jamais d'exception remontante — toute erreur inattendue est capturée et
    traitée comme un rejet.
    """
    # ── timestamp ────────────────────────────────────────────────────────────
    if ts_raw is None:
        return None
    try:
        ts_float = float(ts_raw)
    except (TypeError, ValueError):
        return None
    # Rejet NaN et inf AVANT int() — int(float('inf')) lève OverflowError.
    if not math.isfinite(ts_float):
        return None
    # Rejet flottant fractionnaire : on exige un entier exact.
    # 1000.0 → int 1000 (accepté) ; 1000.5 → rejet.
    if ts_float != int(ts_float):
        return None
    ts = int(ts_float)
    if ts <= 0:
        return None

    # ── price ─────────────────────────────────────────────────────────────────
    if price_raw is None:
        return None
    try:
        price = float(price_raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(price):
        return None
    # price == 0 est un artefact ; price < 0 est impossible sur un marché réel.
    if price <= 0:
        return None

    # ── size ──────────────────────────────────────────────────────────────────
    if size_raw is None:
        return None
    try:
        size = float(size_raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(size):
        return None
    # size == 0 : trade annulé ou artefact feed (voir docstring module).
    if size <= 0:
        return None

    # ── side agresseur ────────────────────────────────────────────────────────
    # Pas de heuristique : on n'accepte que 'buy' et 'sell' (insensible à la
    # casse). ccxt renvoie déjà ces valeurs en minuscules, mais .lower() est
    # appliqué systématiquement pour une cohérence garantie entre adapters.
    if not isinstance(side_raw, str):
        return None
    side = _SIDE_MAP.get(side_raw.lower())
    if side is None:
        return None

    return Trade(ts=ts, price=price, size=size, side=side)
