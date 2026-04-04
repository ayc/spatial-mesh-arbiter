# NPC Runtime and Replication Contract

This document is the canonical architecture/runtime contract for NPC simulation cadence, replication, interest management, reliability classes, and client smoothing behavior.

Canonical split:
- NPC gameplay taxonomy and interaction semantics are canonical in [NPC and World Interaction](../3-gameplay-systems/04-npc-and-world-interaction.md).
- Wire envelope/auth/session contracts remain canonical in [Client-Edge Wire Protocol](../2-contracts-and-interfaces/01-client-edge-wire-protocol.md).

This document is normative. Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used in RFC-style.

---

## 1. Scope

### In scope
- Runtime NPC simulation cadence by tier.
- Replication contract from Arbiter -> Edge/Client.
- Interest rings, per-client update budgets, and prioritization.
- Reliability class by NPC event/delta type.
- Client interpolation/extrapolation and correction behavior.

### Out of scope
- New client->edge intent IDs or envelope shape changes.
- Full dialogue tree data model and quest graph schema.
- Meta-service internal RPC/event schema.

---

## 2. NPC Intelligence Model (Normative)

The engine classifies every NPC into exactly one of two intelligence tiers at **design time**. The boundary between tiers is static — runtime promotion or demotion MUST NOT occur.

### 2.1 Two-Tier Classification

| Property | Arbiter-Local | AI Node |
| :--- | :--- | :--- |
| **Decision origin** | Arbiter `tick()` loop, sub-rate FSM | External AI Node process (Edge Node subclass) |
| **Intelligence model** | Finite state machine with fixed transition rules | Arbitrary decision engine (behavior trees, LLM, scripted AI) |
| **Archetypes** | `LaneCreep`, `NeutralMonster`, `SummonedCombat`, `AmbientFauna` | `BossEncounter`, `SocialServiceNPC`, `ScriptedActor` (complexity-dependent) |
| **Population per shard** | Hundreds to thousands | Tens to low hundreds |
| **Proposal submission** | N/A — decisions execute inline | `ActionProposal` to host Arbiter (identical to player Edge Nodes) |
| **State delivery** | N/A — state is local | `DownstreamPayload` from host Arbiter (identical to player Edge Nodes) |
| **Promotion rules** | Design-time only; MUST NOT promote to AI Node at runtime | Design-time only; MUST NOT demote to Arbiter-Local at runtime |

**Hard rule:** The classification of every NPC archetype MUST be declared in the game data asset at design time. The Arbiter MUST NOT contain code paths that dynamically reclassify an NPC between tiers.

### 2.2 Arbiter-Local NPCs

Arbiter-Local NPCs are unchanged from the existing model. Their decision logic runs inside the Arbiter's `tick()` at sub-rate cadences defined by the tier table (§3.1). The FSM transition rules, leash policies, and aggro models defined in [NPC and World Interaction §3](../3-gameplay-systems/04-npc-and-world-interaction.md) apply directly.

Key properties:
- Decision cadence is governed by runtime tiers T0–T3 (§3.1).
- No external network traffic for decision-making.
- State mutations are applied inline during the Arbiter's simulation tick.
- Replication to clients follows the same interest ring and budget rules as all entities (§4).

### 2.3 AI Node Definition

An **AI Node** is a subclass of Edge Node that hosts AI decision engines for Named NPCs instead of player client sessions. From the Arbiter's perspective, an AI Node is **indistinguishable** from a player Edge Node — it submits `ActionProposal` messages and receives `DownstreamPayload` responses through identical code paths.

```
┌─────────────────┐          ┌─────────────────┐
│  Player Client   │          │   AI Engine      │
│  (Human Input)   │          │  (BT / LLM / …) │
└────────┬────────┘          └────────┬────────┘
         │                            │
         ▼                            ▼
┌─────────────────┐          ┌─────────────────┐
│   Edge Node      │          │   AI Node        │
│  (Proxy Actor)   │          │  (Proxy Actor)   │
└────────┬────────┘          └────────┬────────┘
         │  ActionProposal            │  ActionProposal
         │  DownstreamPayload         │  DownstreamPayload
         ▼                            ▼
┌──────────────────────────────────────────────┐
│              Spatial Arbiter                  │
│           (60 Hz tick loop)                   │
│  No new code paths for AI Node traffic.      │
└──────────────────────────────────────────────┘
```

