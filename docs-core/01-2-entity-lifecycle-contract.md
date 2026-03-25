# Entity Lifecycle Contract

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Extend the kernel's entity model from a binary lifecycle (exists / doesn't exist) to support multi-phase vitals, dormancy, suspension, and runtime actor spawning. This contract is Amendment C from `PRIMITIVE_IMPACT_ASSESSMENT.md`.

**Primitives formalized:** P-25 (Multi-Phase Vitals), P-32 (Actor Spawning), P-33 (Entity Dormancy), P-53 (Entity Suspension)

---

## 1. Scope

This contract defines engine-level entity lifecycle behaviors that the game adapter depends on but does not own. The adapter configures lifecycle parameters (via `SpawnConfiguration` and `IRDirective` declarations); the engine enforces the lifecycle rules.

This contract extends `01-spatial-runtime-kernel.md` without modifying its existing sections. All authority, tick, topology, safety, and numeric contracts remain in force.

## 2. Entity Lifecycle Phases

### 2.1 Phase Model

The engine tracks a `lifecycle_phase` for every entity. The default model is binary:

```
Active → Removed
```

Game adapters MAY define intermediate phases. The engine supports a bounded, linear phase chain:

```
Active → [Phase_1 → Phase_2 → ...] → Removed
```

Each phase has adapter-defined properties:
- **HP pool** — which vital pool receives damage in this phase
- **Ability set** — which abilities are available (adapter resolves via `dispatch_stage`)
- **Movement speed** — maximum speed for kinematic resolution
- **Capability overrides** — which capability flags are forced (e.g., `CAN_MOVE = false` during downed)

### 2.2 Engine-Tracked State

```
EntityLifecycle {
    current_phase:    u8,           // 0 = Active, N = adapter-defined, 255 = Removed
    phase_hp:         SimFixed,     // Current HP pool for the active phase
    phase_max_hp:     SimFixed,     // Max HP for the active phase
    phase_config_id:  u32,         // References phase configuration in game image
}
```

The engine MUST:
1. Track `lifecycle_phase` as authoritative kernel state (not game extension state).
2. Route damage to `phase_hp` based on the current phase — the adapter does not manually redirect damage.
3. Trigger a phase transition check at Stage 10 (`DeathCheck`) when `phase_hp` reaches zero.
4. Transfer `lifecycle_phase` during entity handoff to a new Arbiter.

### 2.3 Phase Transition Protocol

Phase transitions occur exclusively during Stage 10 (`DeathCheck`). The adapter returns a `StageOutcome` that MAY include a phase transition mutation:

```
PhaseTransitionMutation {
    entity_id:        string,
    new_phase:        u8,
    new_phase_hp:     SimFixed,
    new_phase_max_hp: SimFixed,
    new_phase_config: u32,        // References new phase config in game image
}
```

When the engine receives a phase transition mutation:
1. Set `lifecycle_phase` to `new_phase`.
2. Set `phase_hp` and `phase_max_hp` to the provided values.
3. The adapter's phase config determines ability set and movement speed changes — these take effect on the NEXT tick (not mid-tick).
4. If the adapter returns no phase transition and `phase_hp <= 0`, the engine transitions to `Removed` (entity death).

### 2.4 Resolution Bypass (P-24) Interaction

If a damage event carries the `resolution_bypass` flag (P-24, Piercing Execute):
1. The engine MUST skip all phase transition checks.
2. The entity transitions directly to `Removed` regardless of current phase.
3. Phase-specific death hooks do NOT fire — only the terminal death hook fires.

### 2.5 Phase Count Bound

The maximum number of intermediate phases per entity type is bounded:

- Baseline default: `max_lifecycle_phases_per_entity = 3`
- This MUST be defined in `00-1-core-baseline-profile.md`.
- Phase IDs 0 (Active) and 255 (Removed) are engine-reserved.
- Game-defined phases use IDs 1 through `max_lifecycle_phases_per_entity`.

---

## 3. Entity Dormancy (P-33)

### 3.1 Definition

A dormant entity remains in the R-Tree and in the engine's entity registry, but is **skipped during the 12-stage pipeline evaluation**. No `dispatch_stage` calls are made for a dormant entity.

### 3.2 Engine Behavior

When an entity's `is_dormant` flag is set to `true`:

