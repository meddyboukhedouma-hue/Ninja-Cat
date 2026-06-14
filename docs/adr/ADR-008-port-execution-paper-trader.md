# ADR-008: Port d'exécution hexagonal et adapter Paper Trader TradingView

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: architecture, execution, broker, paper-trading, tradingview, hexagonal

## Context

ADR-003 (port mémoire) et ADR-004 (port ingestion) encadrent le cœur côté
donnée ; ADR-007 a introduit `EngineCore`, coquille neutre où la doctrine se
branchera (`_on_trade`). Il manquait le troisième côté : **l'action**. Une
doctrine, une fois décidée, doit pouvoir *exécuter* — passer un ordre — sans que
le moteur ne dépende d'un broker concret.

Découverte déterminante (vérifiée en live le 2026-06-14) : le **Paper Trader de
TradingView Desktop** expose l'**API Broker complète** dans la page
(`placeOrder`, `closePosition`, `positions`, `orders`, `accountManagerInfo`…),
joignable via le Chrome DevTools Protocol (port 9223, ADR-006). Un smoke test
(BUY 0.001 BTC market) a confirmé l'exécution réelle paper. NB : l'outil
`tv_discover` ne voit pas cette API (sonde restreinte) et `replay_trade` ne
couvre que le mode Replay — d'où l'accès direct au broker.

## Decision

Introduire un **port d'exécution hexagonal**, symétrique des ports mémoire et
ingestion, côté action.

- **Port** (`ninja_cat.execution`) : `ExecutionPort` (Protocol
  `runtime_checkable`) — contrat étroit : `submit(order)` + `close(symbol)`.
  Le moteur ne dépend **que** de cette interface, jamais d'un broker concret.
- **Donnée canonique** : `Order` (`symbol`, `qty`, `side` réutilisant
  `schema.Side`, `type`). `OrderType` réduit à `MARKET` (YAGNI ; seul type
  vérifié en live).
- **Fallback sûr** : `NullBroker` (no-op). Défaut **doublement sûr** : non
  seulement le moteur tourne identique sans broker, mais **aucun ordre réel
  n'est émis par accident** tant qu'un broker concret n'est pas explicitement
  branché.
- **Fabrique** : `get_broker()`, symétrique de `get_source()` / `get_memory()`.
  Retourne `NullBroker` par défaut ; `paper_tradingview` pour l'adapter réel.
- **Adapter concret** : `PaperTraderBroker`
  (`src/ninja_cat/adapters/paper_trader.py`) pilote le broker Paper de
  TradingView en évaluant du JS via CDP. **Transport injectable** : le
  constructeur accepte un `evaluator(js) -> objet` ; défaut = client CDP
  websocket. Ce découplage rend l'adapter testable sans navigateur (les tests
  injectent un faux evaluator). Dégradation gracieuse (pattern ADR-003) : CDP
  injoignable / lib websocket absente / exception JS ⇒ `False`, jamais de levée,
  jamais d'ordre « à moitié ». `websocket-client` (lazy) vit dans l'extra
  `[live]` ; le cœur n'est jamais couplé au transport.
- **Câblage moteur** : `EngineCore` détient `self.broker` (défaut `NullBroker`),
  comme `self.memory`. Le cœur neutre ne passe **jamais** d'ordre lui-même ;
  `self.broker` est disponible pour le hook `_on_trade` d'une sous-classe.

FRONTIÈRE (capitale) : le port et l'adapter **transportent** des ordres décidés
ailleurs. Décider quoi/quand/combien trader = **doctrine**, hors du périmètre
infra ; cela vit dans `_on_trade` (ADR-007), jamais dans ce port.

Fichiers matérialisant cette décision : `src/ninja_cat/execution.py` (port +
Order + NullBroker + fabrique), `src/ninja_cat/adapters/paper_trader.py`
(PaperTraderBroker + transport CDP), `src/ninja_cat/engine.py` (broker câblé),
`tests/test_execution.py` (24 tests, evaluator injecté + dégradation gracieuse),
`tests/test_engine.py` (neutralité d'exécution). Suite : 176 tests verts ;
`execution.py` couvert à 100 %.

## Consequences

### Positive
- Le cœur reste pur : la doctrine pourra exécuter via une interface abstraite,
  testable avec un broker espion sans navigateur ni réseau.
- Le Paper Trader devient un canal de **forward-test / exécution paper live**
  réel, complémentaire du backtest historique hors-ligne
  (`quant-backtest-validator`).
- Symétrie des trois ports (ingestion entrant, mémoire + exécution sortants) :
  le cœur du moteur est entièrement encadré par des frontières hexagonales.

### Negative
- Le chemin CDP live (`_cdp_evaluate`) n'est pas couvert par les tests unitaires
  (nécessite un navigateur) — couverture de `paper_trader.py` partielle, même
  situation qu'`agentdb.py`. Mitigé par le smoke test live et le test de
  dégradation gracieuse sur endpoint mort.
- Couplage à un détail d'implémentation de TradingView (chemin
  `bottomWidgetBar…activeBroker().placeOrder`) susceptible de bouger entre
  versions ; isolé dans le seul adapter, remplaçable sans toucher au cœur.
- `EngineCore` détient un port de plus, non utilisé par le cœur neutre (couture
  délibérée, défaut `NullBroker` sûr).

### Neutral
- `OrderType` limité à `MARKET` ; limit/stop s'ajouteront quand un besoin réel
  et spécifié apparaîtra, pas par anticipation.
- Le transport injectable permettrait demain d'autres canaux (broker réel via
  ccxt, autre plateforme) derrière le même `ExecutionPort`.

## Links
- Complète [ADR-007](ADR-007-coquille-moteur-couture-doctrine.md) côté action :
  la doctrine décide dans `_on_trade`, ce port exécute.
- Symétrique de [ADR-003](ADR-003-port-memoire-hexagonal.md) (mémoire) et
  [ADR-004](ADR-004-port-ingestion-hexagonal.md) (ingestion).
- S'appuie sur l'accès CDP TradingView de
  [ADR-006](ADR-006-acces-cdp-tradingview-port-9223.md).
- Respecte la primauté de la donnée d'[ADR-001](ADR-001-verite-donnee-doctrine-moteur.md)
  et la frontière infra/doctrine (mémoire `boundary-no-strategy-definition`).
