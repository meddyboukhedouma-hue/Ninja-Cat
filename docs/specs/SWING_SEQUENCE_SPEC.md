# Spec déterministe — Détection des swings & de la séquence 1-2 (zone d'origine)

> Objectif : détecter les **swings valides** (retracement ≥ 3 ATR) qui **cassent 2 fois** (séquence 1-2), pour identifier la **zone d'origine** de la séquence (= l'OB d'origine, détecté par `OB_DETECTION_SPEC.md`).
> Position pipeline : **amont** de la détection d'OB. Phase 1 (diagnostic) + entrée de Phase 2.
> Source de vérité : canon Garry distillé dans `ressources/data-wiki/concepts/{swing,pattern-1-2,cassage-de-structure}.md` ; citations **vérifiées à la main** dans les transcripts bruts.
> Légende : ✅ déterministe & sourcé · 🟦 décision/convention humaine assumée · ⚠️ hypothèse/inférence à confirmer · 🟡 à valider visuellement.
> **Aucune règle inventée** : tout pointe vers une source ou est marqué comme inférence explicite.
>
> **Révision 2026-06-19** : ajout **§0.5** — le **point de départ = le BIAIS** (2 cassures consécutives même sens, top-down, lecture **depuis la fin**) ; **anti-pattern** explicite : on ne part PAS d'un swing 3 ATR isolé (bug racine `cartographie.py`). §3.2 précisé (depuis la fin + filtre ≥ 3 ATR). §4.2 : la **localisation** de l'OB pointe vers **`OB_DETECTION_SPEC §2.5`** (grille intérieur/extérieur, `NOAGAfn5VhQ@02:56-03:02`).

---

## §0 — Conventions & primitives partagées (avec `OB_DETECTION_SPEC`)

- **`ATR233`**, **conventions par bougie** (`O,H,L,C,body,range,upper_wick,lower_wick`, bull/bear) : cf. `OB_DETECTION_SPEC §0/§1.1`.
- **Pivots 2/2** : `pivot_high = ta.pivothigh(high,2,2)` ; `pivot_low = ta.pivotlow(low,2,2)`, confirmés **2 barres après** (cf. OB §1.2). Un pivot « confirmé » a donc 2 barres de retard — toute jambe non close entre 2 pivots confirmés est **en cours** (exclue, cf. §1).

---

## §0.5 — Point de départ de l'analyse : le BIAIS ✅ (résolu 2026-06-19)

Le point de départ canon **n'est PAS** de mesurer un swing isolé en 3 ATR (anti-pattern = **bug racine de `cartographie.py`**). Garry commence **TOUJOURS** par **« analyser le biais »** (`SWIXd3b3mCg @ 00:24:31` : « déjà, on va analyser le biais, comme on fait tout le temps »), c.-à-d. la **tendance**, établie par **2 cassures de structure consécutives MÊME SENS** (`tendance_deux_cassures_meme_sens`, ebook G-ON p.5 « IDENTIFY THE TREND »).

- **Top-down** : le biais se lit d'abord sur le **TF supérieur** (Semaine / Journée / H4), puis on descend vers les TF d'exécution (`SWIXd3b3mCg @ 00:31:47`). *(Dépendance multi-TF, cf. S1.)*
- **Lecture depuis la FIN du tracé** (présent → passé) : on part de la **dernière** cassure et on isole **les 2 dernières cassures consécutives même sens** = la séquence active (§3.2). 🟦 **Décision 2026-06-19** : le vault **ne nomme pas** le sens de lecture gauche↔droite ; cette convention « depuis la fin » est **assumée**, cohérente avec « séquence active = les 2 derniers swings » (§3.2).
- Le swing/3 ATR, le CHoCH, la zone d'origine sont **EN AVAL** du biais — des **outils** de mesure, **jamais** le point de départ.

---

## §1 — Le swing ✅

### 1.1 Définition — le swing = le RETRACEMENT (pas l'impulsion)
Le swing à mesurer est le **retracement** : la **jambe contre-sens** qui précède directement l'accélération (impulsion/cassure). On le mesure **de l'open du retracement jusqu'au point culminant** (extrême).
> « un swing que je mesure […] c'est-à-dire **un retracement avant l'accélération. C'est ça un swing**. Je vais la mesurer **du départ de ce retracement, donc de l'open, et je vais jusqu'au point culminant** » (`L73Oe98AfwY @ 00:34:51`, **vérifié**).

