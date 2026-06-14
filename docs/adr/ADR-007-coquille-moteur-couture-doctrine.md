# ADR-007: Coquille moteur neutre (EngineCore) et couture de doctrine

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: architecture, moteur, engine, doctrine, hexagonal

## Context

ADR-003 (port mémoire sortant) et ADR-004 (port ingestion entrant) ont encadré
le cœur du système de deux frontières hexagonales. Mais le **moteur** lui-même —
défini par ADR-001 comme l'unique endroit déterministe où vivra la *doctrine* de
trading — n'existait pas encore en code. Conséquence explicitement assumée par
ADR-004 (« Negative ») : aucun consommateur ne lisait de `Trade`. Les ports
étaient prêts, le trou central restait vide.

Matérialiser ce trou pose une tension : il faut donner au moteur sa place et son
câblage **sans** y mettre la moindre logique de décision — la doctrine est
décidée par l'humain / l'agent `strategy-architect`, jamais ajoutée par défaut
(frontière infra/doctrine, cf. mémoire `boundary-no-strategy-definition`).

## Decision

Introduire `EngineCore` (`src/ninja_cat/engine.py`) : une **coquille de moteur
neutre**, sans aucune doctrine.

- **Position** : entre les deux ports. Consomme `MarketDataPort` (entrant,
  ADR-004), détient `MemoryPort` (sortant, ADR-003) pour la doctrine future.
- **Defaults sûrs** : `NullSource` / `NullMemory` (cohérent avec `get_source()`
  et `get_memory()`). `EngineCore().run()` est sûr, déterministe, sans effet de
  bord.
- **`run()`** itère les `Trade` dans l'ordre du port et retourne un `RunStats`
  d'**observabilité de cycle de vie pure** : `processed`, `first_ts`, `last_ts`.
  Aucune métrique de stratégie. Le moteur ne modifie, ne réordonne et n'écarte
  jamais un trade.
- **Couture de doctrine** : `_on_trade()`, **vide par défaut**. C'est l'unique
  point où une stratégie se branchera (par sous-classe), une fois spécifiée.
  Tant que ce hook ne fait rien, le moteur est un transport observé.
- **Invariant de neutralité** : zéro décision, zéro seuil, zéro signal, zéro
  agrégat de méthodologie ; le moteur n'écrit rien en mémoire de lui-même (rien
  à persister sans doctrine — le port reste disponible via `self.memory` pour le
  hook d'une sous-classe).
- **Confiance au contrat des ports** : la dégradation gracieuse (source absente,
  backend hors-ligne) vit dans les adapters (ADR-003/004), pas dans le moteur.

Fichiers matérialisant cette décision : `src/ninja_cat/engine.py` (EngineCore +
RunStats), `tests/test_engine.py` (12 tests : défaut sûr, comptage/fenêtre,
déclenchement ordonné du hook, neutralité — aucune écriture mémoire via espion,
déterminisme, consommation de tout `MarketDataPort` en duck-typing ;
engine.py couvert à 100 %, suite totale 155 tests verts).

## Consequences

### Positive
- La dette « no consumer » d'ADR-004 est levée : il existe enfin un consommateur
  réel de `Trade`, sans une once de doctrine.
- Le pipeline tourne de bout en bout (source → moteur → mémoire), testable avec
  `ReplaySource` sans aucun flux live.
- La doctrine future a un **emplacement net et unique** (`_on_trade`) où se
  poser, au lieu d'une page blanche — la frontière infra/doctrine est inscrite
  dans la structure du code.

### Negative
- `_on_trade` étant vide, le moteur ne *fait* encore rien d'utile : c'est une
  coquille, pas un moteur opérationnel (par construction).
- Le port mémoire est détenu mais non utilisé par le cœur neutre (couture
  délibérée, défaut `NullMemory` sûr) — léger écart au YAGNI strict, assumé pour
  matérialiser la place de la doctrine.
- `run()` boucle indéfiniment sur une source live (itérateur infini) : aucune
  condition d'arrêt n'est encore définie. Acceptable tant que le câblage live et
  la doctrine ne sont pas spécifiés ; à revisiter à ce moment-là.

### Neutral
- Extension par sous-classe (patron *template method*). Si un besoin réel
  apparaît, l'API pourra évoluer vers un callback / composition — pas par
  anticipation.

## Links
- Matérialise le moteur défini par [ADR-001](ADR-001-verite-donnee-doctrine-moteur.md)
  (unique siège déterministe de la doctrine, subordonné au verdict de la donnée).
- Lève la conséquence « no consumer » du port d'ingestion
  [ADR-004](ADR-004-port-ingestion-hexagonal.md) et consomme via son
  `MarketDataPort`.
- Détient le port mémoire de [ADR-003](ADR-003-port-memoire-hexagonal.md) pour
  la doctrine future.
- Respecte la neutralité canonique d'[ADR-002](ADR-002-couche-canonique-neutre.md)
  et la frontière infra/doctrine (mémoire `boundary-no-strategy-definition`).
