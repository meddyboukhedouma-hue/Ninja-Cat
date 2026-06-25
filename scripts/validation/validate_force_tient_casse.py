"""Validation statistique — CLAIM canon « force_courante vs force_zone -> tient/casse ».

================================================================================
HYPOTHESE TESTEE (claim doctrine Garry/G-ON, verbatim-sourcee)
================================================================================
Quand le prix REVIENT tester une zone d'Order Block precedemment detectee :
  - force_courante <  force_zone  -> la zone TIENT  (rebond/reaction)
  - force_courante >= force_zone  -> la zone CASSE.
Source : OB_DETECTION_SPEC.md §3.2 (l.235) ; force-energie.md axiomes
`zone_tient` (l.100) / `zone_casse` (l.115), immutable ; transcript
WO1gp3sk5U0 @ 00:26:00 et @ 00:26:59 (verifies au transcript brut par
doctrine-vault-operator, 2026-06-19).

QUESTION : le signe de (force_courante - force_zone) predit-il l'issue MIEUX
que le taux de base ?

================================================================================
DEFINITION DE LA FORCE  (CADRAGE DOCTRINAL — vault-verifie)
================================================================================
*** POINT CAPITAL ***  force_zone et force_courante sont des PALIERS DE TF
(index 0..11 dans la cascade demi-paliers M1=0 ... W1=11), PAS des grandeurs ATR.
La comparaison canon est PALIER vs PALIER (M15 < H1, D1 >= H4), pas un nombre ATR.
  - force-energie.md l.51-54 : force_zone:int range [0,11].
  - force-energie.md l.45-49 : force_courante:int range [0,11].
  - OB_DETECTION_SPEC §3.2 l.234-236.
La consigne de mission « force_courante ~= min(s.size_atr) » est donc CORRIGEE
au canon : on compare le PALIER TF de force, pas l'ATR. (Caveat reporte au rapport.)

Le moteur `cartographie.py` expose ce palier sous deux formes (labels TF) :
  - SequenceActive.force_finale_tf  : palier APRES degradations (canon strict)
  - SequenceActive.force_cascade_tf : palier BRUT (tf + 2 cassages, sans degradations)
On teste les DEUX (force finale = canon ; force brute = robustesse).

force_zone     = palier de la sequence active qui a CREE la zone OB (snapshot a la formation).
force_courante = palier de la sequence active ARRIVANT a la zone (snapshot au 1er retest).

================================================================================
LABEL D'ISSUE  (impose par la mission, DOCTRINE-FIDELE)
================================================================================
A la penetration la plus profonde du 1er test, mesurer le « reste » (epaisseur
residuelle non consommee, en x ATR233 du TF de la zone) :
  - zone DEMANDE (bull) : reste = (min_low_test  - bas_zone)  / ATR233
  - zone OFFRE   (bear) : reste = (haut_zone - max_high_test)  / ATR233
  - TIENT  <=> reste >= 0.45 ; CASSE <=> reste < 0.45  (ou cloture au-dela du bord lointain).
Source : OB_DETECTION_SPEC §T1-bis(b), xFnFjopAzz8 @ 01:53:18-41.
Contre-test R10 (label alternatif) : CASSE <=> une bougie CLOTURE au-dela du
bord lointain pendant le test ; sinon TIENT. (§T1-bis(c), R10.)

================================================================================
PROTOCOLE ANTI-LOOK-AHEAD (strict)
================================================================================
1. Le moteur opere sur le DERNIER etat du df (iloc[-1], cassures[-1], .tail(50)).
   On TRONQUE chaque df a la barre courante T (time <= T) avant tout appel
   -> aucune info de t+k n'entre dans la detection. ATR-RMA (ewm) et le ZigZag
   ATR-based sont strictement causaux (n'utilisent que le passe).
2. Detection des zones + force_zone : sur df tronques a la barre de FORMATION.
3. force_courante : sur df tronques a la barre du TEST INCLUS (pas apres).
4. Issue : label « reste » mesure sur les barres APRES l'entree dans la zone.
5. 1ere re-entree = le test pertinent (« le meilleur test = le premier »).
   Purge/embargo : une fois une zone testee, elle ne reproduit plus d'evenement.

CAVEAT MOTEUR (signale par la mission) : cartographie.py porte le modele de force
mais INCOMPLET (4 degradations /~9 ; PAS le contre-swing ni la liquidite-au-dessus).
On teste la claim GENERIQUE (signe de l'ecart de palier), pas un cablage particulier.

================================================================================
REPRODUCTIBILITE
================================================================================
Seed fixe, parametres en tete, donnees versionnees (JSON local BTCUSDT Binance).
Sortie : CSV des evenements + JSON des metriques + tables imprimees.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# PARAMETRES (en tete, logges) ----------------------------------------------
# ---------------------------------------------------------------------------
SEED = 12345

REPO = r"C:\Users\DyBoo\Desktop\Nouveau dossier\NinjaCat"
ENGINE_DIR = os.path.join(REPO, "ressources", "scripts")
DATA_DIR = os.path.join(REPO, "ressources", "data-OHLCV")
OUT_DIR = os.path.join(REPO, "scripts", "validation", "out")

# Fichiers OHLCV (BTCUSDT Binance). Multi-TF pour la cascade de force.
DATA_FILES = {
    "M15": "btcusdt_m15_175200.json",
    "H1":  "btcusdt_h1_30000.json",
    "H2":  "btcusdt_h2_30000.json",
    "H4":  "btcusdt_h4_15000.json",
    "H8":  "btcusdt_h8_9550.json",
    "D1":  "btcusdt_d1_2500.json",
    "W1":  "btcusdt_w1_360.json",
}

# Fenetres glissantes passees au moteur (trailing). Assez longues pour ATR233
# chaud + 2 dernieres cassures/swings + OB-candle (cherche dans .tail(50) avant swing1).
WINDOW = {"M15": 1500, "H1": 1200, "H2": 1200, "H4": 1200, "H8": 1200, "D1": 1200, "W1": 360}

# TF de balayage : on avance l'index H4 (TF central de la fenetre d'execution
# H8/H4/H2/H1). A chaque pas on re-detecte la sequence active (donc la zone OB
# d'origine courante). Pas de balayage en barres H4.
SCAN_TF = "H4"
SCAN_STEP_H4 = 1          # 1 = chaque barre H4 ; augmenter pour aller plus vite

# Label « reste » canon
RESTE_SEUIL = 0.45        # seuil canon (FVG validity). Balaye 0.30..0.60 en robustesse.

# TF de mesure du test/penetration. "zone" = le TF propre de la zone (defaut, frame
# naturel du moteur) ; "M15" = mesure fine de la meche (robustesse). Le canon ne fixe
# PAS le TF d'observation de la mitigation (vault-verifie) -> on teste les deux.
MEASURE_TF = "zone"

# Fenetre du test = EVENEMENTIELLE, pas temporelle (cadrage doctrinal vault-verifie,
# doctrine-vault-operator 2026-06-19) : le canon ne donne AUCUNE duree chiffree du
# test. La "mort" est geometrique (une bougie CLOTURE au-dela du bord lointain) ;
# l'incursion se termine quand le prix REJETTE (ressort du cote proche) OU clot
# au-dela du bord lointain. On mesure le "reste" a la penetration la plus profonde
# de la PREMIERE incursion (« tu as pris une quantite, pas tout, puis repousse »,
# xFnFjopAzz8 @01:52-53). INCURSION_SAFETY_CAP = garde-fou anti-boucle (non doctrinal,
# tres large), PAS une fenetre de test : si atteint, l'incursion est tronquee et logguee.
INCURSION_SAFETY_CAP = 500

# Cascade demi-paliers (index de force) — copie locale du mapping canon
# (cartographie.TF_CASCADE_DEMI_PALIERS) pour convertir un label TF en index.
TF_IDX = {"M1": 0, "M3": 1, "M5": 2, "M8": 3, "M15": 4, "M30": 5,
          "H1": 6, "H2": 7, "H4": 8, "H8": 9, "D1": 10, "W1": 11}


def tf_label_to_idx(label: str) -> Optional[int]:
    """Convertit un label de force ('H4', 'D1', 'W1+2', ...) en index de palier."""
    if not label:
        return None
    if label in TF_IDX:
        return TF_IDX[label]
    if label.startswith("W1+"):
        try:
            return 11 + int(label[3:])
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# CHARGEMENT MOTEUR + DONNEES ------------------------------------------------
# ---------------------------------------------------------------------------
sys.path.insert(0, ENGINE_DIR)
import cartographie as C  # noqa: E402  (le moteur de force de reference, NON modifie)


def load_df(name: str) -> pd.DataFrame:
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as fh:
        d = json.load(fh)
    df = pd.DataFrame(d["bars"])
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    return df


def integrity_check(dfs: dict[str, pd.DataFrame]) -> None:
    """Garantit l'integrite : pas de trou anormal, pas de desordre temporel."""
    step = {"M15": 15, "H1": 60, "H2": 120, "H4": 240, "H8": 480, "D1": 1440, "W1": 10080}
    print("[integrity] verification des series :")
    for tf, df in dfs.items():
        dt = df["time"].diff().dropna().dt.total_seconds() / 60.0
        exp = step[tf]
        mono = bool((df["time"].diff().dropna() > pd.Timedelta(0)).all())
        gaps = int((dt > exp * 1.5).sum())
        print(f"   {tf:4s} n={len(df):6d}  {df['time'].iloc[0].date()}->{df['time'].iloc[-1].date()}"
              f"  mono={mono}  gaps>1.5x={gaps}  median_step_min={np.median(dt):.0f}")
        assert mono, f"{tf}: desordre temporel detecte"


