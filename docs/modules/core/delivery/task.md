---
title: "Delivery Task"
summary: "Data structure representing pickup and delivery tasks in a truck's delivery queue."
source_paths:
  - "core/delivery/task.py"
last_updated: "2025-01-10"
owner: "Mateusz Polis"
tags: ["module", "data-structure", "delivery"]
links:
  parent: "../../../SUMMARY.md"
  siblings:
    - "../../agents/transports/truck.md"
    - "../../agents/broker.md"
---

# Delivery Task

> **Purpose:** The DeliveryTask dataclass represents a single stop in a truck's delivery queue, either for picking up packages or delivering them to a destination site.

## Context & Motivation

When trucks receive package assignments from the broker, they need to:
1. Visit the origin site to pick up packages
2. Visit the destination site to deliver packages

A `DeliveryTask` encapsulates this information, allowing trucks to maintain an ordered queue of sites to visit.

## Data Structure

```python
@dataclass
class DeliveryTask:
    site_id: SiteID                           # Where to go
    task_type: TaskType                       # PICKUP or DELIVERY
    package_ids: list[PackageID]              # Packages involved
    estimated_arrival_tick: int = 0           # ETA
    status: TaskStatus = TaskStatus.PENDING   # PENDING/IN_PROGRESS/COMPLETED
```

## Task Types

| Type | Description |
|------|-------------|
| `PICKUP` | Truck loads packages from this site |
| `DELIVERY` | Truck unloads packages at this site |

## Task Status Lifecycle

```
PENDING → IN_PROGRESS → COMPLETED
```

- **PENDING**: Task is queued but not yet started
- **IN_PROGRESS**: Truck is at the site, loading/unloading
- **COMPLETED**: All packages loaded/unloaded, task finished

## Task Consolidation

Multiple packages to the same site are consolidated into a single task:

```python
# Truck receives assignment for pkg-1 (site A → site B)
# Truck receives assignment for pkg-2 (site A → site C)

# Delivery queue:
# 1. PICKUP at site A: [pkg-1, pkg-2]  ← consolidated
# 2. DELIVERY at site B: [pkg-1]
# 3. DELIVERY at site C: [pkg-2]
```

## Serialization

```python
task.to_dict()  # → {"site_id": "...", "task_type": "PICKUP", ...}
DeliveryTask.from_dict(data)  # Reconstruct from dict
```

## References

- `core/types.py` - TaskType, TaskStatus enums
- `agents/transports/truck.py` - Uses delivery_queue
- `agents/broker.py` - Creates tasks via assignment
