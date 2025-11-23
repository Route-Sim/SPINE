"""DTO for map.created signal data."""

from typing import Any

from pydantic import Field

from world.generation.params import GenerationParams


class MapCreatedSignalData(GenerationParams):
    """DTO for map.created signal data.

    This signal is emitted when a new map is generated via the map.create action.
    It inherits all generation parameters from GenerationParams and adds generation
    results and the complete graph structure. This maintains a flat field structure
    while eliminating duplication.
    """

    # Generation results (additional fields beyond GenerationParams)
    generated_nodes: int = Field(ge=0, description="Number of nodes generated")
    generated_edges: int = Field(ge=0, description="Number of edges generated")
    generated_sites: int = Field(ge=0, description="Number of site buildings generated")
    generated_parkings: int = Field(ge=0, description="Number of parking buildings generated")

    # Graph structure
    graph: dict[str, Any] = Field(description="Complete graph structure as dict")
