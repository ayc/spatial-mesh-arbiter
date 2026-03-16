# AI Node Protocol Specification

This document is the canonical protocol specification for the gRPC boundary between team-written **AI Engines** and the platform-provided **AI Node Runtime**.

Canonical split:
- AI Node intelligence model, crash recovery semantics, and Commander Pattern are canonical in [NPC Architecture](02-npc-architecture.md).
- Internal mesh types (`ActionProposal`, `DownstreamPayload`, etc.) are canonical in [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md).
- Client-facing wire protocol (the player analog) is canonical in [Client-Edge Wire Protocol](../2-contracts-and-interfaces/01-client-edge-wire-protocol.md).

This document is normative. Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used in RFC-style.

---

## 1. Scope

### In scope
- gRPC service definition and Protobuf message contracts between AI Engine and AI Node Runtime.
- Session lifecycle: connection, NPC claiming/releasing, graceful disconnect.
- Action submission contract and rate limiting.
- World state delivery contract.
- Error model and retry guidance.
- Crash recovery from the AI Engine perspective.
- Conformance requirements for AI Engine implementations.

### Out of scope
- AI Engine decision logic, behavior tree design, or LLM integration patterns.
- AI Node Runtime internals (RUDP transport, Arbiter connection management, serialization pipeline).
- Arbiter simulation internals (tick loop, combat resolution, physics).
- AI Node Orchestrator assignment and load balancing algorithms.
- NPC gameplay taxonomy and interaction semantics (see [NPC and World Interaction](../3-gameplay-systems/04-npc-and-world-interaction.md)).

---

## 2. Architecture Overview

```
┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────┐
│     AI Engine        │       │   AI Node Runtime    │       │  Spatial Arbiter │
│  (Python/Node/etc.)  │       │   (platform sidecar) │       │   (60 Hz tick)   │
│                      │       │                      │       │                  │
│  Receives world state│ gRPC  │  AiNodeRegistration  │ RUDP  │  ActionProposal  │
│  Makes decisions     │◄─────►│  Redis heartbeat     │◄─────►│  DownstreamPayload│
│  Submits actions     │ Proto │  Protobuf ↔ internal │       │  TopologyUpdate  │
│                      │  buf  │  Session management  │       │                  │
└──────────────────────┘       └──────────────────────┘       └──────────────────┘
    ▲                                                              ▲
    │  Teams implement this                    Platform-internal   │
    │  (this spec defines the boundary)        (transparent)       │
```

**AI Node Runtime** is a platform-provided sidecar process. Teams implement only the **AI Engine** — a process that connects via gRPC, receives world state, makes decisions, and submits actions.

The AI Node Runtime handles:
- Registration with the Session Manager (`AiNodeRegistration`).
- Redis heartbeat maintenance (`SET edge:{ai_node_id}:heartbeat ALIVE EX 6`).
- RUDP transport to Arbiters (submitting `ActionProposal`, receiving `DownstreamPayload`).
- Protobuf ↔ internal type serialization (e.g., dequantizing `NetVec2` → `Vec2F` for the AI Engine).
- Session lifecycle management (`SessionMapping` creation/teardown).

The AI Engine handles:
- Connecting to the Runtime via gRPC.
- Receiving `WorldStateUpdate` messages and maintaining a local view of the game world.
- Making gameplay decisions (behavior trees, LLMs, scripted AI, etc.).
- Submitting actions via `ActionSubmission` and `MovementUpdate`.

**Deployment flexibility:** One AI Node Runtime process MAY host multiple AI Engines (multi-tenant), or operate one-to-one. This is a deployment configuration choice — the gRPC protocol is identical in both modes.

---

## 3. Transport and Connection

