# Technical Blueprint: 2D Spatial Mesh Interfaces

This document serves as the technical companion to `Spatial_Mesh_Arbiter_Architecture_v2.md`. It defines the core data structures, message envelopes, and Actor interfaces required to implement a **2D Spatially-Aware Actor Model**.

---

## 1. Core Messaging Primitives

The system communicates exclusively via asynchronous message passing. The `ActionProposal` is the universal envelope used by Proxy Actors (Edge Nodes) to propose state changes to Spatial Actors (Mesh Arbiters).

### 1.1 Messaging Envelopes

To maintain a strict boundary between Edge Node requests and internal server operations, the engine uses four distinct message envelopes.

```rust
// --- Core Engine Types ---
// EntityID is a compact integer, not a UUID, to maximize CPU cache density during 60Hz 
// iterations and minimize intra-mesh UDP bandwidth. 
// We use a u64 (instead of u32) to implement a Generational Index pattern:
// [32-bit Index | 32-bit Generation]. This prevents the "ABA Problem", ensuring that delayed 
// network packets meant for a deleted entity don't accidentally strike a newly spawned entity 
// that happens to be reusing the same memory slot.
type EntityID = u64;

// --- Deterministic Physics Types ---
// As mandated by the architecture, standard floating-point math (f32/f64) is forbidden
// in the simulation loop to guarantee cross-CPU determinism during Hitless Handoffs.
//
// CRITICAL NUMERIC RULE:
// - Simulation math uses a WIDE fixed-point type (I32F32) to prevent overflow in squared
//   geometry operations (distance checks, Pythagorean extents, CCD sweeps).
// - Wire payloads remain compact 32-bit quantized integers to preserve UDP efficiency.
type SimFixed = I32F32;
// IMPORTANT: SimFixed is 64-bit on wire when serialized directly (unless explicitly quantized).

type NetCoord = i32;
struct NetVec2 {
    x: NetCoord,
    y: NetCoord,
}

struct Vec2F {
    x: SimFixed,
    y: SimFixed,
}

// Shared RUDP transport authentication wrapper for intra-mesh traffic.
// Applied by the network layer to MeshInternalEvent / ProjectileHandoff / MergeHandoff envelopes.
struct MeshAuthHeader {
    wire_schema_version: u16,
    auth_epoch: u32,      // Rotates with topology epoch (or sub-epoch key id)
    nonce: u64,           // Per-sender monotonic nonce
    hmac_tag: [u8; 32],   // HMAC-SHA256 over (header_without_tag || payload_bytes)
}

impl NetVec2 {
    // Convert compact wire coordinates to simulation precision at ingress.
    fn to_sim(&self, scale: SimFixed) -> Vec2F {
        Vec2F {
            x: SimFixed::from_num(self.x) * scale,
            y: SimFixed::from_num(self.y) * scale,
        }
    }
}

impl Vec2F {
    // Quantize simulation coordinates for compact wire transport at egress.
    fn to_net(&self, inv_scale: SimFixed) -> NetVec2 {
        NetVec2 {
            x: (self.x * inv_scale).to_num::<i32>(),
            y: (self.y * inv_scale).to_num::<i32>(),
        }
    }
}

// 1. External Envelope: From Edge Node to Host Arbiter
struct ActionProposal {
    proposal_id: UUID,       // CRITICAL: Used for deduplication during handoffs
    actor_id: EntityID,      // The player making the request
    origin_tick: u64,        // The Edge Node's tick when the action occurred (t0)
    topology_epoch: u32,     // The R-Tree map version this proposal was validated against
    data_epoch: u32,         // The SpellData/Balance version the Edge Node is currently using
    payload: ActionPayload,  
}

// 2. Internal Envelope: From Arbiter to Arbiter (or Projectile to Arbiter)
struct MeshInternalEvent {
    event_id: UUID,          // Used for internal relay deduplication
    source_arbiter_id: u32,  // Who generated this event?
    actor_id: Option<EntityID>, // Passed through for TargetedAbilities
    origin_tick: u64,        // Preserved from the Edge Node for ping tolerance math
    data_epoch: u32,         // Ensures cross-boundary projectiles use the correct version of SpellData
    payload: ActionPayload,  
}

// 3. Control Envelope: From Mesh Controller to Spatial Arbiter
enum ControllerCommand {
    ExecuteGlobalEvent {
        event_id: UUID,         // Prevents duplicate execution from TCP retries
        caster_id: EntityID,    // CRITICAL: Required for kill credit and PvP faction checks
        ability_id: u16,        // Used to trigger specific client-side VFX/SFX
        data_epoch: u32,        // SpellData/Balance version pinned at scheduling time
        context: CombatContext, // The raw damage and status effect payload
        epicenter: Vec2F,
        geometry: CollisionGeometry,      // Deterministic shape used for execution (not radius-only)
        target_filters: Option<Vec<u16>>, // Optional tag filters (e.g., TAG_STRUCTURE only)
        pulse_interval_ticks: Option<u32>,// Optional periodic behavior for zone-style global events
        duration_ticks: Option<u32>,      // Optional periodic behavior for zone-style global events
        execute_at_tick: u64,   // The synchronized Shard Tick for detonation
    },
    UpdateTopology {
        new_epoch: u32,
        cutover_tick: u64, // Deterministic tick for boundary shifts (Sliding)
        my_region: Rect,
        neighbors: Vec<NeighborRegion>, // Neighbors and their current dilation factors
    },
    SyncHeartbeat {
        controller_shard_tick: u64, // The authoritative global Metronome
    },
    PrepareDataEpoch {
        new_epoch: u32,
        asset_uri: String, // e.g., "s3://game-assets/balance/v1.02.fb"
        checksum: String,
    },
    BeginSplit {
        split_id: UUID,
        surrogate_arbiter_id: u32, // The currently overloaded Arbiter (A)
        child_b_id: u32,           // The newly spun-up shadow node (B)
        child_b_address: String,   // IP/Port of Child B for WAL streaming
        child_c_id: u32,           // The newly spun-up shadow node (C)
        child_c_address: String,   // IP/Port of Child C for WAL streaming
        region_b: Rect,            // The geometric half assigned to B
        region_c: Rect,            // The geometric half assigned to C
        new_epoch: u32,            // The topology epoch this split will introduce
    },
    CommitSplit {
        split_id: UUID,
        surrogate_arbiter_id: u32,
        cutover_tick: u64,         // Deterministic tick where A stops, and B/C take over
        new_epoch: u32,
    },
    FinalizeSplit {
        split_id: UUID,
        surrogate_arbiter_id: u32, // Tells the Surrogate it is safe to terminate/drain
    },
    BeginMerge {
        merge_id: UUID,
        winner_arbiter_id: u32,
        winner_address: String, // IP/Port where the Loser must stream its WAL
        loser_arbiter_id: u32,
        merged_region: Rect,
        cutover_tick: u64,
        new_epoch: u32,
    },
    CommitMerge {
        merge_id: UUID,
        winner_arbiter_id: u32,
        loser_arbiter_id: u32,
        cutover_tick: u64, // Deterministic authority flip tick
        new_epoch: u32,    // Applied at commit, not finalize
    },
    FinalizeMerge {
        merge_id: UUID,
        winner_arbiter_id: u32,
        loser_arbiter_id: u32,
        new_epoch: u32,    // Included for auditability; merge already committed
    }
}

// Configurable parameters for Kinematic Dilation (packaged in SpellData assets)
struct DilationConfig {
    safe_entity_threshold: u32,      // e.g., 300 - Below this, dilation is always 1.0
    critical_entity_threshold: u32,  // e.g., 1000 - At/above this, dilation is minimum_dilation_factor
    minimum_dilation_factor: SimFixed, // e.g., 0.2 (1/5th speed)
    curve_exponent: SimFixed,        // 1.0 = Linear, 2.0 = Quadratic
}

struct NeighborRegion {
    region: Rect,
    arbiter_id: u32,
    address: String, // e.g., "10.0.5.42:7000" (Direct UDP port for RUDP/Ghost traffic)
    dilation_factor: SimFixed, // Used for cross-border prediction
}

// 4. Downstream Envelope: From Arbiter to Proxy Actor (Edge Node)
// Defines the strictly quantized wire format for 60Hz state synchronization.
struct EntityStateUpdate {
    id: EntityID,
    position: NetVec2,
    velocity: NetVec2,
    hp: i32,
    resource: i32,
    active_buffs: Vec<u16>, // IDs of currently active effects for client UI/VFX rendering
    is_authoritative_owner: bool,
    is_ghost: bool,
}

// --- Stat Modifier System (Buff/Debuff Stat Layering) ---
// See RPG Mechanics § 1.3 for the full evaluation algorithm and examples.
// Modifiers are carried on ActiveStatusEffect and layered on top of the
// immutable base OffensiveStats/DefensiveStats at evaluation time (Pre-Roll
// for offense, Resolution for defense). The stored base structs are never mutated.

enum StatModifier {
    // Additive: base_value + flat_value (applied first, before multiplicative)
    FlatOffense { field: OffenseField, value: SimFixed },
    FlatDefense { field: DefenseField, value: SimFixed },

    // Multiplicative: base_value * multiplier (applied after all additives)
    MultOffense { field: OffenseField, multiplier: SimFixed },
    MultDefense { field: DefenseField, multiplier: SimFixed },

    // Appends a temporary conditional to the effective OffensiveStats at Pre-Roll time
    AddConditional { conditional: OffensiveCondition },
}

enum OffenseField {
    GlobalDamageMultiplier,
    CritChance,
    CritMultiplier,
    ArmorPenetrationPct,
    ArmorPenetrationFlat,
}

enum DefenseField {
    Resistance { damage_type: u8 },
    EvasionRating,
    BlockChance,
    ThornsDamage,
}

// --- Offensive Stats (Companion Struct — Immutable Base) ---
// Stored alongside SoftState in the Arbiter's per-entity storage, NOT inside SoftState.
// Compiled by Meta Services from equipment/inventory and pushed via UpdateEntityStats.
// The Arbiter never mutates this struct during gameplay; temporary buffs are layered
// on top via StatModifier entries on ActiveStatusEffect at cast time.
// See RPG Mechanics § 1.1 for gameplay context and § 1.3 for the modifier pattern.
struct OffensiveStats {
    global_damage_multiplier: SimFixed, // e.g., 1.2 (+20% all damage)
    crit_chance: SimFixed,              // 0.0 to 1.0
    crit_multiplier: SimFixed,          // e.g., 1.5 (150% damage)
    armor_penetration_pct: SimFixed,    // e.g., 0.3 (Ignores 30% of target armor)
    armor_penetration_flat: SimFixed,   // e.g., 10 (Ignores 10 flat armor)

    // Elemental Damage Conversions (Path of Exile style)
    // A 16-element array indexed by damage_type (matching the Damage Type Registry).
    // e.g., conversion_table[3] = 0.2 means "20% of base damage is converted to Fire"
    conversion_table: [SimFixed; 16],

    // Attacker-Owned Logic resolved during Phase 2 (e.g., Executioner's Axe)
    conditionals: Vec<OffensiveCondition>,
}

// --- Defensive Stats (Inside SoftState) ---
// Lives inside SoftState because it is read on every incoming hit during Phase 2 Resolution.
// See RPG Mechanics § 1.2 for gameplay context.
struct DefensiveStats {
    // A 16-element array mapping to the Damage Type Registry (e.g., 0=Slashing, 3=Fire).
    resistances: [SimFixed; 16],

    evasion_rating: SimFixed, // Chance to completely dodge non-True damage
    block_chance: SimFixed,   // Chance to reduce incoming damage by 50%
    thorns_damage: i32,       // Flat True damage reflected to melee attackers
}

// Internal Engine Representation of a running Buff/Debuff
struct ActiveStatusEffect {
    effect_id: u16,
    caster_id: EntityID,       // Preserved for kill credit if a DoT kills the target
    remaining_ticks: u32,
    next_pulse_tick: u64,      // The absolute Shard Tick when this effect should trigger its payload
    data_epoch: u32,           // The balance version this buff was applied under
    pulse_context: Option<CombatContext>, // The pre-rolled damage/healing payload to apply every pulse
    modifiers: Vec<StatModifier>, // Stat modifications active while this effect is alive
}

// Base attributes for physics and gameplay scaling
struct CoreStats {
    move_speed: SimFixed,
    weight: SimFixed,
    time_scale: SimFixed, // Gameplay Kinematic Dilation multiplier (e.g., 1.0 is normal, 0.5 is slow motion)
}

// Core Entity State (Authoritative)
struct SoftState {
    hp: i32,
    max_hp: i32,
    resource: i32,
    max_resource: i32,
    position: Vec2F,
    velocity: Vec2F,
    rotation: SimFixed,
    last_movement_tick: u64,
    stats: CoreStats,          // Move speed, weight, time scale
    defense: DefensiveStats,   // Resistances, evasion, block, thorns
    active_status_effects: Vec<ActiveStatusEffect>,
    is_invulnerable: bool,
    is_dead: bool,             // Flags the entity for cleanup/corpse transition
    resurrect_window_ticks: Option<u32>, // Time remaining for a healer to resurrect before hard despawn
    logout_fuse_ticks: Option<u32>, // Used for the 60-second wilderness logout mechanic
}

// Per-entity storage in the Arbiter's entity table.
// SoftState is the primary authoritative state. OffensiveStats is a companion struct
// compiled by Meta and read at cast time. Both are included in handoff serialization.
struct EntityRecord {
    soft_state: SoftState,
    offense: OffensiveStats,   // Immutable base from Meta; modified at evaluation time by buff modifiers
}

struct SoftStateSnapshot {
    tick: u64,
    entities: Vec<EntityStateUpdate>,
}

enum DownstreamPayload {
    StateUpdate {
        snapshot: SoftStateSnapshot,
        data_epoch: u32, // Authoritative active SpellData dictionary version
    },
    ActionApplied {
        proposal_id: UUID, // Terminal success for discrete actions (casts/interactions/consumables)
    },
    TopologyUpdate {
        epoch: u32,
        data_epoch: u32, // Authoritative active SpellData dictionary version
        my_region: Rect,
        my_dilation: SimFixed,
        neighbors: Vec<NeighborRegion>,
        redirect_arbiter_id: Option<u32>, // Immediate host override used during split/merge handoffs
    },
    ActionFailed {
        proposal_id: UUID,
        reason: String, // Triggers prediction rollback and cooldown refund at the Edge
    }
}

// 5. Inbound Meta Commands (From Meta Services to Spatial Arbiter via Redis Streams Event Bus)
enum MetaCommand {
    SpawnEntity {
        entity_id: EntityID,
        character_id: UUID,
        compiled_state: SoftState,       // Base stats, JRPG Save Zone coordinates pre-calculated by Meta
        compiled_offense: OffensiveStats, // Gear-compiled offensive attributes for Pre-Roll
    },
    // Pushes updated base stats when equipment changes (e.g., player equips a new weapon).
    // The Arbiter atomically overwrites the stored OffensiveStats and/or DefensiveStats.
    // Active buff modifiers on ActiveStatusEffect are unaffected — they layer on top
    // of the new base at the next evaluation (see RPG Mechanics § 1.3).
    UpdateEntityStats {
        entity_id: EntityID,
        offense: Option<OffensiveStats>,    // Updated if equipment changes affect offense
        defense: Option<DefensiveStats>,    // Updated if equipment changes affect defense
        core_stats: Option<CoreStats>,      // Updated if equipment changes affect move speed, weight, etc.
    },
    InitiateLogout {
        entity_id: EntityID,
        is_safe_zone: bool, // If true, instant despawn. If false, starts the 60s fuse.
    },
    ApplyCrossServerAura {
        entity_id: EntityID,
        buff_id: u16, // e.g., "Guild Buff" activated by a player on another server
    },
    // Notification from Session Manager that an Edge Node has crashed.
    // Arbiter should stop sending StateUpdates to the dead Edge Node and
    // start logout fuse timers for affected entities. See Core Architecture § 9.11.
    EdgeNodeDead {
        edge_node_id: u32,
        affected_entities: Vec<EntityID>,
    },
}

// 5b. Session Manager Types (Edge Node Lifecycle)
// The Session Manager is a Redis-backed registry that tracks active sessions,
// Edge Node liveness, and entity-to-Arbiter mappings. See Core Architecture § 9.11.

struct SessionMapping {
    character_id: UUID,
    entity_id: EntityID,
    arbiter_id: u32,
    edge_node_id: u32,
    status: SessionStatus,
    created_at: u64,       // Shard Tick when the session was established
}

enum SessionStatus {
    Active,    // Player is connected and playing
    Orphaned,  // Edge Node died; entity is alive, awaiting client reconnection
    Expired,   // Logout fuse expired; entity was despawned. Mapping retained for delayed reconnection.
}

struct EdgeNodeRegistration {
    edge_node_id: u32,
    address: String,         // Routable address for client WebSocket connections
    region: String,          // Geographic region (e.g., "us-east-1") for load balancer affinity
    capacity: u32,           // Max concurrent sessions this node can serve
    current_sessions: u32,   // Current active session count (updated periodically)
}

// 6. Upstream Control Envelope: From Spatial Arbiter to Mesh Controller
// Sent via high-frequency Heartbeat to allow the Controller to orchestrate 
// deterministic splits/merges based on actor density.
struct ArbiterHeartbeat {
    arbiter_id: u32,
    topology_epoch: u32,
    entity_count: u32,        // CRITICAL: Driving metric for rebalancing logic
    current_dilation: SimFixed,
    cpu_usage_pct: u8,        // Optional: Used for telemetry/provisioning, not rebalancing logic
}

// 6. Runtime Projectile Boundary Handoff (Arbiter <-> Arbiter, Reliable-UDP)
// This is a lightweight point-to-point protocol for normal boundary crossings.
// (Hitless split serialization still uses the surrogate WAL path.)
struct ProjectileSnapshot {
    projectile_id: UUID,
    owner_id: EntityID,
    target_id: Option<EntityID>,
    position: Vec2F,
    velocity: Vec2F,
    remaining_lifetime_ticks: u32,
    fuse_remaining_ticks: u32,
    pierce_remaining: u8,
    impact_sequence: u32,
    data_epoch: u32,
    damage_origin: u8, // DamageOrigin discriminant
    proc_depth: u8,
}

enum ProjectileHandoffMessage {
    Prepare {
        projectile_id: UUID,
        handoff_seq: u64,      // Monotonic per projectile
        from_arbiter_id: u32,
        to_arbiter_id: u32,
        topology_epoch: u32,
        source_tick: u64,
        commit_tick: u64,      // Future tick when authority flips
        snapshot: ProjectileSnapshot,
    },
    Ack {
        projectile_id: UUID,
        handoff_seq: u64,
        from_arbiter_id: u32,
        to_arbiter_id: u32,
        commit_tick: u64,
    },
    Commit {
        projectile_id: UUID,
        handoff_seq: u64,
        new_owner_arbiter_id: u32,
        commit_tick: u64,
    },
    Reject {
        projectile_id: UUID,
        handoff_seq: u64,
        reason: String, // e.g. "EpochMismatch", "StaleSequence"
    }
}

// 7. Sibling Merge Handoff (Arbiter <-> Arbiter, RUDP + WAL stream)
struct LedgerBucketSnapshot {
    bucket_index: u16, // 0..MAX_EVENT_AGE_TICKS-1
    bucket_tick: u64,  // Absolute tick represented by this ring bucket
    entries: Vec<(UUID, EntityID)>,
}

struct MergeSnapshot {
    merge_id: UUID,
    from_arbiter_id: u32,
    to_arbiter_id: u32,
    topology_epoch: u32,
    source_tick: u64,
    entities: Vec<(EntityID, EntityRecord)>, // Includes both SoftState and OffensiveStats
    projectiles: Vec<ProjectileSnapshot>,
    ghosts: Vec<GhostState2D>,
    pending_global_events: HashMap<UUID, ControllerCommand>,
    ledger_ring: Vec<LedgerBucketSnapshot>,
}

struct MergeWalDelta {
    merge_id: UUID,
    from_arbiter_id: u32,
    to_arbiter_id: u32,
    topology_epoch: u32,
    tick: u64,
    external: Vec<ActionProposal>,
    internal: Vec<MeshInternalEvent>,
}

enum MergeHandoffMessage {
    Prepare {
        merge_id: UUID,
        winner_arbiter_id: u32,
        loser_arbiter_id: u32,
        cutover_tick: u64,
        topology_epoch: u32,
    },
    SnapshotChunk {
        merge_id: UUID,
        chunk_seq: u32,
        is_last: bool,
        snapshot_chunk: MergeSnapshot,
    },
    WalDelta(MergeWalDelta),
    CatchupAck {
        merge_id: UUID,
        winner_arbiter_id: u32,
        loser_arbiter_id: u32,
        synced_to_tick: u64,
    },
    DrainComplete {
        merge_id: UUID,
        loser_arbiter_id: u32,
        winner_arbiter_id: u32,
    },
    Reject {
        merge_id: UUID,
        reason: String, // e.g., "EpochMismatch", "EntityIdCollision"
    },
}

// 8. Sibling Split Handoff (Arbiter <-> Arbiter, RUDP + WAL stream)
struct SplitSnapshot {
    split_id: UUID,
    from_arbiter_id: u32,
    to_arbiter_id: u32, // Specific child (B or C)
    topology_epoch: u32,
    source_tick: u64,
    // Only includes entities and projectiles that fall within the child's assigned region
    entities: Vec<(EntityID, EntityRecord)>,
    projectiles: Vec<ProjectileSnapshot>,
    ghosts: Vec<GhostState2D>,
    pending_global_events: HashMap<UUID, ControllerCommand>,
    ledger_ring: Vec<LedgerBucketSnapshot>,
}

struct SplitWalDelta {
    split_id: UUID,
    from_arbiter_id: u32,
    to_arbiter_id: u32,
    topology_epoch: u32,
    tick: u64,
    external: Vec<ActionProposal>,
    internal: Vec<MeshInternalEvent>,
}

enum SplitHandoffMessage {
    Prepare {
        split_id: UUID,
        surrogate_arbiter_id: u32,
        assigned_region: Rect,
        topology_epoch: u32,
    },
    SnapshotChunk {
        split_id: UUID,
        chunk_seq: u32,
        is_last: bool,
        snapshot_chunk: SplitSnapshot,
    },
    WalDelta(SplitWalDelta),
    CatchupAck {
        split_id: UUID,
        shadow_arbiter_id: u32,
        synced_to_tick: u64,
    },
    Reject {
        split_id: UUID,
        reason: String,
    },
}

// 9. Runtime Entity Boundary Handoff (Arbiter <-> Arbiter, Reliable-UDP)
// Used when a player walks across a static boundary, or when a sliding "Battle Node" 
// swallows or drops a player.
struct EntitySnapshot {
    entity_id: EntityID,
    state: SoftState,
    // Active modifiers and cooldowns are embedded within SoftState
}

enum EntityHandoffMessage {
    Prepare {
        entity_id: EntityID,
        handoff_seq: u64,
        from_arbiter_id: u32,
        to_arbiter_id: u32,
        topology_epoch: u32,
        source_tick: u64,
        commit_tick: u64, // Future tick when authority flips
        snapshot: EntitySnapshot,
    },
    Ack {
        entity_id: EntityID,
        handoff_seq: u64,
        from_arbiter_id: u32,
        to_arbiter_id: u32,
        commit_tick: u64,
    },
    Commit {
        entity_id: EntityID,
        handoff_seq: u64,
        new_owner_arbiter_id: u32,
        commit_tick: u64,
    },
    Reject {
        entity_id: EntityID,
        handoff_seq: u64,
        reason: String,
    },
}
```

