"""Map file management for export and import operations."""

import os
import re
from pathlib import Path

from world.graph.graph import Graph


def sanitize_map_name(name: str) -> str:
    """Sanitize map name to prevent path traversal and allow only safe characters.

    Args:
        name: Original map name

    Returns:
        Sanitized map name containing only alphanumeric characters, underscores, and hyphens
    """
    # Remove path separators and other dangerous characters
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")
    # Ensure non-empty result
    if not sanitized:
        sanitized = "unnamed_map"
    return sanitized


def get_maps_directory() -> str:
    """Get the absolute path to the maps directory.

    Returns:
        Absolute path to the maps directory in the workspace root
    """
    # Get the workspace root (parent of the world directory)
    workspace_root = Path(__file__).parent.parent.parent
    maps_dir = workspace_root / "maps"
    return str(maps_dir)


def ensure_maps_directory() -> None:
    """Create the maps directory if it doesn't exist."""
    maps_dir = get_maps_directory()
    os.makedirs(maps_dir, exist_ok=True)


def get_map_filepath(map_name: str) -> str:
    """Get the full filepath for a map file.

    Args:
        map_name: Sanitized map name

    Returns:
        Full filepath to the map file
    """
    ensure_maps_directory()
    maps_dir = get_maps_directory()
    return os.path.join(maps_dir, f"{map_name}.graphml")


def export_map(graph: Graph, map_name: str) -> None:
    """Export a graph to a GraphML file.

    Args:
        graph: Graph instance to export
        map_name: Name for the map file (will be sanitized)

    Raises:
        ValueError: If the map file already exists
        OSError: If there's an error writing the file
    """
    sanitized_name = sanitize_map_name(map_name)
    filepath = get_map_filepath(sanitized_name)

    # Check if file already exists
    if os.path.exists(filepath):
        raise ValueError(f"Map file already exists: {sanitized_name}")

    # Export the graph
    graph.to_graphml(filepath)


def import_map(map_name: str) -> Graph:
    """Import a graph from a GraphML file.

    Args:
        map_name: Name of the map file to import (will be sanitized)

    Returns:
        Imported Graph instance

    Raises:
        FileNotFoundError: If the map file doesn't exist
        ValueError: If there's an error parsing the GraphML file
    """
    sanitized_name = sanitize_map_name(map_name)
    filepath = get_map_filepath(sanitized_name)

    # Check if file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Map file not found: {sanitized_name}")

    # Import the graph
    return Graph.from_graphml(filepath)


def map_exists(map_name: str) -> bool:
    """Check if a map file exists.

    Args:
        map_name: Name of the map file to check (will be sanitized)

    Returns:
        True if the map file exists, False otherwise
    """
    sanitized_name = sanitize_map_name(map_name)
    filepath = get_map_filepath(sanitized_name)
    return os.path.exists(filepath)
