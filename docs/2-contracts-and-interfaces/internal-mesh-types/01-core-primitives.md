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

// Axis-aligned bounding rectangle for spatial region boundaries.
// Used by topology commands, neighbor tracking, and split/merge handoffs.
struct Rect {
    min: Vec2F, // Bottom-left corner (inclusive)
    max: Vec2F, // Top-right corner (exclusive)
}

impl Rect {
    fn contains(&self, point: &Vec2F) -> bool {
        point.x >= self.min.x && point.x < self.max.x
            && point.y >= self.min.y && point.y < self.max.y
    }

    fn width(&self) -> SimFixed { self.max.x - self.min.x }
    fn height(&self) -> SimFixed { self.max.y - self.min.y }
    fn center(&self) -> Vec2F {
        Vec2F {
            x: (self.min.x + self.max.x) / SimFixed::from_num(2),
            y: (self.min.y + self.max.y) / SimFixed::from_num(2),
        }
    }
    fn intersects(&self, other: &Rect) -> bool {
        self.min.x < other.max.x && self.max.x > other.min.x
            && self.min.y < other.max.y && self.max.y > other.min.y
    }
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

// --- SpellData: The Ability/Balance Dictionary ---
// Versioned by data_epoch. Hot-patched at runtime via PrepareDataEpoch / ActivateDataEpoch.
// Designers author individual entries as JSON; the Asset Loader deserializes string enums
// (e.g., "FIRE") into u8 damage_type indices at boot time.
//
// The SpellData dictionary is the top-level container. AbilityEntry is a single row.

struct AbilityEntry {
    ability_id: u16,
    archetype: AbilityArchetype,
    max_range: SimFixed,
    base_damage: u32,
    damage_type: u8,              // Mapped from Damage Type Registry (see Ability Framework appendix)
    knockback_force: SimFixed,
    armor_penetration_pct: SimFixed,
    armor_penetration_flat: SimFixed,
    geometry: CollisionGeometry,  // Determines hit shape and Global Event escalation threshold
    status_effect_id: Option<u16>,

    // Projectile-specific (ignored for instant abilities)
    projectile_speed: SimFixed,   // Units per tick; zero for stationary zones
    lifetime_ticks: u32,          // Max lifetime before despawn
    fuse_ticks: u32,              // Ticks before the projectile becomes "armed" and can detonate
    pierce: u8,                   // Number of targets the projectile can pass through (0 = explode on first hit)
    homing: bool,                 // Whether the projectile steers toward target_id

    // Zone/pulse-specific (used by SpawnZone alias and Global Events)
    pulse_interval_ticks: Option<u32>, // Ticks between pulse damage/heal applications
    duration_ticks: Option<u32>,       // Total zone lifetime in ticks
    target_filters: Option<Vec<u16>>,  // Optional entity tag filters (e.g., TAG_STRUCTURE)
}

enum AbilityArchetype {
    TargetedAbility,
    GroundTargetedAbility,
    SpawnProjectile,
    SpawnZone, // Content-layer alias: compiles to SpawnProjectile with zero velocity + pulse/duration
}

// The full balance dictionary loaded into memory, keyed by data_epoch version.
struct SpellData {
    epoch: u32,
    abilities: HashMap<u16, AbilityEntry>, // Keyed by ability_id
    dilation: DilationConfig,              // Kinematic Dilation tuning (see Configuration Registry)
}

// Retrieves a single ability entry from the currently loaded SpellData dictionary.
// Panics if ability_id is unknown — validation must happen at Edge Node ingress.
fn get_ability_data(ability_id: u16, data_epoch: u32) -> &AbilityEntry;

// 4. Downstream Envelope: From Arbiter to Proxy Actor (Edge Node)
// Defines the strictly quantized wire format for 60Hz state synchronization.
struct ActiveEffectSnapshot {
    effect_id: u16,
    remaining_ticks: u32,
}

struct EntityStateUpdate {
    id: EntityID,
    position: NetVec2,
    velocity: NetVec2,
    hp: i32,
    resource: i32,
    active_buffs: Vec<u16>, // IDs of active effects for client UI/VFX rendering
    // Optional detailed effects payload for bootstrap/reconnect of the owning player.
    // Edge uses remaining_ticks to reconstruct ability cooldown tables.
    active_effects_detailed: Option<Vec<ActiveEffectSnapshot>>,
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
    bucket_index: u16, // Source-side ring slot (diagnostic only; do not trust for destination mapping)
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
    record: EntityRecord, // Contains both SoftState and OffensiveStats
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
