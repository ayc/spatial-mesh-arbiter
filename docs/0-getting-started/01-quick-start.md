# Quick Start & Local Development Environment

Welcome to the Spatial Mesh Arbiter project. This document outlines the prerequisites and the day-to-day development lifecycle for engineers working on the engine.

## 1. Prerequisites

1.  **Rust Toolchain:** Installed via `rustup` (stable toolchain).
2.  **Docker/OrbStack:** Available for the local containerized stack. OrbStack is recommended for Apple Silicon (arm64) performance.
3.  **Optional Developer Tools:** 
    *   `cargo-watch` or `watchexec` for auto-restart loops.
    *   `bacon` for continuous check/test feedback.

## 2. Project Scaffolding (The Workspace)

The project is structured as a single **Cargo Workspace** to ensure unified dependency management and shared types.

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
└── docs/                     # Documentation
```

## 3. Standard Development Flow

### Stage A: Fast Local Rust Loop
Run compile/check/test quickly before bringing up the full stack:
1. `cargo check --workspace`
2. `cargo test --workspace`
3. `cargo clippy --workspace --all-targets -- -D warnings`

### Stage B: Auto-Restart Workflow
Rust does not provide built-in in-process hot swap for this stack. The preferred workflow is recompile + restart using `cargo watch`:
*   `cargo watch -x 'run -p edge-node'`
*   `cargo watch -x 'run -p spatial-arbiter'`
*   `cargo watch -x 'run -p mesh-controller'`

### Stage C: Containerized Integration (Mesh in a Box)
Use the Docker Compose stack for integration-level behavior, especially networking and R-Tree behavior.
1. Include `redpandadata/redpanda` in the Docker Compose stack for the Event Bus, and `redis:alpine` for the Session Manager registry.
2. Include `nginx:alpine` to act as a local CDN for game assets.
3. Use Docker Compose replicas for the `spatial-arbiter`.
4. Nodes register with the Controller using their **hostname** (e.g., `arbiter-1`), not their internal IP via DNS discovery.

**Warm Pool Lifecycle in Docker:**
*   Arbiters boot in an `IDLE` state and register with the Controller.
*   Controller assigns spatial boundaries via `UpdateTopology`.
*   Arbiters only begin the 60Hz physics loop once `Allocated`.

### Stage D: Conformance + Failure Drills
Before merging networking or runtime changes, you must run relevant scenarios from the [Mini-Mesh Conformance & Failure Testing](../5-testing-and-conformance/01-mini-mesh-conformance.md) document to catch deterministic/runtime regressions.