1. AI Engine and AI Node Runtime communicate over **gRPC (HTTP/2)**.
2. Datacenter traffic MUST use **mTLS**. The AI Node Runtime presents a platform-issued certificate; the AI Engine presents a service mesh identity certificate or shared secret.
3. AI Engine connects to the Runtime at a well-known address configured via environment variable (`AI_NODE_RUNTIME_ADDR`, default `localhost:9090`).
4. Authentication: mTLS certificate identity (preferred) or a shared secret passed in the `Connect` RPC metadata. The Runtime MUST reject unauthenticated connections.
5. gRPC keepalive pings MUST be enabled (default interval: `10s`, timeout: `5s`). The Runtime tracks engine liveness via keepalive acknowledgment and explicit `EngineHeartbeat` messages on the `GameStream`.
6. If the Runtime detects no keepalive response and no `EngineHeartbeat` for `30s`, it MUST treat the engine as dead and begin the crash recovery path (§10).

---

## 4. Protobuf Service Definition

The protocol defines a two-tier RPC design: **lifecycle RPCs** (unary request-response) for connection management and session operations, and a **game loop RPC** (bidirectional streaming) for the real-time hot path.

### 4.1 Service Definition

```protobuf
service AiNodeService {
    // --- Lifecycle RPCs (Unary) ---

    // Handshake and capability negotiation. Must be the first RPC called.
    rpc Connect(ConnectRequest) returns (ConnectResponse);

    // Engine requests control of a Named NPC by character_id.
    // Runtime validates against Session Manager and claims the SessionMapping.
    rpc ClaimNpc(ClaimNpcRequest) returns (ClaimNpcResponse);

    // Engine voluntarily releases an NPC session.
    // Runtime marks session for reassignment by the Orchestrator.
    rpc ReleaseNpc(ReleaseNpcRequest) returns (ReleaseNpcResponse);

    // Graceful shutdown. Runtime releases all sessions and begins
    // passive mode countdown for affected NPCs.
    rpc Disconnect(DisconnectRequest) returns (DisconnectResponse);

    // Observability: returns runtime health and throughput metrics.
    rpc RuntimeStatus(RuntimeStatusRequest) returns (RuntimeStatusResponse);

    // --- Game Loop RPC (Bidirectional Streaming) ---

    // Main hot-path channel for world state delivery and action submission.
    rpc GameStream(stream EngineMessage) returns (stream RuntimeMessage);
}
```

### 4.2 Upstream Messages (Engine → Runtime)

```protobuf
message EngineMessage {
    oneof payload {
        ActionSubmission action = 1;
        MovementUpdate movement = 2;
        CreepCommandSubmission creep_command = 3;
        EngineHeartbeat heartbeat = 4;
    }
}
```

### 4.3 Downstream Messages (Runtime → Engine)

```protobuf
message RuntimeMessage {
    oneof payload {
        WorldStateUpdate world_state = 1;
        ActionResult action_result = 2;
        CreepCommandResult creep_command_result = 3;
        NpcSessionEvent session_event = 4;
        TopologyNotice topology = 5;
        RuntimeHeartbeat heartbeat = 6;
    }
}
```

---

## 5. Message Reference

All Protobuf messages are defined below, organized by category. Each message includes explicit mapping notes to the corresponding internal mesh type from [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md).

### 5.1 Connection and Lifecycle Messages

```protobuf
message ConnectRequest {
    string engine_id = 1;                   // Unique identifier for this engine instance
    string specialization = 2;              // "BossEncounter", "SocialDialogue", or "General"
                                            // Maps to AiNodeSpecialization enum
    uint32 api_version = 3;                 // Protocol version this engine supports
}

message ConnectResponse {
    string assigned_engine_id = 1;          // Runtime-assigned canonical engine ID
    uint32 api_version = 2;                 // Negotiated protocol version
    uint32 heartbeat_interval_ms = 3;       // Required EngineHeartbeat cadence (default 5000)
    repeated string capabilities = 4;       // Runtime capability flags (e.g., "commander_pattern")
}

message ClaimNpcRequest {
    string character_id = 1;                // UUID of the Named NPC (design-time asset ID)
                                            // Maps to SessionMapping.character_id
}

message ClaimNpcResponse {
    bool success = 1;
    uint64 entity_id = 2;                   // Generational index (EntityID) allocated by Arbiter
    EntityState bootstrap_state = 3;        // Full initial state for the claimed NPC
    uint32 arbiter_id = 4;                  // Current host Arbiter (informational)
    string failure_reason = 5;              // Present when success=false
}

message ReleaseNpcRequest {
    uint64 entity_id = 1;                   // EntityID of the NPC to release
}

message ReleaseNpcResponse {
    bool success = 1;
    string failure_reason = 2;
}

message DisconnectRequest {
    string reason = 1;                      // Optional human-readable shutdown reason
}

message DisconnectResponse {
    uint32 released_npc_count = 1;          // Number of NPCs transitioned to passive mode
}
```

