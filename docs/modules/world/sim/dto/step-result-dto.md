---
title: "Step Result DTO"
summary: "Pydantic DTO for encapsulating simulation step results, providing type-safe access to world events, agent diffs, and building updates."
source_paths:
  - "world/sim/dto/step_result_dto.py"
last_updated: "2025-12-09"
owner: "Mateusz Polis"
tags: ["module", "dto", "simulation", "api"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["../controller.md", "../queues.md"]
---

# Step Result DTO

> **Purpose:** Provides strongly-typed encapsulation of simulation step results, replacing raw dictionaries with a validated Pydantic model for type safety and convenient accessor methods.

## Context & Motivation

- Problem solved: Raw `dict[str, Any]` return types from `World.step()` lacked type safety and made it difficult to understand the structure of step results.
- Requirements and constraints:
  - Must support all event types, agent diffs, and building updates
  - Must provide convenient accessor methods for filtering and checking content
- Dependencies and assumptions: Pydantic v2 for validation.

## Responsibilities & Boundaries

**In-scope:**
- Type-safe representation of simulation step results
- Accessor methods for convenient data retrieval
- Filtering None values from agent diffs

**Out-of-scope:**
- Event type validation (events can have arbitrary structure)
- Agent/building-specific validation (handled by respective classes)

## Architecture & Design

**StepResultDTO**: Container for step results with the following fields:
- `events`: List of world events from the tick
- `agent_diffs`: List of agent state changes (may contain None)
- `building_updates`: List of building state changes

### Data Flow

```
World.step() → StepResultDTO → SimulationController._process_step_result()
                                    ↓
                          Signal emission for events, agents, buildings
```

## Public API / Usage

```python
from world.sim.dto.step_result_dto import StepResultDTO

# Create from World.step()
step_result = world.step()  # Returns StepResultDTO

# Check for content and iterate
if step_result.has_events():
    for event in step_result.get_events():
        process_event(event)

if step_result.has_agent_updates():
    for diff in step_result.get_agent_diffs():  # None entries filtered
        emit_agent_update(diff)

if step_result.has_building_updates():
    for update in step_result.get_building_updates():
        emit_building_update(update)
```

## Implementation Notes

- `get_agent_diffs()` filters out None entries to simplify iteration
- All accessor methods are O(n) where n is the number of items

## References

- [World Module](../../world.md) - Source of step results
- [Controller Module](../controller.md) - Consumer of step results
