# Spec déterministe — Détection des 5 types d'Order Block

> Étalon : doctrine verrouillée le 2026-06-17 (vidéo Garry + ebook G-ON + Pine v19 attestée).
> Objectif de ce document : **vérifier** que chaque type est entièrement déterministe et testable.
> Légende statut : ✅ déterministe & sourcé · ⚠️ hypothèse de travail (source muette, à confirmer en relecture) · 🟡 à valider visuellement · 🔴 seuil non sourcé à calibrer.
> **Aucune règle ci-dessous n'est inventée** : tout pointe vers une source ou est marqué comme hypothèse explicite.
>
> **Révision 2026-06-18** (après confrontation vidéo + ebook, cf. mémoire `ob-spec-vs-vault-confrontation`) :
> - **D1 — §T3 corrigé au canon** : l'englobement S/D passe de « corps-sur-corps » à **mèche comprise** (clôture de l'englobante au-delà de l'extrême-mèche opposé), conforme à `6AyQ-UFocFg @ 00:01:21`.
> - **D2 — §T2 : la zone grise est tranchée** par une **convention de doctrine humaine** (la vidéo la déclare discrétionnaire — « zone grise », `FFxKFvuYxrM @ 00:11:18`). Cette convention est marquée 🟦 = décision humaine assumée, HORS vault.
> - **D3 + T4 officialisés** : les seuils 0.30 (borne basse OB §T2 ; corps de base ABA §T4), jusque-là non sourcés/inférés, sont désormais **sourcés** par le dig (`7S_Iovunj20 @ 01:05:17` et `bXSNlOQ-h3c @ 01:38:21`). Correction annexe : base ABA `1 à 5` → **`1 à 3`** bougies (canon `aba.md`).
> - **R3 tranché — cycle de vie OB (§T1-bis)** : la convention non sourcée `close </> bord` est remplacée par le **modèle du « reste »** (épaisseur résiduelle ≥ 0.45 ATR233 = vivant ; traversé sans réaction = mort ; re-légitimation par double cassage). Citations vérifiées à la main. Bords flous restants tracés en R11–R12.
> - **R10 tranché — « sans réaction » = clôture vs mèche (§T1-bis c)** : seule une **clôture** au-delà du bord lointain consomme/tue l'OB ; une **mèche** qui dépasse mais clôture revenue dans la zone = rejet = la zone tient. Canon « la clôture prime ».

---

## §0 — Conventions par bougie `i`

| Symbole | Définition |
|---|---|
| `O,H,L,C` | open, high, low, close de la bougie `i` |
| `body_high` | `max(O, C)` |
| `body_low` | `min(O, C)` |
| `body` | `abs(C − O)` (hauteur de corps) |
| `range` | `H − L` |
| `upper_wick` | `H − body_high` |
| `lower_wick` | `body_low − L` |
| bull/bear | bull si `C > O`, bear si `C < O` |

---

## §1 — Primitives partagées (le socle déterministe)

### 1.1 ATR233 ✅
`ATR233 = SMA(TrueRange, 233)` (TR de Wilder). Unité de toutes les comparaisons de taille. Source : ebook + script `ATR_SMA_233`.

### 1.2 Pivots 2/2 ✅
`pivot_high = ta.pivothigh(high, 2, 2)` · `pivot_low = ta.pivotlow(low, 2, 2)`. Confirmés 2 barres après. Source : Pine v19 (attestation).

### 1.3 « Vrai corps » / filtre noise ⚠️
Constante `noise = 0.5` déclarée (Pine v19) mais **son rôle exact n'est pas dans mes sources**.
**Hypothèse de travail** : une bougie a un « vrai corps » si `body ≥ noise × range` (corps ≥ 50 % de la barre). Utilisée uniquement comme garde-fou « pas de vrai corps » de T2.
→ **À confirmer** : est-ce bien ça que fait `noise` dans la v19 ?

### 1.4 FVG (Fair Value Gap, 3 bougies) ✅
Sur le triplet `(i−2, i−1, i)`, la bougie `i−1` est l'impulsion, `i−2`/`i` l'encadrent :
- **FVG haussière** : `gap = L[i] − H[i−2]` ; valide si `gap ≥ 0.45 × ATR233`.
- **FVG baissière** : `gap = L[i−2] − H[i]` ; valide si `gap ≥ 0.45 × ATR233`.
Zone FVG = `[H[i−2], L[i]]` (bull) / `[H[i], L[i−2]]` (bear). Source : ebook p7/p17.