def make_windows(dfs: dict[str, pd.DataFrame], t_cut: pd.Timestamp) -> dict[str, pd.DataFrame]:
    """Tronque chaque df a time <= t_cut, garde la fenetre trailing. ANTI-LOOK-AHEAD."""
    out = {}
    for tf, df in dfs.items():
        sub = df[df["time"] <= t_cut]
        if len(sub) == 0:
            continue
        out[tf] = sub.tail(WINDOW[tf]).reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# STRUCTURE D'EVENEMENT ------------------------------------------------------
# ---------------------------------------------------------------------------
@dataclass
class ZoneEvent:
    zone_id: str
    tf_zone: str
    direction: str            # haussier (demande) / baissier (offre)
    nature: str
    zone_low: float
    zone_high: float
    atr_zone: float           # ATR233 du TF de la zone, a la formation
    t_form: str               # barre de formation (snapshot force_zone)
    force_zone_finale_idx: Optional[int]
    force_zone_brute_idx: Optional[int]
    force_zone_finale_lbl: str
    force_zone_brute_lbl: str
    # rempli au test :
    t_test: str = ""
    force_cour_finale_idx: Optional[int] = None
    force_cour_brute_idx: Optional[int] = None
    force_cour_finale_lbl: str = ""
    force_cour_brute_lbl: str = ""
    reste_atr: Optional[float] = None
    cloture_au_dela: Optional[bool] = None
    incursion_bars: Optional[int] = None
    incursion_capped: Optional[bool] = None
    # labels d'issue
    issue_reste: str = ""     # TIENT / CASSE  (label reste 0.45)
    issue_r10: str = ""       # TIENT / CASSE  (label cloture bord lointain)


