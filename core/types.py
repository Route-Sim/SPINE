from enum import Enum
from typing import NewType

# IDs
AgentID = NewType("AgentID", str)
BuildingID = NewType("BuildingID", str)
EdgeID = NewType("EdgeID", int)
LegID = NewType("LegID", str)
NodeID = NewType("NodeID", int)
PackageID = NewType("PackageID", str)
SiteID = NewType("SiteID", str)  # Alias for BuildingID but more semantic

# Time
Minutes = NewType("Minutes", int)


class Priority(str, Enum):
    """Package priority levels affecting payment and handling."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class DeliveryUrgency(str, Enum):
    """Delivery urgency levels affecting deadlines and pricing."""

    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"
    SAME_DAY = "SAME_DAY"


class PackageStatus(str, Enum):
    """Package lifecycle status."""

    WAITING_PICKUP = "WAITING_PICKUP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    EXPIRED = "EXPIRED"