### 1.1.1 Network Serialization Rules (UDP-Safe)
- **Compact Wire Coordinates:** Public internet and intra-mesh UDP packets serialize positions/velocities as `NetVec2` (`i32` per component).
- **Wide Simulation Math:** On packet ingress, Arbiters/Proxy Actors convert `NetVec2 -> Vec2F` (`I32F32`) and run all geometry/combat math in wide fixed-point.
- **64-bit Scalar Reality:** Any field typed `SimFixed` serializes as 64-bit when carried directly in RUDP payloads (e.g., `CombatContext`, geometry, dilation), by design.
- **Deterministic Conversion:** Coordinate scaling (`scale`, `inv_scale`) is shard-configured and constant for the entire session to avoid drift.
- **Version Guardrail:** Every packet header must include a `wire_schema_version`; unknown versions are rejected early with `ActionFailed`.
- **Intra-Mesh Auth:** All RUDP intra-mesh envelopes are wrapped with `MeshAuthHeader`; invalid HMAC/nonce/auth-epoch packets are dropped before queue ingress.

### 1.1.2 Proposal Lifecycle Invariant
- **Terminal Outcome Guarantee:** Every non-movement `proposal_id` must end in exactly one terminal downstream message: `ActionApplied` or `ActionFailed`.
- **No Silent Drops:** Queue pressure is resolved via explicit rejection (`ActionFailed`), never by unacknowledged packet eviction.
- **Movement Exception:** `ActionPayload::Movement` is a continuous stream and may be coalesced to latest-per-entity under load; it is reconciled by periodic `StateUpdate` instead of per-proposal terminal acks.

### 1.1.3 Ingress Fairness Guard
- **Per-Entity Token Bucket:** Every inbound `ActionProposal` must pass a lightweight per-entity token bucket before entering `external_inbox`.
- **Abuse Isolation:** A spammy/buggy session can only exhaust its own bucket and cannot monopolize Arbiter queue capacity for other entities.
- **Deterministic Failure Contract:** Over-budget non-movement proposals are rejected immediately with `ActionFailed { reason: "Rate Limited" }`; movement proposals may be dropped/coalesced.

### 1.1.4 Terminal Authority & Border-Targeted Contract
- **Single Terminal Owner:** Only the Arbiter that owns the proposing `actor_id` for a given `proposal_id` may emit terminal `ActionApplied` or `ActionFailed`.
- **Relay Rule:** Neighbor Arbiters processing relayed `MeshInternalEvent` copies must never emit terminal client outcomes for the original `proposal_id`.
- **Cross-Border Target-Locked Rule:** If the target is a local Ghost, the actor-owner Arbiter performs pre-roll (`CombatContext`) and relays `InternalPreparedHit` to the target-owner Arbiter. The target-owner applies mitigation/state mutation.
- **Ack Semantics:** For cross-border target-locked casts, `ActionApplied` means the proposal was accepted and forwarded under valid local checks. It is not a guaranteed damage-commit on the remote owner.
- **No Split-Brain Outcomes:** The same proposal must never simultaneously produce `ActionFailed` on actor-owner and damage application on target-owner.