# ---------------------------------------------------------------------------
# DETECTION DES ZONES (balayage H4, anti-look-ahead) ------------------------
# ---------------------------------------------------------------------------
def zone_identity(seq) -> Optional[str]:
    ob = seq.ob_origine
    if ob is None:
        return None
    # identite stable d'une zone = (tf, candle_time, bornes arrondies)
    return f"{ob.tf}|{pd.Timestamp(ob.candle_time)}|{round(ob.zone_low,2)}|{round(ob.zone_high,2)}"


def scan_zones(dfs: dict[str, pd.DataFrame], t_start: pd.Timestamp,
               t_end: pd.Timestamp, step: int, verbose: bool) -> dict[str, ZoneEvent]:
    """Balaye l'historique au pas H4 ; capture chaque zone OB d'origine UNIQUE
    a sa premiere apparition, avec force_zone (snapshot a la formation)."""
    h4 = dfs["H4"]
    mask = (h4["time"] >= t_start) & (h4["time"] <= t_end)
    scan_times = h4.loc[mask, "time"].iloc[::step].tolist()
    zones: dict[str, ZoneEvent] = {}
    t0 = time.time()
    for k, t_cut in enumerate(scan_times):
        win = make_windows(dfs, t_cut)
        if "H4" not in win or len(win["H4"]) < 300:
            continue
        try:
            seq = C.detect_sequence_active(win)
        except Exception:
            continue
        if seq is None or seq.ob_origine is None:
            continue
        zid = zone_identity(seq)
        if zid is None or zid in zones:
            continue
        ob = seq.ob_origine
        # ATR233 du TF de la zone, a la formation (cause : df tronque)
        df_tf = win.get(ob.tf)
        if df_tf is None or len(df_tf) == 0:
            continue
        atr_s = C.compute_atr_rma(df_tf, C.ATR_PERIOD)
        atr_zone = float(atr_s.iloc[-1]) if len(atr_s) else float("nan")
        if not (atr_zone > 0):
            continue
        ff_lbl, fb_lbl = seq.force_finale_tf, seq.force_cascade_tf
        zones[zid] = ZoneEvent(
            zone_id=zid, tf_zone=ob.tf, direction=ob.direction.value, nature=ob.nature,
            zone_low=float(ob.zone_low), zone_high=float(ob.zone_high), atr_zone=atr_zone,
            t_form=str(t_cut),
            force_zone_finale_idx=tf_label_to_idx(ff_lbl),
            force_zone_brute_idx=tf_label_to_idx(fb_lbl),
            force_zone_finale_lbl=ff_lbl, force_zone_brute_lbl=fb_lbl,
        )
        if verbose and (k % 200 == 0):
            el = time.time() - t0
            print(f"  [scan] step {k}/{len(scan_times)} t={t_cut} zones={len(zones)} ({el:.0f}s)",
                  flush=True)
    print(f"[scan] termine : {len(zones)} zones uniques sur {len(scan_times)} pas "
          f"({time.time()-t0:.0f}s)")
    return zones


