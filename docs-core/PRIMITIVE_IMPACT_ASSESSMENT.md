# Primitive Taxonomy — docs-core/ Impact Assessment

**Status:** DRAFT — pending team review
**Date:** 2026-03-17
**Origin:** `docs-game-compiler/ability-primitives/` taxonomy (65 primitives, 125 ability sketches)
**Author:** Extracted from cross-referencing the canonical primitive taxonomy engine-layer tags against current docs-core/ contracts

**Scope note:** This is the contract-planning counterpart to `docs-game-compiler/GEMINI_CORE_IMPACT_ASSESSMENT.md`. That document highlights the highest-blast-radius architectural gaps; this document translates the canonical primitive taxonomy into proposed `docs-core/` contract amendments and work order.

---

## 1. Executive Summary

The ability primitive taxonomy (`docs-game-compiler/ability-primitives/`) identifies 65 atomic engine primitives required to support the full design space of 125 ability sketches. Of those 65 primitives, **45 are currently tagged `docs-core/`** and **20 are tagged `game-adapter`**.

**Current docs-core/ covers approximately 0 of these 45 at the primitive-specification level.** The existing contracts are correct and well-structured but operate at a higher abstraction layer (authority, topology, transport, durability, adapter hook surface). They define *that* the engine provides hooks and spatial operations, but not *what specific primitives* exist at those hooks.

This document proposes **5 contract amendments** to close the gap, organized by priority and blast radius.

## 2. Methodology

Each of the 65 primitives is tagged with an engine layer in the canonical taxonomy:
- **`docs-core/`** — Engine must implement and contract this behavior. Game code depends on it.
- **`game-adapter`** — Game adapter implements this in hook callbacks. Engine provides the hook surface.
- **`compiler-only`** — Resolved entirely at compile time. No runtime engine involvement.

We then audited every file in `docs-core/` to determine which primitives are already covered, partially covered, or absent.

Current canonical split:
- **45** primitives tagged `docs-core/`
- **20** primitives tagged `game-adapter`
- **0** primitives currently tagged `compiler-only`

### What docs-core/ covers today

| Document | Covers |
|----------|--------|
| `00-scope-and-principles.md` | Single authority, determinism philosophy |
| `00-1-core-baseline-profile.md` | Quantitative bounds (tick budget, queue caps, numeric scales) |
| `01-spatial-runtime-kernel.md` | Authority, tick contract, topology, numeric semantics. Lists "movement integration and collision primitives" in scope but does not specify them. |
| `02-spatial-messaging-plane.md` | Message classes, idempotency, ordering, fairness, trust boundaries |
| `03-durability-bridge.md` | Hard/soft state, event bus, transaction state machine, reconciliation |
| `04-0 through 04-3` | Game adapter interface, behavior contract, API shapes, version transitions |
| `05-x` | Conformance invariants, test matrix, scenario catalog |
| `06-architecture-section-mapping.md` | Extraction roadmap from `docs/1-architecture/` |

### What it does NOT cover

- Specific spatial query operations (shapes, raycasts, neighbor selection)
- Specific kinematic primitives (teleport, displacement, steering, clamping)
- The combat/damage pipeline structure and its interception points
- Entity lifecycle beyond alive/dead
- Timer infrastructure (pulse, delay, global scheduling beyond metronome)
- Entity relationship management (bindings, attached kinematics, control swap)
- Dynamic spatial topology (instance forking, portals, collision injection)
- Downstream payload control (asymmetric rendering, entity suspension)

## 3. Proposed Amendments

### Amendment A: Spatial Primitive Catalog

**Primitives covered:** P-01 through P-14 (14 primitives)
**Target document:** `01-1-spatial-primitive-catalog.md`
**Priority:** HIGH — blocks all spatial query and movement specifications downstream

