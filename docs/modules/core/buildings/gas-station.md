---
title: "Gas Station Building"
summary: "Represents fuel service facilities on graph nodes with capacity limits, dynamic pricing based on a global fuel price and per-station cost factors, and revenue tracking from fuel sales."
source_paths:
  - "core/buildings/gas_station.py"
last_updated: "2025-12-09"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "building", "sim"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["base.md", "parking.md", "site.md", "occupancy.md"]
---

# Gas Station Building

> **Purpose:** Represents gas stations that provide fuel services to transport agents. Each station has a capacity for how many agents can fuel simultaneously, a cost factor that adjusts the global fuel price for this specific location, and tracks accumulated revenue from fuel sales.

## Context & Motivation
- Problem solved: model fuel service facilities attached to road nodes with dynamic pricing and revenue tracking.
- Requirements and constraints:
  - Respect declared capacity limits for simultaneous fueling operations.
  - Support dynamic pricing through a cost factor multiplier on the global fuel price.
  - Track revenue from fuel sales for economic simulation.
  - Provide deterministic serialization for map exports and WebSocket responses.
  - Interoperate with the base `Building` factory (`Building.from_dict`).
- Dependencies and assumptions:
  - Agent identifiers use the `AgentID` alias.
  - The global fuel price is managed by the `World` instance and updated daily.
  - The world generator creates gas stations based on density parameters.
  - Trucks handle payment by calling `add_revenue()` after fueling.

## Responsibilities & Boundaries
- In-scope:
  - Capacity validation at construction time.
  - Cost factor validation (must be positive).
  - Price calculation based on global fuel price and local cost factor.
  - Revenue tracking from fuel sales.
  - Occupancy tracking inherited from `OccupiableBuilding`.
- Out-of-scope:
  - Truck fueling behavior (handled by agent logic).
  - Global fuel price management (handled by `World`).
  - Route planning to gas stations (handled by navigator/routing).

## Architecture & Design
- Class: `GasStation(OccupiableBuilding)` extends the occupancy-capable building with:
  - `cost_factor: float` — multiplier on global fuel price (e.g., 0.8-1.2).
  - `balance_ducats: float` — accumulated revenue from fuel sales (default 0.0).
  - Method `get_fuel_price(global_price: float) -> float`.
  - Method `add_revenue(amount: float)` — adds fuel sale revenue.
- Inherits from `OccupiableBuilding`:
  - `capacity: int`
  - `current_agents: set[AgentID]`
  - Methods: `enter()`, `leave()`, `has_space()`, `assign_occupants()`.
- Data flow:
  - Generator attaches `GasStation` instances based on density parameters.
  - `building.create` actions can provision additional stations at runtime.
  - Trucks query `get_fuel_price()` with the world's current global price.
  - After fueling, trucks call `add_revenue()` to transfer payment.

```python
from core.buildings.gas_station import GasStation
from core.types import AgentID, BuildingID

station = GasStation(
    id=BuildingID("gas-station-42"),
    capacity=4,
    cost_factor=1.15,  # 15% above base price
    balance_ducats=0.0
)
station.enter(AgentID("truck-99"))

# With global price of 5.0 ducats/liter
price = station.get_fuel_price(5.0)  # Returns 5.75 ducats/liter

# After truck fuels 100 liters
station.add_revenue(100 * price)  # Adds 575.0 ducats
print(station.balance_ducats)  # 575.0

payload = station.to_dict()
# {'id': 'gas-station-42', 'type': 'gas_station', 'capacity': 4,
#  'current_agents': ['truck-99'], 'cost_factor': 1.15, 'balance_ducats': 575.0}
```

## Algorithms & Complexity
- Occupancy operations (`enter`, `leave`, `has_space`) are `O(1)` on average.
- Price calculation is `O(1)` — simple multiplication.
- Serialization sorts occupants (`O(n log n)`) for deterministic ordering.

## Public API / Usage
- Instantiate via constructor or `GasStation.from_dict`.
- Use `enter`/`leave` for occupancy updates (inherited from `OccupiableBuilding`).
- Use `get_fuel_price(global_price)` to calculate the local fuel price.
- Use `add_revenue(amount)` to record fuel sale payments.
- When serialized, payloads include `"type": "gas_station"` so `Building.from_dict` can reconstruct instances.

## Implementation Notes
- Validation ensures capacity is positive and cost_factor is greater than zero.
- The cost_factor allows for market-based pricing variation across the network.
- Integration with `World.global_fuel_price` enables daily price fluctuations.
- The `balance_ducats` field tracks accumulated revenue and marks the building dirty when updated.
- Revenue can only be positive (validation in `add_revenue`).

## Tests
- Round-trip serialization through `GasStation.to_dict()` / `GasStation.from_dict()`.
- Capacity and cost_factor validation.
- Price calculation with various global prices and cost factors.
- Revenue tracking via `add_revenue()` method.
- Balance persistence through serialization/deserialization.
- Integration via world generation and WebSocket action handler tests.
- Truck fueling process tests (in `tests/agents/test_truck.py`).

## Performance
- Gas station operations are constant-time.
- No significant bottlenecks expected.

## References
- [Occupiable Building Base](occupancy.md) — provides capacity and occupancy tracking.
- [Building Base Class](base.md) — core serializer and factory.
- [World](../../world/world.md) — manages global fuel price.
- [World Generator](../../world/generation/generator.md) — automatic gas station placement.
- [Building Action Handler](../../world/sim/handlers/building.md) — runtime provisioning via `building.create`.
