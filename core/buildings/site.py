"""Site building type for pickup and delivery locations."""

import math
import random
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from core.buildings.occupancy import OccupiableBuilding
from core.types import AgentID, DeliveryUrgency, PackageID, Priority, SiteID


@dataclass
class SiteStatistics:
    """Statistics tracking for site performance."""

    packages_generated: int = 0
    packages_picked_up: int = 0
    packages_delivered: int = 0
    packages_expired: int = 0
    total_value_delivered: float = 0.0
    total_value_expired: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize statistics to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteStatistics":
        """Deserialize statistics from dictionary."""
        return cls(**data)


@dataclass(kw_only=True)
class Site(OccupiableBuilding):
    """Site building for pickup and delivery operations.

    Sites are occupiable buildings where trucks can dock for loading/unloading.
    Trucks must enter the site to load or unload packages, and the loading time
    is proportional to the total weight of packages being handled.

    Note: Uses kw_only=True to allow non-default fields after inherited defaults.
    All fields must be passed as keyword arguments when constructing Site.
    """

    TYPE: ClassVar[str] = "site"

    # Site-specific fields
    name: str
    activity_rate: float  # λ for Poisson process (packages/hour)
    # Override capacity with a default (3 trucks can dock at once)
    capacity: int = 3
    # Fields with defaults
    loading_rate_tonnes_per_min: float = 0.5  # 0.5 tonnes/min = 2 min per tonne
    destination_weights: dict[SiteID, float] = field(default_factory=dict)
    package_config: dict[str, Any] = field(default_factory=dict)
    active_packages: list[PackageID] = field(default_factory=list)
    statistics: SiteStatistics = field(default_factory=SiteStatistics)

    def __post_init__(self) -> None:
        """Initialize site with default package configuration and validate occupancy."""
        # Validate occupancy configuration from parent
        super().__post_init__()

        if not self.package_config:
            self.package_config = {
                "size_range": (1.0, 30.0),  # Unitless size (1-30)
                "value_range_currency": (10.0, 1000.0),
                "pickup_deadline_range_ticks": (1800, 7200),  # 30min to 2h in ticks
                "delivery_deadline_range_ticks": (3600, 14400),  # 1h to 4h in ticks
                "priority_weights": {
                    Priority.LOW: 0.4,
                    Priority.MEDIUM: 0.3,
                    Priority.HIGH: 0.2,
                    Priority.URGENT: 0.1,
                },
                "urgency_weights": {
                    DeliveryUrgency.STANDARD: 0.6,
                    DeliveryUrgency.EXPRESS: 0.3,
                    DeliveryUrgency.SAME_DAY: 0.1,
                },
            }

    def to_dict(self) -> dict[str, Any]:
        """Serialize site to dictionary."""
        # Start with parent's serialization (includes capacity, current_agents)
        data = super().to_dict()
        # Add site-specific fields
        data["name"] = self.name
        data["activity_rate"] = self.activity_rate
        data["loading_rate_tonnes_per_min"] = self.loading_rate_tonnes_per_min
        data["destination_weights"] = {str(k): v for k, v in self.destination_weights.items()}
        data["package_config"] = self.package_config
        data["active_packages"] = list(self.active_packages)
        # Convert SiteStatistics to dict
        data["statistics"] = self.statistics.to_dict()
        # Add type field
        data["type"] = self.TYPE
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Site":
        """Deserialize site from dictionary."""
        # Remove fields not needed for construction
        data = dict(data)  # Create copy to avoid mutating original
        data.pop("type", None)
        data.pop("_dirty", None)
        data.pop("_last_serialized_state", None)

        # Convert current_agents list back to set
        if "current_agents" in data and isinstance(data["current_agents"], list):
            data["current_agents"] = {AgentID(a) for a in data["current_agents"]}

        # Convert destination_weights keys back to SiteID
        if "destination_weights" in data and isinstance(data["destination_weights"], dict):
            data["destination_weights"] = {
                SiteID(k): v for k, v in data["destination_weights"].items()
            }

        # Convert statistics dict back to SiteStatistics
        if isinstance(data.get("statistics"), dict):
            data["statistics"] = SiteStatistics.from_dict(data["statistics"])
        return cls(**data)

    def should_spawn_package(self, dt_s: float) -> bool:
        """Check if a package should spawn based on Poisson process.

        Args:
            dt_s: Time delta in seconds

        Returns:
            True if package should spawn this tick
        """
        # Convert activity rate from packages/hour to packages/second
        lambda_per_second = self.activity_rate / 3600.0

        # Poisson probability: P(X >= 1) = 1 - exp(-λ * dt)
        spawn_probability: float = 1.0 - math.exp(-lambda_per_second * dt_s)

        result: bool = random.random() < spawn_probability
        return result

    def select_destination(self, available_sites: list[SiteID]) -> SiteID | None:
        """Select destination site based on weights.

        Args:
            available_sites: List of available destination sites

        Returns:
            Selected destination site ID or None if no valid destinations
        """
        if not available_sites:
            return None

        # Filter weights to only include available sites
        valid_weights = {
            site_id: weight
            for site_id, weight in self.destination_weights.items()
            if site_id in available_sites
        }

        if not valid_weights:
            # If no weights defined, select randomly
            return random.choice(available_sites)

        # Normalize weights to probabilities
        total_weight = sum(valid_weights.values())
        if total_weight == 0:
            return random.choice(available_sites)

        probabilities = {
            site_id: weight / total_weight for site_id, weight in valid_weights.items()
        }

        # Weighted random selection
        rand_val = random.random()
        cumulative = 0.0

        for site_id, probability in probabilities.items():
            cumulative += probability
            if rand_val <= cumulative:
                return site_id

        # Fallback to last site (shouldn't happen)
        return list(probabilities.keys())[-1]

    def generate_package_parameters(self) -> dict[str, Any]:
        """Generate random package parameters based on configuration."""
        config = self.package_config

        # Generate size (unitless, 1-30)
        size_min, size_max = config["size_range"]
        size = random.uniform(size_min, size_max)

        # Generate value (higher priority/urgency = higher value)
        value_min, value_max = config["value_range_currency"]
        base_value = random.uniform(value_min, value_max)

        # Select priority and urgency
        priority = self._weighted_choice(config["priority_weights"])
        urgency = self._weighted_choice(config["urgency_weights"])

        # Adjust value based on priority and urgency
        value_multiplier = 1.0
        if priority == Priority.HIGH:
            value_multiplier *= 1.5
        elif priority == Priority.URGENT:
            value_multiplier *= 2.0

        if urgency == DeliveryUrgency.EXPRESS:
            value_multiplier *= 1.3
        elif urgency == DeliveryUrgency.SAME_DAY:
            value_multiplier *= 1.8

        value_currency = base_value * value_multiplier

        # Generate deadlines
        pickup_min, pickup_max = config["pickup_deadline_range_ticks"]
        delivery_min, delivery_max = config["delivery_deadline_range_ticks"]

        pickup_deadline_tick = random.randint(pickup_min, pickup_max)
        delivery_deadline_tick = random.randint(delivery_min, delivery_max)

        # Ensure delivery deadline is after pickup deadline
        if delivery_deadline_tick <= pickup_deadline_tick:
            delivery_deadline_tick = pickup_deadline_tick + random.randint(1800, 3600)

        return {
            "size": size,
            "value_currency": value_currency,
            "priority": priority,
            "urgency": urgency,
            "pickup_deadline_tick": pickup_deadline_tick,
            "delivery_deadline_tick": delivery_deadline_tick,
        }

    def _weighted_choice(self, weights: dict[Any, float]) -> Any:
        """Select an item based on weights."""
        items = list(weights.keys())
        probabilities = list(weights.values())

        # Normalize probabilities
        total = sum(probabilities)
        if total == 0:
            return random.choice(items)

        probabilities = [p / total for p in probabilities]

        # Weighted random selection
        rand_val = random.random()
        cumulative = 0.0

        for item, probability in zip(items, probabilities, strict=False):
            cumulative += probability
            if rand_val <= cumulative:
                return item

        return items[-1]  # Fallback

    def add_package(self, package_id: PackageID) -> None:
        """Add package to active packages list."""
        if package_id not in self.active_packages:
            self.active_packages.append(package_id)
            self.mark_dirty()

    def remove_package(self, package_id: PackageID) -> None:
        """Remove package from active packages list."""
        if package_id in self.active_packages:
            self.active_packages.remove(package_id)
            self.mark_dirty()

    def update_statistics(self, event_type: str, value: float = 0.0) -> None:
        """Update site statistics based on package events."""
        if event_type == "generated":
            self.statistics.packages_generated += 1
            self.mark_dirty()
        elif event_type == "picked_up":
            self.statistics.packages_picked_up += 1
            self.mark_dirty()
        elif event_type == "delivered":
            self.statistics.packages_delivered += 1
            self.statistics.total_value_delivered += value
            self.mark_dirty()
        elif event_type == "expired":
            self.statistics.packages_expired += 1
            self.statistics.total_value_expired += value
            self.mark_dirty()

    def calculate_loading_time_s(self, total_weight_tonnes: float) -> float:
        """Calculate the time needed to load/unload a given weight.

        Args:
            total_weight_tonnes: Total weight of packages to load/unload in tonnes

        Returns:
            Time in seconds to complete the loading/unloading operation
        """
        # loading_rate_tonnes_per_min is tonnes per minute
        # Time in minutes = weight / rate
        # Time in seconds = time in minutes * 60
        if self.loading_rate_tonnes_per_min <= 0:
            return 0.0
        time_minutes = total_weight_tonnes / self.loading_rate_tonnes_per_min
        return time_minutes * 60.0
