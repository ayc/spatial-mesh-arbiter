# Entity Relationship Contract

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define engine-level entity-to-entity relationships: persistent bindings, control authority swaps, and input multiplexing. These are cross-entity dependencies that the engine must track, replicate across Arbiter boundaries, and clean up on entity death. This contract is Amendment D from `PRIMITIVE_IMPACT_ASSESSMENT.md`.

**Primitives formalized:** P-29 (Control Authority Swap), P-30 (Input Multiplexing), P-34 (Persistent Linkage)

**Note:** P-06 (Attached Kinematics) is a spatial relationship already specified in `01-1-spatial-primitive-catalog.md` §3.6. This contract covers non-spatial relationships that affect input routing and cross-entity state dependencies.

---

## 1. Scope

Entity relationships are engine-tracked, cross-boundary-safe links between two or more entities. They differ from game-extension state in three ways:

1. **The engine acts on them** — input routing (P-29, P-30) requires the engine to redirect Edge Node proposals before the adapter sees them.
2. **They survive handoff** — when either entity crosses an Arbiter boundary, the relationship must be maintained or gracefully broken.
3. **They have cleanup invariants** — when either entity transitions to `Removed`, the engine must clean up all relationships involving that entity.

The adapter creates and configures relationships via `StageOutcome` mutations and `IRDirective` declarations. The engine enforces the structural invariants.

---

## 2. Persistent Linkage / Bindings (P-34)

### 2.1 Definition

A binding is a named, typed, two-way dependency between two entities. It is the engine's general-purpose relationship primitive.

### 2.2 Binding Structure

```
EntityBinding {
    binding_id:       u64,          // Engine-allocated, unique per Arbiter
    binding_type:     u32,          // Game-defined type ID (tether, soulbind, symbiote, etc.)
    entity_a:         EntityID,     // First linked entity
    entity_b:         EntityID,     // Second linked entity
    max_distance:     SimFixed,     // Optional distance constraint (0 = unlimited)
    expiry_tick:      u64,          // Tick at which the binding auto-expires (0 = permanent until broken)
    state:            BindingState, // Active, Suspended, PendingCleanup
}

enum BindingState {
    Active,           // Fully operational
    CrossBoundary,    // Entities are on different Arbiters — maintained via relay
    PendingCleanup,   // One entity died or the binding expired — cleanup in progress
}
```

### 2.3 Engine Behavior

**Creation:**
1. The adapter emits a binding creation mutation in a `StageOutcome` (any stage).
2. The engine allocates `binding_id` and stores the binding on BOTH entities' SoftState.
3. Both entities can query their active bindings during any subsequent stage.

**Per-Tick Evaluation:**
1. The engine does NOT evaluate bindings per-tick by default — bindings are passive data.
2. Binding-dependent behavior (e.g., tether damage, soulbind duplication) is driven by the adapter's IR instructions, not by the engine.
3. The one exception is distance-constrained bindings (`max_distance > 0`): if both entities are on the same Arbiter, the engine checks distance during PostKinematic and marks bindings as `distance_violated: bool` for the adapter to read. The engine does NOT enforce the distance limit — that's the adapter's job via P-04 (Positional Clamping).

**Cleanup:**
1. When either entity transitions to `Removed` (death), the engine sets all that entity's bindings to `PendingCleanup`.
2. On the NEXT tick, the engine delivers a `binding_broken` event to the surviving entity's adapter evaluation (injected as an incoming deferred event at Stage 3 or Stage 7, depending on binding type configuration).
3. The adapter decides the consequence (e.g., tether break triggers damage, symbiote detaches).
4. After the cleanup event is processed, the engine removes the binding from both entities.

**Expiry:**
1. If `expiry_tick > 0` and `current_tick >= expiry_tick`, the engine transitions the binding to `PendingCleanup` and follows the same cleanup protocol as entity death.

### 2.4 Cross-Boundary Bindings

When entity A hands off to a new Arbiter while bound to entity B on the old Arbiter:

1. The old Arbiter's binding transitions to `CrossBoundary` state.
2. The binding is replicated to the new Arbiter as part of entity A's SoftState during handoff.
3. The new Arbiter creates a `CrossBoundary` binding referencing entity B by EntityID.
4. The new Arbiter uses entity B's Ghost data for any distance checks.
5. If the adapter emits a relay event targeting entity B (e.g., soulbind damage duplication), the engine routes it to entity B's authoritative Arbiter.

When both entities are on the same Arbiter again (entity B hands off to join A, or vice versa):
1. Both `CrossBoundary` bindings are reconciled into a single `Active` binding.
2. The engine verifies binding IDs match and deduplicates.

### 2.5 Bounds

| Bound | Description | Baseline Key |
|-------|-------------|-------------|
| `max_bindings_per_entity` | Maximum active bindings on a single entity | `00-1-core-baseline-profile.md` |
| `max_cross_boundary_bindings_per_arbiter` | Maximum cross-boundary bindings tracked | `00-1-core-baseline-profile.md` |

Binding creation exceeding `max_bindings_per_entity` MUST be rejected with fault code `BINDING_LIMIT_EXCEEDED`.