### 1.1.5 Data Epoch Handshake
- **Epoch Match:** Proposal `data_epoch` equals Arbiter `current_data_epoch` -> process normally.
- **Proposal Stale:** Proposal `data_epoch` older than Arbiter -> immediate `ActionFailed { reason: "Data Epoch Mismatch" }` for non-movement proposals.
- **Arbiter Behind:** Proposal `data_epoch` newer than Arbiter -> attempt epoch activation; if unavailable, buffer with timeout bounded by `MAX_EVENT_AGE_TICKS`, then fail deterministically.
- **Downstream Sync Contract:** `StateUpdate` and `TopologyUpdate` include authoritative `data_epoch` so Edge Nodes can refresh dictionaries before submitting new proposals.

### 1.2 ActionPayload (Polymorphic Logic)
```rust
// Strictly typed logic blocks that the engine knows how to resolve in Phase 2
enum OffensiveCondition {
    // e.g., Executioner's Ring
    MultiplyDamageIfTargetHpBelow { threshold_pct: SimFixed, multiplier: SimFixed },
    
    // e.g., Giant Slayer (Bonus damage based on max HP differences)
    // Note: We pre-calculate the attacker's Max HP in Phase 1 and pass it over!
    MultiplyDamageIfTargetMaxHpGreater { attacker_max_hp: i32, mult_per_1000: SimFixed },
    
    // e.g., "Deals 5% Target Max HP" (If triggered by an item proc, not a spell)
    AddDamageTargetMaxHpPct { pct_as_damage: SimFixed, damage_type: u8 },
}

// Identifies how damage was produced so reactive systems can avoid recursive proc chains.
enum DamageOrigin {
    DirectCast,      // Player/boss initiated ability or projectile hit
    ReactiveProc,    // Triggered by another combat event (Thorns, On-Hit proc, etc.)
    PeriodicEffect,  // DoT/HoT tick
    Environmental,   // Trap, map hazard, objective pulse
}

// The raw potential of an attack, before target mitigation is applied.
// Provides the framework for deep ARPG/MOBA mechanics (Armor, Distance Falloff, Weight)
struct CombatContext {
    base_damage: u32,
    damage_type: u8, // Maps to a specific subtype (e.g., 0: Slashing, 3: Fire, 100: Healing)
    
    // Physical/Kinetic impact
    knockback_force: SimFixed,
    
    // Deep ARPG Modifiers passed over the network
    armor_penetration_pct: SimFixed,
    armor_penetration_flat: SimFixed,
    is_critical_strike: bool,

    status_effect_id: Option<u16>,

    // Proc safety metadata:
    // - damage_origin gates whether reactive defenses are allowed to trigger.
    // - proc_depth provides a hard deterministic recursion ceiling.
    damage_origin: DamageOrigin,
    proc_depth: u8,
    
    // Phase 2 directives passed from the Attacker's item/buff state
    // ArrayVec keeps the struct stack-allocated to prevent heap allocations in the 60Hz loop
    conditionals: ArrayVec<OffensiveCondition, 4>,
}

// Describes the physical shape of an attack for precise Ghost drift validation
enum CollisionGeometry {
    Circle { radius: SimFixed },
    Cone { radius: SimFixed, angle_degrees: SimFixed, direction: Vec2F },
    Box { width: SimFixed, length: SimFixed, rotation: SimFixed },
}

impl CollisionGeometry {
    // Calculates the absolute furthest reach of the shape from the epicenter.
    // Used to determine if a spell is massive enough to require Global Event Escalation.
    fn get_max_extent(&self) -> SimFixed {
        match self {
            Self::Circle { radius } => *radius,
            Self::Cone { radius, .. } => *radius,
            Self::Box { width, length, .. } => {
                // Compute box diagonal with wide intermediates to prevent overflow:
                // diag = sqrt((w/2)^2 + (l/2)^2)
                let half_w = *width / SimFixed::from_num(2);
                let half_l = *length / SimFixed::from_num(2);
                let hw_bits = i128::from(half_w.to_bits());
                let hl_bits = i128::from(half_l.to_bits());
                let sum_sq = (hw_bits * hw_bits) + (hl_bits * hl_bits);
                let diag_bits = fixed_sqrt_i128(sum_sq); // Integer sqrt in fixed-point bit space
                SimFixed::from_bits(diag_bits as i64)
            }
        }
    }

    // Allows a safe "Favor the Shooter" margin for dropped UDP packets without 
    // degrading directional shapes (like Cones) into generic Circles.
    fn is_inside_with_tolerance(&self, target: Vec2F, epicenter: Vec2F, tolerance: SimFixed) -> bool {
        match self {
            Self::Circle { radius } => target.distance_to(epicenter) <= (radius + tolerance),
            Self::Cone { radius, angle_degrees, direction } => {
                // Direction must still match, we only forgive the max distance edge
                target.is_within_angle(epicenter, *direction, *angle_degrees) 
                && target.distance_to(epicenter) <= (radius + tolerance)
            },
            Self::Box { width, length, rotation } => {
                target.is_inside_expanded_box(epicenter, *width, *length, *rotation, tolerance)
            }
        }
    }
}

// The Specific Game Mechanics (Polymorphic Payload)
// Note: Most variants may come from Edge Node proposals or internal relays.
// InternalPreparedHit is internal-only and must never be accepted from Edge Node ingress.
enum ActionPayload {
    // Continuous Inputs
    Movement { 
        position: Vec2F, 
        velocity: Vec2F, 
        rotation: SimFixed 
    },
    
    // Combat (Target-Locked / Instant)
    TargetedAbility { 
        target_id: EntityID, 
        ability_id: u16,
    },
    
    // Combat (Ground-Targeted / AoEs like Meteor or Blizzard)
    GroundTargetedAbility {
        destination: Vec2F,
        ability_id: u16,
    },
    
    // Combat (Target-Favoring Resolution / Skillshots)
    // Content note: "SpawnZone" is an asset/schema alias compiled into SpawnProjectile
    // with zero velocity + pulse/duration mechanics.
    SpawnProjectile { 
        direction: Vec2F, 
        target_id: Option<EntityID>, // Used for Homing Missiles or Attached Auras
        spell_id: u16 
    },

    // Combat (Cross-Boundary Ghost Interactions)
    ImpactEvent {
        impact_id: UUID, 
        target_ids: Vec<EntityID>, 
        epicenter: Vec2F, 
        geometry: CollisionGeometry, // Used for final, precise mathematical validation of ghost impacts
        impact_tick: u64,
        context: CombatContext, 
    },

    // Combat (Internal-Only / Already Authoritative)
    // Used for reactive procs like Thorns where combat context is already finalized.
    InternalPreparedHit {
        target_id: EntityID,
        context: CombatContext,
    },
    
    // Interactions
    UseConsumable { item_id: u16 },
    Interact { target_entity: EntityID },

    // Internal Reliability Control (Ghost Repair Path)
    RequestGhostCorrection {
        entity_id: EntityID,
        requester_arbiter_id: u32,
    },
}
```

---

## 2. Layer 1: The Edge Node (Proxy Actor)

The Proxy Actor maintains the client connection, manages local prediction (Soft State), and translates raw inputs into `ActionProposals`.

### 2.1 Interface
```rust
// --- Edge Node / Meta Services Dispatch Envelopes ---

// The multiplexed envelope sent from the physical game client to the Edge Node
enum ClientMessage {
    Simulation(RawInput), // High-frequency movement, aiming, ability clicks
    Meta(MetaRequest),    // Low-frequency chat, inventory, grouping
}

// Low-frequency, strongly consistent interactions forwarded to Tier 2
enum MetaRequest {
    SendChatMessage { channel: ChatChannel, text: String },
    MoveInventoryItem { from_slot: u8, to_slot: u8 },
    InviteToParty { target_character_name: String },
    RequestLogout, // Triggers the Section 9.5 logout handshake
}

enum MetaResponse {
    ChatReceived { sender: String, text: String },
    InventorySync(InventorySnapshot),
    PartyInviteReceived { from_name: String },
    SystemAlert { message: String },
}

struct ProxyActor {
    session_id: UUID,        // Secure, unguessable network token for the client connection
    character_id: UUID,      // The persistent DB identity (injected by Auth, trusted by Meta)
    entity_id: EntityID,     // The fast, compact u64 used for physics and mesh routing
    client_connection: UdpSocket,
    
    // --- The Dual-Routing Destinations ---
    // 1. Spatial Mesh (60Hz, UDP, Ephemeral)
    authoritative_mesh_node: IPAddress, 
    // 2. Meta Services (Async, gRPC/TCP, Persistent)
    meta_rpc_client: RpcClient, 
    
    // Time Synchronization & Deduplication
    latest_mesh_tick: u64,
    predicted_tick: u64,
    last_known_authoritative_tick: HashMap<EntityID, u64>,
    
    // Spatial Awareness (Temporal Swamp Prediction)
    current_topology_epoch: u32,
    my_region: Rect,
    my_dilation: SimFixed,
    neighbor_regions: Vec<NeighborRegion>, // Used to smoothly predict cross-border deceleration
    
    current_data_epoch: u32,
    
    // Input Buffer
    pending_inputs: Vec<RawInput>,

    // Proposal lifecycle tracking for deterministic rollback under packet loss/saturation.
    pending_proposals: HashMap<UUID, PendingProposal>,
}

enum PendingProposalKind {
    Discrete, // Casts, interactions, consumables
}

struct PendingProposal {
    kind: PendingProposalKind,
    submitted_at_tick: u64,
}

impl ProxyActor {
    const PROPOSAL_TIMEOUT_TICKS: u64 = 18; // ~300ms at 60Hz

    // 1. Asynchronous Network Receiver: Runs as fast as the client sends data
    // Acts as the "API Gateway" routing layer
    fn on_client_message(&mut self, msg: ClientMessage) {
        match msg {
            ClientMessage::Simulation(input) => {
                // Buffer high-frequency physics inputs for the 60Hz tick
                self.pending_inputs.push(input);
            },
            ClientMessage::Meta(request) => {
                // Instantly forward to Meta Services, bypassing the Arbiter.
                // SECURITY: The Edge Node forcibly injects the trusted character_id.
                // The client cannot spoof who is sending the chat or inventory move.
                self.meta_rpc_client.send_async(self.character_id, request);
            }
        }
    }

    // 1.b Asynchronous Meta Response Handler
    fn on_meta_response_received(&mut self, response: MetaResponse) {
        // Forward back to the physical client UI
        self.send_to_client_reliable(response);
    }

    // 2. Local Simulation Loop: Runs strictly at 60Hz to maintain parity with the Mesh Arbiter
    fn tick(&mut self) {
        self.predicted_tick += 1;
        
        // Aggregate all inputs received since the last 16.6ms frame
        let aggregated_input = aggregate_inputs(self.pending_inputs.drain(..).collect());

        let predicted_state = self.run_local_physics(aggregated_input.clone());
        self.send_to_client(predicted_state); 
        
        if aggregated_input.buttons.contains(FIRE) {
            let proposal = ActionProposal {
                proposal_id: generate_uuid(),
                actor_id: self.entity_id, 
                origin_tick: self.predicted_tick, // Now safely synchronized to the 60Hz baseline
                topology_epoch: self.current_topology_epoch,
                data_epoch: self.current_data_epoch,
                payload: ActionPayload::TargetedAbility { 
                    target_id: aggregated_input.target_id, 
                    ability_id: aggregated_input.selected_ability,
                }
            };
            self.pending_proposals.insert(
                proposal.proposal_id,
                PendingProposal { kind: PendingProposalKind::Discrete, submitted_at_tick: self.predicted_tick }
            );
            self.send_to_mesh(&self.authoritative_mesh_node, proposal);
        }

        // Failsafe: do not let client prediction hang forever if no terminal response arrives.
        let mut timed_out = Vec::new();
        for (proposal_id, pending) in &self.pending_proposals {
            if matches!(pending.kind, PendingProposalKind::Discrete)
                && self.predicted_tick.saturating_sub(pending.submitted_at_tick) >= Self::PROPOSAL_TIMEOUT_TICKS
            {
                timed_out.push(*proposal_id);
            }
        }
        for proposal_id in timed_out {
            self.pending_proposals.remove(&proposal_id);
            self.rollback_specific_action(proposal_id);
            self.send_ui_alert_to_client("Action Timeout (No Ack)".to_string());
        }
    }

    fn on_downstream_payload_received(&mut self, payload: DownstreamPayload) {
        match payload {
            DownstreamPayload::StateUpdate { snapshot: mesh_state, data_epoch } => {
                if data_epoch > self.current_data_epoch {
                    self.current_data_epoch = data_epoch;
                }
                self.latest_mesh_tick = cmp::max(self.latest_mesh_tick, mesh_state.tick);
                
                for entity_update in mesh_state.entities {
                    let last_auth_tick = self.last_known_authoritative_tick.get(&entity_update.id).unwrap_or(&0);

                    if entity_update.is_authoritative_owner {
                        if mesh_state.tick > *last_auth_tick {
                            self.reconcile_entity(entity_update);
                            self.last_known_authoritative_tick.insert(entity_update.id, mesh_state.tick);
                        }
                    } else if entity_update.is_ghost {
                        if mesh_state.tick > *last_auth_tick {
                            self.reconcile_entity(entity_update);
                        }
                    }
                }
                
                if self.diverges_from_prediction(self.get_my_player_state()) {
                    self.trigger_client_rollback(self.get_my_player_state());
                }
            },
            DownstreamPayload::ActionApplied { proposal_id } => {
                self.pending_proposals.remove(&proposal_id);
            },
            DownstreamPayload::TopologyUpdate { epoch, data_epoch, my_region, my_dilation, neighbors, redirect_arbiter_id } => {
                self.current_topology_epoch = epoch;
                if data_epoch > self.current_data_epoch {
                    self.current_data_epoch = data_epoch;
                }
                self.my_region = my_region;
                self.my_dilation = my_dilation;
                self.neighbor_regions = neighbors;
                if let Some(arbiter_id) = redirect_arbiter_id {
                    self.authoritative_mesh_node = self.resolve_arbiter_address(arbiter_id);
                }
            },
            DownstreamPayload::ActionFailed { proposal_id, reason } => {
                // Instantly refund cooldowns/resources and rollback prediction
                self.pending_proposals.remove(&proposal_id);
                self.rollback_specific_action(proposal_id);
                self.send_ui_alert_to_client(reason);
            }
        }
    }
}
```