**Key principle:** The Arbiter MUST use the same ingress, validation, and resolution pipelines for AI Node and player Edge proposals. It MAY branch on entity metadata for lifecycle fallback behavior (for example, player logout fuse vs NPC passive mode), but MUST NOT introduce a separate simulation/network code path for AI traffic.

### 2.4 AI Node Registration and Session Lifecycle

AI Nodes register with the Session Manager using `AiNodeRegistration`, which wraps the standard `EdgeNodeRegistration` with an additional `specialization` field (see [Core Primitives §1.3](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)).

**Registration:**
- AI Nodes share the `edge_node_id` namespace (`u32`) — there is no separate ID space.
- The Session Manager MUST treat `AiNodeRegistration` identically to `EdgeNodeRegistration` for routing, heartbeat tracking, and liveness monitoring.

**Heartbeat contract:**
- AI Nodes MUST maintain the same heartbeat contract as player Edge Nodes:
  ```
  SET edge:{ai_node_id}:heartbeat ALIVE EX 6
  ```
- Heartbeat expiry triggers the same `EdgeNodeDead` pipeline (see §2.5).

**Session mapping:**
- Each Named NPC gets a `SessionMapping` entry where `character_id` is the NPC's persistent UUID (assigned at design time in the game data asset).
- The `entity_id` is allocated by the Arbiter at spawn time, following the standard generational index scheme.

**Spawn flow:**
- Named NPCs are spawned via `MetaCommand::SpawnEntity` — the same command used for player entities.
- The `compiled_state` and `compiled_offense` fields are populated from the NPC's design-time data asset, compiled by Meta Services.

### 2.5 AI Node Crash Recovery

AI Node crash recovery leverages the existing Edge Node crash recovery pipeline (see [Core Concepts and Mesh §9.11](01-core-concepts-and-mesh.md)). No new Arbiter code paths are introduced.

**Detection:**
1. Session Manager detects heartbeat expiry for the AI Node's `edge_node_id`.
2. All `SessionMapping` entries for that AI Node are marked `ORPHANED`.
3. Session Manager publishes `MetaCommand::EdgeNodeDead { edge_node_id, affected_entities }`.

**Arbiter response — behavioral difference from players:**
- For **player** entities: the Arbiter starts `logout_fuse_ticks` (60-second wilderness logout mechanic).
- For **Named NPC** entities: the Arbiter MUST instead enter **passive mode**:
  - Set NPC state to `Idle`.
  - Clear velocity to zero (hold current position).
  - Disable aggro acquisition (non-aggressive).
  - Continue replicating the entity to clients (the NPC remains visible but inert).

The Arbiter determines player vs NPC fallback behavior based on entity metadata — specifically, whether the entity was spawned as an AI-controlled NPC. This is a data-driven branch on existing entity fields, not a new code path in the tick loop.

**Reclamation:**
- A replacement AI Node reclaims orphaned NPCs via the standard Edge Node reconnection flow.
- The AI Node receives a full `StateUpdate` bootstrap for its reclaimed entities.
- On reclamation, the Arbiter exits passive mode and resumes normal proposal processing for the entity.

**Hard despawn timeout:**
- If no AI Node reclaims an orphaned Named NPC within `NPC_ORPHAN_TTL` (default: `120s`), the Arbiter MUST despawn the entity via the standard `NpcLifecycleEvent::Despawned` path.
- `NPC_ORPHAN_TTL` SHOULD be configurable per NPC archetype in the game data asset.

### 2.6 Commander Pattern

