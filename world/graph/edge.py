from dataclasses import dataclass
from enum import Enum, IntEnum

from core.types import EdgeID, NodeID


class Mode(IntEnum):
    ROAD = 1 << 0


class RoadClass(str, Enum):
    """Polish road classification system."""

    A = "A"  # Autostrada (Motorway)
    S = "S"  # Droga ekspresowa (Expressway)
    GP = "GP"  # Droga główna ruchu przyspieszonego (Main accelerated traffic road)
    G = "G"  # Droga główna (Main road)
    Z = "Z"  # Droga zbiorcza (Collector road)
    L = "L"  # Droga lokalna (Local road)
    D = "D"  # Droga dojazdowa (Access road)


@dataclass
class Edge:
    id: EdgeID
    from_node: NodeID
    to_node: NodeID
    length_m: float
    mode: Mode
    road_class: RoadClass
    lanes: int
    max_speed_kph: float
    weight_limit_kg: float | None  # None = unlimited
