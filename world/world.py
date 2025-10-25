from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents.base import AgentBase

from core.types import AgentID


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

    def add_agent(self, agent_id: AgentID, agent: "AgentBase") -> None:
        """Add an agent to the world."""
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already exists")
        self.agents[agent_id] = agent
        self.emit_event({"type": "agent_added", "agent_id": agent_id, "agent_kind": agent.kind})

    def remove_agent(self, agent_id: AgentID) -> None:
        """Remove an agent from the world."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} does not exist")
        agent = self.agents.pop(agent_id)
        self.emit_event({"type": "agent_removed", "agent_id": agent_id, "agent_kind": agent.kind})

    def modify_agent(self, agent_id: AgentID, modifications: dict[str, Any]) -> None:
        """Modify an agent's properties."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} does not exist")

        agent = self.agents[agent_id]
        for key, value in modifications.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
            else:
                # Store in tags for arbitrary metadata
                agent.tags[key] = value

        self.emit_event(
            {"type": "agent_modified", "agent_id": agent_id, "modifications": modifications}
        )

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