The Commander Pattern allows a Named NPC (running on an AI Node) to issue behavioral overrides to Arbiter-Local creeps. This enables rich encounter designs — such as a Necromancer boss commanding undead minions — without promoting the creeps to AI Node intelligence.

**Design invariant:** Creeps remain Arbiter-Local. The Commander Pattern enriches their FSM inputs but does not change their execution model.

**Binding:**
- Commander bindings are established at spawn time via `MetaCommand::BindCommander` (see [Core Primitives §1.3](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)).
- Each `CommanderBinding` associates a commander entity with a group of subordinate entities, a maximum command range, and an override TTL.
- Commander bindings are **Arbiter-local only** — if subordinate creeps migrate to a different Arbiter via handoff, they lose their command override and revert to default FSM behavior.

**Command issuance:**
1. The AI Node submits an `ActionProposal` with `ActionPayload::IssueCreepCommand` as the commander entity.
2. The Arbiter validates:
   - Commander entity is alive and has an active `CommanderBinding` for the targeted creeps.
   - Targeted creeps are within `command_range` of the commander.
   - Targeted creeps are owned by the same Arbiter (Arbiter-local constraint).
3. On success, the Arbiter applies the `CreepDirective` to each targeted creep's FSM as a `command_override`.

**Creep FSM integration:**
- At each decision tick, Arbiter-Local creeps check for an active `command_override` before evaluating default behavior.
- If a `command_override` is present and not expired, the creep executes the directive.
- If the override has expired (`override_ttl_ticks` elapsed without renewal), the creep reverts to default FSM behavior.

**Commander death:**
- On commander death, all subordinate creeps MUST immediately clear their `command_override` and revert to default behavior.

**AI Node crash (commander orphaned):**
- If the commander's AI Node crashes, subordinate creeps hold their last `command_override` for `override_ttl_ticks`, then revert to default behavior.
- This provides a grace period during AI Node recovery without requiring creeps to know about AI Node liveness.

### 2.7 AI Node Cluster Topology

AI Node processes are deployed as a small pool (typically 3–8 processes) per shard. Their scaling is **decoupled** from Spatial Mesh topology — AI Node count is driven by NPC AI workload, not by Arbiter cell count or entity density.

**Specialization:**
- Each AI Node MAY declare a specialization via `AiNodeSpecialization`:
  - `BossEncounter` — optimized for combat-heavy decision engines with low-latency requirements.
  - `SocialDialogue` — optimized for dialogue trees, quest state, and social interaction models.
  - `General` — no specialization; accepts any Named NPC assignment.

**Assignment:**
- An AI Node Orchestrator (part of the Meta Services layer) assigns Named NPCs to AI Nodes based on load and specialization affinity.
- Assignment details are outside the scope of this document — the Arbiter is not aware of which AI Node hosts which NPC.

**Session migration:**
- Named NPCs MAY be migrated between AI Nodes (e.g., for load balancing or specialization reassignment).
- Migration reuses the standard Edge Node reconnection path: the source AI Node releases the session, and the destination AI Node reclaims it.
- From the Arbiter's perspective, this is indistinguishable from a brief AI Node disconnect and reconnection.

### 2.8 AI Node Archetype Catalog

AI Nodes are classified into archetypes based on their **computational profile** — latency budget, decision frequency, state consumption pattern, and whether the entity has a corporeal presence in the world. The archetype determines deployment affinity, interest management configuration, and Orchestrator scheduling.

#### 2.8.1 Corporeal vs Non-Corporeal Entities

An entity in the Arbiter's entity table is a generational index with a `SoftState` record. Nothing in the simulation loop requires that record to represent a physically visible body. AI Node entities fall into two embodiment classes:

- **Corporeal:** The entity has a position, hitbox, HP, and is replicated to clients. Standard interest ring rules apply. Examples: bosses, social NPCs, scripted actors.
- **Non-Corporeal:** The entity exists in the Arbiter's entity table but has no meaningful position, is not replicated to clients, and is excluded from collision and combat processing. The entity serves purely as an authenticated identity for submitting `ActionProposal` messages.

