"""Handler for map import/export actions."""

import base64
import binascii
import json
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

# File extension for SPINE map files
MAP_FILE_EXTENSION = ".smap"


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
        """Handle export map action (sends base64-encoded map file via WebSocket).

        Args:
            params: Action parameters (optional 'filename' for custom name)
            context: Handler context
        """
        try:
            # Get optional filename from params
            filename = params.get("filename", "map")
            if not filename.endswith(MAP_FILE_EXTENSION):
                filename += MAP_FILE_EXTENSION

            # Export graph structure as dictionary
            map_data = context.world.graph.to_dict()

            # Convert to JSON and encode to base64
            json_str = json.dumps(map_data, indent=2)
            file_content_base64 = base64.b64encode(json_str.encode("utf-8")).decode("ascii")

            _emit_signal(
                context,
                create_map_exported_signal(filename=filename, file_content=file_content_base64),
            )
            context.logger.info(f"Map exported via WebSocket: {filename}")
        except Exception as e:
            context.logger.error(f"Unexpected error exporting map: {e}", exc_info=True)
            _emit_error(context, f"Unexpected error exporting map: {e}")
            raise

    @staticmethod
    def handle_import(params: dict[str, Any], context: HandlerContext) -> None:
        """Handle import map action (receives base64-encoded map file via WebSocket).

        Args:
            params: Action parameters (required 'file_content' base64 string, optional 'filename')
            context: Handler context

        Raises:
            ValueError: If file_content is missing
        """
        if "file_content" not in params:
            raise ValueError("file_content is required for map.import action")

        file_content_base64 = params["file_content"]
        if not isinstance(file_content_base64, str):
            raise ValueError("file_content must be a base64-encoded string")

        filename = params.get("filename", "unknown.smap")

        # Stop simulation if it's running
        if context.state.running:
            context.logger.info("Stopping simulation to import map")
            context.state.stop()

        try:
            # Decode base64 and parse JSON
            json_str = base64.b64decode(file_content_base64).decode("utf-8")
            map_data = json.loads(json_str)

            # Import graph from dictionary
            from world.graph.graph import Graph

            new_graph = Graph.from_dict(map_data)
            context.world.graph = new_graph
            _emit_signal(context, create_map_imported_signal(filename))
            context.logger.info(f"Map imported via WebSocket: {filename}")
        except (binascii.Error, UnicodeDecodeError) as e:
            context.logger.error(f"Failed to decode base64 map data: {e}")
            _emit_error(context, f"Invalid base64 encoding: {e}")
            raise ValueError(f"Invalid base64 encoding: {e}") from e
        except json.JSONDecodeError as e:
            context.logger.error(f"Failed to parse map JSON: {e}")
            _emit_error(context, f"Invalid JSON format: {e}")
            raise ValueError(f"Invalid JSON format: {e}") from e
        except ValueError as e:
            context.logger.error(f"Failed to import map: {e}")
            _emit_error(context, f"Failed to import map: {e}")
            raise
        except Exception as e:
            context.logger.error(f"Unexpected error importing map: {e}", exc_info=True)
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

            # Count generated sites and parkings using efficient O(N) node count index
            from core.buildings.parking import Parking
            from core.buildings.site import Site

            generated_sites = sum(
                node.get_building_count_by_type(Site) for node in new_graph.nodes.values()
            )

            generated_parkings = sum(
                node.get_building_count_by_type(Parking) for node in new_graph.nodes.values()
            )

            # Emit success signal with generation info using DTO for type safety
            from world.sim.signal_dtos.map_created import MapCreatedSignalData

            # Use model_dump to get all generation params as dict, then add additional fields
            signal_data = MapCreatedSignalData(
                **gen_params.model_dump(),
                generated_nodes=new_graph.get_node_count(),
                generated_edges=new_graph.get_edge_count(),
                generated_sites=generated_sites,
                generated_parkings=generated_parkings,
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
