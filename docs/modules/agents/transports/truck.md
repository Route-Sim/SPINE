---
title: "Truck - Transport Agent"
summary: "Autonomous transport agent that navigates through the graph network following A* computed routes, managing position state, speed constraints, and explicit route boundary metadata for logistics operations."
source_paths:
  - "agents/transports/truck.py"
  - "tests/agents/test_truck.py"
last_updated: "2025-11-12"
owner: "Mateusz Polis"
tags: ["module", "sim"]
links:
  parent: "../../../SUMMARY.md"
  siblings: ["../base.md", "../buildings/building_agent.md", "../../tests/agents/test-truck.md"]
---

# Truck - Transport Agent

> **Purpose:** Autonomous transport agent that moves through the graph network by following A* computed routes to randomly selected destinations, managing position transitions between nodes and edges while respecting speed constraints.

## Context & Motivation

In a logistics simulation, trucks are the primary transport agents responsible for moving packages between sites. The Truck agent implements autonomous navigation behavior, continuously moving through the road network to simulate realistic transport operations.

### Problem Solved
- Autonomous agent movement through graph network
- Route planning and following using A* pathfinding
- Position state management (node vs edge transitions)
- Speed constraint handling (agent and road limits)
- Explicit integration with capacity-limited parking facilities
- Efficient state change detection for UI updates

### Requirements and Constraints
- Must follow AgentBase interface for consistency
- Must integrate with Navigator service for pathfinding
- Must update position each simulation tick
- Must only emit state changes (not every tick)
- Must respect both agent max speed and edge speed limits
- Must handle edge cases: single node graph, invalid routes

### Dependencies and Assumptions
- Depends on `world.routing.navigator.Navigator` for pathfinding
- Depends on `world.graph.graph.Graph` for network structure
- Depends on `core.buildings.parking.Parking` for parking lifecycle enforcement
- Assumes `world.router` is a Navigator instance
- Assumes `world.dt_s` is simulation time step in seconds
- Assumes edges have valid length and speed attributes
- Assumes graph is connected (or handles disconnected gracefully)

## Responsibilities & Boundaries

### In-scope
- Position state management (current node/edge)
- Route planning via Navigator service
- Movement simulation (distance calculation)
- State transition logic (node ↔ edge)
- Speed management (max vs current)
- Parking assignment lifecycle (occupancy registration and release)
- Random destination selection
- Differential state serialization
- Edge resolution from node-based routes

### Out-of-scope
- Package pickup and delivery (future feature)
- Collision detection or avoidance
- Traffic simulation or congestion
- Fuel consumption or maintenance
- Path optimization beyond A* routing
- Multi-agent coordination
- Dynamic rerouting based on conditions

## Architecture & Design

### Key Data Structure

```python
@dataclass
class Truck:
    # AgentBase interface
    id: AgentID
    kind: str  # "truck"
    inbox: list[Msg]
    outbox: list[Msg]
    tags: dict[str, Any]
    _last_serialized_state: dict[str, Any]

    # Truck-specific state
    max_speed_kph: float  # Agent's maximum speed capability
    current_speed_kph: float  # Actual speed (limited by edge)
    current_node: NodeID | None  # Position if at a node
    current_edge: EdgeID | None  # Position if on an edge
    edge_progress_m: float  # Distance traveled on current edge
    route: list[NodeID]  # Remaining nodes to visit
    destination: NodeID | None  # Current target node
    route_start_node: NodeID | None  # Route origin
    route_end_node: NodeID | None  # Route destination
    current_building_id: BuildingID | None  # Parking facility association

    # Tachograph fields
    driving_time_s: float  # Accumulated driving time
    resting_time_s: float  # Accumulated rest time
    is_resting: bool  # Currently in mandatory rest
    required_rest_s: float  # Required rest duration
    balance_ducats: float  # Financial balance for penalties
    risk_factor: float  # Risk tolerance (0.0-1.0)
    is_seeking_parking: bool  # Actively seeking parking
    original_destination: NodeID | None  # Preserved when diverting
```

### State Representation

**Position state (mutually exclusive):**
- **At node:** `current_node` is set, `current_edge` is None
- **On edge:** `current_edge` is set, `current_node` is None
- **Parked:** `current_building_id` references a `Parking` building collocated with the node

**Speed state:**
- **max_speed_kph:** Agent's inherent capability (constant)
- **current_speed_kph:** Actual speed when on edge = `min(max_speed_kph, edge.max_speed_kph)`

