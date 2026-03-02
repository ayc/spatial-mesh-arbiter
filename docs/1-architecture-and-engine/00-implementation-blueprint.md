# Implementation Blueprint (Agent Instructions)

This document serves as the high-level technical mandate for implementing the Spatial Mesh Arbiter. It defines the project scaffolding, crate selection, and execution environment. 

**ALL implementing agents MUST adhere to the constraints defined in this document.**

---

## 1. Project Scaffolding (The Workspace)

The project is structured as a single **Cargo Workspace** to ensure unified dependency management and shared types.

### Directory Structure
```text
/
├── Cargo.toml                # Workspace definition
├── Dockerfile                # Multi-stage, Apple Silicon optimized
├── docker-compose.yml        # OrbStack-ready "Mesh in a Box"
├── crates/
│   ├── shared-types/         # No-std compatible PODs, Enums, and Math
│   ├── mesh-controller/      # The Control Plane (TCP)
│   ├── spatial-arbiter/      # The Physics Plane (UDP/RUDP)
│   ├── edge-node/            # The Proxy Plane (UDP/Websocket)
│   └── swarm-tester/         # The Headless Load Tester (Boids Algorithm)
└── docs/                     # Documentation (Reorganized)
```

---

## 2. Technical Stack & Crate Mandates

To ensure cross-CPU determinism and high-performance networking, agents must use the following approved crates:

### 2.1 Core Simulation & Math
*   **Fixed-Point Math:** `fixed` (using `I32F32`). Floating point (`f32/f64`) is **strictly forbidden** in the simulation loop.
*   **Spatial Indexing:** `rstar` (for the R-Tree implementation).
*   **Collections:** `hashbrown` (for high-performance hashing) and `arrayvec` (for stack-allocated arrays in 60Hz loops).