---

## 3. Layer 2: The Mesh Arbiter (Spatial Actor)

The Spatial Actor is a single-threaded, lock-free, 60Hz deterministic simulation loop. 

### 3.1 Interface
```rust
// Defines how long the engine remembers events (60 ticks = 1.0 second).
const MAX_EVENT_AGE_TICKS: u64 = 60;

// Configuration structs replacing hardcoded magic numbers
// (See Engine_Configuration_Registry.md for detailed definitions)
struct BootConfig {
    proposal_bucket_capacity: u16,
    proposal_bucket_refill_per_tick: u16,
    max_event_age_ticks: u64,
}

struct LiveConfig {
    combat_radius: SimFixed,
    visible_radius: SimFixed,
    keyframe_interval_ticks: u64,
    ghost_anomaly_margin: SimFixed,
    ghost_degraded_ttl_ticks: u64,
    ghost_render_ttl_ticks: u64,
    dilation: DilationConfig,
}

enum GhostMovementClass {
    Normal,
    HighSpeed, // Dash/leap style displacement
    Teleport,  // Instant large displacement
}

enum GhostQuality {
    Healthy,
    Degraded, // Frozen/clamped until reliable correction arrives or TTL expires
}

struct GhostState2D {
    entity_id: EntityID,
    authoritative_arbiter_id: u32,
    position: Vec2F,
    velocity: Vec2F,
    last_valid_position: Vec2F,
    last_update_tick: u64,
    movement_class: GhostMovementClass,
    quality: GhostQuality,
    degraded_until_tick: u64,
}

struct GhostUpdate {
    entity_id: EntityID,
    source_arbiter_id: u32,
    source_tick: u64,
    position: Vec2F,
    velocity: Vec2F,
    movement_class: GhostMovementClass,
    is_keyframe: bool,
}

struct TokenBucket {
    tokens: u16,
    last_refill_tick: u64,
}

impl TokenBucket {
    fn new(now_tick: u64) -> Self {
        Self {
            tokens: PROPOSAL_BUCKET_CAPACITY,
            last_refill_tick: now_tick,
        }
    }

    fn try_consume(&mut self, now_tick: u64, cost: u16) -> bool {
        let elapsed = now_tick.saturating_sub(self.last_refill_tick);
        if elapsed > 0 {
            let refill = (elapsed as u128) * (PROPOSAL_BUCKET_REFILL_PER_TICK as u128);
            let replenished = (self.tokens as u128 + refill).min(PROPOSAL_BUCKET_CAPACITY as u128);
            self.tokens = replenished as u16;
            self.last_refill_tick = now_tick;
        }

        if self.tokens < cost { return false; }
        self.tokens -= cost;
        true
    }
}

enum MergeRole {
    Winner,
    Loser,
}

enum MergePhase {
    Streaming,
    Catchup,
    AwaitingCommit,
    ForwardingOnly,
}

struct MergeState {
    merge_id: UUID,
    role: MergeRole,
    peer_arbiter_id: u32,
    cutover_tick: u64,
    target_epoch: u32,
    phase: MergePhase,
    forwarding_until_tick: u64,
}

struct SpatialActor {
    arbiter_id: u32,
    topology_epoch: u32,
    current_data_epoch: u32, // The version of the SpellData dictionary currently loaded in memory
    rtree_depth: u8,
    region_bounds: Rect,
    current_tick: u64,
    
    // The "Temporal Swamp" Factor (0.0 to 1.0)
    // 1.0 = Full speed (60Hz resolution)
    // 0.2 = 1/5th speed (Physics resolution every 5th tick)
    dilation_factor: SimFixed, 
    
    // Bounded Queues (Network layer pushes here. Must have explicit capacity limits 
    // to prevent OOM failure modes during blackhole density events).
    external_inbox: BoundedQueue<ActionProposal>,
    internal_inbox: BoundedQueue<MeshInternalEvent>,
    controller_inbox: BoundedQueue<ControllerCommand>,
    
    // Future Event Scheduler
    pending_global_events: HashMap<UUID, ControllerCommand>,
    
    // Stale Buffer: Holds (Proposal, local_arrival_tick) to measure timeout safely.
    // Must be a BoundedQueue to prevent OOM vulnerabilities during prolonged Mesh Controller 
    // outages. Sized to handle spikes based on a ~400 entity capacity limit.
    stale_proposals_buffer: BoundedQueue<(ActionProposal, u64)>,

    entities: HashMap<EntityID, SoftState>, 
    ghost_entities: HashMap<EntityID, GhostState2D>, 
    ghost_grid: SpatialIndex<EntityID>, // Mirrors ghost positions for cheap downstream visibility queries
    proposal_buckets: HashMap<EntityID, TokenBucket>, // Per-entity fairness guard on ingress
    merge_state: Option<MergeState>,
    processed_proposals: LruCache<UUID, bool>, 
    
    // Event Idempotency Ledger: Prevents double-damage from delayed or duplicate relays.
    // Dynamically sized to the max event age to survive delayed packets and Hitless Handoffs.
    event_idempotency_ledger: [HashSet<(UUID, EntityID)>; MAX_EVENT_AGE_TICKS as usize], 
}

impl SpatialActor {
    fn verify_mesh_auth<T>(&self, header: &MeshAuthHeader, payload: &T) -> bool {
        // Pseudocode:
        // 1) validate auth_epoch/key-id is currently accepted
        // 2) reject nonce replay for this sender
        // 3) recompute HMAC over canonical payload bytes and compare constant-time
        verify_hmac_and_nonce(header, payload)
    }

    // Called by the RUDP network layer for authenticated intra-mesh events.
    fn on_internal_event_rudp(&mut self, header: MeshAuthHeader, event: MeshInternalEvent) {
        if !self.verify_mesh_auth(&header, &event) { return; }
        self.internal_inbox.push_back(event);
    }

    // Called by the network ingress layer for each proposal packet before queueing.
    fn on_external_proposal_received(&mut self, proposal: ActionProposal) {
        // Zero-trust ingress: only intent-level payloads are valid from Edge Nodes.
        if !matches!(
            &proposal.payload,
            ActionPayload::Movement { .. }
                | ActionPayload::TargetedAbility { .. }
                | ActionPayload::GroundTargetedAbility { .. }
                | ActionPayload::SpawnProjectile { .. }
                | ActionPayload::UseConsumable { .. }
                | ActionPayload::Interact { .. }
        ) {
            self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                proposal_id: proposal.proposal_id,
                reason: "Invalid Payload Type".to_string(),
            });
            return;
        }

        let cost = if matches!(&proposal.payload, ActionPayload::Movement { .. }) {
            PROPOSAL_COST_MOVEMENT
        } else {
            PROPOSAL_COST_DISCRETE
        };

        let bucket = self.proposal_buckets
            .entry(proposal.actor_id)
            .or_insert(TokenBucket::new(self.current_tick));

        if !bucket.try_consume(self.current_tick, cost) {
            if !matches!(&proposal.payload, ActionPayload::Movement { .. }) {
                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                    proposal_id: proposal.proposal_id,
                    reason: "Rate Limited".to_string(),
                });
            }
            return;
        }

        if self.external_inbox.is_full() {
            if !matches!(&proposal.payload, ActionPayload::Movement { .. }) {
                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                    proposal_id: proposal.proposal_id,
                    reason: "Arbiter Queue Saturated".to_string(),
                });
            }
            return;
        }

        self.external_inbox.push_back(proposal);
    }

    // Core Loop: Runs strictly every 16.6ms (60Hz)
    fn tick(&mut self) {
        self.current_tick += 1;
        
        // 0. O(1) Ledger Cleanup
        let current_bucket = (self.current_tick % MAX_EVENT_AGE_TICKS) as usize;
        self.event_idempotency_ledger[current_bucket].clear();

        // 1. Buffer incoming top-down commands into the persistent scheduler
        for command in self.controller_inbox.drain(..) {
            if let ControllerCommand::ExecuteGlobalEvent { event_id, .. } = command {
                self.pending_global_events.insert(event_id, command);
            } else {
                self.process_controller_command(command);
            }
        }

        // 2. Priority Check: Do we have a Nuke scheduled for RIGHT NOW (or earlier)?
        let mut has_priority_event = false;
        for cmd in self.pending_global_events.values() {
            if let ControllerCommand::ExecuteGlobalEvent { execute_at_tick, .. } = cmd {
                if self.current_tick >= *execute_at_tick { has_priority_event = true; }
            }
        }

        // Heavy frames occur more frequently as dilation_factor approaches 1.0.
        // Formula: is_heavy if (current_tick % (1.0 / dilation_factor) == 0)
        let frame_interval = (SimFixed::from_num(1) / self.dilation_factor).to_num::<u64>();
        let is_heavy_frame = (self.current_tick % frame_interval == 0) || has_priority_event;

        if is_heavy_frame {
            self.simulate_physics_step(); 

            // 3. Execute Scheduled Controller Commands
            self.pending_global_events.retain(|_, cmd| {
                if let ControllerCommand::ExecuteGlobalEvent {
                    epicenter,
                    event_id,
                    geometry,
                    target_filters,
                    pulse_interval_ticks,
                    duration_ticks,
                    execute_at_tick,
                    caster_id,
                    ability_id,
                    data_epoch,
                    context,
                } = cmd {
                    // Ideal execution is `==`. `>=` acts as an emergency fallback if the 
                    // reliable TCP packet was severely delayed due to a datacenter outage.
                    if self.current_tick >= *execute_at_tick {
                        // Deterministic Epoch Pinning:
                        // Execute only under the same data dictionary used during pre-roll.
                        if *data_epoch != self.current_data_epoch {
                            if !self.try_activate_data_epoch(*data_epoch) {
                                // Keep queued and retry next frame rather than detonating under the wrong balance set.
                                return true;
                            }
                        }
                        
                        self.resolve_global_event_effect(
                            *epicenter,
                            geometry.clone(),
                            target_filters.clone(),
                            *pulse_interval_ticks,
                            *duration_ticks,
                            *event_id,
                            *caster_id,
                            *ability_id,
                            *data_epoch,
                            context.clone(),
                        );
                        
                        // Pulse Lifecycle Management
                        if let (Some(interval), Some(duration)) = (pulse_interval_ticks, duration_ticks) {
                            if *duration > *interval {
                                *duration -= *interval;
                                *execute_at_tick += *interval as u64;
                                return true; // Keep in queue for the next pulse
                            }
                        }
                        return false; // Final execution, remove from queue
                    }
                }
                true // Keep in queue for the future
            });

            // 4. Process Internal Mesh Events (Draining the persistent queue)
            for event in self.internal_inbox.drain(..) {
                // Internal Relay Deduplication
                if self.processed_proposals.contains(&event.event_id) { continue; }
                self.processed_proposals.insert(event.event_id, true);
                
                self.resolve_action(event.payload, event.actor_id, event.origin_tick, None, event.data_epoch);
            }

            // 5. Process External Proposals (Draining both persistent queue and stale buffer)
            let mut next_tick_stale_buffer = BoundedQueue::new(1000); // 1,000 capacity protects a 400-player Arbiter
            let mut latest_movement_by_actor: HashMap<EntityID, (ActionProposal, u64)> = HashMap::new();
            
            // We combine new arrivals with anything we held over from the previous tick.
            // Movement packets are coalesced to latest-per-actor before validation to reduce pressure.
            let all_proposals = self.external_inbox.drain(..).map(|p| (p, self.current_tick))
                .chain(self.stale_proposals_buffer.drain(..));

            for (proposal, local_arrival_tick) in all_proposals {
                if matches!(&proposal.payload, ActionPayload::Movement { .. }) {
                    latest_movement_by_actor.insert(proposal.actor_id, (proposal, local_arrival_tick));
                    continue;
                }

                // --- Data Epoch Handshake Validation ---
                if proposal.data_epoch < self.current_data_epoch {
                    self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                        proposal_id: proposal.proposal_id,
                        reason: "Data Epoch Mismatch".to_string()
                    });
                    continue;
                } else if proposal.data_epoch > self.current_data_epoch {
                    if !self.try_activate_data_epoch(proposal.data_epoch) {
                        if self.current_tick.saturating_sub(local_arrival_tick) >= MAX_EVENT_AGE_TICKS {
                            self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: proposal.proposal_id,
                                reason: "Data Epoch Sync Timeout".to_string()
                            });
                        } else {
                            if next_tick_stale_buffer.is_full() {
                                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                                    proposal_id: proposal.proposal_id,
                                    reason: "Arbiter Queue Saturated".to_string()
                                });
                            } else {
                                next_tick_stale_buffer.push_back((proposal, local_arrival_tick));
                            }
                        }
                        continue;
                    }
                }

                // --- Topology Epoch Handshake Validation ---
                if proposal.topology_epoch < self.topology_epoch {
                    self.forward_to_correct_arbiter(proposal); // Proxy is stale
                    continue;
                } else if proposal.topology_epoch > self.topology_epoch {
                    // Arbiter is stale. Buffer until the Controller's topology update arrives.
                    // Timeout is based purely on the Arbiter's local clock, avoiding drift false-positives.
                    // We use MAX_EVENT_AGE_TICKS (60 ticks / 1.0s) to unify the engine's latency budget,
                    // allowing TCP up to 3 retransmissions to deliver the map update before we refund the player.
                    if self.current_tick.saturating_sub(local_arrival_tick) >= MAX_EVENT_AGE_TICKS {
                        self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                            proposal_id: proposal.proposal_id,
                            reason: "Topology Sync Timeout (Arbiter Stale)".to_string()
                        });
                    } else {
                        // Explicit rejection on saturation (never silent drop).
                        if next_tick_stale_buffer.is_full() {
                            self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: proposal.proposal_id,
                                reason: "Arbiter Queue Saturated".to_string()
                            });
                        } else {
                            next_tick_stale_buffer.push_back((proposal, local_arrival_tick));
                        }
                    }
                    continue;
                }

                if self.processed_proposals.contains(&proposal.proposal_id) { continue; }
                self.processed_proposals.insert(proposal.proposal_id, true);
                
                if self.is_in_overlap_buffer(proposal.actor_id) {
                    self.relay_to_neighbors(MeshInternalEvent {
                        event_id: proposal.proposal_id,
                        source_arbiter_id: self.arbiter_id,
                        actor_id: Some(proposal.actor_id),
                        origin_tick: proposal.origin_tick,
                        data_epoch: proposal.data_epoch,
                        payload: proposal.payload.clone()
                    });
                }

                self.resolve_action(proposal.payload, Some(proposal.actor_id), proposal.origin_tick, Some(proposal.proposal_id), proposal.data_epoch);
            }

            // Process latest movement per actor after coalescing (no per-proposal terminal acks).
            for (_, (proposal, local_arrival_tick)) in latest_movement_by_actor {
                if proposal.data_epoch > self.current_data_epoch {
                    if !self.try_activate_data_epoch(proposal.data_epoch)
                        && self.current_tick.saturating_sub(local_arrival_tick) < MAX_EVENT_AGE_TICKS
                    {
                        let _ = next_tick_stale_buffer.try_push_back((proposal, local_arrival_tick));
                        continue;
                    }
                } else if proposal.data_epoch < self.current_data_epoch {
                    // Movement has no terminal ack; stale movement is dropped/coalesced.
                    continue;
                }

                if proposal.topology_epoch < self.topology_epoch {
                    self.forward_to_correct_arbiter(proposal);
                    continue;
                } else if proposal.topology_epoch > self.topology_epoch {
                    if self.current_tick.saturating_sub(local_arrival_tick) < MAX_EVENT_AGE_TICKS {
                        let _ = next_tick_stale_buffer.try_push_back((proposal, local_arrival_tick));
                    }
                    continue;
                }
                self.resolve_action(proposal.payload, Some(proposal.actor_id), proposal.origin_tick, None, proposal.data_epoch);
            }
            
            // Save the held-over proposals for the next simulation tick
            self.stale_proposals_buffer = next_tick_stale_buffer;
        } else {
            // Light Frame: External/Internal inboxes are NOT drained. They accumulate safely.
            self.simulate_light_physics();
        }

        // Integrate dead-reckoned Ghosts with low-cost anomaly guards.
        self.integrate_ghosts_lightweight();
        self.broadcast_ghosts_to_neighbors();
        self.broadcast_with_interest_management(); 
        self.tick_merge_forwarding();
    }

    // --- Ghost Integration (Low-Cost / Anomaly-Gated) ---
    fn integrate_ghosts_lightweight(&mut self) {
        let mut expired = Vec::new();
        for (ghost_id, ghost) in self.ghost_entities.iter_mut() {
            // Expire stale ghosts so downstream rendering never drifts indefinitely.
            if self.current_tick.saturating_sub(ghost.last_update_tick) > GHOST_RENDER_TTL_TICKS {
                expired.push(*ghost_id);
                continue;
            }

            // Degraded ghosts stay frozen briefly to avoid tunneling artifacts until correction arrives.
            if matches!(ghost.quality, GhostQuality::Degraded) && self.current_tick < ghost.degraded_until_tick {
                self.ghost_grid.upsert(*ghost_id, ghost.position);
                continue;
            }
            ghost.position += ghost.velocity;
            self.ghost_grid.upsert(*ghost_id, ghost.position);
        }

        for ghost_id in expired {
            self.ghost_entities.remove(&ghost_id);
            self.ghost_grid.remove(ghost_id);
        }
    }

    // Called by the network layer when an unreliable UDP GhostUpdate arrives.
    fn on_ghost_update_unreliable(&mut self, update: GhostUpdate) {
        if update.source_tick + MAX_EVENT_AGE_TICKS < self.current_tick { return; }

        let ghost = self.ghost_entities.entry(update.entity_id).or_insert(GhostState2D {
            entity_id: update.entity_id,
            authoritative_arbiter_id: update.source_arbiter_id,
            position: update.position,
            velocity: update.velocity,
            last_valid_position: update.position,
            last_update_tick: update.source_tick,
            movement_class: update.movement_class,
            quality: GhostQuality::Healthy,
            degraded_until_tick: 0,
        });

        let dt = self.current_tick.saturating_sub(ghost.last_update_tick);
        let expected_max = max_allowed_displacement(ghost.movement_class, dt) + GHOST_ANOMALY_MARGIN;
        let observed = ghost.position.distance_to(update.position);
        let anomaly = observed > expected_max
            || matches!(update.movement_class, GhostMovementClass::HighSpeed | GhostMovementClass::Teleport);

        if anomaly {
            // Cost control: sweep only against nearby static cells (broadphase), never full-map geometry.
            let candidates = self.static_grid.query_segment_aabb(ghost.position, update.position);
            if segment_hits_static(ghost.position, update.position, &candidates) {
                ghost.position = first_valid_contact_or(ghost.last_valid_position);
                ghost.velocity = Vec2F::ZERO;
                ghost.quality = GhostQuality::Degraded;
                ghost.degraded_until_tick = self.current_tick + GHOST_DEGRADED_TTL_TICKS;
                self.request_ghost_correction_rudp(update.entity_id, update.source_arbiter_id);
                return;
            }
        }

        ghost.position = update.position;
        ghost.velocity = update.velocity;
        ghost.last_valid_position = update.position;
        ghost.last_update_tick = update.source_tick;
        ghost.authoritative_arbiter_id = update.source_arbiter_id;
        ghost.movement_class = update.movement_class;
        ghost.quality = GhostQuality::Healthy;
        self.ghost_grid.upsert(update.entity_id, ghost.position);
    }

    // Reliable correction path reuses the same integration logic but arrives over authenticated RUDP.
    fn on_ghost_update_reliable(&mut self, auth: MeshAuthHeader, update: GhostUpdate) {
        if !self.verify_mesh_auth(&auth, &update) { return; }
        self.on_ghost_update_unreliable(update);
    }

    fn request_ghost_correction_rudp(&mut self, entity_id: EntityID, owner_arbiter_id: u32) {
        self.send_to_arbiter(owner_arbiter_id, MeshInternalEvent {
            event_id: generate_uuid(),
            source_arbiter_id: self.arbiter_id,
            actor_id: None,
            origin_tick: self.current_tick,
            data_epoch: self.current_data_epoch,
            payload: ActionPayload::RequestGhostCorrection {
                entity_id,
                requester_arbiter_id: self.arbiter_id,
            },
        });
    }

    fn send_ghost_update_rudp(&mut self, target_arbiter_id: u32, update: GhostUpdate) {
        self.network.send_rudp(target_arbiter_id, update);
    }

    // --- Intra-Mesh Ghost Propagation (Geometric) ---
    fn broadcast_ghosts_to_neighbors(&mut self) {
        // Purely stateless geometric calculation: No pub/sub tracking needed.
        for entity in self.entities.values() {
            // Find all sibling Arbiters whose AABB intersects the entity's visibility radius
            let overlapping_neighbors = self.local_grid.get_neighbors_intersecting_radius(entity.position, VISIBLE_RADIUS);
            
            for neighbor_id in overlapping_neighbors {
                // Delta-compression: Only send if velocity changed or it's a keyframe
                if entity.kinematics_changed() || self.current_tick % KEYFRAME_INTERVAL == 0 {
                    // Include movement class so receivers can anomaly-gate expensive validation.
                    let ghost_update = entity.get_ghost_update(self.current_tick);
                    // Sent via Unreliable UDP (it is fine if it drops, dead-reckoning covers it)
                    self.send_to_arbiter_unreliable(neighbor_id, ghost_update);
                }
            }
        }
    }

    fn resolve_action(&mut self, payload: ActionPayload, source_actor_id: Option<EntityID>, origin_tick: u64, original_proposal_id: Option<UUID>, data_epoch: u32) {
        match payload {
            ActionPayload::TargetedAbility { target_id, ability_id } => {
                let actor_id = source_actor_id.expect("TargetedAbility requires a source actor");
                
                let local_target_pos = self.entities.get(&target_id).and_then(|target| {
                    if self.has_jurisdiction_over(target.position) { Some(target.position) } else { None }
                });
                let ghost_target_owner = self.ghost_entities.get(&target_id).map(|ghost| ghost.authoritative_arbiter_id);
                let ghost_target_pos = self.ghost_entities.get(&target_id).map(|ghost| ghost.position);

                let target_pos = if let Some(pos) = local_target_pos {
                    pos
                } else if let Some(pos) = ghost_target_pos {
                    pos
                } else {
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                            proposal_id: prop_id,
                            reason: "Invalid Target".to_string()
                        });
                    }
                    return;
                };

                // Safe Actor Lookup: The attacker might be a Real entity or a Ghost (if relayed)
                let actor_pos = match self.get_entity_or_ghost_position(actor_id) {
                    Some(pos) => pos,
                    None => {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: prop_id,
                                reason: "Unknown Attacker".to_string()
                            });
                        }
                        return; // Attacker is completely unknown due to dropped packets; safely abort.
                    },
                };

                let ability = get_ability_data(ability_id, data_epoch);
                
                // --- Phase 1: The Pre-Roll (Originating Server Authority) ---
                // The Arbiter securely calculates the offensive math using its authoritative state,
                // completely ignoring any math the client/Edge Node might have attempted to claim.
                let context = self.generate_combat_context(actor_id, &ability);

                // --- Global Event Escalation ---
                if ability.geometry.get_max_extent() > MAX_SPELL_RANGE {
                    if self.mesh_controller_client.is_offline() {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed { 
                                proposal_id: prop_id,
                                reason: "Mesh Controller Unreachable".to_string() 
                            });
                        }
                        return;
                    }
                    // Pass the full combat identity up to the Controller so it can construct the downstream command
                    self.mesh_controller_client.escalate_event(
                        actor_id,
                        ability_id, 
                        data_epoch,
                        context.clone(),
                        target_pos,
                        ability.geometry.clone(),
                        ability.target_filters.clone(),
                        ability.pulse_interval_ticks,
                        ability.duration_ticks,
                    );
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                    return;
                }

                let distance = actor_pos.distance_to(target_pos);
                let prediction_tolerance = calculate_prediction_drift(origin_tick, self.current_tick);
                let effective_range = ability.max_range + prediction_tolerance;

                if distance <= effective_range {
                    if local_target_pos.is_some() {
                        self.apply_combat_math(target_id, Some(actor_id), context.clone(), distance);
                    } else if let Some(owner_arbiter_id) = ghost_target_owner {
                        // Border-targeted cast: actor-owner pre-rolls context, target-owner applies mutation.
                        self.send_to_arbiter(owner_arbiter_id, MeshInternalEvent {
                            event_id: generate_uuid(),
                            source_arbiter_id: self.arbiter_id,
                            actor_id: Some(actor_id),
                            origin_tick,
                            data_epoch,
                            payload: ActionPayload::InternalPreparedHit {
                                target_id,
                                context: context.clone(),
                            },
                        });
                    }
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                } else if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                        proposal_id: prop_id,
                        reason: "Out of Range".to_string()
                    });
                }
            },
            ActionPayload::InternalPreparedHit { target_id, context } => {
                // Internal-only path: context is already authoritative and must not be recomputed.
                let target_pos = match self.entities.get(&target_id) {
                    Some(target) if self.has_jurisdiction_over(target.position) => target.position,
                    _ => return, // Internal relay may race ownership during boundary transitions; intentional safe drop.
                };

                let distance = match source_actor_id.and_then(|id| self.get_entity_or_ghost_position(id)) {
                    Some(attacker_pos) => attacker_pos.distance_to(target_pos),
                    None => SimFixed::from_num(0),
                };

                self.apply_combat_math(target_id, source_actor_id, context, distance);
            },
            ActionPayload::GroundTargetedAbility { destination, ability_id } => {
                let actor_id = source_actor_id.expect("GroundTargetedAbility requires a source actor");
                
                let actor_pos = match self.get_entity_or_ghost_position(actor_id) {
                    Some(pos) => pos,
                    None => {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: prop_id,
                                reason: "Unknown Attacker".to_string()
                            });
                        }
                        return;
                    },
                };

                let ability = get_ability_data(ability_id, data_epoch);
                let context = self.generate_combat_context(actor_id, &ability);

                // --- Global Event Escalation (Ground-Targeted) ---
                if ability.geometry.get_max_extent() > MAX_SPELL_RANGE {
                    if self.mesh_controller_client.is_offline() {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed { 
                                proposal_id: prop_id,
                                reason: "Mesh Controller Unreachable".to_string() 
                            });
                        }
                        return;
                    }
                    
                    // Escalate using the raw ground coordinate (destination) as the epicenter
                    self.mesh_controller_client.escalate_event(
                        actor_id,
                        ability_id, 
                        data_epoch,
                        context.clone(),
                        destination, // Ground Coordinate
                        ability.geometry.clone(),
                        ability.target_filters.clone(),
                        ability.pulse_interval_ticks,
                        ability.duration_ticks,
                    );
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                    return;
                }

                // Standard Local Resolution
                let distance_to_cast = actor_pos.distance_to(destination);
                let prediction_tolerance = calculate_prediction_drift(origin_tick, self.current_tick);
                let effective_cast_range = ability.max_range + prediction_tolerance;

                if distance_to_cast <= effective_cast_range {
                    // Because it is ground-targeted, the Arbiter spawns an ephemeral ZoneActor or 
                    // instantly applies an AoE blast at that specific [x, y] coordinate.
                    // CRITICAL FIX: We MUST use the original_proposal_id to guarantee that if this 
                    // proposal was relayed to neighboring Arbiters, they all generate the exact same 
                    // UUID for the resulting ImpactEvent, allowing the Ledger to prevent double-damage.
                    let event_uuid = original_proposal_id.unwrap_or_else(|| generate_uuid());
                    self.resolve_aoe_effect(destination, ability.radius, event_uuid, actor_id, ability_id, data_epoch, context);
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                } else if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                        proposal_id: prop_id,
                        reason: "Out of Range".to_string()
                    });
                }
            },
            ActionPayload::RequestGhostCorrection { entity_id, requester_arbiter_id } => {
                // Owner-side reliable repair response for degraded ghost correction requests.
                if let Some(entity) = self.entities.get(&entity_id) {
                    if !self.has_jurisdiction_over(entity.position) { return; }
                    let mut keyframe = entity.get_ghost_update(self.current_tick);
                    keyframe.is_keyframe = true; // Force full state correction semantics.
                    self.send_ghost_update_rudp(requester_arbiter_id, keyframe); // Reliable RUDP path.
                }
            },
            ActionPayload::ImpactEvent { impact_id, target_ids, epicenter, geometry, impact_tick, context } => {
                // Network Discard Window: Drop packets that are older than our ledger's memory capacity.
                // Using `>=` ensures we don't accidentally write to the bucket currently being cleared.
                if self.current_tick.saturating_sub(impact_tick) >= MAX_EVENT_AGE_TICKS { return; }

                for target_id in target_ids {
                    let ledger_key = (impact_id, target_id);
                    let bucket_index = (impact_tick % MAX_EVENT_AGE_TICKS) as usize;
                    if self.event_idempotency_ledger[bucket_index].contains(&ledger_key) { continue; }

                    // SCENARIO A: Target is a REAL entity owned by this Arbiter
                    if let Some(target) = self.entities.get(&target_id) {
                        if self.has_jurisdiction_over(target.position) {
                            // --- Final Mathematical Validation (Ghost Drift Check) ---
                            // Because the reporting Arbiter may have been aiming at a dead-reckoned Ghost,
                            // their coordinates for the explosion might slightly miss the true entity.
                            // We allow a small 'ghost_drift_tolerance' to favor the shooter and prevent phantom dodges,
                            // while strictly preserving the geometric integrity of Cones and Boxes.
                            let distance_to_impact = target.position.distance_to(epicenter);
                            let ghost_drift_tolerance = calculate_ghost_drift(impact_tick, self.current_tick);
                            
                            if geometry.is_inside_with_tolerance(target.position, epicenter, ghost_drift_tolerance) {
                                self.event_idempotency_ledger[bucket_index].insert(ledger_key);
                                self.apply_combat_math(target_id, source_actor_id, context.clone(), distance_to_impact);
                            }
                        }
                        continue;
                    }

                    // SCENARIO B: Target is a GHOST entity owned by a neighboring Arbiter
                    if let Some(ghost) = self.ghost_entities.get(&target_id) {
                        if ghost.position.is_inside_geometry(epicenter, &geometry) {
                            self.event_idempotency_ledger[bucket_index].insert(ledger_key);
                            
                            // Package the ImpactEvent and relay it to the Ghost's true owner
                            let relay_payload = MeshInternalEvent {
                                event_id: generate_uuid(), // Unique envelope ID for this relay hop
                                source_arbiter_id: self.arbiter_id,
                                actor_id: source_actor_id,
                                origin_tick: impact_tick,
                                data_epoch, // CRITICAL FIX: Pass the data_epoch forward so the receiving Arbiter uses the correct dictionary
                                // Preserve original impact_id for destination ledger deduplication
                                payload: ActionPayload::ImpactEvent {
                                    impact_id, 
                                    target_ids: vec![target_id], 
                                    epicenter,
                                    geometry: geometry.clone(),
                                    impact_tick,
                                    context: context.clone(),
                                }
                            };
                            
                            // Dispatched via Reliable-UDP (RUDP). If dropped, the network layer will retry.
                            // The receiving Arbiter's Idempotency Ledger will deduplicate any retries.
                            self.send_to_arbiter(ghost.authoritative_arbiter_id, relay_payload);
                        }
                    }
                }
            },
            ActionPayload::SpawnProjectile { direction, target_id, spell_id } => {
                let actor_id = source_actor_id.expect("SpawnProjectile requires a source actor");
                let actor_pos = match self.get_entity_or_ghost_position(actor_id) {
                    Some(pos) => pos,
                    None => {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: prop_id,
                                reason: "Unknown Attacker".to_string()
                            });
                        }
                        return;
                    }
                };

                let ability = get_ability_data(spell_id, data_epoch);
                // Validate cooldowns, resources, and CC states here (omitted for brevity)
                let context = self.generate_combat_context(actor_id, &ability);

                let projectile = ProjectileActor {
                    projectile_id: original_proposal_id.unwrap_or_else(|| generate_uuid()),
                    owner_id: actor_id,
                    target_id,
                    position: actor_pos,
                    // Fixed-point vector math
                    velocity: direction.normalize() * ability.projectile_speed, 
                    remaining_lifetime_ticks: ability.duration_ticks.unwrap_or(120),
                    fuse_remaining_ticks: ability.fuse_timer_ticks.unwrap_or(0),
                    pierce_remaining: ability.pierce_count.unwrap_or(0),
                    data_epoch,
                    damage_origin: DamageOrigin::DirectCast,
                    proc_depth: 0,
                    authoritative_arbiter_id: self.arbiter_id,
                    handoff_topology_epoch: self.topology_epoch,
                    handoff_cutover_tick: self.current_tick,
                    handoff_seq: 0,
                    handoff_state: ProjectileHandoffState::Owned,
                    impact_sequence: 0,
                    spell_data: ability,
                };
                
                self.projectiles.insert(projectile.projectile_id, projectile);

                if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                }
            },
            ActionPayload::Movement { position, velocity, rotation } => {
                let actor_id = source_actor_id.expect("Movement requires a source actor");
                if let Some(entity) = self.entities.get_mut(&actor_id) {
                    if !self.has_jurisdiction_over(entity.position) { return; }
                    
                    // Anti-Cheat: Validate displacement against max theoretical speed
                    let dt = self.current_tick.saturating_sub(entity.last_movement_tick);
                    let max_displacement = (entity.stats.move_speed * SimFixed::from_num(dt)) + GHOST_ANOMALY_MARGIN;
                    
                    if entity.position.distance_to(position) <= max_displacement {
                        // Validate against static geometry (Navmesh)
                        if !self.static_grid.is_colliding(position) {
                            entity.position = position;
                            entity.velocity = velocity;
                            entity.rotation = rotation;
                            entity.last_movement_tick = self.current_tick;
                            self.local_grid.upsert(actor_id, position);
                        } else {
                            // Hit a wall, rubber-band back to last valid
                            self.trigger_client_rollback(actor_id);
                        }
                    } else {
                        // Speed hack detected, rubber-band back
                        self.trigger_client_rollback(actor_id);
                    }
                }
            },
            ActionPayload::UseConsumable { item_id } => {
                let actor_id = source_actor_id.unwrap();
                // 1. Verify inventory via asynchronous Meta Service check (or pre-synced local SoftState)
                // 2. Apply soft state changes (e.g., add HP, start potion cooldown)
                if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                }
            },
            ActionPayload::Interact { target_entity } => {
                let actor_id = source_actor_id.unwrap();
                // Logic: distance check, type check (NPC, Loot, Resource), trigger UI/Quest event via Meta Services
                if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                }
            }
        }
    }

    // --- Deep RPG Combat Engine ---
    // This centralizes all complex ARPG/MOBA math (Armor, Resistance, Weight, Falloff)
    // ensuring it only runs on the true authoritative owner of the target.
    // (See `RPG_Mechanics_and_State.md` for the full mitigation formula including Evasion and Block).
    // 
    // RUST BORROW CHECKER NOTE: This function takes a mutable borrow of the `victim`. 
    // You cannot simultaneously take a mutable borrow of the `attacker` from `self.entities` 
    // (e.g., to apply Lifesteal or Thorns damage) without triggering a compiler error. 
    // Instead, "reflection" mechanics must push a new `MeshInternalEvent` with
    // `ActionPayload::InternalPreparedHit` to the `internal_inbox`.
    fn apply_combat_math(&mut self, target_id: EntityID, attacker_id: Option<EntityID>, context: CombatContext, distance: SimFixed) {
        let mut victim = self.entities.get_mut(&target_id).unwrap();
        
        if victim.is_invulnerable { return; }

        // --- Healing vs Damage Branch ---
        if context.damage_type == 100 { // 100 = HEALING
            victim.hp = std::cmp::min(victim.max_hp, victim.hp + context.base_damage as i32);
            return; 
        }

        // 1. Distance Falloff
        let distance_multiplier = calculate_falloff(distance);
        let mut incoming_damage = context.base_damage as SimFixed * distance_multiplier;

        // 2. Resistance & Penetration Mitigation
        // Note: For brevity, Evasion and Block checks are omitted here. See `RPG_Mechanics_and_State.md`.
        if context.damage_type != 99 {
            let mut effective_resistance = victim.defense.resistances[context.damage_type as usize];
            
            // Fixed-point deterministic math using F32 literal macros/conversions
            effective_resistance *= (SimFixed::from_num(1) - context.armor_penetration_pct);
            effective_resistance -= context.armor_penetration_flat;
            
            effective_resistance = effective_resistance.clamp(SimFixed::from_num(-100), SimFixed::from_num(85));
            
            let one_hundred = SimFixed::from_num(100);
            if effective_resistance > SimFixed::from_num(0) {
                incoming_damage *= (SimFixed::from_num(1) - (effective_resistance / one_hundred));
            } else {
                incoming_damage *= (SimFixed::from_num(1) + (effective_resistance.abs() / one_hundred));
            }
        }

        // 3. Application
        victim.hp -= incoming_damage as i32;

        // 4. Physics Engine (Knockback vs Weight)
        if context.knockback_force > 0 {
            victim.velocity.x += calculate_knockback(context.knockback_force, victim.stats.weight);
        }

        // 5. Hard State Trigger
        if victim.hp <= 0 {
            self.emit_hard_state(HardEvent::PlayerDied { killer: attacker_id, victim: target_id });
        }
        
        // 6. Reactive Procs (Lifesteal / Thorns)
        // We push to the internal inbox to be processed sequentially, safely bypassing the borrow checker.
        // Safety Rule: Reactive effects only trigger from DIRECT hits and only at depth 0.
        // This prevents infinite loops (e.g., Thorns-vs-Thorns ping-pong).
        if let Some(atk_id) = attacker_id {
            if victim.has_thorns_buff()
                && matches!(context.damage_origin, DamageOrigin::DirectCast)
                && context.proc_depth == 0
            {
                self.internal_inbox.push_back(MeshInternalEvent {
                    event_id: generate_uuid(),
                    source_arbiter_id: self.arbiter_id,
                    actor_id: Some(target_id),
                    origin_tick: self.current_tick,
                    data_epoch: self.current_data_epoch, // CRITICAL FIX: Use the data epoch, not the topology map version!
                    payload: ActionPayload::InternalPreparedHit {
                        target_id: atk_id,
                        context: CombatContext { 
                            base_damage: 15, 
                            damage_type: 99, // TRUE DAMAGE
                            knockback_force: SimFixed::from_num(0), 
                            armor_penetration_pct: SimFixed::from_num(0),
                            armor_penetration_flat: SimFixed::from_num(0),
                            is_critical_strike: false,
                            status_effect_id: None,
                            damage_origin: DamageOrigin::ReactiveProc,
                            proc_depth: context.proc_depth.saturating_add(1),
                        }
                    }
                });
            }
        }
    }

    // Safely retrieves coordinates for an entity, checking both local ownership and Ghost memory
    fn get_entity_or_ghost_position(&self, id: EntityID) -> Option<Vec2F> {
        if let Some(entity) = self.entities.get(&id) { return Some(entity.position); }
        if let Some(ghost) = self.ghost_entities.get(&id) { return Some(ghost.position); }
        None
    }

    fn process_controller_command(&mut self, command: ControllerCommand) {
        match command {
            ControllerCommand::UpdateTopology { .. } => { /* ... */ }
            ControllerCommand::BeginMerge { merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch, .. } => {
                self.on_begin_merge_command(merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch);
            }
            ControllerCommand::CommitMerge { merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch } => {
                self.on_commit_merge_command(merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch);
            }
            ControllerCommand::FinalizeMerge { merge_id, winner_arbiter_id, loser_arbiter_id, new_epoch } => {
                self.on_finalize_merge_command(merge_id, winner_arbiter_id, loser_arbiter_id, new_epoch);
            }
            ControllerCommand::SyncHeartbeat { controller_shard_tick } => {
                // The Metronome Corrector
                let diff = (controller_shard_tick as i64) - (self.current_tick as i64);
                // Adjust our frame sleep target (e.g., +/- 100 microseconds per frame) to smoothly catch up 
                // or slow down without causing a massive temporal snap that would break ghost extrapolation.
                self.frame_pacing_offset_micros = (diff * 50).clamp(-1000, 1000); 
            }
            ControllerCommand::PrepareDataEpoch { new_epoch, asset_uri, checksum } => {
                // Offload the I/O to a background thread so the 60Hz loop never stalls.
                // The background thread will download, parse, and push the new dictionary 
                // into a lock-free queue that the Arbiter reads from at the top of tick().
                self.asset_loader.async_fetch_and_parse(new_epoch, asset_uri, checksum);
            }
            _ => { /* ExecuteGlobalEvent and Splits handled in scheduler block */ }
        }
    }

    fn simulate_physics_step(&mut self) {
        // 1. Resolve discrete physics steps (Movement integration, knockback decay)
        self.apply_kinematics();
        
        // 2. Process all active Status Effects (DoTs, HoTs, CC)
        self.tick_status_effects();
    }

    fn tick_status_effects(&mut self) {
        for (entity_id, entity) in self.entities.iter_mut() {
            let mut expired = Vec::new();
            
            for (i, effect) in entity.active_status_effects.iter_mut().enumerate() {
                if self.current_tick >= effect.next_pulse_tick {
                    // Trigger the damage/healing payload
                    if let Some(context) = &effect.pulse_context {
                        // We push to the internal inbox to bypass the borrow checker
                        // and ensure the mitigation math runs cleanly in sequence.
                        self.internal_inbox.push_back(MeshInternalEvent {
                            event_id: generate_uuid(),
                            source_arbiter_id: self.arbiter_id,
                            actor_id: Some(effect.caster_id),
                            origin_tick: self.current_tick,
                            data_epoch: effect.data_epoch,
                            payload: ActionPayload::InternalPreparedHit {
                                target_id: *entity_id,
                                context: context.clone(),
                            }
                        });
                    }
                    
                    // Reset the pulse timer based on the SpellData (e.g., 60 ticks for a 1-second DoT)
                    let spell_data = get_ability_data(effect.effect_id, effect.data_epoch);
                    effect.next_pulse_tick = self.current_tick + spell_data.pulse_interval_ticks.unwrap_or(60) as u64;
                }
                
                effect.remaining_ticks = effect.remaining_ticks.saturating_sub(1);
                if effect.remaining_ticks == 0 {
                    expired.push(i);
                }
            }
            
            // Remove expired buffs (iterate in reverse to avoid index shifting)
            for i in expired.into_iter().rev() {
                entity.active_status_effects.remove(i);
            }
        }
    }

    // Lock-Free Ownership check
    fn has_jurisdiction_over(&self, target_point: Vec2F) -> bool {
        for sibling in self.get_overlapping_siblings(target_point) {
            if sibling.rtree_depth > self.rtree_depth { return false; }
            if sibling.rtree_depth == self.rtree_depth && sibling.arbiter_id < self.arbiter_id { return false; }
        }
        true
    }

    // --- Interest Management (Downstream Bandwidth Control) ---
    fn broadcast_with_interest_management(&mut self, live_config: &LiveConfig) {
        for proxy_id in self.connected_proxies() {
            let proxy_pos = self.get_proxy_position(proxy_id);
            let mut proxy_payload = Vec::new();
            let mut seen = HashSet::new();

            let close_entities = self.local_grid.query_radius(proxy_pos, live_config.combat_radius);
            for entity in close_entities {
                seen.insert(entity.id);
                proxy_payload.push(entity.get_full_update()); // is_authoritative_owner = true
            }

            // Include border-neighbor ghosts for rendering/raycast consistency at Arbiter seams.
            let close_ghost_ids = self.ghost_grid.query_radius(proxy_pos, live_config.combat_radius);
            for ghost_id in close_ghost_ids {
                if seen.contains(&ghost_id) { continue; } // Prefer local owner update if both exist.
                if let Some(ghost) = self.ghost_entities.get(&ghost_id) {
                    proxy_payload.push(ghost.get_full_update()); // is_ghost = true
                    seen.insert(ghost_id);
                }
            }

            if self.current_tick % live_config.keyframe_interval_ticks == 0 {
                let far_entities = self.local_grid.query_donut(proxy_pos, live_config.combat_radius, live_config.visible_radius);
                for entity in far_entities {
                    if seen.insert(entity.id) {
                        proxy_payload.push(entity.get_keyframe_update());
                    }
                }

                let far_ghost_ids = self.ghost_grid.query_donut(proxy_pos, live_config.combat_radius, live_config.visible_radius);
                for ghost_id in far_ghost_ids {
                    if !seen.insert(ghost_id) { continue; }
                    if let Some(ghost) = self.ghost_entities.get(&ghost_id) {
                        proxy_payload.push(ghost.get_keyframe_update()); // is_ghost = true
                    }
                }
            }
            self.network.send_to(proxy_id, proxy_payload);
        }
    }
}

---

### 3.3 Ephemeral Actors (Projectiles)

To support lock-free cross-boundary combat and complex multi-hit spells, projectiles are not treated as raw spatial vectors. They are instantiated as independent "Thinker" Actors hosted by the Spatial Arbiter. 

The Projectile Actor is the sole authority on *who it hits*, generating a globally unique `UUID` for every explosion/impact. This allows the Spatial Arbiter to flawlessly deduplicate boundary overlaps using the Idempotency Ledger.

```rust
enum ProjectileHandoffState {
    Owned,
    TransferPending {
        to_arbiter_id: u32,
        handoff_seq: u64,
        commit_tick: u64,
        acked: bool,
    },
    Shadow, // Replica kept briefly after commit; never simulates
}