# ---------------------------------------------------------------------------
# 1er RETEST + LABEL D'ISSUE (sur M15, fin) ---------------------------------
# ---------------------------------------------------------------------------
def find_first_retest_and_label(ev: ZoneEvent, dfs: dict[str, pd.DataFrame]) -> bool:
    """Trouve la 1ere re-entree dans la zone APRES sa formation, mesure le label
    d'issue sur la PREMIERE INCURSION (fenetre evenementielle, pas temporelle).

    Incursion = a partir de la 1ere barre qui rentre dans [lo,hi], on avance
    bougie par bougie en suivant la penetration la plus profonde. L'incursion
    se TERMINE quand :
      (CASSE) une bougie CLOTURE au-dela du bord lointain        -> cloture_au_dela=True
      (FIN)   le prix RESSORT entierement du cote proche (rejet) -> on mesure le reste
    Le label de mesure se fait sur le TF passe (zone TF par defaut, M15 en robustesse).
    """
    meas_tf = MEASURE_TF if MEASURE_TF != "zone" else ev.tf_zone
    df = dfs.get(meas_tf)
    if df is None:
        return False
    t_form = pd.Timestamp(ev.t_form)
    fut = df[df["time"] > t_form].reset_index(drop=True)
    if len(fut) == 0:
        return False
    lo, hi = ev.zone_low, ev.zone_high
    inside = (fut["low"] <= hi) & (fut["high"] >= lo)
    idxs = np.where(inside.values)[0]
    if len(idxs) == 0:
        return False
    i0 = int(idxs[0])
    ev.t_test = str(fut["time"].iloc[i0])
    bull = (ev.direction == "haussier")     # demande (bull) : bord lointain = lo
    far = lo if bull else hi
    deepest = fut["low"].iloc[i0] if bull else fut["high"].iloc[i0]
    cloture_au_dela = False
    n_bars = 0
    capped = False
    for j in range(i0, min(i0 + INCURSION_SAFETY_CAP, len(fut))):
        row = fut.iloc[j]
        n_bars = j - i0 + 1
        # mise a jour de la penetration la plus profonde
        deepest = min(deepest, row["low"]) if bull else max(deepest, row["high"])
        # (CASSE) cloture au-dela du bord lointain
        if (bull and row["close"] < far) or ((not bull) and row["close"] > far):
            cloture_au_dela = True
            break
        # (FIN d'incursion) le prix ressort entierement du cote proche :
        # plus aucun contact avec la zone (range entierement hors [lo,hi]) APRES
        # etre entre. Pour bull : low > hi (repasse au-dessus). Pour bear : high < lo.
        if j > i0:
            out_near = (row["low"] > hi) if bull else (row["high"] < lo)
            if out_near:
                break
    else:
        capped = True
    if bull:
        ev.reste_atr = (float(deepest) - lo) / ev.atr_zone
    else:
        ev.reste_atr = (hi - float(deepest)) / ev.atr_zone
    ev.cloture_au_dela = bool(cloture_au_dela)
    ev.incursion_bars = int(n_bars)
    ev.incursion_capped = bool(capped)
    tient_reste = (ev.reste_atr >= RESTE_SEUIL) and (not ev.cloture_au_dela)
    ev.issue_reste = "TIENT" if tient_reste else "CASSE"
    ev.issue_r10 = "CASSE" if ev.cloture_au_dela else "TIENT"
    return True


