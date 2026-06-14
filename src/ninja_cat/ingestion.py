"""Port d'ingestion — frontière hexagonale entre le moteur et les sources de marché.

Le moteur (cœur de doctrine) ne connaît que l'interface `MarketDataPort`. Il ne
sait rien de CCXT, des websockets, ni d'aucun connecteur d'exchange concret :
ceux-ci sont des *adapters* branchés derrière ce port (cf. `ninja_cat.adapters`).

Conséquence voulue (miroir d'ADR-003) : si une source de marché est absente ou
hors ligne, le moteur tourne **identique** — le fallback `NullSource` ne produit
aucun trade, sans erreur. La source d'ingestion transporte uniquement des trades
bruts canoniques ; elle ne calcule jamais de doctrine.

Horloge : tout timestamp est en UTC, epoch millisecondes (monotone croissant).
Côté agresseur : porté tel quel depuis la source quand disponible ; jamais
deviné ici (règle portée par les adapters concrets).
"""

from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable

from ninja_cat.schema import Trade


@runtime_checkable
class MarketDataPort(Protocol):
    """Contrat minimal de transport de trades bruts que le moteur attend.

    Volontairement étroit : une seule méthode `trades()` qui itère des `Trade`
    canoniques. Les adapters concrets (CCXT live, replay Parquet, fixture test)
    implémentent ce protocole.

    Le port ne prescrit pas de cadence ni de volume : l'adapter décide si le flux
    est fini (historique) ou infini (live). Le moteur consomme simplement ce qui
    arrive.
    """

    def trades(self) -> Iterator[Trade]:
        """Itère les trades canoniques disponibles depuis cette source.

        - Chaque `Trade` est normalisé (schéma canonique de `ninja_cat.schema`).
        - L'ordre de livraison doit être temporellement croissant (ts monotone).
        - Un flux live peut bloquer entre deux trades ; un flux historique se
          termine quand l'itérateur est épuisé.
        - N'émet jamais de trade dupliqué ni de trade avec ts décroissant :
          cette garantie est de la responsabilité de l'adapter, pas du port.
        """
        ...


class NullSource:
    """Fallback no-op : ne produit aucun trade — jamais d'erreur.

    Garantit que le moteur fonctionne à l'identique en l'absence de source de
    marché. Utilisé comme défaut sûr et comme base pour les tests unitaires.
    """

    def trades(self) -> Iterator[Trade]:
        """Itérateur vide — ne produit aucun trade."""
        return iter(())


class ReplaySource:
    """Source de replay : rejoue une séquence de trades fournie à la construction.

    Usage principal : tests et reproductibilité. Permet de vérifier la parité
    live==replay en fournissant la même liste de `Trade` que celle enregistrée
    depuis un flux live.

    Les trades sont rejoués dans l'ordre de la liste ; aucune modification ni
    re-tri n'est effectué (l'appelant est responsable de fournir une séquence
    temporellement croissante).
    """

    def __init__(self, trades: list[Trade]) -> None:
        self._trades = trades

    def trades(self) -> Iterator[Trade]:
        """Itère les trades dans l'ordre fourni à la construction."""
        return iter(self._trades)


def get_source(backend: str = "null") -> MarketDataPort:
    """Fabrique l'implémentation du port d'ingestion.

    Par défaut `null` (no-op) — sûr, déterministe, sans effet de bord. Passer
    `replay` n'est pas possible via cette fabrique (ReplaySource requiert une
    liste de trades à la construction ; l'instancier directement). Cette fabrique
    est destinée aux backends nommés (ex. futurs adapters CCXT).
    """
    if backend == "null":
        return NullSource()
    raise ValueError(f"backend d'ingestion inconnu : {backend!r}")
