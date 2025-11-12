---
title: "Simulation Action Parser"
summary: "Validates inbound WebSocket commands and translates them into canonical ActionRequest envelopes for the simulation stack."
source_paths:
  - "world/sim/actions/action_parser.py"
  - "tests/world/test_action_parser.py"
last_updated: "2025-11-08"
owner: "Mateusz Polis"
tags: ["module", "api"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["action-registry.md", "action-processor.md"]
---

# Simulation Action Parser

> **Purpose:** Enforces the `<domain>.<action>` protocol on WebSocket commands and produces typed `ActionRequest` envelopes that downstream components can rely on without re-validating their shape.

## Context & Motivation
- Problem solved
  - Incoming WebSocket payloads must be validated before touching the simulation.
  - Ensures legacy clients cannot bypass the canonical naming scheme.
- Requirements and constraints
  - Accept mixed payloads with optional `params` keys.
  - Reject malformed or non-dictionary parameter structures.
- Dependencies and assumptions
  - Built on Pydantic models (v2) for structural guarantees.
  - Consumed by `ActionQueue` and the Action Processor.
  - Domains such as `building.create` and `building.*` map directly onto handler registrations with no parser changes.

## Responsibilities & Boundaries
- In-scope
  - Regex validation of `<domain>.<action>` identifiers.
  - Default handling for omitted `params`.
  - Raising actionable errors for invalid payloads.
- Out-of-scope
  - Business-level validation of parameter content (delegated to handlers).
  - Registry/processor orchestration (handled in neighbouring modules).

## Architecture & Design
- Key functions, classes, or modules
  - `ActionRequest`: Pydantic data class storing the canonical envelope.
  - `ActionParser.parse`: Entry point for validating raw dictionaries.
- Data flow and interactions
  - WebSocket server calls `parse` before enqueuing messages.
  - Outputs feed directly into `ActionQueue`.
- State management or concurrency
  - Stateless; no internal caching.
- Resource handling
  - None beyond in-memory validation.

## Algorithms & Complexity
- Regex validation on the action string is O(1).
- Pydantic validation is O(n) with respect to payload size.

## Public API / Usage
- Short function signatures
  - `ActionParser.parse(raw: dict[str, Any]) -> ActionRequest`
- Example usage snippet
  ```python
  parser = ActionParser()
  request = parser.parse({"action": "simulation.start", "params": {"tick_rate": 30.0}})
  ```

## Implementation Notes
- Relies on a strict regex to guard against snake/dot casing errors.
- Provides descriptive error messages surfaced to clients via the error signal.

## Tests (If Applicable)
- `tests/world/test_action_parser.py` covers:
  - Happy path parsing with/without params.
  - Error handling for invalid formats and param types.

## Performance
- Negligible cost relative to network I/O.
- No allocations beyond the returned `ActionRequest`.

## Security & Reliability
- Prevents command injection by rejecting malformed identifiers.
- Ensures `params` is always a dictionary, avoiding type confusion.

## References
- `ActionQueue` documentation for downstream storage expectations.
- `Simulation Action Processor` for consumers of `ActionRequest`.
