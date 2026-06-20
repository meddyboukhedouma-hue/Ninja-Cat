# Spec déterministe — Qualification ABA via la brique « 5 barres », branchée sur le pipeline de type d'OB

> Cible : détecteur Pine v6 `ressources/scripts_pin/OB_Detector_v2.13.txt` (fonction `f_OB`).
> Format : aligné sur `docs/specs/OB_DETECTION_SPEC.md` (même conventions §0, mêmes primitives §1).
> Auteur du livrable : spécification seulement. **Aucune valeur non fixée par le canon n'est tranchée ici.**
> Date : 2026-06-20.
>
> **Légende statut** (identique à la spec OB) :
> ✅ déterministe & sourcé · 🟦 décision/convention humaine assumée (hors vault) ·
> ⚠️ inférence (source muette, à confirmer humain) · 🟡 à valider visuellement ·
> 🔴 **TROU CANON — décision humaine requise** (le canon ne chiffre pas / ne tranche pas).

---

## §A — Résumé exécutif : CANON-SÛR vs DÉCISION HUMAINE

### Ce qui est CANON-SÛR (chiffré, sourcé, déterministe)
1. **Comptage 5 barres** : 5 bougies consécutives même sens ; **≤1 opposée isolée**, **jamais 2 opposées consécutives** ; **3 opposées consécutives disqualifient** (`5-barres.md` axiomes `cinq_barres_definition`, `cinq_barres_max_une_opposee_isolee`, `bougie-institutionnelle.md` `cinq_barres_3_consecutives_disqualifient`). `count = 5` et `opposite ≤ 1` sont des **paramètres canon `tunable: false`**.
2. **Fenêtre suggérée 7-8 bougies** (`5-barres.md` implications : « 5 + 1 opposée + tolérance bruit »).
3. **Accélération = 5-barres OU 3x** (≥ 3 ATR) (`bougie-3x.md` `bougie_3x_definition`, `5-barres.md` définition).
4. **Base ABA = 1 à 3 bougies, petit corps + longues mèches** (`aba.md` `aba_base_petit_corps_longue_meche`, `aba_base_bougies_max`). Au-delà de 3, ce n'est plus une base.
5. **Force ABA = TF+1** (jeu institutionnel un temps au-dessus) (`aba.md` `aba_force_tf_plus_1`).
6. **Désactivation ABA au re-tap = −1 force** (et non −2 du jeu normal), car intrinsèquement TF+1 (`force-energie.md` `desactivation_jeu_normal_perd_deux_fois_force`).
7. **Polarité positive** de l'accélération/5-barres (`5-barres.md` `cinq_barres_polarite_positive`).
8. **Base = mèches incluses** pour le tracé de la zone (concordance vault relevée dans `ob-spec-vs-vault-confrontation.md` ; déjà adopté §T4 de la spec OB).

### DÉCISIONS HUMAINES — fermées 2026-06-20 (détails §D/§E/§F/§I)
- **TC-1** ✅ **FERMÉ : `corps < upper_wick ET corps < lower_wick`** (β, scale-free, zéro paramètre inventé ; cohérent OB §T4). Pas de seuil ATR absolu.
- **TC-2** ✅ **FERMÉ : « un temps au-dessus » = +1 temps = +2 crans.** Force ABA = `min(tf0 + 2, 11)`, **SANS climb**. Établi par 5 exemples chiffrés (H4→D1, H1→H4, M30→H2 ×2) + calibration « 1 fois de force = 2 crans » (D1 perd 2 fois → H1) + loi de parité « pas de demi-temps ». Le « +1 cran » et la glose `aba.md` « demi-temps au-dessus » sont **RÉFUTÉS** (cf. §F.1). Triple-vérifié (transcript brut + 2 digs aveugles indépendants).
- **TC-3** ✅ **FERMÉ : gate = `typ == "micro"` + test mèches §E** (le seuil mèche EST TC-1).
- **TC-4** ✅ **FERMÉ : descente TF−0,5 via `request.security`** (archi canon-pure : l'ABA se cherche un demi-TF sous la 5-barres, `aba.md aba_affinage_demi_temps`). Cf. §I.2(b).
- **TC-5** 🔴 : **Critère « propre » (monte vite)** : le canon le qualifie mais ne chiffre ni le retracement intra-séquence ni la durée. **Non chiffré** — raffinement de QUALITÉ, pas condition d'existence (n'empêche pas le câblage).
- **TC-6** ⚠️ : **Asymétrie `accél_in`/`accél_out`** (5-barres d'un côté, 3x de l'autre). Canon muet → asymétrie autorisée par défaut (§E.4).

> **Les 4 décisions bloquantes (TC-1/2/3/4) sont fermées.** La règle ABA est désormais exécutable. TC-5 (qualité) et TC-6 (cas mixte) sont des raffinements non bloquants.

### Corollaire — DÉSACTIVATION (correction du code existant, cf. §F.2)
« 1 fois de force = 1 temps = 2 crans » ⇒ jeu **normal** « perd deux fois » = **−4 crans** ; **ABA** « perd une fois » = **−2 crans**. Le détecteur applique aujourd'hui `f0 − 2` à TOUS (= le taux institutionnel) → **OB normaux sous-pénalisés**. Correction requise : `desact = is_inst ? f0−2 : f0−4` (pas encore appliquée au code).

---

## §B — Conventions et primitives réutilisées (ne rien réinventer)

