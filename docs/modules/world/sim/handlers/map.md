---
title: "Map Action Handler"
summary: "Coordinates map import/export/create actions, validates procedural generation parameters, and emits canonical signals enriched with structural metadata."
source_paths:
  - "world/sim/handlers/map.py"
last_updated: "2025-11-08"
owner: "Mateusz Polis"
tags: ["module", "api", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["../controller.md", "../queues.md", "../runner.md"]
---

# Map Action Handler

> **Purpose:** Provides the simulation-facing implementation of map lifecycle commands. It validates procedural generation parameters, mediates GraphML import/export, coordinates world state swaps, and now emits enriched `map.created` signals containing a complete graph snapshot with buildings.

## Context & Motivation
- Supports frontend-driven orchestration of map generation, export, and import.
- Centralizes validation for the high-dimensional parameter space used by the procedural generator.
- Ensures simulation safety by disallowing map mutations while the loop is running.
- Emits user-facing signals with sufficient metadata for UI updates immediately after generation completes.

## Responsibilities & Boundaries
- **In-scope**
  - Validate `map.create`, `map.export`, and `map.import` parameters.
  - Invoke the procedural `MapGenerator` and replace the active `world.graph`.
  - Emit canonical signals (`map.created`, `map.exported`, `map.imported`) and structured error messages.
  - Serialize a complete graph snapshot for the freshly generated graph including all nodes, edges, and buildings.
- **Out-of-scope**
  - Low-level map generation algorithms (`world/generation`).
  - Graph persistence mechanics (`world/io/map_manager.py`).
  - WebSocket dispatch or queue plumbing (handled by controller/queues modules).

## Architecture & Design
- **Validation Layer:** Sequential checks ensure required parameters exist and conform to expected ranges/types before generation.
- **Generation Pipeline:** Builds a `GenerationParams` dataclass, runs `MapGenerator.generate()`, and installs the resulting `Graph` into `context.world`.
- **Graph Snapshot:** Uses `Graph.to_dict()` to serialize the in-memory `Graph` into `{nodes, edges}` lists with all node attributes including buildings, ready for JSON encoding.
- **Signal Emission:** Uses queue helpers (`create_map_created_signal`, etc.) to publish success events; `_emit_error` funnels problems into the standard `error` signal stream.

## Algorithms & Complexity
- Parameter validation executes in O(n) with n equal to the number of scalar inputs.
- Graph serialization is O(V + E) to traverse all nodes and edges once.
- No additional asymptotic cost beyond the generator itself.

## Public API / Usage
- Triggered via WebSocket action envelopes `{"action": "map.create", "params": {...}}`.
- Upon success, emits `map.created` with:
  - Generation metrics (dimensions, densities, connectivity parameters, counts).
  - `graph.nodes`: array of `{id, x, y, buildings}` objects where `buildings` is an array of serialized building objects.
  - `graph.edges`: array of `{id, from_node, to_node, length_m, mode, road_class, lanes, max_speed_kph, weight_limit_kg}` objects.
- Errors surface as `error` signals with descriptive messages when validation fails or I/O exceptions occur.

## Implementation Notes
- Uses `Graph.to_dict()` to serialize the complete graph structure including all buildings in nodes. The signal provides full graph fidelity without requiring a separate `state.full_map_data` request.
- The handler logs success/error messages with structured dictionaries for observability, leveraging the same payload sent to the frontend.
- Map mutations are guarded by `context.state.running` to maintain simulation consistency.

## Tests
- Covered indirectly through integration tests in `tests/world/test-sim-runner.py` and WebSocket workflow suites that assert signal sequencing.
- Scenario-driven tests should verify that `map.created` includes `graph` payloads and respects validation errors.

## Performance
- Serialization adds a linear pass proportional to graph size; negligible relative to procedural generation.
- No additional threading or locking requirements beyond existing queue interactions.

## Security & Reliability
- Prevents map operations while simulation runs, eliminating race conditions.
- Emits explicit error signals for validation and unexpected exceptions, keeping the frontend informed.
- Restricts export/import to sanitized filenames through downstream world I/O services.

## References
- `world/sim/controller.py` – delegates map actions to this handler.
- `world/sim/queues.py` – signal factory helpers used for outbound messages.
- `world/generation/generator.py` – procedural generation implementation.