### 5.2 World State Messages

```protobuf
// Continuous world state delivery from the Runtime.
// Maps to DownstreamPayload::StateUpdate.
message WorldStateUpdate {
    uint64 shard_tick = 1;                  // Monotonic tick from the authoritative Arbiter
    uint32 data_epoch = 2;                  // Active SpellData/Balance version (informational)
    repeated EntityState entities = 3;      // All entities visible to the engine's NPCs
    bool is_bootstrap = 4;                  // True for the initial full-state delivery after
                                            // GameStream open or reconnection
}

// Per-entity state record delivered in WorldStateUpdate.
// Maps to EntityStateUpdate with dequantized coordinates.
// Positions are delivered as Vec2F (SimFixed pair) — the Runtime handles
// dequantization from the Arbiter's quantized NetVec2 wire format.
message EntityState {
    uint64 entity_id = 1;                   // EntityID (generational index)
    Vec2F position = 2;                     // Dequantized world position
    Vec2F velocity = 3;                     // Dequantized velocity vector
    int32 hp = 4;
    int32 max_hp = 5;
    int32 resource = 6;
    int32 max_resource = 7;
    repeated uint32 active_buff_ids = 8;    // Active effect IDs for decision-making
    bool is_dead = 9;
}

// Notifies engine of region/epoch changes.
// Maps to DownstreamPayload::TopologyUpdate.
message TopologyNotice {
    uint32 epoch = 1;                       // New topology epoch
    uint32 data_epoch = 2;                  // Active SpellData/Balance version
    uint32 arbiter_id = 3;                  // New host Arbiter (if changed)
}
```

### 5.3 Action Messages

```protobuf
// Discrete action submission from engine to Runtime.
// Maps to ActionProposal with the appropriate ActionPayload variant.
message ActionSubmission {
    uint64 npc_entity_id = 1;              // The NPC performing the action (must be claimed)
    uint64 action_id = 7;                  // REQUIRED engine-generated idempotency key; echoed by ActionResult
    oneof action {
        TargetedAbility targeted_ability = 2;
        GroundTargetedAbility ground_targeted_ability = 3;
        SpawnProjectile spawn_projectile = 4;
        Interact interact = 5;
        UseConsumable use_consumable = 6;
    }
}

// Maps to ActionPayload::Game(ArpgAction::TargetedAbility)
message TargetedAbility {
    uint64 target_id = 1;                  // EntityID of the target
    uint32 ability_id = 2;                 // Ability definition ID from SpellData
}

// Maps to ActionPayload::Game(ArpgAction::GroundTargetedAbility)
message GroundTargetedAbility {
    Vec2F destination = 1;                 // World-space target location
    uint32 ability_id = 2;
}

// Maps to ActionPayload::Game(ArpgAction::SpawnProjectile)
message SpawnProjectile {
    Vec2F direction = 1;                   // Projectile direction vector
    uint64 target_id = 2;                  // Optional homing target (0 = none)
    uint32 spell_id = 3;
}

// Maps to ActionPayload::Game(ArpgAction::Interact)
message Interact {
    uint64 target_entity = 1;
}

// Maps to ActionPayload::Game(ArpgAction::UseConsumable)
message UseConsumable {
    uint32 item_id = 1;
}

// Continuous position/velocity stream for NPC movement.
// Maps to ActionPayload::Engine(EngineAction::Movement).
// Coalesced by the Runtime under load (latest-per-entity semantics).
message MovementUpdate {
    uint64 npc_entity_id = 1;
    Vec2F position = 2;
    Vec2F velocity = 3;
    sfixed64 rotation = 4;                 // SimFixed rotation value
    uint64 tick = 5;                       // Must be monotonically increasing per entity
}

// Terminal outcome for a discrete ActionSubmission.
// Maps to DownstreamPayload::ActionApplied or DownstreamPayload::ActionFailed.
message ActionResult {
    uint64 npc_entity_id = 1;
    oneof outcome {
        ActionAccepted accepted = 2;
        ActionRejected rejected = 3;
    }
    uint64 action_id = 4;                  // Echoes ActionSubmission.action_id
}

message ActionAccepted {
    // Corresponds to DownstreamPayload::ActionApplied.
    // Terminal success — the action was applied by the Arbiter.
}

message ActionRejected {
    // Corresponds to DownstreamPayload::ActionFailed.
    string reason = 1;                     // Matches ActionFailed.reason strings:
                                           // "RateLimited", "OutOfRange", "OnCooldown",
                                           // "TargetDead", "InvalidTarget",
                                           // "Data Epoch Mismatch", etc.
}
```