Non-corporeal entities MUST be spawned via `MetaCommand::SpawnEntity` with `is_intangible: true` in entity metadata. The Arbiter MUST skip collision, combat target selection, and client replication for intangible entities. Interest management for non-corporeal entities is configured via an explicit interest set (list of entity IDs or region bounds) rather than position-based rings.

#### 2.8.2 Archetype Definitions

| Archetype | Embodiment | Decision latency budget | Action rate | State read pattern | Typical NPC count per engine |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Reactive Combat | Corporeal | `< 10 ms` | High (abilities + movement every few ticks) | Narrow: nearby entities in combat range | 1–3 |
| Strategic Commander | Corporeal | `50–100 ms` | Medium (group directives, not per-frame) | Wide: positions of many subordinates and players | 1–5 |
| Conversational | Corporeal | `100 ms – 2 s` | Very low (dialogue state transitions) | Narrow: interacting player only | 5–20 |
| Choreographer | Corporeal | `< 5 ms` (tick-precise) | Medium (waypoint + animation commands) | Narrow: own position and scripted triggers | 3–10 |
| Director | Non-Corporeal | `1–10 s` | Very low (spawn directives, difficulty tuning) | Very wide: aggregate world state across regions | 1 |
| Ambient Autonomous (Puppeteer) | Corporeal | `1–5 s` | Low (patrol waypoints, idle behaviors) | Narrow: immediate surroundings | 20–50 |

**Reactive Combat** — Boss encounters, elite named mobs. Behavior trees or hand-tuned FSMs making sub-frame decisions. The defining constraint is latency — the engine MUST respond within a few milliseconds to maintain combat responsiveness. Engines hosting this archetype SHOULD be colocated with the AI Node Runtime to minimize gRPC round-trip. Maps to `AiNodeSpecialization::BossEncounter`.

**Strategic Commander** — Named NPCs using the Commander Pattern (§2.6) to coordinate groups of Arbiter-Local creeps. The AI reasons over spatial formations, threat assessment, and group tactics. Decision latency is relaxed (creep overrides persist via `override_ttl_ticks`), but the world state read set is wide — the engine needs visibility into all subordinate positions and nearby player positions. Maps to `AiNodeSpecialization::BossEncounter` (combat-oriented commanders) or `General`.

**Conversational** — Quest givers, lore NPCs, merchants with dynamic dialogue. MAY integrate LLM inference for freeform conversation. Latency tolerance is high — players expect a pause before dialogue responses. The defining architectural property is **variable and potentially unbounded compute cost per decision** (LLM inference). Engines hosting this archetype MUST be isolated from latency-sensitive archetypes to prevent resource contention. Maps to `AiNodeSpecialization::SocialDialogue`.

**Choreographer** — Scripted actors in cutscenes, world events, tutorials. Requires **tick-precise timing** — movement waypoints and animation triggers MUST land at exact `shard_tick` values. Low decision complexity but strict synchronization requirements. The engine pre-computes a timeline and submits actions keyed to `shard_tick` values from `WorldStateUpdate`. Maps to `AiNodeSpecialization::General`.

**Director** — A non-corporeal meta-level AI that observes aggregate world state and influences the game at a macro level: adjusting spawn wave composition, scaling encounter difficulty based on player performance, triggering ambient world events. Does not control a visible NPC — it claims an intangible entity and submits `ActionProposal` messages that map to `MetaCommand`-style directives. Interest management for Director entities uses region-scoped observation rather than position-based rings. Maps to `AiNodeSpecialization::General`.

**Ambient Autonomous (Puppeteer)** — A single AI Engine claims dozens of Named NPCs (townsfolk with daily routines, wandering merchants, environmental storytellers) and batch-drives their behavior from one decision loop. This is the **puppeteer pattern**: the engine acts as a centralized intelligence giving pseudo-intelligence to many individually simple NPCs.

