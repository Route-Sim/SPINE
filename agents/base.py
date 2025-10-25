from dataclasses import dataclass, field
from typing import Any

from core.messages import Msg
from core.types import AgentID
from world.world import World


@dataclass
class AgentBase:
    id: AgentID
    kind: str
    inbox: list[Msg] = field(default_factory=list)
    outbox: list[Msg] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)  # arbitrary metadata
    _last_serialized_state: dict[str, Any] = field(default_factory=dict, init=False)

    def perceive(self, world: World) -> None:
        """Optional: pull local info (e.g., edge speed) into cached fields."""
        pass

    def decide(self, world: World) -> None:
        """Consume inbox, update own state, write outbox."""
        raise NotImplementedError

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
