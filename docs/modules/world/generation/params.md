---
title: "Generation Parameters"
summary: "Defines the Pydantic model that validates and documents all parameters controlling world generation, including map dimensions, urban structure, road density, site placement, and parking generation."
source_paths:
  - "world/generation/params.py"
last_updated: "2025-11-23"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../../SUMMARY.md"
  siblings:
    - "generator.md"
---

# Generation Parameters

> **Purpose:** This module provides a Pydantic `GenerationParams` model that encapsulates all configuration values for procedural map generation. It ensures type safety, validation, and self-documentation for the world generation process.

## Context & Motivation
- Problem solved: Centralise and validate all generation parameters in a single typed model, eliminating ad-hoc parameter passing and manual validation.
- Requirements and constraints: Parameters must be validated at construction time, with clear constraints (e.g., positive values, valid ranges) enforced declaratively.
- Dependencies and assumptions: Uses Pydantic v2 for validation; consumed by `WorldGenerator` during map creation.

## Responsibilities & Boundaries
- In-scope: Define all generation parameters with types, constraints, and descriptions; provide automatic validation.
- Out-of-scope: Parameter selection logic, generation algorithms, or persistence (handled by generator and simulation controller).

## Architecture & Design
- Key classes: `GenerationParams` (Pydantic `BaseModel`) with field validation via `Field` constraints and custom validators.
- Data flow: Parameters are typically loaded from JSON/dict by the simulation controller, validated on instantiation, then passed to `WorldGenerator`.
- Validation: Uses Pydantic's declarative constraints (`ge`, `gt`, `le`) and custom `@field_validator` for complex rules.

## Parameter Categories

### Map Dimensions
- `map_width: float` - Map width in kilometers (must be positive)
- `map_height: float` - Map height in kilometers (must be positive)

### Urban Structure Parameters
- `num_major_centers: int` - Number of major urban centers (≥1)
- `minor_per_major: float` - Minor centers per major center (≥0)
- `center_separation: float` - Minimum separation between centers (positive)
- `urban_sprawl: float` - Urban sprawl radius (positive)

### Density Parameters
- `local_density: float` - Local road network density (positive)
- `rural_density: float` - Rural area road density (≥0)

### Connectivity Parameters
- `intra_connectivity: float` - Within-center connectivity (0 to 1)
- `inter_connectivity: int` - Between-center connectivity level (≥1)
- `arterial_ratio: float` - Ratio of arterial roads (0 to 1)
- `gridness: float` - Grid-like structure factor (0=organic, 1=grid)

### Highway and Road Parameters
- `ring_road_prob: float` - Probability of ring roads around centers (0 to 1)
- `highway_curviness: float` - Highway curviness (0=straight, 1=curved)

### Site Generation Parameters
- `rural_settlement_prob: float` - Probability of rural settlements (0 to 1)
- `urban_sites_per_km2: float` - Urban site density per km² (≥0)
- `rural_sites_per_km2: float` - Rural site density per km² (≥0)
- `urban_activity_rate_range: tuple[float, float]` - [min, max] activity rate for urban sites (packages/hour)
- `rural_activity_rate_range: tuple[float, float]` - [min, max] activity rate for rural sites (packages/hour)

### Parking Generation Parameters
- `urban_parkings_per_km2: float` - Urban parking density per km² (≥0)
- `rural_parkings_per_km2: float` - Rural parking density per km² (≥0)

These parameters control the number of parking facilities generated in urban and rural areas. The generator calculates urban and rural areas based on center radii, then multiplies by these densities to determine target parking counts. Valid parking nodes are randomly sampled from nodes with at least 2 edges and at least one non-highway connection. Capacity is determined by the highest road class connected to each selected node.

### Generation Seed
- `seed: int` - Random seed used for generation (ensures reproducibility)

## Custom Validation

### Activity Rate Range Validation
The `validate_activity_range` validator ensures:
- Exactly 2 values provided (min, max)
- Both values are non-negative
- Min ≤ max

This validator applies to both `urban_activity_rate_range` and `rural_activity_rate_range`.

## Public API / Usage

### Creating Parameters

```python
from world.generation.params import GenerationParams

# From dict (typical usage from JSON config)
params = GenerationParams.model_validate({
    "map_width": 25.0,
    "map_height": 15.0,
    "num_major_centers": 2,
    "minor_per_major": 1.0,
    "center_separation": 5000.0,
    "urban_sprawl": 3000.0,
    "local_density": 0.8,
    "rural_density": 0.2,
    "intra_connectivity": 0.7,
    "inter_connectivity": 2,
    "arterial_ratio": 0.3,
    "gridness": 0.5,
    "ring_road_prob": 0.7,
    "highway_curviness": 0.3,
    "rural_settlement_prob": 0.2,
    "urban_sites_per_km2": 5.0,
    "rural_sites_per_km2": 0.5,
    "urban_activity_rate_range": [10.0, 50.0],
    "rural_activity_rate_range": [1.0, 10.0],
    "urban_parkings_per_km2": 2.0,
    "rural_parkings_per_km2": 0.2,
    "seed": 42
})

# Direct instantiation
params = GenerationParams(
    map_width=25.0,
    map_height=15.0,
    # ... other fields
)
```

### Validation Examples

```python
# Invalid: negative width
GenerationParams(map_width=-10.0, ...)  # Raises ValidationError

# Invalid: activity rate min > max
GenerationParams(
    urban_activity_rate_range=[50.0, 10.0], ...
)  # Raises ValidationError

# Invalid: connectivity out of range
GenerationParams(intra_connectivity=1.5, ...)  # Raises ValidationError
```

## Implementation Notes
- All constraints are declarative using Pydantic's `Field` constraints, avoiding manual validation logic.
- Uses PEP 604 type unions (`tuple[float, float]`) for modern Python type hints.
- Custom validators use `@field_validator` with `@classmethod` decorator (Pydantic v2 pattern).
- Parking density parameters were added to match site generation pattern, enabling deterministic parking placement.

## Tests (If Applicable)
- Parameter validation is indirectly tested through generator tests that instantiate parameters and verify generation outcomes.
- Consider adding explicit unit tests for validation edge cases in `tests/world/test_generation_params.py`.

## Performance
- Validation overhead is negligible (occurs once at parameter instantiation).
- No runtime performance impact on generation.

## Security & Reliability
- Strict validation prevents invalid parameter combinations that could cause generation failures.
- Type safety ensures parameter misuse is caught at construction time.
- Clear error messages from Pydantic when validation fails.

## References
- Related modules: `docs/modules/world/generation/generator.md`, `docs/modules/world/sim/controller.md`
- ADRs: none recorded to date.