### 5.4 Commander Pattern Messages

```protobuf
// Commander NPC issues behavioral overrides to Arbiter-Local creeps.
// Maps to ActionPayload::Game(ArpgAction::IssueCreepCommand).
// See NPC Architecture §2.6 for Commander Pattern semantics.
message CreepCommandSubmission {
    uint64 commander_entity_id = 1;        // Must be a claimed NPC with active CommanderBinding
    repeated uint64 target_creep_ids = 2;  // Subordinate entities to command
    uint64 command_id = 8;                 // REQUIRED engine-generated idempotency key; echoed by CreepCommandResult
    oneof directive {                       // Maps to CreepDirective enum
        MoveTo move_to = 3;
        AttackTarget attack_target = 4;
        HoldPosition hold_position = 5;
        Retreat retreat = 6;
        ClearOverride clear_override = 7;
    }
}

message MoveTo {
    Vec2F destination = 1;
}

message AttackTarget {
    uint64 target_id = 1;
}

message HoldPosition {}

message Retreat {
    Vec2F destination = 1;
}

message ClearOverride {}

message CreepCommandResult {
    uint64 commander_entity_id = 1;
    bool success = 2;
    string failure_reason = 3;             // "NoBinding", "OutOfRange", "CreepNotLocal",
                                           // "CommanderDead", "InvalidTarget"
    uint64 command_id = 4;                 // Echoes CreepCommandSubmission.command_id
}
```

### 5.5 Session Lifecycle Messages

```protobuf
// Pushed by Runtime on session lifecycle changes.
message NpcSessionEvent {
    uint64 entity_id = 1;
    oneof event {
        NpcClaimed claimed = 2;
        NpcReleased released = 3;
        NpcOrphaned orphaned = 4;
        NpcDespawned despawned = 5;
        NpcHandoffStarted handoff_started = 6;
        NpcHandoffCompleted handoff_completed = 7;
    }
}

message NpcClaimed {
    string character_id = 1;               // UUID of the claimed NPC
}

message NpcReleased {
    string reason = 1;                     // "voluntary", "orchestrator_reassignment"
}

message NpcOrphaned {
    // Runtime lost contact with the Arbiter or session was orphaned.
    // Engine MUST cease action submission for this entity.
    string reason = 1;
}

message NpcDespawned {
    // NPC was despawned (NPC_ORPHAN_TTL expired, or design-time despawn).
    // Entity ID is no longer valid.
}

message NpcHandoffStarted {
    uint32 new_arbiter_id = 1;             // Destination Arbiter
}

message NpcHandoffCompleted {
    uint32 new_arbiter_id = 1;             // New host Arbiter
}
```

### 5.6 Heartbeat and Observability Messages

