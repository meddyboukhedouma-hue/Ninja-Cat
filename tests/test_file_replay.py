"""Tests de l'adapter FileReplaySource — aucun appel réseau.

Tous les fichiers sont écrits dans tmp_path (pytest). On vérifie :
- Lecture Parquet et CSV.
- Mapping de colonnes custom.
- Tri chronologique (ts croissant).
- Déduplication sur (ts, price, size, side).
- Side insensible à la casse.
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
) -> dict:
    """Retourne un dict avec les colonnes canoniques."""
    return {"ts": ts, "price": price, "size": size, "side": side}


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


# ── Déduplication ─────────────────────────────────────────────────────────────

def test_dedup_identical_rows_csv(tmp_path: Path):
    """Deux lignes CSV identiques → un seul Trade."""
    row = _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy")
    f = _write_csv(tmp_path, [row, row])
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1


def test_dedup_identical_rows_parquet(tmp_path: Path):
    """Deux lignes Parquet identiques → un seul Trade."""
    row = _canonical_row(ts=1_000, price=10.0, size=0.5, side="buy")
    f = _write_parquet(tmp_path, [row, row])
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 1


def test_dedup_keeps_distinct_trades(tmp_path: Path):
    """Des trades distincts ne sont pas dédupliqués."""
    rows = [
        _canonical_row(ts=1_000, price=1.0, size=0.1, side="buy"),
        _canonical_row(ts=1_000, price=1.0, size=0.2, side="buy"),   # size différente
        _canonical_row(ts=2_000, price=2.0, size=0.1, side="sell"),
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    assert len(trades) == 3


def test_dedup_after_sort(tmp_path: Path):
    """Le dedup est appliqué après le tri ; le premier trade de chaque clé est gardé."""
    rows = [
        _canonical_row(ts=2_000, price=1.0, size=0.1, side="buy"),
        _canonical_row(ts=1_000, price=1.0, size=0.1, side="buy"),
        _canonical_row(ts=2_000, price=1.0, size=0.1, side="buy"),  # doublon du premier
    ]
    f = _write_csv(tmp_path, rows)
    trades = list(FileReplaySource(f).trades())
    # ts=1_000 et ts=2_000 sont des clés distinctes → 2 trades.
    assert len(trades) == 2
    assert trades[0].ts == 1_000
    assert trades[1].ts == 2_000


# ── Side insensible à la casse ────────────────────────────────────────────────

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
