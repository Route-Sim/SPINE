"""DTO for map.created signal data."""

from typing import Any

from pydantic import Field, field_validator

from .base import SignalData


class MapCreatedSignalData(SignalData):
    """DTO for map.created signal data.

    This signal is emitted when a new map is generated via the map.create action.
    It contains all generation parameters, results, and the complete graph structure.
    """

    # Map dimensions
    map_width: float = Field(gt=0, description="Map width in kilometers")
    map_height: float = Field(gt=0, description="Map height in kilometers")

    # Urban structure parameters
    num_major_centers: int = Field(ge=1, description="Number of major urban centers")
    minor_per_major: float = Field(ge=0, description="Minor centers per major center")
    center_separation: float = Field(gt=0, description="Minimum separation between centers")
    urban_sprawl: float = Field(gt=0, description="Urban sprawl radius")

    # Density parameters
    local_density: float = Field(gt=0, description="Local road network density")
    rural_density: float = Field(ge=0, description="Rural area road density")

    # Connectivity parameters
    intra_connectivity: float = Field(ge=0, le=1, description="Within-center connectivity")
    inter_connectivity: int = Field(ge=1, description="Between-center connectivity level")
    arterial_ratio: float = Field(ge=0, le=1, description="Ratio of arterial roads")
    gridness: float = Field(
        ge=0, le=1, description="Grid-like structure factor (0=organic, 1=grid)"
    )

    # Highway and road parameters
    ring_road_prob: float = Field(
        ge=0, le=1, description="Probability of ring roads around centers"
    )
    highway_curviness: float = Field(
        ge=0, le=1, description="Highway curviness (0=straight, 1=curved)"
    )

    # Site generation parameters
    rural_settlement_prob: float = Field(ge=0, le=1, description="Probability of rural settlements")
    urban_sites_per_km2: float = Field(ge=0, description="Urban site density per km²")
    rural_sites_per_km2: float = Field(ge=0, description="Rural site density per km²")
    urban_activity_rate_range: list[float] = Field(
        min_length=2, max_length=2, description="[min, max] activity rate for urban sites"
    )
    rural_activity_rate_range: list[float] = Field(
        min_length=2, max_length=2, description="[min, max] activity rate for rural sites"
    )

    # Generation seed
    seed: int = Field(description="Random seed used for generation")

    # Generation results
    generated_nodes: int = Field(ge=0, description="Number of nodes generated")
    generated_edges: int = Field(ge=0, description="Number of edges generated")
    generated_sites: int = Field(ge=0, description="Number of sites generated")

    # Graph structure
    graph: dict[str, Any] = Field(description="Complete graph structure as dict")

    @field_validator("urban_activity_rate_range", "rural_activity_rate_range")
    @classmethod
    def validate_activity_range(cls, v: list[float]) -> list[float]:
        """Validate that activity rate ranges are valid [min, max] pairs."""
        if len(v) != 2:
            raise ValueError("Activity rate range must contain exactly 2 values")
        if any(x < 0 for x in v):
            raise ValueError("Activity rate values must be non-negative")
        if v[0] > v[1]:
            raise ValueError("Activity rate min must be <= max")
        return v
