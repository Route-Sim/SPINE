# API Reference

> **Purpose:** Complete reference for all Action types (Frontend → Backend) and Signal types (Backend → Frontend) with Postman examples for testing the WebSocket API.

## Overview

The SPINE WebSocket API uses a bidirectional communication pattern:
- **Actions**: Commands sent from Frontend to Backend
- **Signals**: Updates sent from Backend to Frontend

All communication is JSON-based and real-time through WebSocket connections.

## WebSocket Connection

### Connection Details
- **URL**: `ws://localhost:8000/ws`
- **Protocol**: WebSocket
- **Format**: JSON messages
- **Authentication**: None (for testing)

### Health Check
- **URL**: `http://localhost:8000/health`
- **Method**: GET
- **Response**: `{"status": "healthy", "service": "spine-websocket"}`

### Postman Collection
A complete Postman collection with all examples is available at `docs/postman-collection.json`. Import this file into Postman to get all WebSocket API examples and test scenarios.

---

## Actions (Frontend → Backend)

Actions are commands sent from the Frontend to control the simulation.

### 1. START - Start Simulation

**Purpose**: Start the simulation with optional tick rate configuration.

**Action Type**: `start`

**JSON Example**:
```json
{
  "type": "start",
  "tick_rate": 30
}
```

**Parameters**:
- `tick_rate` (optional): Simulation frequency in Hz (default: 20)

**Postman Test**:
1. Connect to `ws://localhost:8000/ws`
2. Send the JSON above
3. Expect acknowledgment and simulation_started signal

---

### 2. STOP - Stop Simulation

**Purpose**: Stop the running simulation.

**Action Type**: `stop`

**JSON Example**:
```json
{
  "type": "stop"
}
```

**Parameters**: None

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment and simulation_stopped signal

---

### 3. PAUSE - Pause Simulation

**Purpose**: Pause the running simulation.

**Action Type**: `pause`

**JSON Example**:
```json
{
  "type": "pause"
}
```

**Parameters**: None

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment and simulation_paused signal

---

### 4. RESUME - Resume Simulation

**Purpose**: Resume the paused simulation.

**Action Type**: `resume`

**JSON Example**:
```json
{
  "type": "resume"
}
```

**Parameters**: None

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment and simulation_resumed signal

---

### 5. SET_TICK_RATE - Change Simulation Speed

**Purpose**: Change the simulation tick rate while running.

**Action Type**: `set_tick_rate`

**JSON Example**:
```json
{
  "type": "set_tick_rate",
  "tick_rate": 60
}
```

**Parameters**:
- `tick_rate` (required): New simulation frequency in Hz

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment (no additional signal)

---

### 6. ADD_AGENT - Add New Agent

**Purpose**: Add a new agent to the simulation.

**Action Type**: `add_agent`

**JSON Example**:
```json
{
  "type": "add_agent",
  "agent_id": "truck1",
  "agent_kind": "transport",
  "agent_data": {
    "capacity": 1000,
    "speed": 50,
    "location": "warehouse1"
  }
}
```

**Parameters**:
- `agent_id` (required): Unique identifier for the agent
- `agent_kind` (required): Type of agent ("transport", "building", etc.)
- `agent_data` (required): Agent-specific properties

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment and agent_update signal

**Note**: This is the legacy format. For new implementations, use the canonical action format below.

---

### 6a. agent.create - Create Agent (Canonical Format)

**Purpose**: Create a new agent using the canonical action format.

**Action Type**: `agent.create`

**JSON Example - Truck Agent (Default Speed)**:
```json
{
  "action": "agent.create",
  "params": {
    "agent_id": "truck-1",
    "agent_kind": "truck"
  }
}
```

**JSON Example - Truck Agent (Custom Speed)**:
```json
{
  "action": "agent.create",
  "params": {
    "agent_id": "truck-fast",
    "agent_kind": "truck",
    "agent_data": {
      "max_speed_kph": 120.0
    }
  }
}
```

**JSON Example - Building Agent**:
```json
{
  "action": "agent.create",
  "params": {
    "agent_id": "building-1",
    "agent_kind": "building",
    "agent_data": {}
  }
}
```

**Parameters**:
- `agent_id` (required, string): Unique identifier for the agent
- `agent_kind` (required, string): Type of agent
  - `"truck"`: Autonomous transport agent with A* navigation
  - `"building"`: Stationary building agent
- `agent_data` (optional, object): Agent-specific configuration

**Agent-Specific Parameters**:

**Truck (`agent_kind: "truck"`)**:
- `max_speed_kph` (optional, number): Maximum speed capability in km/h (default: 100.0)
  - Must be positive number
  - Truck will spawn at random node
  - Actual speed limited by road max_speed during movement

**Building (`agent_kind: "building"`)**:
- No specific parameters currently

**Response Signals**:
- `agent.created` signal with full agent state immediately after creation
- Agent state updates in subsequent tick signals (only when state changes)

**Postman Test - Truck Creation**:
1. Connect to `ws://localhost:8000/ws`
2. Start simulation: `{"action": "simulation.start", "params": {}}`
3. Create truck: `{"action": "agent.create", "params": {"agent_id": "truck-1", "agent_kind": "truck"}}`
4. Observe truck movement in tick signals
5. Create fast truck: `{"action": "agent.create", "params": {"agent_id": "truck-2", "agent_kind": "truck", "agent_data": {"max_speed_kph": 150.0}}}`