1. **Tick evaluation:** The entity is excluded from all `dispatch_stage` entity batches. No adapter code runs for this entity.
2. **Spatial queries:** The entity remains in the R-Tree. It MAY appear in P-09 (Shape Overlap Query) results depending on the `dormant_targetable` flag (see §3.3).
3. **Downstream payloads:** The entity MAY appear in downstream payloads (it is still "visible" unless separately flagged as suspended). The adapter controls visibility via Stage 12 directives on OTHER entities that reference the dormant entity.
4. **Timers:** Status effect timers on the dormant entity are **paused** — expiry ticks do not advance. This is the default behavior; game adapters that want timers to continue during dormancy MUST handle timer advancement explicitly upon wake.
5. **Handoff:** A dormant entity participates in boundary handoff like any other entity. The `is_dormant` flag transfers with the entity's SoftState.
6. **Ghost updates:** The dormant entity's position does not change, so Ghost updates cease naturally (no movement = no delta to replicate).

### 3.3 Dormancy + Targetability

Dormancy and targetability are independent flags:

| `is_dormant` | `is_targetable` | Behavior |
|:---:|:---:|---|
| false | true | Normal entity — evaluated and targetable |
| false | false | Active but untargetable (P-27, e.g., Burrow phase) |
| true | true | Dormant but targetable (e.g., Cocoon shell — can be attacked to break) |
| true | false | Dormant and untargetable (e.g., stasis — completely inert) |

The adapter sets both flags via `StageOutcome` mutations. The engine checks `is_dormant` before building stage batches and checks `is_targetable` before including entities in spatial query results.

### 3.4 Wake Protocol

Setting `is_dormant` back to `false` resumes tick evaluation on the NEXT tick. The entity re-enters `dispatch_stage` batches starting from Stage 1 of the next tick. Timers resume from their paused state.

### 3.5 Baseline Bounds

- `max_dormant_entities_per_arbiter`: Maximum number of simultaneously dormant entities. Bounded to prevent dormant entities from accumulating without limit.
- Defined in `00-1-core-baseline-profile.md`.

---

## 4. Entity Suspension (P-53)

### 4.1 Definition

A suspended entity is **removed from the R-Tree, excluded from all spatial queries, excluded from downstream payloads, and excluded from tick evaluation**. It exists only as a preserved state blob in the engine's entity registry.

Suspension is strictly stronger than dormancy. A dormant entity is still in the R-Tree; a suspended entity is not.

### 4.2 Engine Behavior

When an entity's `is_suspended` flag is set to `true`:

1. **R-Tree:** The entity is removed from the R-Tree immediately. It does not appear in any spatial query results.
2. **Tick evaluation:** Excluded from all `dispatch_stage` batches (same as dormancy).
3. **Downstream payloads:** Excluded from ALL downstream payloads for ALL teams. The entity is invisible to all Edge Nodes.
4. **Timers:** Paused (same as dormancy).
5. **Handoff:** A suspended entity does NOT participate in boundary handoff — it is pinned to its current Arbiter for the duration of suspension. If the Arbiter crashes, the entity's preserved state is recovered through the durability bridge (`03-durability-bridge.md`).
6. **Ghost updates:** The entity has no Ghost representation while suspended (removed from R-Tree, so neighbors do not receive updates).

### 4.3 Un-Suspension Protocol

Setting `is_suspended` back to `false`:
1. The engine re-inserts the entity into the R-Tree at its **preserved position** (the position it had when suspended).
2. The entity becomes visible in spatial queries and downstream payloads on the NEXT tick.
3. Timers resume from their paused state.
4. Ghost updates resume as neighbors discover the entity via the next R-Tree scan.

### 4.4 Suspension Duration Bound

- Every suspension MUST have a finite `suspension_deadline_tick`. If the deadline is reached and the adapter has not un-suspended the entity, the engine MUST un-suspend automatically and emit a fault signal.
- `max_suspension_duration_ticks`: Baseline bound defined in `00-1-core-baseline-profile.md`.
- This prevents entities from being permanently lost in suspension due to adapter bugs.

---

## 5. Actor Spawning (P-32)

### 5.1 Spawn Lifecycle

Actor spawning is a multi-step protocol between the adapter and the engine:

1. **Directive:** The adapter emits a P-32 `IRDirective` (cross-cutting) during any stage's `StageOutcome`.
2. **Allocation:** The engine allocates an `entity_id` using the generational ID allocation contract (`03-durability-bridge.md`). The engine reserves an R-Tree slot at the requested position.
3. **Configuration:** The engine calls `initialize_spawn_configuration` with a `SpawnRequest` containing the allocated `entity_id`, `archetype_id`, `owner_entity_id`, `spawn_position`, and `spawn_tick`.
4. **Initialization:** The adapter returns a `SpawnConfiguration` containing `initial_entity_state`, `ghost_movement_replication_cadence`, and `lifetime_ticks`.
5. **Insertion:** The engine inserts the entity into the R-Tree and begins evaluation on the NEXT tick.

