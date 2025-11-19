"""Handler for map import/export actions."""

from typing import Any

from pydantic import ValidationError

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
            params: Action parameters (all GenerationParams fields)
            context: Handler context

        Raises:
            ValueError: If parameters are missing, invalid, or simulation is running
        """
        # Reject if simulation is running
        if context.state.running:
            error_msg = "Cannot create map while simulation is running"
            context.logger.warning(error_msg)
            _emit_error(context, error_msg)
            raise ValueError(error_msg)

        try:
            # Convert activity rate ranges from list to tuple for Pydantic validation
            params_copy = params.copy()
            if "urban_activity_rate_range" in params_copy and isinstance(
                params_copy["urban_activity_rate_range"], list
            ):
                params_copy["urban_activity_rate_range"] = tuple(
                    params_copy["urban_activity_rate_range"]
                )
            if "rural_activity_rate_range" in params_copy and isinstance(
                params_copy["rural_activity_rate_range"], list
            ):
                params_copy["rural_activity_rate_range"] = tuple(
                    params_copy["rural_activity_rate_range"]
                )

            # Create and validate generation parameters using Pydantic
            # This automatically handles all validation
            gen_params = GenerationParams(**params_copy)

            # Generate the map
            generator = MapGenerator(gen_params)
            new_graph = generator.generate()

            # Replace the world's graph and store generation parameters
            context.world.graph = new_graph
            context.world.generation_params = gen_params

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

            # Use model_dump to get all generation params as dict, then add additional fields
            signal_data = MapCreatedSignalData(
                **gen_params.model_dump(),
                generated_nodes=new_graph.get_node_count(),
                generated_edges=new_graph.get_edge_count(),
                generated_sites=generated_sites,
                graph=new_graph.to_dict(),
            )
            _emit_signal(context, create_map_created_signal(signal_data))
            context.logger.info(f"Map created with {signal_data.generated_nodes} nodes")

        except ValidationError as e:
            # Convert Pydantic validation errors to user-friendly messages
            error_messages = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"{field}: {msg}")
            error_msg = f"Invalid parameters: {'; '.join(error_messages)}"
            context.logger.error(f"Validation error creating map: {error_msg}")
            _emit_error(context, error_msg)
            raise ValueError(error_msg) from e
        except ValueError as e:
            context.logger.error(f"Failed to create map: {e}")
            _emit_error(context, f"Failed to create map: {e}")
            raise
        except Exception as e:
            context.logger.error(f"Unexpected error creating map: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error creating map: {e}")
            raise
