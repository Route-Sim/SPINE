---
title: "Simulation Action Processor"
summary: "Executes validated action envelopes against the simulation state by resolving handlers from the registry and emitting signals."
source_paths:
  - "world/sim/actions/action_processor.py"
  - "tests/world/test_sim_controller.py"
  - "tests/world/test_sim_runner.py"
last_updated: "2025-11-08"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["action-parser.md", "action-registry.md"]
---

# Simulation Action Processor

> **Purpose:** Bridges validated `ActionRequest` envelopes to concrete handler execution, managing logging, error propagation, and signal emission within the simulation runtime.

## Context & Motivation
- Problem solved
  - Centralises execution flow for all incoming commands.
  - Ensures consistent error handling and signal emission.
- Requirements and constraints
  - Must cooperate with the registry for handler resolution.
  - Needs access to simulation state, world instance, and signal queues.
- Dependencies and assumptions
  - Uses `HandlerContext` to share mutable state with handlers.
  - Relies on `SimulationState` for current tick information.

## Responsibilities & Boundaries
- In-scope
  - Resolving handlers and executing them with the appropriate context.
  - Emitting error signals when handlers fail.
  - Logging at debug/warning/error levels for observability.
- Out-of-scope
  - Long-running threading concerns (handled by `SimulationController`).
  - Handler implementation details.

## Architecture & Design
- Key functions, classes, or modules
  - `ActionProcessor.process`: Main entry for executing envelopes.
  - `_emit_error`: Internal helper to push error signals safely.
- Data flow and interactions
  - Receives envelopes from `ActionQueue` via the controller.
  - Obtains handlers from `ActionRegistry`.
  - Emits signals through `SignalQueue`.
- State management or concurrency
  - Stateless aside from references injected at construction.
  - Thread safety derived from controller scheduling.
- Resource handling
  - No external resources; interacts with in-memory simulation objects.

## Algorithms & Complexity
- Handler lookup is O(1); performance dominated by handler logic.
- Error emission uses bounded queue operations with timeout protection.

## Public API / Usage
- Constructor signature emphasises explicit dependencies.
  ```python
  processor = ActionProcessor(registry, state, world, signal_queue, logger)
  processor.process(action_request)
  ```

## Implementation Notes
- Distinguishes between expected validation errors and unexpected exceptions.
- Wraps unexpected exceptions to surface consistent messaging upstream.

## Tests (If Applicable)
- `tests/world/test_sim_controller.py` validates processing flows.
- `tests/world/test_sim_runner.py` ensures end-to-end integration with the runner.

## Performance
- Lightweight wrapper; handler execution time dominates cost.
- Error signalling attempts a bounded put with a 1-second timeout.

## Security & Reliability
- Prevents unhandled exceptions from crashing the controller thread.
- Emits structured error signals to inform clients about failures.

## References
- `Simulation Action Registry` for handler mappings.
- `Simulation Controller` for orchestration and lifecycle management.
- `Simulation Queue Infrastructure` for the surrounding messaging layer.