⚠️ **Piège canon (cause racine du débit nul de `cartographie.py`)** : NE PAS mesurer l'**impulsion** (jambe directionnelle qui suit). Axiome `swing_principal_definition_dernier_complet`, triangulé sur **6+ vidéos, 0 réfutation** (`L73Oe98AfwY`, `MyA-xocP_J0 @ 00:29:39`, `lxSpGEk1Ec4 @ 00:05:19`, …).

### 1.2 Le swing pris = le DERNIER COMPLET
`swing_principal` = le **dernier retracement complet** (jambe terminée **entre 2 pivots 2/2 confirmés**) — **jamais** la jambe en cours (en formation), ni un swing antérieur.

### 1.3 Validité — hauteur ∈ [3, 4] ATR233
- **`swing_size`** = hauteur du retracement, mesurée **du corps (open du retracement) jusqu'à la mèche extrême** (point culminant) — PAS mèche-à-mèche (`7S_Iovunj20 @ 00:16:08`).
- **Valide ssi `3.0 ≤ swing_size / ATR233 ≤ 4.0`** (`24tpbSEAXeA @ 00:11:07` : « les swings se lissent toujours en **trois ATR** » ; `@ 00:12:21` : « entre **3 ATR et 4 ATR** », **vérifié**).
- `< 3 ATR` → **pas un swing comptable** sur ce TF (bruit structurel) → descendre d'un demi-TF pour le voir (`WO1gp3sk5U0 @ 01:01:26` ; `iAmYRT7JXUk @ 00:15:55`).
- `> 4 ATR` → appartient au **demi-palier supérieur** (`24tpbSEAXeA @ 00:12:21`).

### 1.4 Nombre de bougies ≥ 2 (avec exception)
- Un swing valide nécessite **≥ 2 bougies** (`o6HYwGv5riI @ 01:01:43` : « Une bougie c'est pas assez […] Il faudrait qu'il y en ait deux au moins »).
- **Exception** : une **énorme bougie unique** d'accélération (institutionnelle) vaut pour un swing (`be0adcdA7lw @ 01:46:22`).

### 1.5 TF du swing — zoom adaptatif sur la cascade demi-paliers
Le **TF d'un swing** = celui où sa hauteur tombe dans `[3, 4] ATR233`. On adapte le zoom sur la cascade **M1·M3·M5·M8·M15·M30·H1·H2·H4·H8·D1·W1** jusqu'à atteindre cette fourchette (`swing_tf_via_zoom`). *(Dépendance multi-TF, cf. S1.)*

