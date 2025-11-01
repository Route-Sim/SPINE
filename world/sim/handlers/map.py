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
            params: Action parameters (required: width, height, nodes, density, urban_areas)
            context: Handler context

        Raises:
            ValueError: If parameters are missing, invalid, or simulation is running
        """
        # Validate required parameters
        required_params = ["width", "height", "nodes", "density", "urban_areas"]
        for param in required_params:
            if param not in params:
                raise ValueError(f"{param} is required for map.create action")

        # Validate parameter types
        width = params["width"]
        height = params["height"]
        nodes = params["nodes"]
        density = params["density"]
        urban_areas = params["urban_areas"]

        if not isinstance(width, int | float) or width <= 0:
            raise ValueError("width must be a positive number")
        if not isinstance(height, int | float) or height <= 0:
            raise ValueError("height must be a positive number")
        if not isinstance(nodes, int) or not (0 <= nodes <= 100):
            raise ValueError("nodes must be an integer between 0 and 100")
        if not isinstance(density, int) or not (0 <= density <= 100):
            raise ValueError("density must be an integer between 0 and 100")
        if not isinstance(urban_areas, int) or urban_areas <= 0:
            raise ValueError("urban_areas must be a positive integer")

        # Reject if simulation is running
        if context.state.running:
            error_msg = "Cannot create map while simulation is running"
            context.logger.warning(error_msg)
            _emit_error(context, error_msg)
            raise ValueError(error_msg)

        try:
            # Create generation parameters
            gen_params = GenerationParams(
                width=float(width),
                height=float(height),
                nodes=nodes,
                density=density,
                urban_areas=urban_areas,
            )

            # Generate the map
            generator = MapGenerator(gen_params)
            new_graph = generator.generate()

            # Replace the world's graph
            context.world.graph = new_graph

            # Emit success signal with generation info
            signal_data = {
                "width": width,
                "height": height,
                "nodes": nodes,
                "density": density,
                "urban_areas": urban_areas,
                "generated_nodes": new_graph.get_node_count(),
                "generated_edges": new_graph.get_edge_count(),
            }
            _emit_signal(context, create_map_created_signal(signal_data))
            context.logger.info(f"Map created: {signal_data}")

        except ValueError as e:
            context.logger.error(f"Failed to create map: {e}")
            _emit_error(context, f"Failed to create map: {e}")
            raise
        except Exception as e:
            context.logger.error(f"Unexpected error creating map: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error creating map: {e}")
            raise