**Expected Behavior**:
- Truck spawns at random node in the graph
- `agent.created` signal emitted with full initial state
- Truck automatically picks random destinations
- Truck follows A* computed routes
- State updates only sent when node, edge, speed, or route changes (NOT every tick)
- Truck respects both its max_speed and edge speed limits
- Frontend receives route information for visualization

**Notes**:
- Trucks require a graph with at least 2 nodes to move
- Single-node graphs will result in stationary trucks
- Trucks continuously move to random destinations (future: package-driven routes)
- Position state is either `current_node` (at node) or `current_edge` (on edge), never both

---

### 6b. agent.describe - Describe Agent (Canonical Format)

**Purpose**: Retrieve the full serialized state for a single agent on demand.

**Action Type**: `agent.describe`

**JSON Example**:
```json
{
  "action": "agent.describe",
  "params": {
    "agent_id": "truck-1"
  }
}
```

**Parameters**:
- `agent_id` (required, string): Identifier of the agent to inspect.

**Prerequisites**:
- The requested agent must already exist in the world.

**Response Signals**:
- `agent.described` signal containing the full agent payload plus the current simulation tick.

**Error Signals**:
- `error` with code `GENERIC_ERROR` and descriptive message when the agent cannot be found.

**Postman Test**:
1. Start the simulation: `{"action": "simulation.start", "params": {}}`
2. Create an agent (e.g., `agent.create` as shown above).
3. Send the describe request JSON shown here.
4. Observe the `agent.described` signal containing the same serialized structure emitted during state snapshots.

---

### 6c. agent.list - List Agents (Canonical Format)

**Purpose**: Retrieve serialized states for all agents, optionally filtered by kind.

**Action Type**: `agent.list`

**JSON Example - All Agents**:
```json
{
  "action": "agent.list",
  "params": {}
}
```

**JSON Example - Filter by Kind**:
```json
{
  "action": "agent.list",
  "params": {
    "agent_kind": "truck"
  }
}
```

**Parameters**:
- `agent_kind` (optional, string): Filter results to agents whose `kind` matches.

**Response Signals**:
- `agent.listed` signal containing `total`, `agents` (list of serialized payloads), and `tick`.

**Error Signals**:
- `error` with code `GENERIC_ERROR` and descriptive message when validation fails (e.g., non-string `agent_kind`).

**Postman Test**:
1. Create several agents (e.g., `agent.create` for trucks/buildings).
2. Send `{ "action": "agent.list", "params": {} }` to fetch all agents.
3. Optionally filter: `{ "action": "agent.list", "params": { "agent_kind": "truck" } }`.
4. Observe the `agent.listed` response; each agent entry includes `agent_id`, `kind`, and associated state fields.

---

### 7. DELETE_AGENT - Remove Agent

**Purpose**: Remove an existing agent from the simulation.

**Action Type**: `delete_agent`

**JSON Example**:
```json
{
  "type": "delete_agent",
  "agent_id": "truck1"
}
```

**Parameters**:
- `agent_id` (required): ID of the agent to remove

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment (agent will be removed)

---

### 8. MODIFY_AGENT - Update Agent Properties

**Purpose**: Modify properties of an existing agent.

**Action Type**: `modify_agent`

**JSON Example**:
```json
{
  "type": "modify_agent",
  "agent_id": "truck1",
  "agent_data": {
    "speed": 75,
    "capacity": 1500,
    "status": "active"
  }
}
```

**Parameters**:
- `agent_id` (required): ID of the agent to modify
- `agent_data` (required): New properties to update

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment and agent_update signal

---

### 9. EXPORT_MAP - Export Current Map

**Purpose**: Export the current simulation map to a GraphML file.

**Action Type**: `export_map`

**JSON Example**:
```json
{
  "type": "export_map",
  "metadata": {
    "map_name": "my_custom_map"
  }
}
```

**Parameters**:
- `metadata` (required): Object containing map information
  - `map_name` (required): Name for the map file

**Notes**:
- Simulation must be stopped before exporting
- Map name will be sanitized to prevent path traversal
- Exports to `/maps/{sanitized_name}.graphml`
- Fails if file already exists

**Postman Test**:
1. Ensure simulation is stopped
2. Send the JSON above
3. Expect acknowledgment and map_exported signal

---

### 10. IMPORT_MAP - Import Saved Map

**Purpose**: Import a previously saved map from a GraphML file.

**Action Type**: `import_map`

**JSON Example**:
```json
{
  "type": "import_map",
  "metadata": {
    "map_name": "my_custom_map"
  }
}
```

**Parameters**:
- `metadata` (required): Object containing map information
  - `map_name` (required): Name of the map file to import

**Notes**:
- Simulation must be stopped before importing
- Map name will be sanitized
- Imports from `/maps/{sanitized_name}.graphml`
- Fails if file doesn't exist

**Postman Test**:
1. Ensure simulation is stopped
2. Send the JSON above
3. Expect acknowledgment and map_imported signal

---

### 11. CREATE_MAP - Generate New Map Procedurally

**Purpose**: Generate a new simulation map procedurally using hierarchical algorithms with Polish road classification.

**Action Type**: `map.create`