### 1.6 Cas particulier — premier swing d'un retournement
Lors d'un **retournement**, le **premier** swing se mesure depuis **le sweep jusqu'au point de départ** (l'énergie des positions piégées) ; les swings suivants se mesurent normalement (`premier_swing_retournement_mesure_sweep`, `Ev0BYxPh2Wk @ 00:26:02`). *(Cas spécial, cf. S5.)*

---

## §2 — Le cassage (« la casse ») ✅

### 2.1 Cassage propre vs sweep — la clôture du CORPS prime
- **Cassage propre** : une bougie **clôture son CORPS au-delà** du niveau du swing (`close` au-delà du pivot).
- **Sweep** : la **mèche** dépasse le niveau mais la **clôture revient en deçà** → **pas** un cassage (prise de liquidité seule).
> « la bougie, elle a pas clôturé sous ce bas et après elle est montée […] **fausse cassure** » (`0OeOoBj-Hb0 @ 00:48:54`) ; « La mèche n'a pas cassé ses bas […] c'est cette bougie qui est à l'origine de la cassure » (`48O7ZguVUVE @ 00:45:57`).
- Formel : `body_close au-delà du niveau ⇒ cassage_propre = true` ; `wick au-delà ET body_close PAS au-delà ⇒ sweep`.
- **= le BoS** de `OB_DETECTION_SPEC §1.5` (et le BoS **externe** est le cassage qui valide la séquence — le « 2 » après le CHoCH).

### 2.2 Validation d'un cassage — zoom 2 cm (demi-palier au-dessus)
Pour valider qu'une bougie a **vraiment** clôturé au-delà, regarder le TF **un demi-palier au-dessus** (zoom ≈ 2 cm), pas en 3 cm (trop de bruit) (`validation_cassage_zoom_2cm`, `KQUcqYcvLsM @ 00:21:00`). *(Dépendance multi-TF, cf. S2.)*

### 2.3 Cassage interne ≠ retournement
Casser un **swing interne** (creux local) **ne valide pas** un retournement de structure — c'est seulement un **jeu interne** (`cassage_swing_interne_pas_retournement`, `YpTulm2Wj04 @ 02:09:17`). Un **sweep-mèche** des hauts **promeut** les swings internes en externes (`swing_interne_promu_via_sweep`, `YpTulm2Wj04 @ 02:07:53`).

---

## §3 — La séquence « casse 2 fois » (pattern 1-2) ✅

### 3.1 Toujours un jeu de DEUX swings
> « **Toujours un jeu de deux swings.** Pourquoi ? parce que le premier swing, c'est souvent le comportement des gros joueurs » (`toujours_jeu_de_deux_swings`, `MPnzEcwA25U @ 00:17:10`).
Mécanique causale : un gros joueur impulse **2 vagues successives** (parfois 3, rare) (`jQ1dw2zgUek @ 00:16:43`).

### 3.2 Séquence active = les 2 dernières cassures consécutives **MÊME SENS** (lues depuis la fin)
`sequence_active` = **fenêtre glissante** sur les 2 derniers swings/cassures consécutifs de **même direction** (PAS un scan global) (`sequence_active_plus_petit_pattern_1_2`, `WO1gp3sk5U0 @ 00:12:42` : « On était sur une séquence en M30 puis en M15 […] on regarde le marché M15 M15 »).
- **Lecture depuis la FIN** (§0.5) : on part de la **dernière** cassure et on remonte ; on retient **les 2 dernières cassures consécutives même sens**.
- **Filtre de validité** : seuls comptent les swings **≥ 3 ATR233** (§1.3) ; les micro-swings `< 3 ATR` sont **ignorés** (§3.5) — « casser un micro swing n'est PAS le début d'une séquence » (`rwRNzxzzr10 @ 00:16:24`).

### 3.3 TF de trade = le PLUS PETIT des 2 swings
`pattern_1_2_tf = min(swing_a.tf, swing_b.tf)` (`regle_1_2_tf_de_trade`, `SmJFcCi8cHA @ 00:38:06` : « on prend toujours le plus petit des deux swings »).
**Contre-trend** : on observe en face le TF **`pattern_1_2_tf + 2` demi-paliers** (`regle_1_2_contre_trend_tf_n_plus_2`, `SmJFcCi8cHA @ 00:38:14` : « on va chercher deux time frame au-dessus »).

### 3.4 Structures de séquence canon (plafond 4 cassages)
Une séquence canon valide est **l'une** de ces structures équivalentes (`sequence_structure_canon_3_ou_4_cassages`, `eqX6RZm8_4Y @ 01:49:23`) :
(a) **3 cassages** de swing même TF · (b) **4 cassages** même TF · (c) **1 gros + 1 petit** cassage · (d) **1 gros + 2 petits**. → **« jamais plus, jamais moins »**. Au-delà de 4 cassages : séquence terminée / nouvelle séquence.

⚠️ **À ne pas confondre avec §3.1-3.3** : le **pattern 1-2 actif** = les **2 derniers swings** qu'on lit et trade (fenêtre glissante) ; les structures ci-dessus décrivent le **nombre de cassages d'une séquence COMPLÈTE** (qui se clôt à 3-4 cassages, nouvelle séquence au-delà). La logique « gros vs petit swing » des variantes (c)/(d) reste à formaliser (cf. S4).

### 3.5 Exclusions du comptage des swings
- **Double top / double bottom** : ne compte **PAS** (= liquidité accumulée, pas un swing) (`double_top_pas_compte_comme_swing`, `0OeOoBj-Hb0 @ 01:07:56`, `-ePJRgURtOA @ 03:40:01`).
- **Swing < 3 ATR** (micro) : ne compte pas (`swing_sous_3cm_pas_compte`) ; « casser un micro swing n'est PAS le début d'une séquence » (`rwRNzxzzr10 @ 00:16:24`).
- **Sweep-only** (mèche, pas de clôture) : pas un cassage comptable (§2.1).

### 3.6 Comptage directionnel & contre-swing
- **Direction** = côté avec le plus de cassures (`comptage_directionnel_max_cassures`, `KQUcqYcvLsM @ 00:14:42`).
- **Contre-swing valide** = swing **1 à 1,5 temps inférieur** au swing principal (`contre_swing_min_size`, `rwRNzxzzr10 @ 00:16:54`) — cf. `OB_DETECTION_SPEC R13(b)` (réconcilie « moitié du swing » ↔ « ~1 cm »).

---

## §4 — Identifier la zone d'origine ✅

### 4.1 Référence = le premier des swings
> « **On regarde toujours par rapport au premier des swings** » (`sequence_mesuree_par_premier_swing`, `cZuWS5kuXqg @ 02:17:25`).

### 4.2 La zone = l'OB d'origine de la séquence
La **zone d'origine** de la séquence détectée = l'**OB d'origine** (la racine du mouvement). Répartition des responsabilités :
- **Cette spec** fournit la **séquence** (les 2 cassures même sens, le TF, le biais, le `bar_origine`).
- **`OB_DETECTION_SPEC §2.5`** — **LOCALISE** *lequel* des candidats est l'OB d'origine (grille **intérieur → 1ᵉʳ micro-swing / extérieur → 1ᵉʳ gros swing / même TF imbriqué → liquidité**, sourcée `NOAGAfn5VhQ@02:56-03:02`). Référence = **le 1ᵉʳ des 2 swings** (§4.1).
- **`OB_DETECTION_SPEC §2` (5 types) + §T1-bis** — donnent la **forme / tracé / cycle de vie** de la zone une fois localisée.

### 4.3 Force & priorité
- Chaque swing porte un `force_level` ; le calcul (cascade demi-paliers + cassages **+2 demi-paliers/cassage, plafond 2** − dégradations) = **`OB_DETECTION_SPEC §3.2`** (modèle de force, pointeur vers `force-energie.md`).
- **3 cassures + liquidité sur le 2e swing** → le marché tape **d'abord le 2e swing**, puis remonte chercher le 1er (2 étapes de trade distinctes) (`trois_cassures_2eme_swing_first`, `jevVat55Svg @ 00:15:49`).

---

## §5 — Registre des points ouverts / dépendances

| # | Point | Statut |
|---|---|---|
| S1 | TF du swing par zoom adaptatif (§1.5) | ⚠️ **dépendance multi-TF** : mesurer la hauteur du swing sur la cascade jusqu'à `[3,4] ATR` → la fonction a besoin d'un accès multi-TF (comme la zone grise OB §T2-bis) |
| S2 | Validation du cassage en zoom 2 cm (§2.2) | ⚠️ **dépendance multi-TF** : confirmer la clôture sur le demi-palier au-dessus |
| S3 | « Dernier swing complet » (§1.2) | ✅ sourcé, mais lag : pivots 2/2 = 2 barres de retard ; la jambe en cours est exclue par construction |
| S4 | Structures (c)/(d) « gros + petit(s) » (§3.4) | ⚠️ codable mais demande une logique **TF-relative** (qu'est-ce qu'un « gros » vs « petit » swing dans la séquence) — à préciser |
| S5 | Premier swing de retournement = mesure sweep→départ (§1.6) | ⚠️ cas spécial, à coder distinctement de la mesure standard |
| S6 | Mesure « corps → mèche extrême » vs « open → point culminant » (§1.1/§1.3) | ✅ cohérent (open du retracement = départ corps ; point culminant = mèche extrême) — à confirmer sur cas-types 🟡 |

---

## §6 — Testabilité
Sortie de cette spec = pour chaque séquence active : `{direction, pattern_1_2_tf, swings: [s1, s2], cassages, bar_origine}` → consommé par `OB_DETECTION_SPEC` (qui détecte la zone à `bar_origine`). Déterministe ⇒ rejouable barre par barre, vérifiable sur replay TradingView. Les seuls degrés de liberté sont S1–S6 (dépendances multi-TF + 2 cas spéciaux) ; tout le reste est figé/sourcé.
