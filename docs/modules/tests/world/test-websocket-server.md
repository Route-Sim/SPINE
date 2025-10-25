---
title: "Tests: WebSocket Server"
summary: "Test suite for the FastAPI WebSocket server including connection management, action handling, signal broadcasting, and endpoint behavior."
source_paths:
  - "tests/world/test_websocket_server.py"
last_updated: "2025-10-25"
owner: "Mateusz Polis"
tags: ["test", "sim", "api"]
links:
  parent: "../../SUMMARY.md"
  siblings: ["test-sim-runner.md"]
---

# Tests: WebSocket Server

> **Purpose:** Validate `WebSocketServer` control plane: client connect/disconnect, message routing to `ActionQueue`, signal broadcast loop lifecycle, and REST-like health endpoint.

## Context & Motivation
- Ensure correctness of client interactions and server-side broadcasting.
- Validate robustness under task cancellation and loop attachment edge cases.

## Coverage
- `ConnectionManager`: connect, disconnect, personal messages, broadcast.
- Message parsing and validation: valid actions, invalid JSON/commands.
- Signal broadcasting: start/stop, cancellation handling, idempotent start.
- Endpoints: `/ws` handshake behavior, `/health` response contract.

## Notes
- Minor style fix applied to use `contextlib.suppress(Exception)` in endpoint test.

## References
- `modules/world/io/websocket_server.md`