**Status: ADOPTED.** Formalized in `01-1-spatial-primitive-catalog.md`. The catalog defines:
- 8 kinematic mutations (P-01 through P-08): input/output types, engine behavior, Ghost policy, cross-boundary behavior, determinism requirements
- 6 spatial queries (P-09 through P-14): input/output types, R-Tree interaction, Ghost inclusion rules, bounded result guarantees
- Normative kinematic resolution sub-order (forced displacement → voluntary → attached → sweeps)
- Per-primitive Ghost inclusion policy (queries include Ghosts for cross-boundary relay; mutations operate on authoritative entities only)
- Baseline profile keys for query radii, buffer depths, geometry limits, and monitored zone caps

**Dependencies:** None.

---

### Amendment B: Adapter Hook Taxonomy Expansion

**Primitives covered:** P-35, P-36, P-39, P-40 (4 primitives) + pipeline structure for P-15, P-18, P-19, P-20, P-22, P-60, P-61
**Target document:** `04-1-game-adapter-contract.md` §2 (Required Adapter Surface) and §3 (Tick Boundary and Call Order)
**Priority:** HIGH — blocks combat pipeline specification
**Concrete proposal:** `docs-game-compiler/03-1-compiler-ir-specification.md` defines 12 canonical pipeline stages and maps all 65 primitives to stages. This is the compiler team's proposed hook taxonomy for engine adoption.

**What exists:** The adapter contract has been upgraded to API v2. The legacy hooks (`resolve_external`, `resolve_internal`) are deprecated. The new surface is:

- `validate_intent` — dedicated hook for Stage 2 (IntentValidation) with reject/accept terminal outcome semantics
- `dispatch_stage` — unified generic hook called once per active stage per tick, covering Stages 1 and 3-12
- `initialize_spawn_configuration` — spawn-configuration initialization hook for P-32 Actor Spawning
- `describe_compatibility` — startup negotiation

The 12-stage pipeline is defined in `04-1-game-adapter-contract.md` §3. The `dispatch_stage` hook contract — including the normative stage type model (`PipelineStageId`, `DispatchStageId`, `DeferredTargetStageId`), `DispatchStageRequest` payload schema, and `StageOutcome` response schema — is defined in `04-2-game-adapter-api-contract.md` §3.5.

**Status: ADOPTED.** The architectural question (named hooks vs generic stage dispatch) is resolved. The remaining work is filling in per-stage context schemas as primitives are implemented.

**Dependencies:** Complements Amendment A (spatial queries are inputs fed into stage contexts).

---

### Amendment C: Entity Lifecycle Extension

**Primitives covered:** P-25 (Multi-Phase Vitals), P-32 (Actor Spawning), P-33 (Entity Dormancy), P-53 (Entity Suspension)
**Target document:** `01-2-entity-lifecycle-contract.md`
**Priority:** MEDIUM — blocks downed-state and stasis mechanics

**Status: ADOPTED.** Formalized in `01-2-entity-lifecycle-contract.md`. The contract defines:
- Multi-phase lifecycle model with adapter-defined phases and engine-tracked `lifecycle_phase` state
- Phase transitions at Stage 10 (`DeathCheck`) via `PhaseTransitionMutation` in `StageOutcome`
- Entity dormancy (R-Tree present, tick evaluation skipped, timers paused, targetability independent)
- Entity suspension (R-Tree removed, fully isolated, bounded duration with automatic un-suspension deadline)
- Actor spawning lifecycle (directive → allocation → `initialize_spawn_configuration` → insertion on next tick)
- Bounded entity counts per Arbiter and per owner
- Interaction matrix (Active/Dormant/Suspended/Removed × R-Tree/Evaluation/Queries/Payloads/Timers)

**Dependencies:** Amendment B (resolved — Stage 10 `DeathCheck` via `dispatch_stage`).

---

### Amendment D: Entity Relationship Contract