def fill_force_courante(ev: ZoneEvent, dfs: dict[str, pd.DataFrame]) -> None:
    """force_courante = palier de la sequence active au moment du TEST (inclus).
    df tronques a t_test -> anti-look-ahead."""
    t_test = pd.Timestamp(ev.t_test)
    win = make_windows(dfs, t_test)
    if "H4" not in win:
        return
    try:
        seq = C.detect_sequence_active(win)
    except Exception:
        return
    if seq is None:
        return
    ev.force_cour_finale_lbl = seq.force_finale_tf
    ev.force_cour_brute_lbl = seq.force_cascade_tf
    ev.force_cour_finale_idx = tf_label_to_idx(seq.force_finale_tf)
    ev.force_cour_brute_idx = tf_label_to_idx(seq.force_cascade_tf)


# ---------------------------------------------------------------------------
# STATISTIQUES ---------------------------------------------------------------
# ---------------------------------------------------------------------------
def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den
    return (centre - half, centre + half)


def two_prop_z(k1, n1, k2, n2):
    """Test z bilateral de difference de proportions (TIENT|predit-tient vs TIENT|predit-casse)."""
    if n1 == 0 or n2 == 0:
        return (float("nan"), float("nan"))
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (float("nan"), float("nan"))
    z = (p1 - p2) / se
    # p-value bilaterale via fonction d'erreur
    pval = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return (z, pval)


