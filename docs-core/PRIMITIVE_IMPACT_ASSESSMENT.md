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
**Target document:** New section in `01-spatial-runtime-kernel.md` or standalone `01-1-spatial-primitive-catalog.md`
**Priority:** HIGH — blocks all spatial query and movement specifications downstream

**What exists:** `01-spatial-runtime-kernel.md` §1 lists "movement integration and collision primitives" as kernel-owned. The baseline profile defines numeric bounds for position/velocity. `06-architecture-section-mapping.md` marks the collision algorithm as `RESOLVED` (T0-03). But no contract exists for the 14 specific spatial operations the game adapter depends on.

**What's needed:** A catalog of engine-provided spatial operations with:

- **Kinematic mutations** (P-01 through P-08): Instant translation, forced displacement, trajectory steering, positional clamping, historical state buffer, attached kinematics, entity-as-kinematic-volume, dynamic collision injection. For each: input parameters, execution phase within the tick, interaction with handoff, determinism guarantees.

- **Spatial queries** (P-09 through P-14): Shape overlap, raycast, N-nearest neighbor, facing check, tag filtering, continuous proximity monitor. For each: input parameters, return type, R-Tree interaction, Ghost entity inclusion rules, bounded result guarantees.

**Blast radius:** Moderate. This is additive — no existing contract changes, only new specification. The adapter contract (04-x) would gain references to these primitives as "engine-provided capabilities the adapter may invoke."

**Dependencies:** None. Can proceed independently.

---

### Amendment B: Adapter Hook Taxonomy Expansion

**Primitives covered:** P-35, P-36, P-39, P-40 (4 primitives) + pipeline structure for P-15, P-18, P-19, P-20, P-22, P-60, P-61
**Target document:** `04-1-game-adapter-contract.md` §2 (Required Adapter Surface) and §3 (Tick Boundary and Call Order)
**Priority:** HIGH — blocks combat pipeline specification
**Concrete proposal:** `docs-game-compiler/03-1-compiler-ir-specification.md` defines 12 canonical pipeline stages and maps all 65 primitives to stages. This is the compiler team's proposed hook taxonomy for engine adoption.

**What exists:** The adapter contract defines 4 required hooks:
1. Intent validation hook
2. External action resolution hook
3. Internal event resolution hook
4. Spawn/initial-state construction hook

**What's needed:** The combat resolution pipeline requires finer-grained hook points than "external action resolution." The 125 ability sketches demonstrate that game adapters need to intercept at specific stages:

| Hook Point | Primitives Served | Pipeline Stage |
|------------|-------------------|----------------|
| `validate_intent` (exists) | P-26 (capability check), P-40 (on-cast intercept) | Phase 1: Intent validation |
| **`pre_damage_resolution`** (new) | P-18 (absorption barrier), P-19 (instance barrier), P-22 (deferred ledger) | Phase 2: Before damage applies to HP |
| **`post_damage_resolution`** (new) | P-35 (on-hit), P-36 (on-damage-received), P-60 (event cloning), P-61 (projectile hijack) | Phase 2: After damage applied |
| **`death_check`** (new) | P-23 (floor clamping), P-24 (resolution bypass), P-25 (multi-phase vitals), P-39 (on-death) | Phase 2: Entity reaches 0 HP |
| `resolve_internal` (exists) | Cross-Arbiter relay resolution | Phase 2: Internal events |

The amendment does NOT define the combat math — that stays game-owned. It defines the **pipeline stages** and **hook call order** so that game adapters have deterministic interception points.

**Blast radius:** Moderate. Expands the adapter surface (§2) and call order (§3). Existing hooks are preserved; new hooks are additive. The API contract (04-2) gains new request/response envelope definitions for the new hooks.

**Dependencies:** None directly, but complements Amendment A (spatial queries are inputs to combat resolution).

---

### Amendment C: Entity Lifecycle Extension