### 1.5 BoS (Break of Structure) ✅ (avec 1 sous-décision)
`P_high` = dernier pivot_high 2/2 confirmé ; `P_low` = dernier pivot_low 2/2 confirmé.
- **BoS haussier** : `close > P_high`.
- **BoS baissier** : `close < P_low`.
⚠️ **Sous-décision ouverte** : l'ebook distingue BoS **externe** (swing majeur) vs **interne** (creux local) [p3]. Par défaut on prend la **cassure du dernier pivot 2/2** (externe le plus proche). À confirmer si l'impulsion exige spécifiquement l'externe.

### 1.6 Impulsion ✅ (VERROUILLÉ)
Un mouvement est **impulsif** ssi il **casse la structure (BoS, §1.5) OU laisse une FVG valide (§1.4)**.
Socle des 5 types. Rejeté : `1.5×ATR14` (proxy code), `≥3 ATR233 / 5 bougies` (= grande impulsion scénario D seulement).

### 1.7 Mèche longue ✅
Bougie à **mèche longue** côté `X` si `X_wick / range ≥ 0.50` (`X` = upper ou lower). Source : Pine v19 (mèche ≥ 0.50).

---

## §2 — Les 5 détecteurs

### Principe architectural (transcription) ✅ — UNE zone par impulsion
« Tu pars du mouvement → tu remontes à la source → tu CHOISIS la bonne zone. » Donc par impulsion on sélectionne **un seul** type (T1/T2/T3/T4/T5), jamais plusieurs en parallèle. Concrètement : **FVG présente → T2 décide (corps ou FVG), T1 éteint** ; BoS sans FVG → T1.

### T1 — OB Classique ✅ (tracé : défaut Pine)
**Déclencheur** : une jambe impulsive (§1.6) part d'un pivot 2/2.
**Algorithme** (cas haussier ; bear symétrique) :
1. Pivot_low `PL` confirmé.
2. La jambe montante depuis `PL` est impulsive (§1.6) — sinon rejet.
3. **OB candle** = la **dernière bougie bear** (`C<O`) au plus tard à `PL`, en remontant jusqu'à `lookback = 30` barres.
4. **Zone (tracé verrouillé `open→low`)** : `top = O_ob`, `bottom = L_ob`. (Bear : `top = H_ob`, `bottom = O_ob`, tracé `open→high`.)
**Invalidation / cycle de vie** : voir **§T1-bis** (R3 tranché — modèle du reste). Remplace l'ancienne convention non sourcée `close </> bord`.

#### T1-bis — Cycle de vie de l'OB (R3 — modèle du « reste », tranché 2026-06-18)
Citations vérifiées à la main dans les transcripts bruts. **Grandeur pivot = l'épaisseur du RESTE de la zone** (pas un compteur de tapes). Le 50 % et les « 3 conditions » des deux vidéos ne sont pas des seuils rivaux : ce sont deux mesures de « combien il reste ».

**(a) Persistance à la formation** : l'OB reste valide tant qu'aucune bougie postérieure ne **clôture au-delà de sa mèche** (les bougies qui naissent après doivent rester « enfermées » dans le `[plus haut ; plus bas]` de l'OB). Bull : invalidé si `close > H_ob` ; bear : `close < L_ob`. Source (haussier) `Kp68Daasc6I @ 01:09:34` (« si la bougie ferme au-dessus de la mèche, ça c'est plus rien »). **R12 tranché (2026-06-18) : symétrie bear ADOPTÉE par inférence** (non sourcée ; le canon ne cite que le haussier et a même retiré la borne basse après audit — cohérence avec `bougie_englobante_cloture_canon` bi-directionnel). À retester si une source bear apparaît.

**(b) Entame partielle → consommation, le reste survit** : un retour qui pénètre la zone **consomme une partie** (« tu as pris une certaine quantité… tu as pas tout pris », `xFnFjopAzz8 @ 01:52:14`). On **ré-affine** l'OB sur le reste non consommé :
- `reste ≥ 0.45 × ATR233` → l'OB **survit** comme zone résiduelle ré-affinée (`@ 01:53:18`).
- `reste < 0.45 × ATR233` → « **il y a plus rien** » → mort de fait (`@ 01:53:41`).
- (0.45 ATR233 = même seuil que la validité FVG §1.4 → cohérent.)

