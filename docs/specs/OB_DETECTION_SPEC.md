# Spec déterministe — Détection des 5 types d'Order Block

> Étalon : doctrine verrouillée le 2026-06-17 (vidéo Garry + ebook G-ON + Pine v19 attestée).
> Objectif de ce document : **vérifier** que chaque type est entièrement déterministe et testable.
> Légende statut : ✅ déterministe & sourcé · 🟦 décision/convention humaine assumée (tranchée au-delà du vault) · ⚠️ hypothèse de travail (source muette, à confirmer) · 🟡 à valider visuellement · 🔴 seuil non sourcé à calibrer.
> **Aucune règle ci-dessous n'est inventée** : tout pointe vers une source ou est marqué comme hypothèse explicite.
>
> **Révision 2026-06-18** (après confrontation vidéo + ebook, cf. mémoire `ob-spec-vs-vault-confrontation`) :
> - **D1 — §T3 corrigé au canon** : l'englobement S/D passe de « corps-sur-corps » à **mèche comprise** (clôture de l'englobante au-delà de l'extrême-mèche opposé), conforme à `6AyQ-UFocFg @ 00:01:21`.
> - **D2 — §T2 : la zone grise est tranchée** par une **convention de doctrine humaine** (la vidéo la déclare discrétionnaire — « zone grise », `FFxKFvuYxrM @ 00:11:18`). Cette convention est marquée 🟦 = décision humaine assumée, HORS vault.
> - **D3 + T4 officialisés** : les seuils 0.30 (borne basse OB §T2 ; corps de base ABA §T4), jusque-là non sourcés/inférés, sont désormais **sourcés** par le dig (`7S_Iovunj20 @ 01:05:17` et `bXSNlOQ-h3c @ 01:38:21`). Correction annexe : base ABA `1 à 5` → **`1 à 3`** bougies (canon `aba.md`).
> - **R3 tranché — cycle de vie OB (§T1-bis)** : la convention non sourcée `close </> bord` est remplacée par le **modèle du « reste »** (épaisseur résiduelle ≥ 0.45 ATR233 = vivant ; traversé sans réaction = mort ; re-légitimation par double cassage). Citations vérifiées à la main. Bords flous restants tracés en R11–R12.
> - **R10 tranché — « sans réaction » = clôture vs mèche (§T1-bis c)** : seule une **clôture** au-delà du bord lointain consomme/tue l'OB ; une **mèche** qui dépasse mais clôture revenue dans la zone = rejet = la zone tient. Canon « la clôture prime ».
>
> **Révision 2026-06-18/19 (suite)** : **R1·R2·R4·R5·R6·R7·R9·R11·R12·R13** également tranchés/résolus côté doctrine. Confrontation au canon **bouclée** — voir le **registre §4** pour l'état complet. Ne restent NON-doctrinaux : R6 (géométrie fine du gap → visuel TV), inférences à valider (morphologie base §T4), câblage force (`cartographie.py`).

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

