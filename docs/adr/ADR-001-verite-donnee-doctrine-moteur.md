# ADR-001: Vérité = donnée de marché ; doctrine = moteur

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: doctrine, architecture, fondation

## Context

Le scaffold initial posait comme principe directeur : « le moteur Python est la
**source unique de vérité** ; les couches d'affichage ne font que rendre ».

Cette formule fusionnait deux idées distinctes — et l'une d'elles est fausse :

1. **« Il y a UN seul endroit où vit la logique de décision. »** Vrai et sain :
   c'est l'anti-duplication, le déterminisme, le « le chart ne fait que rendre ».
2. **« Cet endroit EST la vérité. »** Faux, et dangereux en quant : croire que
   son modèle *est* la vérité est la voie royale vers l'overfitting et
   l'auto-illusion. Un système qui se proclame « la vérité » ne peut pas, par
   construction, être une *aide à la décision* honnête.

Le projet contredisait d'ailleurs déjà lui-même cette formule : l'agent
`quant-backtest-validator` affirme « le juge final, c'est la donnée ». Le mot
« Python » figeait par ailleurs un détail d'implémentation au rang de dogme.

## Decision

On sépare les deux concepts et on réécrit le principe directeur :

> **La donnée de marché est la seule source de vérité.** Le marché tranche,
> toujours.
> **Le moteur est la source unique de _doctrine_** — l'unique endroit,
> déterministe, où s'exprime la logique de décision (jamais dupliquée dans le
> chart, Pine, ou ailleurs). Mais le moteur reste un *modèle*, subordonné en
> permanence au verdict de la donnée.

Conséquences structurelles (architecture hexagonale, ports & adapters) :

- **Cœur** = le moteur (doctrine unique, déterministe, scale-free).
- **Arbitre** = la donnée de marché ; le moteur lui répond via le
  `quant-backtest-validator`.
- **Port entrant (hypothèses)** : toute idée externe — y compris les sorties de
  `neural-trader` / HNSW de ruflo, ou une intuition discrétionnaire — entre
  comme *hypothèse non vérifiée*. Elle ne devient doctrine qu'après transcription
  déterministe par `quant-strategy-architect` puis preuve par le validator.
- **Ports sortants** : le rendu (TradingView, ne fait que dessiner) et la
  mémoire (AgentDB / `claude-flow`, qui range et retrouve ce que le moteur a
  produit — il ne calcule aucune doctrine).

Invariant unique, non négociable : *aucune sortie externe ne devient une
décision sans avoir traversé le moteur et passé le verdict de la donnée.*

Fichiers alignés sur cette décision : `README.md`, `src/ninja_cat/__init__.py`,
`.claude/agents/quant-strategy-architect.md`,
`.claude/agents/quant-viz-verifier.md`.

## Consequences

### Positive
- Doctrine épistémiquement correcte : le modèle est falsifiable, jamais sacralisé.
- Tout ce qui était sain est conservé (logique unique, déterminisme, scale-free,
  chart en simple rendu) — aucun recul de qualité.
- Le conflit avec les plugins trading de ruflo se dissout : ils deviennent des
  générateurs d'hypothèses légitimes, sans jamais court-circuiter la validation.
- Doctrine langage-agnostique : « Python » n'est plus un dogme, juste
  l'implémentation actuelle du moteur.

### Negative
- La couche d'ingestion/qualité de la donnée devient le maillon critique : si
  l'arbitre est faux, tout l'est. Met une pression accrue sur
  `quant-data-engineer` (parité live==replay, détection d'anomalies).

### Neutral
- Le `quant-viz-verifier` compare désormais le rendu à la « référence de
  doctrine » (sortie du moteur) plutôt qu'à « la vérité » ; comportement
  inchangé, vocabulaire corrigé.

## Links
- Future : ADR sur la frontière ruflo (port hypothèses / port mémoire) et le
  `MemoryPort` découplant le moteur d'AgentDB.
