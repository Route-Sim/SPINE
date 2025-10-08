from dataclasses import dataclass, field
from typing import Any

from world.world import World

from ..core.ids import AgentID
from ..core.messages import Msg


@dataclass
class AgentBase:
    id: AgentID
    kind: str
    inbox: list[Msg] = field(default_factory=list)
    outbox: list[Msg] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)  # arbitrary metadata

    def perceive(self, world: World) -> None:
        """Optional: pull local info (e.g., edge speed) into cached fields."""
        pass

    def decide(self, world: World) -> None:
        """Consume inbox, update own state, write outbox."""
        raise NotImplementedError

    def serialize_diff(self) -> dict[str, str]:
        """Return a small dict for UI delta."""
        return {"id": self.id, "kind": self.kind}
