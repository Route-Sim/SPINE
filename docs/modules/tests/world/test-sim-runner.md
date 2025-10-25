---
title: "Tests: Simulation Runner"
summary: "Test suite covering signal handling, graceful shutdown, thread lifecycle, and integration flow for the simulation runner."
source_paths:
  - "tests/world/test_sim_runner.py"
last_updated: "2025-10-25"
owner: "Mateusz Polis"
tags: ["test", "sim"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["test-websocket-server.md"]
---

# Tests: Simulation Runner

> **Purpose:** Validate `SimulationRunner` orchestration: signal handling (SIGINT/SIGTERM), controller/websocket lifecycle, and graceful shutdown semantics including thread joins and task cancellation.

## Context & Motivation
- Ensure the runner reliably coordinates the simulation controller and WebSocket server.
- Verify behavior under interrupts and repeated shutdown calls.
- Guarantee bounded shutdown via timeouts and task cancellation.

## Responsibilities & Boundaries
- **In-scope:** signal handler invocation, shutdown event, controller stop, task cancel, thread joins, integration startup/shutdown.
- **Out-of-scope:** controller internals, FastAPI specifics (covered elsewhere).

## Key Cases
- Registration of SIGINT/SIGTERM handlers.
- Shutdown event set and propagated.
- Controller stop and running state transitions.
- Signal broadcast task cancellation when active/already-done.
- Thread lifecycle hygiene and time-bounded joins.
- Integration: start, action dispatch, and clean shutdown.
- KeyboardInterrupt resilience in the main loop.

## Notes
- Minor style fixes applied to satisfy ruff (unused lambda arg, unused variable removal) without changing behavior.

## References
- `modules/world/sim/runner.md`