**JSON Example**:
```json
{
  "action": "map.create",
  "params": {
    "map_width": 10000,
    "map_height": 10000,
    "num_major_centers": 3,
    "minor_per_major": 2.0,
    "center_separation": 2500.0,
    "urban_sprawl": 800.0,
    "local_density": 50.0,
    "rural_density": 5.0,
    "intra_connectivity": 0.3,
    "inter_connectivity": 2,
    "arterial_ratio": 0.2,
    "gridness": 0.3,
    "ring_road_prob": 0.5,
    "highway_curviness": 0.2,
    "rural_settlement_prob": 0.15,
    "urban_sites_per_km2": 5.0,
    "rural_sites_per_km2": 1.0,
    "urban_activity_rate_range": [5.0, 20.0],
    "rural_activity_rate_range": [1.0, 8.0],
    "seed": 42
  }
}
```

**Parameters**:
- `map_width` (required): Map width in meters (must be positive)
- `map_height` (required): Map height in meters (must be positive)
- `num_major_centers` (required): Number of major cities (must be ≥1)
- `minor_per_major` (required): Average number of minor towns per major city (≥0)
- `center_separation` (required): Minimum distance between major centers in meters (>0)
- `urban_sprawl` (required): Typical city radius in meters (>0)
- `local_density` (required): Node density inside cities (nodes per km², >0)
- `rural_density` (required): Node density outside cities (nodes per km², ≥0)
- `intra_connectivity` (required): Edge density within cities (0-1, higher = more roads)
- `inter_connectivity` (required): Highway redundancy factor (≥1, higher = more alternatives)
- `arterial_ratio` (required): Share of arterial roads in cities (0-1)
- `gridness` (required): Street pattern (0=organic, 1=grid-like, 0-1)
- `ring_road_prob` (required): Probability of ring roads around major cities (0-1)
- `highway_curviness` (required): Highway path curvature (0=straight, 1=curved, 0-1)
- `rural_settlement_prob` (required): Probability of rural settlements (0-1)
- `urban_sites_per_km2` (required): Density of site buildings in urban areas (sites per km², ≥0)
- `rural_sites_per_km2` (required): Density of site buildings in rural areas (sites per km², ≥0)
- `urban_activity_rate_range` (required): Activity rate range for urban sites as [min, max] array (packages/hour, both ≥0)
- `rural_activity_rate_range` (required): Activity rate range for rural sites as [min, max] array (packages/hour, both ≥0)
- `seed` (required): Random seed for reproducibility (integer)

**Notes**:
- Simulation must be stopped before creating a new map
- Uses hierarchical generation: centers → nodes → intra-city roads → highways → rings → buildings
- Implements Polish road classification (A, S, GP, G, Z, L, D)
- Assigns lane counts (1-6), speed limits (20-140 km/h), and weight restrictions
- Uses Poisson disk sampling for natural node placement
- Uses Delaunay triangulation + Gabriel graph for realistic road networks
- Highways connect cities via k-nearest neighbor graph
- 95% of city roads are bidirectional, 100% of highways are bidirectional
- Places Site buildings on nodes (excluding highway-only nodes)
- Urban sites have higher baseline activity, rural sites can occasionally be very active
- Destination weights favor rural→city patterns (70-80%) while allowing all combinations
- Returns signal with generation statistics

**Example Configurations**:

*Dense Urban Map:*
```json
{
  "num_major_centers": 5,
  "local_density": 80.0,
  "rural_density": 0.0,
  "gridness": 0.7,
  "ring_road_prob": 1.0,
  "urban_sites_per_km2": 10.0,
  "rural_sites_per_km2": 0.0,
  "urban_activity_rate_range": [10.0, 30.0],
  "rural_activity_rate_range": [0.0, 0.0]
}
```

*Sparse Rural Map:*
```json
{
  "num_major_centers": 2,
  "local_density": 20.0,
  "rural_density": 10.0,
  "gridness": 0.0,
  "rural_settlement_prob": 0.3,
  "urban_sites_per_km2": 3.0,
  "rural_sites_per_km2": 2.0,
  "urban_activity_rate_range": [5.0, 15.0],
  "rural_activity_rate_range": [0.5, 5.0]
}
```

**Postman Test**:
1. Ensure simulation is stopped
2. Send the JSON above
3. Expect acknowledgment and map.created signal with generation statistics
4. Inspect `data.graph` to confirm nodes/edges arrays are present (buildings intentionally omitted)

---

### 12. REQUEST_STATE - Request Full State Snapshot

**Purpose**: Request a complete snapshot of the current simulation state (map + agents).

**Action Type**: `request_state`

**JSON Example**:
```json
{
  "type": "request_state"
}
```

**Parameters**: None

**Notes**:
- Returns complete map data and all agent states
- Useful for frontend initialization or state recovery
- Can be requested at any time during simulation

**Postman Test**:
1. Send the JSON above
2. Expect acknowledgment and state snapshot signals (see Signals section)

---

### 13. BUILDING_CREATE - Provision Parking Building

**Purpose**: Provision a capacity-limited parking facility on an existing node.

**Action Type**: `building.create`

**JSON Example**:
```json
{
  "action": "building.create",
  "params": {
    "building_id": "parking-node42",
    "node_id": 42,
    "capacity": 40
  }
}
```

**Parameters**:
- `building_id` (required, string): Unique identifier for the parking building.
- `node_id` (required, integer): Graph node (host) that already exists in the generated map.
- `capacity` (required, integer): Maximum number of trucks the parking can host; must be positive.
- `building_type` (optional, string): Defaults to `"parking"`. Non-parking types are rejected until future extensions land.

