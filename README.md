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
3. Lance **TradingView Desktop** avec `--remote-debugging-port=9222`
   (abonnement TradingView requis, port local 9222).

## Setup (quant)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt  # cœur runtime (épinglé)
pip install -e ".[dev]"          # paquet (src/) en editable + outillage de test
pytest                           # pythonpath=src est configuré dans pyproject.toml
# Extras optionnels : pip install -e ".[perf]"  (numba)  /  ".[live]"  (websockets)
```
