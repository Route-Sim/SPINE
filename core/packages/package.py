"""Package data structure for delivery items."""

from dataclasses import asdict, dataclass
from typing import Any

from core.types import DeliveryUrgency, PackageID, PackageStatus, Priority, SiteID


@dataclass
class Package:
    """Package data structure representing a delivery item."""

    id: PackageID
    origin_site: SiteID
    destination_site: SiteID
    size: float  # Unitless size (1-30), represents cargo space consumed
    value_currency: float
    priority: Priority
    urgency: DeliveryUrgency
    spawn_tick: int
    pickup_deadline_tick: int
    delivery_deadline_tick: int
    status: PackageStatus = PackageStatus.WAITING_PICKUP

    def to_dict(self) -> dict[str, Any]:
        """Serialize package to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Package":
        """Deserialize package from dictionary."""
        # Convert string enums back to enum instances
        if isinstance(data.get("priority"), str):
            data["priority"] = Priority(data["priority"])
        if isinstance(data.get("urgency"), str):
            data["urgency"] = DeliveryUrgency(data["urgency"])
        if isinstance(data.get("status"), str):
            data["status"] = PackageStatus(data["status"])

        return cls(**data)

    def is_expired(self, current_tick: int) -> bool:
        """Check if package has expired based on pickup deadline."""
        return current_tick >= self.pickup_deadline_tick

    def is_delivery_overdue(self, current_tick: int) -> bool:
        """Check if package delivery is overdue."""
        return current_tick > self.delivery_deadline_tick

    def get_remaining_pickup_time_ticks(self, current_tick: int) -> int:
        """Get remaining ticks until pickup deadline."""
        return max(0, self.pickup_deadline_tick - current_tick)

    def get_remaining_delivery_time_ticks(self, current_tick: int) -> int:
        """Get remaining ticks until delivery deadline."""
        return max(0, self.delivery_deadline_tick - current_tick)