```protobuf
message EngineHeartbeat {
    uint64 engine_tick = 1;                // Engine's local monotonic counter
}

message RuntimeHeartbeat {
    uint64 shard_tick = 1;                 // Latest known Arbiter tick
    uint32 connected_arbiters = 2;         // Number of Arbiter connections active
}

message RuntimeStatusRequest {}

message RuntimeStatusResponse {
    uint32 connected_engines = 1;
    uint32 claimed_npcs = 2;
    uint64 actions_per_second = 3;         // Discrete action throughput
    uint64 movements_per_second = 4;       // Movement update throughput
    uint64 errors_last_minute = 5;
    repeated ArbiterConnectionHealth arbiter_health = 6;
}

message ArbiterConnectionHealth {
    uint32 arbiter_id = 1;
    bool connected = 2;
    uint64 last_heartbeat_tick = 3;
    uint32 latency_ms = 4;
}
```

### 5.7 Common Types

```protobuf
// Two SimFixed values (I32F32) serialized as sfixed64 pairs.
// The AI Node Runtime dequantizes Arbiter NetVec2 → Vec2F before
// delivering to the engine; the engine always works in simulation precision.
message Vec2F {
    sfixed64 x = 1;                        // SimFixed (I32F32) as raw 64-bit
    sfixed64 y = 2;                        // SimFixed (I32F32) as raw 64-bit
}

// EntityID: uint64 generational index [32-bit Index | 32-bit Generation].
// Carried as plain uint64 fields throughout the protocol.

// Timestamp: uint64 shard tick. Monotonic within an Arbiter's timeline.
// Carried as plain uint64 fields (shard_tick, tick) throughout the protocol.
```

---

## 6. Session Lifecycle

### 6.1 Initial Connection and NPC Claiming

```
Engine                          Runtime                         Session Manager / Arbiter
  │                                │                                │
  │  Connect(engine_id,            │                                │
  │    specialization, api_version)│                                │
  │───────────────────────────────►│                                │
  │                                │                                │
  │  ConnectResponse(assigned_id,  │                                │
  │    capabilities, heartbeat_ms) │                                │
  │◄───────────────────────────────│                                │
  │                                │                                │
  │  ClaimNpc(character_id:        │                                │
  │    "boss-001")                 │                                │
  │───────────────────────────────►│  Validate + claim              │
  │                                │  SessionMapping                │
  │                                │───────────────────────────────►│
  │                                │                                │
  │                                │  SessionMapping confirmed      │
  │                                │  (entity_id, arbiter_id)       │
  │                                │◄───────────────────────────────│
  │                                │                                │
  │  ClaimNpcResponse(entity_id,   │                                │
  │    bootstrap_state, arbiter_id)│                                │
  │◄───────────────────────────────│                                │
  │                                │                                │
  │  Open GameStream               │                                │
  │◄══════════════════════════════►│                                │
  │                                │                                │
  │  WorldStateUpdate              │  DownstreamPayload::StateUpdate│
  │    (is_bootstrap=true)         │◄───────────────────────────────│
  │◄───────────────────────────────│                                │
  │                                │                                │
  │  WorldStateUpdate (continuous) │  DownstreamPayload (continuous)│
  │◄───────────────────────────────│◄───────────────────────────────│
  │                                │                                │
  │  ActionSubmission              │  ActionProposal                │
  │───────────────────────────────►│───────────────────────────────►│
  │                                │                                │
  │  ActionResult                  │  ActionApplied / ActionFailed  │
  │◄───────────────────────────────│◄───────────────────────────────│
```

### 6.2 Graceful Release

1. Engine calls `ReleaseNpc(entity_id)`.
2. Runtime marks the `SessionMapping` as released and notifies the Arbiter.
3. Arbiter transitions the NPC to **passive mode** (idle, zero velocity, non-aggressive — see [NPC Architecture §2.5](02-npc-architecture.md)).
4. Runtime pushes `NpcSessionEvent::Released` on the `GameStream`.
5. The AI Node Orchestrator MAY reassign the NPC to a different engine.

### 6.3 Graceful Disconnect

1. Engine calls `Disconnect(reason)`.
2. Runtime releases all claimed NPCs — each enters passive mode for up to `NPC_ORPHAN_TTL` (default: `120s`).
3. Runtime returns `DisconnectResponse` with count of released NPCs.
4. Engine closes the gRPC channel.