**Primitives covered:** P-06 (Attached Kinematics), P-29 (Control Authority Swap), P-30 (Input Multiplexing), P-34 (Persistent Linkage)
**Target document:** `01-3-entity-relationship-contract.md` (P-29, P-30, P-34) and `01-1-spatial-primitive-catalog.md` §3.6 (P-06)
**Priority:** MEDIUM — blocks tether, symbiote, mind control, and multi-entity mechanics

**Status: ADOPTED.** P-06 (Attached Kinematics) formalized in `01-1-spatial-primitive-catalog.md` §3.6. P-29, P-30, and P-34 formalized in `01-3-entity-relationship-contract.md`. The contract defines:
- Persistent bindings (P-34): two-way entity links with type, distance constraint, expiry, cross-boundary state management, and death cleanup protocol
- Control authority swap (P-29): Edge Node input redirection with single-controller constraint, no-chain rule, atomic revert, and cross-boundary relay forwarding
- Input multiplexing (P-30): one-to-many and many-to-one modes with configurable input policies (Mirror, RoleSplit, AdapterRouted), bounded group size, and coordinator model for cross-boundary groups
- All relationships backed by P-34 bindings for unified cleanup semantics
- 3 baseline profile keys for binding limits, cross-boundary binding capacity, and multiplex group size

**Dependencies:** Amendment A (P-06 attached kinematics), Amendment B (Stage 1 routing).

---

### Amendment E: Dynamic Spatial Topology

**Primitives covered:** P-08 (Dynamic Collision Injection), P-52 (Asymmetric Team-Rendering), P-56 (Spatial Instance Forking), P-57 (Polyline Collision Generator), P-58 (Container/Vehicle Logic), P-59 (N-Way Portal Network)
**Target document:** `01-4-dynamic-topology-contract.md` (P-52, P-56, P-57, P-58, P-59) and `01-1-spatial-primitive-catalog.md` §3.8 (P-08)
**Priority:** LOW — blocks terrain walls, pocket arenas, portals, and vehicles.

**Status: ADOPTED.** P-08 formalized in `01-1-spatial-primitive-catalog.md` §3.8. The remaining 5 primitives formalized in `01-4-dynamic-topology-contract.md`. The contract defines:
- Asymmetric team-rendering (P-52): per-entity `TeamVisibility` bitmask checked at Stage 12 engine boundary, Ghost-replicated, independent from targetability
- Spatial instance forking (P-56): private R-Tree partitions within a single Arbiter, entity migration enter/exit protocol, isolation from parent R-Tree, mandatory expiry, instance-local spatial queries
- Polyline collision generator (P-57): incremental segment construction with FIFO decay, extends P-08 collision injection, per-segment TTL for trail effects
- Container/vehicle logic (P-58): extends P-06 attachment with capacity bounds, enter/exit protocol, grouped handoff, destruction ejection
- Portal network (P-59): Controller-mediated anchor registry, cross-Arbiter teleport-as-handoff, network replication, displacement visible to P-63
- 10 baseline profile keys for team count, instance limits, polyline capacity, container capacity, and portal network bounds

**Dependencies:** Amendment A (P-08, P-06, P-01, P-09), Amendment D (container uses P-06 attachment, portals use owner linkage).

---

## 4. Primitives Requiring No docs-core/ Change

For completeness, these **20 primitives** are correctly classified as `game-adapter` and require no docs-core/ amendments. They operate entirely within adapter hook callbacks using engine-provided infrastructure:

| Category | Primitives |
|----------|-----------|
| Combat math | P-16 (Stat Layering), P-17 (Conditional Thresholds), P-21 (Value Conversion) |
| Entity state (game) | P-28 (Hostility Inversion), P-31 (Identity/Loadout Swap) |
| Hooks (game) | P-37 (On-Crit Hook), P-38 (On-Block/Defend Hook) |
| Accumulators | P-41 (DR Tracker), P-42 (Stacking Counters), P-43 (Charge-Up State) |
| Resources | P-47 (Spatial Corpse Registry), P-48 (Stagger Bar), P-49 (Resource-to-Damage), P-50 (Typed Charge Pool), P-51 (Desperation Cost) |
| UI/Group | P-54 (Group Choice Aggregator), P-55 (Concentration Intercept) |
| Systemic | P-63 (Movement-Damage Scalar), P-64 (Combo Field Matrix), P-65 (Vulnerability Window) |