**Route state:**
- **route_start_node:** Node where the active route originated
- **route_end_node:** Final target node for the active route
- **route:** Remaining NodeIDs to visit (excludes current position)
- **destination:** Alias maintained for compatibility with existing consumers

### Data Flow and Interactions

**Each simulation tick (`decide` method):**

1. **Route planning phase:**
   - If route is empty: pick random destination, compute route via Navigator
   - `_set_route` helper stores start/end metadata and trims the current node from the path

2. **Movement phase:**
   - **If at node:** Enter next edge in route
     - Query graph for outgoing edges
     - Find edge where `edge.to_node == route[0]`
     - Set `current_edge`, clear `current_node`
     - Set `current_speed_kph = min(max_speed_kph, edge.max_speed_kph)`

   - **If on edge:** Move along edge
     - Calculate distance: `current_speed_kph * (1000/3600) * world.dt_s`
     - Increment `edge_progress_m`
     - If edge complete: transition to next node
       - Set `current_node = edge.to_node`
       - Clear `current_edge`, reset `edge_progress_m`
       - Pop completed node from route

3. **Serialization phase:**
   - Compare current state with last serialized state
   - Return diff if changed, None otherwise (diff payload now includes `current_building_id`)

### Parking Lifecycle Helpers

- `park_in_building(world, building_id)` validates node alignment, delegates capacity checks to `Parking.park`, and assigns `current_building_id`.
- `leave_parking(world)` resolves the parking facility, releases the agent if still registered, and clears `current_building_id`.
- `_enter_next_edge` defensively calls `leave_parking` before the truck departs a node, ensuring building occupancy remains consistent whenever movement resumes.

### Tachograph System (Driving Time & Rest Management)

The truck implements a tachograph system that enforces driving time limits and mandatory rest periods, simulating real-world driver regulations.

**Key Components:**

1. **Driving Time Tracking:**
   - Accumulates `driving_time_s` while the truck is moving on edges
   - Maximum legal driving time: 8 hours (28,800 seconds)
   - Tracking begins from spawn and resets after completing mandatory rest

2. **Rest Requirements:**
   - Formula: Linear interpolation between 6h drive → 6h rest and 8h drive → 10h rest
   - 6 hours driving requires 6 hours rest (21,600 seconds)
   - 8 hours driving requires 10 hours rest (36,000 seconds)
   - Rest must be taken at parking facilities

3. **Parking Search Behavior:**
   - Probabilistic decision-making based on driving time and `risk_factor`
   - Search threshold: `7.0 + risk_factor` hours (range: 7.0-8.0 hours)
   - Probability increases linearly from threshold to 8 hours
   - Higher `risk_factor` means later parking search (riskier behavior)

4. **Penalty System:**
   - Overtime penalties applied when exceeding 8 hours:
     - 0-1 hour overtime: -100 ducats
     - 1-2 hours overtime: -200 ducats
     - 2+ hours overtime: -500 ducats
   - Penalties deducted from `balance_ducats` (can go negative)
   - Emits `truck.penalty` signal for monitoring

5. **Adaptive Risk Behavior:**
   - Trucks learn from experience by adjusting `risk_factor`
   - After penalty: risk decreases by 0.5-1% (more cautious)
   - After successful rest: risk increases by 0.5-1% (more confident)
   - Risk clamped to [0.0, 1.0] range

6. **Parking Full Handling:**
   - If parking full at arrival, searches for next closest parking
   - Maintains set of tried parkings to avoid loops
   - Navigator caches parking routes for efficiency
   - Gives up if no available parking found

**Tachograph State Fields:**

```python
driving_time_s: float = 0.0  # Accumulated driving time
resting_time_s: float = 0.0  # Accumulated rest time
is_resting: bool = False  # Currently in mandatory rest
required_rest_s: float = 0.0  # Required rest duration
balance_ducats: float = 0.0  # Financial balance
risk_factor: float = 0.5  # Risk tolerance (0.0-1.0)
is_seeking_parking: bool = False  # Actively seeking parking
original_destination: NodeID | None  # Preserved when diverting
```

**Tachograph Workflow:**

1. Truck drives accumulating `driving_time_s`
2. As driving time approaches limit, probability of seeking parking increases
3. When deciding to seek parking:
   - Preserves `original_destination`
   - Finds closest parking via Navigator
   - Routes to parking location
