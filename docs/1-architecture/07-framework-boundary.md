# Framework Boundary: Engine vs. Game Layer

This document defines the contract between the **Spatial Mesh Engine** (the reusable distributed runtime) and the **Game Layer** (the game-specific logic that plugs into it). The engine is designed to support 2D and isometric ARPG/MMO-style games with 4k+ concurrent players, 60Hz deterministic simulation, and zero global locks.

The goal: a game team provides data definitions, stat formulas, and resolution logic. The engine provides the distributed mesh, topology management, deterministic physics, cross-boundary transport, and client connectivity.

Historical note: this document predates the current `docs-core` API v2 terminology in a few places. The authoritative engine/game boundary now lives in `docs-core/04-1-game-adapter-contract.md` and `docs-core/04-2-game-adapter-api-contract.md`, centered on `validate_intent`, `dispatch_stage`, `initialize_spawn_configuration`, and `describe_compatibility`.

---

## 1. Design Principles

1. **Engine owns space and time.** Movement, topology, dilation, ghost replication, tick scheduling, and interest management are engine concerns. The game never touches these directly.

2. **Game owns meaning.** What an ability does, how damage is calculated, what stats exist, what items look like — these are game concerns. The engine transports and schedules; the game resolves.

3. **The boundary is the trait.** The engine defines trait interfaces that the game implements. The engine calls into the game at well-defined points in the tick loop. The game never calls engine internals directly — it returns values and the engine applies them.

4. **Data over code.** Where possible, game behavior is expressed as data (JSON/binary assets loaded via Data Epoch) rather than compiled Rust. The engine provides the asset loading pipeline; the game defines the schema.

5. **The ARPG spec is the first template.** Everything currently in `docs/3-gameplay-systems/` becomes a reference implementation — the "ARPG Starter Kit." Other games (survival MMO, MOBA, sandbox) would provide different implementations of the same trait interfaces.

---

## 2. What the Engine Owns

These systems are game-agnostic and provided by the framework. Game code does not implement or override these.

### 2.1 Spatial Mesh Runtime

| System | Docs |
|:-------|:-----|
| R-Tree topology, cell jurisdiction, overlap buffers | `01-core-concepts-and-mesh.md` §2–4 |
| Split / Merge / Boundary Slide orchestration | `03-mesh-controller.md` §3 |
| Warm Pool lifecycle, capacity management | `03-mesh-controller.md` §4, `01-deployment-and-orchestration.md` |
| Topology epochs, Metronome tick sync | `03-mesh-controller.md` §5–6 |
| Ghost entity replication, dead reckoning, anomaly detection | `01-core-concepts-and-mesh.md` §5 |
| Event idempotency ledger | `01-core-concepts-and-mesh.md` §6 |
| Kinematic Dilation (entity time scaling under load) | `06-kinematic-dilation.md` |

### 2.2 Transport & Connectivity

| System | Docs |
|:-------|:-----|
| Client ↔ Edge WebSocket protocol (envelopes, sequencing, backpressure) | `01-client-edge-wire-protocol.md` |
| Edge ↔ Arbiter RUDP transport | `01-core-concepts-and-mesh.md` §4 |
| Arbiter ↔ Arbiter relay (MeshInternalEvent, 1-hop TTL) | `01-core-concepts-and-mesh.md` §7 |
| Controller ↔ Arbiter TCP command channel | `03-mesh-controller.md` §2 |
| AI Node ↔ AI Engine gRPC sidecar protocol | `05-ai-node-protocol.md` |

### 2.3 Core Tick Loop Structure

The engine owns the 60Hz tick loop and its ordering. The game plugs in at specific extension points (Section 4). The following steps are engine-owned and immutable:

```
0.  Ledger cleanup (O(1) ring rotation)
1.  Controller command buffer drain
2.  Dilation recalculation
3.  Physics simulation (movement integration, collision)     ← engine
4.  Scheduled global event execution                         ← delegates to game
5.  Internal mesh event drain                                ← delegates to game for resolution
6.  External proposal drain (epoch validation, stale buffer) ← delegates to game for resolution
7.  Ghost integration (dead reckoning, anomaly detection)
8.  Ghost broadcast to neighbors
9.  Interest management broadcast to Edge Nodes
10. Merge forwarding
11. GC expired prepares
12. Metronome correction
13. Frame sleep
```

