"""Handler for building-related actions."""

from __future__ import annotations

from typing import Any

from core.buildings.base import Building
from core.buildings.parking import Parking
from core.buildings.site import Site
from core.types import BuildingID, NodeID, SiteID

from ..queues import create_building_created_signal
from .base import HandlerContext


class BuildingActionHandler:
    """Handler for building domain actions."""

    @staticmethod
    def handle_create(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle building.create action to add buildings to nodes."""
        # Validate building_type is present and is a string
        if "building_type" not in params:
            raise ValueError("building_type is required for building.create action")
        building_type_raw = params["building_type"]
        if not isinstance(building_type_raw, str):
            raise ValueError("building_type must be a string")

        # Validate common required parameters
        if "building_id" not in params:
            raise ValueError("building_id is required for building.create action")
        if "node_id" not in params:
            raise ValueError("node_id is required for building.create action")

        building_id_raw = params["building_id"]
        node_id_raw = params["node_id"]

        if not isinstance(building_id_raw, str):
            raise ValueError("building_id must be a string")
        if not isinstance(node_id_raw, int):
            raise ValueError("node_id must be an integer")

        building_id = BuildingID(building_id_raw)
        node_id = NodeID(node_id_raw)

        # Validate node exists
        graph = context.world.graph
        if node_id not in graph.nodes:
            raise ValueError(f"Node {node_id_raw} does not exist")

        # Validate building doesn't already exist
        if _building_exists(graph, building_id):
            raise ValueError(f"Building {building_id_raw} already exists")

        # Create building using factory pattern
        building = _create_building(building_type_raw, building_id, params)

        # Add building to node
        node = graph.nodes[node_id]
        node.add_building(building)
        context.logger.info(
            "Created %s building %s on node %s",
            building_type_raw,
            building_id_raw,
            node_id_raw,
        )

        try:
            context.signal_queue.put(
                create_building_created_signal(
                    building_data=building.to_dict(),
                    node_id=int(node_id),
                    tick=context.state.current_tick,
                ),
                timeout=1.0,
            )
        except Exception as exc:
            context.logger.error("Failed to emit building.created signal: %s", exc)
            raise


def _create_building(
    building_type: str, building_id: BuildingID, params: dict[str, Any]
) -> Building:
    """Factory function to create building instances based on type.

    Args:
        building_type: Type of building to create (e.g., "parking", "site")
        building_id: Unique identifier for the building
        params: Action parameters containing type-specific fields

    Returns:
        Building instance of the specified type

    Raises:
        ValueError: If building_type is unsupported or required parameters are missing
    """
    if building_type == "parking":
        if "capacity" not in params:
            raise ValueError("capacity is required for parking buildings")
        capacity_raw = params["capacity"]
        if not isinstance(capacity_raw, int):
            raise ValueError("capacity must be an integer")
        return Parking(id=building_id, capacity=capacity_raw)
    elif building_type == "site":
        # Validate required parameters
        if "name" not in params:
            raise ValueError("name is required for site buildings")
        if "activity_rate" not in params:
            raise ValueError("activity_rate is required for site buildings")

        name_raw = params["name"]
        activity_rate_raw = params["activity_rate"]

        if not isinstance(name_raw, str):
            raise ValueError("name must be a string")
        if not isinstance(activity_rate_raw, int | float):
            raise ValueError("activity_rate must be a float")
        activity_rate = float(activity_rate_raw)
        if activity_rate <= 0:
            raise ValueError("activity_rate must be greater than 0")

        # Handle optional destination_weights
        destination_weights: dict[SiteID, float] = {}
        if "destination_weights" in params:
            weights_raw = params["destination_weights"]
            if not isinstance(weights_raw, dict):
                raise ValueError("destination_weights must be a dictionary")
            # Convert string keys to SiteID and validate values
            for key, value in weights_raw.items():
                if not isinstance(key, str):
                    raise ValueError("destination_weights keys must be strings")
                if not isinstance(value, int | float):
                    raise ValueError("destination_weights values must be floats")
                destination_weights[SiteID(key)] = float(value)

        return Site(
            id=building_id,
            name=name_raw,
            activity_rate=activity_rate,
            destination_weights=destination_weights,
        )
    else:
        raise ValueError(
            f"Unsupported building type: {building_type}. Supported types: 'parking', 'site'."
        )


def _building_exists(graph: Any, building_id: BuildingID) -> bool:
    """Return True if the building identifier already exists in the graph."""
    for node in graph.nodes.values():
        for building in node.buildings:
            if building.id == building_id:
                return True
    return False
