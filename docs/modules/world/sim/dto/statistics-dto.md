---
title: "Statistics DTOs"
summary: "Data Transfer Objects for simulation performance statistics collection, enabling type-safe storage and analysis of timing data."
source_paths:
  - "world/sim/dto/statistics_dto.py"
last_updated: "2025-01-27"
owner: "Mateusz Polis"
tags: ["module", "dto", "sim", "performance"]
links:
  parent: "../../../../SUMMARY.md"
  siblings: ["simulation-dto.md", "agent-dto.md", "truck-dto.md"]
---

# Statistics DTOs

> **Purpose:** Provides validated, typed data transfer objects for collecting and storing simulation performance statistics. Enables analysis of simulation timing, tick rate maintenance, and performance bottlenecks.

## Context & Motivation

Performance monitoring is essential for understanding simulation behavior and identifying bottlenecks. The statistics DTOs provide:

- Type-safe storage of timing measurements per tick
- Batched collection for efficient file I/O
- Structured data format for analysis tools
- Maintainable extension points for additional metrics

## Responsibilities & Boundaries

### In-scope
- Single tick statistics (action processing time, simulation step time, total time)
- Batch aggregation of tick statistics
- Type validation and serialization
- Dictionary conversion for JSON storage

### Out-of-scope
- Statistics collection logic (handled by `SimulationController`)
- File I/O operations (handled by background writer thread)
- Analysis and visualization (external tools)

## Architecture & Design

### Class Structure

```python
class TickStatisticsDTO(BaseModel):
    tick: int
    action_time_ms: float
    step_time_ms: float
    total_time_ms: float
    target_tick_rate: float
    achieved_rate: float

class StatisticsBatchDTO(BaseModel):
    batch_id: int
    timestamp: float
    ticks: list[TickStatisticsDTO]
```

### Key Fields

**TickStatisticsDTO**:
- `tick`: Tick number (0-based)
- `action_time_ms`: Time spent processing actions in milliseconds
- `step_time_ms`: Time spent running simulation step in milliseconds
- `total_time_ms`: Total processing time (action + step) in milliseconds
- `target_tick_rate`: Target ticks per second
- `achieved_rate`: Actual achieved rate calculated as `1000.0 / total_time_ms`

**StatisticsBatchDTO**:
- `batch_id`: Unique batch identifier (incremental)
- `timestamp`: Batch creation timestamp (Unix timestamp)
- `ticks`: List of tick statistics (default: 1000 ticks per batch)

### Data Flow

```
SimulationController._run()
    ↓
Timing measurements (perf_counter)
    ↓
TickStatisticsDTO creation
    ↓
Batch accumulation (1000 ticks)
    ↓
StatisticsBatchDTO creation
    ↓
Background writer thread
    ↓
JSON file (stats/stats_batch_*.json)
```

## Algorithms & Complexity

- **TickStatisticsDTO creation**: O(1) - simple field assignment
- **StatisticsBatchDTO creation**: O(n) where n = number of ticks in batch
- **to_dict()**: O(n) for batch, O(1) for single tick
- **Serialization**: O(n) where n = batch size

## Public API / Usage

### Creating Tick Statistics

```python
from world.sim.dto.statistics_dto import TickStatisticsDTO

tick_stats = TickStatisticsDTO(
    tick=1000,
    action_time_ms=2.5,
    step_time_ms=45.3,
    total_time_ms=47.8,
    target_tick_rate=20.0,
    achieved_rate=20.92  # 1000.0 / 47.8
)
```

### Creating Statistics Batch

```python
from world.sim.dto.statistics_dto import StatisticsBatchDTO, TickStatisticsDTO
import time

ticks = [
    TickStatisticsDTO(tick=i, action_time_ms=2.0, step_time_ms=40.0,
                     total_time_ms=42.0, target_tick_rate=20.0, achieved_rate=23.81)
    for i in range(1000)
]

batch = StatisticsBatchDTO(
    batch_id=1,
    timestamp=time.time(),
    ticks=ticks
)
```

### Converting to Dictionary

```python
# Single tick
tick_dict = tick_stats.to_dict()
# {"tick": 1000, "action_time_ms": 2.5, "step_time_ms": 45.3, ...}

# Batch
batch_dict = batch.to_dict()
# {"batch_id": 1, "timestamp": 1234567890.0, "ticks": [...]}
```

## Implementation Notes

### Design Trade-offs

1. **Batching**: Statistics are batched (default 1000 ticks) to:
   - Reduce file I/O overhead
   - Enable efficient background writing
   - Maintain reasonable file sizes

2. **Milliseconds**: All time values stored in milliseconds for:
   - Human-readable precision
   - Consistent units across all metrics
   - Easy conversion to seconds (divide by 1000)

3. **Achieved Rate Calculation**: Calculated as `1000.0 / total_time_ms` to:
   - Show actual performance vs target
   - Enable easy comparison with target tick rate
   - Identify when tick rate cannot be maintained

### Third-party Libraries

- **pydantic**: Runtime type validation and serialization

## Tests

Test coverage should include:
- DTO creation with valid data
- Field validation (non-negative values, etc.)
- to_dict() serialization
- Batch aggregation
- Edge cases (zero times, very high times)

## Performance

- DTO creation: < 1μs per tick
- Batch creation: ~1ms per 1000 ticks
- Serialization: ~5ms per 1000-tick batch
- Memory usage: ~50KB per 1000-tick batch

## Security & Reliability

### Validation
- All time values must be non-negative
- Tick numbers must be non-negative
- Target tick rate must be positive
- Achieved rate must be non-negative

### Error Handling
- Pydantic validation ensures data integrity
- Type safety prevents runtime errors
- Clear field constraints prevent invalid data

## File Format

Statistics are written to JSON files with the following structure:

```json
{
  "batch_id": 1,
  "timestamp": 1234567890.0,
  "ticks": [
    {
      "tick": 0,
      "action_time_ms": 2.5,
      "step_time_ms": 45.3,
      "total_time_ms": 47.8,
      "target_tick_rate": 20.0,
      "achieved_rate": 20.92
    },
    ...
  ]
}
```

Files are named: `stats_batch_{batch_id:06d}_{timestamp}.json`

## References

- **Related modules**:
  - `world.sim.controller` - Statistics collection
  - `world.sim.state` - Target tick rate source
- **ADRs**: N/A
- **API Reference**: Statistics are internal, not exposed via WebSocket API