Steps 4, 5, and 6 call into the game layer via traits. All other steps are pure engine.

### 2.4 Determinism Contract

The engine enforces:
- Fixed-point arithmetic (`I32F32` via the `fixed` crate). **f32/f64 forbidden in simulation.**
- Truncation toward zero on all fixed-point conversions.
- Saturating arithmetic on all operations.
- `BTreeMap` for deterministic entity iteration order.
- Local RNG (`WyRand`, OS-entropy seeded). Roll results baked into messages before transmission.
- Self-contained WAL entries (carry all non-deterministic values).

The game layer must use `SimFixed` for all simulation math. The engine provides the RNG interface; the game calls it and receives deterministic results.

### 2.5 Infrastructure

| System | Docs |
|:-------|:-----|
| Deployment (Agones, warm pool, Kubernetes) | `01-deployment-and-orchestration.md` |
| Configuration registry (boot + live variables) | `02-configuration-registry.md` |
| Data Epoch hot-patching pipeline | `03-mesh-controller.md` §7 |
| Event bus (Redpanda) publishing, DLQ, consumer groups | `04-hard-state-events.md` |
| Session management (Redis, heartbeat TTL, orphan cleanup) | `04-meta-services.md` §2 |
| EntityID allocation (generational index, Meta-only) | `01-core-primitives.md` §1 |

---

## 3. What the Game Owns

These are implemented by the game team against engine-provided trait interfaces.

### 3.1 Entity State Schema

The engine provides a minimal `EntityCore` that it reads directly for physics, replication, and interest management:

```rust
/// Engine-owned. Always present on every entity. The engine reads and writes
/// these fields directly during physics, ghost replication, and handoffs.
struct EntityCore {
    position: Vec2F,
    velocity: Vec2F,
    rotation: SimFixed,
    last_movement_tick: u64,

    move_speed: SimFixed,
    weight: SimFixed,          // Knockback resistance
    time_scale: SimFixed,      // KiDi per-entity multiplier (1.0 = normal)

    hp: i32,
    max_hp: i32,
    is_dead: bool,
    is_invulnerable: bool,
}
```

The game defines everything else via an associated type:

```rust
/// Game-provided. Opaque to the engine. Serialized during handoffs,
/// broadcast via interest management, but never read by engine internals.
trait GameEntity: Clone + Send + Sync + 'static {
    /// Game-specific mutable state (resource bars, status effects, cooldowns,
    /// logout fuse, resurrect window, defensive stats, etc.)
    type SoftExt: Clone + Send + Sync + serde::Serialize + serde::de::DeserializeOwned;

    /// Game-specific immutable base stats (offensive stats, compiled from
    /// equipment/attributes by Meta). Replaced atomically via UpdateEntityStats.
    type OffenseExt: Clone + Send + Sync + serde::Serialize + serde::de::DeserializeOwned;
}
```

**In the ARPG template**, `SoftExt` contains `resource`, `max_resource`, `DefensiveStats`, `active_status_effects`, `resurrect_window_ticks`, `logout_fuse_ticks`. `OffenseExt` is the current `OffensiveStats` struct.

**In a MOBA template**, `SoftExt` might contain `mana`, `level`, `gold`, `items_purchased`. `OffenseExt` might be a simpler flat struct without conversion tables.

**In a survival game**, `SoftExt` might contain `hunger`, `thirst`, `temperature`, `carry_weight`. `OffenseExt` might be minimal (weapon damage only).

### 3.2 Action Taxonomy

The engine defines a fixed set of **engine actions** it handles directly:

```rust
/// Engine-owned actions. The game cannot extend this enum.
enum EngineAction {
    Movement { direction: Vec2F, speed_multiplier: SimFixed },
    RequestGhostCorrection { entity_id: EntityID, position: Vec2F },
    UpdateEntityStats { /* ... */ },
}
```

The game registers its own actions via an associated type:

