---
title: "Agent Action Handler"
summary: "Details the handler orchestrating agent lifecycle commands and the new describe workflow that publishes complete agent snapshots."
source_paths:
  - "world/sim/handlers/agent.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["map.md"]
---

# Agent Action Handler

> **Purpose:** Executes agent-related actions (`agent.create`, `agent.delete`, `agent.update`, `agent.describe`) by combining simulation state, world mutations, and signal emission into a cohesive orchestration layer reachable from the WebSocket controller.

## Context & Motivation
- Problem solved
  - Centralises all agent lifecycle commands behind a single handler to ensure consistent validation, logging, and signal emission.
  - Adds synchronous inspection (`agent.describe`) so the UI can request a full agent snapshot without waiting for differential updates.
- Requirements and constraints
  - Must reject mutating commands when required parameters are missing or invalid.
  - `agent.describe` is only permitted once the simulation has been started to guarantee the world is fully instantiated.
- Dependencies and assumptions
  - Relies on `HandlerContext` for access to `SimulationState`, `World`, `SignalQueue`, and a logger.
  - Uses helper factories from `world.sim.queues` to emit canonical signals.

## Responsibilities & Boundaries
- In-scope
  - Creating, deleting, updating, and describing agents.
  - Listing agents with optional kind-based filtering via `agent.list`.
  - Emitting `agent.created`, `agent.updated`, and `agent.described` signals with authoritative payloads.
  - Emitting `agent.listed` snapshots that batch agent states for UI consumption.
  - Surfacing validation failures through `error` signals with contextual metadata.
- Out-of-scope
  - Long-running simulation logic (delegated to `World` and individual agent implementations).
  - WebSocket routing or registry lookup (handled by the controller and `ActionRegistry`).

## Architecture & Design
- Key functions, classes, or modules
  - `AgentActionHandler.handle_create`: Instantiates agents, storing them in the world and broadcasting `agent.created`.
  - `AgentActionHandler.handle_delete` and `.handle_update`: Perform integrity-checked mutations against the world.
  - `AgentActionHandler.handle_describe`: Retrieves a full agent snapshot and emits a dedicated `agent.described` signal including the current tick.
  - `AgentActionHandler.handle_list`: Aggregates serialized agent states (optionally filtered by `agent_kind`) and emits `agent.listed`.
- Data flow and interactions
  - Handlers read parameters from the canonical action envelope, interact with the `World`, and write signals into `SignalQueue`.
  - Errors are translated into `error` signals before exceptions bubble upstream, allowing the UI to react immediately.
- State management or concurrency
  - Thread-safety is derived from the queue and state abstractions; handlers keep operations idempotent per action invocation.
- Resource handling
  - No external resources beyond in-memory world and queue structures.

## Algorithms & Complexity
- Lookup operations use dictionary access on `world.agents` (O(1)).
- Agent serialization delegates to agent-specific implementations (`serialize_full`, `serialize_diff`).

## Public API / Usage
- `handler.handle_describe({"agent_id": "truck-1"}, context)` emits:
  ```json
  {
    "signal": "agent.described",
    "data": {
      "id": "truck-1",
      "kind": "truck",
      "tick": 42,
      "...": "additional agent fields"
    }
  }
  ```
- Errors propagate as `ValueError` for validation failures, while unexpected exceptions are wrapped and logged.

## Implementation Notes
- `agent.describe` can be invoked regardless of simulation run state, allowing inspectors to fetch data while paused or before the loop starts.
- `agent.list` reuses `serialize_full()` results, adding a stable `agent_id` field so clients can key lists without relying on tags.
- The handler reuses `AgentBase.serialize_full()` to guarantee parity with state snapshots and `state.full_agent_data`.
- Logging differentiates between validation warnings and unexpected errors for easier observability.

## Tests (If Applicable)
- See `tests/world/test_agent_action_handler.py` for scenarios covering success, simulation-not-running, and missing-agent errors.

## Performance
- Negligible overhead: operations are dominated by agent serialization, typically small dictionaries.

## Security & Reliability
- Emitted signals include the current simulation tick, supporting temporal correlation on the frontend.
- Error signals carry a `GENERIC_ERROR` code plus descriptive message, ensuring consistent UX for failure cases.

## References
- `world.sim.queues` for action and signal helper factories.
- `world.sim.actions.action_registry` for registration details.
- `docs/api-reference.md` for the canonical WebSocket contract.
