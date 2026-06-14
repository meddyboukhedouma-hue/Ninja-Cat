# ADR-002: La couche canonique ne présuppose aucune stratégie

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: doctrine, schema, config, process

## Context

Le scaffold initial livrait un schéma (`schema.py`) et une config (`config.py`)
déjà engagés dans une famille de stratégie **order-flow / footprint** :
`Bar` avec `delta`, `delta_max/min`, `poc_price`, `poc_position`,
`levels = {prix: (bid_vol, ask_vol)}` ; et des scalaires `imbalance_ratio`,
`volume_spike_mult`, `flip_*`, `sequence_*`, `poc_*`.

Or **aucune stratégie n'a été définie**. Ces primitives présupposaient une
doctrine que personne n'avait choisie — la charrue avant les bœufs. Cela
contredit le flux que le projet se donne (`architect → data-engineer →
implementer`) et la règle de l'architecte : « les primitives requises = la liste
exacte des grandeurs nécessaires, *et seulement celles-là* ». Le choix même d'un
type de barre (temps / tick / volume / dollar) est déjà une décision de
méthodologie (cf. López de Prado, référencé par le `quant-backtest-validator`).

## Decision

La couche canonique est ramenée à la **donnée de marché brute, neutre** vis-à-vis
de toute stratégie :

- `schema.py` : ne conserve que `Trade` (ts, price, size, side) et `Side`.
  `Bar` et tous les champs footprint sont **supprimés**.
- `config.py` : ne conserve que `tick_size` (métadonnée de marché, par-symbole).
  Tous les scalaires de stratégie sont **supprimés**.

Les agrégats (type de barre) et les scalaires de stratégie seront (ré)introduits
**à partir de la spec produite par l'architecte**, une fois une stratégie
choisie par le décideur humain — jamais présupposés en amont.

Périmètre de l'assistant : préparation de l'infrastructure et du workflow
uniquement ; la définition de la stratégie appartient au décideur humain.

## Consequences

### Positive
- Le schéma cesse d'imposer une doctrine non validée ; il découle des specs.
- Aligne le code sur le flux et la discipline d'altitude des agents.
- Élimine du code mort (scalaires/champs sans spec) et un import inutilisé.

### Negative
- Couche canonique très minimale : il faudra (ré)introduire des structures dès
  qu'une stratégie est définie. Coût assumé et volontaire.

### Neutral
- Les agents restent inchangés : ils décrivent la *méthode*, pas une stratégie
  (l'architecte cite l'imbalance seulement comme *exemple* de scalaire
  « conventionnel »).

## Links
- Découle de [ADR-001](ADR-001-verite-donnee-doctrine-moteur.md) : la doctrine
  vit dans le moteur, sous le verdict de la donnée — donc rien n'est doctrine
  tant que ce n'est pas spécifié puis validé.