### 2.2 Networking & Serialization
*   **Async Runtime:** `tokio` (Multi-threaded for the Controller/Edge, Single-threaded runtime for the Arbiter to preserve lock-free invariants).
*   **Serialization:** `bincode`. High-speed binary serialization for all network payloads.
*   **Meta Services Event Bus:** **Redis Streams** (using the `fred` or `redis-rs` crate). Provides durable, at-least-once delivery for asynchronous Hard-State events (e.g., `PlayerDied`, `LootSpawned`). Uses consumer groups with explicit `XACK` to guarantee that no event is lost if a Meta consumer crashes mid-processing. See the durability contract in [Core Architecture § 9.3](01-core-architecture.md#93-cross-layer-handshake-the-event-bus). The Arbiter and Meta Services interact with the bus through an `EventBus` trait (defined in `shared-types`) to decouple application logic from the transport implementation.
*   **Transport Layer (Strictly Segmented):** 
    *   **External Edge (Client <-> Edge Node):** `tokio-tungstenite` (WebSockets). Prioritizes browser compatibility, easy TLS termination, and bypassing UDP-blocking firewalls. **Crucial:** The AI must set `TCP_NODELAY=true` to prevent Nagle's algorithm from causing input latency.
    *   **Edge Node <-> Arbiter:** `renet`. The Edge Node translates WebSocket TCP frames into high-speed UDP `renet` packets (Unreliable for movement, Reliable for proposals).
    *   **Internal Mesh (Arbiter <-> Arbiter):** `renet`. Uses raw, unencrypted UDP to maximize the 60Hz CPU budget within the trusted VPC. Use `Unreliable` channels for Ghosts/Movement, and `ReliableUnordered` for Impacts/Handoffs.
    *   **Control Plane (Controller <-> Arbiters):** `tokio::net::TcpStream` (using `tokio-util::codec` for length-prefixed framing). Used for low-frequency, highly reliable topology commands.
*   **Asset Distribution (Hot-Patching):** The Mesh Controller signals a new `Data Epoch` by broadcasting a URL (e.g., `http://asset-server/v1.0.bin`). Arbiters must use `reqwest` in a background thread to download and deserialize the asset, then push it to the 60Hz loop via a lock-free channel (e.g., `crossbeam-channel` or `tokio::sync::mpsc`) for atomic activation.

---

## 3. Local Development Environment (OrbStack)

The local stack is managed via `docker-compose` and optimized for **Apple Silicon (arm64)**.

### The "Mesh in a Box" Workflow
1.  **Infrastructure:** Include `redis:alpine` in the Docker Compose stack (serves dual duty as the **Redis Streams Event Bus** for Hard-State events and the **Session Manager** registry). Include a simple `nginx:alpine` container to act as a local CDN for game assets.
2.  **Orchestration:** Use Docker Compose replicas for the `spatial-arbiter`.
3.  **DNS Discovery:** Leverage OrbStack/Docker DNS. Nodes register with the Controller using their **hostname** (e.g., `arbiter-1`), not their internal IP.
4.  **Warm Pool Lifecycle:** 
    *   Arbiters boot in an `IDLE` state and register with the Controller.
    *   Controller assigns spatial boundaries via `UpdateTopology`.
    *   Arbiters only begin the 60Hz physics loop once `Allocated`.

---

## 4. Implementation Phases (The Roadmap)

### Phase 1: The Foundation (`shared-types`)
*   Implement `SimFixed` wrappers using the `fixed` crate.
*   Define all `ActionPayload` and `CombatContext` enums.
*   Implement the `CollisionGeometry` math (Circle, Cone, Box).

### Phase 2: The Control Plane (`mesh-controller`)
*   Implement the TCP registration server.
*   Implement basic R-Tree subdivision logic (splitting a rectangle into two based on entity counts).
*   Implement the "Metronome" (Global Tick Synchronization) heartbeat.

### Phase 3: The Physics Runner (`spatial-arbiter`)
*   Implement the 60Hz non-blocking loop.
*   Implement the **Idempotency Ledger** (Ring Buffer).
*   Implement basic movement and collision resolution.

### Phase 4: The Edge Node (`edge-node`)
*   Implement raw client input capture over WebSocket (Edge ingress).
*   Implement semantic translation (turning "Click" into "ActionProposal").
*   Implement downstream state interpolation.

### Phase 5: The Headless Swarm Tester (`swarm-tester`)
*   Implement a headless multi-client simulation that connects hundreds of WebSocket sessions to the Edge Node.
*   Implement a **Boids Flocking Algorithm** (Separation, Alignment, Cohesion) to drive bot movement. This organically forces the bots to herd together, perfectly stressing the R-Tree `Boundary Sliding` and `Kinematic Dilation` logic.
*   Implement periodic combat spam (e.g., bots randomly casting `SpawnProjectile` at nearby flockmates) to test cross-boundary RUDP packet loss under load.

---

## 5. Agent Constraints (The "Never" List)
1.  **NEVER** use `f32` or `f64` for any coordinate or combat math.
2.  **NEVER** use `std::sync::Mutex` or `RwLock` inside the Arbiter's 60Hz loop. Use the Actor Model patterns defined in the docs.
3.  **NEVER** assume a global database is available. Use the **Redis Streams-backed Meta Services Event Bus** for all asynchronous hard-state transitions.
4.  **NEVER** perform blocking I/O (like Redis Streams writes) inside the Arbiter's 60Hz physics loop. Use an internal non-blocking channel to offload events to an async worker thread.
5.  **NEVER** consume a durable resource (inventory item, currency) in Meta without writing a `PendingTransaction` record in the same database transaction. See [Core Architecture § 9.8](01-core-architecture.md) for the cross-layer transaction ledger pattern.
6.  **NEVER** attempt WAL-based recovery for a crashed Arbiter. Arbiter crashes are total-loss events. Recovery is handled by Meta Services via the Spawn Handshake and transaction reconciliation. See [Core Architecture § 9.7](01-core-architecture.md).
