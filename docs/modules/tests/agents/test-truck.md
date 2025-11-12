---
title: "Test: Truck Parking"
summary: "Unit coverage for the truck parking helpers, confirming capacity checks, node validation, and serialization updates for the new `current_building_id` field."
source_paths:
  - "tests/agents/test_truck.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["test", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["../world/test-agent-action-handler.md"]
---

# Test: Truck Parking

> **Purpose:** Provide regression coverage for the explicit parking lifecycle helpers on the `Truck` agent, ensuring parking assignments remain consistent with building capacity and surface through serialization signals.

## Context & Motivation
- Problem solved
  - Validates that trucks can only park in buildings located on their current node.
  - Ensures parking capacity constraints raise appropriate errors.
  - Confirms serialized diffs emit `current_building_id` transitions for downstream consumers.
- Requirements and constraints
  - Tests operate on lightweight in-memory `Graph`/`World` instances.
  - Reuses concrete `Parking` implementations to exercise real validation logic.
- Dependencies and assumptions
  - Relies on `core.buildings.parking.Parking` for occupancy management.
  - Uses `world.world.World` with default navigator for contextual completeness.

## Responsibilities & Boundaries
- In-scope
  - Parking registration and release flows invoked via explicit helpers.
  - Validation of error handling for mismatched nodes and full capacity.
  - Differential serialization assertions for `current_building_id`.
- Out-of-scope
  - Broader routing behaviour or movement along edges.
  - Integration with future parking-related actions (not yet implemented).

## Architecture & Design
- Key functions, classes, or modules
  - `Truck.park_in_building` and `Truck.leave_parking` methods under test.
  - `Parking` data model for capacity enforcement.
- Data flow and interactions
  - Tests construct a `World` with a single node containing a `Parking` building.
  - Trucks mutate `Parking.current_agents` via the helpers, then serialize state.
- State management or concurrency
  - Tests run sequentially using isolated world instances; no concurrency aspects.

## Algorithms & Complexity
- Core algorithmic approach
  - Direct method invocation with assertions on side effects (`current_agents` set, serialized diff payloads).
- Big-O complexity
  - Helper operations are constant time; test runtime dominated by fixture construction (also constant).
- Edge cases and stability
  - Covers error paths for node mismatch and exhausted capacity.

## Public API / Usage
- Short function/class signatures
  - `truck.park_in_building(world, building_id)` assigns parking.
  - `truck.leave_parking(world)` releases the reserved slot.
- Example usage snippet
  ```python
  truck.park_in_building(world, parking_id)
  truck.serialize_diff()
  truck.leave_parking(world)
  ```

## Implementation Notes
- Key design trade-offs
  - Chosen to reuse actual `Graph`/`World` classes instead of fakes to stay close to runtime behaviour.
  - Maintains explicit helper usage, mirroring the intended external action workflow.
- 3rd-party libraries
  - `pytest` for assertions and exception handling.
- Testing hooks or debug modes
  - No bespoke hooks; direct calls into domain objects.

## Tests (If Applicable)
- Test scope and strategy
  - Focused unit tests verifying parking assignment lifecycle.
- Critical test cases
  - Successful parking registers the truck and emits serialized diffs.
  - Leaving parking releases occupancy and surfaces state changes.
  - Mismatched node raises `ValueError`.
  - Capacity overflow raises `ValueError`.

## Performance
- Benchmarks or baselines
  - Tests execute in microseconds; negligible overhead.
- Known bottlenecks
  - None observed.

## Security & Reliability
- Validation, error handling, fault tolerance
  - Exercises guardrails around node validation and capacity checks.
- Logging and observability
  - Not addressed within tests; relies on assertions.

## References
- Related modules
  - `agents/transports/truck.py`
  - `core/buildings/parking.py`
- ADRs
  - None.
- Papers, specifications, issues, PRs
  - None.