Key distinction from the Commander Pattern (§2.6): the Commander Pattern operates *within* the Arbiter — a corporeal commander entity issues `IssueCreepCommand` to Arbiter-Local creeps via `command_override`, and the creeps revert to default FSM behavior if the commander dies. The puppeteer pattern operates *outside* the Arbiter — the engine claims each NPC as an independent Named NPC with its own `SessionMapping` and submits `MovementUpdate` / `ActionSubmission` for each directly. The Arbiter sees no relationship between the puppeteered NPCs. There is no in-game binding; coordination is purely engine-side.

These patterns compose: an engine MAY simultaneously puppeteer a group of ambient NPCs *and* use Commander Pattern for a combat encounter NPC that commands Arbiter-Local creeps. A Director (non-corporeal) MAY coordinate multiple puppeteer engines by publishing spawn directives.

The defining property is **high NPC-to-engine ratio** — optimized for throughput over latency. Very low decision frequency (`1–5 s` per NPC).

**Known limitation:** `WorldStateUpdate` delivers the union of interest sets for all claimed NPCs. Puppeteering 50 townsfolk scattered across a town produces a large merged visibility set, much of which is irrelevant to any individual NPC's decision. Per-NPC filtered state delivery is a future optimization — not a blocker at current scale, but engines SHOULD be aware of the bandwidth cost when claiming spatially dispersed NPCs.

Maps to `AiNodeSpecialization::SocialDialogue` or `General`.

#### 2.8.3 Specialization Mapping

The `AiNodeSpecialization` enum (§2.7) maps to archetypes as a scheduling hint for the Orchestrator:

| `AiNodeSpecialization` | Primary archetypes | Scheduling priority |
| :--- | :--- | :--- |
| `BossEncounter` | Reactive Combat, Strategic Commander | Latency-optimized: prefer low-contention nodes with Runtime colocation |
| `SocialDialogue` | Conversational, Ambient Autonomous | Throughput-optimized: allow higher NPC-per-engine packing |
| `General` | Choreographer, Director, overflow | No affinity: accepts any archetype the Orchestrator assigns |

The Orchestrator SHOULD NOT pack `Reactive Combat` and `Conversational` archetypes onto the same AI Engine process. An LLM inference spike on a dialogue NPC MUST NOT starve a boss encounter's decision loop.

### 2.9 NPC Asset and Spawn Data Contract

NPC runtime behavior is data-authored and compiled into the game image. The canonical authoring
model is:

```
NPC YAML definitions   -> EntityDefinitions (game image 0x11)
Spawn rule YAML        -> Static Data Tables / Spawn Tables
```

#### 2.9.1 NPC definition asset

NPC definitions declare the per-archetype runtime state the Arbiter or AI Node consumes:

```yaml
npc:
  npc_type_id: "forest_wolf"
  display_name: "Dire Wolf"
  archetype: "NeutralMonster"
  runtime_tier: 1

  stats:
    max_hp: 450
    movement_speed: 0.35
    base_stats:
      vigor: 15
      fortitude: 10
      agility: 20
    offensive:
      physical_damage: 45
      attack_speed: 1.2
    defensive:
      resistances: { physical: 10, fire: -10 }

  abilities:
    - "wolf_bite"
    - "wolf_howl"

  threat:
    swap_threshold_pct: 0.10
    leash_range: 30.0
    leash_return_speed_multiplier: 2.0
    aggro_range: 15.0

  loot:
    loot_table_id: "forest_wolf_drops"

  lifecycle:
    orphan_ttl_ticks: 600
    despawn_on_owner_death: false
    corpse_duration_ticks: 1800
```

Required invariants:

- `npc_type_id` MUST be unique within a content pack.
- referenced abilities MUST exist in `AbilityDefinitions`
- referenced loot table IDs MUST exist in the loot/Meta content set
- threat, leash, and lifecycle values compile into the same `EntityDefinition_Wire` used at
  runtime by `initialize_spawn_configuration`

#### 2.9.2 Spawn rule asset

