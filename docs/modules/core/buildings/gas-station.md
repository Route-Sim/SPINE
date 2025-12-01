---
title: "Gas Station Building"
summary: "Represents fuel service facilities on graph nodes with capacity limits and dynamic pricing based on a global fuel price and per-station cost factors."
source_paths:
  - "core/buildings/gas_station.py"
last_updated: "2025-12-01"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "building", "sim"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["base.md", "parking.md", "site.md", "occupancy.md"]
---

# Gas Station Building

> **Purpose:** Represents gas stations that provide fuel services to transport agents. Each station has a capacity for how many agents can fuel simultaneously and a cost factor that adjusts the global fuel price for this specific location.

## Context & Motivation
- Problem solved: model fuel service facilities attached to road nodes with dynamic pricing.
- Requirements and constraints:
  - Respect declared capacity limits for simultaneous fueling operations.
  - Support dynamic pricing through a cost factor multiplier on the global fuel price.
  - Provide deterministic serialization for map exports and WebSocket responses.
  - Interoperate with the base `Building` factory (`Building.from_dict`).
- Dependencies and assumptions:
  - Agent identifiers use the `AgentID` alias.
  - The global fuel price is managed by the `World` instance and updated daily.
  - The world generator creates gas stations based on density parameters.

## Responsibilities & Boundaries
- In-scope:
  - Capacity validation at construction time.
  - Cost factor validation (must be positive).
  - Price calculation based on global fuel price and local cost factor.
  - Occupancy tracking inherited from `OccupiableBuilding`.
- Out-of-scope:
  - Truck fueling behavior (handled by agent logic).
  - Global fuel price management (handled by `World`).
  - Route planning to gas stations (handled by navigator/routing).

## Architecture & Design
- Class: `GasStation(OccupiableBuilding)` extends the occupancy-capable building with:
  - `cost_factor: float` — multiplier on global fuel price (e.g., 0.8-1.2).
  - Method `get_fuel_price(global_price: float) -> float`.
- Inherits from `OccupiableBuilding`:
  - `capacity: int`
  - `current_agents: set[AgentID]`
  - Methods: `enter()`, `leave()`, `has_space()`, `assign_occupants()`.
- Data flow:
  - Generator attaches `GasStation` instances based on density parameters.
  - `building.create` actions can provision additional stations at runtime.
  - Trucks query `get_fuel_price()` with the world's current global price.

```python
from core.buildings.gas_station import GasStation
from core.types import AgentID, BuildingID

station = GasStation(
    id=BuildingID("gas-station-42"),
    capacity=4,
    cost_factor=1.15  # 15% above base price
)
station.enter(AgentID("truck-99"))

# With global price of 5.0 ducats/liter
price = station.get_fuel_price(5.0)  # Returns 5.75 ducats/liter

payload = station.to_dict()
# {'id': 'gas-station-42', 'type': 'gas_station', 'capacity': 4,
#  'current_agents': ['truck-99'], 'cost_factor': 1.15}
```

## Algorithms & Complexity
- Occupancy operations (`enter`, `leave`, `has_space`) are `O(1)` on average.
- Price calculation is `O(1)` — simple multiplication.
- Serialization sorts occupants (`O(n log n)`) for deterministic ordering.

## Public API / Usage
- Instantiate via constructor or `GasStation.from_dict`.
- Use `enter`/`leave` for occupancy updates (inherited from `OccupiableBuilding`).
- Use `get_fuel_price(global_price)` to calculate the local fuel price.
- When serialized, payloads include `"type": "gas_station"` so `Building.from_dict` can reconstruct instances.

## Implementation Notes
- Validation ensures capacity is positive and cost_factor is greater than zero.
- The cost_factor allows for market-based pricing variation across the network.
- Integration with `World.global_fuel_price` enables daily price fluctuations.

## Tests
- Round-trip serialization through `GasStation.to_dict()` / `GasStation.from_dict()`.
- Capacity and cost_factor validation.
- Price calculation with various global prices and cost factors.
- Integration via world generation and WebSocket action handler tests.

## Performance
- Gas station operations are constant-time.
- No significant bottlenecks expected.

## References
- [Occupiable Building Base](occupancy.md) — provides capacity and occupancy tracking.
- [Building Base Class](base.md) — core serializer and factory.
- [World](../../world/world.md) — manages global fuel price.
- [World Generator](../../world/generation/generator.md) — automatic gas station placement.
- [Building Action Handler](../../world/sim/handlers/building.md) — runtime provisioning via `building.create`.
