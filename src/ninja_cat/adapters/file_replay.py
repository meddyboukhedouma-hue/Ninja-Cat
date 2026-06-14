"""Adapter replay fichier — lit des trades historiques Parquet ou CSV et les normalise.

Implémente ``MarketDataPort`` : expose ``trades()`` qui itère des ``Trade``
canoniques lus depuis un fichier disque. Utilisé pour le replay historique
et pour les tests d'intégration sans réseau.

Colonnes canoniques attendues dans le fichier
---------------------------------------------
- ``ts``    : timestamp epoch ms (UTC), entier ou numérique
- ``price`` : prix, flottant
- ``size``  : taille, flottant
- ``side``  : côté agresseur texte, « buy » ou « sell » (insensible à la casse)

Mapping de colonnes optionnel
-----------------------------
Passer ``column_map={nom_fichier: nom_canonique}`` pour les fichiers dont les
entêtes diffèrent des noms canoniques (ex. ``{"qty": "size", "time_ms": "ts"}``).
Les colonnes sans correspondance dans le mapping sont cherchées sous leur nom
canonique direct. Au-delà du mapping, aucune heuristique de devinette.

Formats supportés
-----------------
- ``.parquet`` — lu via pyarrow/pandas.
- ``.csv``     — lu via pandas.
Le format peut être forcé explicitement via ``fmt="parquet"`` ou ``fmt="csv"``.

Dégradation gracieuse
---------------------
Dans tous les cas suivants, ``trades()`` retourne un itérateur **vide** sans
lever d'exception — le moteur n'est jamais bloqué :

- fichier absent ou illisible
- format non supporté (extension inconnue, ``fmt`` non reconnu)
- pandas ou pyarrow absent (ImportError intercepté)
- colonnes canoniques manquantes dans le DataFrame
- valeur manquante/None/NaN pour ts, price ou size
- ``side`` non reconnu (autre que 'buy'/'sell') : la **ligne** est ignorée

Invariants du port garantis (ADR-004)
--------------------------------------
1. Ordre chronologique : tri par ``ts`` croissant avant tout yield.
2. Absence de doublons : déduplication sur ``(ts, price, size, side)`` après
   le tri — même schéma que ``ccxt_source.py``.

Décision get_source()
----------------------
``FileReplaySource`` exige un chemin de fichier à la construction ; il ne peut
pas être instancié par la fabrique ``get_source()`` (qui ne prend qu'un nom de
backend sans argument). On l'instancie directement, comme ``ReplaySource`` et
``CcxtSource``. La fabrique n'est pas modifiée.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from ninja_cat.ingestion import MarketDataPort
from ninja_cat.schema import Side, Trade

logger = logging.getLogger(__name__)

# Mapping insensible à la casse : texte fichier → Side canonique.
_SIDE_MAP: dict[str, Side] = {
    "buy": Side.BUY,
    "sell": Side.SELL,
}

# Extensions reconnues → identifiant de format interne.
_EXT_TO_FMT: dict[str, str] = {
    ".parquet": "parquet",
    ".csv": "csv",
}


class FileReplaySource:
    """Source de replay depuis un fichier Parquet ou CSV.

    Paramètres
    ----------
    path:
        Chemin vers le fichier à lire (absolu ou relatif).
    column_map:
        Dictionnaire optionnel ``{nom_colonne_fichier: nom_canonique}``
        (ex. ``{"qty": "size", "time_ms": "ts"}``). Permet d'adapter les
        fichiers dont les entêtes ne correspondent pas aux noms canoniques.
        Les colonnes absentes du mapping sont cherchées telles quelles.
    fmt:
        Force le format (``"parquet"`` ou ``"csv"``). Si ``None``, le format
        est détecté par l'extension du fichier. Passer un fmt explicite est
        utile quand l'extension est absente ou trompeuse.
    """

    def __init__(
        self,
        path: str | Path,
        column_map: dict[str, str] | None = None,
        fmt: str | None = None,
    ) -> None:
        self._path = Path(path)
        self._column_map: dict[str, str] = column_map or {}
        self._fmt = fmt  # None → auto-détection par extension

    # ------------------------------------------------------------------
    # MarketDataPort
    # ------------------------------------------------------------------

    def trades(self) -> Iterator[Trade]:
        """Itère les trades normalisés depuis le fichier.

        Respecte les invariants du port :
        - ts monotone croissant (tri sur ts avant yield).
        - Aucun doublon (déduplication sur (ts, price, size, side) après tri).
        - Dégradation gracieuse : tout échec produit un itérateur vide.
        """
        df = self._load_dataframe()
        if df is None:
            return

        canonical = list(self._normalise(df))
        if not canonical:
            return

        # 1. Tri par ts croissant — garantit la monotonicité avant dédup.
        canonical.sort(key=lambda t: t.ts)

        # 2. Déduplication : on conserve la première occurrence de chaque
        #    (ts, price, size, side). L'ordre est préservé car on itère
        #    après le tri.
        seen: set[tuple[int, float, float, Side]] = set()
        for trade in canonical:
            key = (trade.ts, trade.price, trade.size, trade.side)
            if key in seen:
                continue
            seen.add(key)
            yield trade

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _detect_fmt(self) -> str | None:
        """Détecte le format à partir de l'extension ou de ``self._fmt``.

        Retourne l'identifiant de format (``"parquet"`` / ``"csv"``) ou
        ``None`` si non supporté.
        """
        if self._fmt is not None:
            fmt = self._fmt.lower()
            if fmt not in ("parquet", "csv"):
                logger.warning(
                    "FileReplaySource : format %r non supporté — flux vide.", self._fmt
                )
                return None
            return fmt

        ext = self._path.suffix.lower()
        fmt = _EXT_TO_FMT.get(ext)
        if fmt is None:
            logger.warning(
                "FileReplaySource : extension %r non reconnue pour %r — flux vide.",
                ext,
                str(self._path),
            )
        return fmt

    def _load_dataframe(self):  # type: ignore[return]
        """Charge le fichier en DataFrame. Retourne ``None`` en cas d'échec."""
        fmt = self._detect_fmt()
        if fmt is None:
            return None

        if not self._path.exists():
            logger.warning(
                "FileReplaySource : fichier absent %r — flux vide.", str(self._path)
            )
            return None

        try:
            import pandas as pd  # lazy import — le cœur ne porte jamais pandas
        except ImportError:
            logger.warning(
                "FileReplaySource : pandas non disponible — flux vide."
            )
            return None

        try:
            if fmt == "parquet":
                # pyarrow est le backend par défaut de pandas pour Parquet ;
                # on importe explicitement pour détecter son absence.
                try:
                    import pyarrow  # noqa: F401  — vérifie la présence sans l'utiliser
                except ImportError:
                    logger.warning(
                        "FileReplaySource : pyarrow non disponible pour lire "
                        "Parquet — flux vide."
                    )
                    return None
                df = pd.read_parquet(self._path)
            else:  # csv
                df = pd.read_csv(self._path)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "FileReplaySource : impossible de lire %r : %s — flux vide.",
                str(self._path),
                exc,
            )
            return None

        return df

    def _apply_column_map(self, df) -> object:
        """Renomme les colonnes du DataFrame selon ``self._column_map``.

        Seules les colonnes présentes dans le DataFrame ET dans le mapping
        sont renommées. Les autres restent inchangées.
        """
        # Filtre : uniquement les entrées dont la source existe dans df.
        rename = {src: dst for src, dst in self._column_map.items() if src in df.columns}
        if rename:
            df = df.rename(columns=rename)
        return df

    def _normalise(self, df) -> Iterator[Trade]:
        """Convertit chaque ligne du DataFrame en ``Trade`` canonique.

        Une ligne avec un champ manquant, None/NaN, ou un side non reconnu
        est **ignorée silencieusement** — on ne propage jamais une donnée
        douteuse (ADR-001), et on ne devine jamais le côté agresseur.
        """
        df = self._apply_column_map(df)

        # Vérification de la présence des quatre colonnes canoniques.
        required = {"ts", "price", "size", "side"}
        missing = required - set(df.columns)
        if missing:
            logger.warning(
                "FileReplaySource : colonnes manquantes %r dans %r — flux vide.",
                sorted(missing),
                str(self._path),
            )
            return

        for _, row in df.iterrows():
            # --- timestamp ---
            ts_raw = row.get("ts")
            if ts_raw is None:
                continue
            # pandas peut retourner NaN (float) pour une cellule vide
            try:
                import math
                if isinstance(ts_raw, float) and math.isnan(ts_raw):
                    continue
                ts = int(ts_raw)
            except (TypeError, ValueError):
                continue
            if ts <= 0:
                continue

            # --- price ---
            price_raw = row.get("price")
            if price_raw is None:
                continue
            try:
                import math as _math
                if isinstance(price_raw, float) and _math.isnan(price_raw):
                    continue
                price = float(price_raw)
            except (TypeError, ValueError):
                continue

            # --- size ---
            size_raw = row.get("size")
            if size_raw is None:
                continue
            try:
                import math as _math2
                if isinstance(size_raw, float) and _math2.isnan(size_raw):
                    continue
                size = float(size_raw)
            except (TypeError, ValueError):
                continue

            # --- side agresseur ---
            # On utilise le côté tel que fourni par le fichier (source native).
            # Aucune heuristique : si le champ est absent ou non reconnu, la
            # ligne est ignorée (règle ADR-001 / zéro compromis sur la qualité).
            side_raw = row.get("side")
            if not isinstance(side_raw, str):
                continue
            side = _SIDE_MAP.get(side_raw.lower())
            if side is None:
                continue

            yield Trade(ts=ts, price=price, size=size, side=side)


# ------------------------------------------------------------------
# Conformité protocole (vérification statique à l'import)
# ------------------------------------------------------------------
assert hasattr(FileReplaySource, "trades"), "FileReplaySource doit exposer trades()"