struct ProjectileActor {
    projectile_id: UUID,
    owner_id: EntityID,
    target_id: Option<EntityID>,
    position: Vec2F,
    velocity: Vec2F,
    remaining_lifetime_ticks: u32,
    fuse_remaining_ticks: u32,
    pierce_remaining: u8,
    data_epoch: u32,
    damage_origin: DamageOrigin, // Inherited from the launch context
    proc_depth: u8,              // Propagated for deterministic proc recursion limits
    authoritative_arbiter_id: u32, // The only Arbiter allowed to advance this projectile
    handoff_topology_epoch: u32,    // Topology version where authority was last assigned
    handoff_cutover_tick: u64,      // Tick where current authority became active
    handoff_seq: u64,               // Monotonic ownership transfer sequence
    handoff_state: ProjectileHandoffState,
    impact_sequence: u32,           // Monotonic owner-local sequence for deterministic impact UUID derivation
    spell_data: SpellData,
}

impl ProjectileActor {
    // Projectiles run their own tick within the Host Arbiter's simulation loop.
    // The Arbiter passes in the current_target_pos (resolved from Real entities or dead-reckoned Ghosts).
    fn tick(&mut self, local_hitboxes: &Vec<Hitbox>, current_target_pos: Option<Vec2F>) -> Option<MeshInternalEvent> {
        // Split/Handoff safety: shadow replicas must never simulate or emit impacts.
        if self.authoritative_arbiter_id != current_arbiter_id() { return None; }

        // Runtime cross-boundary transfer: lightweight RUDP Prepare/Ack/Commit.
        if let ProjectileHandoffState::TransferPending { to_arbiter_id, handoff_seq, commit_tick, acked } = self.handoff_state {
            if acked && current_shard_tick() >= commit_tick {
                self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Commit {
                    projectile_id: self.projectile_id,
                    handoff_seq,
                    new_owner_arbiter_id: to_arbiter_id,
                    commit_tick,
                });
                self.authoritative_arbiter_id = to_arbiter_id;
                self.handoff_cutover_tick = commit_tick;
                self.handoff_state = ProjectileHandoffState::Shadow;
                return None;
            }
            // Still authoritative until commit; continue simulation and retry Prepare via network layer if needed.
        } else if self.will_cross_neighbor_boundary_next_step() {
            self.handoff_seq = self.handoff_seq.saturating_add(1);
            let destination = choose_neighbor_by_depth_then_id(self.position, self.velocity);
            let commit_tick = current_shard_tick() + 2; // deterministic small future window
            self.handoff_state = ProjectileHandoffState::TransferPending {
                to_arbiter_id: destination,
                handoff_seq: self.handoff_seq,
                commit_tick,
                acked: false,
            };
            self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Prepare {
                projectile_id: self.projectile_id,
                handoff_seq: self.handoff_seq,
                from_arbiter_id: current_arbiter_id(),
                to_arbiter_id: destination,
                topology_epoch: current_topology_epoch(),
                source_tick: current_shard_tick(),
                commit_tick,
                snapshot: self.to_snapshot(),
            });
        }

        // --- Homing "Dumb NPC" Steering Logic ---
        if let Some(pos) = current_target_pos {
            let desired_dir = (pos - self.position).normalize();
            // In a full implementation, apply a max `turn_rate` here to prevent instant 180-degree snaps.
            // If target is lost (current_target_pos is None), the projectile maintains its current velocity.
            self.velocity = desired_dir * self.spell_data.projectile_speed;
        }

        self.position.x += self.velocity.x;
        self.position.y += self.velocity.y;
        self.remaining_lifetime_ticks = self.remaining_lifetime_ticks.saturating_sub(1);
        self.fuse_remaining_ticks = self.fuse_remaining_ticks.saturating_sub(1);

        // The Projectile determines who it hits (Real players AND Ghosts).
        let victims = self.calculate_collisions(local_hitboxes);
        
        if !victims.is_empty() {
            // Generate a universally unique ID for this specific interaction/explosion.
            // This guarantees the Idempotency Ledger prevents double-damage, even for 
            // pulsing AoEs or returning boomerangs.
            let impact_uuid = deterministic_impact_uuid(self.projectile_id, self.impact_sequence, current_shard_tick());
            self.impact_sequence = self.impact_sequence.saturating_add(1);
            
            // The Projectile hands the authoritative ImpactEvent back to its Host Arbiter.
            // The Host Arbiter will apply damage to Real victims, and relay the impact to Ghost owners.
            return Some(MeshInternalEvent {
                event_id: generate_uuid(),
                source_arbiter_id: current_arbiter_id(),
                actor_id: Some(self.owner_id),
                origin_tick: current_shard_tick(), // Projectile actions are anchored to their current simulation frame
                data_epoch: self.data_epoch, // CRITICAL: Ensures receiving Arbiters use the correct dictionary version
                payload: ActionPayload::ImpactEvent { 
                    impact_id: impact_uuid, 
                    target_ids: victims,
                    epicenter: self.position, // Provides absolute center for Ghost drift checks and distance falloff
                    geometry: self.spell_data.collision_geometry,
                    impact_tick: current_shard_tick(),
                    context: CombatContext {
                        base_damage: self.spell_data.base_damage,
                        damage_type: self.spell_data.damage_type,
                        knockback_force: self.spell_data.knockback_force,
                        armor_penetration_pct: self.spell_data.armor_penetration_pct, // Passed from Pre-Roll
                        armor_penetration_flat: self.spell_data.armor_penetration_flat, // Passed from Pre-Roll
                        is_critical_strike: self.spell_data.is_critical_strike, // Ensures clients render Crits
                        status_effect_id: self.spell_data.status_effect_id,
                        damage_origin: self.damage_origin,
                        proc_depth: self.proc_depth,
                    }
                }
            });
        }
        None
    }

    fn to_snapshot(&self) -> ProjectileSnapshot {
        ProjectileSnapshot {
            projectile_id: self.projectile_id,
            owner_id: self.owner_id,
            target_id: self.target_id,
            position: self.position,
            velocity: self.velocity,
            remaining_lifetime_ticks: self.remaining_lifetime_ticks,
            fuse_remaining_ticks: self.fuse_remaining_ticks,
            pierce_remaining: self.pierce_remaining,
            impact_sequence: self.impact_sequence,
            data_epoch: self.data_epoch,
            damage_origin: self.damage_origin as u8,
            proc_depth: self.proc_depth,
        }
    }
}
```

#### 3.3.1 Projectile Ownership Transfer (Split/Handoff Safety)
```rust
// Called by the surrogate Arbiter during split planning.
fn assign_projectile_owner_at_cutover(
    projectile: &ProjectileActor,
    child_b: ArbiterRegion,
    child_c: ArbiterRegion,
    cutover_tick: u64,
    topology_epoch: u32,
) -> u32 {
    // Predict position at cutover using deterministic fixed-point integration.
    let dt = cutover_tick.saturating_sub(current_shard_tick());
    let predicted = projectile.position + (projectile.velocity * SimFixed::from_num(dt));

    // Reuse the same jurisdiction rule as entities: depth, then lowest Arbiter_ID.
    let owner_child_id = choose_owner_by_depth_then_id(predicted, child_b, child_c);

    serialize_handoff_record(HandoffProjectileRecord {
        projectile_id: projectile.projectile_id,
        owner_child_id,
        cutover_tick,
        topology_epoch,
    });

    owner_child_id
}

