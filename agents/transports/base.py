# spine/agents/base.py
from dataclasses import dataclass, field
from typing import Any

from agents.base import AgentBase
from core.fsm import VehicleState
from core.messages import Msg
from core.types import EdgeID, LegID
from world.world import World


@dataclass
class EdgePos:
    edge: EdgeID
    s_m: float = 0.0  # distance along edge in meters


@dataclass
class PlanLeg:
    leg_id: LegID
    mode: str  # "truck" | "train"
    path: list[EdgeID]  # sequence of edges
    current_idx: int = 0  # index within path


@dataclass
class Telemetry:
    distance_m: float = 0.0
    fuel_j: float = 0.0
    co2_kg: float = 0.0


@dataclass
class Transport(AgentBase):
    state: VehicleState = VehicleState.IDLE
    pos: EdgePos | None = None
    vel_mps: float = 0.0
    capacity: float = 0.0  # e.g., pallets/tons
    load: float = 0.0
    eta_s: int | None = None
    duty_end_s: int | None = None  # for hours-of-service
    plan: PlanLeg | None = None
    queueing: bool = False
    telemetry: Telemetry = field(default_factory=Telemetry)
    policy: dict[str, Any] = field(default_factory=dict)  # thresholds, weights

    # --- movement on current edge ---
    def advance(self, world: World, dt_s: float) -> None:
        if not self.pos:
            return
        g = world.graph
        now_min = world.time_min()
        speed = g.speed_at(self.pos.edge, now_min)
        # allow per-vehicle caps
        self.vel_mps = min(speed, self.policy.get("max_speed_mps", 1e9))
        self.pos.s_m += self.vel_mps * dt_s

        edge = g.edges[self.pos.edge]
        if self.pos.s_m >= edge.length_m:
            self.pos.s_m -= edge.length_m
            self._try_enter_next_edge(world)

    def _try_enter_next_edge(self, world: World) -> None:
        """Request transition to next edge in plan; node capacity rules decide."""
        if not self.plan or not self.pos:
            return
        if self.plan.current_idx + 1 >= len(self.plan.path):
            # end of leg
            self.state = VehicleState.AT_NODE
            world.emit_event({"type": "arrived", "id": self.id, "leg": self.plan.leg_id})
            return
        next_e = self.plan.path[self.plan.current_idx + 1]
        # ask node/edge controller for permission (capacity/queue)
        ok = world.traffic.allow_enter(
            self.id, from_edge=self.plan.path[self.plan.current_idx], to_edge=next_e
        )
        if ok:
            self.plan.current_idx += 1
            self.pos.edge = next_e
            self.queueing = False
        else:
            self.queueing = True  # will try again next tick

    # --- bidding helpers (truck overrides) ---
    def estimate_marginal_cost(self, world: World, path: list[EdgeID]) -> dict[str, float]:
        """Return {cost, eta, risk} for inserting a small leg; simplistic default."""
        # naive free-flow estimate; truck/train override with better models
        t_s = 0.0
        dist = 0.0
        for e in path:
            edge = world.graph.edges[e]
            v = world.graph.speed_at(e, world.time_min())
            t_s += edge.length_m / max(v, 0.1)
            dist += edge.length_m
        cost = (dist / 1000.0) * self.policy.get("cost_per_km", 1.0)
        return {"cost": cost, "eta": world.now_s() + int(t_s), "risk": 0.1}

    # --- agent API ---
    def decide(self, world: World) -> None:
        # consume messages and act on local FSM
        for m in self.inbox:
            if m.typ == "auction" and self._can_bid(world, m):
                est = self.estimate_marginal_cost(world, m.body["path"])
                self.outbox.append(
                    Msg(src=self.id, dst=m.src, typ="bid", body={"leg_id": m.body["leg_id"], **est})
                )
            elif m.typ == "award" and m.body.get("leg_id"):
                # accept if feasible; set plan and state
                self.plan = m.body["plan"]
                self.state = VehicleState.ASSIGNED
                self.outbox.append(
                    Msg(src=self.id, dst=m.src, typ="ack_award", body={"leg_id": m.body["leg_id"]})
                )
            elif m.typ == "reroute":
                # request recompute from routing policy
                new_path = world.router.replan(self, constraints=m.body)
                if new_path and self.plan:
                    self.plan.path = new_path
                    self.plan.current_idx = 0
        self.inbox.clear()

        # movement (if enroute)
        if self.state in (VehicleState.ENROUTE, VehicleState.ASSIGNED) and self.plan:
            self.state = VehicleState.ENROUTE
            self.advance(world, world.dt_s)

    def _can_bid(self, world: World, m: Msg) -> bool:
        # hours-of-service, capacity, distance caps, etc.
        _ = m  # Keep parameter for future use
        return self.load <= self.capacity and (
            self.duty_end_s is None or world.now_s() < self.duty_end_s
        )

    def serialize_diff(self) -> dict[str, str]:
        d = {"id": self.id, "kind": self.kind, "state": self.state.name}
        if self.pos:
            d.update({"edge": str(int(self.pos.edge)), "s": str(self.pos.s_m)})
        return d