---

## 3. Control Authority Swap (P-29)

### 3.1 Definition

A control authority swap redirects one player's Edge Node input stream to a different entity. The original entity's inputs are suspended for the duration.

### 3.2 Control State

```
ControlOverride {
    controlled_entity_id:   EntityID,   // Entity receiving redirected inputs
    controller_entity_id:   EntityID,   // Entity whose player's inputs are used
    original_owner_id:      EntityID,   // The controlled entity's original input source
    expiry_tick:            u64,        // Auto-revert tick (0 = until explicitly broken)
    binding_id:             u64,        // References a P-34 binding between controller and controlled
}
```

### 3.3 Engine Behavior

**Activation (Stage 1):**
1. The adapter returns a control swap mutation during Stage 1 (`ControlAuthorityAndInputRouting`).
2. The engine validates: the controlled entity does NOT already have an active `ControlOverride` (only one controller at a time).
3. The engine installs the `ControlOverride` and creates a backing P-34 binding between the two entities.
4. Starting from Stage 2 of the SAME tick: the controlled entity's intent validation uses the controller player's Edge Node proposals instead of its own.

**During Control:**
1. The controller player's Edge Node sends proposals as normal. The engine routes proposals addressed to the controller's entity to BOTH the controller entity AND the controlled entity. The adapter decides per-proposal which entity acts on it.
2. The controlled entity's original player's Edge Node receives a `control_suspended` signal. Their proposals are rejected with `CONTROL_SUSPENDED` until control reverts.
3. The controlled entity retains its own authoritative Arbiter — the Arbiter does NOT change. Only the input source changes.

**Revert:**
1. On `expiry_tick`, or when the adapter emits a control-break mutation, or when either entity transitions to `Removed`:
2. The engine removes the `ControlOverride`.
3. The controlled entity resumes receiving inputs from its original Edge Node source.
4. Revert is atomic — takes effect at the Stage 1 engine boundary of the tick in which it occurs.

### 3.4 Cross-Boundary Control

If the controller and controlled entities are on different Arbiters:

1. The controller's Arbiter knows (via the binding) that proposals should be relayed to the controlled entity's Arbiter.
2. The controller's Edge Node proposals are forwarded as internal relay events to the controlled entity's Arbiter.
3. The controlled entity's Arbiter receives them as part of `incoming_deferred_events` and processes them in the appropriate stage.
4. Latency: cross-boundary control introduces one relay hop of latency per proposal. For Mind Control (SK-40), this is acceptable — the controlled entity acts with ~1 tick delay relative to the controller's input.

### 3.5 Constraints

1. **One controller per entity.** An entity MUST NOT have more than one active `ControlOverride`. Attempts to install a second MUST be rejected with fault code `CONTROL_ALREADY_OVERRIDDEN`.
2. **No chain control.** If entity A controls entity B, entity B MUST NOT simultaneously control entity C. The engine rejects control swap mutations where the proposed controller is already being controlled.
3. **Authority preservation.** The controlled entity's authoritative Arbiter does NOT change during the swap. Single-authority is maintained.

---

## 4. Input Multiplexing (P-30)

### 4.1 Definition

Input multiplexing extends the input routing model beyond 1:1 (one player → one entity) to support:
- **One-to-many:** One player controls N entities (e.g., SK-68 Multi-Entity Control)
- **Many-to-one:** N players control one entity (e.g., SK-77 Two-Player Entity)

### 4.2 Multiplexing State

```
InputMultiplexConfig {
    mode:               MultiplexMode,
    primary_entity_id:  EntityID,       // The "anchor" entity
    secondary_entities: Vec<EntityID>,  // Additional entities in the multiplex group
    input_policy:       InputPolicy,    // How inputs are distributed
    binding_ids:        Vec<u64>,       // Backing P-34 bindings for each pair
}

enum MultiplexMode {
    OneToMany,  // Primary entity's player controls all secondary entities
    ManyToOne,  // Secondary entities' players contribute inputs to the primary entity
}

enum InputPolicy {
    Mirror,       // All entities receive identical inputs (OneToMany: movement mirrored)
    RoleSplit,    // Different input channels routed to different entities (ManyToOne: player 1 = movement, player 2 = abilities)
    AdapterRouted, // The adapter decides per-proposal which entity receives it (most flexible)
}
```

### 4.3 Engine Behavior

**One-to-Many (`OneToMany` + `Mirror`):**
1. The primary entity's player sends proposals.
2. The engine duplicates each proposal to all secondary entities.
3. Each entity receives and processes the proposal independently in its own `dispatch_stage` evaluation.
4. Movement proposals are applied to all entities (they move together). Ability proposals may be filtered by the adapter (e.g., only the primary entity casts abilities).

**One-to-Many (`OneToMany` + `AdapterRouted`):**
1. The primary entity's player sends proposals.
2. The engine forwards all proposals to the primary entity's adapter evaluation.
3. The adapter returns routing mutations specifying which secondary entities receive which proposals.
4. This enables the "commander" pattern — one player issues orders, different minions execute different commands.

