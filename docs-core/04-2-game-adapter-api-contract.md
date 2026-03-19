# Game Adapter API Contract (Normative)

This document defines strict API and startup negotiation requirements for
the engine/game adapter boundary.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope and Precedence

1. `05-conformance-invariants.md` defines global invariants.
2. `04-1-game-adapter-contract.md` defines adapter behavior constraints.
3. This document defines strict API shapes and compatibility negotiation.
4. `04-3-version-line-transition-contract.md` defines rollout/rollback behavior between valid lines.
5. `04-0-game-adapter-interface.md` is conceptual and explanatory.

If there is a conflict, higher-precedence documents win.

## 2. Canonical Hook Names (API v2)

The engine-facing adapter API is fixed to these hook identifiers. The transition from API v1 (monolithic `resolve_external`/`internal`) to API v2 establishes the 12-stage tick lifecycle.

1. `validate_intent` (Entry point for Stage 2)
2. `dispatch_stage` (Unified entry point for Stages 1 and 3-12)
3. `initialize_spawn_configuration`
4. `describe_compatibility`

Engine integration MUST NOT require any additional mandatory hook names. The v1 hooks `resolve_external` and `resolve_internal` are deprecated.

## 3. Call Envelope Contract

### 3.1 Request Envelope

Every hook call MUST carry this request envelope:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `call_id` | string | yes | unique per invocation |
| `hook_name` | enum | yes | one of section 2 values |
| `tick` | u64 | yes | authoritative tick anchor |
| `topology_epoch` | u64 | yes | topology context |
| `data_epoch` | u64 | yes | content/config context |
| `deadline_us` | u32 | yes | hard call deadline from engine |
| `primary_entity_id` | string or null | yes | primary entity in scope for this call, when applicable |
| `payload` | object | yes | hook-specific payload |
| `wire_schema_version` | u32 | yes | payload-wire schema version |

### 3.2 Response Envelope

Every hook call MUST return this response envelope:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `call_id` | string | yes | must match request |
| `hook_name` | enum | yes | must match request |
| `status` | enum | yes | `OK`, `REJECT`, `FAULT`, `TIMEOUT` |
| `stage_outcome` | object or null | no | required for `dispatch_stage` and optionally `validate_intent` (for P-40 intercepts) |
| `terminal_outcome` | object or null | no | required for discrete intents in validation hooks |
| `spawn_configuration` | object or null | no | required for `initialize_spawn_configuration` |
| `reject_code` | string or null | no | required when `status=REJECT` |
| `fault_code` | string or null | no | required when `status=FAULT` or `status=TIMEOUT` |

Response rules:
1. `status=OK` MUST NOT include `reject_code` or `fault_code`.
2. `status=REJECT` MUST include deterministic `reject_code` and MUST NOT include mutations.
3. `status=FAULT` or `status=TIMEOUT` MUST fail closed (no mutation side effects).
4. Envelope fields and ordering used for digest/replay MUST be deterministic.

### 3.3 StageOutcome Payload (Declarative Boundary)

For `dispatch_stage` and mutating `validate_intent` calls, the adapter MUST return all state changes declaratively via the `stage_outcome` object. No mutable engine contexts are exposed.

```json
{
  "mutations": [],        // State changes to apply to specific entities
  "emitted_events": [],   // Internal/Hard events to broadcast immediately
  "deferred_events": [],  // Events queued for the next tick (required by Stage 9 & 11)
  "faults": []            // Non-fatal errors to log/observe
}
```

### 3.4 Hook-Specific Constraints

| Hook | Required Input Payload Class | Allowed Status Values | Mutation Allowed |
| --- | --- | --- | --- |
| `validate_intent` | external intent + actor snapshot | `OK`, `REJECT`, `FAULT`, `TIMEOUT` | yes (via `stage_outcome` for Stage 2 cast intercepts) |
| `dispatch_stage` | `DispatchStageRequest` (§3.5) | `OK`, `FAULT`, `TIMEOUT` | yes (via `stage_outcome`) |
| `initialize_spawn_configuration` | `SpawnRequest` (§3.6) | `OK`, `REJECT`, `FAULT`, `TIMEOUT` | yes (via `spawn_configuration` per §3.6) |
| `describe_compatibility` | empty payload | `OK`, `FAULT`, `TIMEOUT` | no |

### 3.5 `dispatch_stage` Contract

The `dispatch_stage` hook is the unified entry point for Stages 1 and 3 through 12 of the tick lifecycle. The engine calls it once per active stage per tick.

