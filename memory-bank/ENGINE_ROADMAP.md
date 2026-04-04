# Engine Implementation Roadmap

> Build phases aligned to `docs-core/` contracts. Replaces the ARPG-focused phases in `docs/0-getting-started/02-implementation-phases.md` §2.
>
> Crate mandates (§1) and agent constraints (§3) from that document remain in effect.
>
> Last Updated: 2026-04-04

---

## Phase 1: Foundation (`shared-types`)

**Contracts:** `docs-core/00-scope-and-principles.md`, `docs-core/00-1-core-baseline-profile.md`

**Scope:**
- Stage ID enums (PipelineStageId, DispatchStageId, DeferredTargetStageId) — done
- DeferredEvent scheduler types — done
- EntityId type alias — done
- SimFixed wrappers using `fixed` crate (`I32F32`, saturating arithmetic helpers)
- CollisionGeometry primitives (Circle, Cone, Box) with fixed-point math
- Baseline profile constants (tick rate, ingress budgets, replay horizons from `00-1`)

**Status:** In progress. Stage IDs and deferred events complete. SimFixed and geometry not started.

**Acceptance:** All types compile `no_std`. Unit tests cover boundary conditions and deterministic arithmetic.

---

## Phase 2: Spatial Runtime Kernel (`spatial-runtime-kernel`)

**Contracts:** `docs-core/01-spatial-runtime-kernel.md`, `01-1-spatial-primitive-catalog.md`, `01-2-entity-lifecycle-contract.md`, `01-3-entity-relationship-contract.md`, `01-4-dynamic-topology-contract.md`

**Scope:**
- 60Hz non-blocking tick loop
- R-Tree spatial index (using `rstar`)
- Entity ownership and single-authority enforcement
- Entity lifecycle state machine (Active → intermediate phases → Removed)
- Spatial primitive dispatch (14 operations: 8 kinematic mutations, 6 queries)
- Kinematic dilation (dilation_factor calculation and application)
- Idempotency ledger (ring buffer)
- Entity relationship graph (persistent linkage, control authority)
- Ghost entity integration (dead-reckoning, anomaly guards)

**Dependencies:** Phase 1 complete.

**Acceptance:** Single-Arbiter tick loop processes movement proposals deterministically. Dilation activates under configurable entity thresholds. Idempotency ledger rejects duplicates within TTL window.

---

## Phase 3: Spatial Messaging Plane (`spatial-messaging-plane`)

**Contracts:** `docs-core/02-spatial-messaging-plane.md`

**Scope:**
- Envelope contracts (ActionProposal, MeshInternalEvent, ControllerCommand, DownstreamPayload)
- Ghost protocol (UDP dead-reckoning, RUDP keyframe correction)
- Cross-boundary relay (TTL-1, terminal outcome rules)
- Interest management (ring tiers, budget, hysteresis)
- Proximity manifest for P2P visual layer
- Transport bindings: `renet` for Arbiter↔Arbiter, `tokio::net::TcpStream` for Controller↔Arbiter

**Dependencies:** Phase 2 (spatial runtime provides the entity state that messaging operates on).

**Acceptance:** Two-Arbiter mesh with ghost synchronization. Cross-boundary proposals relay and resolve correctly. Interest management filters downstream broadcasts by distance tier.

---

## Phase 4: Durability Bridge (`durability-bridge`)

**Contracts:** `docs-core/03-durability-bridge.md`

**Scope:**
- Hard vs soft state classification
- HardEvent producer (Redpanda via `rdkafka`, idempotent, `acks=all`)
- Consumer-side idempotency (Postgres upsert pattern)
- Retry policy (5-retry exponential backoff)
- Dead-letter topic handling
- Pending transaction / confirmed / refund reconciliation
- Recovery inbox (generic compensation pattern)

**Dependencies:** Phase 3 (messaging plane provides the event transport layer). Redpanda available in dev environment.

**Acceptance:** HardEvents produced by Arbiter are consumed exactly-once by a test Meta consumer. DLQ captures poison pills. Pending transactions reconcile after simulated crash.

---

## Phase 5: Game Adapter Interface (`game-adapter-interface`)

**Contracts:** `docs-core/04-0-game-adapter-interface.md`, `04-1-game-adapter-contract.md`, `04-2-game-adapter-api-contract.md`, `04-3-version-line-transition-contract.md`

**Scope:**
- GameAdapter trait with 4 hooks: validate_intent, dispatch_stage, initialize_spawn_configuration, describe_compatibility
- 12-stage pipeline dispatch (engine calls adapter per stage, adapter returns StageOutcome)
- Request/response envelope structure
- Startup compatibility negotiation
- Version line transition state machine (PREPARE → DRAIN → CUTOVER → STABILIZE → COMMITTED/ROLLED_BACK)

**Dependencies:** Phase 2 (kernel drives the pipeline), Phase 3 (messaging delivers proposals to the pipeline).

**Note:** This is where layer extraction (`docs-core/06-architecture-section-mapping.md`) becomes critical. The adapter trait must cleanly separate engine-owned behavior from game-owned behavior. If extraction hasn't been executed by this point, the trait boundary may be ambiguous.

**Acceptance:** A minimal "echo" adapter passes conformance. The ARPG adapter (from `docs/`) can plug in and resolve a basic combat scenario through all 12 stages.

---

## Phase 6: Conformance Harness (`conformance`)

**Contracts:** `docs-core/05-conformance-invariants.md`, `05-1-conformance-test-matrix.md`, `05-2-core-conformance-scenario-catalog.md`

**Scope:**
- Assertion framework (predicate + timing window + severity)
- Scenario runner for SCN-AUTH-*, SCN-DET-*, SCN-MSG-*, SCN-RT-*, SCN-DUR-* catalogs
- Determinism validation (multi-architecture replay comparison: x86_64 vs arm64)
- CI integration (Docker Compose + conformance-runner binary)
- Gate policy enforcement (PR / NIGHTLY / RELEASE tiers)

**Dependencies:** Phases 2-5 (needs a working engine to test against).

**Acceptance:** Full conformance suite passes on x86_64. Cross-architecture determinism validated for core simulation path.

---

## Phase Dependency Graph

```
Phase 1 (shared-types)
  └─► Phase 2 (spatial-runtime-kernel)
        ├─► Phase 3 (spatial-messaging-plane)
        │     └─► Phase 4 (durability-bridge)
        └─► Phase 5 (game-adapter-interface)
              └─► Phase 6 (conformance)
```