**Notes**:
- Validation fails if the node is missing or the ID collides with an existing building.
- Successful execution mutates the world graph in-place and emits a `building.created` signal with canonical payload (`current_agents` starts empty until future routing logic assigns trucks).

**Postman Test**:
1. Start or resume the simulation (`simulation.start`).
2. Send the JSON above to create the parking building.
3. Expect immediate `building.created` signal acknowledging the new facility.
4. Optionally send a follow-up `state.request` to verify the parking was attached to the node.

---

## Signals (Backend → Frontend)

Signals are updates sent from the Backend to inform the Frontend about simulation state changes.

### 1. TICK_START - Simulation Tick Started

**Purpose**: Indicates the start of a simulation tick.

**Signal**: `tick.start`

**JSON Example**:
```json
{
  "signal": "tick.start",
  "data": {
    "tick": 123
  }
}
```

**Fields**:
- `data.tick`: Current simulation tick number

**When Received**: At the beginning of each simulation step

---

### 2. TICK_END - Simulation Tick Ended

**Purpose**: Indicates the end of a simulation tick.

**Signal**: `tick.end`

**JSON Example**:
```json
{
  "signal": "tick.end",
  "data": {
    "tick": 123
  }
}
```

**Fields**:
- `data.tick`: Current simulation tick number

**When Received**: At the end of each simulation step

---

### 3. AGENT_CREATED - Agent Created

**Purpose**: Notifies that a new agent has been created in the simulation.

**Signal**: `agent.created`

**JSON Example - Truck Agent**:
```json
{
  "signal": "agent.created",
  "data": {
    "id": "truck-1",
    "kind": "truck",
    "max_speed_kph": 100.0,
    "current_speed_kph": 0.0,
    "current_node": 5,
    "current_edge": null,
    "edge_progress_m": 0.0,
    "route": [],
    "destination": null,
    "inbox_count": 0,
    "outbox_count": 0,
    "tags": {}
  }
}
```

**JSON Example - Building Agent**:
```json
{
  "signal": "agent.created",
  "data": {
    "id": "building-1",
    "kind": "building",
    "tags": {},
    "inbox_count": 0,
    "outbox_count": 0,
    "building": {
      "id": "building-1"
    }
  }
}
```

**Fields**:
- `data.id`: Agent ID
- `data.kind`: Agent type ("truck", "building", etc.)
- `data.*`: Full agent state (varies by agent type)

**Truck-Specific Fields**:
- `data.max_speed_kph`: Maximum speed capability
- `data.current_speed_kph`: Current speed (0 when spawned)
- `data.current_node`: Spawn node ID
- `data.current_edge`: null (spawns at node)
- `data.route`: Empty initially
- `data.destination`: null initially

**When Received**: Immediately after `agent.create` action is processed

---

### 3a. AGENT_DESCRIBED - Agent Snapshot Response

**Purpose**: Returns the full serialized state for a specific agent requested through `agent.describe`.

**Signal**: `agent.described`

**JSON Example**:
```json
{
  "signal": "agent.described",
  "data": {
    "id": "truck-1",
    "kind": "truck",
    "max_speed_kph": 100.0,
    "current_speed_kph": 0.0,
    "current_node": 5,
    "current_edge": null,
    "route": [],
    "destination": null,
    "inbox_count": 0,
    "outbox_count": 0,
    "tags": {},
    "tick": 120
  }
}
```

**Fields**:
- Identical to `agent.created`, reflecting the current full state of the agent.
- `data.tick`: Simulation tick number when the snapshot was taken.

**When Received**: Immediately after a successful `agent.describe` action.

---

### 3b. AGENT_LISTED - Agent Collection Snapshot

**Purpose**: Returns aggregated serialized state for agents, typically after `agent.list`.

**Signal**: `agent.listed`

**JSON Example**:
```json
{
  "signal": "agent.listed",
  "data": {
    "total": 2,
    "agents": [
      {
        "agent_id": "truck-1",
        "id": "truck-1",
        "kind": "truck",
        "inbox_count": 0,
        "outbox_count": 0,
        "tags": {}
      },
      {
        "agent_id": "building-1",
        "id": "building-1",
        "kind": "building",
        "inbox_count": 0,
        "outbox_count": 0,
        "tags": {}
      }
    ],
    "tick": 120
  }
}
```

**Fields**:
- `data.total`: Count of agents included after any filtering.
- `data.agents`: Array of serialized agent payloads (matches `serialize_full()` output plus `agent_id`).
- `data.tick`: Simulation tick when the snapshot was generated.

**When Received**: After a successful `agent.list` action.

---

### 4. AGENT_UPDATE - Agent State Changed

**Purpose**: Notifies about changes in agent state (differential updates).

**Signal**: `agent.updated`

**JSON Example - Truck Entering Edge**:
```json
{
  "signal": "agent.updated",
  "data": {
    "id": "truck-1",
    "kind": "truck",
    "max_speed_kph": 100.0,
    "current_speed_kph": 80.0,
    "current_node": null,
    "current_edge": 42,
    "route": [7, 10, 15]
  }
}
```

**JSON Example - Truck Arriving at Node**:
```json
{
  "signal": "agent.updated",
  "data": {
    "id": "truck-1",
    "kind": "truck",
    "max_speed_kph": 100.0,
    "current_speed_kph": 0.0,
    "current_node": 7,
    "current_edge": null,
    "route": [10, 15]
  }
}
```

