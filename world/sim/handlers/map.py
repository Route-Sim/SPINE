"""Handler for map import/export actions."""

from typing import Any

from world.generation import GenerationParams, MapGenerator

from ..queues import (
    create_error_signal,
    create_map_created_signal,
    create_map_exported_signal,
    create_map_imported_signal,
)
from .base import HandlerContext


def _emit_error(context: HandlerContext, error_message: str) -> None:
    """Emit an error signal."""
    try:
        context.signal_queue.put(
            create_error_signal(error_message, context.state.current_tick), timeout=1.0
        )
    except Exception as e:
        context.logger.error(f"Failed to emit error signal: {e}")


def _emit_signal(context: HandlerContext, signal: Any) -> None:
    """Emit a signal to the signal queue."""
    try:
        context.signal_queue.put(signal, timeout=1.0)
    except Exception as e:
        context.logger.error(f"Failed to emit signal: {e}")


class MapActionHandler:
    """Handler for map management actions."""

    @staticmethod
    def handle_export(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle export map action.

        Args:
            params: Action parameters (required 'map_name')
            context: Handler context

        Raises:
            ValueError: If map_name is missing or simulation is running
        """
        if "map_name" not in params:
            raise ValueError("map_name is required for map.export action")

        map_name = params["map_name"]
        if not isinstance(map_name, str):
            raise ValueError("map_name must be a string")

        # Reject if simulation is running
        if context.state.running:
            error_msg = "Cannot export map while simulation is running"
            context.logger.warning(error_msg)
            _emit_error(context, error_msg)
            raise ValueError(error_msg)

        try:
            context.world.export_graph(map_name)
            _emit_signal(context, create_map_exported_signal(map_name))
            context.logger.info(f"Map exported: {map_name}")
        except ValueError as e:
            context.logger.error(f"Failed to export map {map_name}: {e}")
            _emit_error(context, f"Failed to export map: {e}")
            raise
        except Exception as e:
            context.logger.error(f"Unexpected error exporting map {map_name}: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error exporting map: {e}")
            raise

    @staticmethod
    def handle_import(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle import map action.

        Args:
            params: Action parameters (required 'map_name')
            context: Handler context

        Raises:
            ValueError: If map_name is missing or simulation is running
            FileNotFoundError: If map file not found
        """
        if "map_name" not in params:
            raise ValueError("map_name is required for map.import action")

        map_name = params["map_name"]
        if not isinstance(map_name, str):
            raise ValueError("map_name must be a string")

        # Reject if simulation is running
        if context.state.running:
            error_msg = "Cannot import map while simulation is running"
            context.logger.warning(error_msg)
            _emit_error(context, error_msg)
            raise ValueError(error_msg)

        try:
            context.world.import_graph(map_name)
            _emit_signal(context, create_map_imported_signal(map_name))
            context.logger.info(f"Map imported: {map_name}")
        except FileNotFoundError as e:
            context.logger.error(f"Map file not found: {e}")
            _emit_error(context, f"Map file not found: {map_name}")
            raise
        except ValueError as e:
            context.logger.error(f"Failed to import map {map_name}: {e}")
            _emit_error(context, f"Failed to import map: {e}")
            raise
        except Exception as e:
            context.logger.error(f"Unexpected error importing map {map_name}: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error importing map: {e}")
            raise

    @staticmethod
    def handle_create(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle create map action.

        Args:
            params: Action parameters (required: map_width, map_height, num_major_centers,
                    minor_per_major, center_separation, urban_sprawl, local_density,
                    rural_density, intra_connectivity, inter_connectivity, arterial_ratio,
                    gridness, ring_road_prob, highway_curviness, rural_settlement_prob,
                    urban_sites_per_km2, rural_sites_per_km2, urban_activity_rate_range,
                    rural_activity_rate_range, seed)
            context: Handler context

        Raises:
            ValueError: If parameters are missing, invalid, or simulation is running
        """
        # Validate required parameters
        required_params = [
            "map_width",
            "map_height",
            "num_major_centers",
            "minor_per_major",
            "center_separation",
            "urban_sprawl",
            "local_density",
            "rural_density",
            "intra_connectivity",
            "inter_connectivity",
            "arterial_ratio",
            "gridness",
            "ring_road_prob",
            "highway_curviness",
            "rural_settlement_prob",
            "urban_sites_per_km2",
            "rural_sites_per_km2",
            "urban_activity_rate_range",
            "rural_activity_rate_range",
            "seed",
        ]
        for param in required_params:
            if param not in params:
                raise ValueError(f"{param} is required for map.create action")

        # Extract and validate parameters
        map_width = params["map_width"]
        map_height = params["map_height"]
        num_major_centers = params["num_major_centers"]
        minor_per_major = params["minor_per_major"]
        center_separation = params["center_separation"]
        urban_sprawl = params["urban_sprawl"]
        local_density = params["local_density"]
        rural_density = params["rural_density"]
        intra_connectivity = params["intra_connectivity"]
        inter_connectivity = params["inter_connectivity"]
        arterial_ratio = params["arterial_ratio"]
        gridness = params["gridness"]
        ring_road_prob = params["ring_road_prob"]
        highway_curviness = params["highway_curviness"]
        rural_settlement_prob = params["rural_settlement_prob"]
        urban_sites_per_km2 = params["urban_sites_per_km2"]
        rural_sites_per_km2 = params["rural_sites_per_km2"]
        urban_activity_rate_range = params["urban_activity_rate_range"]
        rural_activity_rate_range = params["rural_activity_rate_range"]
        seed = params["seed"]

        # Type validation
        if not isinstance(map_width, int | float) or map_width <= 0:
            raise ValueError("map_width must be a positive number")
        if not isinstance(map_height, int | float) or map_height <= 0:
            raise ValueError("map_height must be a positive number")
        if not isinstance(num_major_centers, int) or num_major_centers < 1:
            raise ValueError("num_major_centers must be a positive integer")
        if not isinstance(minor_per_major, int | float) or minor_per_major < 0:
            raise ValueError("minor_per_major must be a non-negative number")
        if not isinstance(center_separation, int | float) or center_separation <= 0:
            raise ValueError("center_separation must be a positive number")
        if not isinstance(urban_sprawl, int | float) or urban_sprawl <= 0:
            raise ValueError("urban_sprawl must be a positive number")
        if not isinstance(local_density, int | float) or local_density <= 0:
            raise ValueError("local_density must be a positive number")
        if not isinstance(rural_density, int | float) or rural_density < 0:
            raise ValueError("rural_density must be a non-negative number")
        if not isinstance(intra_connectivity, int | float) or not (0 <= intra_connectivity <= 1):
            raise ValueError("intra_connectivity must be between 0 and 1")
        if not isinstance(inter_connectivity, int) or inter_connectivity < 1:
            raise ValueError("inter_connectivity must be a positive integer")
        if not isinstance(arterial_ratio, int | float) or not (0 <= arterial_ratio <= 1):
            raise ValueError("arterial_ratio must be between 0 and 1")
        if not isinstance(gridness, int | float) or not (0 <= gridness <= 1):
            raise ValueError("gridness must be between 0 and 1")
        if not isinstance(ring_road_prob, int | float) or not (0 <= ring_road_prob <= 1):
            raise ValueError("ring_road_prob must be between 0 and 1")
        if not isinstance(highway_curviness, int | float) or not (0 <= highway_curviness <= 1):
            raise ValueError("highway_curviness must be between 0 and 1")
        if not isinstance(rural_settlement_prob, int | float) or not (
            0 <= rural_settlement_prob <= 1
        ):
            raise ValueError("rural_settlement_prob must be between 0 and 1")
        if not isinstance(urban_sites_per_km2, int | float) or urban_sites_per_km2 < 0:
            raise ValueError("urban_sites_per_km2 must be a non-negative number")
        if not isinstance(rural_sites_per_km2, int | float) or rural_sites_per_km2 < 0:
            raise ValueError("rural_sites_per_km2 must be a non-negative number")
        if (
            not isinstance(urban_activity_rate_range, list)
            or len(urban_activity_rate_range) != 2
            or not all(isinstance(x, int | float) for x in urban_activity_rate_range)
        ):
            raise ValueError("urban_activity_rate_range must be a list of 2 numbers")
        if urban_activity_rate_range[0] < 0 or urban_activity_rate_range[1] < 0:
            raise ValueError("urban_activity_rate_range values must be non-negative")
        if urban_activity_rate_range[0] > urban_activity_rate_range[1]:
            raise ValueError("urban_activity_rate_range min must be <= max")
        if (
            not isinstance(rural_activity_rate_range, list)
            or len(rural_activity_rate_range) != 2
            or not all(isinstance(x, int | float) for x in rural_activity_rate_range)
        ):
            raise ValueError("rural_activity_rate_range must be a list of 2 numbers")
        if rural_activity_rate_range[0] < 0 or rural_activity_rate_range[1] < 0:
            raise ValueError("rural_activity_rate_range values must be non-negative")
        if rural_activity_rate_range[0] > rural_activity_rate_range[1]:
            raise ValueError("rural_activity_rate_range min must be <= max")
        if not isinstance(seed, int):
            raise ValueError("seed must be an integer")

        # Reject if simulation is running
        if context.state.running:
            error_msg = "Cannot create map while simulation is running"
            context.logger.warning(error_msg)
            _emit_error(context, error_msg)
            raise ValueError(error_msg)

        try:
            # Create generation parameters
            gen_params = GenerationParams(
                map_width=float(map_width),
                map_height=float(map_height),
                num_major_centers=num_major_centers,
                minor_per_major=float(minor_per_major),
                center_separation=float(center_separation),
                urban_sprawl=float(urban_sprawl),
                local_density=float(local_density),
                rural_density=float(rural_density),
                intra_connectivity=float(intra_connectivity),
                inter_connectivity=inter_connectivity,
                arterial_ratio=float(arterial_ratio),
                gridness=float(gridness),
                ring_road_prob=float(ring_road_prob),
                highway_curviness=float(highway_curviness),
                rural_settlement_prob=float(rural_settlement_prob),
                urban_sites_per_km2=float(urban_sites_per_km2),
                rural_sites_per_km2=float(rural_sites_per_km2),
                urban_activity_rate_range=(
                    float(urban_activity_rate_range[0]),
                    float(urban_activity_rate_range[1]),
                ),
                rural_activity_rate_range=(
                    float(rural_activity_rate_range[0]),
                    float(rural_activity_rate_range[1]),
                ),
                seed=seed,
            )

            # Generate the map
            generator = MapGenerator(gen_params)
            new_graph = generator.generate()

            # Replace the world's graph
            context.world.graph = new_graph

            # Count generated sites
            from core.buildings.site import Site

            generated_sites = sum(
                1
                for node in new_graph.nodes.values()
                for building in node.buildings
                if isinstance(building, Site)
            )

            # Emit success signal with generation info using DTO for type safety
            from world.sim.signal_dtos.map_created import MapCreatedSignalData

            signal_data = MapCreatedSignalData(
                map_width=map_width,
                map_height=map_height,
                num_major_centers=num_major_centers,
                minor_per_major=minor_per_major,
                center_separation=center_separation,
                urban_sprawl=urban_sprawl,
                local_density=local_density,
                rural_density=rural_density,
                intra_connectivity=intra_connectivity,
                inter_connectivity=inter_connectivity,
                arterial_ratio=arterial_ratio,
                gridness=gridness,
                ring_road_prob=ring_road_prob,
                highway_curviness=highway_curviness,
                rural_settlement_prob=rural_settlement_prob,
                urban_sites_per_km2=urban_sites_per_km2,
                rural_sites_per_km2=rural_sites_per_km2,
                urban_activity_rate_range=urban_activity_rate_range,
                rural_activity_rate_range=rural_activity_rate_range,
                seed=seed,
                generated_nodes=new_graph.get_node_count(),
                generated_edges=new_graph.get_edge_count(),
                generated_sites=generated_sites,
                graph=new_graph.to_dict(),
            )
            _emit_signal(context, create_map_created_signal(signal_data))
            context.logger.info(f"Map created with {signal_data.generated_nodes} nodes")

        except ValueError as e:
            context.logger.error(f"Failed to create map: {e}")
            _emit_error(context, f"Failed to create map: {e}")
            raise
        except Exception as e:
            context.logger.error(f"Unexpected error creating map: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error creating map: {e}")
            raise