**(c) Mort par traversée** : l'OB est consommé/désactivé quand une bougie **CLÔTURE au-delà du bord lointain** de la zone (ré-affinée). **R10 tranché (clôture vs mèche, 2026-06-18)** : seule la **clôture** consomme — une **mèche** qui dépasse le bord lointain mais dont la **clôture revient dans la zone** = **rejet = réaction** → la zone tient ; une **clôture** au-delà = traversée = mort. Canon : « la clôture prime » (`yiy47FOMIOk @ 00:12:33`) + mèche de rejet (`FQO8F7WmlGY @ 00:18:42`). Cohérent avec (b) : une clôture au-delà du bord lointain ⇒ reste = 0 < 0.45 ATR233. Source mort : `FQO8F7WmlGY @ 00:10:39` + `@ 00:11:08`. *(Proxy minimal assumé : ne capture pas le CHoCH TF inférieur ni la « réaction nette » de l'usage confirmation-d'entrée.)*

**(d) Re-tradabilité du reste** : un OB entamé est « testé, point bar » → **plus une entrée propre** tant qu'il n'y a pas de **re-légitimation par un double cassage de structure (1-2)**, qui rouvre un retest du reste si `reste ≥ 0.45 ATR233` (`xFnFjopAzz8 @ 01:51:48`, `@ 01:54:18`). Formalisation du gating à préciser (cf. R11).

**Symétrie** : (b), (c), (d) sont **neutres de sens** (formulés en « zone »/« OB ») → symétriques par construction. Seule (a) a une symétrie bear **inférée** (R12).

### T2 — OB + Imbalance ✅ / 🟦 (zone grise = décision humaine)
**Pré-condition** : l'impulsion crée une **FVG valide** (§1.4). Sinon → pas un T2.
**Bougie de départ** `d` = bougie impulsion du FVG (la `i−1` du triplet). Mesure `body_d` (en ATR233) :
- `body_d < 0.30` **ou** pas de vrai corps (§1.3) sur les 2–3 dernières → **pas d'OB**. *(D3 — borne basse 0.30 **sourcée** : « le corps […] fait 0,3 ATR minimum pour constituer un order bloc d'origine. J'ai 0,24. Donc […] pas assez épais → pas d'order bloc », `7S_Iovunj20 @ 01:05:17`. Tension résiduelle : un seuil voisin ~0.5 ATR (« pas même 1 demi-cm » → prendre la bougie dessous, `0OeOoBj-Hb0 @ 00:47:47`) concerne un **fallback distinct**, cf. R9.)*
- `0.30 ≤ body_d ≤ 0.63` → **OB = la bougie `d`**, tracé = **son corps** `[body_low_d, body_high_d]`.
- `body_d > 0.65` → impulsion trop violente → **OB = la FVG** (§1.4), tracé = la boîte FVG. **R4 tranché (2026-06-18)** : cas standard = la FVG de l'impulsion ; si **plusieurs FVG superposées** (« deux FVG » de Garry), prendre **la plus profonde dans le sens du swing** — haussier → la plus **basse**, baissier → la plus **haute** (« pas la plus haute » au sens naïf) — sourcé `be0adcdA7lw @ 01:05:08`. *(Fusion assumée : appliquer ce critère au déclencheur corps>0,65 de `FQO8F7WmlGY @ 00:03:47` est déductif, non verbatim Garry. Cas > 2 FVG non couvert par le canon.)*
- `0.63 < body_d ≤ 0.65` → **ZONE GRISE** → arbitrage multi-TF (§T2-bis).

