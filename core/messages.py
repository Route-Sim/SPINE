from dataclasses import dataclass, field
from typing import Any

from .types import AgentID


@dataclass
class Msg:
    src: AgentID
    dst: AgentID | None = None
    topic: str | None = None
    typ: str = ""  # e.g., "auction", "award", "reroute", "handoff", "signal"
    body: dict[str, Any] = field(default_factory=dict)