**Fields**:
- `data.id`: Agent ID
- `data.kind`: Agent type
- `data.*`: Changed state fields (varies by agent type)

**Truck-Specific Fields**:
- `data.current_node`: Node ID if at node, null if on edge
- `data.current_edge`: Edge ID if on edge, null if at node
- `data.current_speed_kph`: Current speed (0 at node, limited by edge when moving)
- `data.route`: Remaining nodes to visit (for frontend visualization)

**Important Notes**:
- Trucks only emit updates when node, edge, speed, or route changes
- `edge_progress_m` is NOT included (frontend doesn't need it)
- Updates are NOT sent every tick, only on meaningful state changes
- This reduces network traffic significantly

**When Received**: When an agent's state changes (not every tick)

---

### 4. WORLD_EVENT - Simulation Event

**Purpose**: Reports general simulation events.

**Signal**: `event.created`

**JSON Example**:
```json
{
  "signal": "event.created",
  "data": {
    "tick": 123,
    "event_type": "agent_added",
    "agent_id": "truck1",
    "agent_kind": "transport",
    "timestamp": 1640995200
  }
}
```

**Fields**:
- `data.tick`: Simulation tick when event occurred
- `data.*`: Event details

**When Received**: When simulation events occur

---

### 5. ERROR - Error Notification

**Purpose**: Reports errors that occurred in the simulation.

**Signal**: `error`

**JSON Example**:
```json
{
  "signal": "error",
  "data": {
    "code": "GENERIC_ERROR",
    "message": "Agent truck1 not found",
    "tick": 123
  }
}
```

**Fields**:
- `data.code`: Error code (e.g., "GENERIC_ERROR")
- `data.message`: Description of the error
- `data.tick`: Simulation tick when error occurred (optional)

**When Received**: When errors occur in the simulation

---

### 6. SIMULATION_STARTED - Simulation Started

**Purpose**: Confirms that the simulation has started.

**Signal**: `simulation.started`

**JSON Example**:
```json
{
  "signal": "simulation.started",
  "data": {
    "tick_rate": 30
  }
}
```

**Fields**:
- `data.tick_rate`: Simulation tick rate in Hz (optional)

**When Received**: After successful start action

---

### 7. SIMULATION_STOPPED - Simulation Stopped

**Purpose**: Confirms that the simulation has stopped.

**Signal**: `simulation.stopped`

**JSON Example**:
```json
{
  "signal": "simulation.stopped",
  "data": {}
}
```

**Fields**:
- `data`: Empty object

**When Received**: After successful stop action

---

### 8. SIMULATION_PAUSED - Simulation Paused

**Purpose**: Confirms that the simulation has been paused.

**Signal**: `simulation.paused`

**JSON Example**:
```json
{
  "signal": "simulation.paused",
  "data": {}
}
```

**Fields**:
- `data`: Empty object

**When Received**: After successful pause action

---

### 9. SIMULATION_RESUMED - Simulation Resumed

**Purpose**: Confirms that the simulation has been resumed.

**Signal**: `simulation.resumed`

**JSON Example**:
```json
{
  "signal": "simulation.resumed",
  "data": {}
}
```

**Fields**:
- `data`: Empty object

**When Received**: After successful resume action

---

### 10. MAP_EXPORTED - Map Export Confirmation

**Purpose**: Confirms that a map was successfully exported.

**Signal**: `map.exported`

**JSON Example**:
```json
{
  "signal": "map.exported",
  "data": {
    "map_name": "my_custom_map"
  }
}
```

**Fields**:
- `data.map_name`: Name of the exported map

**When Received**: After successful map export

---

### 11. MAP_IMPORTED - Map Import Confirmation

**Purpose**: Confirms that a map was successfully imported.

**Signal**: `map.imported`

**JSON Example**:
```json
{
  "signal": "map.imported",
  "data": {
    "map_name": "my_custom_map"
  }
}
```

**Fields**:
- `data.map_name`: Name of the imported map

**When Received**: After successful map import

---

### 12. MAP_CREATED - Map Generation Confirmation

**Purpose**: Confirms that a procedural map was successfully generated with hierarchical structure.

**Signal**: `map.created`

**JSON Example**:
```json
{
  "signal": "map.created",
  "data": {
    "map_width": 10000,
    "map_height": 10000,
    "num_major_centers": 3,
    "minor_per_major": 2.0,
    "center_separation": 2500.0,
    "urban_sprawl": 800.0,
    "local_density": 50.0,
    "rural_density": 5.0,
    "intra_connectivity": 0.3,
    "inter_connectivity": 2,
    "arterial_ratio": 0.2,
    "gridness": 0.3,
    "ring_road_prob": 0.5,
    "highway_curviness": 0.2,
    "rural_settlement_prob": 0.15,
    "urban_sites_per_km2": 5.0,
    "rural_sites_per_km2": 1.0,
    "urban_activity_rate_range": [5.0, 20.0],
    "rural_activity_rate_range": [1.0, 8.0],
    "seed": 42,
    "generated_nodes": 850,
    "generated_edges": 2400,
    "generated_sites": 45,
    "graph": {
      "nodes": [
        {"id": "1", "x": 0.0, "y": 0.0},
        {"id": "2", "x": 120.0, "y": 45.0}
      ],
      "edges": [
        {
          "id": "10",
          "from_node": "1",
          "to_node": "2",
          "length_m": 115.0,
          "mode": 1,
          "road_class": "L",
          "lanes": 2,
          "max_speed_kph": 50.0,
          "weight_limit_kg": null
        }
      ]
    }
  }
}
```

**Fields**:
- `data.map_width`: Map width in meters
- `data.map_height`: Map height in meters
- `data.num_major_centers`: Number of major cities generated
- `data.minor_per_major`: Average minor towns per major city
- `data.center_separation`: Minimum distance between major centers
- `data.urban_sprawl`: Typical city radius
- `data.local_density`: Node density inside cities (nodes per km²)
- `data.rural_density`: Node density outside cities (nodes per km²)
- `data.intra_connectivity`: Edge density within cities (0-1)
- `data.inter_connectivity`: Highway redundancy factor
- `data.arterial_ratio`: Share of arterial roads in cities (0-1)
- `data.gridness`: Street pattern (0=organic, 1=grid-like)
- `data.ring_road_prob`: Probability of ring roads (0-1)
- `data.highway_curviness`: Highway curvature (0=straight, 1=curved)
- `data.rural_settlement_prob`: Probability of rural settlements (0-1)
- `data.urban_sites_per_km2`: Site density in urban areas (sites per km²)
- `data.rural_sites_per_km2`: Site density in rural areas (sites per km²)
- `data.urban_activity_rate_range`: Activity rate range for urban sites (packages/hour)
- `data.rural_activity_rate_range`: Activity rate range for rural sites (packages/hour)
- `data.seed`: Random seed used for generation
- `data.generated_nodes`: Actual number of nodes created
- `data.generated_edges`: Actual number of edges created
- `data.generated_sites`: Actual number of site buildings placed
- `data.graph.nodes`: Simplified node list (id/x/y) for immediate rendering
- `data.graph.edges`: Simplified edge list with topology and road attributes (no buildings/agents)

**When Received**: After successful procedural map generation with hierarchical algorithm. Use `state.full_map_data` if the frontend needs full node building inventories.

---

### 13. STATE_SNAPSHOT_START - State Snapshot Started

**Purpose**: Indicates the beginning of a complete state snapshot transmission.

**Signal**: `state.snapshot_start`

**JSON Example**:
```json
{
  "signal": "state.snapshot_start",
  "data": {}
}
```

**Fields**:
- `data`: Empty object

**When Received**: Before sending complete state data (map + agents)

---

### 14. STATE_SNAPSHOT_END - State Snapshot Completed

**Purpose**: Indicates the end of a complete state snapshot transmission.

**Signal**: `state.snapshot_end`

**JSON Example**:
```json
{
  "signal": "state.snapshot_end",
  "data": {}
}
```

**Fields**:
- `data`: Empty object

**When Received**: After all state data has been sent

---

### 15. FULL_MAP_DATA - Complete Map Data

**Purpose**: Contains the complete graph structure (nodes and edges).

**Signal**: `state.full_map_data`

**JSON Example**:
```json
{
  "signal": "state.full_map_data",
  "data": {
    "nodes": [
      {
        "id": "1",
        "x": 0.0,
        "y": 0.0,
        "buildings": [
          {
            "id": "building1",
            "type": "warehouse",
            "capacity": 1000
          }
        ]
      }
    ],
    "edges": [
      {
        "id": "1",
        "from_node": "1",
        "to_node": "2",
        "length_m": 100.0,
        "mode": 1
      }
    ]
  }
}
```

**Fields**:
- `data`: Complete graph structure
  - `nodes`: Array of node objects with coordinates and buildings
  - `edges`: Array of edge objects with connections and properties

**When Received**: As part of state snapshot transmission

---

### 16. FULL_AGENT_DATA - Complete Agent State

**Purpose**: Contains the complete state of a single agent.

**Signal**: `state.full_agent_data`

**JSON Example**:
```json
{
  "signal": "state.full_agent_data",
  "data": {
    "id": "truck1",
    "kind": "transport",
    "tags": {
      "status": "moving",
      "cargo": "electronics"
    },
    "inbox_count": 0,
    "outbox_count": 1,
    "state": "ENROUTE",
    "pos": {
      "edge": "1",
      "s_m": 50.0
    },
    "vel_mps": 15.0,
    "capacity": 1000.0,
    "load": 500.0,
    "telemetry": {
      "distance_m": 1500.0,
      "fuel_j": 50000.0,
      "co2_kg": 25.0
    }
  }
}
```

**Fields**:
- `data`: Complete agent state including position, status, and telemetry

**When Received**: As part of state snapshot transmission (one signal per agent)

---

### 17. PACKAGE_CREATED - Package Created

**Purpose**: Notifies when a new package is created at a site.

**Signal**: `package.created`

**JSON Example**:
```json
{
  "signal": "package.created",
  "data": {
    "id": "pkg-123",
    "origin_site": "warehouse-a",
    "destination_site": "warehouse-b",
    "size_kg": 25.0,
    "value_currency": 1500.0,
    "priority": "HIGH",
    "urgency": "EXPRESS",
    "spawn_tick": 1000,
    "pickup_deadline_tick": 4600,
    "delivery_deadline_tick": 8200,
    "status": "WAITING_PICKUP",
    "tick": 1000
  }
}
```

**Fields**:
- `data`: Complete package information including `tick` field

**When Received**: When a site spawns a new package

---

### 18. PACKAGE_EXPIRED - Package Expired

**Purpose**: Notifies when a package expires (not picked up by deadline).

**Signal**: `package.expired`

**JSON Example**:
```json
{
  "signal": "package.expired",
  "data": {
    "package_id": "pkg-123",
    "site_id": "warehouse-a",
    "value_lost": 1500.0,
    "tick": 4600
  }
}
```

**Fields**:
- `data.package_id`: ID of the expired package
- `data.site_id`: Site where package expired
- `data.value_lost`: Monetary value lost due to expiry
- `data.tick`: Simulation tick when package expired

**When Received**: When a package passes its pickup deadline

---

### 19. PACKAGE_PICKED_UP - Package Picked Up

**Purpose**: Notifies when a package is picked up by an agent.

**Signal**: `package.picked_up`

**JSON Example**:
```json
{
  "signal": "package.picked_up",
  "data": {
    "package_id": "pkg-123",
    "agent_id": "truck-1",
    "tick": 2000
  }
}
```

**Fields**:
- `data.package_id`: ID of the picked up package
- `data.agent_id`: ID of the agent that picked up the package
- `data.tick`: Simulation tick when package was picked up

**When Received**: When an agent picks up a package

---

### 20. PACKAGE_DELIVERED - Package Delivered

**Purpose**: Notifies when a package is successfully delivered to its destination.

**Signal**: `package.delivered`

**JSON Example**:
```json
{
  "signal": "package.delivered",
  "data": {
    "package_id": "pkg-123",
    "site_id": "warehouse-b",
    "value": 1500.0,
    "tick": 5000
  }
}
```

**Fields**:
- `data.package_id`: ID of the delivered package
- `data.site_id`: Destination site where package was delivered
- `data.value`: Monetary value of the delivered package
- `data.tick`: Simulation tick when package was delivered

**When Received**: When a package reaches its destination site

---

### 21. SITE_STATS_UPDATE - Site Statistics Update

**Purpose**: Provides periodic updates of site statistics for business intelligence.

**Signal**: `site.stats_update`

**JSON Example**:
```json
{
  "signal": "site.stats_update",
  "data": {
    "site_id": "warehouse-a",
    "stats": {
      "packages_generated": 150,
      "packages_picked_up": 140,
      "packages_delivered": 135,
      "packages_expired": 5,
      "total_value_delivered": 150000.0,
      "total_value_expired": 5000.0
    },
    "tick": 1000
  }
}
```

**Fields**:
- `data.site_id`: ID of the site
- `data.stats`: Complete statistics object
- `data.tick`: Simulation tick when statistics were updated

**When Received**: Periodically or when significant changes occur

---

### 22. BUILDING_CREATED - Parking Building Provisioned

**Purpose**: Confirms that a parking building has been provisioned on a node in response to `building.create`.

**Signal**: `building.created`

**JSON Example**:
```json
{
  "signal": "building.created",
  "data": {
    "node_id": 42,
    "building": {
      "id": "parking-node42",
      "type": "parking",
      "capacity": 40,
      "current_agents": []
    },
    "tick": 512
  }
}
```

**Fields**:
- `data.node_id`: Host node identifier.
- `data.building`: Canonical building payload (matches `Parking.to_dict()` output).
- `data.tick`: Simulation tick when the parking was created.

**When Received**: Immediately after the handler validates and installs the parking building.

---

## Postman Testing Workflow

### 1. Basic Connection Test

1. **Connect to WebSocket**:
   - URL: `ws://localhost:8000/ws`
   - Should see "Connected" status

2. **Test Health Endpoint**:
   - GET `http://localhost:8000/health`
   - Should return: `{"status": "healthy", "service": "spine-websocket"}`

### 2. Simulation Control Test

1. **Start Simulation**:
   ```json
   {"type": "start", "tick_rate": 30}
   ```
   - Expect: `{"type": "action_ack", "action_type": "start", "status": "received"}`
   - Expect: `{"signal": "simulation.started", "data": {"tick_rate": 30}}`

2. **Pause Simulation**:
   ```json
   {"type": "pause"}
   ```
   - Expect: `{"type": "action_ack", "action_type": "pause", "status": "received"}`
   - Expect: `{"signal": "simulation.paused", "data": {}}`

3. **Resume Simulation**:
   ```json
   {"type": "resume"}
   ```
   - Expect: `{"type": "action_ack", "action_type": "resume", "status": "received"}`
   - Expect: `{"signal": "simulation.resumed", "data": {}}`

4. **Stop Simulation**:
   ```json
   {"type": "stop"}
   ```
   - Expect: `{"type": "action_ack", "action_type": "stop", "status": "received"}`
   - Expect: `{"signal": "simulation.stopped", "data": {}}`

### 3. Agent Management Test

1. **Add Agent**:
   ```json
   {
     "type": "add_agent",
     "agent_id": "truck1",
     "agent_kind": "transport",
     "agent_data": {"capacity": 1000, "speed": 50}
   }
   ```
   - Expect: Acknowledgment and agent_update signal

2. **Modify Agent**:
   ```json
   {
     "type": "modify_agent",
     "agent_id": "truck1",
     "agent_data": {"speed": 75, "status": "active"}
   }
   ```
   - Expect: Acknowledgment and agent_update signal

3. **Delete Agent**:
   ```json
   {
     "type": "delete_agent",
     "agent_id": "truck1"
   }
   ```
   - Expect: Acknowledgment (agent removed)

### 4. Map Export/Import Test

1. **Export Map** (simulation must be stopped):
   ```json
   {
     "type": "export_map",
     "metadata": {"map_name": "test_map"}
   }
   ```
   - Expect: Acknowledgment and map_exported signal
   - Error if simulation is running

2. **Import Map** (simulation must be stopped):
   ```json
   {
     "type": "import_map",
     "metadata": {"map_name": "test_map"}
   }
   ```
   - Expect: Acknowledgment and map_imported signal
   - Error if simulation is running or file doesn't exist

### 5. Package Lifecycle Test

1. **Start Simulation** and observe package signals:
   - `package_created` signals when sites spawn packages
   - `package_picked_up` signals when agents pick up packages
   - `package_delivered` signals when packages reach destinations
   - `package_expired` signals when packages pass pickup deadlines
   - `site_stats_update` signals with site statistics

2. **Monitor Package Events**:
   - Packages should spawn at sites based on Poisson process
   - Package deadlines are in ticks (1 tick = 1 simulation second)
   - Expired packages generate failure metrics
   - Site statistics track all package lifecycle events

### 6. Real-time Updates Test

1. **Start Simulation** and observe:
   - `tick_start` signals every ~33ms (30Hz)
   - `tick_end` signals every ~33ms
   - `agent_update` signals when agents change
   - `world_event` signals for simulation events

### 7. Error Handling Test

1. **Invalid Action**:
   ```json
   {"type": "invalid_action"}
   ```
   - Expect: Error signal with validation message

2. **Missing Agent**:
   ```json
   {"type": "delete_agent", "agent_id": "nonexistent"}
   ```
   - Expect: Error signal with "Agent not found" message

3. **Map Export While Running**:
   ```json
   {
     "type": "export_map",
     "metadata": {"map_name": "test"}
   }
   ```
   - Expect: Error signal with "Cannot export map while simulation is running"

4. **Map Import Non-existent**:
   ```json
   {
     "type": "import_map",
     "metadata": {"map_name": "nonexistent"}
   }
   ```
   - Expect: Error signal with "Map file not found"

### 8. Parking Provisioning Test

1. **Create Parking**:
   ```json
   {
     "action": "building.create",
     "params": {
       "building_id": "parking-node42",
       "node_id": 42,
       "capacity": 40
     }
   }
   ```
   - Expect: `{"signal": "building.created", "data": {"node_id": 42, "building": {...}, "tick": <current>}}`

2. **Validate Occupants**:
   - Send another `building.create` with a duplicate `building_id` to confirm the handler rejects duplicates.
   - Optionally run `{"action": "state.request", "params": {}}` and verify the parking entry in `state.full_map_data` (the `current_agents` array should remain empty until trucks park).

---

## Common Testing Scenarios

### Scenario 1: Complete Simulation Cycle
1. Start simulation → Pause → Resume → Stop
2. Verify all state change signals are received
3. Check that tick signals stop when paused

### Scenario 2: Agent Lifecycle
1. Add agent → Modify agent → Delete agent
2. Verify agent_update signals for each change
3. Check that deleted agents no longer appear in updates

### Scenario 3: Multiple Clients
1. Open multiple Postman WebSocket connections
2. Send actions from different clients
3. Verify all clients receive the same signals

### Scenario 4: High-Frequency Updates
1. Start simulation with high tick rate (60Hz)
2. Monitor signal frequency and performance
3. Verify no signal loss or delays

### 5. State Snapshot Test

1. **Request State Snapshot**:
   ```json
   {"type": "request_state"}
   ```
   - Expect: `{"type": "action_ack", "action_type": "request_state", "status": "received"}`
   - Expect: `{"signal": "state.snapshot_start", "data": {}}`
   - Expect: `{"signal": "state.full_map_data", "data": {...}}`
   - Expect: Multiple `{"signal": "state.full_agent_data", "data": {...}}` signals (one per agent)
   - Expect: `{"signal": "state.snapshot_end", "data": {}}`

2. **Test Client Connection During Simulation**:
   - Start simulation: `{"type": "start", "tick_rate": 20}`
   - Open new WebSocket connection
   - Should automatically receive state snapshot (if simulation is running)
   - Verify complete state is received before regular tick signals

3. **Test State Snapshot on Simulation Start**:
   - Connect to WebSocket
   - Send: `{"type": "start", "tick_rate": 20}`
   - Should receive state snapshot immediately after simulation_started signal

---

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Check if server is running: `curl http://localhost:8000/health`
   - Verify port 8000 is not blocked

2. **No Signals Received**:
   - Check if simulation is running
   - Verify WebSocket connection is active
   - Check server logs for errors

3. **Invalid JSON Errors**:
   - Validate JSON syntax
   - Check required fields are present
   - Verify data types match specifications

4. **Agent Not Found Errors**:
   - Verify agent ID exists
   - Check agent was successfully added
   - Ensure agent hasn't been deleted

### Debug Tips

1. **Enable Logging**: Check server logs for detailed error messages
2. **Test Health Endpoint**: Verify server is responding
3. **Validate JSON**: Use JSON validator for message format
4. **Check Network**: Ensure WebSocket connection is stable
