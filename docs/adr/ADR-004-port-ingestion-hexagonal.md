# ADR-004: Port d'ingestion hexagonal (le moteur découplé des exchanges)

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: architecture, ingestion, hexagonal, ccxt, replay

## Context

ADR-002 a neutralisé la couche canonique : `schema.py` ne contient que le
`Trade` brut, neutre vis-à-vis de toute stratégie. ADR-003 a matérialisé le
port mémoire (sortant) en architecture hexagonale, découplant le moteur
d'AgentDB.

Le chemin d'entrée de la donnée manquait son équivalent symétrique : le moteur
ne doit dépendre que d'une interface abstraite pour recevoir des `Trade` — jamais
d'un exchange concret, d'une bibliothèque CCXT, ni d'un format de fichier
particulier. Sans cette frontière, tout test du moteur nécessite un flux live ou
des fixtures couplées à un format d'import — ce qui contredit l'exigence
d'identité live == replay posée par ADR-001.

## Decision

Architecture hexagonale (ports & adapters) pour l'ingestion de données :

- **Port** (`ninja_cat.ingestion`) : `MarketDataPort` (Protocol
  `runtime_checkable`) expose un contrat minimal — `trades()` renvoyant un
  itérable de `Trade` canoniques. Le moteur ne dépend **que** de cette
  interface, jamais d'un adapter concret.
- **Fallback** : `NullSource`, implémentation no-op (aucun trade, jamais
  d'erreur). Équivalent de `NullMemory` côté ingestion ; garantit que le moteur
  tourne identique sans source réelle.
- **Brique replay** : `ReplaySource` rejoue une liste de `Trade` fournie à la
  construction. C'est la fondation de la parité live == replay : développer et
  tester tout le moteur avec des séquences de `Trade` déterministes, sans
  aucun flux live.
- **Fabrique** : `get_source()`, symétrique de `get_memory()` d'ADR-003.
  Retourne `NullSource` par défaut.
- **Invariants du contrat** : ordre chronologique (timestamps monotones
  croissants), absence de doublons — documentés dans l'interface, à garantir
  par les adapters de transport concrets, pas par le port lui-même.
- **Périmètre strict** : transport de `Trade` bruts uniquement. Aucune
  primitive dérivée, aucun agrégat, aucune doctrine. Conforme à ADR-002.

Fichiers matérialisant cette décision : `src/ninja_cat/ingestion.py` (port +
NullSource + ReplaySource + fabrique) et `tests/test_ingestion.py` (26 tests
verts, committés en 8108124).

## Consequences

### Positive
- Le cœur reste pur et testable sans flux live : `ReplaySource` suffit pour
  développer et valider l'ensemble du moteur en isolation.
- Les adapters réels (CCXT live, Parquet historique, CSV…) sont branchables
  sans toucher au cœur — même pattern qu'ADR-003.
- La parité live == replay est architecturalement garantie : les deux chemins
  traversent le même `MarketDataPort`.

### Negative
- Un adapter CCXT concret est délibérément **différé** (YAGNI) : aucun
  consommateur ni stratégie ne consomme encore de `Trade` ; l'écrire maintenant
  serait du code mort.
- Le flux live n'a de sens qu'une fois une stratégie définie par le décideur
  humain (doctrine hors périmètre infra).

### Neutral
- Interface volontairement étroite (une méthode `trades()`) ; elle s'étendra
  si un besoin réel et spécifié apparaît, pas par anticipation.

## Links
- Complète [ADR-003](ADR-003-port-memoire-hexagonal.md) (port mémoire sortant)
  côté donnée entrante : les deux ports encadrent le cœur du moteur.
- Matérialise dans le code la primauté de la donnée de marché posée par
  [ADR-001](ADR-001-verite-donnee-doctrine-moteur.md).
- Respecte la neutralité de la couche canonique d'[ADR-002](ADR-002-couche-canonique-neutre.md) :
  `Trade` brut uniquement, zéro présupposition de stratégie.
