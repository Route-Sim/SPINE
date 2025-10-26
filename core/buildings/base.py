from dataclasses import asdict, dataclass
from typing import Any

from core.types import BuildingID


@dataclass
class Building:
    """Base building class representing a physical facility in the logistics network."""

    id: BuildingID

    def to_dict(self) -> dict[str, Any]:
        """Serialize building to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Building":
        """Deserialize building from dictionary."""
        return cls(**data)