### 6.4 Multi-NPC Claiming

An engine MAY claim multiple NPCs by issuing sequential `ClaimNpc` calls. All claimed NPCs share the single `GameStream` — `WorldStateUpdate` includes entities visible to **all** of the engine's claimed NPCs, and upstream messages identify the acting NPC via `npc_entity_id`.

---

## 7. World State Delivery Contract

1. The Runtime pushes `WorldStateUpdate` at the cadence the Arbiter delivers `DownstreamPayload::StateUpdate`. The engine MUST NOT request a faster update rate — the Arbiter's tick loop is authoritative.
2. Each update includes a monotonic `shard_tick` for ordering. Engines MUST process updates in `shard_tick` order and discard stale updates (lower `shard_tick` than the latest processed).
3. Updates include all entities visible to the engine's NPCs, as determined by the Arbiter's interest management. Visibility is the Arbiter's decision — the engine has no control over which entities appear.
4. On `GameStream` open (initial or reconnection), the Runtime MUST deliver a **bootstrap** `WorldStateUpdate` (`is_bootstrap=true`) containing full authoritative state before sending subsequent delta updates.
5. `data_epoch` is included for informational purposes — engines can track balance version changes but do not load `SpellData` themselves. The Runtime handles epoch-aware proposal construction.

---

## 8. Action Submission Contract

### 8.1 Discrete Actions

- Engine sends `ActionSubmission` on the `GameStream`.
- `ActionSubmission.action_id` MUST be unique per `(npc_entity_id)` for at least a 10-second rolling window.
- Runtime translates to `ActionProposal` with appropriate `ActionPayload` variant, stamps `proposal_id`, `origin_tick`, `topology_epoch`, and `data_epoch`, then sends to the Arbiter via RUDP.
- Engine receives `ActionResult` with terminal outcome:
  - `Accepted` — the Arbiter applied the action (`DownstreamPayload::ActionApplied`).
  - `Rejected { reason }` — the Arbiter rejected the action (`DownstreamPayload::ActionFailed`).
- Runtime MUST echo `action_id` from submission to result, allowing deterministic correlation and deduplication after reconnect/retry.
- **Terminal outcome guarantee:** Every discrete `ActionSubmission` MUST produce exactly one `ActionResult`. The Runtime MUST NOT silently drop discrete actions.

### 8.2 Movement

- Engine sends `MovementUpdate` as a continuous stream on the `GameStream`.
- No individual terminal acknowledgments — movement is reconciled by periodic `WorldStateUpdate` snapshots.
- Under load, the Runtime MAY coalesce movement updates (latest-per-entity semantics), matching the `ActionPayload::Engine(EngineAction::Movement)` coalescing behavior defined in [Core Primitives §1.1.2](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md).

### 8.3 Rate Limiting

The AI Node Runtime enforces the same **per-entity `TokenBucket`** as player Edge Nodes (see [Core Primitives §1.1.3](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)):

- Over-budget discrete `ActionSubmission` messages receive `ActionResult::Rejected { reason: "RateLimited" }`.
- Over-budget `MovementUpdate` messages MAY be coalesced or dropped — no explicit rejection.

### 8.4 Ordering

- Actions are processed in stream order by the Runtime.
- Engine SHOULD NOT submit conflicting actions for the same entity within the same tick window (e.g., two `TargetedAbility` casts from the same NPC in rapid succession). The second will likely be rejected with `OnCooldown` or `RateLimited`.

---

## 9. Error Model

### 9.1 Transport Errors

gRPC status codes for transport-level failures:

| gRPC Status | Meaning | Engine behavior |
| :--- | :--- | :--- |
| `UNAVAILABLE` | Runtime is unreachable or shutting down | Reconnect with jittered backoff (§10) |
| `DEADLINE_EXCEEDED` | RPC timed out | Retry once; if repeated, reconnect |
| `UNAUTHENTICATED` | mTLS or shared secret rejected | Fix credentials; do not retry blindly |
| `PERMISSION_DENIED` | Engine not authorized for requested operation | Do not retry; check configuration |
| `INVALID_ARGUMENT` | Malformed request (e.g., bad `character_id` format) | Fix request; do not retry same payload |
| `NOT_FOUND` | NPC `character_id` unknown or not spawned | Do not retry immediately; wait for spawn |
| `ALREADY_EXISTS` | NPC already claimed by another engine | Do not retry; wait for release/reassignment |
| `FAILED_PRECONDITION` | Operation out of sequence (e.g., `ClaimNpc` before `Connect`) | Complete prerequisite steps first |

### 9.2 Application-Level Errors

Application-level errors are delivered via typed result messages on the `GameStream`:

| Error type | Delivery mechanism | Engine behavior |
| :--- | :--- | :--- |
| Action rejected | `ActionResult { action_id, Rejected { reason } }` | Log and adapt; do not retry same action in tight loop |
| Creep command rejected | `CreepCommandResult { command_id, success: false }` | Check binding validity and range |
| Session orphaned | `NpcSessionEvent::Orphaned` | Cease all action submission for the affected entity |
| Session despawned | `NpcSessionEvent::Despawned` | Remove entity from local state; do not reference entity ID |

`ActionResult.rejected.reason` strings match the existing `ActionFailed.reason` values from [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md):
- `"RateLimited"` — per-entity token bucket exhausted.
- `"OutOfRange"` — target beyond ability range.
- `"OnCooldown"` — ability not yet available.
- `"TargetDead"` — target entity is dead.
- `"InvalidTarget"` — target entity does not exist or is not targetable.
- `"Data Epoch Mismatch"` — stale balance version (Runtime handles epoch sync; this is rare).

---

## 10. Crash Recovery and Reconnection

### 10.1 AI Engine Crash

1. Runtime detects gRPC stream drop (keepalive failure or stream reset).
2. All NPCs claimed by the crashed engine enter **passive mode** — idle, zero velocity, non-aggressive (see [NPC Architecture §2.5](02-npc-architecture.md)).
3. Engine restarts and reconnects:
   - Calls `Connect` to re-establish the session.
   - Opens a new `GameStream`.
   - Calls `ClaimNpc` for each NPC it wants to reclaim.
4. Runtime delivers a bootstrap `WorldStateUpdate` (`is_bootstrap=true`) for reclaimed NPCs.
5. On successful reclamation, the Arbiter exits passive mode and resumes normal proposal processing for the entity.

**Recovery timeline:** Engines SHOULD reconnect within `NPC_ORPHAN_TTL` (default: `120s`). NPCs not reclaimed within this window are hard-despawned via `NpcLifecycleEvent::Despawned`.

### 10.2 AI Node Runtime Crash

1. Session Manager detects heartbeat expiry for the Runtime's `edge_node_id`.
2. The existing `EdgeNodeDead` pipeline fires (see [Core Concepts and Mesh §9.11](01-core-concepts-and-mesh.md)). All NPCs go passive.
3. Engine's gRPC channel fails — engine detects via keepalive timeout or stream error.
4. Engine reconnects to a different Runtime instance (or the restarted one) using the same `Connect` → `ClaimNpc` flow.
5. Hard despawn after `NPC_ORPHAN_TTL` if no Runtime reclaims the NPCs.

**Engine reconnection:** Engines SHOULD use jittered exponential backoff when reconnecting:
- Attempt 1 delay: `0.5–1.5s` random.
- Exponential growth with jitter.
- Max delay cap: `10s`.

### 10.3 Arbiter Handoff

1. Runtime receives `DownstreamPayload::TopologyUpdate` from the Arbiter.
2. Runtime pushes `TopologyNotice` to the engine on the `GameStream`.
3. Runtime pushes `NpcSessionEvent::HandoffStarted` for each affected NPC.
4. The Runtime transparently re-routes proposals to the new Arbiter. **The engine SHOULD NOT need to act** — handoff is transparent at the gRPC layer.
5. Once handoff completes, Runtime pushes `NpcSessionEvent::HandoffCompleted`.