def analyse(events: list[ZoneEvent], force_kind: str, label_kind: str,
            seuil: float = RESTE_SEUIL) -> dict:
    """force_kind in {finale, brute} ; label_kind in {reste, r10}.
    Predicteur canon : predit CASSE si (force_courante - force_zone) >= 0, sinon TIENT.
    """
    rows = []
    for ev in events:
        fz = ev.force_zone_finale_idx if force_kind == "finale" else ev.force_zone_brute_idx
        fc = ev.force_cour_finale_idx if force_kind == "finale" else ev.force_cour_brute_idx
        if fz is None or fc is None:
            continue
        if label_kind == "reste":
            if ev.reste_atr is None:
                continue
            tient = (ev.reste_atr >= seuil) and (not ev.cloture_au_dela)
            real = "TIENT" if tient else "CASSE"
        else:
            if ev.cloture_au_dela is None:
                continue
            real = "CASSE" if ev.cloture_au_dela else "TIENT"
        delta = fc - fz
        pred = "CASSE" if delta >= 0 else "TIENT"   # canon : >= -> casse ; < -> tient
        rows.append((delta, pred, real))
    n = len(rows)
    if n == 0:
        return {"n": 0}
    # contingence
    cells = {("TIENT", "TIENT"): 0, ("TIENT", "CASSE"): 0,
             ("CASSE", "TIENT"): 0, ("CASSE", "CASSE"): 0}
    for _, pred, real in rows:
        cells[(pred, real)] += 1
    n_pred_tient = cells[("TIENT", "TIENT")] + cells[("TIENT", "CASSE")]
    n_pred_casse = cells[("CASSE", "TIENT")] + cells[("CASSE", "CASSE")]
    n_real_tient = cells[("TIENT", "TIENT")] + cells[("CASSE", "TIENT")]
    base_rate_tient = n_real_tient / n
    hits = cells[("TIENT", "TIENT")] + cells[("CASSE", "CASSE")]
    hit_rate = hits / n
    # P(TIENT | predit tient) vs P(TIENT | predit casse)
    p_tient_given_predtient = (cells[("TIENT", "TIENT")] / n_pred_tient) if n_pred_tient else float("nan")
    p_tient_given_predcasse = (cells[("CASSE", "TIENT")] / n_pred_casse) if n_pred_casse else float("nan")
    z, pval = two_prop_z(cells[("TIENT", "TIENT")], n_pred_tient,
                         cells[("CASSE", "TIENT")], n_pred_casse)
    # lift = hit_rate vs accuracy de la regle triviale (toujours predire la classe majoritaire)
    trivial_acc = max(base_rate_tient, 1 - base_rate_tient)
    lift_vs_trivial = hit_rate - trivial_acc
    ci_pt = wilson_ci(cells[("TIENT", "TIENT")], n_pred_tient)
    ci_pc = wilson_ci(cells[("CASSE", "TIENT")], n_pred_casse)
    # effet dose-reponse : P(TIENT) par tranche de delta
    dose = {}
    for d_lo, d_hi, name in [(-99, -2, "delta<=-2"), (-1, -1, "delta=-1"),
                             (0, 0, "delta=0"), (1, 1, "delta=+1"), (2, 99, "delta>=+2")]:
        sub = [r for r in rows if d_lo <= r[0] <= d_hi]
        if sub:
            nt = sum(1 for r in sub if r[2] == "TIENT")
            dose[name] = {"n": len(sub), "p_tient": nt / len(sub)}
    return {
        "n": n, "cells": {f"{k[0]}->{k[1]}": v for k, v in cells.items()},
        "base_rate_tient": base_rate_tient, "hit_rate": hit_rate,
        "trivial_acc": trivial_acc, "lift_vs_trivial": lift_vs_trivial,
        "n_pred_tient": n_pred_tient, "n_pred_casse": n_pred_casse,
        "P(TIENT|pred=TIENT)": p_tient_given_predtient, "CI95_pred_tient": ci_pt,
        "P(TIENT|pred=CASSE)": p_tient_given_predcasse, "CI95_pred_casse": ci_pc,
        "z_diff": z, "pval_diff": pval, "dose_response": dose,
    }


def print_report(events: list[ZoneEvent]) -> dict:
    res = {}
    print("\n" + "=" * 78)
    print("RESULTATS — table de contingence predit{tient/casse} x reel{tient/casse}")
    print("=" * 78)
    for force_kind in ["finale", "brute"]:
        for label_kind in ["reste", "r10"]:
            key = f"force={force_kind} | label={label_kind}"
            a = analyse(events, force_kind, label_kind)
            res[key] = a
            print(f"\n--- {key} ---")
            if a.get("n", 0) == 0:
                print("   N=0 (pas d'evenements exploitables)")
                continue
            c = a["cells"]
            print(f"   N={a['n']}   taux de base TIENT={a['base_rate_tient']:.3f}")
            print(f"   contingence : "
                  f"PT->RT={c['TIENT->TIENT']}  PT->RC={c['TIENT->CASSE']}  "
                  f"PC->RT={c['CASSE->TIENT']}  PC->RC={c['CASSE->CASSE']}")
            print(f"   hit_rate={a['hit_rate']:.3f}  (trivial={a['trivial_acc']:.3f}, "
                  f"lift={a['lift_vs_trivial']:+.3f})")
            print(f"   P(TIENT|pred=TIENT)={a['P(TIENT|pred=TIENT)']:.3f} "
                  f"CI95={tuple(round(x,3) for x in a['CI95_pred_tient'])} (n={a['n_pred_tient']})")
            print(f"   P(TIENT|pred=CASSE)={a['P(TIENT|pred=CASSE)']:.3f} "
                  f"CI95={tuple(round(x,3) for x in a['CI95_pred_casse'])} (n={a['n_pred_casse']})")
            z, p = a["z_diff"], a["pval_diff"]
            print(f"   z(diff de prop)={z:.2f}  p={p:.4g}")
            print("   dose-reponse P(TIENT) par tranche de delta=force_cour-force_zone :")
            for name, d in a["dose_response"].items():
                print(f"      {name:11s} n={d['n']:4d}  P(TIENT)={d['p_tient']:.3f}")
    return res