### 1.3 Filtre « bruit » / vrai corps ✅ (R1 tranché 2026-06-18)
L'ancienne hypothèse « vrai corps = `body ≥ 0.5 × range` » était **NON sourcée** (mauvaise lecture de la constante Pine `noise=0.5`). Le canon donne **deux** critères sourcés, distincts :
- **Bruit (canon, immuable)** : une bougie dont l'**amplitude `range < 0.5 × ATR233`** est du **bruit, à ignorer** (`atr#atr_bruit_threshold`, `lxSpGEk1Ec4 @ 00:01:43` : « Moins de 0,5 ATR, ce sera que du bruit »). C'est ce à quoi correspond `noise=0.5` du Pine — un **seuil d'amplitude**, pas un ratio corps/range.
- **« Corps exploitable » (garde-fou T2 « FVG vide »)** : qualitatif chez Garry (`FQO8F7WmlGY @ 00:04:09` : « le corps est vraiment petit […] aucun corps exploitable → la FVG est vide → pas d'OB »), opérationnalisé via le plancher de corps OB **`corps < 0.30 ATR233`** (§T2 / D3) : si les 2–3 dernières bougies n'ont aucun corps ≥ 0.30 ATR → FVG vide → pas d'OB.

### 1.4 FVG (Fair Value Gap, 3 bougies) ✅
Sur le triplet `(i−2, i−1, i)`, la bougie `i−1` est l'impulsion, `i−2`/`i` l'encadrent :
- **FVG haussière** : `gap = L[i] − H[i−2]` ; valide si `gap ≥ 0.45 × ATR233`.
- **FVG baissière** : `gap = L[i−2] − H[i]` ; valide si `gap ≥ 0.45 × ATR233`.
Zone FVG = `[H[i−2], L[i]]` (bull) / `[H[i], L[i−2]]` (bear). Source : ebook p7/p17.

### 1.5 BoS (Break of Structure) ✅ (R2 tranché 2026-06-18 : externe, sur corps)
`P_high` = dernier pivot_high 2/2 confirmé ; `P_low` = dernier pivot_low 2/2 confirmé.
- **BoS haussier** : `close > P_high`.
- **BoS baissier** : `close < P_low`.
**R2 tranché** : le BoS qui valide l'impulsion (donc l'OB) est le **BoS EXTERNE** — la 2e cassure d'un swing **majeur**, le « 2 » après le CHoCH (`jevVat55Svg @ 00:28:27`, vérifié : « Choche + cassage externe. Une fois, deux fois → identification de l'order block »). Le **BoS interne** (creux local, « mouvement mineur qui ne change pas la tendance », `bos_interne_definition`) **ne valide pas**. La cassure doit être **bâtie sur des corps clôturés**, pas des mèches/sweeps (`yiy47FOMIOk @ 00:12:33` ; `mpkBAJCdkgs @ 01:16:03`) — mèche seule = fausse cassure (énergie ÷2, cf. §3.2). Aligné `cartographie.py` (exclut `BOS_INTERNE` de la construction séquence/OB). *(Déduction forte : le vault associe toujours la validation d'OB au cassage externe, sans écrire littéralement l'exclusion de l'interne.)*

### 1.6 Impulsion ✅ (VERROUILLÉ)
Un mouvement est **impulsif** ssi il **casse la structure (BoS externe, §1.5 / R2) OU laisse une FVG valide (§1.4)**.
Socle des 5 types. Rejeté : `1.5×ATR14` (proxy code), `≥3 ATR233 / 5 bougies` (= grande impulsion scénario D seulement).

### 1.7 Mèche longue ✅ (unifié 2026-06-19)
Bougie à **mèche longue côté `X`** (`X` = upper ou lower) ssi **`X_wick > body`** (la mèche dépasse le corps). Critère canon « petit corps + longue mèche » (`qCAdx5LIcL0 @ 00:13:03`, `ejjGH70rhbA @ 00:16:57`), applicable **à un côté** (T5 wick block) ou **aux deux** (T4 base ABA — `upper_wick > body` ET `lower_wick > body`). *Subsume l'ancien `X_wick/range ≥ 0.50` (Pine v19) : pour une bougie à mèche dominante d'un seul côté, `wick > body ⟺ wick/range ≳ 0.50` ; et `≥0.50 des deux côtés` était impossible (somme > range).*

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

**(d) Re-tradabilité du reste — machine à états (R11 tranché 2026-06-18)** : la **détection SUIT l'état** de l'OB ; l'**acte d'entrée est Phase 2**. États : `frais` → `testé/mitigé` (entamé : « testé, point bar » → plus une entrée propre) → `re-légitimé` **ssi** un **double cassage de structure 1-2** (réutilise le BoS externe §1.5) **ET** `reste ≥ 0.45 ATR233` après ré-affinage → de nouveau jouable ; à défaut → `mort` (cf. c). Sources `xFnFjopAzz8 @ 01:51:48`, `@ 01:54:18`, `@ 02:22:29` (vérifiées). **La détection émet l'état ; Phase 2 décide d'entrer.**

**Symétrie** : (b), (c), (d) sont **neutres de sens** (formulés en « zone »/« OB ») → symétriques par construction. Seule (a) a une symétrie bear **inférée** (R12).

### T2 — OB + Imbalance ✅ / 🟦 (zone grise = décision humaine)
**Pré-condition** : l'impulsion crée une **FVG valide** (§1.4). Sinon → pas un T2.
**Bougie de départ** `d` = bougie impulsion du FVG (la `i−1` du triplet). Mesure `body_d` (en ATR233) :
- `body_d < 0.30` **ou** pas de vrai corps (§1.3) sur les 2–3 dernières → **pas d'OB**. *(D3 — borne basse 0.30 **sourcée** : « le corps […] fait 0,3 ATR minimum pour constituer un order bloc d'origine. J'ai 0,24. Donc […] pas assez épais → pas d'order bloc », `7S_Iovunj20 @ 01:05:17`. **R9 tranché (2026-06-18)** : le seuil voisin ~0,5 (« OB microscopique », `0OeOoBj-Hb0 @ 00:47:47`) est une **règle DISTINCTE**, pas « pas d'OB » — c'est une règle de **placement (Phase 2)** : si l'OB retenu est microscopique (**< ~0,5 ATR** ; forme portable — « 1 ATR ≈ 1 cm » `IwszbzgyK9M @ 00:24:23` est la calibration zoom de Garry, non portable en code), élargir la zone de référence à la **bougie complète dessous** (SL/entrée). L'OB existe toujours ; seule sa référence change.)*
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

