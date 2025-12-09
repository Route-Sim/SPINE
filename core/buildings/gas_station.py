"""Gas station building type for fuel services."""

from dataclasses import dataclass, field
from typing import Any, ClassVar

from core.buildings.occupancy import OccupiableBuilding
from core.types import AgentID, BuildingID


@dataclass
class GasStation(OccupiableBuilding):
    """Gas station building that provides fuel services to transport agents.

    Inherits agent storage functionality from OccupiableBuilding.
    Tracks a cost factor that multiplies the global fuel price to determine
    the actual price at this station.
    Maintains a balance of revenue from fuel sales.
    """

    TYPE: ClassVar[str] = "gas_station"
    # Use kw_only to allow non-default field after inherited defaults
    cost_factor: float = field(kw_only=True)  # Multiplier on global fuel price (e.g., 0.8-1.2)
    balance_ducats: float = field(default=0.0, kw_only=True)  # Accumulated revenue from fuel sales

    def __post_init__(self) -> None:
        """Validate the gas station configuration."""
        super().__post_init__()
        if self.cost_factor <= 0:
            raise ValueError("GasStation cost_factor must be positive")

    def get_fuel_price(self, global_price: float) -> float:
        """Calculate the fuel price at this station.

        Args:
            global_price: The global/base fuel price

        Returns:
            The actual fuel price at this station (global_price * cost_factor)
        """
        return global_price * self.cost_factor

    def add_revenue(self, amount: float) -> None:
        """Add revenue to the gas station's balance.

        Args:
            amount: Amount to add in ducats

        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError("Revenue amount must be non-negative")
        self.balance_ducats += amount
        self.mark_dirty()

    def to_dict(self) -> dict[str, Any]:
        """Serialize gas station to dictionary."""
        data = super().to_dict()
        data["cost_factor"] = self.cost_factor
        data["balance_ducats"] = self.balance_ducats
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GasStation":
        """Deserialize gas station from dictionary."""
        agents_raw = data.get("current_agents", [])
        agents = {AgentID(agent) for agent in agents_raw}
        return cls(
            id=BuildingID(data["id"]),
            capacity=int(data["capacity"]),
            current_agents=agents,
            cost_factor=float(data["cost_factor"]),
            balance_ducats=float(data.get("balance_ducats", 0.0)),
        )
