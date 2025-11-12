"""Handler for building-related actions."""

from __future__ import annotations

from typing import Any

from core.buildings.parking import Parking
from core.types import BuildingID, NodeID

from ..queues import create_building_created_signal
from .base import HandlerContext


class BuildingActionHandler:
    """Handler for building domain actions."""

    @staticmethod
    def handle_create(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle building.create action to add parking facilities to nodes."""
        building_type = params.get("building_type", "parking")
        if building_type != "parking":
            raise ValueError("Only parking buildings are supported at this time")

        if "building_id" not in params:
            raise ValueError("building_id is required for building.create action")
        if "node_id" not in params:
            raise ValueError("node_id is required for building.create action")
        if "capacity" not in params:
            raise ValueError("capacity is required for building.create action")

        building_id_raw = params["building_id"]
        node_id_raw = params["node_id"]
        capacity_raw = params["capacity"]

        if not isinstance(building_id_raw, str):
            raise ValueError("building_id must be a string")
        if not isinstance(node_id_raw, int):
            raise ValueError("node_id must be an integer")
        if not isinstance(capacity_raw, int):
            raise ValueError("capacity must be an integer")

        building_id = BuildingID(building_id_raw)
        node_id = NodeID(node_id_raw)
        capacity = capacity_raw

        graph = context.world.graph
        if node_id not in graph.nodes:
            raise ValueError(f"Node {node_id_raw} does not exist")

        if _building_exists(graph, building_id):
            raise ValueError(f"Building {building_id_raw} already exists")

        parking = Parking(id=building_id, capacity=capacity)

        node = graph.nodes[node_id]
        node.add_building(parking)
        context.logger.info(
            "Created parking building %s on node %s with capacity %s",
            building_id_raw,
            node_id_raw,
            capacity,
        )

        try:
            context.signal_queue.put(
                create_building_created_signal(
                    building_data=parking.to_dict(),
                    node_id=int(node_id),
                    tick=context.state.current_tick,
                ),
                timeout=1.0,
            )
        except Exception as exc:
            context.logger.error("Failed to emit building.created signal: %s", exc)
            raise


def _building_exists(graph: Any, building_id: BuildingID) -> bool:
    """Return True if the building identifier already exists in the graph."""
    for node in graph.nodes.values():
        for building in node.buildings:
            if building.id == building_id:
                return True
    return False