### T4 — Base d'Accélération (ABA) ✅ (R5 tranché 2026-06-19 : base = morphologie canon, sans chiffre)
**Séquence** : `accél_in → base → accél_out`.
- **Bougie de base** — **morphologie canon, sans chiffre** : **petit corps + mèche longue (§1.7) des DEUX côtés** (`upper_wick > body` **ET** `lower_wick > body`), canon `qCAdx5LIcL0 @ 00:13:03` / `ejjGH70rhbA @ 00:16:57`. *(Inférence assumée : le canon donne le qualitatif « petit corps longue mèche », pas la formule — cf. §1.7 unifié.)* *(Le `body ≤ 0.30 ATR` n'est **PAS** dans le canon distillé — `aba.md` laisse le seuil en placeholder ; unique source garbled sans ATR `bXSNlOQ-h3c @ 01:38:21` → retiré du critère, conservé en proxy tunable optionnel.)*
- **Base** = **1 à 3** bougies de base consécutives (canon `aba.md` ; au-delà, ce n'est plus une base).
- **Morphologie typique** (indicative, **non requise**) : séquence **baissière→haussière** (bull) / haussière→baissière (bear) — `ejjGH70rhbA @ 05:28:59` (1 passage, contexte ABA imbriqué).
- **Bougie d'accél** : bougie **impulsive** (§1.6) encadrant la base (l'ancien `body > 0.30 ATR` partageait le proxy garbled → hors canon).
- **Validation `accél_out`** (verrouillé) : sa clôture franchit l'extrême de la base — bull : `close > base_high` ; bear : `close < base_low`.
- **Zone** = `[min(L) de la base, max(H) de la base]`, **mèches incluses**.

### T5 — Wick Block 🟡 (R6 : inter-mèches ; géométrie exacte à valider)
**Définition canon** (`FQO8F7WmlGY @ 00:09:07` & `@ 00:12:42` ; `NSs7Sa8VTSI @ 02:26:41` ; `order-block.md#4`) : **deux** bougies à énorme mèche dont l'**écart entre les mèches** forme la zone — « s'il y a un **écart entre deux mèches**, alors c'est un wick block ». Insistance canon : « **la vraie lecture n'est PAS dans le corps mais dans l'espace laissé entre les deux mèches** » → **le corps ne définit PAS la zone**.
**Algorithme** : **2 bougies** à mèche longue (§1.7) côté du rejet — une mèche **seule** « peut ne rien être » (`NSs7Sa8VTSI @ 02:26:41`) → exclue. Zone = le **gap entre les deux mèches** : bull → côté des **bas** des deux mèches ; bear → côté des **hauts** des deux mèches.
🟡 **R6 tranché (2026-06-18)** : zone = **inter-mèches** (corrigé — l'ancien tracé `top = body_low` utilisait le **corps**, NON canon). Les **bords géométriques exacts** du gap restent ambigus dans le canon (« entre les bas » vs « entre les hauts et les bas des deux mèches ») → **validation visuelle TV déférée** (seul point où le visuel lève une ambiguïté que le texte ne lève pas).

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
- **Contre-swing** — deux effets distincts (vérifiés à la main dans les transcripts) :
  - **(portée du mouvement)** absent (descente directe) → portée au **même temps** (`24tpbSEAXeA @ 00:47:55` : « de H2 H2 s'il y a pas de contre-swing ») ; présent (descente en escalier, **≥ ~1 cm ≈ 1 ATR**, `WO1gp3sk5U0 @ 00:44:27`) → portée à **+1 temps (= +2 demi-paliers)**, PAS +2 temps (`24tpbSEAXeA @ 00:48:00` : « … on va jusqu'à H8 »). Le contre-swing est cherchable sur un **demi-TF inférieur** (`24tpbSEAXeA @ 00:48:14`).
  - **(dégradation)** son **absence = −1** (swing « né de rien », `24tpbSEAXeA @ 01:16:26`).
  - Le contre-swing n'est PAS « = force_courante » : il en est le **constructeur** via l'escalier de cassages (R13(d) clarifié), pas l'égal. Seuil canon = swing **1 à 1,5 temps inférieur** (R13(b) : « moitié du swing » ↔ « ~1 cm » = deux bornes).
- **Exemples chiffrés vérifiés** (lecture directe transcripts) : (1) `ufdWzL2kXUY @ 00:06:07-07:55` — D1 −3 fois (zone qui absorbe −1, liquidité-avant-liquidité jeu interne −1, séquence 1-2 visible −1) = **M15**, recoupé bottom-up H4 −2 = M15 ; (2) `WO1gp3sk5U0 @ 00:41:38-42:42` — H8 −3 fois (zone **très** épaisse −2, liquidité au-dessus −1) = **M8**. **Arithmétique canon (vérifiée lecture directe)** : « on descend d'un temps, **on saute de demi-temps**. Donc ça fait H4, H1, M15 » (`6eL9OUdSc94 @ 00:43:18`) — Garry rejette le comptage en demi-temps (« H2 c'est pas possible »). Donc **1 fois de force = 1 temps = 2 demi-paliers**, échelle de comptage **D1·H4·H1·M15** (les noms H8/H2/M30 sont les crans *sautés*, pas un 2ᵉ système). ⚠️ Les exemples PARLÉS contiennent des lapsus de comptage de Garry lui-même (ex. `6eL9OUdSc94 @ 00:44:49` dit « M15 car deux fois » alors que sa propre échelle donne 3) — se fier à la RÈGLE, pas au décompte oral d'un exemple.

**Table des dégradations (vérifiées verbatim) — remplace le compteur non sourcé :**

| Configuration | Quantum | Condition | Source (vérifiée) | Câblé `cartographie.py` |
|---|---|---|---|---|
| Polarité OB d'origine | +1 positive / −2 négative | Convention A | force-energie §4.4 | ✅ `polarite` |
| Liquidité sous le 1er swing | −1 | — | force-energie | ✅ `liquidite_sous_swing1` |
| Zone sur zone (même TF) | −1 | la zone du dessus devient « visible » = liquidité | `NOAGAfn5VhQ @ 00:07:17` | ✅ `zone_sur_zone` |
| Zone avant l'OB d'origine | **−1 temps** (= −2 demi-paliers) | FVG exceptée | `24tpbSEAXeA @ 00:30:18` | ✅ code `−1` = −1 fois = −2 demi-paliers (R13(e) : **cohérent**, pas une incohérence) |
| Liquidité avant la liquidité (jeu interne) | −1 | cible intermédiaire + liquidité au-delà + jeu interne | `ufdWzL2kXUY @ 00:07:36` | ❌ manquant |
| Liquidité au-dessus de la zone | −1 | **seulement si force ≥** (plus faible ne compte pas) | `WO1gp3sk5U0 @ 00:42:03` / `@ 02:01:55` | ❌ manquant |
| Zone **épaisse** | **+1 (bonus masse) → net ~0** | « jeu d'un temps au-dessus » ; compense une dégradation (`WO1gp3sk5U0 @ 00:29:32` : « zéro force si vous êtes une zone épaisse ») | `WO1gp3sk5U0 @ 00:29:32` / `24tpbSEAXeA @ 01:13:19` | ❌ différé Phase 2 |
| Zone **TRÈS épaisse** | **−2** | ≥ ~2,7 ATR (seuil `WO1gp3sk5U0` ; absent de `24tpbSEAXeA` — R13) | `WO1gp3sk5U0 @ 00:36:22` / exemple `@ 00:41:54` | ❌ différé Phase 2 |
| Contre-swing absent | −1 | swing « né de rien » | `24tpbSEAXeA @ 01:16:26` | ❌ manquant |
| Fausse cassure | **÷2** (la moitié) | jeu interne | `FFxKFvuYxrM @ 00:55:54` | (cf. force-energie) |

Comptage canon : **pas de cumul automatique** par liquidité successive — lire la structure sur 2 cassages (`6eL9OUdSc94 @ 00:29:45`) ; `force ∈ [0, 11]` ; plafond **+2 sur les cassages uniquement** ; « en cas de doute, **sous-estimer** la force » (`7S_Iovunj20 @ 00:19:24`).

### 3.3 Résolution (zones concurrentes) ✅ (corrigé 2026-06-18)
Pour des zones concurrentes sur le chemin du prix :
- **Forces effectives différentes** → la **plus forte gagne** : devant, le prix s'y arrête (n'atteint pas la plus faible derrière) ; derrière, elle **aimante** et casse la plus faible devant.
- **Forces effectives égales** → **NO-TRADE** (« +3 contre un +3 […] on ne sait pas où veut aller le marché », `HvbI6rA95tk @ 03:26:55`). À force égale, l'ordre de sélection le plus proche sourcé est **« premier POI rencontré dans le sens de marche »** (`poi.md#poi_premier_rencontre_dans_le_sens`, **sans timestamp Garry** → canon-faible). ⚠️ Ni « la plus profonde gagne » (formulation initiale) ni « le premier à taper l'OB d'origine gagne » (1ʳᵉ correction) ne sont sourcés verbatim — R13.
- Deux jeux indépendants ne se retrouvent **jamais** au même niveau (`Gh_CK4kJ-iQ`), sauf natures différentes (FVG + base accélération).

