"""Pydantic models for map generation parameters."""

from pydantic import BaseModel, Field, field_validator


class GenerationParams(BaseModel):
    """Parameters for hierarchical procedural map generation.

    This Pydantic model provides automatic validation for all generation parameters.
    All fields use declarative constraints for validation instead of manual checks.
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
    urban_activity_rate_range: tuple[float, float] = Field(
        description="[min, max] activity rate for urban sites (packages/hour)"
    )
    rural_activity_rate_range: tuple[float, float] = Field(
        description="[min, max] activity rate for rural sites (packages/hour)"
    )

    # Parking generation parameters
    urban_parkings_per_km2: float = Field(ge=0, description="Urban parking density per km²")
    rural_parkings_per_km2: float = Field(ge=0, description="Rural parking density per km²")

    # Gas station generation parameters
    urban_gas_stations_per_km2: float = Field(ge=0, description="Urban gas station density per km²")
    rural_gas_stations_per_km2: float = Field(ge=0, description="Rural gas station density per km²")
    gas_station_capacity_range: tuple[int, int] = Field(
        description="[min, max] fuel places at gas stations"
    )
    gas_station_cost_factor_range: tuple[float, float] = Field(
        description="[min, max] cost factor multiplier for gas station prices"
    )

    # Generation seed
    seed: int = Field(description="Random seed used for generation")

    @field_validator("urban_activity_rate_range", "rural_activity_rate_range")
    @classmethod
    def validate_activity_range(cls, v: tuple[float, float]) -> tuple[float, float]:
        """Validate that activity rate ranges are valid [min, max] pairs."""
        if len(v) != 2:
            raise ValueError("Activity rate range must contain exactly 2 values")
        if any(x < 0 for x in v):
            raise ValueError("Activity rate values must be non-negative")
        if v[0] > v[1]:
            raise ValueError("Activity rate min must be <= max")
        return v

    @field_validator("gas_station_capacity_range")
    @classmethod
    def validate_capacity_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Validate that gas station capacity range is a valid [min, max] pair."""
        if len(v) != 2:
            raise ValueError("Gas station capacity range must contain exactly 2 values")
        if any(x < 1 for x in v):
            raise ValueError("Gas station capacity values must be at least 1")
        if v[0] > v[1]:
            raise ValueError("Gas station capacity min must be <= max")
        return v

    @field_validator("gas_station_cost_factor_range")
    @classmethod
    def validate_cost_factor_range(cls, v: tuple[float, float]) -> tuple[float, float]:
        """Validate that gas station cost factor range is a valid [min, max] pair."""
        if len(v) != 2:
            raise ValueError("Gas station cost factor range must contain exactly 2 values")
        if any(x <= 0 for x in v):
            raise ValueError("Gas station cost factor values must be positive")
        if v[0] > v[1]:
            raise ValueError("Gas station cost factor min must be <= max")
        return v
