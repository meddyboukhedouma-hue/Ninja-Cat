# ADR-006: Accès CDP TradingView sur port 9223 (runbook viz)

- **Status**: accepted
- **Date**: 2026-06-14
- **Deciders**: MeddyB
- **Tags**: ops, viz, tradingview, cdp, mcp, runbook

## Context

L'agent `viz-verifier` pilote `tradingview-mcp` via le Chrome DevTools Protocol
(CDP) pour visualiser et vérifier les sorties du moteur sur le chart TradingView.
Deux obstacles concrets sur la machine de développement bloquaient le lancement :

1. **Port 9222 occupé** : Brave Browser utilise en permanence le port CDP par
   défaut (9222), provoquant des conflits systématiques.
2. **TradingView Desktop = app UWP** : TradingView Desktop est distribué via le
   Microsoft Store — aucun `.exe` aux chemins standards (Program Files, AppData).
   L'outil `tv_launch` du MCP échoue, et une app UWP ne se lance avec des
   arguments de démarrage que via l'activation shell `shell:AppsFolder`.

## Decision

Déplacer le point d'attache CDP sur le port **9223** et définir un runbook de
lancement reproductible :

- **Port MCP** : le serveur MCP `tradingview` est configuré pour lire
  `CDP_PORT=9223` (variable dans `connection.js`). Brave conserve 9222, aucun
  conflit.
- **Lancement UWP** : TradingView Desktop est lancé via l'activation shell
  `shell:AppsFolder\<PackageFamilyName>!<AppId>` avec l'argument
  `--remote-debugging-port=9223`. Le `PackageFamilyName` est résolu
  **dynamiquement** via `Get-AppxPackage` — jamais de version hardcodée, le
  runbook reste valide après mise à jour de l'app.
- **Launcher PowerShell idempotent** (`Start-TradingViewCDP.ps1`) : ferme les
  instances existantes → relance TradingView → poll
  `http://127.0.0.1:9223/json` jusqu'à ce que le CDP réponde **et** qu'une page
  `tradingview.com/chart` soit présente. Retourne le statut final.
- **Périmètre strict du launcher** : il ne lance ni le serveur MCP (géré par
  Claude Code) ni Claude Desktop. Une seule responsabilité : TradingView +
  CDP.
- **Emplacement** : le script vit hors du dépôt (dossier outils
  `tradingview-mcp`), décision plutôt ops/runbook qu'architecture cœur.

## Consequences

### Positive
- Lancement reproductible en une commande depuis n'importe quelle session.
- Cohabitation propre avec Brave : chacun sur son port, zéro conflit.
- Résolution dynamique du package UWP : le runbook reste valide après mises à
  jour de TradingView Desktop, sans maintenance.
- Remplace l'ancien `.bat` fragile qui visait 9222 et échouait silencieusement.

### Negative
- Dépend de la présence du package UWP TradingView sur la machine et d'un
  abonnement TradingView actif.
- Le script étant externe au dépôt, il doit être documenté dans le README pour
  ne pas se perdre entre environnements.

### Neutral
- Décision de nature ops/runbook ; n'affecte ni l'architecture du moteur ni la
  doctrine.

## Links
- Sert le rôle de l'agent `viz-verifier` (cf. flux d'agents du README) : c'est
  sa dépendance d'environnement, pas une dépendance du cœur.
- N'impacte aucune doctrine : TradingView ne fait que rendre, conformément à
  [ADR-001](ADR-001-verite-donnee-doctrine-moteur.md).