(Mapping des 7 cas → cf. [[ob-hierarchy-arbitration]].)

---

## §4 — Registre des points NON fermés (à trancher en relecture)

| # | Point | Statut |
|---|---|---|
| R1 | `noise = 0.5` / vrai corps (§1.3) | 🟦 tranché 2026-06-18 : hypothèse `body≥0.5×range` NON sourcée ; canon = bruit si `range < 0.5 ATR` (`lxSpGEk1Ec4@00:01:43`) + corps exploitable via plancher 0.30 ATR |
| R2 | BoS externe vs interne pour l'impulsion (§1.5) | 🟦 tranché 2026-06-18 : BoS EXTERNE requis, sur corps (`jevVat55Svg@00:28:27`) ; interne ne valide pas |
| R3 | Cycle de vie OB (mitigation/mort) | 🟦 résolu 2026-06-18 — modèle du « reste » (§T1-bis) |
| R4 | T2 « première des deux FVG » multi-gap (§T2) | 🟦 tranché 2026-06-18 : FVG la plus profonde dans le sens du swing (`be0adcdA7lw@01:05:08`), fusion assumée |
| R5 | Base ABA — corps (§T4) | 🟦 tranché 2026-06-19 : canon = morphologie qualitative (petit corps + longues mèches deux côtés) ; opérationnalisé `body < chaque mèche` (inférence) ; `0.30 ATR` PAS dans le canon distillé (proxy garbled `bXSNlOQ-h3c`, retiré du critère). Corrige aussi l'ancien critère mèche impossible (somme>range) |
| R6 | T5 tracé du wick block (§T5) | 🟦/🟡 R6 2026-06-18 : zone = inter-mèches (corps exclu, canon `FQO8F7WmlGY@00:09`) ; bords exacts du gap → validation visuelle TV déférée |
| R7 | Modèle de force / « −1 par jeu interne » (§3.2) | 🟦 résolu 2026-06-18 : §3.2 = pointeur vers `force-energie.md` + table dégradations vérifiées (compteur non sourcé retiré) |
| R8 | Zone grise (§T2-bis) : voisin TF+1/TF−1 indisponible | 🟦 tranché 2026-06-18 : voisin manquant = « non-proche » |
| R9 | Seuil bas OB : 0.30 « pas d'OB » vs ~0.5 « bougie dessous » (§T2) | 🟦 tranché 2026-06-18 : DEUX règles distinctes — A (0,30 ATR, présence, encodé) ; B (~0,5 ATR, placement Phase 2, OB microscopique → bougie dessous) |
| R10 | « traversé sans réaction » (§T1-bis c) | 🟦 tranché 2026-06-18 : proxy clôture-vs-mèche (mèche = rejet, clôture au-delà = mort) |
| R11 | Re-tradabilité du reste (§T1-bis d) | 🟦 tranché 2026-06-18 : détection suit l'état (machine à états : double cassage 1-2 + reste ≥0,45 → re-légitimé) ; acte d'entrée = Phase 2 |
| R12 | Symétrie bear de la règle clôture-au-delà-mèche (§T1-bis a) | 🟦 tranché 2026-06-18 : inférence adoptée (bear actif), non sourcée |
| R13 | Modèle de force — points ouverts (§3.2). **Arithmétique RÉSOLUE 2026-06-18** : 1 fois = 1 temps = 2 demi-paliers, échelle D1·H4·H1·M15 (`6eL9OUdSc94@00:43:18`). **Creusé 2026-06-19 (lecture directe)** : (c) RÉSOLU — à force égale = **NO-TRADE** (`HvbI6rA95tk@03:27:00` « +3 contre +3, on ne sait pas où va le marché ») → pas de règle de gagnant nécessaire, « premier POI » sans objet ; (e) RÉSOLU — zone-avant-OB « −1 temps » = code « −1 fois » = −2 demi-paliers (artefact d'unité). **(a) RÉSOLU 2026-06-19 via zones S/D** : la catégorie canon **« FINE » = `< 0,75 ATR`** (« rien dedans » → zone invalide ; `supply-demand#zone_epaisseur_min`, `FQO8F7WmlGY@00:05:57` + `29bGrivmwTM@01:51:09` + `6z7KNx5TC1Y@02:27:50`) ancre l'échelle d'épaisseur des zones S/D : **fine `<0,75` | normale `0,75–1,65` | épaisse `1,65–2,7` | très épaisse `≥2,7`** (plancher 0,75 ferme S/D ; paliers hauts = `WO1gp3sk5U0@00:22:22` détaillé ; le « 1,5 » de `24tpbSEAXeA` = cadrage grossier « en moyenne »). **(b) RÉSOLU 2026-06-19 via le swing** : `swing.md#contre_swing_present` unifie déjà — contre-swing = swing valide **1 à 1,5 temps inférieur** au swing principal. Or 1 temps inférieur = ÷2 volatilité (`WO1gp3sk5U0@00:23:58`) = **moitié du swing** (`rwRNzxzzr10@00:08:55`) ; 1,5 temps inférieur ≈ ~1 ATR ≈ **1 cm** (`WO1gp3sk5U0@00:44:27`). Les deux seuils = les **deux bornes** d'un même intervalle, pas deux doctrines. **(d) CLARIFIÉ 2026-06-19** : « contre-swing = force_courante » était une **mauvaise formulation**. Canon : `force_courante` = force du swing qui **ARRIVE / « vient taper »** la zone (`xFnFjopAzz8@00:10:31`), construite via la cascade (swing_tf + cassages) ; le contre-swing en est le **CONSTRUCTEUR** via l'escalier (sans → portée même temps `@00:36:26` ; avec → +1 temps). Relation **builder→résultat, pas identité** — pas de trou. | ✅ **R13 RÉSOLU côté doctrine** (a–e) ; ne reste que le **CÂBLAGE** dans `cartographie.py` (engineering, pas doctrine) |

> Note : confrontation au canon **BOUCLÉE** (2026-06-18/19, cf. mémoire `ob-spec-vs-vault-confrontation`). **D1·D2·D3 et R1–R13 tous tranchés/résolus côté doctrine** — chaque décision sourcée + vérifiée à la main au transcript. Ne restent, tous **NON-doctrinaux** : **R6** (géométrie fine du gap → validation visuelle TV) ; **inférences à valider** (formule morphologie base §T4 `body<mèche`) ; **câblage** du modèle de force dans `cartographie.py` (engineering). Tout 🟡/⚠️ résiduel relève de l'un de ces trois.

## §5 — Testabilité
Chaque détecteur reste une fonction pure `(série OHLC, ATR233) → liste de zones {type, side, top, bottom, bar_origine, TF}`. **Exception D2** : l'arbitrage de la zone grise (§T2-bis) introduit une **dépendance multi-TF** — la fonction T2 doit recevoir, pour la zone candidate, le corps mesuré sur TF+1 et TF−1 (ou un accès aux séries voisines). Déterministe ⇒ rejouable barre par barre, vérifiable sur replay TradingView. **R1–R13 sont tous tranchés/résolus côté doctrine** (cf. §4) ; ne restent ouverts que **R6** (géométrie visuelle), les **inférences à valider** (formule morphologie base) et le **câblage force**. Tout le reste est figé.