Spawn rules are authored separately from NPC definitions so one archetype can appear in many
locations:

```yaml
spawn_rule:
  rule_id: "forest_wolves_zone_a"
  npc_type_id: "forest_wolf"

  location:
    zone_id: "enchanted_forest"
    spawn_points:
      - { position: [150.0, 200.0], radius: 5.0 }
      - { position: [170.0, 210.0], radius: 5.0 }

  population:
    min_alive: 2
    max_alive: 3
    respawn_delay_ticks: 600
    stagger_ticks: 60

  conditions:
    time_of_day: "night"
    quest_flag: null

  patrol:
    mode: "waypoint_loop"
    waypoints:
      - [150.0, 200.0]
      - [165.0, 215.0]
      - [180.0, 200.0]
    pause_at_waypoint_ticks: 180
    patrol_speed_multiplier: 0.7
```

Supported patrol modes are `none`, `waypoint_loop`, `waypoint_bounce`, and `random_wander`.
Waypoints are absolute world coordinates (`Vec2F`) and are consumed by Arbiter-local FSMs or AI
Nodes as advisory path anchors.

#### 2.9.3 Compilation and runtime consumption

The compiler MUST:

1. validate NPC type IDs for uniqueness
2. validate ability, loot, and spawn-rule references
3. compile NPC stats through the same stat-compilation pipeline used for other authored entities
4. serialize NPC archetypes into `EntityDefinitions`
5. serialize spawn rules into `Static Data Tables` / `Spawn Tables`

At runtime:

1. Meta or world scripting reads the compiled spawn tables.
2. Meta issues the appropriate spawn command to the owning Arbiter.
3. The Arbiter calls `initialize_spawn_configuration`.
4. The adapter reads the compiled `EntityDefinitions` entry and returns the NPC's initial state,
   including threat, leash, lifecycle, ability-list, and runtime-tier data.

This keeps NPC runtime behavior authored, compiled, and activated through the same game-image and
adapter boundary used for other entities.

---

## 3. Core Timing Model (Normative)

1. The authoritative world clock MUST remain on the existing fixed mesh tick.
2. NPC AI and movement MAY execute at sub-rates through tier scheduling.
3. Combat outcomes (hit/death/state mutation) MUST remain authoritative on the core world tick path even when decision cadence is lower.

### 3.1 Default NPC runtime tiers

| Tier | Archetype default | Decision tick | Movement integration | Replication cadence |
| :--- | :--- | :--- | :--- | :--- |
| `T0 CombatCritical` | boss phases, high-threat combat NPCs | `15 Hz` | `30 Hz` | near/mid/far = `15/8/2 Hz` |
| `T1 LaneCreep` | lane creeps and simple combat waves | `10 Hz` engaged, `5 Hz` march | `20 Hz` | near/mid/far = `10/5/1 Hz` |
| `T2 Ambient` | fauna/background world actors | `2 Hz` | `10 Hz` | near/far = `5 Hz` / event-only |
| `T3 SocialStatic` | vendors/quest hubs/service NPCs | `1 Hz` | `0 Hz` (static) | event-only + optional `1 Hz` visible keepalive |

### 3.2 Tier assignment defaults

| NPC archetype | Default tier | Note |
| :--- | :--- | :--- |
| `LaneCreep` | `T1 LaneCreep` | |
| `NeutralMonster` | `T0 CombatCritical` while engaged, else `T1 LaneCreep` | |
| `BossEncounter` | `T0 CombatCritical` | AI Node NPC — decision cadence is driven by the AI Node, not the Arbiter's sub-rate scheduler. Replication cadence still applies. |
| `SummonedCombat` | `T0 CombatCritical` while active | |
| `SocialServiceNPC` | `T3 SocialStatic` | AI Node NPC — decision cadence is driven by the AI Node, not the Arbiter's sub-rate scheduler. Replication cadence still applies. |
| `AmbientFauna` | `T2 Ambient` | |
| `ScriptedActor` | `T3 SocialStatic` unless script marks combat-critical window | AI Node when classified as such at design time — decision cadence is driven by the AI Node. |

