# ADR-005: Swarm claude-flow persistant (orchestration de l'équipe quant)

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: architecture, orchestration, claude-flow, swarm, agents

## Context

Jusqu'ici l'orchestration était implicite : la session Claude Code principale
déléguait aux subagents définis dans `.claude/agents/` au cas par cas, sans
état persistant entre sessions. `swarm_status` renvoyait `no_swarm`. La
composition de l'équipe (architect, data-engineer, implementer,
backtest-validator, viz-verifier) était documentée dans le README mais
n'existait pas comme entité de coordination persistante.

Sans couche de coordination, l'état des tâches en cours, l'attribution des
responsabilités et la topologie de l'équipe doivent être reconstruits à chaque
session — fragilité organisationnelle qui augmente avec la complexité du projet.

## Decision

Monter un swarm claude-flow **persistant** pour coordonner l'équipe quant :

- **Topologie** : `hierarchical`, stratégie `specialized`, protocole
  `message-bus`, consensus `majority`, auto-scaling activé.
- **6 agents enregistrés** : `orchestrator` (rôle coordinator) + 5 spécialistes
  quant — `architect` (quant-strategy-architect), `data-engineer`
  (quant-data-engineer), `implementer` (quant-algo-implementer),
  `backtest-validator` (quant-backtest-validator), `viz-verifier`
  (quant-viz-verifier).
- **Frontière coordination / exécution** (invariant essentiel) :
  - **claude-flow = couche de COORDINATION persistante** : registre des agents,
    topologie, message-bus, mémoire partagée, état du swarm, tâches
    pending→completed avec résultats persistés.
  - **Claude Code = MOTEUR d'EXÉCUTION** : les subagents font le travail réel
    via le Task tool, pilotés par la session active.
  - claude-flow n'est **pas** un daemon qui lance des process Claude en
    autonomie ; l'exécution reste toujours pilotée par une session.
- **État runtime** : stocké dans `.claude-flow/` et `.swarm/` (gitignoré),
  non versionné — reconstruction possible à tout moment via les outils
  claude-flow.

## Consequences

### Positive
- L'état d'orchestration (composition de l'équipe, tâches, topologie) survit
  entre sessions sans reconstruction manuelle.
- Séparation nette coordination / exécution : claude-flow sait *qui fait quoi*,
  Claude Code *fait* réellement.
- Routage explicite et traçable : tâches enregistrées avec responsable, statut
  et résultat persisté dans AgentDB.

### Negative
- Les agents enregistrés dans le swarm ne sont **pas** des process vivants en
  arrière-plan ; leur existence dans le registre ne garantit pas leur
  disponibilité — une session doit être active pour qu'une tâche s'exécute.
- L'état runtime n'étant pas versionné, toute réinitialisation de `.claude-flow/`
  exige de reconstruire le swarm (opération rapide mais manuelle).

### Neutral
- L'exécution concrète du travail reste inchangée : les subagents `.claude/agents/`
  exécutent toujours le travail réel ; le swarm n'ajoute que la couche de
  coordination par-dessus.

## Links
- Prolonge le rôle de claude-flow / AgentDB comme port sortant de
  [ADR-001](ADR-001-verite-donnee-doctrine-moteur.md) : la coordination est un
  service d'infrastructure, jamais un lieu de doctrine.
- S'appuie sur la même infrastructure mémoire matérialisée par
  [ADR-003](ADR-003-port-memoire-hexagonal.md) (AgentDB via `MemoryPort`).
