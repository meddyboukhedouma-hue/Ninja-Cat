"""Tests de l'adapter FileReplaySource — aucun appel réseau.

Tous les fichiers sont écrits dans tmp_path (pytest). On vérifie :
- Lecture Parquet et CSV.
- Mapping de colonnes custom.
- Tri chronologique (ts croissant).
- Déduplication par id natif quand disponible (C1) ; pas de dédup sur quadruplet.
- Side insensible à la casse (C5).
- Gardes de finitude (NaN, inf, C2) et rejet price/size <= 0 (C4).
- Conformité au protocole MarketDataPort.
- Dégradation gracieuse dans tous les cas d'erreur.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterator

import pandas as pd
import pytest

from ninja_cat.adapters.file_replay import FileReplaySource
from ninja_cat.ingestion import MarketDataPort
from ninja_cat.schema import Side, Trade


# ── Helpers ──────────────────────────────────────────────────────────────────

def _df(rows: list[dict]) -> pd.DataFrame:
    """Construit un DataFrame minimal depuis une liste de dicts."""
    return pd.DataFrame(rows)


def _canonical_row(
    ts: int = 1_700_000_000_000,
    price: float = 30_000.0,
    size: float = 0.5,
    side: str = "buy",
    trade_id: str | None = None,
) -> dict:
    """Retourne un dict avec les colonnes canoniques (et 'id' optionnel)."""
    d = {"ts": ts, "price": price, "size": size, "side": side}
    if trade_id is not None:
        d["id"] = trade_id
    return d


def _write_parquet(path: Path, rows: list[dict]) -> Path:
    file = path / "trades.parquet"
    _df(rows).to_parquet(file, index=False)
    return file


def _write_csv(path: Path, rows: list[dict], name: str = "trades.csv") -> Path:
    file = path / name
    _df(rows).to_csv(file, index=False)
    return file


# ── Conformité au protocole ───────────────────────────────────────────────────

def test_file_replay_source_is_a_marketdataport(tmp_path: Path):
    """FileReplaySource satisfait le protocole MarketDataPort."""
    f = _write_parquet(tmp_path, [_canonical_row()])
    src = FileReplaySource(f)
    assert isinstance(src, MarketDataPort)


def test_trades_returns_iterator(tmp_path: Path):
    f = _write_csv(tmp_path, [_canonical_row()])
    src = FileReplaySource(f)
    result = src.trades()
    assert hasattr(result, "__iter__") and hasattr(result, "__next__")


# ── Lecture Parquet ───────────────────────────────────────────────────────────

def test_read_parquet_single_trade(tmp_path: Path):
    """Un fichier Parquet avec un trade canonique → un Trade normalisé."""
    rows = [_canonical_row(ts=1_700_000_000_000, price=30_000.0, size=0.5, side="buy")]
    f = _write_parquet(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    t = trades[0]
    assert t.ts == 1_700_000_000_000
    assert t.price == 30_000.0
    assert t.size == 0.5
    assert t.side is Side.BUY


def test_read_parquet_sell_trade(tmp_path: Path):
    """Un trade 'sell' dans Parquet → Side.SELL."""
    rows = [_canonical_row(side="sell")]
    f = _write_parquet(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].side is Side.SELL


def test_read_parquet_multiple_trades(tmp_path: Path):
    """Plusieurs trades Parquet → tous normalisés."""
    rows = [
        _canonical_row(ts=1_000, price=10.0, size=1.0, side="buy"),
        _canonical_row(ts=2_000, price=20.0, size=2.0, side="sell"),
        _canonical_row(ts=3_000, price=30.0, size=3.0, side="buy"),
    ]
    f = _write_parquet(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 3


def test_read_parquet_signed_size(tmp_path: Path):
    """signed_size cohérent avec le côté pour les trades lus depuis Parquet."""
    rows = [
        _canonical_row(ts=1_000, side="buy", size=1.0),
        _canonical_row(ts=2_000, side="sell", size=1.0),
    ]
    f = _write_parquet(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert trades[0].signed_size > 0
    assert trades[1].signed_size < 0


# ── Lecture CSV ───────────────────────────────────────────────────────────────

def test_read_csv_single_trade(tmp_path: Path):
    """Un fichier CSV avec un trade canonique → un Trade normalisé."""
    rows = [_canonical_row(ts=1_700_000_001_000, price=31_000.0, size=1.5, side="sell")]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    t = trades[0]
    assert t.ts == 1_700_000_001_000
    assert t.price == 31_000.0
    assert t.size == 1.5
    assert t.side is Side.SELL


def test_read_csv_multiple_trades(tmp_path: Path):
    rows = [
        _canonical_row(ts=1_000, price=10.0),
        _canonical_row(ts=2_000, price=20.0, side="sell"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 2


def test_read_csv_preserves_all_fields(tmp_path: Path):
    rows = [_canonical_row(ts=9_999_000, price=42_000.5, size=2.123, side="sell")]
    f = _write_csv(tmp_path, rows)
    t = list(FileReplaySource(f).trades())[0]
    assert t.ts == 9_999_000
    assert t.price == 42_000.5
    assert t.size == 2.123
    assert t.side is Side.SELL


# ── Forcer le format explicitement ────────────────────────────────────────────

def test_fmt_explicit_parquet(tmp_path: Path):
    """fmt='parquet' force la lecture Parquet même si l'extension diffère."""
    rows = [_canonical_row()]
    # Écrit le fichier Parquet avec une extension non standard.
    import pyarrow.parquet as pq
    import pyarrow as pa
    df = _df(rows)
    file = tmp_path / "trades.dat"
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), file)
    trades = list(FileReplaySource(file, fmt="parquet").trades())
    assert len(trades) == 1


