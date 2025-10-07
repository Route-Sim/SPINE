from dataclasses import dataclass, field
from typing import Any

from .ids import AgentID, LegID


@dataclass
class Msg:
    src: AgentID
    dst: AgentID | None = None
    topic: str | None = None
    typ: str = ""  # e.g., "auction", "award", "reroute", "handoff", "signal"
    body: dict[str, Any] = field(default_factory=dict)


# convenience builders (optional)
def Auction(src: AgentID, leg_id: LegID, payload: Any) -> Msg:
    """Create an auction message."""
    return Msg(src=src, typ="auction", body={"leg_id": leg_id, "payload": payload})


def Bid(
    src: AgentID, dst: AgentID, leg_id: LegID, cost: float, eta: int, risk: float, meta: Any = None
) -> Msg:
    """Create a bid message."""
    body = {"leg_id": leg_id, "cost": cost, "eta": eta, "risk": risk}
    if meta is not None:
        body["meta"] = meta
    return Msg(src=src, dst=dst, typ="bid", body=body)


def Award(src: AgentID, dst: AgentID, leg_id: LegID, terms: Any) -> Msg:
    """Create an award message."""
    return Msg(src=src, dst=dst, typ="award", body={"leg_id": leg_id, "terms": terms})


def Reroute(src: AgentID, dst: AgentID, reason: str, constraints: Any) -> Msg:
    """Create a reroute message."""
    return Msg(src=src, dst=dst, typ="reroute", body={"reason": reason, "constraints": constraints})