#### T2-bis — Arbitrage de la zone grise ]0.63 ; 0.65] 🟦 (convention humaine, HORS vault)
La doctrine Garry laisse ce choix **discrétionnaire** : « entre les deux c'est ce que j'appelle une zone grise… de temps en temps c'est la zone d'OB, de temps en temps celle dessous » (`FFxKFvuYxrM @ 00:11:18`). Le vault ne donne **aucun** critère codable (dig épuisé : concepts + transcripts + PDF). La règle ci-dessous est une **décision de doctrine humaine assumée** (2026-06-18), pas une transcription :
1. Repérer la **même zone OB** `d` sur les deux demi-temps voisins : **TF+1** et **TF−1** (cascade demi-paliers).
2. Sur chacun, mesurer le corps de la bougie OB correspondante en **ATR233 propre à ce TF** : `body_{+1}`, `body_{−1}`.
3. Un voisin « se rapproche de 0.63 » ssi son corps ∈ **[0.61, 0.65]** (marge ±0.02).
4. Décision :
   - **≥1 voisin proche** (`body_{+1} ∈ [0.61,0.65]` **OU** `body_{−1} ∈ [0.61,0.65]`) → cutoff **strict 0.63** → `d` rejetée → **OB = la FVG** (comme `> 0.65`).
   - **aucun voisin proche** → tolérance étendue à **0.65** → **OB = la bougie `d`** (corps), comme le cas `≤ 0.63`.
5. Cas limite (TF+1 ou TF−1 indisponible : bord de données / pas de zone correspondante) → le **voisin manquant compte comme « non-proche »** (décision humaine 2026-06-18). Conséquence : si les deux voisins sont indisponibles → « aucun voisin proche » → tolérance 0.65.

### T3 — Zone S/D (offre/demande) ✅ (D1 corrigé : englobement mèche comprise)
**Algorithme** : couple `(A, B)` consécutif, `B` juste après `A`.
1. `body_A ≥ 0.75 × ATR233`.
2. **Englobement mèche comprise (canon Garry)** : `B` de couleur opposée à `A`, et la **clôture de `B` dépasse l'extrême-mèche opposé de `A`** :
   - `A` bear, `B` bull → `C_B > H_A` (clôture de B au-dessus du **haut, mèche comprise**, de A).
   - `A` bull, `B` bear → `C_B < L_A` (clôture de B sous le **bas, mèche comprise**, de A).
   Plus strict que l'engulfing SMC corps-sur-corps — source : `bougie_englobante_cloture_canon`, vidéo `6AyQ-UFocFg @ 00:01:21` (« la bougie englobante doit clôturer au-dessus du plus haut de la mèche ») et `@ 00:02:20` pour le supply. **Remplace l'ancien critère corps-sur-corps (D1).**
3. **Type** : `A` bull avalée → **zone d'offre** (vente) ; `A` bear avalée → **zone de demande** (achat).
4. **Zone** = corps de `A` : `[body_low_A, body_high_A]`.

