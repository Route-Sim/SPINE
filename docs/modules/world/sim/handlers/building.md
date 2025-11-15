---
title: "Building Action Handler"
summary: "Processes building.create actions using a factory pattern, validates building payloads, and emits building.created signals back to the WebSocket layer."
source_paths:
  - "world/sim/handlers/building.py"
last_updated: "2025-01-27"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["agent.md", "map.md", "simulation.md", "state.md", "tick_rate.md"]
---

# Building Action Handler

> **Purpose:** Accepts canonical `building.create` actions from the frontend, provisions buildings on the world graph using a factory pattern, and publishes confirmation signals that mirror the canonical API contract. Currently supports parking buildings with extensibility for future building types.

## Context & Motivation
- Problem solved: allow the UI to provision additional building capacity (e.g., parking) after map generation without rebuilding the world.
- Requirements and constraints:
  - Enforce unique `building_id` assignments across every node.
  - Require explicit `building_type` specification for extensibility.
  - Validate node existence and type-specific parameters before mutating world state.
  - Emit a deterministic `building.created` signal to keep WebSocket consumers in sync.
- Dependencies and assumptions: relies on building classes from `core.buildings`, the world graph stored in `HandlerContext`, and queue helpers from `world.sim.queues`.

## Responsibilities & Boundaries
- In-scope:
  - Parameter validation for `building.create` actions, including required `building_type`.
  - Factory-based building instantiation supporting multiple building types.
  - Publishing success responses with the current simulation tick.
- Out-of-scope:
  - Building removal or modification (future extensions).
  - Truck routing decisions into or out of buildings (handled by agents/routes).
  - Persistence of building metadata beyond the active simulation session.

## Architecture & Design
- Key functions:
  - `BuildingActionHandler.handle_create(params, context)` — main entry point that validates and delegates to factory.
  - `_create_building(building_type, building_id, params)` — factory function that instantiates building instances based on type.
  - `_building_exists(graph, building_id)` — deduplicates building IDs across the graph.
- Data flow:
  1. Handler validates `building_type` is present and is a string.
  2. Handler validates common parameters (`building_id`, `node_id`) and node existence.
  3. Factory function `_create_building` validates type-specific parameters and instantiates the appropriate building class.
  4. Handler appends the building to the node, then enqueues a `building.created` signal including `building` payload and `node_id`.
- Factory pattern: The `_create_building` function maps building types to their constructors, currently supporting `"parking"` → `Parking`. New building types can be added by extending this function.
- State management: relies on building-specific state (e.g., `Parking`'s set-backed occupancy for future truck tracking); current actions always start with empty initial state.
- Resource handling: limited to in-memory graph mutation; queue operations are bounded by configured timeouts.

## Algorithms & Complexity
- Building lookup scans node inventories (`O(|V|)` worst-case, typically far less).
- Signal emission is non-blocking with timeout handling delegated to the queue infrastructure.

## Public API / Usage
- Trigger creation (parking building):
  ```json
  {
    "action": "building.create",
    "params": {
      "building_type": "parking",
      "building_id": "parking-node42",
      "node_id": 42,
      "capacity": 40
    }
  }
  ```
- Successful response (`building.created`):
  ```json
  {
    "signal": "building.created",
    "data": {
      "node_id": 42,
      "building": {
        "id": "parking-node42",
        "type": "parking",
        "capacity": 40,
        "current_agents": []
      },
      "tick": 512
    }
  }
  ```

## Implementation Notes
- `building_type` is a required parameter and must be explicitly specified. Only `"parking"` is currently supported; unsupported types raise `ValueError`.
- The factory pattern (`_create_building`) provides a clean extension point for new building types. To add support for a new type:
  1. Implement the building class in `core.buildings`
  2. Add a branch in `_create_building` to handle the new type
  3. Validate type-specific parameters in the factory function
- Validation order: `building_type` → common parameters → node existence → building uniqueness → type-specific parameters → building creation.
- `create_building_created_signal` appends the current tick so clients can reconcile state transitions with simulation time.
- Validation errors raise `ValueError`, which the `ActionProcessor` translates into `error` signals.

## Tests
- Exercised indirectly through integration flows that assert queue helper outputs (see `docs/api-reference.md` Postman scripts).
- Future work: unit coverage for duplicate ID rejection and future occupancy management.

## References
- [Building Base Class](../../core/buildings/base.md) — core serializer and factory.
- [Parking Building](../../core/buildings/parking.md) — capacity-constrained staging model.
- [Simulation Queue Infrastructure](../queues.md) — helper factories and enum definitions.
- [Action Registry](../actions/action-registry.md) — wiring of canonical identifiers to handlers.
