---
title: "Broker Agent"
summary: "Singleton agent that negotiates package pickups with trucks and manages company finances for delivery operations."
source_paths:
  - "agents/broker.py"
last_updated: "2025-12-10"
owner: "Mateusz Polis"
tags: ["module", "agent", "negotiation", "finance"]
links:
  parent: "../../SUMMARY.md"
  siblings:
    - "./transports/truck.md"
---

# Broker Agent

> **Purpose:** The Broker agent acts as a central coordinator for package delivery negotiations. It receives information about new packages, proposes pickup jobs to trucks, tracks negotiations, and manages the company's financial balance.

## Context & Motivation

In a multi-truck logistics simulation, packages spawn at various sites and need to be picked up and delivered. Without coordination, trucks would either:
- Compete for the same packages
- Leave packages stranded
- Make suboptimal routing decisions

The Broker solves this by:
- Maintaining a queue of packages awaiting assignment
- Negotiating with trucks one package at a time to prevent race conditions
- Tracking financial outcomes (delivery payments, late penalties, expiry fines)

## Responsibilities & Boundaries

### In-scope
- Detecting new packages in the world
- Proposing pickups to suitable trucks
- Processing accept/reject responses
- Tracking package assignments
- Managing company balance (payments, fines)

### Out-of-scope
- Route planning (handled by trucks)
- Package spawning (handled by sites)
- Physical delivery execution (handled by trucks)

## Architecture & Design

### Key Data Structure

```python
@dataclass
class Broker:
    id: AgentID
    kind: str = "broker"
    inbox: list[Msg]
    outbox: list[Msg]

    # Financial state
    balance_ducats: float = 10000.0

    # Negotiation state
    package_queue: list[PackageID]  # FIFO queue
    active_negotiation: NegotiationState | None  # Only ONE at a time
    assigned_packages: dict[PackageID, AgentID]
    known_packages: set[PackageID]
```

### Negotiation State Machine

```
Package Spawned → Added to Queue → Start Negotiation
                                        ↓
                               Send Proposal to Truck
                                        ↓
                            ┌─── Wait for Response ───┐
                            ↓                         ↓
                        Accepted                  Rejected
                            ↓                         ↓
                    Finalize Assignment      Try Next Truck
                            ↓                         ↓
                      Send Confirmation      (or return to queue)
```

### Key Constraint: One Negotiation at a Time

To prevent race conditions where a truck accepts multiple packages based on stale state, the broker only negotiates ONE package per tick:

1. Pop package from queue
2. Send proposal to best candidate truck
3. Wait for response
4. Either assign or try next truck
5. Only then start next negotiation

## Message Protocol

| Message Type | Direction | Fields |
|-------------|-----------|--------|
| `proposal` | Broker → Truck | package_id, origin_site_id, destination_site_id, size, deadlines |
| `accept` | Truck → Broker | package_id, estimated_pickup_tick, estimated_delivery_tick |
| `reject` | Truck → Broker | package_id, rejection_reason |
| `assignment_confirmed` | Broker → Truck | package_id, site details |
| `pickup_confirmed` | Truck → Broker | package_id |
| `delivery_confirmed` | Truck → Broker | package_id, delivery_tick, on_time |

## Financial Flow

| Event | Balance Change |
|-------|---------------|
| Package delivered on time | `+ package.value_currency` |
| Package delivered late | `+ value - (0.1% × ticks_late × value)` |
| Pickup deadline expired | `- 50% × package.value_currency` |

## Public API

### Construction

```python
broker = Broker(
    id=AgentID("broker-1"),
    kind="broker",
    balance_ducats=10000.0,
)
```

### Agent Interface

```python
broker.perceive(world)  # Scan for new packages
broker.decide(world)    # Process negotiations
broker.serialize_full() # Get complete state
```

## Implementation Notes

- Perception uses guard clauses to enqueue each `WAITING_PICKUP` package exactly once, avoiding duplicate negotiations across ticks while still tracking newly discovered packages in `known_packages`.

## References

- `agents/transports/truck.py` - Truck negotiation interface
- `core/messages.py` - Message format
- `core/packages/package.py` - Package data structure