### 5.2 Owner Linkage

Every spawned actor carries an `owner_entity_id` linking it to the entity that spawned it. This linkage:
- Is stored as kernel state (not game extension state).
- Survives handoff — if the spawned actor crosses an Arbiter boundary, the owner linkage transfers.
- Is cleaned up on owner death — when the owner transitions to `Removed`, the engine notifies spawned actors. The adapter decides whether spawned actors despawn, persist, or transfer ownership.

### 5.3 Entity Count Bounds

The engine MUST enforce bounded entity counts:

| Bound | Scope | Baseline Key |
|-------|-------|-------------|
| `max_entities_per_arbiter` | Total entities (owned + spawned) on one Arbiter | `00-1-core-baseline-profile.md` |
| `max_spawned_actors_per_owner` | Actors spawned by a single owner entity | `00-1-core-baseline-profile.md` |

If a spawn would exceed either bound:
1. The engine MUST reject the spawn directive.
2. The `initialize_spawn_configuration` hook is NOT called.
3. A fault signal is emitted with code `SPAWN_ENTITY_LIMIT_EXCEEDED`.

### 5.4 Lifetime Enforcement

If the adapter returns a non-null `lifetime_ticks` in `SpawnConfiguration`:
1. The engine tracks an `expiry_tick = spawn_tick + lifetime_ticks`.
2. When `current_tick >= expiry_tick`, the engine transitions the entity to `Removed` at the end of Stage 10 (`DeathCheck`).
3. The adapter's `dispatch_stage` for Stage 10 can observe the pending expiry and choose to extend, despawn gracefully, or trigger effects.

If `lifetime_ticks` is null, the actor persists until explicitly despawned by the adapter or its owner dies.

### 5.5 Spawned Actor Types

The engine does not distinguish between actor types (projectile, zone, summon, decoy). All spawned actors are entities with the same lifecycle guarantees. The distinction is adapter-defined via `archetype_id` and the game image's `EntityDefinitions`.

The `ghost_movement_replication_cadence` in `SpawnConfiguration` controls how frequently the spawned actor's position is replicated to neighbors — `None` for static zones, `High` for projectiles.

### 5.6 Cross-Stage Spawn Timing

Spawn directives emitted during any stage are collected by the engine and processed AFTER Stage 12 of the current tick (post-emission). The spawned entity begins evaluation on the NEXT tick's Stage 1. This ensures spawned actors never appear mid-pipeline.

---

## 6. Interaction Matrix

| Feature | R-Tree Present | Tick Evaluated | In Spatial Queries | In Downstream Payloads | Timers Run |
|---------|:-:|:-:|:-:|:-:|:-:|
| Active entity | Yes | Yes | Yes | Yes | Yes |
| Dormant entity | Yes | No | Configurable | Yes | No (paused) |
| Suspended entity | No | No | No | No | No (paused) |
| Removed entity | No | No | No | No | No |

## 7. Conformance Requirements

Implementations MUST pass:

1. **Phase transition determinism:** Same damage sequence produces same phase transitions across replay.
2. **Resolution bypass:** P-24 flagged events skip all phases and transition directly to Removed.
3. **Dormancy exclusion:** Dormant entities produce zero `dispatch_stage` invocations.
4. **Suspension isolation:** Suspended entities appear in zero spatial query results and zero downstream payloads.
5. **Spawn count enforcement:** Spawn attempts exceeding entity bounds are rejected with fault signals.
6. **Lifetime expiry:** Actors with finite lifetime are removed deterministically at the correct tick.
7. **Suspension deadline:** Suspension exceeding `max_suspension_duration_ticks` triggers automatic un-suspension plus fault.
8. **Handoff preservation:** `lifecycle_phase`, `is_dormant`, `owner_entity_id`, and `expiry_tick` survive entity handoff. `is_suspended` entities do not hand off (pinned).

## 8. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `01-spatial-runtime-kernel.md` | This contract extends the kernel's entity model. All kernel invariants remain in force. |
| `04-1-game-adapter-contract.md` | Stage 10 (`DeathCheck`) is where phase transitions are evaluated. `initialize_spawn_configuration` is called during the spawn protocol. |
| `04-2-game-adapter-api-contract.md` | `SpawnRequest`, `SpawnConfiguration`, and `StageOutcome` payloads carry lifecycle data. |
| `03-durability-bridge.md` | Entity ID allocation and suspended entity recovery. |
| `00-1-core-baseline-profile.md` | Baseline bounds for phase count, entity count, suspension duration. |
| `docs-game-compiler/ability-primitives/` | P-25, P-32, P-33, P-53 are formalized by this contract. |