```rust
trait GameActions: Clone + Send + Sync + 'static {
    /// Game-specific action payload (abilities, interactions, consumables, etc.)
    /// Serialized into ActionProposal.payload alongside EngineAction.
    type Action: Clone + Send + Sync + serde::Serialize + serde::de::DeserializeOwned;
}
```

The `ActionPayload` on the wire becomes:

```rust
enum ActionPayload<G: GameActions> {
    Engine(EngineAction),
    Game(G::Action),
}
```

**In the ARPG template**, `G::Action` covers `TargetedAbility`, `GroundTargetedAbility`, `SpawnProjectile`, `UseConsumable`, `Interact`, `IssueCreepCommand`.

The engine handles `EngineAction` variants directly. For `Game(action)`, it routes the work through the game adapter boundary described below.

### 3.3 Combat / Resolution Logic

The engine provides no built-in damage formulas, stat compilation, or combat math. In the current API v2 model, the game implements a stage-aware adapter boundary rather than older monolithic callback patterns:

```rust
trait GameAdapter: Send + Sync + 'static {
    type Entity: GameEntity;
    type Actions: GameActions;

    /// Stage 2 entry point for game-specific validation.
    fn validate_intent(
        &self,
        action: &<Self::Actions as GameActions>::Action,
        actor: &EntityView<Self::Entity>,
        world: &WorldView<Self::Entity>,
        tick: u64,
    ) -> TerminalOutcome;

    /// Unified entry point for Stages 1 and 3-12.
    fn dispatch_stage(
        &self,
        stage_id: StageId,
        batch: &[EntityStageContext<Self::Entity>],
        world: &WorldView<Self::Entity>,
        rng: &mut DeterministicRng,
        tick: u64,
        dilation_factor: SimFixed,
    ) -> StageOutcome<Self::Entity>;

    /// Called when the engine allocates a new entity ID for a spawned actor.
    fn initialize_spawn_configuration(&self, spawn: &SpawnRequest) -> SpawnConfiguration<Self::Entity>;

    /// Startup compatibility negotiation surface.
    fn describe_compatibility(&self) -> CompatibilityDescriptor;
}
```

The adapter returns declarative payloads that the engine applies through its own pipeline:

```rust
struct StageOutcome<E: GameEntity> {
    entity_mutations: Vec<EntityMutation<E>>,
    emitted_events: Vec<ImmediateEvent>,
    deferred_events: Vec<DeferredEvent>,
    faults: Vec<FaultRecord>,
}

enum TerminalOutcome {
    Accept,
    Reject,
}
```

**Key insight:** The engine still owns projectile Actor lifecycle (movement integration, collision detection, boundary handoff, fuse expiry). But when a projectile *hits* or a deferred combat payload becomes ready, the engine does not hand control to a special internal resolver hook. Instead, it injects the resulting payload into the appropriate API v2 stage (typically Stage 7 `PreMitigation`, or Stage 3 `TargetResolution` for spatial timer payloads) and lets the adapter return a declarative `StageOutcome`.

### 3.4 NPC Archetypes

The engine provides:
- FSM execution harness (tick state machines, handle transitions)
- AI Node routing and lifecycle (claim, release, orphan, passive mode)
- Commander pattern infrastructure (binding storage, directive routing)
- Interest management tiers (near/mid/far rings, budget enforcement)

The game defines:
- Archetype registry (which NPC types exist, their allowed states and transitions)
- FSM behavior per state (what "Patrol" means, what "Engaged" means)
- Threat/leash/aggro formulas
- Loot tables and drop logic
- Spawn rules and patrol paths

```rust
trait GameNpcArchetype: Send + Sync + 'static {
    type Entity: GameEntity;

    /// Return the set of valid states for this archetype.
    fn allowed_states(&self) -> &[NpcState];

    /// Called every tick for Arbiter-local NPCs. Returns the NPC's
    /// desired action (move, attack, idle, transition state).
    fn tick(
        &self,
        npc: &NpcView<Self::Entity>,
        world: &WorldView<Self::Entity>,
        rng: &mut DeterministicRng,
        tick: u64,
        dilation_factor: SimFixed,
    ) -> NpcDecision<Self::Entity>;
}
```

### 3.5 Meta Services

