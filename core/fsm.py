from enum import Enum, auto


class VehicleState(Enum):
    IDLE = auto()
    BIDDING = auto()
    ASSIGNED = auto()
    ENROUTE = auto()
    AT_NODE = auto()
    HANDOFF = auto()
    OUT_OF_SERVICE = auto()