### B.0 — Conventions par bougie `i` (héritées OB §0)
`O,H,L,C` ; `body = abs(C−O)` ; `range = H−L` ; `upper_wick = H − max(O,C)` ; `lower_wick = min(O,C) − L` ; bull si `C>O`, bear si `C<O`.

### B.1 — Primitives héritées de la spec OB (§1) et du détecteur
| Primitive | Source / variable détecteur | Réutilisation ABA |
|---|---|---|
| `ATR233 = SMA(TR, 233)` | `atr233` (L63) | unité de toutes les comparaisons |
| Pivots tracé | `ph`/`pl` (L64-65, `len=5`) | délimitation des swings |
| Micro-pivots | `mph`/`mpl` (L66-67, `microLen=2`) | bougies internes / base candidate |
| **Mèche longue côté X** : `X_wick > body` | spec OB §1.7 | brique morphologie base (§E) |
| **3x / BI** : `range ≥ 3·ATR233` | `bougie-3x.md`, `minATR=3.0` (L15) | accélération-1-bougie |
| **Impulsion** : BoS externe corps OU FVG valide | spec OB §1.5/§1.6, porte `reqCorps` (L16) | accélération encadrante |
| **Classement type OB** : `bodyR = body/za` → micro/corps/gris/FVG | `f_OB` L257-275 | **gate de candidature ABA** (§D) |
| Force de base `tf0` | `f_idxFromATR(ratio)` L102-109 / L276 | base du calcul force ABA (§F) |
| Cascade demi-paliers (M1=0 … W1=11) | `f_tfName`/`chartIdx` L71-85 | échelle de force |
| Cycle de vie (tape/mort/désact) | type `OB.taps/.dead/.desact`, `f_life` L533-568 | désactivation ABA −1 (§F) |
| Champ force | `OB.f0` | force ABA écrite ici |
| Champ désactivation | `OB.desact` | flag re-tap ABA |

> **Principe architectural (impératif humain).** La recherche 5-barres/ABA **n'est PAS un scan autonome**. C'est une **qualification branchée** : `f_OB` détecte d'abord un OB et le **classe par type** (`bodyR`) ; la qualification ABA s'exécute **APRÈS** ce classement, **gatée par le type** (§D), pour décider si l'OB déjà détecté **EST la base d'une 5 barres**. Cohérent avec le canon « OB d'origine = 3 temps et demi sous la 5 barres » (`5-barres.md` `ob_origine_3_temps_demi_sous_5_barres`) : l'OB siège à la base de l'accélération.

---

## §C — Définition opérationnelle de la 5 barres (brique de comptage)

### C.1 — Intention
Reconnaître une **accélération canon** = 5 bougies consécutives même sens, avec la tolérance canon d'une opposée isolée. C'est la **structure englobante** dont la base ABA sera le centre.

### C.2 — Primitives requises (et seulement celles-là)
Pour chaque bougie de la fenêtre : son **sens** (bull/bear via `C>O`/`C<O`), et l'index de barre. Rien d'autre n'est requis pour le comptage pur. (La morphologie « petit corps + longues mèches » concerne la **base**, pas le comptage — §E.)

### C.3 — Règle exacte de comptage

**Fenêtre** *(conventionnel)* : `W_5b = 8` bougies (canon « 7-8 », on retient 8 comme borne haute pour absorber 5 + 1 opposée + 2 de tolérance de bruit). Paramètre `aba_window_5b` (§H).

**Direction de référence** *(exact)* : `D ∈ {bull, bear}` = sens majoritaire des bougies de la fenêtre, OU le sens imposé par le contexte injecté (cf. principe « tendance = injectée »). **TC-4 / §I** : on n'estime PAS la tendance ici ; `D` est une **entrée** (`up`/`down`).

**Comptage `count` dans le sens `D`** *(exact)* : nombre de bougies de la fenêtre dont le sens == `D`.

**Tolérance d'opposées** *(exact, zéro paramètre dérivé du canon)* :
```
opposite_isolated = nombre de bougies de sens ≠ D
two_consecutive_opposite = ∃ deux bougies adjacentes (i, i+1) toutes deux de sens ≠ D
three_consecutive_opposite = ∃ trois bougies adjacentes toutes ≠ D
```

**Validité 5-barres** *(combinaison exact + conventionnel)* :
```
cinq_barres_valide(D, fenêtre) =
        count >= ABA_COUNT_CANON            # 5  (conventionnel canon, tunable:false)
    AND opposite_isolated <= ABA_OPP_MAX    # 1  (conventionnel canon, tunable:false)
    AND NOT two_consecutive_opposite        # exact
    # NOT three_consecutive_opposite est impliqué par NOT two_consecutive_opposite
```

> ⚠️ **Cohérence canon à noter (non bloquante)** : `5-barres.md` dit « ≤1 opposée isolée, jamais 2 consécutives » tandis que `bougie-institutionnelle.md` (`cinq_barres_2_consecutives_opposees_invalide` / `cinq_barres_3_consecutives_disqualifient`) tolère « 1 ou 2 opposées consécutives, 3 disqualifient ». **Divergence inter-sources sur le seuil de consécutivité (2 vs 3).** La règle ci-dessus retient la **version STRICTE de `5-barres.md`** (jamais 2 consécutives), qui est la note canon primaire. **TC-6 / §G** : si l'humain préfère la version `bougie-institutionnelle.md`, remplacer `NOT two_consecutive_opposite` par `NOT three_consecutive_opposite` et borner `opposite_isolated ≤ 2`.