// Child boot behavior:
// - Winner child sets authoritative_arbiter_id = self.arbiter_id and continues tick().
// - Loser child keeps an optional shadow copy for one grace window but never advances it.
```

#### 3.3.2 Runtime Projectile Boundary Handoff (Low-Cost)
```rust
// Receiver-side handler for RUDP projectile handoffs.
fn on_projectile_handoff_rudp(&mut self, auth: MeshAuthHeader, msg: ProjectileHandoffMessage) {
    if !self.verify_mesh_auth(&auth, &msg) { return; }
    match msg {
        ProjectileHandoffMessage::Prepare {
            projectile_id, handoff_seq, from_arbiter_id, to_arbiter_id,
            topology_epoch, source_tick, commit_tick, snapshot
        } => {
            if to_arbiter_id != self.arbiter_id { return; }

            // Epoch safety mirrors proposal-epoch rules.
            if topology_epoch < self.topology_epoch {
                self.forward_handoff_surrogate(msg);
                return;
            }
            if topology_epoch > self.topology_epoch {
                self.buffer_handoff_until_epoch(msg);
                return;
            }

            // Single-simulator safety: only accept newer sequence.
            let last_seq = self.last_projectile_handoff_seq(projectile_id);
            if handoff_seq <= last_seq {
                self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Reject {
                    projectile_id, handoff_seq, reason: "StaleSequence".to_string()
                });
                return;
            }

            // Reconstruct full mid-flight state from snapshot.
            let mut p = ProjectileActor::from_snapshot(snapshot);
            p.authoritative_arbiter_id = from_arbiter_id; // Owner flips at commit_tick only.
            p.handoff_state = ProjectileHandoffState::Shadow;
            p.handoff_seq = handoff_seq;
            p.handoff_topology_epoch = topology_epoch;
            p.handoff_cutover_tick = commit_tick;
            self.projectiles.insert(projectile_id, p);

            self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Ack {
                projectile_id, handoff_seq, from_arbiter_id, to_arbiter_id, commit_tick
            });
        }
        ProjectileHandoffMessage::Ack { projectile_id, handoff_seq, commit_tick, .. } => {
            if let Some(p) = self.projectiles.get_mut(&projectile_id) {
                if let ProjectileHandoffState::TransferPending { handoff_seq: seq, commit_tick: ct, acked, .. } = &mut p.handoff_state {
                    if *seq == handoff_seq && *ct == commit_tick { *acked = true; }
                }
            }
        }
        ProjectileHandoffMessage::Commit { projectile_id, handoff_seq, new_owner_arbiter_id, commit_tick } => {
            if let Some(p) = self.projectiles.get_mut(&projectile_id) {
                if handoff_seq >= p.handoff_seq && current_shard_tick() >= commit_tick {
                    p.authoritative_arbiter_id = new_owner_arbiter_id;
                    p.handoff_state = if new_owner_arbiter_id == self.arbiter_id {
                        ProjectileHandoffState::Owned
                    } else {
                        ProjectileHandoffState::Shadow
                    };
                }
            }
        }
        ProjectileHandoffMessage::Reject { .. } => {
            // Sender remains authoritative and retries with updated destination/epoch.
        }
    }
}
```

#### 3.3.3 Sibling Merge Protocol (Prepare -> Stream -> Controller Commit -> Drain)
Commit-phase routing contract:
- At `CommitMerge`, the loser must emit a final downstream `TopologyUpdate` (`new_epoch`) with `redirect_arbiter_id = winner_arbiter_id` before entering `ForwardingOnly`.
- During the forwarding drain window, the loser must still serve or proxy `RequestRoutingDelta` so stale Edge Nodes can converge to winner routing.

```rust
fn on_begin_merge_command(
    &mut self,
    merge_id: UUID,
    winner_arbiter_id: u32,
    loser_arbiter_id: u32,
    cutover_tick: u64,
    new_epoch: u32,
) {
    let role = if self.arbiter_id == winner_arbiter_id {
        Some(MergeRole::Winner)
    } else if self.arbiter_id == loser_arbiter_id {
        Some(MergeRole::Loser)
    } else {
        None
    };
    if role.is_none() { return; }

    self.merge_state = Some(MergeState {
        merge_id,
        role: role.unwrap(),
        peer_arbiter_id: if self.arbiter_id == winner_arbiter_id { loser_arbiter_id } else { winner_arbiter_id },
        cutover_tick,
        target_epoch: new_epoch,
        phase: MergePhase::Streaming,
        forwarding_until_tick: 0,
    });

    if matches!(self.merge_state.as_ref().unwrap().role, MergeRole::Loser) {
        self.send_merge_handoff_rudp(MergeHandoffMessage::Prepare {
            merge_id,
            winner_arbiter_id,
            loser_arbiter_id,
            cutover_tick,
            topology_epoch: self.topology_epoch,
        });
        self.stream_merge_snapshot_and_wal(winner_arbiter_id, merge_id, new_epoch);
    }
}

