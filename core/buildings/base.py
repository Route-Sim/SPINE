from dataclasses import asdict, dataclass
from typing import Any, ClassVar

from core.types import BuildingID


@dataclass
class Building:
    """Base building class representing a physical facility in the logistics network."""

    id: BuildingID
    TYPE: ClassVar[str] = "building"

    def to_dict(self) -> dict[str, Any]:
        """Serialize building to dictionary."""
        data = asdict(self)
        data["id"] = str(self.id)
        data["type"] = self.TYPE
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Building":
        """Deserialize building from dictionary."""
        building_type = data.get("type", cls.TYPE)
        if building_type == "parking":
            from core.buildings.parking import Parking

            return Parking.from_dict(data)
        elif building_type == "site":
            from core.buildings.site import Site

            return Site.from_dict(data)
        elif building_type == "gas_station":
            from core.buildings.gas_station import GasStation

            return GasStation.from_dict(data)
        return cls(id=BuildingID(data["id"]))