**Primitives covered:** P-25 (Multi-Phase Vitals), P-32 (Actor Spawning), P-33 (Entity Dormancy), P-53 (Entity Suspension)
**Target document:** New section in `01-spatial-runtime-kernel.md` or new `01-2-entity-lifecycle-contract.md`
**Priority:** MEDIUM — blocks downed-state and stasis mechanics

**What exists:** The implicit entity lifecycle is binary: an entity exists in the R-Tree and is evaluated each tick, or it doesn't exist. The durability bridge (03) classifies hard vs soft state. The adapter contract defines a spawn hook.

**What's needed:**

1. **Multi-phase lifecycle model.** The engine currently assumes Alive → Dead. Game adapters need to define intermediate phases (Downed, Transformed) where the entity persists but with different evaluation rules. The engine contract should specify:
   - Entity life phase as a kernel-tracked enum (game adapter defines the phases)
   - Death check as an interceptable pipeline stage (Amendment B's `death_check` hook)
   - Phase transitions as deterministic, atomic operations within a tick

2. **Entity dormancy contract.** An entity can be paused (skipped during tick evaluation) while remaining in the R-Tree. The contract should specify: what "paused" means for timers, for spatial queries (included or excluded?), for downstream payloads.

3. **Entity suspension contract.** An entity can be fully removed from spatial/targeting/rendering while preserved in memory. Stronger than dormancy. The contract should specify: R-Tree removal and re-insertion semantics, timer behavior, state preservation guarantees.

4. **Actor spawning contract.** Formalizing what "spawn an entity at runtime" means: R-Tree insertion, OwnerID linkage, bounded entity count per owner, handoff behavior for spawned actors.

**Blast radius:** Moderate. Extends the kernel's entity model. Existing entities behave identically (single-phase lifecycle is the default). New phases are opt-in via game adapter configuration.

**Dependencies:** Amendment B (death_check hook is where phase transitions are intercepted).

---

### Amendment D: Entity Relationship Contract

**Primitives covered:** P-06 (Attached Kinematics), P-29 (Control Authority Swap), P-30 (Input Multiplexing), P-34 (Persistent Linkage)
**Target document:** New `01-3-entity-relationship-contract.md` or section in `01-spatial-runtime-kernel.md`
**Priority:** MEDIUM — blocks tether, symbiote, mind control, and multi-entity mechanics

**What exists:** The authority contract (01 §2) defines single-authority ownership. The messaging plane (02) routes messages by entity owner. No contract exists for entity-to-entity relationships that the engine must track.

**What's needed:**

1. **Persistent linkage (bindings).** A two-way dependency between entities that:
   - Survives Arbiter handoff (replicated as SoftState on both entities)
   - Is cleaned up when either entity dies or the link expires
   - Has a bounded count per entity
   - Can trigger cross-Arbiter relay when a linked entity changes state

2. **Attached kinematics.** Parenting one entity's position to another's transform. The engine must:
   - Overwrite the child's position each tick to match parent + offset
   - Hand off the child with the parent when crossing boundaries (or orphan it)
   - Skip independent kinematic resolution for attached entities

3. **Control authority swap.** Routing one player's Edge Node input to a different entity. The engine must:
   - Redirect input at the transport layer (not the game layer)
   - Maintain single-authority — the controlled entity still has one authoritative Arbiter
   - Revert atomically on expiry or break

4. **Input multiplexing.** One-to-many (one player controls N entities) or many-to-one (N players control one entity). Extends the Edge Node input routing model.

**Blast radius:** Significant. Touches the authority model (01), the messaging plane (02), and the adapter interface (04). Bindings introduce a new cross-Arbiter state synchronization requirement. This is the most architecturally complex amendment.

**Dependencies:** None strictly, but pairs well with Amendment A (attached kinematics depends on kinematic resolution order).

---

### Amendment E: Dynamic Spatial Topology

**Primitives covered:** P-08 (Dynamic Collision Injection), P-52 (Asymmetric Team-Rendering), P-56 (Spatial Instance Forking), P-57 (Polyline Collision Generator), P-58 (Container/Vehicle Logic), P-59 (N-Way Portal Network)
**Target document:** New `01-4-dynamic-topology-contract.md`
**Priority:** LOW — blocks terrain walls, pocket arenas, portals, and vehicles. These are powerful but less frequently needed than combat pipeline basics.

**What exists:** The topology contract (01 §4) covers topology epochs and split/merge/slide. The Mesh Controller manages the R-Tree. No contract exists for game-triggered spatial modifications.

**What's needed:**

1. **Dynamic collision injection** (P-08): Temporarily adding/removing static geometry. Requires: spatial grid update, bounded area/lifetime, cross-boundary replication if geometry overlaps a boundary.

2. **Spatial instance forking** (P-56): Creating a private R-Tree partition. Requires: entity migration protocol (remove from parent, insert into child), bounded lifetime, exit protocol (re-insert into parent on expiry).

3. **Portal network** (P-59): A registry of spatial anchors for cross-Arbiter teleportation. Requires: Controller-mediated registry, teleport-as-handoff protocol, bounded anchor count.

4. **Asymmetric rendering** (P-52): Per-team visibility flags on entities affecting downstream payloads. Requires: the downstream payload builder to check per-entity per-team visibility flags.

5. **Container/vehicle logic** (P-58): Entities locked to a parent's transform with suppressed movement. Specialization of P-06 (attached kinematics) with capacity bounds and explicit enter/exit protocol.

6. **Polyline collision generator** (P-57): Building collision geometry from a point sequence. Specialization of P-08 with incremental construction and FIFO segment expiry.

**Blast radius:** Moderate per-primitive, but covers 6 primitives across different subsystems. Can be delivered incrementally — P-08 and P-52 are simpler; P-56 and P-59 are more complex.

**Dependencies:** Amendment A (spatial queries underpin all of these). Amendment D (container logic depends on attached kinematics).

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
| T1-03 (Combat Modifier Pipeline & Proc Order) | Amendment B directly formalizes the hook pipeline that T1-03 is drafting. These should be reconciled — T1-03's 11-step `apply_combat_math` expansion maps to Amendment B's hook stages. |
| T1-04 (Contention Lock Algorithm) | Relevant to P-47 (Spatial Corpse Registry) where multiple consumers contend for the same corpse. Game-adapter level, but the algorithm gap remains. |
| T1-06 (Reactive Proc & Cascade Depth) | Amendment B's `post_damage_resolution` hook is where reactive procs (P-35, P-36) fire. The cascade depth bound is a constraint on hook re-entrancy that Amendment B should specify. |

## 7. Open Questions for Team Review

1. **Should spatial primitives (Amendment A) live in `01-spatial-runtime-kernel.md` as a new section, or as a separate `01-1-spatial-primitive-catalog.md`?** The kernel doc is already 116 lines of high-level contracts. Adding 14 primitive specifications would roughly triple its length.

2. **Should the adapter hook expansion (Amendment B) define specific hook names (e.g., `pre_damage_resolution`), or define a generic "pipeline stage" model where the game adapter registers interception points?** The former is more prescriptive; the latter is more flexible but harder to conformance-test.

3. **Are there primitives currently tagged `game-adapter` that the team believes should be engine-level?** The 20 game-adapter primitives in §4 were classified based on "the engine doesn't need to know about this." If the team disagrees on any, they should be promoted before amendments are drafted.

4. **Should Amendment D (Entity Relationships) be attempted before Amendment E (Dynamic Topology)?** D is more architecturally complex but enables more high-value mechanics (tether, mind control, symbiote). E covers more primitives but they're lower-frequency in the sketch corpus.

5. **How does this relate to `06-architecture-section-mapping.md`'s extraction roadmap?** Several `docs/1-architecture/` sections flagged as `retain-core` or `split` contain partial specifications for primitives in this assessment (e.g., collision algorithm, resolution policies, death/respawn lifecycle). Should the extraction and the primitive amendments proceed as one workstream or two?

---

*This assessment is derived from `docs-game-compiler/ability-primitives/` (the canonical primitive taxonomy) cross-referenced against `docs-core/` contracts as of 2026-03-17.*