4. On arrival at parking:
   - Attempts to park (may fail if full)
   - If successful: calculates required rest and enters resting state
   - If full: tries next parking
5. While resting:
   - Increments `resting_time_s`
   - Can plan route to original destination (once)
   - Cannot move until rest complete
6. When rest complete:
   - Resets tachograph counters
   - Resumes journey to original destination
   - Adjusts risk based on performance

### State Transitions

```
[At Node] --enter_next_edge--> [On Edge] --move_along_edge--> [At Node]
    ^                                                              |
    |                                                              |
    +------------------route complete or empty--------------------+
                              |
                              v
                        [Plan New Route]
```

### Edge Resolution from Route

Given route `[A, B, C]` and `current_node = A`:

1. Get next node: `next_node = route[0]` (B)
2. Query edges: `edges = world.graph.get_outgoing_edges(A)`
3. Find match: `edge where edge.to_node == B`
4. Enter edge: Set `current_edge = edge.id`

This approach allows node-based routes while supporting graphs with multiple edges between nodes.

## Serialization DTOs

### TruckWatchFieldsDTO

Immutable Pydantic DTO containing only fields that trigger serialization when changed:

```python
@dataclass(frozen=True)
class TruckWatchFieldsDTO:
    current_node: NodeID | None
    current_edge: EdgeID | None
    current_speed_kph: float
    route: tuple[NodeID, ...]  # Immutable tuple for hashing
    route_start_node: NodeID | None
    route_end_node: NodeID | None
```

**Design Rationale:**
- Position and navigation fields represent meaningful state changes requiring frontend updates
- Excludes tachograph counters that change every tick (driving_time_s, resting_time_s)
- Frozen for immutability and efficient equality comparison
- Route converted to tuple for hashability

### TruckStateDTO

Complete state DTO returned in diff payloads:

```python
@dataclass(frozen=True)
class TruckStateDTO:
    # Watch fields
    current_node: NodeID | None
    current_edge: EdgeID | None
    current_speed_kph: float
    route: list[NodeID]  # Mutable list for frontend consumption
    route_start_node: NodeID | None
    route_end_node: NodeID | None

    # Metadata
    id: AgentID
    kind: str
    max_speed_kph: float
    current_building_id: str | None

    # Tachograph fields
    driving_time_s: float
    resting_time_s: float
    is_resting: bool
    balance_ducats: float
    risk_factor: float
    is_seeking_parking: bool
    original_destination: NodeID | None
```

**Design Rationale:**
- Contains all truck state for complete snapshot
- Frontend receives full context on every update
- Tachograph fields included but don't trigger updates
- Route as list (not tuple) for JSON serialization

### Serialization Workflow

1. Create `TruckWatchFieldsDTO` from current state
2. Compare with `_last_serialized_watch_state`
3. If equal: return `None` (no changes)
4. If different: create `TruckStateDTO` and return `model_dump()`
5. Update `_last_serialized_watch_state`

**Benefits:**
- Eliminates per-tick updates from tachograph counters
- Maintains complete state in each diff
- Type-safe with Pydantic validation
- Clear separation of concerns (trigger vs payload)

## Algorithms & Complexity

### Movement Calculation

**Distance per tick:**
```python
distance_m = current_speed_kph * (1000 / 3600) * world.dt_s
```

Conversion: kph → m/s → m per tick
- `1 kph = 1000 m / 3600 s = 0.277... m/s`
- Multiply by `dt_s` to get meters per tick

**Example:**
- Speed: 100 kph
- dt_s: 1.0 seconds (typical, configurable via simulation.update)
- Distance per tick: 100 * (1000/3600) * 1.0 = 27.78 meters

### Random Destination Selection

```python
available_nodes = [n for n in world.graph.nodes.keys() if n != current_node]
destination = random.choice(available_nodes)
```

**Complexity:** O(V) where V is number of nodes
- List comprehension: O(V)
- random.choice: O(1)

**Optimization opportunity:** Cache available nodes, update on graph changes

### Edge Resolution

```python
for edge in world.graph.get_outgoing_edges(current_node):
    if edge.to_node == next_node:
        return edge
```

**Complexity:** O(degree) where degree is node's out-degree
- Typically small (< 10 for most nodes)
- Could optimize with adjacency map: node_pair → edge

### Differential Serialization