**Critère « propre » (monte vite)** *(qualitatif → 🔴 TC-5)* : `5-barres.md` `cinq_barres_propre_si_monte_vite` exige `retracement_intra_sequence < seuil` ET `duree_formation < seuil`. **Aucun des deux seuils n'est chiffré au canon.** → marqué `aba_clean_max_retrace` et `aba_clean_max_duration` en §H avec **valeur = TROU**. Le comptage C.3 reste valide sans ce critère ; « propre » est un **raffinement de qualité**, pas une condition d'existence.

### C.4 — Cas limites (comptage)
- **Bougie doji** (`C == O`, sens indéfini) : compte comme **opposée** au sens `D` (conservateur : un doji n'est pas une bougie « dans le sens »). *(Convention 🟦, à confirmer — le canon est muet.)*
- **Fenêtre incomplète (warm-up, < `W_5b` barres)** : `cinq_barres_valide = false` (pas assez de données). Pas d'erreur, simple absence.
- **Volume nul / barre vide** : ignorée pour le sens ? **Le détecteur n'utilise pas le volume** ; une barre `H==L` (range nul) → sens via `C` vs `O` ; si `C==O` aussi → traitée comme doji ci-dessus.
- **Mèche qui « efface le jeu » avant la séquence** (`bougie-institutionnelle.md` `cinq_barres_ne_pas_compter_bougie_meche_efface`) : le comptage 1-2-3-4-5 doit **démarrer après** le point d'effacement (sweep/invalidation). ⚠️ « efface le jeu » est **narratif, non formalisé** → **non encodé** ici (marqué TROU mineur, hérité du canon).

---

## §D — Branchement sur le type d'OB (le cœur de l'architecture)

### D.1 — Intention
Décider **quel OB déjà classé par `f_OB`** déclenche la recherche 5-barres autour de lui. **L'ABA n'est testée QUE pour les OB d'un type compatible avec une base « petit corps + longues mèches ».**

### D.2 — Rappel du classement existant `f_OB` (L257-275, ne pas réinventer)
```
bodyR = |C−O| / za            # za = ATR de la bougie OB
bodyR < 0.30   → "micro"      # tracé optionnel (showDown)
bodyR <= 0.63  → "corps"      # OB-corps standard
bodyR <= 0.65  → "gris"       # zone grise
sinon          → "FVG"        # impulsion trop violente
```

### D.3 — Quel type est candidat ABA-base ? 🔴 **TC-3 — décision humaine**

**Analyse morphologique.** La base ABA canon = **petit corps + longues mèches** (`aba.md`). Dans le vocabulaire `bodyR` de `f_OB` :
- Un **petit corps** ⇒ `bodyR` **faible** ⇒ catégorie **`micro` (`bodyR < 0.30`)** est le candidat le plus naturel : c'est exactement « corps minuscule ».
- Mais `bodyR` mesure **corps/ATR**, PAS le ratio corps/mèche. Une bougie peut avoir `bodyR < 0.30` **sans** longues mèches (une toute petite bougie compacte). Donc `micro` est **nécessaire mais pas suffisant** : il faut **ajouter** le test mèches (§E).
- Les types `corps`/`gris`/`FVG` correspondent à des corps **dominants** → **antinomiques** avec une base « petit corps ». **Exclus** comme base ABA.

**Options (NON tranchées) :**

| Option | Gate de candidature | Argument | Risque |
|---|---|---|---|
| **D3-a** | `typ == "micro"` **ET** test mèches §E | colle au canon « petit corps » via le seuil 0.30 déjà câblé | le 0.30 est un seuil OB-présence, pas un seuil base-ABA (cf. `ob-spec-vs-vault-confrontation` T4 : 0.30 base = passage garbled, retiré du critère) |
| **D3-b** | `typ ∈ {"micro"}` **OU** bougie sous le seuil bruit (`range ≥ 0.5 ATR` mais `bodyR` quelconque) + test mèches §E | capte les bases à corps moyen mais mèches énormes que `micro` raterait | élargit la candidature → faux positifs possibles |
| **D3-c** | **Test morphologique dédié** indépendant de `bodyR` : `body < upper_wick ET body < lower_wick` (§E), appliqué à TOUT OB non-FVG | aligne sur le §T4 de la spec OB (morphologie pure, sans chiffre) | dé-corrèle de la taxonomie `bodyR` → 2 notions de « base » dans le code |

> **Recommandation de spec (non décisionnaire) :** D3-a est le plus fidèle à l'architecture « gaté par le type » exigée par l'humain (réutilise littéralement le classement `f_OB`). D3-c est le plus fidèle au canon morphologique pur (`aba.md`). **L'arbitrage tranche TC-1 et TC-3 ensemble** (le seuil mèche EST TC-1).

### D.4 — Intégration dans le pipeline `f_OB` (déterministe, indépendante du choix D3)
La qualification ABA s'insère **après** le bloc de classement (`f_OB` L257-275) et **avant** l'écriture du label/box, comme une **étape conditionnelle** :

```
# --- dans f_OB, après le calcul de `typ` et de `tf0` ---
is_aba_candidate = GATE_TC3(typ, base_morpho)        # §D.3 (au choix humain)
aba_qualified    = false
if is_aba_candidate:
    aba_qualified = qualifie_ABA(x1, endBar, bull, base_zone)   # §E
if aba_qualified:
    # force TF+1 (§F), polarité positive, tag "ABA"
    f0  := force_aba(tf0)                              # §F.1  (dépend de TC-2)
    pol := POSITIVE                                    # canon 5-barres
    tag := "ABA"
```

> **Aucun nouveau détecteur.** `qualifie_ABA` ne fait que **regarder autour de l'OB déjà trouvé** (la jambe `[x1, endBar]` déjà connue de `f_OB`) pour vérifier accélération-avant + base(=l'OB) + accélération-après.

