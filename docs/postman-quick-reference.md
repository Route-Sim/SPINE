# Postman Quick Reference

> **Quick reference for testing the SPINE WebSocket API with Postman.**

## Connection Setup

### WebSocket Connection
- **URL**: `ws://localhost:8000/ws`
- **Method**: WebSocket
- **Status**: Should show "Connected"

### Health Check
- **URL**: `http://localhost:8000/health`
- **Method**: GET
- **Expected**: `{"status": "healthy", "service": "spine-websocket"}`

---

## Quick Test Messages

### 1. Start Simulation
```json
{"type": "start", "tick_rate": 30}
```

### 2. Pause Simulation
```json
{"type": "pause"}
```

### 3. Resume Simulation
```json
{"type": "resume"}
```

### 4. Stop Simulation
```json
{"type": "stop"}
```

### 5. Add Transport Agent
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

### 6. Add Building Agent
```json
{
  "type": "add_agent",
  "agent_id": "warehouse1",
  "agent_kind": "building",
  "agent_data": {
    "capacity": 10000,
    "processing_rate": 100,
    "location": "downtown"
  }
}
```

### 7. Modify Agent
```json
{
  "type": "modify_agent",
  "agent_id": "truck1",
  "agent_data": {
    "speed": 75,
    "status": "active",
    "cargo": "electronics"
  }
}
```

### 8. Delete Agent
```json
{
  "type": "delete_agent",
  "agent_id": "truck1"
}
```

### 9. Change Tick Rate
```json
{
  "type": "set_tick_rate",
  "tick_rate": 60
}
```

---

## Expected Responses

### Action Acknowledgments
```json
{
  "type": "action_ack",
  "action_type": "start",
  "status": "received"
}
```

### Simulation State Signals
```json
{"type": "simulation_started"}
{"type": "simulation_stopped"}
{"type": "simulation_paused"}
{"type": "simulation_resumed"}
```

### Tick Signals
```json
{"type": "tick_start", "tick": 123}
{"type": "tick_end", "tick": 123}
```

### Agent Updates
```json
{
  "type": "agent_update",
  "agent_id": "truck1",
  "data": {
    "id": "truck1",
    "kind": "transport",
    "tags": {"position": {"x": 100, "y": 200}}
  },
  "tick": 123
}
```

### Error Signals
```json
{
  "type": "error",
  "error_message": "Agent not found",
  "tick": 123
}
```

---

## Testing Workflow

### 1. Basic Test
1. Connect to WebSocket
2. Send: `{"type": "start", "tick_rate": 30}`
3. Observe: `simulation_started` signal
4. Observe: `tick_start` and `tick_end` signals every ~33ms
5. Send: `{"type": "stop"}`
6. Observe: `simulation_stopped` signal

### 2. Agent Test
1. Start simulation
2. Add agent with the transport example above
3. Observe: `agent_update` signal
4. Modify agent with the modify example above
5. Observe: `agent_update` signal
6. Delete agent
7. Observe: Agent removed from updates

### 3. Multi-Client Test
1. Open multiple Postman WebSocket connections
2. Send actions from different clients
3. Verify all clients receive the same signals

---

## Common Issues

### Connection Issues
- **"Connection Refused"**: Server not running
- **"WebSocket Error"**: Check URL format
- **"No Response"**: Check server logs

### Message Issues
- **"Invalid JSON"**: Check JSON syntax
- **"Validation Error"**: Check required fields
- **"Agent Not Found"**: Verify agent exists

### Performance Issues
- **Slow Responses**: Check server performance
- **Missing Signals**: Check simulation state
- **High CPU**: Reduce tick rate

---

## Debug Commands

### Check Server Status
```bash
curl http://localhost:8000/health
```

### Check Server Logs
```bash
# Look for error messages in terminal where server is running
```

### Test JSON Validity
```bash
echo '{"type": "start", "tick_rate": 30}' | python -m json.tool
```

---

## Performance Tips

### Optimal Settings
- **Tick Rate**: 20-30 Hz for testing
- **Message Size**: Keep agent_data small
- **Connection Count**: Test with 1-5 clients

### Monitoring
- **Signal Frequency**: Should match tick rate
- **Response Time**: < 10ms for actions
- **Memory Usage**: Monitor server resources

---

## Advanced Testing

### Stress Test
1. Start simulation with 60Hz tick rate
2. Add 100 agents rapidly
3. Monitor signal frequency and server performance
4. Check for signal loss or delays

### Error Test
1. Send invalid JSON: `{"invalid": "message"}`
2. Send missing fields: `{"type": "add_agent"}`
3. Send invalid agent ID: `{"type": "delete_agent", "agent_id": "nonexistent"}`
4. Verify error signals are received

### State Test
1. Start → Pause → Resume → Stop
2. Verify state transitions are correct
3. Check that tick signals stop when paused
4. Verify agents continue updating when resumed