---

## 4. Interest Management Contract (Normative)

### 4.1 Per-client rings

Each subscribed client view MUST classify visible NPCs into rings:
- `Near`: full combat relevance.
- `Mid`: reduced cadence relevance.
- `Far`: low-rate or event-only relevance.

Default ring thresholds:
- `Near`: `0-35m`
- `Mid`: `35-80m`
- `Far`: `80-140m`
- beyond `140m`: not replicated unless explicit script override.

### 4.2 Hysteresis

Ring promotion/demotion MUST use hysteresis to prevent flapping:
- promote only after crossing inward threshold for `>= 250 ms`,
- demote only after crossing outward threshold for `>= 500 ms`.

### 4.3 Per-client budget and priority

Hard per-client NPC replication budget defaults:
- `32 KiB/s` payload budget for NPC deltas/events.
- `max 64` NPC delta records per replication batch.

If budget pressure occurs, scheduler MUST degrade in this order:
1. preserve lifecycle-critical events,
2. preserve combat-critical deltas,
3. preserve interaction state transitions,
4. degrade/drop ambient/background deltas first.

---

## 5. Replication Interfaces (Documentation-Level Types)

No client->edge wire envelope changes are required in this phase. These types define downstream/runtime replication contract semantics.

```rust
enum NpcRuntimeTier {
    T0CombatCritical,
    T1LaneCreep,
    T2Ambient,
    T3SocialStatic,
}

enum NpcState {
    Idle,
    PatrolMarch,
    AcquireTarget,
    Engaged,
    EvadeLeash,
    DeadCorpse,
    Despawned,
    ConversationLocked,
    ServiceOpen,
    Unavailable,
    ScriptedControl,
    Interactive,
    CinematicLocked,
}

struct NpcStateDelta {
    npc_id: u64,
    npc_type_id: u16,
    state: NpcState,
    pos_q: (i32, i32),   // quantized NetCoord
    vel_q: (i16, i16),   // quantized velocity
    facing_q: i16,       // quantized orientation
    anim_state: u16,
    server_tick: u64,
}

enum NpcLifecycleKind {
    Spawned,
    Despawned,
    Died,
    Respawned,
    StateReset,
}

struct NpcLifecycleEvent {
    npc_id: u64,
    kind: NpcLifecycleKind,
    server_tick: u64,
}

enum NpcInteractionKind {
    InteractionOpened,
    InteractionResolved,
    ObjectiveProgressed,
    LootClaimed,
}

struct NpcInteractionEvent {
    npc_id: u64,
    kind: NpcInteractionKind,
    initiator_entity_id: Option<u64>,
    server_tick: u64,
}

struct NpcReplicationBatch {
    batch_tick: u64,
    priority_tier: NpcRuntimeTier,
    deltas: Vec<NpcStateDelta>,
    lifecycle_events: Vec<NpcLifecycleEvent>,
    interaction_events: Vec<NpcInteractionEvent>,
}
```

### 5.1 Sample payload: combat-critical batch

```json
{
  "batch_tick": 812340,
  "priority_tier": "T0CombatCritical",
  "deltas": [
    {
      "npc_id": 99120044,
      "npc_type_id": 41,
      "state": "Engaged",
      "pos_q": [129440, -23360],
      "vel_q": [122, -18],
      "facing_q": 602,
      "anim_state": 7,
      "server_tick": 812340
    }
  ],
  "lifecycle_events": [],
  "interaction_events": []
}
```

### 5.2 Sample payload: interaction resolution

```json
{
  "batch_tick": 812361,
  "priority_tier": "T1LaneCreep",
  "deltas": [],
  "lifecycle_events": [],
  "interaction_events": [
    {
      "npc_id": 4401,
      "kind": "LootClaimed",
      "initiator_entity_id": 7000021,
      "server_tick": 812361
    }
  ]
}
```

---

## 6. Reliability Matrix

