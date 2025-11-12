---
title: "World Test: Agent Action Handler"
summary: "Explains the regression tests validating the agent action handler, covering describe and list workflows plus error propagation paths."
source_paths:
  - "tests/world/test_agent_action_handler.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["test", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["test-graph-graphml.md", "test-sim-runner.md", "test-websocket-server.md"]
---

# World Test: Agent Action Handler

> **Purpose:** Documents the pytest coverage for `AgentActionHandler`, ensuring agent lifecycle, describe, and list actions emit the correct signals and enforce state preconditions/filter semantics.

## Context & Motivation
- Problem solved
  - Prevent regressions in the `agent.describe` and `agent.list` workflows.
  - Ensure existing lifecycle actions continue to surface errors via the signal queue.
- Requirements and constraints
  - Tests construct a lightweight `World` with a dummy graph to avoid heavy fixtures.
  - Simulation state must be toggled explicitly to cover both running and non-running scenarios.
- Dependencies and assumptions
  - Relies on `HandlerContext` and queue helpers defined under `world.sim`.
  - Uses `AgentBase` as a lightweight agent implementation for serialization checks.

## Responsibilities & Boundaries
- In-scope
  - Happy-path describe action confirming `agent.described` payload structure.
  - `agent.list` aggregation behaviour, including filters and empty results.
  - Validation of required parameter types (e.g., non-string filters).
  - Error emission when the target agent is absent.
- Out-of-scope
  - Full integration tests of the WebSocket boundary (covered elsewhere).
  - Route or graph validation (handled by dedicated routing tests).

## Architecture & Design
- Key fixtures
  - `_DummyGraph`: minimal stub exposing an empty `nodes` mapping for world initialisation.
  - `_build_context`: helper constructing `HandlerContext` with configurable running state.
- Test flow
  - Tests enqueue describe and list actions and immediately inspect the `SignalQueue` for responses or error signals.
  - Assertions verify both signal type and payload semantics (IDs, agent counts, tick propagation, error codes).
- State and concurrency
  - Each test uses isolated `SimulationState` and `SignalQueue` instances to avoid cross-test interference.
- Resource handling
  - No disk or network dependencies; tests execute entirely in memory.

## Algorithms & Complexity
- All operations are O(1) dictionary lookups or queue interactions; runtime dominated by pytest overhead.

## Public API / Usage
- Execute with `poetry run pytest tests/world/test_agent_action_handler.py`.

## Implementation Notes
- The tests access `AgentBase.serialize_full()` to confirm parity with handler signals.
- Assertions check for the canonical `GENERIC_ERROR` code to keep UX expectations stable.

## Performance
- Test module completes in milliseconds; suitable for inclusion in pre-commit hooks.

## Security & Reliability
- Verifies that describe errors still produce `error` signals, preventing silent failures on the frontend.

## References
- `docs/modules/world/sim/handlers/agent.md` for handler design.
- `docs/modules/world/sim/queues.md` for helper usage.
- `docs/api-reference.md` for the published action/signal contract.