Cross-reference: [NPC Architecture §2.5](02-npc-architecture.md) for passive mode semantics, [Core Concepts and Mesh §9.11](01-core-concepts-and-mesh.md) for the `EdgeNodeDead` pipeline.

---

## 11. Versioning and Compatibility

1. API version is negotiated in `ConnectRequest.api_version` / `ConnectResponse.api_version`. The Runtime selects the highest mutually supported version.
2. If no compatible version exists, the Runtime MUST reject with gRPC `FAILED_PRECONDITION` and a descriptive error message.
3. Protobuf forward/backward compatibility rules apply:
   - Field numbers MUST NOT be renumbered or reused.
   - Minor version changes MUST be additive-only (new fields, new `oneof` variants).
   - Major version changes MAY remove fields but MUST increment the API version.
4. `data_epoch` is included in `WorldStateUpdate` so engines can track balance version changes. Engines do not load `SpellData` — this field is informational for logging and observability.

---

## 12. Observability Contract

### 12.1 Runtime Metrics

The `RuntimeStatus` RPC returns operational metrics:
- Connected engine count.
- Claimed NPC count.
- Action throughput (discrete and movement, per second).
- Error rates (last minute).
- Per-Arbiter connection health (connected, latency, last heartbeat tick).

### 12.2 Standard gRPC Metrics

The Runtime MUST expose standard gRPC server metrics:
- Request count by RPC method and status code.
- Latency histogram by RPC method.
- Stream message rates (upstream and downstream) on `GameStream`.

### 12.3 Engine-Side Metrics

Engines SHOULD expose their own operational metrics for observability:
- Decision latency (time from `WorldStateUpdate` receipt to `ActionSubmission`).
- Action submission rate per NPC.
- Claimed NPC count.
- Reconnection count and duration.

The format and transport of engine-side metrics is the engine team's choice (Prometheus, StatsD, structured logs, etc.).

---

## 13. Conformance Checklist

1. AI Engine MUST complete `Connect` handshake before any other RPC.
2. AI Engine MUST `ClaimNpc` before submitting actions for that NPC.
3. AI Engine MUST handle `NpcSessionEvent::Orphaned` by ceasing action submission for the affected entity.
4. AI Engine MUST handle `ActionResult::Rejected` without retrying the same action in a tight loop.
5. `MovementUpdate.tick` values MUST be monotonically increasing per entity.
6. AI Engine SHOULD call `Disconnect` on graceful shutdown rather than dropping the connection.
7. AI Engine MUST NOT submit actions for entities it has not claimed.
8. `ActionSubmission.action_id` MUST be unique per `(npc_entity_id)` for at least a 10-second rolling window.
9. `CreepCommandSubmission.command_id` MUST be unique per `(commander_entity_id)` for at least a 10-second rolling window.
10. `CreepCommandSubmission` MUST target entities bound to the commander via `CommanderBinding`.
11. AI Engine MUST process `WorldStateUpdate` messages in `shard_tick` order.
12. AI Engine MUST handle `NpcSessionEvent::Despawned` by removing the entity from local state.
13. AI Engine MUST send `EngineHeartbeat` at the interval specified in `ConnectResponse.heartbeat_interval_ms`.

---

## 14. Cross-References

- NPC intelligence model, crash recovery, and Commander Pattern: [NPC Architecture](02-npc-architecture.md)
- Edge Node crash recovery pipeline: [Core Concepts and Mesh §9.11](01-core-concepts-and-mesh.md)
- Internal mesh types (`ActionProposal`, `DownstreamPayload`, `SessionMapping`, etc.): [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)
- AI Node and Commander types (`AiNodeRegistration`, `CreepDirective`, `CommanderBinding`): [Core Primitives §1.3](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)
- Client-Edge wire protocol (player analog): [Client-Edge Wire Protocol](../2-contracts-and-interfaces/01-client-edge-wire-protocol.md)
- NPC gameplay taxonomy and interaction semantics: [NPC and World Interaction](../3-gameplay-systems/04-npc-and-world-interaction.md)