#### 3.5.1 StageId Enum (Normative)

| Value | Name | Description |
|-------|------|-------------|
| 1 | `ControlAuthorityAndInputRouting` | Resolve control authority swaps and input multiplexing (P-29, P-30). See §3.5.3 for Stage 1 semantics. |
| 3 | `TargetResolution` | Resolve intent-time spatial queries (P-09 through P-13) |
| 4 | `PreKinematic` | Apply movement modifiers — roots, slows, steering vectors (P-03, P-26) |
| 5 | `KinematicResolution` | Resolve all movement — teleport, displacement, attached, sweeps (P-01, P-02, P-06, P-07) |
| 6 | `PostKinematic` | Position-dependent consequences — clamping, proximity events, collision geometry (P-04, P-05, P-08, P-09, P-14, P-57, P-63) |
| 7 | `PreMitigation` | Combat interception — instance barriers, deferred ledger, CC immunity (P-19, P-22, P-62, P-65) |
| 8 | `DamageResolution` | Combat math — shields, mitigation, value modification, conversion (P-15, P-16, P-18, P-20, P-21, P-49) |
| 9 | `PostDamage` | Reactive hooks — on-hit, on-damage-received, event cloning (P-35, P-36, P-37, P-38, P-55, P-60, P-61). Deferred events MUST be queued for next tick. |
| 10 | `DeathCheck` | Life-phase transitions — floor clamping, bypass, multi-phase, on-death (P-23, P-24, P-25, P-39) |
| 11 | `StateUpdate` | Accumulators and timers — counters, charges, loadout swaps, pulse/delay timers (P-31, P-41, P-42, P-44, P-45, P-46, P-48, P-50). Deferred events MUST be queued for next tick. |
| 12 | `ObserverScopedPayloadEmission` | Downstream payload filtering — asymmetric rendering, suspension, group UI (P-52, P-53, P-54) |

Stage 2 (`IntentValidation`) is NOT dispatched via `dispatch_stage`. It uses the dedicated `validate_intent` hook, which has distinct reject/accept terminal outcome semantics.

StageId values 0, 2, and 13+ are reserved and MUST be rejected by the adapter.

#### 3.5.2 DispatchStageRequest Payload

```
DispatchStageRequest {
    stage_id:           u8,             // StageId enum value
    entity_batch:       list<EntityStageContext>,  // Entities with active work for this stage
    global_context:     GlobalStageContext,         // Tick-level shared state
}

EntityStageContext {
    entity_id:          string,         // Entity being evaluated
    ir_instructions:    list<object>,   // IR instructions tagged for this stage (from game image)
    ir_directives:      list<object>,   // Active cross-cutting directives for this entity
    entity_snapshot:    object,         // Current authoritative entity state
    ir_execution_binding_values: object, // Runtime values accumulated in IR binding slots from prior stages
}

GlobalStageContext {
    tick:               u64,            // Current authoritative tick
    topology_epoch:     u64,
    data_epoch:         u64,
    incoming_deferred_events: list<object>, // Deferred events arriving from the previous tick's Stage 9/11
}
```

The engine batches all entities with active IR instructions for the given stage into a single `dispatch_stage` call. The adapter processes the batch and returns a `stage_outcome` containing mutations, events, and deferred events for all entities in the batch.

#### 3.5.3 Stage 1 (ControlAuthorityAndInputRouting) Semantics

Stage 1 is dispatched via `dispatch_stage` like other stages. The adapter evaluates P-29 (Control Authority Swap) and P-30 (Input Multiplexing) directives and returns routing decisions as mutations. The engine then commits the routing changes before proceeding to `validate_intent` (Stage 2).

The adapter computes routing outcomes; the engine commits them. This preserves the declarative outcome model — the adapter never directly mutates engine input routing state.

### 3.6 `initialize_spawn_configuration` Contract

The `initialize_spawn_configuration` hook is called when the engine needs the adapter to initialize spawn-time configuration for a newly spawned entity (from P-32 Actor Spawning directives).

#### 3.6.1 SpawnRequest Payload

The Arbiter allocates the entity ID and R-Tree slot before calling the adapter. The `SpawnRequest` carries the engine-allocated ID so the adapter can reference it in the returned configuration.

```
SpawnRequest {
    entity_id:          string,         // Engine-allocated entity ID (Arbiter owns identity)
    archetype_id:       u32,            // Entity archetype from game image EntityDefinitions
    owner_entity_id:    string,         // Spawning entity
    spawn_position:     object,         // Requested spawn position (Vec2F)
    spawn_tick:         u64,            // Tick at which spawn was requested
}
```