def test_fmt_explicit_csv(tmp_path: Path):
    """fmt='csv' force la lecture CSV même si l'extension diffère."""
    file = tmp_path / "trades.dat"
    _df([_canonical_row()]).to_csv(file, index=False)
    trades = list(FileReplaySource(file, fmt="csv").trades())
    assert len(trades) == 1


# ── Mapping de colonnes ───────────────────────────────────────────────────────

def test_column_map_basic(tmp_path: Path):
    """Un mapping custom permet de lire des fichiers dont les colonnes diffèrent."""
    rows = [{"time_ms": 1_000, "px": 10.0, "qty": 0.5, "direction": "buy"}]
    f = _write_csv(tmp_path, rows)
    cmap = {"time_ms": "ts", "px": "price", "qty": "size", "direction": "side"}
    trades = list(FileReplaySource(f, column_map=cmap).trades())
    assert len(trades) == 1
    t = trades[0]
    assert t.ts == 1_000
    assert t.price == 10.0
    assert t.size == 0.5
    assert t.side is Side.BUY


def test_column_map_partial(tmp_path: Path):
    """Un mapping partiel : seules les colonnes mappées sont renommées.

    Ici 'qty' → 'size', les autres colonnes gardent les noms canoniques.
    """
    rows = [{"ts": 1_000, "price": 10.0, "qty": 0.5, "side": "sell"}]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f, column_map={"qty": "size"}).trades())
    assert len(trades) == 1
    assert trades[0].size == 0.5
    assert trades[0].side is Side.SELL


def test_column_map_parquet(tmp_path: Path):
    """Le mapping fonctionne aussi sur des fichiers Parquet."""
    rows = [{"timestamp": 2_000, "price": 20.0, "amount": 1.0, "side": "buy"}]
    file = tmp_path / "trades.parquet"
    _df(rows).to_parquet(file, index=False)
    trades = list(
        FileReplaySource(file, column_map={"timestamp": "ts", "amount": "size"}).trades()
    )
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_column_map_unknown_source_column_ignored(tmp_path: Path):
    """Une entrée du mapping dont la source n'existe pas dans le fichier est ignorée
    silencieusement (pas d'erreur, les colonnes existantes sont quand même traitées).
    """
    rows = [_canonical_row(ts=5_000)]
    f = _write_csv(tmp_path, rows)
    # 'inexistant' n'est pas dans le fichier → mapping ignoré, le reste est normal.
    trades = list(FileReplaySource(f, column_map={"inexistant": "ts"}).trades())
    assert len(trades) == 1
    assert trades[0].ts == 5_000


