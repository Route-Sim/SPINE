title: "World Generator"
summary: "Explains the stochastic generator that assembles roads, sites, and routing weights for SPINE simulation scenarios."
source_paths:
  - "world/generation/generator.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["module", "sim"]
links:
  parent: "../../../../SUMMARY.md"
  siblings:
    - "../../generation.md"
---

# Generator

> **Purpose:** This component synthesises a playable logistics world by sampling settlements, building the transport graph, and instantiating agent-facing structures such as `Site` buildings and `Parking` facilities. It couples geographic heuristics with stochastic draws to deliver varied yet reproducible environments.

## Context & Motivation
- Problem solved: emulate realistic urban–rural logistics networks without relying on external GIS data.
- Requirements and constraints: respect map size parameters, maintain connectivity, and keep generation time suitable for iterative experimentation.
- Dependencies and assumptions: depends on `world.graph`, `core.buildings.site`, and random number generation seeded by higher-level orchestration.

## Responsibilities & Boundaries
- In-scope: node selection, edge weighting, construction of buildings, and assignment of inter-site destination weights.
- Out-of-scope: runtime package spawning logic (handled by `Site`), transport agent behaviour, and persistence of generated maps.

## Architecture & Design
- Key functions, classes, or modules: `WorldGenerator` orchestrates map creation; helper methods like `_select_site_nodes`, `_create_site`, `_place_parking`, and `_assign_destination_weights` subdivide tasks.
- Data flow and interactions: the generator enriches a `Graph` instance, embeds `Site` buildings on nodes, adds `Parking` buildings based on road classes, then records metadata in `self.sites`/`self.parkings` for later simulation stages.
- State management or concurrency: uses internal counters (`site_count`, `parking_count`) to guarantee stable identifiers; no concurrent execution expected.
- Resource handling: operates purely in-memory; no external files or network operations.

## Algorithms & Complexity
- Node selection scans all graph nodes (`O(|V|)`) while filtering by road class and urban coverage.
- Destination weight assignment iterates over the Cartesian product of sites (`O(|S|^2)`), applying biased random weights to emphasise urban importance.
- Parking placement inspects the adjacency set of each node to compute the highest road class encountered and derive a capacity in `O(degree(node))`.
- Edge cases include isolated nodes (skipped), nodes with single incoming/outgoing edges (parking omitted), and scenarios with fewer than two sites (weights are not generated).

## Public API / Usage
- Typical usage: invoked through higher-level scenario builders that call `WorldGenerator.build_world()`.
- Helper signatures:
  - `_select_site_nodes(graph: Graph, is_urban: bool) -> list[NodeID]`
  - `_create_site(node_id: NodeID, is_urban: bool) -> Site`
  - `_place_parking(graph: Graph) -> None`
  - `_determine_parking_capacity(road_classes: set[RoadClass], graph: Graph, node_id: NodeID) -> int | None`
  - `_assign_destination_weights(graph: Graph) -> None`

## Implementation Notes
- Site identifiers now embed the origin node (e.g., `node42_site_3`), preserving a traceable link between buildings and their host nodes.
- Parking identifiers follow `parking_<node>_<counter>` and capacities scale with the strongest connected road class (`A` → 80 slots, `S` → 60, …, `D` → 6).
- Parking placement skips dead-ends (degree < 2) to avoid staging in cul-de-sacs.
- Parking metadata becomes available for runtime handlers to honour parking occupancy semantics once truck parking workflows are implemented.
- Site names mirror the hosting node index to aid debugging when inspecting generated worlds.
- Random draws balance urban saturation with occasional high-activity rural hubs to encourage diverse routing.
- Speed limits interpret lane counts per directed edge; dual carriageways are detected when a unidirectional edge advertises at least two lanes.

## Tests (If Applicable)
- Generation behaviours are indirectly validated by simulation tests in `tests/world`, which assert graph connectivity, queue processing, and deterministic building placement.

## Performance
- Designed for medium-sized maps (<10k nodes); quadratic destination weighting can be costly for extremely dense site populations.

## Security & Reliability
- Defensive checks avoid isolated nodes and self-referential weights; randomness is contained, with deterministic reproduction available via seeding.

## References
- Related modules: `docs/modules/world/generation.md`, `docs/modules/world/sim/controller.md`, `docs/modules/core/buildings/base.md`, `docs/modules/core/buildings/parking.md`, `docs/modules/core/buildings/site.md`
- ADRs: none recorded to date.