The engine provides:
- Event bus consumption framework (consumer groups, offset management, DLQ)
- Session management (Redis, heartbeat TTL, EntityID allocation)
- `UpdateEntityStats` delivery to Arbiter
- Spawn pipeline (auth → zone lookup → Controller query → Arbiter routing)

The game implements service-specific logic behind trait interfaces:

```rust
/// Called during the spawn pipeline. Game provides the entity's initial state.
trait SpawnProvider: Send + Sync + 'static {
    type Entity: GameEntity;

    fn build_initial_state(
        &self,
        character_id: UUID,
        zone_id: u32,
    ) -> (EntityCore, <Self::Entity as GameEntity>::SoftExt, <Self::Entity as GameEntity>::OffenseExt);
}

/// Called when a HardEvent arrives on the event bus. Game handles persistence.
trait HardEventConsumer: Send + Sync + 'static {
    fn on_hard_event(&self, event: HardEvent) -> Result<(), ConsumerError>;
}
```

**In the ARPG template**, these are the Inventory Service, Loot Service, Progression Service, etc. from `04-meta-services.md`.

### 3.6 Intent Registry

The engine reserves intent IDs `0x0000–0x00FF` for engine-level intents (movement, ghost correction, topology sync). The game registers its own intents in `0x0100+` via a static registry provided at startup.

```rust
struct IntentRegistration {
    intent_id: u16,
    name: &'static str,
    lane: IntentLane,  // Simulation, Meta, or Control
}
```

The existing intent taxonomy (`02-intent-taxonomy.md`) becomes the ARPG template's registration set.

### 3.7 Data Assets

The engine provides:
- Asset loading pipeline (download, checksum, atomic swap via Data Epoch)
- Hot-reload notification to Arbiters

The game defines:
- Asset schemas (spell data, NPC definitions, drop tables, attribute formulas)
- Asset parsing and validation logic

---

## 4. The Extension Points (Where Engine Calls Game)

The engine calls into the game layer at these specific extension points:

| Tick Step | Engine Calls | Game Returns |
|:----------|:-------------|:-------------|
| **Startup admission** | `GameAdapter::describe_compatibility()` | `CompatibilityDescriptor` |
| **Stage 2: IntentValidation** | `GameAdapter::validate_intent()` | `TerminalOutcome` (and optionally `StageOutcome` for cast intercepts) |
| **Stages 1 and 3-12** | `GameAdapter::dispatch_stage()` | `StageOutcome` |
| **NPC tick (within Step 3)** | `GameNpcArchetype::tick()` | `NpcDecision` |
| **Spawn** | `GameAdapter::initialize_spawn_configuration()` | `SpawnConfiguration` |
| **Hard event publish** | Engine publishes; `HardEventConsumer::on_hard_event()` on Meta side | Persistence result |

The engine applies the returned `StageOutcome` / `SpawnConfiguration` / `TerminalOutcome` objects through its own scheduler and ownership rules. The game never directly mutates engine state.

---

## 5. Serialization Boundary

During handoffs (split/merge), the engine serializes:

```
EntityRecord<E: GameEntity> {
    entity_id: EntityID,
    core: EntityCore,
    soft_ext: E::SoftExt,      // Game-specific, opaque to engine
    offense_ext: E::OffenseExt, // Game-specific, opaque to engine
}
```

The engine uses `bincode` for all wire serialization. Game types must derive `serde::Serialize` and `serde::Deserialize`. The engine handles chunking, streaming, and reassembly. The game types are serialized as opaque byte blobs from the engine's perspective.

Cross-boundary relay payloads (e.g., `CombatContext` traveling with a projectile) are game-serialized bytes inside a `MeshInternalEvent`. The engine transports them; the game deserializes and resolves them.

---

## 6. What Changes in Existing Docs

