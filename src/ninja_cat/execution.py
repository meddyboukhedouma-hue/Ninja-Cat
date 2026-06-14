"""Port d'exécution — frontière hexagonale entre le moteur et le broker.

Symétrique des ports mémoire (ADR-003) et ingestion (ADR-004), côté **action** :
le moteur ne connaît que `ExecutionPort`. Il ne sait rien de TradingView, du
Paper Trader, ni d'aucun broker concret — ceux-ci sont des *adapters* branchés
derrière le port (cf. `ninja_cat.adapters.paper_trader`).

FRONTIÈRE (capitale) : ce port **transporte** des ordres décidés ailleurs. Quoi
trader, quand, avec quelle taille = **doctrine** (hors du périmètre infra). La
doctrine vit dans la couture `_on_trade` d'`EngineCore` (ADR-007) ; c'est elle
qui *décide* puis appelle `submit()`. Le port et ses adapters ne décident jamais.

Dégradation gracieuse (miroir ADR-003/004) : si le broker est absent ou
hors-ligne, les opérations retournent `False` sans lever — le moteur n'est jamais
bloqué par l'indisponibilité de l'exécution. Le fallback `NullBroker` ne fait
rien (et c'est un défaut sûr : aucun ordre réel n'est passé par accident).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from ninja_cat.schema import Side


class OrderType(str, Enum):
    """Type d'ordre. Volontairement réduit à `MARKET` (YAGNI) : c'est le seul
    type vérifié en live ; limit/stop seront ajoutés quand un besoin réel et
    spécifié apparaîtra, pas par anticipation.
    """

    MARKET = "market"


@dataclass(frozen=True)
class Order:
    """Ordre canonique à transmettre au broker — neutre vis-à-vis de la doctrine.

    Ne porte que le strict nécessaire pour exécuter : quoi, combien, quel sens.
    `side` réutilise `schema.Side` (buy/sell). C'est la *décision* (produire cet
    Order) qui relève de la doctrine ; l'objet lui-même est une simple donnée.
    """

    symbol: str
    qty: float
    side: Side
    type: OrderType = OrderType.MARKET


@runtime_checkable
class ExecutionPort(Protocol):
    """Contrat minimal d'exécution que le moteur attend.

    Volontairement étroit : `submit` (passer un ordre) + `close` (clôturer la
    position d'un symbole). Tout adapter concret implémente ce protocole.
    """

    def submit(self, order: Order) -> bool:
        """Transmet `order` au broker. Retourne True si accepté, False sinon."""
        ...

    def close(self, symbol: str) -> bool:
        """Clôture la position ouverte sur `symbol`. True si clôturée, False sinon."""
        ...


class NullBroker:
    """Fallback no-op : ne passe aucun ordre, ne clôture rien — jamais d'erreur.

    Défaut **sûr** : garantit qu'aucun ordre réel n'est émis tant qu'un broker
    concret n'est pas explicitement branché. Équivalent de `NullSource` /
    `NullMemory` côté exécution.
    """

    def submit(self, order: Order) -> bool:
        return False

    def close(self, symbol: str) -> bool:
        return False


def get_broker(backend: str = "null") -> ExecutionPort:
    """Fabrique l'implémentation du port d'exécution.

    Par défaut `null` (no-op) — sûr, déterministe, n'émet aucun ordre. Passer
    `paper_tradingview` pour brancher le Paper Trader de TradingView (import
    paresseux : le cœur n'est jamais couplé à l'adapter ni à son transport CDP).
    """
    if backend == "paper_tradingview":
        from .adapters.paper_trader import PaperTraderBroker

        return PaperTraderBroker()
    if backend == "null":
        return NullBroker()
    raise ValueError(f"backend d'exécution inconnu : {backend!r}")
