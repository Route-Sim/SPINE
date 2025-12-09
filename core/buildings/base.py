from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from core.types import BuildingID


@dataclass
class Building:
    """Base building class representing a physical facility in the logistics network.

    Tracks state changes via _dirty flag for efficient diff serialization.
    Buildings emit update signals only when explicitly marked dirty.
    """

    id: BuildingID
    TYPE: ClassVar[str] = "building"

    # Internal state for diff tracking (excluded from serialization)
    _dirty: bool = field(default=False, init=False, repr=False, compare=False)
    _last_serialized_state: dict[str, Any] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def mark_dirty(self) -> None:
        """Mark building as having changed state, triggering update signal emission."""
        self._dirty = True

    def is_dirty(self) -> bool:
        """Check if building has unserialized state changes."""
        return self._dirty

    def clear_dirty(self) -> None:
        """Clear the dirty flag after serializing changes."""
        self._dirty = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize building to dictionary."""
        data = asdict(self)
        data["id"] = str(self.id)
        data["type"] = self.TYPE
        # Remove internal tracking fields from serialization
        data.pop("_dirty", None)
        data.pop("_last_serialized_state", None)
        return data

    def serialize_full(self) -> dict[str, Any]:
        """Return complete building state for state snapshot.

        Returns:
            Full serialized building state dictionary.
        """
        return self.to_dict()

    def serialize_diff(self) -> dict[str, Any] | None:
        """Return building state if dirty, or None if no changes.

        Buildings use full state serialization (not incremental diffs)
        since building state changes are infrequent.

        Returns:
            Full building state dict if dirty, None otherwise.
        """
        if not self._dirty:
            return None

        current_state = self.to_dict()

        # Update last serialized state and clear dirty flag
        self._last_serialized_state = current_state.copy()
        self._dirty = False

        return current_state

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
