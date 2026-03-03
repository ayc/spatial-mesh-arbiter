# Implementation Blueprint & Mandates

This document serves as the high-level technical mandate for implementing the Spatial Mesh Arbiter. It defines crate selection and the roadmap.

**ALL implementing agents MUST adhere to the constraints defined in this document.**

## 1. Technical Stack & Crate Mandates

To ensure cross-CPU determinism and high-performance networking, engineers must use the following approved crates:

### 1.1 Core Simulation & Math
*   **Fixed-Point Math:** `fixed` (using `I32F32`). Floating point (`f32/f64`) is **strictly forbidden** in the simulation loop.
*   **Spatial Indexing:** `rstar` (for the R-Tree implementation).
*   **Collections:** `hashbrown` (for high-performance hashing) and `arrayvec` (for stack-allocated arrays in 60Hz loops).

### 1.2 Networking & Serialization
*   **Async Runtime:** `tokio` (Multi-threaded for the Controller/Edge, Single-threaded runtime for the Arbiter to preserve lock-free invariants).
*   **Serialization:** `bincode`. High-speed binary serialization for all network payloads.
*   **Meta Services Event Bus:** **Redis Streams** (using the `fred` or `redis-rs` crate). Provides durable, at-least-once delivery for asynchronous Hard-State events.
*   **Transport Layer (Strictly Segmented):** 
    *   **External Edge (Client <-> Edge Node):** `tokio-tungstenite` (WebSockets). `TCP_NODELAY=true` must be set.
    *   **Edge Node <-> Arbiter:** `renet`. (Unreliable for movement, Reliable for proposals).
    *   **Internal Mesh (Arbiter <-> Arbiter):** `renet`. Raw UDP within the VPC. (Unreliable for Ghosts, ReliableUnordered for Impacts/Handoffs).
    *   **Control Plane (Controller <-> Arbiters):** `tokio::net::TcpStream` (using `tokio-util::codec`).
*   **Asset Distribution:** HTTP downloads via `reqwest` in a background thread, pushed to the 60Hz loop via a lock-free channel (`crossbeam-channel` or `tokio::sync::mpsc`).

## 2. Implementation Phases (The Roadmap)

### Phase 1: The Foundation (`shared-types`)
*   Implement `SimFixed` wrappers using the `fixed` crate.
*   Define all `ActionPayload` and `CombatContext` enums.
*   Implement the `CollisionGeometry` math (Circle, Cone, Box).

### Phase 2: The Control Plane (`mesh-controller`)
*   Implement the TCP registration server.
*   Implement basic R-Tree subdivision logic.
*   Implement the "Metronome" (Global Tick Synchronization) heartbeat.

### Phase 3: The Physics Runner (`spatial-arbiter`)
*   Implement the 60Hz non-blocking loop.
*   Implement the **Idempotency Ledger** (Ring Buffer).
*   Implement basic movement and collision resolution.

### Phase 4: The Edge Node (`edge-node`)
*   Implement raw client input capture over WebSocket.
*   Implement semantic translation (turning "Click" into "ActionProposal").
*   Implement downstream state interpolation.

### Phase 5: The Headless Swarm Tester (`swarm-tester`)
*   Implement a headless multi-client simulation.
*   Implement a **Boids Flocking Algorithm**.
*   Implement periodic combat spam.

## 3. Agent Constraints (The "Never" List)
1.  **NEVER** use `f32` or `f64` for any coordinate or combat math.
2.  **NEVER** use `std::sync::Mutex` or `RwLock` inside the Arbiter's 60Hz loop. 
3.  **NEVER** assume a global database is available. Use Redis Streams.
4.  **NEVER** perform blocking I/O inside the Arbiter's 60Hz physics loop. 
5.  **NEVER** consume a durable resource in Meta without writing a `PendingTransaction` record in the same database transaction.
6.  **NEVER** attempt WAL-based recovery for a crashed Arbiter. Arbiter crashes are total-loss events recovered via the Spawn Handshake.