**Many-to-One (`ManyToOne` + `RoleSplit`):**
1. Multiple players send proposals addressed to the shared entity.
2. The engine tags each proposal with its source player ID.
3. The adapter evaluates proposals with source attribution and applies role-based routing (e.g., player 1's movement proposals are accepted, player 2's ability proposals are accepted, conflicting inputs are resolved by the adapter).

**Many-to-One (`ManyToOne` + `AdapterRouted`):**
1. Same as `RoleSplit` but with fully adapter-defined conflict resolution.

### 4.4 Cross-Boundary Multiplexing

If secondary entities in a multiplex group are on different Arbiters:

1. The primary entity's Arbiter is the multiplex coordinator.
2. Proposals routed to secondary entities on other Arbiters are forwarded as internal relay events.
3. Secondary entity Arbiters process the relayed proposals through their local `dispatch_stage` pipeline.
4. For `ManyToOne`, each contributing player's Arbiter forwards proposals to the shared entity's Arbiter.

### 4.5 Constraints

1. **Bounded group size.** `max_multiplex_group_size` defines the maximum number of entities in a multiplex group. Defined in `00-1-core-baseline-profile.md`.
2. **Backed by bindings.** Every multiplex relationship creates P-34 bindings between the primary and each secondary entity. Binding cleanup on entity death automatically breaks the multiplex group.
3. **Single multiplex per entity.** An entity MUST NOT be the primary in more than one multiplex group, and MUST NOT be a secondary in more than one group.
4. **No nested multiplexing.** A secondary entity in a `OneToMany` group MUST NOT be the primary of another multiplex group.

---

## 5. Relationship Lifecycle Summary

| Event | P-34 Binding | P-29 Control Swap | P-30 Multiplex |
|-------|:---:|:---:|:---:|
| Created by adapter | Stage mutation | Stage 1 mutation | Stage 1 mutation |
| Backed by P-34 binding | — (is the binding) | Yes | Yes (per pair) |
| Cross-boundary support | Yes (CrossBoundary state) | Yes (relay forwarding) | Yes (coordinator model) |
| Cleanup on entity death | Auto (PendingCleanup) | Auto (revert + binding break) | Auto (binding break dissolves group) |
| Cleanup on expiry | Auto (PendingCleanup) | Auto (revert) | Adapter-driven |
| Max per entity | `max_bindings_per_entity` | 1 controller | 1 group membership |

## 6. Baseline Profile Keys

The following keys MUST be defined in `00-1-core-baseline-profile.md`:

| Key | Description |
|-----|-------------|
| `max_bindings_per_entity` | Maximum active bindings on a single entity |
| `max_cross_boundary_bindings_per_arbiter` | Maximum cross-boundary bindings tracked per Arbiter |
| `max_multiplex_group_size` | Maximum entities in an input multiplex group |

## 7. Conformance Requirements

Implementations MUST pass:

1. **Binding survival:** A binding between two entities survives handoff of either entity to a new Arbiter. Binding ID and type are preserved.
2. **Binding cleanup:** When either entity dies, all its bindings transition to `PendingCleanup` and deliver `binding_broken` events to surviving partners.
3. **Binding expiry:** Bindings with `expiry_tick` auto-expire deterministically at the correct tick.
4. **Control swap atomicity:** Control override takes effect at the Stage 1 engine boundary. No split-brain input between old and new controller during a tick.
5. **Control swap revert:** On expiry, break, or entity death, control reverts atomically. The original player's inputs resume on the next tick.
6. **No chain control:** Installing a control swap on an already-controlled entity is rejected.
7. **Multiplex bounded:** Group sizes exceeding `max_multiplex_group_size` are rejected.
8. **Cross-boundary relay:** Proposals routed across boundaries arrive and are processed deterministically on the target Arbiter.
9. **Single authority:** No relationship primitive creates dual-authority over an entity. The controlled entity's Arbiter remains its sole authority.

## 8. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `01-spatial-runtime-kernel.md` | Authority model (§2) — relationships MUST NOT violate single-authority. |
| `01-1-spatial-primitive-catalog.md` | P-06 (Attached Kinematics) is a spatial relationship specified there. P-04 (Positional Clamping) enforces distance limits that binding distance checks inform. |
| `01-2-entity-lifecycle-contract.md` | Entity death triggers binding cleanup. Dormant/suspended entities retain their bindings (frozen). |
| `02-spatial-messaging-plane.md` | Cross-boundary relay for binding events and control swap proposal forwarding. |
| `04-1-game-adapter-contract.md` | Stage 1 (`ControlAuthorityAndInputRouting`) is where P-29/P-30 mutations are committed. |
| `04-2-game-adapter-api-contract.md` | `DispatchStageRequest` for Stage 1 carries control/multiplex directives. `DeferredEvent` delivers `binding_broken` events. |
| `00-1-core-baseline-profile.md` | Baseline bounds for binding count, cross-boundary binding count, and multiplex group size. |
| `docs-game-compiler/ability-primitives/04-entity-state-capability.md` | Game-layer descriptions of P-29, P-30, P-34. |
