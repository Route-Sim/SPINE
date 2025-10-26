from dataclasses import dataclass, field
from typing import Any

from core.buildings.base import Building
from core.messages import Msg
from core.types import AgentID
from world.world import World


@dataclass
class BuildingAgent:
    """Agent wrapper for Building that combines Building data with agent capabilities."""

    # Required fields (no defaults) come first
    building: Building
    id: AgentID
    kind: str

    # Fields with defaults come after
    inbox: list[Msg] = field(default_factory=list)
    outbox: list[Msg] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)
    _last_serialized_state: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize BuildingAgent with building data."""
        # Convert BuildingID to AgentID (they're both string-based NewTypes)
        self.id = AgentID(str(self.building.id))
        self.kind = self.kind or "building"

    def perceive(self, world: World) -> None:
        """Optional: pull local info (e.g., edge speed) into cached fields."""
        pass

    def decide(self, world: World) -> None:
        """Consume inbox, update own state, write outbox."""
        pass

    def serialize_diff(self) -> dict[str, Any] | None:
        """Return a small dict for UI delta, or None if no changes."""
        current_state = {
            "id": self.id,
            "kind": self.kind,
            "tags": self.tags.copy(),
            "inbox_count": len(self.inbox),
            "outbox_count": len(self.outbox),
        }

        # Compare with last serialized state
        if current_state == self._last_serialized_state:
            return None  # No changes

        # Update last serialized state
        self._last_serialized_state = current_state.copy()
        return current_state
