from enum import Enum
from typing import NewType

# IDs
AgentID = NewType("AgentID", str)
BrokerID = NewType("BrokerID", str)
BuildingID = NewType("BuildingID", str)
EdgeID = NewType("EdgeID", int)
LegID = NewType("LegID", str)
NodeID = NewType("NodeID", int)
PackageID = NewType("PackageID", str)
SiteID = BuildingID  # Alias for BuildingID but more semantic

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


class NegotiationStatus(str, Enum):
    """Status of package negotiation between broker and truck."""

    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class TaskType(str, Enum):
    """Type of delivery task for truck queue."""

    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"


class TaskStatus(str, Enum):
    """Status of a delivery task in truck queue."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