# ── Tri chronologique ─────────────────────────────────────────────────────────

def test_trades_sorted_by_ts_ascending_csv(tmp_path: Path):
    """Le tri ts croissant est appliqué même si le fichier est désordonné."""
    rows = [
        _canonical_row(ts=3_000, price=3.0),
        _canonical_row(ts=1_000, price=1.0),
        _canonical_row(ts=2_000, price=2.0),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    ts_list = [t.ts for t in trades]
    assert ts_list == sorted(ts_list), f"ts non croissants : {ts_list}"


def test_trades_sorted_by_ts_ascending_parquet(tmp_path: Path):
    """Idem en Parquet."""
    rows = [
        _canonical_row(ts=3_000, price=3.0),
        _canonical_row(ts=1_000, price=1.0),
        _canonical_row(ts=2_000, price=2.0),
    ]
    f = _write_parquet(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    ts_list = [t.ts for t in trades]
    assert ts_list == sorted(ts_list)


def test_already_sorted_content_unchanged(tmp_path: Path):
    """Si le fichier est déjà trié, le contenu n'est pas altéré."""
    rows = [
        _canonical_row(ts=1_000, price=1.0),
        _canonical_row(ts=2_000, price=2.0),
        _canonical_row(ts=3_000, price=3.0),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert [t.price for t in trades] == [1.0, 2.0, 3.0]


# ── Déduplication par id natif (C1) ──────────────────────────────────────────

def test_dedup_identical_rows_by_id_csv(tmp_path: Path):
    """Deux lignes CSV avec le même id → un seul Trade (dédup par id natif)."""
    rows = [
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy", trade_id="abc"),
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy", trade_id="abc"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1


def test_dedup_identical_rows_by_id_parquet(tmp_path: Path):
    """Deux lignes Parquet avec le même id → un seul Trade."""
    rows = [
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy", trade_id="xyz"),
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy", trade_id="xyz"),
    ]
    f = _write_parquet(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1


def test_dedup_distinct_ids_both_kept(tmp_path: Path):
    """T1 — Deux trades avec des ids distincts mais même quadruplet sont TOUS DEUX
    conservés — c'est le bug C1 corrigé : la dédup sur quadruplet les aurait détruits.
    """
    rows = [
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy", trade_id="id-001"),
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy", trade_id="id-002"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 2, (
        "Deux trades avec des ids distincts mais même quadruplet doivent être conservés"
    )


def test_dedup_pagination_scenario_file(tmp_path: Path):
    """T1 — Scénario pagination fichier : entrée désordonnée où deux occurrences
    du MÊME id sont séparées par d'autres trades puis rapprochées par le tri.

    Entrée (ordre fichier) : B, A, B (B est le doublon, séparé par A).
    Après tri par ts : A (ts=1000) < B (ts=2000) < B (ts=2000, doublon).
    Après dédup par id : A, B (le deuxième B est éliminé).
    """
    rows = [
        _canonical_row(ts=2_000, price=20.0, size=1.0, side="sell", trade_id="trade-B"),
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy",  trade_id="trade-A"),
        _canonical_row(ts=2_000, price=20.0, size=1.0, side="sell", trade_id="trade-B"),  # doublon
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 2
    assert trades[0].ts == 1_000
    assert trades[1].ts == 2_000


def test_dedup_keeps_distinct_trades(tmp_path: Path):
    """Des trades distincts (ids différents, quadruplets différents) ne sont pas dédupliqués."""
    rows = [
        _canonical_row(ts=1_000, price=1.0, size=0.1, side="buy",  trade_id="t1"),
        _canonical_row(ts=1_000, price=1.0, size=0.2, side="buy",  trade_id="t2"),  # size différente
        _canonical_row(ts=2_000, price=2.0, size=0.1, side="sell", trade_id="t3"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 3


def test_dedup_after_sort_by_id(tmp_path: Path):
    """La dédup par id est appliquée après le tri : le doublon est détecté."""
    rows = [
        _canonical_row(ts=2_000, price=1.0, size=0.1, side="buy", trade_id="dup"),
        _canonical_row(ts=1_000, price=1.0, size=0.1, side="buy", trade_id="uniq"),
        _canonical_row(ts=2_000, price=1.0, size=0.1, side="buy", trade_id="dup"),   # doublon
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 2
    assert trades[0].ts == 1_000
    assert trades[1].ts == 2_000


def test_no_dedup_without_id_logs_warning(tmp_path: Path, caplog):
    """Sans colonne id/trade_id, la dédup est désactivée et un warning est loggé."""
    import logging
    rows = [
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy"),   # sans id
        _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy"),   # même quadruplet
    ]
    f = _write_csv(tmp_path, rows)
    with caplog.at_level(logging.WARNING, logger="ninja_cat.adapters.file_replay"):
        trades = list(FileReplaySource(f).trades())
    # Les deux trades sont conservés (pas de dédup destructrice).
    assert len(trades) == 2
    assert any("déduplication désactivée" in r.message for r in caplog.records)


def test_dedup_trade_id_column(tmp_path: Path):
    """La colonne 'trade_id' est acceptée comme alternative à 'id'."""
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": "buy",  "trade_id": "tx-1"},
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": "buy",  "trade_id": "tx-1"},  # doublon
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell", "trade_id": "tx-2"},
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 2


# ── Précision des id entiers upcastés en float par pandas ──────────────────────
# Quand une colonne d'id numérique contient une valeur manquante, pandas upcaste
# TOUTE la colonne en float64. L'id entier 1001 devient 1001.0 ; un str() naïf
# donnerait "1001.0" (ou "1.2e+16"), ce qui casserait la parité de dédup vs le
# même id lu en entier ailleurs. _format_native_id() reconvertit le float entier.

def test_integer_id_upcast_to_float_is_formatted_without_decimal(tmp_path: Path):
    """Un id entier dont la colonne est upcastée en float64 (NaN présent) produit
    un id natif SANS suffixe '.0' — sinon il ne matcherait pas le même id en int.
    """
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": "buy",  "id": 1001},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},  # id manquant → NaN → upcast
    ]
    f = _write_csv(tmp_path, rows)

    # Garde : la colonne d'id est bien upcastée en float par pandas (sinon le
    # test ne prouverait rien).
    df = pd.read_csv(f)
    assert df["id"].dtype == float

    pairs = list(FileReplaySource(f)._normalise(df))
    ids = [trade_id for trade_id, _ in pairs]
    assert "1001" in ids, f"id entier mal formaté : {ids}"
    assert "1001.0" not in ids
    assert None in ids  # la ligne sans id reste non identifiée (pas de dédup)


def test_large_integer_id_below_2pow53_kept_exact_parquet(tmp_path: Path):
    """Un grand id entier <= 2**53-1 reste EXACT malgré l'upcast float64, en
    Parquet (schéma typé, pas de parseur de chaîne). Seul le formatage était à
    corriger : la valeur tient exactement dans un float64.

    NB : en CSV ce même id serait altéré par le parseur de flottants par défaut
    de pandas (cf. docstring de _format_native_id) — c'est pourquoi ce test cible
    Parquet. La mitigation CSV pour les très grands ids = colonne texte.
    """
    big_id = 9_007_199_254_740_991  # 2**53 - 1, dernier entier exact en float64
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": "buy",  "id": big_id},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},  # NaN → upcast float
    ]
    f = _write_parquet(tmp_path, rows)
    df = pd.read_parquet(f)
    assert df["id"].dtype == float  # garde : bien upcasté (NaN présent)

    pairs = list(FileReplaySource(f)._normalise(df))
    ids = [trade_id for trade_id, _ in pairs]
    assert str(big_id) in ids, f"grand id altéré : {ids}"


def test_dedup_integer_ids_with_float_upcast(tmp_path: Path):
    """Dédup de bout en bout : deux trades de même id entier sont dédupliqués
    même quand la colonne est upcastée en float (NaN sur une autre ligne).
    """
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": "buy",  "id": 1001},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},               # NaN → upcast
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": "buy",  "id": 1001},   # doublon de 1001
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    # 1001 dédupliqué (2 → 1) + la ligne sans id conservée = 2 trades.
    assert len(trades) == 2


# ── Side insensible à la casse (C5) ──────────────────────────────────────────

def test_side_uppercase_buy(tmp_path: Path):
    """'BUY' (majuscules) → Side.BUY."""
    f = _write_csv(tmp_path, [_canonical_row(side="BUY")])
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].side is Side.BUY


def test_side_uppercase_sell(tmp_path: Path):
    """'SELL' (majuscules) → Side.SELL."""
    f = _write_csv(tmp_path, [_canonical_row(side="SELL")])
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].side is Side.SELL


def test_side_mixedcase(tmp_path: Path):
    """'Buy' (mixte) → Side.BUY."""
    f = _write_csv(tmp_path, [_canonical_row(side="Buy")])
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].side is Side.BUY


def test_side_mixedcase_sell(tmp_path: Path):
    """'Sell' (mixte) → Side.SELL."""
    f = _write_csv(tmp_path, [_canonical_row(side="Sell")])
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].side is Side.SELL


# ── Monotonie (T2) ────────────────────────────────────────────────────────────

def test_monotonicity_disordered_with_ties(tmp_path: Path):
    """T2 — invariant monotonie sur >=5 trades vraiment désordonnés dont deux ex-aequo
    (même ts). Après tri : all(a.ts <= b.ts) ; ordre stable des ex-aequo préservé.
    """
    rows = [
        _canonical_row(ts=5_000, price=5.0, size=1.0, side="sell", trade_id="t5"),
        _canonical_row(ts=2_000, price=2.0, size=1.0, side="buy",  trade_id="t2a"),
        _canonical_row(ts=1_000, price=1.0, size=1.0, side="buy",  trade_id="t1"),
        _canonical_row(ts=2_000, price=2.1, size=1.0, side="buy",  trade_id="t2b"),  # ex-aequo
        _canonical_row(ts=3_000, price=3.0, size=1.0, side="sell", trade_id="t3"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 5
    ts_list = [t.ts for t in trades]
    assert all(a <= b for a, b in zip(ts_list, ts_list[1:])), f"ts non croissants : {ts_list}"
    # Les deux trades ts=2_000 sont présents (ids distincts → conservés).
    ties = [t for t in trades if t.ts == 2_000]
    assert len(ties) == 2


# ── Gardes de finitude, types, price/size <= 0 (T3/C2/C4) ───────────────────

def test_side_numeric_ignored(tmp_path: Path):
    """T3 — side numérique (int 1) : rejeté car ce n'est pas une str."""
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": 1},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_side_empty_string_ignored(tmp_path: Path):
    """T3 — side '' : non reconnu dans le mapping → ignoré."""
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": ""},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_price_non_numeric_ignored(tmp_path: Path):
    """T3 — price non numérique ('abc') : ignoré (déclenche la branche except)."""
    rows = [
        {"ts": 1_000, "price": "abc", "size": 0.5, "side": "buy"},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_size_non_numeric_ignored(tmp_path: Path):
    """T3 — size non numérique ('abc') : ignoré."""
    rows = [
        {"ts": 1_000, "price": 10.0, "size": "abc", "side": "buy"},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_ts_inf_ignored(tmp_path: Path):
    """T3 — ts = inf : rejeté par garde isfinite, trades() ne lève jamais."""
    df = pd.DataFrame([
        {"ts": float("inf"), "price": 10.0, "size": 0.5, "side": "buy"},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_ts_nan_ignored(tmp_path: Path):
    """T3 — ts = NaN : rejeté par garde isfinite."""
    df = pd.DataFrame([
        {"ts": float("nan"), "price": 10.0, "size": 0.5, "side": "buy"},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_price_inf_ignored(tmp_path: Path):
    """T3 — price = inf : rejeté par garde isfinite."""
    df = pd.DataFrame([
        {"ts": 1_000, "price": float("inf"), "size": 0.5, "side": "buy"},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_price_nan_ignored(tmp_path: Path):
    """T3 — price = NaN : rejeté par garde isfinite."""
    df = pd.DataFrame([
        {"ts": 1_000, "price": float("nan"), "size": 0.5, "side": "buy"},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_size_inf_ignored(tmp_path: Path):
    """T3 — size = inf : rejeté par garde isfinite."""
    df = pd.DataFrame([
        {"ts": 1_000, "price": 10.0, "size": float("inf"), "side": "buy"},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_size_nan_ignored(tmp_path: Path):
    """T3 — size = NaN : rejeté par garde isfinite."""
    df = pd.DataFrame([
        {"ts": 1_000, "price": 10.0, "size": float("nan"), "side": "buy"},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_price_zero_ignored(tmp_path: Path):
    """C4 — price == 0 : rejeté (défaut qualité donnée)."""
    rows = [
        {"ts": 1_000, "price": 0.0, "size": 1.0, "side": "buy"},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_price_negative_ignored(tmp_path: Path):
    """C4 — price < 0 : rejeté."""
    rows = [
        {"ts": 1_000, "price": -1.0, "size": 1.0, "side": "buy"},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_size_zero_ignored(tmp_path: Path):
    """C4 — size == 0 : rejeté (défaut qualité donnée)."""
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.0, "side": "buy"},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_size_negative_ignored(tmp_path: Path):
    """C4 — size < 0 : rejeté."""
    rows = [
        {"ts": 1_000, "price": 10.0, "size": -1.0, "side": "buy"},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_trades_never_raises_on_bad_data(tmp_path: Path):
    """T3 — trades() ne lève jamais, même avec un mélange de ts/price/size = inf et NaN."""
    df = pd.DataFrame([
        {"ts": float("inf"), "price": 10.0,          "size": 1.0,          "side": "buy"},
        {"ts": 1_000,        "price": float("nan"),  "size": 1.0,          "side": "buy"},
        {"ts": 1_000,        "price": 10.0,          "size": float("inf"), "side": "buy"},
        {"ts": float("nan"), "price": float("nan"),  "size": float("nan"), "side": "sell"},
        {"ts": 2_000,        "price": 20.0,          "size": 1.0,          "side": "sell"},  # valide
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    try:
        result = list(FileReplaySource(f).trades())
    except Exception as exc:
        pytest.fail(f"trades() a levé une exception inattendue : {exc!r}")
    assert len(result) == 1
    assert result[0].ts == 2_000


# ── Lignes malformées ignorées silencieusement ────────────────────────────────

def test_unknown_side_ignored(tmp_path: Path):
    """Un side non reconnu ('maker', 'taker', ...) est ignoré sans exception."""
    rows = [
        _canonical_row(ts=1_000, side="taker"),
        _canonical_row(ts=2_000, side="buy"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_none_side_ignored(tmp_path: Path):
    """Une ligne avec side=None est ignorée."""
    rows = [
        {"ts": 1_000, "price": 10.0, "size": 0.5, "side": None},
        _canonical_row(ts=2_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_missing_ts_value_ignored(tmp_path: Path):
    """Une ligne avec ts manquant (NaN dans CSV) est ignorée."""
    df = pd.DataFrame([
        {"ts": float("nan"), "price": 10.0, "size": 0.5, "side": "buy"},
        {"ts": 2_000, "price": 20.0, "size": 1.0, "side": "sell"},
    ])
    f = tmp_path / "trades.csv"
    df.to_csv(f, index=False)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 2_000


def test_zero_ts_ignored(tmp_path: Path):
    """ts=0 est ignoré (invariant : ts > 0)."""
    rows = [
        _canonical_row(ts=0),
        _canonical_row(ts=1_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 1_000


def test_negative_ts_ignored(tmp_path: Path):
    """ts négatif est ignoré."""
    rows = [
        _canonical_row(ts=-1),
        _canonical_row(ts=1_000),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1
    assert trades[0].ts == 1_000


def test_mixed_valid_and_malformed(tmp_path: Path):
    """Seules les lignes valides sont normalisées ; les malformées sont ignorées."""
    rows = [
        _canonical_row(ts=1_000, price=10.0, size=1.0, side="buy"),
        _canonical_row(ts=2_000, price=20.0, size=2.0, side="unknown"),  # side inconnu
        _canonical_row(ts=3_000, price=30.0, size=3.0, side="sell"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 2
    assert trades[0].ts == 1_000
    assert trades[1].ts == 3_000


# ── Dégradation gracieuse ─────────────────────────────────────────────────────

def test_graceful_file_not_found():
    """Fichier absent → itérable vide, sans exception."""
    src = FileReplaySource("/chemin/inexistant/trades.parquet")
    assert list(src.trades()) == []


def test_graceful_file_not_found_csv():
    """Fichier CSV absent → itérable vide, sans exception."""
    src = FileReplaySource("/chemin/inexistant/trades.csv")
    assert list(src.trades()) == []


def test_graceful_unknown_extension(tmp_path: Path):
    """Extension non reconnue → itérable vide, sans exception."""
    file = tmp_path / "trades.xyz"
    file.write_text("ts,price,size,side\n1000,10.0,0.5,buy")
    src = FileReplaySource(file)
    assert list(src.trades()) == []


def test_graceful_unsupported_fmt():
    """fmt non supporté → itérable vide, sans exception."""
    src = FileReplaySource("/quelconque.parquet", fmt="json")
    assert list(src.trades()) == []


def test_graceful_missing_canonical_columns(tmp_path: Path):
    """Fichier sans les colonnes canoniques → itérable vide, sans exception."""
    rows = [{"a": 1, "b": 2}]  # colonnes non canoniques
    f = _write_csv(tmp_path, rows)
    assert list(FileReplaySource(f).trades()) == []


def test_graceful_partial_missing_columns(tmp_path: Path):
    """Fichier avec seulement certaines colonnes canoniques → itérable vide."""
    rows = [{"ts": 1_000, "price": 10.0}]  # manque 'size' et 'side'
    f = _write_csv(tmp_path, rows)
    assert list(FileReplaySource(f).trades()) == []


def test_graceful_empty_file_parquet(tmp_path: Path):
    """Fichier Parquet avec zéro ligne → itérable vide."""
    file = tmp_path / "empty.parquet"
    _df([]).to_parquet(file, index=False)
    assert list(FileReplaySource(file).trades()) == []


def test_graceful_empty_csv(tmp_path: Path):
    """Fichier CSV avec uniquement l'entête → itérable vide."""
    file = tmp_path / "empty.csv"
    file.write_text("ts,price,size,side\n")
    assert list(FileReplaySource(file).trades()) == []


def test_graceful_corrupted_parquet(tmp_path: Path):
    """Fichier Parquet corrompu (contenu non-Parquet) → itérable vide, sans exception."""
    file = tmp_path / "bad.parquet"
    file.write_bytes(b"contenu_arbitraire_non_parquet")
    assert list(FileReplaySource(file).trades()) == []


def test_graceful_multiple_calls_independent(tmp_path: Path):
    """Chaque appel à trades() est indépendant et ne partage pas d'état."""
    f = _write_csv(tmp_path, [_canonical_row(ts=1_000)])
    src = FileReplaySource(f)
    first = list(src.trades())
    second = list(src.trades())
    assert first == second
    assert len(first) == 1


# ── Parité replay ─────────────────────────────────────────────────────────────

def test_replay_parity_parquet_csv_same_content(tmp_path: Path):
    """Parité : le même contenu lu depuis Parquet ou CSV produit les mêmes Trade."""
    rows = [
        _canonical_row(ts=1_000, price=10.0, size=1.0, side="buy"),
        _canonical_row(ts=2_000, price=20.0, size=2.0, side="sell"),
    ]
    parquet_file = _write_parquet(tmp_path, rows)
    csv_file = _write_csv(tmp_path, rows)

    trades_parquet = list(FileReplaySource(parquet_file).trades())
    trades_csv = list(FileReplaySource(csv_file).trades())

    assert trades_parquet == trades_csv
