"""Moteur — coquille neutre, sans aucune doctrine.

Le moteur est, dans cette architecture, l'**unique endroit déterministe où la
doctrine de trading vivra** (ADR-001). Cette coquille matérialise sa place et son
câblage **avant** toute logique de décision : elle consomme des `Trade` via le
port d'ingestion (`MarketDataPort`, ADR-004) et détient le port mémoire
(`MemoryPort`, ADR-003) pour la doctrine future. Elle débloque la conséquence
« no consumer » d'ADR-004 : enfin un consommateur réel de `Trade`, sans présumer
d'aucune stratégie.

NEUTRALITÉ — invariant central de ce fichier :
    Ce module ne prend AUCUNE décision de trading. Pas de signal, pas de seuil,
    pas d'entrée/sortie, pas d'agrégat de méthodologie. Le seul état tenu est de
    l'observabilité de cycle de vie pure (nombre de trades traités, premier et
    dernier timestamp) — ce que n'importe quel pipeline compte, indépendamment
    de toute stratégie.

    Le point d'accroche de la doctrine est `_on_trade()`, **vide par défaut**.
    C'est là — et seulement là — qu'une stratégie se branchera (par sous-classe),
    une fois spécifiée par le décideur humain / l'architecte. Tant que ce hook
    reste vide, le moteur est un simple transport observé.

Le moteur fait confiance au contrat des ports : la dégradation gracieuse (source
absente, backend mémoire hors-ligne) vit dans les adapters (ADR-003/004), pas
ici. Avec `NullSource`/`NullMemory` par défaut, `EngineCore().run()` est sûr,
déterministe et sans effet de bord.
"""

from __future__ import annotations

from dataclasses import dataclass

from ninja_cat.ingestion import MarketDataPort, NullSource
from ninja_cat.memory import MemoryPort, NullMemory
from ninja_cat.schema import Trade


@dataclass(frozen=True)
class RunStats:
    """Bilan d'observabilité d'un passage du moteur — neutre, sans doctrine.

    Ne contient que des compteurs de cycle de vie : combien de trades ont
    traversé le moteur et sur quelle fenêtre temporelle. Aucune métrique de
    stratégie (ce serait de la doctrine).
    """

    processed: int            # nombre de Trade consommés
    first_ts: int | None      # ts du premier trade (None si flux vide)
    last_ts: int | None       # ts du dernier trade (None si flux vide)


class EngineCore:
    """Coquille de moteur : consomme des `Trade`, ne décide rien.

    Paramètres
    ----------
    source:
        Port d'ingestion fournissant les `Trade`. Défaut : `NullSource`
        (flux vide, sûr) — cohérent avec `get_source()`.
    memory:
        Port mémoire mis à disposition de la doctrine future. Défaut :
        `NullMemory` (no-op) — cohérent avec `get_memory()`. La coquille neutre
        ne l'utilise pas elle-même (rien à persister sans doctrine) ; il est
        accessible via `self.memory` pour le hook `_on_trade` d'une sous-classe.
    """

    def __init__(
        self,
        source: MarketDataPort | None = None,
        memory: MemoryPort | None = None,
    ) -> None:
        self.source: MarketDataPort = source if source is not None else NullSource()
        self.memory: MemoryPort = memory if memory is not None else NullMemory()

    def run(self) -> RunStats:
        """Consomme tout le flux de la source et retourne un bilan neutre.

        Itère les `Trade` dans l'ordre fourni par le port, appelle `_on_trade`
        pour chacun (hook de doctrine, vide par défaut), et comptabilise une
        observabilité de cycle de vie. Ne modifie jamais un `Trade`, ne réordonne
        rien, ne décide rien.

        Pour un flux live (itérateur infini), `run()` boucle indéfiniment — c'est
        le comportement attendu d'un moteur en marche ; l'appelant choisit la
        source finie (replay) ou infinie (live) selon le contexte.
        """
        processed = 0
        first_ts: int | None = None
        last_ts: int | None = None

        for trade in self.source.trades():
            if first_ts is None:
                first_ts = trade.ts
            last_ts = trade.ts
            processed += 1
            self._on_trade(trade)

        return RunStats(processed=processed, first_ts=first_ts, last_ts=last_ts)

    def _on_trade(self, trade: Trade) -> None:
        """Point d'accroche de la doctrine — **vide par défaut (neutre)**.

        C'est l'unique couture où une stratégie se branchera, par sous-classe,
        une fois spécifiée (hors du périmètre de cette coquille : la doctrine est
        décidée par l'humain / l'architecte, jamais ajoutée ici). Tant que ce
        hook ne fait rien, `EngineCore` reste un transport observé sans décision.
        """
        return None