| Document | Change |
|:---------|:-------|
| `docs/3-gameplay-systems/*` | Add `README.md` reframing as "ARPG Template — reference implementation of the engine's game layer traits." Content stays as-is. |
| `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` | Split `SoftState` into `EntityCore` (engine) + `SoftExt` (game). Split `ActionPayload` into `EngineAction` + `Game(T)`. Keep current definitions as ARPG template examples. |
| `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` | `SpatialActor` becomes generic over a game adapter boundary. Entity storage becomes `HashMap<EntityID, (EntityCore, G::Entity::SoftExt)>`. Tick loop delegation points are now expressed via API v2 (`validate_intent`, `dispatch_stage`, spawn initialization, compatibility negotiation). |
| `docs/1-architecture/04-meta-services.md` | Reframe as ARPG template services. Extract `SpawnProvider` and `HardEventConsumer` traits into engine spec. Session management and EntityID allocation remain engine-owned. |
| `docs/6-spec-drafts/GAPS_CHECKLIST.md` | Game-specific gaps (T1-01 stat formulas, T1-02 distance falloff, T1-03 combat pipeline, T3-05 threat/leash, T3-06 NPC assets) move to "ARPG Template Gaps" section. Engine gaps remain. |

---

## 7. Impact on Implementation Phases

| Phase | Change from Current Plan |
|:------|:------------------------|
| **Phase 1: shared-types** | Define `EntityCore`, `GameEntity`, `GameActions`, `GameAdapter`, and `GameNpcArchetype` traits plus the API v2 payload types. Define `EngineAction`. Provide ARPG implementations as a `game-arpg` crate (or feature-gated module). |
| **Phase 2: mesh-controller** | No change. Controller is fully engine-owned. |
| **Phase 3: spatial-arbiter** | `SpatialActor` becomes generic over `G: GameAdapter`. Tick loop delegates to `G` through API v2 extension points. Physics, ghosts, dilation, idempotency remain engine code. |
| **Phase 4: edge-node** | Edge Node becomes generic over game intent registry. Wire protocol transport is engine-owned. Game-specific meta request routing delegates to game-provided handlers. |
| **Phase 5: swarm-tester** | Parameterized by game — the ARPG tester uses ARPG actions and assertions. |

---

## 8. What This Enables

With this boundary in place, the engine supports:

- **ARPG MMO** (the current spec): Deep stat systems, loot, cross-boundary combat, AI bosses. The full `docs/3-gameplay-systems/` spec.
- **Isometric MOBA**: Simpler stat model, no loot, lane/objective mechanics. Same mesh topology, same KiDi, same ghost replication. Different `GameAdapter` and `GameNpcArchetype`.
- **Survival MMO**: Hunger/thirst/temperature in `SoftExt`, crafting in Meta services, building placement as game actions. Same spatial partitioning and player density management.
- **MMO-RTS**: Unit groups as entities, Commander pattern repurposed for player-commanded squads, strategic resource nodes as interactables.

The engine's value proposition is the hard distributed systems work — topology, determinism, dilation, handoffs, replication. The game layer is where creative differentiation lives.

---

## 9. Decided: One Stack, One Game

The engine uses **monomorphization** (`SpatialActor<G: GameAdapter>`) — not trait objects. The arbiter binary is compiled per-game with zero-cost dispatch at every extension point. There is no multi-game hosting. A different game pulls in the engine crates as dependencies, implements the traits, and compiles its own binaries.

This is a hard architectural constraint, not an open question. It means:
- No runtime game-switching or hot-loading of game logic.
- The engine is a library/SDK, not a hosted platform.
- Each game's deployment is a fully independent stack (its own arbiters, controller, edge nodes, meta services).

---

## 10. Open Questions

1. **Interest management filtering.** The engine broadcasts `EntityCore` + `SoftExt` to Edge Nodes. Should the game be able to filter or transform `SoftExt` before broadcast (e.g., hide certain fields from enemies)? This would require an additional trait method: `fn filter_for_observer(&self, entity: &SoftExt, observer_id: EntityID) -> SoftExt`.

2. **Projectile parameterization.** Projectiles currently carry game-specific `CombatContext` as opaque bytes. Should the engine understand projectile "type" (dumb-fire vs. homing vs. piercing) or should steering behavior also be game-defined? Current spec has the engine owning steering, which seems right — but the game needs to parameterize it (turn rate, pierce count, fuse duration).

3. **Static geometry.** The `static_grid` (AABB collision, LOS raycasting) is engine-owned. But the map data itself (wall positions, terrain types) is game content loaded via Data Epoch. The loading/parsing boundary needs clarification.