The truck uses a two-tier DTO approach for efficient state change detection:

**Watch Fields (TruckWatchFieldsDTO):**
- Position and navigation fields that trigger serialization
- Changes to these fields indicate meaningful state updates
- Includes: `current_node`, `current_edge`, `current_speed_kph`, `route`, `route_start_node`, `route_end_node`

**Complete State (TruckStateDTO):**
- Full state payload returned in diffs
- Includes watch fields plus tachograph counters, metadata, and configuration
- All fields present in every diff, but diffs only emitted on watch field changes

```python
# Create watch fields DTO for comparison
current_watch_fields = TruckWatchFieldsDTO(...)

# Compare with last watch state
if current_watch_fields == _last_serialized_watch_state:
    return None  # No watch field changes

# Return complete state DTO
return TruckStateDTO(...).model_dump()
```

**Complexity:** O(k) where k is number of watch fields (6 fields, constant)
- Pydantic DTO comparison: O(k)
- Prevents excessive updates from continuously-changing tachograph counters (driving_time_s, resting_time_s)
- Reduces network traffic by 90%+ (only changes to position/navigation sent)
- All fields included in payload for complete state snapshot

## Public API / Usage

### Creation via WebSocket

**Basic creation (default 100 kph):**
```json
{
  "action": "agent.create",
  "params": {
    "agent_id": "truck-1",
    "agent_kind": "truck"
  }
}
```

**Custom speed and risk:**
```json
{
  "action": "agent.create",
  "params": {
    "agent_id": "truck-fast",
    "agent_kind": "truck",
    "agent_data": {
      "max_speed_kph": 120.0,
      "risk_factor": 0.8,
      "initial_balance_ducats": 1000.0
    }
  }
}
```

**Parameters:**
- `max_speed_kph` (float, default: 100.0): Maximum speed capability
- `risk_factor` (float, default: 0.5, range: 0.0-1.0): Risk tolerance affecting parking search timing
- `initial_balance_ducats` (float, default: 0.0): Starting financial balance

### State Updates

**Differential update (position changed):**
```json
{
  "id": "truck-1",
  "kind": "truck",
  "max_speed_kph": 100.0,
  "current_speed_kph": 80.0,
  "current_node": null,
  "current_edge": 42,
  "route": [17, 19],
  "route_start_node": 5,
  "route_end_node": 19
}
```

**No update (position unchanged):**
- `serialize_diff()` returns `None`
- No data sent to client

### Parking Workflow Helpers

```python
# Register the truck with a parking facility located on its current node
truck.park_in_building(world, BuildingID("parking-node-42"))

# Later, release the parking slot before resuming movement
truck.leave_parking(world)
```

- Resulting state diffs emit both `current_node` and `current_building_id`, enabling clients to display the precise location context.

### Integration Example

```python
# In simulation loop (world.step())
for agent in world.agents.values():
    agent.perceive(world)  # No-op for Truck
    agent.decide(world)    # Movement logic

# Collect diffs
diffs = [a.serialize_diff() for a in world.agents.values()]
diffs = [d for d in diffs if d is not None]  # Filter None
```

## Implementation Notes

### Key Design Trade-offs

1. **Node-based routes vs Edge-based routes:**
   - **Choice:** Node-based (list of NodeIDs)
   - **Rationale:** Simpler Navigator interface, works with any graph structure
   - **Trade-off:** Must resolve edges at runtime (small overhead)

2. **Differential vs Full serialization:**
   - **Choice:** Differential by default, full on demand
   - **Rationale:** Reduces network traffic, improves scalability, enriches diffs with route boundary metadata for UI overlays
   - **Trade-off:** Must track last state (small memory overhead) and ensure new fields such as `current_building_id` are included in diff comparisons

3. **Random destinations vs Assigned routes:**
   - **Choice:** Random for now
   - **Rationale:** Simpler initial implementation, tests pathfinding
   - **Trade-off:** Not realistic for logistics (future: package-driven routes)

4. **Speed management (two fields):**
   - **Choice:** Store both max_speed_kph and current_speed_kph
   - **Rationale:** Separates agent capability from situational speed
   - **Trade-off:** Slight redundancy, but clearer semantics

5. **Position representation (mutually exclusive):**
   - **Choice:** current_node OR current_edge (never both)
   - **Rationale:** Clear state machine, prevents invalid states
   - **Trade-off:** Must handle transitions carefully; parking adds an additional association that must remain consistent with node occupancy