def sensitivity_threshold(events: list[ZoneEvent]) -> dict:
    print("\n" + "=" * 78)
    print("ROBUSTESSE — sensibilite au seuil 'reste' (force finale, label reste)")
    print("=" * 78)
    out = {}
    for seuil in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
        a = analyse(events, "finale", "reste", seuil=seuil)
        if a.get("n", 0) == 0:
            continue
        out[f"{seuil:.2f}"] = {
            "base_rate_tient": a["base_rate_tient"], "hit_rate": a["hit_rate"],
            "lift": a["lift_vs_trivial"],
            "P(TIENT|predTIENT)": a["P(TIENT|pred=TIENT)"],
            "P(TIENT|predCASSE)": a["P(TIENT|pred=CASSE)"],
            "pval": a["pval_diff"],
        }
        print(f"   seuil={seuil:.2f}  base={a['base_rate_tient']:.3f}  hit={a['hit_rate']:.3f}  "
              f"lift={a['lift_vs_trivial']:+.3f}  "
              f"P(T|pT)={a['P(TIENT|pred=TIENT)']:.3f}  P(T|pC)={a['P(TIENT|pred=CASSE)']:.3f}  "
              f"p={a['pval_diff']:.3g}")
    return out


# ---------------------------------------------------------------------------
# MAIN -----------------------------------------------------------------------
# ---------------------------------------------------------------------------
def main():
    global MEASURE_TF
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=SCAN_STEP_H4, help="pas de balayage en barres H4")
    ap.add_argument("--start", type=str, default="2022-12-01", help="debut balayage (donnees H1 multi-TF denses)")
    ap.add_argument("--end", type=str, default="2026-04-25")
    ap.add_argument("--max-zones", type=int, default=0, help="0=illimite (debug)")
    ap.add_argument("--measure-tf", type=str, default=MEASURE_TF,
                    help="TF de mesure du test : 'zone' (defaut) ou 'M15' (robustesse)")
    ap.add_argument("--out", type=str, default=OUT_DIR, help="repertoire de sortie")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    MEASURE_TF = args.measure_tf
    out_dir = args.out

    np.random.seed(SEED)
    os.makedirs(out_dir, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    print("PARAMS:", {"seed": SEED, "scan_tf": SCAN_TF, "step": args.step,
                      "window": WINDOW, "reste_seuil": RESTE_SEUIL,
                      "incursion_safety_cap": INCURSION_SAFETY_CAP, "measure_tf": MEASURE_TF,
                      "start": args.start, "end": args.end})

    dfs = {tf: load_df(f) for tf, f in DATA_FILES.items()}
    integrity_check(dfs)

    t_start = pd.Timestamp(args.start)
    t_end = pd.Timestamp(args.end)
    zones = scan_zones(dfs, t_start, t_end, args.step, args.verbose)

    events = list(zones.values())
    if args.max_zones:
        events = events[: args.max_zones]

    # 1er retest + label, puis force_courante au test
    kept = []
    n_tested = 0
    for ev in events:
        if find_first_retest_and_label(ev, dfs):
            fill_force_courante(ev, dfs)
            n_tested += 1
        kept.append(ev)
    print(f"\n[events] zones={len(events)}  avec 1er retest={n_tested}")

    # garder seulement les evenements complets (force_zone, force_courante, label)
    complete = [ev for ev in kept if ev.t_test and ev.reste_atr is not None
                and ev.force_zone_finale_idx is not None and ev.force_cour_finale_idx is not None]
    print(f"[events] exploitables (force_zone+force_courante+label complets)={len(complete)}")

    # dump CSV
    df_ev = pd.DataFrame([asdict(e) for e in kept])
    csv_path = os.path.join(out_dir, "events.csv")
    df_ev.to_csv(csv_path, index=False)
    print(f"[out] {csv_path}")

    metrics = print_report(complete)
    sens = sensitivity_threshold(complete)

    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"params": {"seed": SEED, "step": args.step, "window": WINDOW,
                              "reste_seuil": RESTE_SEUIL, "measure_tf": MEASURE_TF,
                              "start": args.start, "end": args.end},
                   "n_zones": len(events), "n_tested": n_tested, "n_complete": len(complete),
                   "metrics": metrics, "sensitivity": sens}, fh, indent=2, default=str)
    print(f"[out] {os.path.join(out_dir, 'metrics.json')}")


if __name__ == "__main__":
    main()
