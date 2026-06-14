# ADR-003: Port mémoire hexagonal (le moteur découplé d'AgentDB)

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: architecture, memoire, ruflo, agentdb, hexagonal

## Context

ADR-001 pose que la mémoire (AgentDB / claude-flow) est un *port sortant* :
elle range et retrouve ce que le moteur produit, sans jamais calculer de
doctrine. Restait à matérialiser cette frontière dans le code — sans coupler le
cœur à claude-flow, et en garantissant que l'indisponibilité du backend ne
change rien au comportement du moteur.

Contrainte forte : claude-flow s'invoque via une CLI/MCP externe, lente à
démarrer (npx) et pas toujours présente. Le cœur ne doit ni l'importer, ni
dépendre de sa disponibilité.

## Decision

Architecture hexagonale (ports & adapters) pour la mémoire :

- **Port** (`ninja_cat.memory`) : `MemoryPort` (Protocol) expose un contrat
  minimal — `store(namespace, key, value)` et `search(namespace, query, limit)`
  renvoyant des `MemoryHit`. Le moteur ne dépend **que** de cette interface.
- **Fallback** : `NullMemory`, un no-op (n'écrit/retrouve rien, jamais d'erreur).
  C'est l'implémentation par défaut de la fabrique `get_memory()`. Garantit que
  le moteur tourne **identique** sans backend (exigence d'ADR-001).
- **Adapter** (`ninja_cat.adapters.agentdb.AgentDbMemory`) : parle à claude-flow
  via sa CLI (`memory store`/`search`). **Dégradation gracieuse** — CLI absente,
  échec ou timeout ⇒ résultat neutre (`False`/`[]`), jamais d'exception.
- **Découplage** : la fabrique importe l'adapter en *lazy import* ; le cœur
  n'importe jamais `adapters`. Ce sous-paquet est le seul autorisé à parler au
  monde extérieur (subprocess, réseau).

## Consequences

### Positive
- Le cœur reste pur et testable ; AgentDB est branchable/remplaçable sans le
  toucher.
- Robustesse : aucune panne backend ne casse le moteur (no-op garanti).
- La frontière d'ADR-001 existe désormais dans le code, pas seulement en prose.

### Negative
- Le parsing de `memory search` est *best-effort* tant que le format de sortie
  live de claude-flow n'est pas figé ; à durcir une fois le serveur validé.
- Latence potentielle de l'adapter (démarrage npx) ; à mesurer/optimiser avant
  tout usage sur un chemin chaud.

### Neutral
- Interface volontairement étroite (store/search) ; elle s'étendra si un besoin
  réel et spécifié apparaît, pas par anticipation.

## Links
- Matérialise le port mémoire de [ADR-001](ADR-001-verite-donnee-doctrine-moteur.md).
- Le port *entrant* (hypothèses : neural-trader / HNSW / discrétionnaire) reste
  à matérialiser quand une stratégie sera définie par le décideur humain.