fn on_finalize_merge_command(
    &mut self,
    merge_id: UUID,
    winner_arbiter_id: u32,
    loser_arbiter_id: u32,
    _new_epoch: u32,
) {
    if self.arbiter_id == winner_arbiter_id {
        self.mark_merge_complete(merge_id);
    } else if self.arbiter_id == loser_arbiter_id {
        self.mark_merge_complete(merge_id);
        self.shutdown_or_return_to_pool();
    }
}

fn on_commit_merge_command(
    &mut self,
    merge_id: UUID,
    winner_arbiter_id: u32,
    loser_arbiter_id: u32,
    cutover_tick: u64,
    new_epoch: u32,
) {
    // Commit is idempotent and may arrive before cutover; requeue until effective tick.
    if self.current_tick < cutover_tick {
        self.controller_inbox.push_back(ControllerCommand::CommitMerge {
            merge_id,
            winner_arbiter_id,
            loser_arbiter_id,
            cutover_tick,
            new_epoch,
        });
        return;
    }

    if self.already_committed_merge(merge_id) { return; }

    if self.arbiter_id == winner_arbiter_id {
        self.apply_merge_snapshot_atomic(merge_id, new_epoch);
        self.topology_epoch = new_epoch;
        self.promote_merged_region_ownership();
        self.mark_merge_committed(merge_id);
    } else if self.arbiter_id == loser_arbiter_id {
        self.topology_epoch = new_epoch;
        self.broadcast_topology_redirect_to_connected_edges(
            new_epoch,
            winner_arbiter_id,
            self.current_data_epoch,
        );
        if let Some(state) = self.merge_state.as_mut() {
            state.phase = MergePhase::ForwardingOnly;
            state.forwarding_until_tick = self.current_tick + MAX_EVENT_AGE_TICKS;
        }
        self.mark_merge_committed(merge_id);
    }
}

