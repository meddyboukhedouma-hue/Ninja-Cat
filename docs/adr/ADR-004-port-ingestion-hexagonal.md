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
  croissants) ; absence de doublons **par identifiant natif** — quand le trade
  expose un id (champ `id` côté ccxt, colonne `id`/`trade_id` côté fichier), la
  déduplication s'effectue sur cet id (couvre le cas pagination/rollover). Sans
  id disponible, **aucune déduplication destructrice** n'est faite (un warning
  est loggé) : le tri garantit la monotonicité mais pas l'unicité — on préfère
  conserver la donnée plutôt que jeter des trades légitimement identiques.
  Garantis par les adapters concrets, pas par le port lui-même.
- **Périmètre strict** : transport de `Trade` bruts uniquement. Aucune
  primitive dérivée, aucun agrégat, aucune doctrine. Conforme à ADR-002.
- **Premier adapter concret** : `CcxtSource` (`src/ninja_cat/adapters/ccxt_source.py`)
  implémente `MarketDataPort` via `fetch_trades` REST de ccxt. Garanties :
  tri par `ts` croissant + déduplication sur l'`id` natif du trade ;
  dégradation gracieuse (pattern ADR-003) — ccxt absent / exchange inconnu /
  `fetch_trades` échoue / trade malformé ⇒ itérable vide, jamais d'exception ;
  import ccxt en lazy, le cœur n'est jamais couplé à ccxt. `CcxtSource` exige
  `exchange_id` + `symbol`, donc instanciation directe (comme `ReplaySource`),
  pas via `get_source()`.
- **Adapter de replay fichier** : `FileReplaySource`
  (`src/ninja_cat/adapters/file_replay.py`) lit des trades historiques depuis
  Parquet et CSV (mapping de colonnes optionnel), mêmes garanties (tri + dédup
  par colonne `id`/`trade_id`, dégradation gracieuse, pandas/pyarrow en lazy).
  Exige un chemin de fichier, donc instanciation directe également.
- **Normalisation partagée** : `normalize_trade()`
  (`src/ninja_cat/adapters/_normalize.py`) est l'unique fonction de
  normalisation brut→`Trade`, utilisée par les deux adapters — garantit la
  parité de contrat (live==replay). Elle rejette les valeurs non finies
  (NaN/inf), un `ts` non entier, et `price`/`size` ≤ 0 ; ne lève jamais
  (retourne `None` pour une ligne douteuse).

Fichiers matérialisant cette décision : `src/ninja_cat/ingestion.py` (port +
NullSource + ReplaySource + fabrique), `src/ninja_cat/adapters/_normalize.py`
(normalize_trade partagé), `src/ninja_cat/adapters/ccxt_source.py` (CcxtSource),
`src/ninja_cat/adapters/file_replay.py` (FileReplaySource),
`tests/test_ingestion.py` (13 tests, committés en 8108124),
`tests/test_ccxt_source.py` (51 tests, ccxt mocké) et
`tests/test_file_replay.py` (63 tests, fichiers temp, zéro réseau ; suite
totale 140 tests verts).

## Consequences

### Positive
- Le cœur reste pur et testable sans flux live : `ReplaySource` suffit pour
  développer et valider l'ensemble du moteur en isolation.
- Les adapters réels (CCXT live, Parquet historique, CSV…) sont branchables
  sans toucher au cœur — même pattern qu'ADR-003.
- La parité live == replay est architecturalement garantie : les deux chemins
  traversent le même `MarketDataPort`.

### Negative
- `CcxtSource` existe et est testé, mais **aucun consommateur ni stratégie ne
  lit encore de `Trade`** : l'adapter n'est pas encore branché à un moteur. Le
  câblage live et tout traitement en aval restent différés (YAGNI déplacé :
  ce n'est plus l'adapter lui-même qui est manquant, c'est son usage).
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