These depend on the hook infrastructure from Amendment B being available, but their behavior is fully game-defined.

## 5. Proposed Work Order

| Order | Amendment | Primitives | Est. Scope | Rationale |
|-------|-----------|-----------|------------|-----------|
| 1 | **B: Hook Taxonomy** | 11 | Expand 04-1, 04-2 | Unblocks all combat pipeline work. Smallest change with largest downstream impact. |
| 2 | **A: Spatial Catalog** | 14 | New section in 01 or new 01-1 | Unblocks spatial query specifications. Largest primitive count. |
| 3 | **C: Entity Lifecycle** | 4 | New section or 01-2 | Unblocks downed state, stasis, actor spawning. Depends on B. |
| 4 | **D: Entity Relationships** | 4 | New 01-3 | Unblocks tether/symbiote/mind control. Most architecturally complex. |
| 5 | **E: Dynamic Topology** | 6 | New 01-4 | Unblocks terrain walls, portals, pocket arenas. Can be incremental. |

Amendments A and B can proceed in parallel. C depends on B. D is independent but complex. E depends on A and D.

## 6. Relationship to Existing Gap Tracker

Several entries in `docs/6-spec-drafts/GAPS_CHECKLIST.md` are directly addressed by this work:

| Gap | Overlap |
|-----|---------|
| T1-03 (Combat Modifier Pipeline & Proc Order) | Now resolved in the canonical gameplay docs. Amendment B remains the primitive-level formalization of the same Stage 7-10 combat flow. |
| T1-04 (Contention Lock Algorithm) | Now resolved in the canonical gameplay docs. Still relevant to P-47 (Spatial Corpse Registry) anywhere multiple consumers contend for the same corpse. |
| T1-06 (Reactive Proc & Cascade Depth) | Now resolved in the canonical gameplay docs. Amendment B's `post_damage_resolution` hook remains the primitive-level home for reactive proc/defer semantics. |

## 7. Open Questions for Team Review

1. **Should spatial primitives (Amendment A) live in `01-spatial-runtime-kernel.md` as a new section, or as a separate `01-1-spatial-primitive-catalog.md`?** The kernel doc is already 116 lines of high-level contracts. Adding 14 primitive specifications would roughly triple its length.

2. **[RESOLVED] Should the adapter hook expansion (Amendment B) define specific hook names (e.g., `pre_damage_resolution`), or define a generic "pipeline stage" model where the game adapter registers interception points?** The team has adopted the generic 12-stage model via the `dispatch_stage` hook in API v2, allowing the compiler to emit deterministic IR without forcing the engine into a dozen bespoke Rust traits.

3. **Are there primitives currently tagged `game-adapter` that the team believes should be engine-level?** The 20 game-adapter primitives in §4 were classified based on "the engine doesn't need to know about this." If the team disagrees on any, they should be promoted before amendments are drafted.

4. **Should Amendment D (Entity Relationships) be attempted before Amendment E (Dynamic Topology)?** D is more architecturally complex but enables more high-value mechanics (tether, mind control, symbiote). E covers more primitives but they're lower-frequency in the sketch corpus.

5. **How does this relate to `06-architecture-section-mapping.md`'s extraction roadmap?** Several `docs/1-architecture/` sections flagged as `retain-core` or `split` contain partial specifications for primitives in this assessment (e.g., collision algorithm, resolution policies, death/respawn lifecycle). Should the extraction and the primitive amendments proceed as one workstream or two?

---

*This assessment is derived from `docs-game-compiler/ability-primitives/` (the canonical primitive taxonomy) cross-referenced against `docs-core/` contracts as of 2026-03-17.*
