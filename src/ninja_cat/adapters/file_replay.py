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

Colonne d'identifiant optionnelle
----------------------------------
Si le fichier contient une colonne ``id`` ou ``trade_id``, elle est utilisée
pour la déduplication par identité native (priorité à ``id`` si les deux sont
présentes). Sans cette colonne, la déduplication sur le quadruplet
``(ts, price, size, side)`` est **désactivée** — on préfère conserver des
données potentiellement dupliquées plutôt que détruire silencieusement des
trades réellement distincts partageant ce quadruplet. Un warning est loggé
pour signaler que la dédup est désactivée.

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
- valeur manquante/None/NaN/inf pour ts, price ou size
- ts fractionnaire (ex. 1000.5) : rejeté — pas de troncature silencieuse
- price <= 0 ou size <= 0 : rejetés (défaut qualité donnée)
- ``side`` non reconnu (autre que 'buy'/'sell', insensible à la casse) : ligne ignorée
- Toute exception inattendue dans trades() : itérateur vide (inviolable)

Invariants du port garantis (ADR-004)
--------------------------------------
1. Ordre chronologique : tri par ``ts`` croissant avant tout yield.
2. Déduplication par colonne ``id``/``trade_id`` si présente ; sinon pas de
   dédup (voir section « Colonne d'identifiant optionnelle » ci-dessus).

Normalisation déléguée à ``ninja_cat.adapters._normalize.normalize_trade`` —
même contrat que CcxtSource, invariant live == replay garanti.

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

from ninja_cat.adapters._normalize import normalize_trade
from ninja_cat.ingestion import MarketDataPort
from ninja_cat.schema import Trade

logger = logging.getLogger(__name__)

# Extensions reconnues → identifiant de format interne.
_EXT_TO_FMT: dict[str, str] = {
    ".parquet": "parquet",
    ".csv": "csv",
}

# Noms de colonnes candidats pour l'identifiant natif du trade.
# Priorité : 'id' > 'trade_id'.
_ID_COLUMN_CANDIDATES: tuple[str, ...] = ("id", "trade_id")


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
        - Déduplication par id natif si disponible ; sinon pas de dédup
          (voir module docstring pour la politique complète).
        - Dégradation gracieuse inviolable : TOUTE exception inattendue est
          capturée ici — trades() ne peut jamais remonter d'exception au moteur.
        """
        try:
            yield from self._trades_inner()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "FileReplaySource.trades(%r) : exception inattendue interceptée "
                "— flux vide. %s",
                str(self._path),
                exc,
            )
            return

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _trades_inner(self) -> Iterator[Trade]:
        """Logique principale — appelée depuis trades() sous try/except global."""
        df = self._load_dataframe()
        if df is None:
            return

        canonical: list[tuple[str | None, Trade]] = list(self._normalise(df))
        if not canonical:
            return

        # 1. Tri par ts croissant — garantit la monotonicité avant dédup.
        canonical.sort(key=lambda pair: pair[1].ts)

        # 2. Déduplication par id natif si disponible.
        has_ids = any(trade_id is not None for trade_id, _ in canonical)
        if not has_ids:
            logger.warning(
                "FileReplaySource(%r) : aucune colonne 'id'/'trade_id' trouvée "
                "— déduplication désactivée pour ne pas détruire de données.",
                str(self._path),
            )
            for _, trade in canonical:
                yield trade
            return

        seen_ids: set[str] = set()
        for trade_id, trade in canonical:
            if trade_id is not None:
                if trade_id in seen_ids:
                    continue
                seen_ids.add(trade_id)
            yield trade

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

    def _normalise(self, df) -> Iterator[tuple[str | None, Trade]]:
        """Convertit chaque ligne du DataFrame en ``(trade_id, Trade)`` canonique.

        La colonne d'id natif (``id`` ou ``trade_id``) est extraite pour
        permettre la déduplication par identité dans _trades_inner(). Elle peut
        être None si la colonne est absente ou si la cellule est NaN.

        Une ligne avec un champ manquant, None/NaN/inf, price/size <= 0, ts
        fractionnaire ou un side non reconnu est **ignorée silencieusement** —
        on ne propage jamais une donnée douteuse (ADR-001). La normalisation est
        déléguée à normalize_trade() pour garantir la parité live == replay.
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

        # Détecte la colonne d'identifiant natif si elle existe.
        id_col: str | None = None
        for candidate in _ID_COLUMN_CANDIDATES:
            if candidate in df.columns:
                id_col = candidate
                break

        for _, row in df.iterrows():
            # Extrait l'id natif si disponible (NaN pandas → None).
            trade_id: str | None = None
            if id_col is not None:
                raw_id = row.get(id_col)
                # pandas NaN est un float ; on vérifie via pandas isna si possible,
                # sinon on tente isinstance float NaN.
                try:
                    import math as _math
                    if raw_id is not None and not (
                        isinstance(raw_id, float) and _math.isnan(raw_id)
                    ):
                        trade_id = str(raw_id)
                except (TypeError, ValueError):
                    trade_id = None

            trade = normalize_trade(
                ts_raw=row.get("ts"),
                price_raw=row.get("price"),
                size_raw=row.get("size"),
                side_raw=row.get("side"),
            )
            if trade is None:
                continue

            yield trade_id, trade


# ------------------------------------------------------------------
# Conformité protocole (vérification statique à l'import)
# ------------------------------------------------------------------
assert hasattr(FileReplaySource, "trades"), "FileReplaySource doit exposer trades()"
