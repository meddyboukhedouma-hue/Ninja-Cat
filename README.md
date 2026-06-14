# Ninja-Cat

Plateforme d'aide à la décision pour le trading (quant).

**Principe directeur :** la **donnée de marché est la seule source de vérité** —
le marché tranche, toujours. Le **moteur** est la source unique de *doctrine*
(l'unique endroit, déterministe, où vit la logique de décision) ; il reste un
*modèle* subordonné au verdict de la donnée. Les couches d'affichage ne font que
*rendre*. Seuils **scale-free** centralisés dans `Config` ; seul `tick_size` est
par-symbole. Simplicité avant tout.

## Structure

```
.claude/agents/      Agents quant spécialisés (voir ci-dessous)
.mcp.json            Serveurs MCP du projet (claude-flow ; tradingview au scope user)
src/ninja_cat/
  config.py          Config centrale (métadonnée marché ; scalaires de stratégie à venir)
  schema.py          Schéma canonique : Trade, Side (donnée de marché brute, neutre)
  ingestion.py       Port d'ingestion entrant (MarketDataPort) + NullSource/ReplaySource
  memory.py          Port mémoire sortant (MemoryPort) + NullMemory
  execution.py       Port d'exécution sortant (ExecutionPort, Order) + NullBroker
  engine.py          Coquille moteur neutre (EngineCore) : consomme les Trade, couture de doctrine vide
  adapters/          Adapters concrets (CcxtSource, FileReplaySource, AgentDbMemory, PaperTraderBroker)
tests/               pytest
requirements.txt
```

## Agents (`.claude/agents/`)

| Agent | Rôle |
|---|---|
| `quant-strategy-architect` | Idée/doctrine → spec déterministe (pas de code) |
| `quant-data-engineer` | Ingestion/normalisation flux, schéma canonique, parité live==replay |
| `quant-algo-implementer` | Spec → code Python (+ Rust/Numba si mesuré) + tests |
| `quant-backtest-validator` | Mesure l'edge : triple-barrier, meta-labeling, purged CV, anti-look-ahead |
| `quant-viz-verifier` | Pilote tradingview-mcp : rend, vérifie visuellement, auto-corrige le rendu |

Flux : architect → data-engineer → implementer → backtest-validator → viz-verifier.

## Affichage / vérification (tradingview-mcp)

L'agent `quant-viz-verifier` s'appuie sur
[tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) pour afficher
les sorties du moteur sur le chart, les relire, et auto-corriger le rendu.
TradingView ne recalcule **jamais** la doctrine — il ne fait que rendre.

Pré-requis :
1. Récupère le serveur `tradingview-mcp` :
   `git clone https://github.com/tradesdontlie/tradingview-mcp`
   puis `cd tradingview-mcp && npm install` (Node 18+).
2. Enregistre-le **au scope user** (pas dans le `.mcp.json` projet, pour éviter
   les chemins absolus committés) :
   `claude mcp add tradingview -s user -- node <chemin>/tradingview-mcp/src/server.js`
3. Lance **TradingView Desktop** avec le port de debug CDP **9223**
   (abonnement TradingView requis). On utilise 9223 et non le 9222 par défaut
   car celui-ci est souvent occupé par un navigateur Chromium (cf. ADR-006) ;
   le serveur MCP est configuré pour lire 9223.
   - TradingView est distribué via le Microsoft Store (app UWP) : il se lance
     avec un argument via l'activation shell
     `shell:AppsFolder\<PackageFamilyName>!<AppId>` +
     `--remote-debugging-port=9223` (le package se résout dynamiquement via
     `Get-AppxPackage`, jamais de version en dur).
   - Un launcher PowerShell idempotent **`Start-TradingViewCDP.ps1`** automatise
     ça (ferme les instances → relance sur 9223 → attend que le CDP réponde).
     Il vit dans le dossier outils `tradingview-mcp` (hors dépôt), à côté du
     serveur MCP. Voir ADR-006 pour le détail.

## Setup (quant)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt  # cœur runtime (épinglé)
pip install -e ".[dev]"          # paquet (src/) en editable + outillage de test
pytest                           # pythonpath=src est configuré dans pyproject.toml
# Extras optionnels : pip install -e ".[perf]"  (numba)  /  ".[live]"  (websockets)
```