#### 3.6.2 SpawnConfiguration Payload

The adapter returns game-specific configuration only. The `entity_id` is NOT included — it is engine-owned and was provided in the request.

```
SpawnConfiguration {
    initial_entity_state: object,       // Full initial entity state (stats, HP, abilities, soft state)
    ghost_movement_replication_cadence: u8,  // GhostMovementReplicationCadence enum (see below)
    lifetime_ticks:     u32 or null,    // Bounded lifetime (null = permanent until despawned)
}
```

`GhostMovementReplicationCadence` is a closed enum controlling how frequently the engine replicates this entity's movement-state Ghost updates to neighboring Arbiters. It does NOT affect the entity's actual movement speed or simulation behavior (which are governed by the entity's authoritative kinematic state).

| Value | Name | Description |
|-------|------|-------------|
| 0 | `None` | No position replication (e.g., placed zones, terrain walls) |
| 1 | `Low` | Infrequent updates (e.g., stationary NPCs with occasional repositioning) |
| 2 | `Standard` | Default update cadence (e.g., players, roaming monsters) |
| 3 | `High` | Frequent updates (e.g., projectiles, dash entities) |

Values 4+ are reserved and MUST be rejected.

The Arbiter combines its allocated `entity_id` with the adapter's `SpawnConfiguration` to commit the entity into the R-Tree. The spawned entity begins evaluation on the NEXT tick.

## 4. Enum and Extension Rules

1. `hook_name` and `status` are closed enums; unknown values are non-conformant.
2. `reject_code` values MAY include game-defined codes, but game-defined codes MUST use `GAME_` prefix.
3. Engine-defined boundary/fault codes MUST remain stable across adapter upgrades.
4. Unknown required fields in request or response envelopes MUST fail validation.

## 5. Startup Compatibility Negotiation

Startup admission MUST execute this deterministic handshake:
1. `ENGINE_HELLO`
2. `ADAPTER_HELLO`
3. `ADMISSION_DECISION`

### 5.1 `ENGINE_HELLO` Required Fields

1. `engine_identity`
2. `engine_version_semver`
3. `supported_adapter_api_majors` (non-empty set)
4. `supported_wire_schema_versions` (non-empty set)
5. `deployment_adapter_identity` (expected adapter identity for mesh)

### 5.2 `ADAPTER_HELLO` Required Fields

1. `adapter_identity`
2. `adapter_version_semver`
3. `adapter_api_major`
4. `supported_wire_schema_versions` (non-empty set)
5. `payload_schema_descriptors` where each descriptor contains:
   - `payload_type_id`
   - `schema_version`
   - `compatibility_mode` (`BACKWARD`, `FORWARD`, or `BIDIRECTIONAL`)

### 5.3 Admission Rules

1. `adapter_identity` MUST equal `deployment_adapter_identity`.
2. `adapter_api_major` MUST be in `supported_adapter_api_majors`.
3. `supported_wire_schema_versions` intersection MUST be non-empty.
4. Negotiated wire schema version MUST be deterministic (highest common numeric version).
5. If any required check fails, node admission MUST fail before runtime authority assignment.

### 5.4 Deterministic Negotiation Failure Codes

1. `ADAPTER_IDENTITY_MISMATCH`
2. `ADAPTER_API_MAJOR_UNSUPPORTED`
3. `WIRE_SCHEMA_NO_INTERSECTION`
4. `PAYLOAD_SCHEMA_DESCRIPTOR_INVALID`
5. `NEGOTIATION_TIMEOUT`
6. `MESH_VERSION_LINE_CONFLICT`

## 6. Mesh Version-Line Policy

1. A runtime mesh MUST contain exactly one adapter identity/version line.
2. Nodes presenting a different adapter identity or version line MUST be rejected from authority duties.
3. Mixed-version operation inside one active authority mesh is non-conformant.
4. Version-line transitions MUST follow `04-3-version-line-transition-contract.md`.
5. Upgrade strategy MUST ensure deterministic authority continuity (for example by generation cutover or drained replacement policy).

## 7. Conformance Requirements

A boundary implementation is conformant only if it passes:
1. request/response schema validation tests for all hooks
2. enum closed-set validation tests
3. success and failure startup negotiation tests
4. mixed-version-line rejection tests
5. replay/idempotency tests proving duplicate invocation does not mint duplicate mutation side effects
6. transition-admission integration tests proving only valid version lines enter authority duties