### T4 — Base d'Accélération (ABA) ✅ (T4 officialisé : seuil 0.30 sourcé, source unique)
**Séquence** : `accél_in → base → accél_out`.
- **Bougie de base** : `body ≤ 0.30 × ATR233` ✅ **sourcé** : « pour qu'on considère une ABA, le corps ne doit pas dépasser 0,3 ATR » (`bXSNlOQ-h3c @ 01:38:21`). ⚠️ Réserve : source **unique**, transcription bruitée, contexte TF mensuel → à reconfirmer/calibrer (cf. R5). **ET** mèche longue des **deux** côtés (`upper_wick/range ≥ 0.50` ET `lower_wick/range ≥ 0.50`).
- **Base** = **1 à 3** bougies de base consécutives (corrigé 5→3 au canon : `aba.md` « 1, 2 ou 3 bougies — au-delà, ce n'est plus une base » ; params `aba_base_bougies_min=1` / `max=3`).
- **Bougie d'accél** : `body > 0.30 × ATR233` (complément du seuil base, même source).
- **Validation `accél_out`** (verrouillé) : sa clôture franchit l'extrême de la base — bull : `close > base_high` ; bear : `close < base_low`.
- **Zone** = `[min(L) de la base, max(H) de la base]`, **mèches incluses**.

### T5 — Wick Block 🟡 (à valider sur chart)
**Algorithme** : 1 à 2 bougies à mèche longue (§1.7) côté du rejet.
- **Bull** (mèches **basses** longues) : `bottom = min(L₁, L₂)`, `top = min(body_low₁, body_low₂)`.
- **Bear** (mèches **hautes** longues) : `top = max(H₁, H₂)`, `bottom = max(body_high₁, body_high₂)`.
- Cas 1 bougie (dégénéré) : bull `bottom = L`, `top = body_low` ; bear `top = H`, `bottom = body_high`.
🟡 Tracé verrouillé **par défaut**, seul point que le décideur confirme à l'œil (vidéo contradictoire).

---

## §3 — Arbitrage multi-TF (qui gagne)

### 3.1 Détection multi-TF ✅
Les 5 types sont détectés sur **Large / Moyen / Court** (ebook p11). Chaque zone porte son **TF d'origine**.

### 3.2 Force d'une zone — POINTEUR vers le modèle de force 🟦 (R7 résolu 2026-06-18)
**La spec OB ne possède PAS le modèle de force.** Source de vérité : `ressources/data-wiki/concepts/force-energie.md` (canon) + `ressources/scripts/cartographie.py` (implémentation de référence). Ce §3.2 ne fait que **pointer** et lister les dégradations vérifiées au texte vidéo. L'ancien compteur « `force − nb cassures internes` / −1 par jeu interne » est **retiré** : non sourcé (le canon donne des dégradations **conditionnelles hétérogènes**, pas un compte).

**Cadre canon (vérifié transcripts) :**
- `force_origine` = rang du TF d'origine dans la cascade **demi-paliers** (M1=0 … W1=11), relatif au TF tradé. Chaque « fois de force » = **−2 demi-paliers** (force-energie.md).
- **Comparaison décisive** : `force_courante < force_zone` → la zone **tient** (rebond) ; `≥` → elle **casse** (`WO1gp3sk5U0 @ 00:26:00` / `@ 00:26:59`).
- `force_courante` = `swing_tf` + (+2 demi-paliers/cassage, **plafond 2**) − (**÷2** si fausse cassure) − dégradations.
- **Contre-swing** : conditionne la cascade — absent → rebond au TF courant ; présent (**≥ ~1 cm ≈ 1 ATR**, `WO1gp3sk5U0 @ 00:44:27`) → cascade jusqu'à TF+2 (`@ 00:43:17` / `@ 00:47:55`) ; **absent = −1** (`24tpbSEAXeA @ 01:16:26`) ; cherchable sur un demi-TF inférieur (`@ 00:48:09`). ⚠️ Le vault ne pose PAS « contre-swing = force_courante » (déduction, cf. R13).

**Table des dégradations (vérifiées verbatim) — remplace le compteur non sourcé :**

| Configuration | Quantum | Condition | Source (vérifiée) | Câblé `cartographie.py` |
|---|---|---|---|---|
| Polarité OB d'origine | +1 positive / −2 négative | Convention A | force-energie §4.4 | ✅ `polarite` |
| Liquidité sous le 1er swing | −1 | — | force-energie | ✅ `liquidite_sous_swing1` |
| Zone sur zone (même TF) | −1 | la zone du dessus devient « visible » = liquidité | `NOAGAfn5VhQ @ 00:07:17` | ✅ `zone_sur_zone` |
| Zone avant l'OB d'origine | **−1 temps** (= −2 demi-paliers) | FVG exceptée | `24tpbSEAXeA @ 00:30:18` | ⚠️ code applique −1 brut (incohérence, R13) |
| Liquidité avant la liquidité (jeu interne) | −1 | cible intermédiaire + liquidité au-delà + jeu interne | `ufdWzL2kXUY @ 00:07:36` | ❌ manquant |
| Liquidité au-dessus de la zone | −1 | **seulement si force ≥** (plus faible ne compte pas) | `WO1gp3sk5U0 @ 00:42:03` / `@ 02:01:55` | ❌ manquant |
| Grosse zone épaisse | −2 | seuils ATR (2 vidéos divergent — non tranché, R13) | `WO1gp3sk5U0 @ 00:41:54` | ❌ différé Phase 2 |
| Contre-swing absent | −1 | swing « né de rien » | `24tpbSEAXeA @ 01:16:26` | ❌ manquant |
| Fausse cassure | **÷2** (la moitié) | jeu interne | `FFxKFvuYxrM @ 00:55:54` | (cf. force-energie) |

Comptage canon : **pas de cumul automatique** par liquidité successive — lire la structure sur 2 cassages (`6eL9OUdSc94 @ 00:29:45`) ; `force ∈ [0, 11]` ; plafond **+2 sur les cassages uniquement** ; « en cas de doute, **sous-estimer** la force » (`7S_Iovunj20 @ 00:19:24`).

### 3.3 Résolution (zones concurrentes) ✅ (corrigé 2026-06-18)
Pour des zones concurrentes sur le chemin du prix :
- **Forces effectives différentes** → la **plus forte gagne** : devant, le prix s'y arrête (n'atteint pas la plus faible derrière) ; derrière, elle **aimante** et casse la plus faible devant.
- **Forces effectives égales** → **NO-TRADE** (« +3 contre un +3 […] on ne sait pas où veut aller le marché », `HvbI6rA95tk`) ; à force égale, **« le premier à taper l'OB d'origine gagne »** (séquentialité, force-energie §6). **Corrigé** : l'ancienne formulation « la plus profonde gagne » n'est **pas sourcée**.
- Deux jeux indépendants ne se retrouvent **jamais** au même niveau (`Gh_CK4kJ-iQ`), sauf natures différentes (FVG + base accélération).

