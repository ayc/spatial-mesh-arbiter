# Developer Lifecycle (Rust + Docker)

This document defines the day-to-day development lifecycle for engineers working on Spatial Mesh Arbiter.

Canonical scope:
- Developer workflow and execution sequence are defined here.
- Scenario-level conformance and failure drills remain canonical in [01. Mini-Mesh Conformance & Failure Testing](01-mini-mesh-conformance-and-failure-testing.md).

---

## 1. Goals

The lifecycle is designed to:
- keep local feedback loops fast,
- ensure containerized integration behavior matches architectural contracts,
- catch deterministic/runtime regressions before merge.

---

## 2. Prerequisites

1. Rust toolchain installed (`rustup`, stable toolchain).
2. Docker/OrbStack available for local containerized stack.
3. Workspace scaffold aligned with [Implementation Blueprint](../1-architecture-and-engine/00-implementation-blueprint.md).

Optional but recommended developer tools:
- `cargo-watch` for auto-restart loops.
- `bacon` for continuous check/test feedback.
- `watchexec` as an alternative process restarter.

---

## 3. Standard Development Flow

### Stage A: Understand Contracts

Before implementing a feature, review relevant canonical docs:
1. [Core Architecture](../1-architecture-and-engine/01-core-architecture.md)
2. [Network Interfaces](../1-architecture-and-engine/02-network-interfaces.md)
3. [Client <-> Edge Message Contract](../1-architecture-and-engine/03-client-edge-message-contract.md)
4. NPC-specific work: [NPC Runtime and Replication Contract](../1-architecture-and-engine/04-npc-runtime-and-replication-contract.md) and [NPC and In-World Interaction Design](../2-gameplay-and-design/05-npc-and-world-interaction-design.md)

### Stage B: Fast Local Rust Loop

Run compile/check/test quickly before bringing up the full stack:
1. `cargo check --workspace`
2. `cargo test --workspace`
3. `cargo clippy --workspace --all-targets -- -D warnings` (if enabled for your branch/pipeline)

For service-focused iteration:
- `cargo run -p edge-node`
- `cargo run -p spatial-arbiter`
- `cargo run -p mesh-controller`

### Stage C: Auto-Restart ("Hot Reload Style") Workflow

Rust does not provide built-in in-process hot swap for this stack. Preferred workflow is recompile + restart:
- `cargo watch -x 'run -p edge-node'`
- `cargo watch -x 'run -p spatial-arbiter'`
- `cargo watch -x 'run -p mesh-controller'`

Alternative:
- `watchexec --restart -- cargo run -p edge-node`

Use `bacon` for continuous diagnostics:
- `bacon check`
- `bacon test`

### Stage D: Containerized Integration Loop

Use Docker Compose stack (as defined by project scaffolding) for integration-level behavior:
1. Build services in release or dev profile as configured.
2. Start stack with Compose.
3. Verify service registration/topology wiring.
4. Drive load/traffic via `swarm-tester`.

Containerized integration is required before merge for networking/runtime changes.

### Stage E: Conformance + Failure Drills

Run relevant scenarios from [01. Mini-Mesh Conformance & Failure Testing](01-mini-mesh-conformance-and-failure-testing.md):
- split/handoff/ghost paths,
- epoch/topology handling,
- crash and recovery (`docker kill`) paths,
- NPC cadence/budget/contention paths.

### Stage F: Pre-Merge Readiness

A change is ready when:
1. Local Rust checks/tests pass.
2. Integration stack behavior matches expected contracts.
3. Relevant conformance scenarios pass.
4. At least one failure-path scenario passes for modified runtime paths.
5. Observability/log traces are deterministic under retry/replay.

---

## 4. Lifecycle Gates (Required)

- `Gate 1: Contract Alignment`  
  Feature scope mapped to canonical docs before coding.

- `Gate 2: Fast Loop Health`  
  Workspace checks/tests green in local Rust loop.

- `Gate 3: Integration Health`  
  Containerized stack boots and routes traffic correctly.

- `Gate 4: Conformance`  
  Relevant mini-mesh scenarios pass.

- `Gate 5: Failure Resilience`  
  Crash/reconnect or equivalent failure-path scenario passes.

---

## 5. Recommended Inner Loop by Change Type

### Protocol or Ingress Changes
1. Update contract docs first.
2. Run single-service auto-restart on `edge-node`.
3. Run integration with swarm traffic.
4. Execute sequence/idempotency/failure scenarios.

### Arbiter Simulation Changes
1. Run fast checks for `spatial-arbiter`.
2. Execute split/merge/ghost and load scenarios.
3. Validate deterministic behavior across retries/replays.

### NPC/Interaction Changes
1. Validate against NPC taxonomy/runtime docs.
2. Execute NPC tier cadence and contention scenarios.
3. Confirm no unintended wire intent/schema changes.

---

## 6. Anti-Patterns to Avoid

1. Skipping containerized integration for networking changes.
2. Treating auto-restart as equivalent to deterministic conformance validation.
3. Merging runtime changes without failure-path drills.
4. Introducing protocol changes without updating canonical docs.

---

## 7. References

- [Implementation Blueprint](../1-architecture-and-engine/00-implementation-blueprint.md)
- [Mini-Mesh Conformance & Failure Testing](01-mini-mesh-conformance-and-failure-testing.md)
- [Client <-> Edge Message Contract](../1-architecture-and-engine/03-client-edge-message-contract.md)
- [NPC Runtime and Replication Contract](../1-architecture-and-engine/04-npc-runtime-and-replication-contract.md)
