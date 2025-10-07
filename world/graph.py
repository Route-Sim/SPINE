from dataclasses import dataclass

from ..core.ids import EdgeID


@dataclass
class TimeBand:
    start_min: int
    end_min: int
    speed_mult: float = 1.0
    cap_mult: float = 1.0


@dataclass
class Edge:
    id: EdgeID
    u: int
    v: int
    length_m: float
    base_speed_mps: float
    base_cap_vph: float
    lanes: int = 1
    bands: list[TimeBand] | None = None


class RoadGraph:
    def __init__(self) -> None:
        self.edges: dict[EdgeID, Edge] = {}
        self.out_adj: dict[int, list[EdgeID]] = {}  # node -> outgoing edges
        # optionally, store polylines for rendering

    def speed_at(self, e: EdgeID, now_min: int) -> float:
        edge = self.edges[e]
        m = 1.0
        if edge.bands:
            for b in edge.bands:
                if b.start_min <= now_min <= b.end_min:
                    m = b.speed_mult
                    break
        return edge.base_speed_mps * m

    def capacity_at(self, e: EdgeID, now_min: int) -> float:
        edge = self.edges[e]
        m = 1.0
        if edge.bands:
            for b in edge.bands:
                if b.start_min <= now_min <= b.end_min:
                    m = b.cap_mult
                    break
        return edge.base_cap_vph * edge.lanes * m