(Mapping des 7 cas → cf. [[ob-hierarchy-arbitration]].)

---

## §4 — Registre des points NON fermés (à trancher en relecture)

| # | Point | Statut |
|---|---|---|
| R1 | Rôle exact de `noise = 0.5` (§1.3) | ⚠️ hypothèse `body ≥ 0.5×range` |
| R2 | BoS externe vs interne pour l'impulsion (§1.5) | ⚠️ défaut = dernier pivot 2/2 |
| R3 | Cycle de vie OB (mitigation/mort) | 🟦 résolu 2026-06-18 — modèle du « reste » (§T1-bis) |
| R4 | T2 « première des deux FVG » multi-gap (§T2) | 🟦 tranché 2026-06-18 : FVG la plus profonde dans le sens du swing (`be0adcdA7lw@01:05:08`), fusion assumée |
| R5 | T4 corps base/accél `≤/>` 0.30 ATR233 (§T4) | ✅ sourcé `bXSNlOQ-h3c @ 01:38:21` — source unique/bruitée, reconfirmer/calibrer |
| R6 | T5 tracé du gap (§T5) | 🟡 à valider visuellement |
| R7 | Modèle de force / « −1 par jeu interne » (§3.2) | 🟦 résolu 2026-06-18 : §3.2 = pointeur vers `force-energie.md` + table dégradations vérifiées (compteur non sourcé retiré) |
| R8 | Zone grise (§T2-bis) : voisin TF+1/TF−1 indisponible | 🟦 tranché 2026-06-18 : voisin manquant = « non-proche » |
| R9 | Seuil bas OB : 0.30 « pas d'OB » vs ~0.5 « prendre la bougie dessous » (§T2) | ⚠️ deux seuils voisins sourcés — fallback distinct à clarifier |
| R10 | « traversé sans réaction » (§T1-bis c) | 🟦 tranché 2026-06-18 : proxy clôture-vs-mèche (mèche = rejet, clôture au-delà = mort) |
| R11 | Re-tradabilité du reste (§T1-bis d) : gating par double cassage 1-2 | ⚠️ à formaliser (détection vs Phase 2 entrée) |
| R12 | Symétrie bear de la règle clôture-au-delà-mèche (§T1-bis a) | 🟦 tranché 2026-06-18 : inférence adoptée (bear actif), non sourcée |
| R13 | Modèle de force — points ouverts (§3.2) : contre-swing↔force_courante (déduction), seuils ATR épaisseur (2 vidéos divergent), quantum zone-avant-OB (−1 brut code vs −1 temps vault) | ⚠️ DÉFÉRÉ au sous-système `force-energie.md` / `cartographie.py` (hors spec OB) |

> Note : le dig 2026-06-18 (cf. mémoire `ob-spec-vs-vault-confrontation`) a officialisé D1, D2, D3, T4, **R3** (cycle de vie OB, §T1-bis) et **R10** (clôture-vs-mèche). Restent ouverts : R1, R2, R6 (historiques) + R9, R11 (bords flous issus du dig) + R13 (modèle de force, déféré au sous-système).

## §5 — Testabilité
Chaque détecteur reste une fonction pure `(série OHLC, ATR233) → liste de zones {type, side, top, bottom, bar_origine, TF}`. **Exception D2** : l'arbitrage de la zone grise (§T2-bis) introduit une **dépendance multi-TF** — la fonction T2 doit recevoir, pour la zone candidate, le corps mesuré sur TF+1 et TF−1 (ou un accès aux séries voisines). Déterministe ⇒ rejouable barre par barre, vérifiable sur replay TradingView. Les points R1–R13 sont les seuls degrés de liberté ; tout le reste est figé.