fn on_merge_handoff_rudp(&mut self, auth: MeshAuthHeader, msg: MergeHandoffMessage) {
    if !self.verify_mesh_auth(&auth, &msg) { return; }
    match msg {
        MergeHandoffMessage::Prepare { merge_id, winner_arbiter_id, topology_epoch, .. } => {
            if self.arbiter_id != winner_arbiter_id { return; }
            if topology_epoch != self.topology_epoch {
                self.send_merge_handoff_rudp(MergeHandoffMessage::Reject {
                    merge_id,
                    reason: "EpochMismatch".to_string(),
                });
                return;
            }
            self.init_merge_staging(merge_id);
        }
        MergeHandoffMessage::SnapshotChunk { merge_id, snapshot_chunk, is_last, .. } => {
            if !self.is_merge_winner(merge_id) { return; }
            self.stage_merge_snapshot_chunk(merge_id, snapshot_chunk);
            if is_last {
                if let Some(state) = self.merge_state.as_mut() {
                    if state.merge_id == merge_id { state.phase = MergePhase::Catchup; }
                }
            }
        }
        MergeHandoffMessage::WalDelta(delta) => {
            if !self.is_merge_winner(delta.merge_id) { return; }
            self.replay_merge_wal(delta);
            let awaiting_ack = self.merge_state.as_ref()
                .map(|s| s.merge_id == delta.merge_id && matches!(s.phase, MergePhase::Catchup))
                .unwrap_or(false);
            if awaiting_ack && self.merge_staging_synced_to(delta.merge_id) >= self.current_tick {
                self.send_merge_handoff_rudp(MergeHandoffMessage::CatchupAck {
                    merge_id: delta.merge_id,
                    winner_arbiter_id: self.arbiter_id,
                    loser_arbiter_id: self.merge_peer(delta.merge_id),
                    synced_to_tick: self.current_tick,
                });
                if let Some(state) = self.merge_state.as_mut() {
                    if state.merge_id == delta.merge_id { state.phase = MergePhase::AwaitingCommit; }
                }
            }
        }
        MergeHandoffMessage::DrainComplete { merge_id, loser_arbiter_id, winner_arbiter_id } => {
            if self.arbiter_id == winner_arbiter_id {
                self.notify_controller_merge_drained(merge_id, loser_arbiter_id);
            }
        }
        MergeHandoffMessage::CatchupAck { merge_id, winner_arbiter_id, loser_arbiter_id, synced_to_tick } => {
            // Loser forwards winner readiness to controller; controller owns commit orchestration.
            if self.arbiter_id == loser_arbiter_id {
                self.notify_controller_merge_ready(merge_id, winner_arbiter_id, loser_arbiter_id, synced_to_tick);
            }
        }
        MergeHandoffMessage::Reject { .. } => {
            // Omitted: retry/abort policy driven by controller deadlines.
        }
    }
}

fn apply_merge_snapshot_atomic(&mut self, merge_id: UUID, new_epoch: u32) {
    let staged = self.take_merge_staging(merge_id);

    // 1) Entity import + Ghost->Real promotion in same frame.
    for (entity_id, incoming) in staged.entities {
        if self.entities.contains_key(&entity_id) {
            self.abort_merge(merge_id, "EntityIdCollision");
            return;
        }
        self.ghost_entities.remove(&entity_id);
        self.ghost_grid.remove(entity_id);
        self.entities.insert(entity_id, incoming);
    }

    // 2) Projectile import with UUID-based deduplication.
    for snap in staged.projectiles {
        match self.projectiles.get(&snap.projectile_id) {
            Some(existing) if existing.impact_sequence >= snap.impact_sequence => {}
            _ => { self.projectiles.insert(snap.projectile_id, ProjectileActor::from_snapshot(snap)); }
        }
    }

    // 3) Idempotency ledger union by ring bucket.
    for b in staged.ledger_ring {
        let idx = b.bucket_index as usize;
        if idx >= self.event_idempotency_ledger.len() { continue; }
        for entry in b.entries {
            self.event_idempotency_ledger[idx].insert(entry);
        }
    }

    // 4) Merge deterministic schedulers and epoch.
    self.pending_global_events.extend(staged.pending_global_events);
    self.topology_epoch = new_epoch;
}

fn tick_merge_forwarding(&mut self) {
    if let Some(state) = &self.merge_state {
        if matches!(state.role, MergeRole::Loser) && matches!(state.phase, MergePhase::ForwardingOnly) {
            self.forward_all_external_and_internal_to(state.peer_arbiter_id);
            self.service_or_proxy_routing_delta_requests(state.peer_arbiter_id);
            if self.current_tick >= state.forwarding_until_tick && self.external_inbox.is_empty() && self.internal_inbox.is_empty() {
                self.send_merge_handoff_rudp(MergeHandoffMessage::DrainComplete {
                    merge_id: state.merge_id,
                    loser_arbiter_id: self.arbiter_id,
                    winner_arbiter_id: state.peer_arbiter_id,
                });
                self.shutdown_or_return_to_pool();
            }
        }
    }
}
```

---

## 4. Layer 3: The Datastore (Immutable Ledger)

The Datastore is an asynchronous worker pool that persists finalized "Hard State" events. It is entirely removed from the 60Hz simulation loop.

### 4.1 Interface
```rust
// Irreversible/Economic events
enum HardEvent {
    // Killer is an Option to support PvE / Environmental deaths
    PlayerDied { killer: Option<EntityID>, victim: EntityID },
    PlayerResurrected { healer: EntityID, victim: EntityID }, // Cancels the Meta respawn timer
    ItemDropped { entity_id: EntityID, item_id: u16, location: Vec2F },
    ObjectiveCaptured { team: TeamID, zone: RegionID },

    // Boss/Monster kill event — triggers loot table rolls in Meta
    MonsterDied {
        killer: Option<EntityID>,
        monster_id: EntityID,
        monster_type_id: u16,                // SpellData monster definition ID
        participating_entities: Vec<EntityID>, // All entities eligible for kill credit / loot
    },

    // Confirms that a loot drop was claimed by a player in the simulation
    LootClaimed {
        drop_id: UUID,         // Links to the loot spawn generated by Meta
        character_id: UUID,    // The player who picked it up (resolved from EntityID by Meta)
        item_id: u16,
    },

    // Cross-layer transaction confirmation (see Core Architecture § 9.8)
    TransactionConfirmed { tx_id: UUID },
}

// Controller → Event Bus notification when an Arbiter is declared dead
// Consumed by Meta's reconciliation service (see Core Architecture § 9.7)
struct ArbiterCrashedEvent {
    arbiter_id: u32,
    topology_epoch: u32,
    declared_dead_at: u64,  // Shard Tick at which the Controller declared the crash
}

struct DatastoreWorker {
    db_connection: DatabasePool,
}

impl DatastoreWorker {
    // Called asynchronously by Spatial Actors (Fire-and-Forget)
    fn append_event(&self, event: HardEvent) {
        // 1. Append to the durable Write-Ahead Log (WAL)
        self.db_connection.insert(event);
        
        // 2. Trigger asynchronous progression/analytics pipelines
        self.trigger_progression_pipelines(event);
    }
}
```

---

## 5. Summary of Architecture Rules

1.  **No Shared Memory:** Actors only communicate via message envelopes.
2.  **No Blocking Calls:** Spatial Actors must never perform Disk I/O or wait for Database locks within the 60Hz `tick()`.
3.  **Deterministic Time:** Every action is bound to a Shard Tick.
4.  **Spatial Jurisdiction:** Geography and R-Tree depth determine authoritative ownership.
