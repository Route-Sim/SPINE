---
title: "Simulation Action Registry"
summary: "Central mapping between canonical action identifiers and their execution handlers within the simulation loop."
source_paths:
  - "world/sim/actions/action_registry.py"
last_updated: "2025-11-08"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["action-parser.md", "action-processor.md"]
---

# Simulation Action Registry

> **Purpose:** Maintains the lookup table that binds `<domain>.<action>` identifiers to concrete handler callables, making it easy to add or remove capabilities without touching the controller.

## Context & Motivation
- Problem solved
  - Avoids scattering string comparisons across the codebase.
  - Provides a single source of truth for currently supported actions.
- Requirements and constraints
  - Must support canonical `ActionType` enum values.
  - Should allow custom or experimental registrations in tests.
- Dependencies and assumptions
  - Handlers follow the signature `(params: dict[str, Any], context: HandlerContext) -> None`.
  - The registry exists inside the new `world.sim.actions` subpackage.

## Responsibilities & Boundaries
- In-scope
  - Registering built-in handlers (simulation, tick-rate, agents, maps, state).
  - Providing helper methods to check and fetch handlers.
- Out-of-scope
  - Executing handlers (delegated to `ActionProcessor`).
  - Parameter validation (handled by handlers themselves).

## Architecture & Design
- Key functions, classes, or modules
  - `ActionRegistry`: Holds the mapping and exposes `register`, `get_handler`, `has_handler`.
  - `create_default_registry()`: Populates the default registry used by the controller.
- Data flow and interactions
  - The controller builds a registry and passes it into the processor.
  - Handlers live under `world.sim.handlers.*`.
- State management or concurrency
  - Not thread-safe by design; mutations occur during bootstrap only.
- Resource handling
  - Minimal; dictionary lookups only.

## Algorithms & Complexity
- Registration and lookup are O(1) dictionary operations.

## Public API / Usage
- Example:
  ```python
  registry = create_default_registry()
  if registry.has_handler(ActionType.START):
      handler = registry.get_handler(ActionType.START)
  ```
- New custom handlers can be registered via `registry.register`.

## Implementation Notes
- Accepts either `ActionType` or raw strings, providing flexibility for external tools.
- Keeps canonicalisation logic in one place (value extraction for enums).

## Tests (If Applicable)
- Covered indirectly through controller and processor integration tests.
- Unit tests can inject fake handlers using `register`.

## Performance
- Negligible overhead; underlying dict remains small (<20 entries).

## Security & Reliability
- Strips ENUM values to strings to avoid mismatches.
- Non-existent actions return `None`, allowing graceful error reporting.

## References
- `Simulation Action Processor` for execution flow.
- `Simulation Controller` for registry creation and consumption.