---

## §E — Qualification ABA = l'OB est la base centrale d'une 5 barres

### E.1 — Intention
Partant d'un OB candidat (type compatible §D), tester s'il est la **base** d'une séquence **accélération → base → accélération**.

### E.2 — Primitives requises
- La jambe d'impulsion de l'OB : `[x1, endBar]` (déjà passés à `f_OB`).
- Pour la **base** (l'OB lui-même + jusqu'à 3 bougies) : `body`, `upper_wick`, `lower_wick` de chaque bougie de base.
- Pour les **accélérations** encadrantes : le test `accélération` (§E.4).

### E.3 — Morphologie de la base *(🔴 TC-1)*
**Règle (forme, sans chiffre arrêté) :**
```
base = 1 à 3 bougies consécutives, chacune vérifiant :
    petit_corps(b) ET longue_meche_haut(b) ET longue_meche_bas(b)
```
- **`longue_meche_haut` / `longue_meche_bas`** *(relatif, sans paramètre — réutilise spec OB §1.7)* :
  `upper_wick > body` ET `lower_wick > body`. Mèches longues **des deux côtés** (canon `aba_base_petit_corps_longue_meche`).
- **`petit_corps`** *(🔴 TROU — 3 options, non tranchées, = TC-1)* :
  - **Option TC-1-α** : réutiliser le plancher OB `body < 0.30·ATR233` (seuil déjà câblé, frontière `micro`). Justif : cohérence avec `f_OB`. Réserve : `ob-spec-vs-vault-confrontation` note que le 0.30-base-ABA vient d'un passage **garbled** (`bXSNlOQ-h3c@01:38:21`) **retiré du critère** — donc **non canon**.
  - **Option TC-1-β** : pas de seuil ATR absolu — **`body < upper_wick ET body < lower_wick`** suffit (le corps est dominé par chaque mèche). C'est la formulation **déjà retenue au §T4 de la spec OB** (inférence assumée). Avantage : scale-free, zéro paramètre. C'est la voie recommandée par cohérence avec OB §T4.
  - **Option TC-1-γ** : seuil ATR dédié `aba_base_body_max` (nouveau paramètre tunable, calibré au backtest). Avantage : tunable. Inconvénient : nombre introduit hors canon.

  > **Le canon ne chiffre PAS ce ratio** (`aba.md` `aba_base_petit_corps_longue_meche` : `seuil_petit_corps` est un **placeholder**). La spec **n'en tranche aucune**. Note : TC-1-β rend `petit_corps` **redondant** avec `longue_meche_*` (déjà `body < chaque mèche`), donc la règle base se réduirait à « longues mèches des deux côtés », ce qui est le choix le plus parcimonieux.

- **Nombre de bougies** *(conventionnel canon)* : `1 ≤ |base| ≤ ABA_BASE_MAX` avec `ABA_BASE_MAX = 3` (`aba.md` `aba_base_bougies_max`, `tunable:false`). Au-delà → **pas une base** → pas d'ABA.

### E.4 — Définition de l'accélération encadrante
Une accélération = **5-barres OU 3x** (canon, deux formes équivalentes) :
```
acceleration(segment, D) =
        cinq_barres_valide(D, segment)            # §C.3
    OU  ∃ bougie ∈ segment : range(bougie) >= ABA_3X_ATR · ATR233   # 3x, ABA_3X_ATR=3.0
```
- **`accél_in`** (avant la base, dans le sens `D`) : segment des bougies **précédant** la base jusqu'à `x1`.
- **`accél_out`** (après la base, dans le sens `D`) : segment des bougies **suivant** la base jusqu'à `endBar`.
- **Validation `accél_out`** *(exact, verrouillé — repris du §T4 OB)* : sa clôture franchit l'extrême de la base — bull : `close > base_high` ; bear : `close < base_low`.

> **TC-6** ⚠️ : le canon autorise « 5-barres OU 3x » pour UNE accélération, mais ne dit pas si `accél_in` et `accél_out` peuvent être **de formes différentes** (ex. 5-barres avant, 3x après). Par défaut, cette spec **autorise l'asymétrie** (chaque côté validé indépendamment par `acceleration(...)`). À confirmer humain.

### E.5 — Règle de qualification ABA complète *(exact, conditionnée aux TROUS)*
```
qualifie_ABA(x1, endBar, D, base_zone) =
        is_aba_candidate (§D.3, gate de type — TC-3)
    AND base_valide        : 1..3 bougies petit-corps + longues mèches (§E.3 — TC-1)
    AND acceleration(accél_in,  D)                         # §E.4
    AND acceleration(accél_out, D)
    AND close(accél_out) franchit l'extrême de la base     # E.4 validation
    # optionnel (qualité) : cinq_barres_propre  (§C.3 — TC-5)
```

