from dataclasses import dataclass
from enum import IntEnum

from core.types import EdgeID, NodeID


class Mode(IntEnum):
    ROAD = 1 << 0


@dataclass
class Edge:
    id: EdgeID
    from_node: NodeID
    to_node: NodeID
    length_m: float
    mode: Mode
