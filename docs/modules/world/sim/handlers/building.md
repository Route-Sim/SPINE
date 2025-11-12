---
title: "Building Action Handler"
summary: "Processes building.create actions, validates parking payloads, and emits building.created signals back to the WebSocket layer."
source_paths:
  - "world/sim/handlers/building.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["agent.md", "map.md", "simulation.md", "state.md", "tick_rate.md"]
---

# Building Action Handler

> **Purpose:** Accepts canonical `building.create` actions from the frontend, provisions `Parking` buildings on the world graph, and publishes confirmation signals that mirror the canonical API contract.

## Context & Motivation
- Problem solved: allow the UI to provision additional parking capacity after map generation without rebuilding the world.
- Requirements and constraints:
  - Enforce unique `building_id` assignments across every node.
  - Validate node existence and integer capacity before mutating world state.
  - Emit a deterministic `building.created` signal to keep WebSocket consumers in sync.
- Dependencies and assumptions: relies on `Parking` from `core.buildings.parking`, the world graph stored in `HandlerContext`, and queue helpers from `world.sim.queues`.

## Responsibilities & Boundaries
- In-scope:
  - Parameter validation for `building.create` actions.
  - Publishing success responses with the current simulation tick.
- Out-of-scope:
  - Parking removal or modification (future extensions).
  - Truck routing decisions into or out of parking (handled by agents/routes).
  - Persistence of parking metadata beyond the active simulation session.

## Architecture & Design
- Key functions:
  - `BuildingActionHandler.handle_create(params, context)` — main entry point.
  - `_building_exists(graph, building_id)` — deduplicates building IDs across the graph.
- Data flow:
  1. Handler resolves the target `NodeID` inside the `World.graph`.
  2. Constructs a `Parking` instance with empty occupancy.
  3. Appends the parking to the node, then enqueues a `building.created` signal including `building` payload and `node_id`.
- State management: relies on `Parking`'s set-backed occupancy for future truck tracking; current actions always start with an empty set.
- Resource handling: limited to in-memory graph mutation; queue operations are bounded by configured timeouts.

## Algorithms & Complexity
- Building lookup scans node inventories (`O(|V|)` worst-case, typically far less).
- Signal emission is non-blocking with timeout handling delegated to the queue infrastructure.

## Public API / Usage
- Trigger creation:
  ```json
  {
    "action": "building.create",
    "params": {
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
- Only `parking` buildings are currently supported; other types will require additional handlers or branching logic.
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