7. **Explicit parking helpers vs implicit behaviour:**
   - **Choice:** Provide explicit `park_in_building` / `leave_parking` helpers without auto-invocation
   - **Rationale:** Keeps future actions in control of parking semantics while ensuring infrastructure is ready
   - **Trade-off:** Callers must explicitly manage parking lifecycle when orchestrating truck staging

6. **Route boundary tracking:**
   - **Choice:** Persist `route_start_node` and `route_end_node` alongside the mutable route list
   - **Rationale:** Allows consumers to display full trip context even after intermediate nodes are popped
   - **Trade-off:** Requires careful resets when routes are discarded or completed

### Third-party Libraries

- **random:** Python standard library for destination selection
- **dataclasses:** Python standard library for clean data structure

### Testing Hooks

- Stateful design requires careful test setup
- Mock World and Graph for unit tests
- Test state transitions independently

## Tests

### Test Scope and Strategy

**Unit tests** (future):
- State transitions: node → edge → node
- Route planning: random destination, Navigator integration
- Movement calculation: distance per tick, edge completion
- Edge resolution: find correct edge from route
- Serialization: diff detection, no-change returns None

**Integration tests** (future):
- Full simulation loop with multiple trucks
- Complex routes through large graphs
- Edge cases: single node, disconnected graph

### Critical Test Cases

1. **Simple movement:** Truck at node A, route to B, verify edge entry
2. **Edge traversal:** Truck on edge, verify progress and node arrival
3. **Route completion:** Truck reaches destination, verify new route planned
4. **Speed limiting:** Edge max_speed < truck max_speed, verify current_speed
5. **No route:** Disconnected graph, verify graceful handling
6. **Single node:** Graph with one node, verify truck stays put
7. **Diff serialization:** No movement, verify None returned
8. **Parking lifecycle:** Park/unpark helpers update building occupancy and serialized diffs (`tests/agents/test_truck.py`)

## Performance

### Benchmarks

**Expected performance** (not yet measured):
- Movement calculation: < 0.01ms per tick
- Route planning: 1-10ms (depends on graph size)
- Edge resolution: < 0.1ms (small out-degree)
- Serialization: < 0.01ms

### Known Bottlenecks

1. **Route planning:** A* pathfinding dominates tick time
   - Only occurs when route is empty
   - Amortized over many ticks

2. **Edge resolution:** Linear search through outgoing edges
   - Typically small (< 10 edges)
   - Could optimize with adjacency map

3. **Random destination:** List comprehension over all nodes
   - O(V) every route planning
   - Could cache available nodes

### Optimization Opportunities

1. **Route caching:** Cache routes between common node pairs
2. **Adjacency map:** Precompute node_pair → edge mapping
3. **Destination pool:** Maintain list of available destinations
4. **Batch pathfinding:** Compute routes for multiple trucks in parallel

## Security & Reliability

### Validation

- max_speed_kph validated in handler (must be positive number)
- Spawn node always valid (random selection from existing nodes)
- Route validation: clears route if edge not found

### Error Handling

- **Invalid route:** Clears route, plans new one next tick
- **Missing edge:** Logs warning (future), clears route
- **Empty graph:** No movement, no errors
- **Disconnected nodes:** Navigator returns empty route, handled gracefully

### Fault Tolerance

- State machine prevents invalid states (node and edge both set)
- Graceful degradation: if routing fails, truck stops until next planning
- No crashes on invalid input

### Logging and Observability

**Current:** No logging implemented

**Future:**
- Log route planning events
- Log state transitions (node → edge → node)
- Log speed changes
- Metrics: distance traveled, routes completed, average speed

## References

### Related Modules

- `agents.base.AgentBase`: Base agent interface
- `world.routing.navigator.Navigator`: Pathfinding service
- `world.graph.graph.Graph`: Network structure
- `world.graph.node.Node`: Node representation
- `world.graph.edge.Edge`: Edge representation with speed limits
- `world.world.World`: Simulation world container
- `world.sim.handlers.agent.AgentActionHandler`: Agent creation handler
- `core.buildings.parking.Parking`: Capacity-tracked parking facility data model
- `tests/agents/test_truck.py`: Regression tests for explicit parking lifecycle

### ADRs

- None yet (consider ADR for position state representation)

### Papers and Specifications

- None specific to Truck agent

### Issues and PRs

- None yet