| Signal class | Reliability class | Rule |
| :--- | :--- | :--- |
| `NpcLifecycleEvent::Spawned/Despawned/Died/Respawned/StateReset` | Reliable | MUST be delivered/replayed deterministically before dependent deltas |
| `NpcInteractionEvent::InteractionResolved/ObjectiveProgressed/LootClaimed` | Reliable | MUST be delivered/replayed deterministically |
| `NpcStateDelta` continuous movement/animation | Best-effort | MAY drop under pressure; later authoritative deltas reconcile |
| Ring transitions and tier reclassification notices | Reliable | MUST preserve ordering with lifecycle changes |

Deterministic recovery rule:
- If best-effort deltas are missed, subsequent authoritative deltas MUST converge client state without requiring client->edge protocol changes.

---

## 7. Client Smoothing Contract

1. Client MUST interpolate `NpcStateDelta` by default.
2. Client MAY extrapolate for short gaps up to `120 ms`.
3. Snap correction MUST occur when either condition is true:
   - position error exceeds `2.0m`, or
   - no authoritative delta for `> 500 ms` while entity remains relevant.
4. Lifecycle events MUST be ordered before movement deltas at the same or newer `server_tick`.
5. `Died` or `Despawned` lifecycle events MUST immediately invalidate future interpolation on prior trajectories.

---

## 8. Failure Modes and Edge Cases

### 8.1 Arbiter handoff while NPC engaged
- Handoff boundary transition MUST preserve `npc_id`, state continuity, and monotonic `server_tick`.
- Duplicate deltas around handoff window MAY occur; client MUST keep newest-by-tick.

### 8.2 Bursty combat and budget saturation
- Scheduler MUST preserve reliable events and degrade low-priority ambient deltas first.
- Combat-critical tiers MUST retain minimum replication cadence of `8 Hz` in `Near`.

### 8.3 Interaction contention
- Single-winner interactions (loot/objective claim points) MUST produce exactly one `InteractionResolved` winner event.
- Losers MUST receive deterministic reject/result outcome through existing interaction resolution path.

### 8.4 Edge-node reconnection bootstrap
- Reconnected clients MUST receive an authoritative NPC bootstrap snapshot for `Near` ring before resumptive deltas.
- Bootstrap MAY downsample `Mid/Far` initial rings and backfill progressively.

---

## 9. Conformance Checklist

1. Every NPC archetype has exactly one default tier mapping.
2. Tier cadence table defines decision, movement, and replication rates without gaps.
3. Reliable vs best-effort classification is explicit for all replication signal classes.
4. `world.interact_entity` semantics map to interaction outcomes without new intent IDs.
5. No section introduces required new fields for existing client->edge envelopes.
6. Sample payloads validate against documented fields and ordering constraints.
7. Every NPC archetype has an explicit Arbiter-Local or AI Node classification.
8. AI Node crash recovery follows the existing Edge Node crash recovery path without new Arbiter code paths.
9. Commander bindings are Arbiter-local; cross-boundary commands are not supported.
10. Non-corporeal entities MUST be spawned with `is_intangible: true` and MUST be excluded from collision, combat, and client replication.
11. The Orchestrator MUST NOT co-schedule Reactive Combat and Conversational archetypes on the same AI Engine process.
12. Every AI Node archetype has an explicit `AiNodeSpecialization` mapping.

---

## 10. Cross-References

- NPC gameplay taxonomy and semantics: [NPC and World Interaction](../3-gameplay-systems/04-npc-and-world-interaction.md)
- Edge wire and ingress contract: [Client-Edge Wire Protocol](../2-contracts-and-interfaces/01-client-edge-wire-protocol.md)
- Runtime interfaces companion: [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)
- Edge Node crash recovery: [Core Concepts and Mesh §9.11](01-core-concepts-and-mesh.md)
- AI Node and Commander types: [Core Primitives §1.3](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)
- AI Node gRPC protocol specification: [AI Node Protocol](05-ai-node-protocol.md)