### E.6 — Cas limites (qualification)
- **Base de 0 bougie** (l'OB n'a pas de mèches longues) → `base_valide = false` → pas d'ABA. L'OB reste un OB normal.
- **`accél_in` absente** (l'OB est en tout début de série, pas de bougies avant `x1` dans la fenêtre) → pas d'ABA (il faut **deux** accélérations encadrantes). L'OB reste un OB normal.
- **`accél_out` non confirmée** (clôture ne franchit pas l'extrême de la base à `endBar`) → pas encore ABA ; ré-évaluable à barres suivantes (cohérent avec confirmation 2-barres des pivots).
- **Range dégénéré** (base à `H==L`) → `upper_wick = lower_wick = 0`, `body = 0` → `body < wick` faux (0 < 0 faux) → **pas une base** (correct : une bougie plate n'a pas de longues mèches).
- **ATR233 nul / warm-up** (`za <= 0`) : `bodyR = na`, `typ = "?"` (déjà géré L263) → pas candidat → pas d'ABA.
- **Égalités** (`upper_wick == body`) : la règle stricte `>` rejette l'égalité → pas une longue mèche (conservateur).

---

## §F — Effet sur la force (réutilise `f0` et `desact`)

### F.1 — Force ABA = +1 temps = +2 crans ✅ **TC-2 FERMÉ (2026-06-20)**
**Verdict (triple-vérifié : transcript brut + 2 digs aveugles indépendants)** : « un temps au-dessus » d'un ABA = **+1 temps = +2 crans** (= +1 paire d'énergie dans la cascade).

**Preuve — 5 exemples chiffrés (TF base ET résultat nommés), tous +2 crans :**
| Source | Base | ABA actif | Crans |
|---|---|---|---|
| `24tpbSEAXeA 01:20:26` | H4 (8) | D1 (10) | +2 |
| `24tpbSEAXeA 01:21:20` | H1 (6) | H4 (8) | +2 |
| `8TeAEU76TEY 01:06:57` (+ `01:09:38`) | M30 (5) | H2 (7) | +2 |
| `aNdmUXqCHfw 01:00:14` (lu en entier) | M30 (5) | H2 (7) | +2 |
| `vZ15cwe3r5A 00:40:52` | H1 (6) | H4 (8) | +2 |

**Calibration « 1 fois de force = 1 temps = 2 crans »** (7 ex. indép.) : décisive `aNdmUXqCHfw 00:56:23` « D1 perd **deux fois** → H1 » (10−4=6 ⟹ 1 fois = 2 crans).

**Pourquoi « un temps » = 2 crans** : les crans de la cascade sont des **demi-paliers**. « Un temps au-dessus » de M30 saute par-dessus H1 (= partenaire de paire {M30,H1}, « même jeu ») et atterrit sur **H2**. Loi de parité « pas de demi-temps » (en-tête détecteur L4) : un ABA à +1 cran aurait la parité inverse de sa base → **interdit**. Seul +2 crans est cohérent.

**RÉFUTÉS** : (a) la lecture « +1 cran » (M30→H1) = artefact de lecture tronquée du passage `aNdmUXqCHfw 01:00` (« il devient M30 » = l'état DÉSACTIVÉ ; l'ACTIF était H2, `01:00:14`) ; (b) la glose `aba.md` « +1 demi-palier / demi-temps au-dessus » — Garry ne le dit JAMAIS pour la force ABA (« un temps au-dessus » ×4 ; le « demi-temps » canon vise la ZONE normale `24tpbSEAXeA 01:22:29` ou l'AFFINAGE, jamais l'ABA).

**Règle (fermée) :**
```
f0_aba = min(tf0 + 2, 11)        # tf0 = force de base d'OBSERVATION (leg/swing)
```
- `aba_force_offset = 2 crans` (= +1 temps), `tunable:false`.
- **SANS climb** : Dig A n'a trouvé **aucun** empilement du +1-ABA sur une force déjà montée par cassage/climb. L'ABA est une **source de force autonome** (base d'observation + 1 temps), pas `tf0fExt + 2`. ⚠️ **Réserve impl/viz** : vérifier au rendu que « sans climb » ne sous-évalue pas l'ABA vs un OB-corps climbé (+4) — si tension, re-confronter au canon avant d'ajuster (ne pas inventer).

### F.2 — Désactivation au re-tap = −1 (et non −2) ✅
**Canon** : `force-energie.md` `desactivation_jeu_normal_perd_deux_fois_force` — jeu **normal** désactivé → **−2** ; jeu **institutionnel** (ABA / BI, intrinsèquement TF+1) → **−1** (la perte de 2 ramènerait à TF−1, donc on compense le +1 de base).

**État actuel du détecteur** (`f_life` L565-568) : `useDesact` applique **−2 à tous** (`fdes = o.f0 - 2`) avec commentaire explicite « institutionnel/ABA = −1 **non détecté** → défaut −2 ». **La qualification ABA de cette spec FOURNIT précisément le signal manquant.**

**Règle exacte (unité FERMÉE avec TC-2 : 1 fois = 1 temps = 2 crans) :**
```
# à l'écriture de l'OB (§D.4) : marquer la nature institutionnelle
OB.is_inst := aba_qualified        # nouveau champ booléen (ou réutiliser un bit libre)

# dans f_life, au moment de la désactivation (L565-568) :
desact_penalty = OB.is_inst ? ABA_DESACT_PENALTY : NORMAL_DESACT_PENALTY
fdes = o.f0 - desact_penalty
# ABA_DESACT_PENALTY    = 2 crans  (ABA "perd une fois" = −1 temps ; ramène à la base)
# NORMAL_DESACT_PENALTY = 4 crans  (jeu normal "perd deux fois" = −2 temps)
```
- ✅ **Calibration verrouillée** : « 1 fois de force = 2 crans » (7 ex. chiffrés, dont `aNdmUXqCHfw 00:56:23` D1 perd 2 fois → H1). Donc normal « **perd deux fois** » (`aNdmUXqCHfw 00:55:36`) = **−4 crans** ; ABA « **perd une fois** » = **−2 crans**.
- ⚠️ **CORRECTION D'UN CODE EXISTANT** : `f_life` applique aujourd'hui `fdes = o.f0 − 2` (−2 crans) à **TOUS** les OB (`c747c6f`, commentaire « ABA=−1 non détecté → défaut −2 »). Or −2 crans = le **taux institutionnel** (−1 temps). Les **OB normaux sont donc sous-pénalisés de moitié** : ils doivent perdre **−4 crans**. La qualification ABA (`is_inst`) fournit le signal manquant pour différencier. **À appliquer au code après feu vert** (touche du commité).

### F.3 — Cas limites (force)
- **`tf0 + offset > 11`** (W1 dépassé) → clamp à 11 (W1), déjà le pattern `math.min(..., 11)` du détecteur.
- **Force négative après désactivation** (`fdes < 0`) → affichage `"<M1"` (déjà géré L568). Pas de clamp dur (cohérent avec le détecteur, canon muet sur le plancher — cf. spec OB R18 « plancher : muet canon »).
- **Double désactivation** : le flag `OB.desact` (L565 `not o.desact`) garantit que la pénalité ne s'applique **qu'une fois**. Inchangé.

---

## §G — Tracé / sorties

### G.1 — Tracé de la zone ABA
- **Base = 1 à 3 bougies, mèches incluses** *(✅ canon, statut : concordance vault relevée `ob-spec-vs-vault-confrontation`, déjà adopté §T4 OB)*. Zone = `[min(L) sur les bougies de base, max(H) sur les bougies de base]`.
- **Verbatim vs convention** 🟡 : `aba.md` dit « base petit corps **longue mèche** » sans préciser si la **zone tracée** inclut les mèches. Le §T4 de la spec OB tranche **« mèches incluses »** (`Zone = [min L, max H]`). Cette spec **suit §T4 OB** par cohérence, en marquant que « mèches incluses » est une **convention héritée** (pas un verbatim ABA explicite). À valider visuellement TV.

### G.2 — Champs ajoutés au label / à la zone
| Champ | Valeur | Source |
|---|---|---|
| `tag` | `"ABA"` (ajouté au label, ex. `"BULL ▲ · H1 · ABA"`) | qualification §E |
| `f0` | force TF+1 (§F.1, **dépend TC-2**) | `aba.md` `aba_force_tf_plus_1` |
| `polarite` | `POSITIVE` | `5-barres.md` `cinq_barres_polarite_positive` |
| `is_inst` | `true` (pilote la désactivation −1, §F.2) | `desactivation_jeu_normal...` |

> **Réutilisation du type `OB`** : ajouter **un champ** `is_inst` (bool) au `type OB` (L161-174). Le `tag` peut être encodé dans le texte du label existant (pas de nouveau champ structurel nécessaire au-delà de `is_inst`).

### G.3 — Lien avec la BA (zone d'entrée) — HORS PÉRIMÈTRE DÉTECTEUR
`aba.md` `aba_entree_par_ba` : l'entrée se prend sur la **BA** (Base + Accélération de retour), pas sur la 1ʳᵉ accélération. **C'est une décision d'ENTRÉE (Phase 2)**, pas de détection. La spec note le lien mais **ne l'implémente pas** dans `f_OB` (cohérent avec la frontière détection/Phase-2 de la spec OB).

---

## §H — Paramètres `Config` (objet central, aucun nombre magique dans la règle)

| Paramètre | Valeur défaut | Unité | tunable | Justification / source | Statut |
|---|---|---|---|---|---|
| `aba_count_canon` | **5** | bougies | non | `5-barres.md` `cinq_barres_count_canon` | ✅ |
| `aba_opp_max` | **1** | bougies | non | `5-barres.md` `cinq_barres_max_opposite_isolated` | ✅ |
| `aba_window_5b` | **8** | bougies | oui | canon « 7-8 » (`5-barres.md` implications) | ✅ |
| `aba_base_max` | **3** | bougies | non | `aba.md` `aba_base_bougies_max` | ✅ |
| `aba_base_min` | **1** | bougies | non | `aba.md` `aba_base_bougies_min` | ✅ |
| `aba_3x_atr` | **3.0** | ×ATR233 | non | `bougie-3x.md` `bougie_3x_atr_min` | ✅ |
| `aba_base_morpho` | `corps < upper_wick ET corps < lower_wick` | — (scale-free) | non | **TC-1 fermé** : OB §T4, pas de seuil ATR | ✅ |
| `aba_force_offset` | **+2** | crans cascade | non | **TC-2 fermé** : « un temps au-dessus » = +1 temps = 2 crans (5 ex. chiffrés) | ✅ |
| `aba_base_force_ref` | `tf0` (force d'observation, **sans climb**) | — | non | **TC-2 fermé** : ABA = source autonome, pas d'empilement sur climb (Dig A) | ✅ |
| `aba_desact_penalty` | **2** (ABA) / **4** (normal) | crans | non | **TC-2 fermé** : « 1 fois = 2 crans » → ABA −1 temps, normal −2 temps | ✅ |
| `aba_gate_type` | `micro` | enum | non | **TC-3 fermé** : micro + test mèches §E | ✅ |
| `aba_clean_max_retrace` | **TROU** | ratio | oui | **TC-5** : critère « propre », non chiffré | 🔴 |
| `aba_clean_max_duration` | **TROU** | bougies | oui | **TC-5** : critère « propre », non chiffré | 🔴 |

\* `tunable: false` côté valeur canon, mais l'**unité** reste à fixer (TC-2).

---

## §I — Hypothèses explicites et tendance injectée

1. **Tendance/contexte injecté** (principe doctrinal) : `D` (`up`/`down`/`range`) est une **entrée** de `qualifie_ABA`, **jamais estimée** par la qualification. En `range`, **pas de qualification ABA** (pas de sens d'accélération défini). Le sens majoritaire de fenêtre (§C.3) n'est qu'un **fallback** si aucun contexte n'est injecté — à n'utiliser qu'avec accord humain.
2. **Single-TF vs cascade (TC-4)** 🔴 : le canon situe l'ABA **un demi-TF sous** la 5-barres (`aba.md` `aba_affinage_demi_temps`) et dit qu'on cherche l'ABA **à l'intérieur** d'une 5-barres en descendant d'un demi-TF (`bougie-institutionnelle.md` `cinq_barres_pas_d_imbalance_a_l_interieur`). **Le détecteur est single-TF.** Sur le TF chart, on détecte donc soit la **5-barres** (structure de comptage §C), soit la **base ABA** (morphologie §E) — **mais pas les deux étages simultanément sans accès TF−0,5**. La fondation TF−0,5 existe dans le détecteur (`useMTF`, `phLow`/`plLow`, L124-126) mais n'est **pas** branchée sur la qualification ABA. **Décision humaine : la qualification ABA opère-t-elle (a) sur le TF chart en assimilant base = OB micro courant, ou (b) en descendant via `request.security` au TF−0,5 ?** La spec décrit (a) par défaut (cohérent single-TF) et **signale** (b) comme l'archi canon-pure différée.
3. **Doctrine = moteur, une seule fois** : toutes les constantes vivent dans `Config` (§H). La règle (§C, §E, §F) ne contient **aucun littéral** — uniquement des références `ABA_*`.
4. **L'ABA NE remplace PAS le type d'OB** : un OB qualifié ABA **reste** un OB (de type `micro`/etc.) **augmenté** d'un tag + force TF+1 + désact −1. La qualification est **additive**, non substitutive.

---

## §J — Critères de validation (comment le backtest-validator prouvera l'edge)

> La spec **ne décrète aucun seuil de performance**. Elle dit **comment mesurer**. Méthode alignée triple-barrier / meta-labeling.

### J.1 — Labellisation triple-barrier
Pour chaque zone qualifiée ABA (sur replay barre-par-barre, déterministe) :
- **Barrière supérieure / inférieure** : `± k · ATR233` à la barre de qualification (`k` = paramètre de validation, **non fixé ici**).
- **Barrière temporelle** : `T` barres (paramètre de validation).
- **Label** : +1 si la barrière dans le sens `D` (polarité positive ⇒ continuation) est touchée en premier ; −1 si l'opposée ; 0 si timeout.

### J.2 — Meta-labeling (l'ABA porte-t-elle un edge AU-DELÀ de l'OB nu ?)
- **Échantillon A** : OB qualifiés ABA. **Échantillon B** : OB du même type **non** qualifiés ABA (groupe témoin).
- **Mesure** : taux de réussite (label +1) et espérance R **de A vs B**. L'edge ABA est démontré **si et seulement si** A surperforme B de façon **statistiquement significative** (test à fixer par le validateur — p. ex. bootstrap sur la distribution des R). **Aucun seuil décrété** : c'est la **différence A−B** qui doit être positive et significative.

### J.3 — Validation du gate de type (TC-3)
Rejouer la qualification sous **chacune** des options D3-a/b/c et comparer l'edge meta-label (J.2). **L'option retenue est celle qui maximise A−B** sans exploser le nombre de faux positifs (précision). Mesure : courbe précision/rappel des qualifications vs continuation effective.

### J.4 — Validation de la force TF+1 (TC-2)
- **Test de monotonie** : les zones ABA (force TF+1) doivent **tenir** plus souvent que des zones de force TF (cohérent `force_max_tf_plus_1`). Mesurer le taux de « tient » (rebond) des ABA vs OB normaux de même TF de base.
- **Test de l'offset** : rejouer avec `aba_force_offset ∈ {1 cran, 2 crans}` et comparer la **cohérence des verdicts tient/casse** avec les issues réelles (J.1). L'offset correct est celui qui **aligne le mieux** force prédite et comportement observé.

### J.5 — Validation de la désactivation −1 (F.2)
- Sur les ABA **re-tapées** (`taps ≥ 1`), mesurer le taux de réussite au **2ᵉ** passage. Le −1 (vs −2) prédit que l'ABA re-tapée **conserve plus de force** qu'un OB normal re-tapé. Comparer empiriquement les deux populations re-tapées : l'ABA doit **mieux tenir** au re-tap.

### J.6 — Déterminisme / rejouabilité
`qualifie_ABA` reste une **fonction pure** `(série OHLC, ATR233, D, zone OB) → {aba: bool, f0, polarite, is_inst}`. Rejouable barre-par-barre sur replay TradingView (`replay_*`), vérifiable visuellement (label « ABA »). **Exception multi-TF** : si l'option I.2(b) est retenue, dépendance `request.security` TF−0,5 (comme la zone grise §T2-bis de la spec OB introduit déjà une dépendance multi-TF).

---

## §K — Registre des points NON fermés (à trancher en relecture humaine)

| # | Point | Statut |
|---|---|---|
| **TC-1** | Ratio « petit corps / longues mèches » de la base | ✅ **FERMÉ (2026-06-20)** : `corps < upper_wick ET corps < lower_wick` (β, scale-free, déjà OB §T4). |
| **TC-2** | « un temps au-dessus » = combien de crans + désactivation | ✅ **FERMÉ (2026-06-20)** : **+1 temps = +2 crans** ; force ABA = `min(tf0+2,11)` SANS climb ; désact normal −4 / ABA −2 crans. 5 ex. chiffrés + calibration « 1 fois = 2 crans » + parité ; triple-vérifié (transcript + 2 digs aveugles). « +1 cran » et glose `aba.md` « demi-temps » RÉFUTÉS. |
| **TC-3** | Type(s) d'OB `f_OB` candidat(s) base ABA | ✅ **FERMÉ (2026-06-20)** : `typ == "micro"` + test mèches §E. |
| **TC-4** | Articulation 5-barres↔ABA single-TF vs TF−0,5 | ✅ **FERMÉ (2026-06-20)** : descente **TF−0,5** (`request.security`), archi canon-pure §I.2(b). |
| **TC-5** | Seuils du critère « propre » (retracement intra-séquence, durée) | 🔴 **NON chiffré au canon** — qualité, pas existence (non bloquant). |
| **TC-6** | (a) seuil consécutivité opposées 2 (`5-barres.md`) vs 3 (`bougie-institutionnelle.md`) ; (b) asymétrie `accél_in`/`accél_out` (5-barres d'un côté, 3x de l'autre) | ⚠️ **divergence inter-sources** (a) / **muet** (b) — à confirmer. |
| TC-7 | Doji / barre `C==O` compte comme opposée (convention conservatrice) | 🟦 convention assumée, canon muet. |
| TC-8 | « Mèche qui efface le jeu » (début de comptage) | ⚠️ narratif non formalisé, **non encodé** (hérité du canon). |
| TC-9 | Tracé base mèches incluses (verbatim ABA absent ; hérité OB §T4) | 🟡 convention héritée, validation visuelle. |

> **TC-1/TC-2/TC-3/TC-4 sont FERMÉS (2026-06-20, arbitrage humain + dig chiffré).** La règle ABA est exécutable. Restent non bloquants : TC-5 (qualité « propre »), TC-6 (asymétrie accél), TC-7/8/9 (conventions). **Reste à coder** : détection 5-barres/ABA (§C/§D/§E) + force ABA `tf0+2` (§F.1) + correction désactivation normal −4/ABA −2 (§F.2, touche le commité → feu vert requis).

---

## §L — Sources lues (citées)
- `ressources/data-wiki/concepts/5-barres.md` — note canon primaire (13 axiomes : count=5, opposée≤1, polarité positive, retrace 25%, consumée, 5è=BI, OB origine 3 temps½, propre=monte vite).
- `ressources/data-wiki/concepts/aba.md` — morphologie ABA, base 1-3 petit corps/longues mèches, force TF+1, désact −1, entrée par BA, affinage demi-temps, interchangeabilité ABA↔zone.
- `ressources/data-wiki/concepts/aba-imbrique.md` — ABA dans ABA (cascade propre vs piège ; non requis pour cette brique single-niveau, signalé).
- `ressources/data-wiki/concepts/bougie-3x.md` — 3x = ≥3 ATR, l'autre forme d'accélération.
- `ressources/data-wiki/concepts/bougie-institutionnelle.md` — 5è barre = BI ; seuils consécutivité opposées (2/3) divergents du `5-barres.md`.
- `ressources/data-wiki/concepts/order-block.md` — taxonomie OB, seuils corps/ATR 0.30/0.63/0.65.
- `ressources/data-wiki/concepts/force-energie.md` — cascade demi-paliers, désactivation −2 normal / −1 institutionnel.
- `ressources/scripts_pin/OB_Detector_v2.13.txt` — détecteur cible : `f_OB` (classement bodyR→micro/corps/gris/FVG, `tf0`, climb 1-2 +4 crans), type `OB` (`f0`, `desact`, `taps`, `dead`, `inside`, `ext`), `f_life` (cycle de vie + désactivation −2 défaut), cascade `f_tfName`/`f_subIdx`/`f_idxFromATR`.
- `docs/specs/OB_DETECTION_SPEC.md` — format de spec, primitives §0/§1, §T4 (base ABA), §3.2 (force), §T1-bis (cycle de vie).
- `C:\Users\DyBoo\.claude\projects\...\memory\ob-spec-vs-vault-confrontation.md` (lecture seule) — historique des arbitrages OB, statut du 0.30 base ABA (garbled, retiré), désactivation −2/−1, polarité=localisation.
