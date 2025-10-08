from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents.base import AgentBase

from core.ids import AgentID


class World:
    def __init__(self, graph: Any, router: Any, traffic: Any, dt_s: float = 0.05) -> None:
        self.graph = graph
        self.router = router
        self.traffic = traffic
        self.dt_s = dt_s
        self.tick = 0
        self.agents: dict[AgentID, AgentBase] = {}  # AgentID -> AgentBase
        self._events: list[Any] = []

    def now_s(self) -> int:
        return int(self.tick * self.dt_s)

    def time_min(self) -> int:
        return int(self.now_s() / 60)

    def emit_event(self, e: Any) -> None:
        self._events.append(e)

    def step(self) -> dict[str, Any]:
        self.tick += 1
        # 1) sense (optional)
        for a in self.agents.values():
            a.perceive(self)
        # 2) dispatch messages (outboxes to inboxes)
        self._deliver_all()
        # 3) decide/act
        for a in self.agents.values():
            a.decide(self)
        # 4) collect UI diffs
        diffs = [a.serialize_diff() for a in self.agents.values()]
        evts = self._events
        self._events = []
        return {"type": "tick", "t": self.now_s() * 1000, "events": evts, "agents": diffs}

    def _deliver_all(self) -> None:
        # deliver last tick's outboxes (you can store separately)
        outboxes = []
        for a in self.agents.values():
            if a.outbox:
                outboxes.extend(a.outbox)
                a.outbox = []
        for m in outboxes:
            if m.dst and m.dst in self.agents:
                self.agents[m.dst].inbox.append(m)
            elif m.topic:
                for _, agent in self.agents.items():
                    if m.topic in agent.tags.get("topics", []):
                        agent.inbox.append(m)
