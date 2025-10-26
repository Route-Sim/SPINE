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

## Signals (Backend → Frontend)

Signals are updates sent from the Backend to inform the Frontend about simulation state changes.

### 1. TICK_START - Simulation Tick Started

**Purpose**: Indicates the start of a simulation tick.

**Signal Type**: `tick_start`

**JSON Example**:
```json
{
  "type": "tick_start",
  "tick": 123
}
```

**Fields**:
- `tick`: Current simulation tick number

**When Received**: At the beginning of each simulation step

---

### 2. TICK_END - Simulation Tick Ended

**Purpose**: Indicates the end of a simulation tick.

**Signal Type**: `tick_end`

**JSON Example**:
```json
{
  "type": "tick_end",
  "tick": 123
}
```

**Fields**:
- `tick`: Current simulation tick number

**When Received**: At the end of each simulation step

---

### 3. AGENT_UPDATE - Agent State Changed

**Purpose**: Notifies about changes in agent state.

**Signal Type**: `agent_update`

**JSON Example**:
```json
{
  "type": "agent_update",
  "agent_id": "truck1",
  "data": {
    "id": "truck1",
    "kind": "transport",
    "tags": {
      "position": {"x": 100, "y": 200},
      "status": "moving",
      "cargo": "electronics"
    },
    "inbox_count": 0,
    "outbox_count": 1
  },
  "tick": 123
}
```

**Fields**:
- `agent_id`: ID of the changed agent
- `data`: New agent state
- `tick`: Simulation tick when change occurred

**When Received**: When an agent's state changes

---

### 4. WORLD_EVENT - Simulation Event

**Purpose**: Reports general simulation events.

**Signal Type**: `world_event`

**JSON Example**:
```json
{
  "type": "world_event",
  "data": {
    "event_type": "agent_added",
    "agent_id": "truck1",
    "agent_kind": "transport",
    "timestamp": 1640995200
  },
  "tick": 123
}
```

**Fields**:
- `data`: Event details
- `tick`: Simulation tick when event occurred

**When Received**: When simulation events occur

---

### 5. ERROR - Error Notification

**Purpose**: Reports errors that occurred in the simulation.

**Signal Type**: `error`

**JSON Example**:
```json
{
  "type": "error",
  "error_message": "Agent truck1 not found",
  "tick": 123
}
```

**Fields**:
- `error_message`: Description of the error
- `tick`: Simulation tick when error occurred

**When Received**: When errors occur in the simulation

---

### 6. SIMULATION_STARTED - Simulation Started

**Purpose**: Confirms that the simulation has started.

**Signal Type**: `simulation_started`

**JSON Example**:
```json
{
  "type": "simulation_started"
}
```

**Fields**: None

**When Received**: After successful start action

---

### 7. SIMULATION_STOPPED - Simulation Stopped

**Purpose**: Confirms that the simulation has stopped.

**Signal Type**: `simulation_stopped`

**JSON Example**:
```json
{
  "type": "simulation_stopped"
}
```

**Fields**: None

**When Received**: After successful stop action

---

### 8. SIMULATION_PAUSED - Simulation Paused

**Purpose**: Confirms that the simulation has been paused.

**Signal Type**: `simulation_paused`

**JSON Example**:
```json
{
  "type": "simulation_paused"
}
```

**Fields**: None

**When Received**: After successful pause action

---

### 9. SIMULATION_RESUMED - Simulation Resumed

**Purpose**: Confirms that the simulation has been resumed.

**Signal Type**: `simulation_resumed`

**JSON Example**:
```json
{
  "type": "simulation_resumed"
}
```

**Fields**: None

**When Received**: After successful resume action

---

### 10. MAP_EXPORTED - Map Export Confirmation

**Purpose**: Confirms that a map was successfully exported.

**Signal Type**: `map_exported`

**JSON Example**:
```json
{
  "type": "map_exported",
  "data": {
    "map_name": "my_custom_map"
  }
}
```

**Fields**:
- `data`: Map information
  - `map_name`: Name of the exported map

**When Received**: After successful map export

---

### 11. MAP_IMPORTED - Map Import Confirmation

**Purpose**: Confirms that a map was successfully imported.

**Signal Type**: `map_imported`

**JSON Example**:
```json
{
  "type": "map_imported",
  "data": {
    "map_name": "my_custom_map"
  }
}
```

**Fields**:
- `data`: Map information
  - `map_name`: Name of the imported map

**When Received**: After successful map import

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
   - Expect: `{"type": "simulation_started"}`

2. **Pause Simulation**:
   ```json
   {"type": "pause"}
   ```
   - Expect: `{"type": "action_ack", "action_type": "pause", "status": "received"}`
   - Expect: `{"type": "simulation_paused"}`

3. **Resume Simulation**:
   ```json
   {"type": "resume"}
   ```
   - Expect: `{"type": "action_ack", "action_type": "resume", "status": "received"}`
   - Expect: `{"type": "simulation_resumed"}`

4. **Stop Simulation**:
   ```json
   {"type": "stop"}
   ```
   - Expect: `{"type": "action_ack", "action_type": "stop", "status": "received"}`
   - Expect: `{"type": "simulation_stopped"}`

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

### 5. Real-time Updates Test

1. **Start Simulation** and observe:
   - `tick_start` signals every ~33ms (30Hz)
   - `tick_end` signals every ~33ms
   - `agent_update` signals when agents change
   - `world_event` signals for simulation events

### 6. Error Handling Test

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
