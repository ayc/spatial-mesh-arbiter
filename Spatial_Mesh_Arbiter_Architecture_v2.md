# Architectural Proposal v2

## Spatial Mesh Arbiter Architecture for Large-Scale Real-Time Combat (4k+ Players)

------------------------------------------------------------------------

# 1. Executive Summary

This document proposes a scalable, low-latency architecture for large-scale (4k+ player) real-time combat, specifically tailored for **top-down ARPG, MOBA, or MMO-RTS environments** (mechanically similar to *Diablo*, *League of Legends*, or *Albion Online*). 

Because the game relies on target-locked abilities and traveling projectiles (skillshots) rather than FPS-style zero-width hitscan weapons, the engine is designed without expensive time-travel history buffers. The architecture is fundamentally built upon a **2D Spatially-Aware Actor Model**. It departs from both traditional monolithic servers and generic, asynchronous actor frameworks (which struggle with 60Hz physics and deterministic conflict resolution).

The system is built around three principles:

1.  **Edge Nodes (Proxy Actors) handle immediacy and prediction.**
2.  **Mesh Nodes (Spatial Actors) act as lock-free arbiters (authoritative
    per region).**
3.  **Only hard state transitions are durably committed.**

The architecture does **not** attempt to provide ACID-style global
consistency. Instead, it leverages asynchronous message passing to guarantee:

> Deterministic convergence for contested interactions.

This ensures player agency, consistent bias in combat resolution, and
scalable arbitration without a centralized simulation loop or distributed locks.

------------------------------------------------------------------------

# 2. Architectural Overview (The Spatial Actor Framework)

Traditional Actor Models fail in real-time physics because they process events as fast as they arrive, making the simulation highly sensitive to network jitter. This architecture solves that by injecting a deterministic time-step (Tick) and spatial jurisdiction into the Actor Model.

-   **Message Passing:** Actors share no memory. They communicate exclusively via asynchronous `ActionProposal` envelopes (containing `origin_tick` and `payload`).
-   **Lock-Free Concurrency:** Because a single Microcell Arbiter (Actor) exclusively owns all entities within its bounding box, it processes combat proposals sequentially. This eliminates the need for mutexes when players interact.

## 2.1 Proxy Actors (Edge Nodes)

The architecture operates on a strict **Zero-Trust Client Model**. The client executable running on the user's physical PC is treated as an ultra-thin "dumb terminal" tasked solely with rendering visuals and capturing raw inputs. It is never trusted to send semantic game logic (e.g., "I hit Player X"). 

Instead, the system utilizes the **"Headless Twin" Model**. Proxy Actors act as **Trusted Headless Game Clients** deployed geographically close to the user (e.g., edge datacenters). They execute the exact same core game engine logic as the central Arbiters, but scoped entirely to the individual player's session.

### Responsibilities

-   Maintain client connection (WebSocket/UDP).
-   **Anti-Cheat Validation:** Ingest raw, untrusted client inputs (e.g., `Mouse_Delta`, `Button_Click`) and sanitize them against speed-hacks or impossible angles.
-   **Semantic Translation (The Headless Engine):** Run the actual game engine locally to translate raw inputs into formal `ActionProposals` (e.g., calculating an initial raycast or validating a cooldown before proposing a `TargetedAbility`).
-   Provide immediate player feedback (hitmarkers, recoil, VFX) via prediction.
-   Propose these trusted state changes to the central Mesh Arbiters.

### Non-Responsibilities

-   Finalizing PvP outcomes.
-   Committing hard state changes.
-   Overriding mesh arbitration decisions.

Because Edges act as fully fledged trusted clients, they distribute massive CPU load (like initial collision checks and anti-cheat filtering) away from the central Arbiters. However, due to intra-datacenter transit latency, they remain **proposers**, not final authorities.

### 2.1.1 The Identity Triad (Session vs. Entity)

To support complex game mechanics (like Vehicles, Mind Control, or Combat Disconnects), the architecture mandates a strict decoupling of identity across the network and physics layers.

1.  **The Session (`session_id: UUID`):** The secure, persistent network connection on the Edge Node representing the human player. 
2.  **The Character (`character_id: UUID`):** The persistent database record handled by the Meta Services layer (e.g., Level, Inventory). *Note: The `character_id` is stored exclusively in the Meta Services layer and is never transmitted within the 60Hz Spatial Mesh.*
3.  **The Entity (`entity_id: u64`):** The ephemeral, 60Hz physics body currently instantiated inside the Spatial Arbiter.

The Edge Node acts as the bridge. A single `Session` may temporarily take control of a different `Entity` (e.g., entering a Siege Mech), or multiple `Entities` (e.g., controlling summoned pets). If a player unplugs their router during combat, the `Session` is destroyed, but the `Entity` safely remains in the Spatial Arbiter for a "combat log-out" timer, governed by basic server AI until it is safe to despawn.

------------------------------------------------------------------------

## 2.2 Spatial Actors (Mesh Arbiters)

Because the engine operates in 2D space, the Mesh layer is organized as a **dynamic R-Tree (Bounding Volume Hierarchy)** rather than a rigid quadtree. This allows the Mesh to dynamically create overlapping "Battle Nodes" that tightly wrap dense player hotspots without being constrained by static geographical boundaries.

Each leaf node (Microcell Arbiter) owns:

-   Authoritative state for entities within its 2D spatial region.
-   Combat resolution logic.
-   Arbitration of contested interactions.
-   Emission of committed outcomes.

### Core Invariant & Overlap Resolution

> At any instant, each entity has exactly one authoritative Mesh Arbiter.

Because R-Tree bounding boxes can overlap, Arbiters use a strict, lock-free deterministic tie-breaker to establish jurisdiction:
1.  **Depth:** The Arbiter deepest in the R-Tree (the most localized node) owns the entity.
2.  **ID Tie-Breaker:** If depth is equal, the Arbiter with the lowest `Arbiter_ID` wins.

Each leaf arbiter maintains:

-   Entity transforms (authoritative 2D coordinates).
-   Ephemeral combat state (HP, MP, buffs).
-   Collision geometry relevant to the region.
-   Ghost Entities (lightweight 2D projections of players in overlapping regions).

### Responsibilities

-   Validate proposals from Edge Nodes against the *current* authoritative state.
-   Apply deterministic resolution policies.
-   Emit authoritative outcomes.
-   Commit hard state transitions.

------------------------------------------------------------------------

## 2.3 Ghost Entity Lifecycle

To allow Spatial Actors to resolve combat crossing boundaries without direct cross-server locking, the system utilizes lightweight **Ghost Entities**.

-   **Ownership & Broadcast (Geometric Propagation):** The Arbiter that possesses jurisdiction over an entity is responsible for broadcasting that entity's minimal state (ID, Position, Velocity, Radius) to neighboring Arbiters. This is NOT a pub/sub model. It is purely geometric: if an entity's `VISIBLE_RADIUS` intersects with the spatial Bounding Box (AABB) of a sibling Arbiter, the Ghost is pushed to that sibling. 
-   **Bandwidth Optimization (Velocity-Based Dead Reckoning):** To prevent network floods, Arbiters do **not** send a GhostUpdate every tick. Instead, they utilize delta-compressed updates:
    -   An Arbiter only broadcasts a `GhostUpdate` when an entity's velocity, rotation, or intent (e.g., firing a weapon) changes.
    -   The receiving neighbor Arbiter instantiates the Ghost and **simulates its movement locally** based on the last known velocity.
    -   This reduces intra-mesh bandwidth by >90%, as a player running in a straight line generates zero network traffic between Arbiters.
-   **Low-Cost Drift Guard (Anomaly-Gated):** The receiver does **not** run expensive swept checks for every Ghost every tick. It only triggers validation when displacement is abnormal (e.g., `delta > max_speed * dt + margin`) or when the update is tagged as high-speed/teleport movement. In that case, it performs a single swept-segment test against nearby static collision cells (broadphase-limited, not full-map geometry).
-   **Degraded Fallback & Repair:** If that anomaly-gated sweep detects invalid tunneling (e.g., crossing a wall/out-of-bounds), the Ghost is clamped/frozen at the last valid point and marked `degraded` for a short TTL. The Arbiter immediately requests a reliable `GhostCorrection` keyframe from the owner over RUDP. The owner must respond with a reliable keyframe (`is_keyframe = true`) sourced from authoritative local state. This keeps local raycasts stable while bounding CPU cost.
-   **Downstream Visibility Rule:** The Arbiter's `StateUpdate` to Edge Nodes includes both locally-owned entities and nearby Ghosts (tagged `is_ghost`). This prevents border pop-in and ensures clients can render cross-boundary combat correctly (e.g., projectiles colliding with off-owner targets).
-   **Geometric Role:** Ghost Entities are purely geometric blockers used for raycasting and collision detection. They are **immutable**; they do not receive damage, mutate state, or emit events. 
-   **Resolution via Impact Relay:** Because Ghost tracking relies on UDP dead-reckoning, a Ghost may briefly drift from the true entity if a packet drops. To prevent "phantom dodges" or disappearing projectiles, Arbiters do not silently drop hits on Ghosts. If an Arbiter calculates that a projectile intersects with a Ghost, it destroys the projectile locally and forwards an asynchronous `ImpactEvent` to the Arbiter that owns the true entity.
-   **Event Idempotency Ledger:** To prevent "double-damage" race conditions (where both the owning Arbiter and a neighbor independently resolve the same collision), each Spatial Actor maintains a local **Event Idempotency Ledger**. Any local collision resolution or incoming `ImpactEvent` is checked against this ledger using a unique `(Impact_UUID, Target_ID)` key generated by the Projectile Actor. If the interaction has already been processed for that specific entity, the event is silently discarded, ensuring state mutations are applied exactly once. Because this ledger protects the engine from delayed packets, it is treated as authoritative state and strictly survives server handoffs/splits.
-   **Synchronization:** Ghosts are synchronized via intra-mesh UDP streams at 60Hz (using delta-compression) and are evaluated solely against the current authoritative tick.

------------------------------------------------------------------------

## 2.4 The Arbiter Relay Protocol (Margin of Relevancy)

To solve cross-boundary combat without creating a massive centralized bottleneck at the Parent Node (LCA) or saturating public internet bandwidth with client-side multicasting, the Mesh utilizes a localized peer-to-peer relay protocol.

-   **Single Upstream:** Proxy Actors (Edge Nodes) send `ActionProposals` to exactly **one** Host Arbiter (the primary owner of the player's coordinate).
-   **Intent vs Authority Split:** Edge-originated payloads remain intent-only (e.g., `TargetedAbility { target_id, ability_id }`). Authoritative precomputed combat envelopes (e.g., Thorns/proc reflections) are internal-only `MeshInternalEvent` payloads and are never accepted directly from Edge Nodes.
-   **The Overlap Buffer:** Every Spatial Arbiter maintains an internal geographic "Buffer Zone" along its borders (sized to the maximum range of the game's longest spell/projectile). 
-   **Internal Relaying (TTL=1):** If an Arbiter receives an original `ActionProposal` from a Proxy Actor for an entity standing inside this Buffer Zone, the Arbiter instantly relays a copy to the relevant neighboring Arbiters. To prevent broadcast storms, the Arbiter wraps the payload in a `MeshInternalEvent` envelope. An Arbiter that receives a `MeshInternalEvent` will **never** forward it again, enforcing a strict 1-hop limit based purely on the envelope type.
-   **Lock-Free Resolution:** All receiving Arbiters simulate the relayed action simultaneously against their local entities and Ghosts. The deterministic depth/ID tie-breaker ensures only the rightful owner mutates the state.

------------------------------------------------------------------------

# 3. State Model

## 3.1 Hard State (Durably Committed)

Hard state represents irreversible or economically meaningful
transitions:

-   PlayerDeath
-   Inventory / Equipment changes
-   Respawn
-   Objective completion
-   Currency updates

Hard state is: - Finalized by Mesh Arbiter - Emitted to WAL -
Recoverable after crash

------------------------------------------------------------------------

## 3.2 Soft State (Ephemeral but Authoritative)

Soft state includes:

-   HP / MP
-   Shields
-   Buffs / Debuffs
-   Stuns / CC
-   Knockback
-   Cooldowns

Soft state: - Is not durably committed - Is authoritative within the
Mesh Arbiter - May be predicted by edges - Must converge
deterministically at conflict boundaries

### Rule

> Soft state may diverge temporarily for presentation, but any event
> that influences hard state must be validated by the Mesh Arbiter at
> the moment of transition.

------------------------------------------------------------------------

# 4. Propose → Validate → Commit Model

All contested interactions follow an immediate, forward-moving validation model (no rewinding):

1.  **Edge Proposes**

        ActionProposed { action_id, topology_epoch, actor_id, target_id, t0, action_params }

2.  **Mesh Arbiter Validates**

    -   Check if `target_id` is currently alive and targetable.
    -   Apply resolution policy based on current spatial distance (with internal prediction tolerance margins).
    -   Update ephemeral state immediately.

3.  **Mesh Emits Outcome**

    -   ActionApplied (ephemeral terminal ack for accepted non-movement proposals)
    -   ActionFailed (ephemeral terminal reject/refund for invalid, stale, or saturated proposals)
    -   PlayerDiedCommitted (durable, if threshold crossed)

Edges apply idempotently.

Invariant:
> Every non-movement `proposal_id` must terminate with exactly one `ActionApplied` or `ActionFailed`.

------------------------------------------------------------------------

# 5. Resolution Policies (Top-Down Combat)

Because this is a 2D top-down environment, combat does not rely on zero-width hitscan raycasts or time-travel rewinding. Resolution is based on Target-Locking and Ephemeral Projectiles.

------------------------------------------------------------------------

## 5.1 Target-Locked Resolution (Instant Abilities)

Used for: - Smite - Curses - Direct Melee Strikes

Algorithm: 
-   The Arbiter evaluates the action against the **current authoritative tick**.
-   **Range Check:** Is the distance between the actor and the `target_id` less than or equal to the ability's `Max_Range`?
-   **Prediction Tolerance Margin:** Because the Edge Node (Proxy) is a Trusted Server providing immediate visual prediction to the client, it generates the `origin_tick` when it receives the raw input. The Arbiter expands the `Max_Range` slightly to account *only* for the internal datacenter latency (Edge-to-Arbiter) and microscopic prediction drift. 
-   **Anti-Cheat Posture:** Because this margin does not compensate for the player's public internet ping, it is immune to "Lag Switching" or "Long-Arm" exploits. A player intentionally delaying their packets will simply cause the Edge Node to generate the proposal late, resulting in a natural miss.

------------------------------------------------------------------------

## 5.2 Target-Favoring Resolution (Projectiles)

Used for: - Rockets - Grenades - Slow spells - Traps

Because these objects have a travel time and can cross server boundaries, they are promoted to **Ephemeral Actors** within the Mesh.
-   **Creation:** The Arbiter instantiates the projectile as an independent Actor with its own velocity and ownership receipt (`owner_id`).
-   **Runtime Boundary Handoff (RUDP):** If a projectile crosses a normal sibling boundary, Arbiters use a dedicated lightweight `ProjectileHandoff` protocol over Reliable-UDP (not the split WAL path). This carries a full mid-flight snapshot so the receiver can reconstruct exact state (position, velocity, fuse/lifetime timers, target lock, pierce counters, impact sequence, data epoch).
-   **Split-Safe Ownership:** Projectile Actors obey the exact same single-owner spatial invariant as standard entities. During a split, the surrogate Arbiter assigns each in-flight projectile to exactly one child at the cutover tick using the same jurisdiction tie-breaker (depth, then lowest Arbiter_ID). The non-owner child may keep a shadow copy for observability but must never advance simulation or emit `ImpactEvent`.
-   **Resolution:** The projectile itself carries the detonation logic. When it calculates an impact, it submits a `MeshInternalEvent` (containing an `ImpactEvent` payload) to its host Arbiter. The host Arbiter applies the damage based on Target-Favoring rules (evaluating the victim's position at the exact moment of impact). 
-   **Cross-Boundary Kill Credit:** If a long-range projectile kills a player several Arbiters away, the receiving Arbiter will not have the original attacker in its local memory. This is by design. The receiving Arbiter simply emits the `PlayerDied { killer, victim }` event to the **Meta Services Bus** (Section 9). The Meta Services layer resolves the global IDs and distributes the XP/Loot without the Spatial Mesh ever needing to verify the distant attacker's existence.

### 5.2.1 ProjectileHandoff Protocol (Prepare -> Ack -> Commit)
- **Prepare:** Sender packages `ProjectileSnapshot` plus transfer metadata (`handoff_seq`, `topology_epoch`, `source_tick`, `commit_tick`) and sends to target Arbiter over RUDP.
- **Ack:** Receiver validates epoch/sequence and acks if accepted. Sender remains authoritative until ack is received.
- **Commit:** Authority flips at deterministic `commit_tick`. Before `commit_tick`, sender simulates; after `commit_tick`, receiver simulates. The prior owner transitions to shadow mode.
- **Single-Simulator Invariant:** At any tick, only one Arbiter may advance projectile simulation or emit impacts.
- **Idempotency & Ordering:** Receiver only accepts strictly newer `handoff_seq` for each `projectile_id`. Duplicate/stale Prepare packets are rejected safely.
- **Epoch Change During Transfer:** If handoff `topology_epoch` is stale/new, apply the same surrogate-forwarding or short buffer timeout strategy used by proposal epoch handshake before accepting transfer. Never commit under unresolved epoch disagreement.

------------------------------------------------------------------------

## 5.3 Zone-Favoring Resolution (Large AoE / Global Events)

Used for: - Massive explosions (Nukes) - Environmental destruction - Server-wide objective captures

For abilities whose Area of Effect is larger than the standard Overlap Buffer (e.g., a radius spanning multiple Arbiters), the system cannot rely on the peer-to-peer Relay Protocol, as it would cause a cascading routing flood.

Instead, these events utilize the **Global Event Escalation Protocol**:
-   **Escalation:** The Host Arbiter recognizes the ability radius exceeds its local buffer and asynchronously forwards the `ActionProposal` (including the launch `origin_tick` and effect delay) to the **Mesh Controller**.
-   **Fan-Out & Scheduling:** The Mesh Controller calculates exactly which Arbiters intersect with the event's massive radius. It then schedules the explosion by issuing a top-down command: *"Execute Event X at exactly Future Shard Tick Y."* Crucially, this command includes the full combat identity (Caster ID, Spell ID, **Data Epoch**, and Damage Context) to ensure the Arbiters can accurately apply localized damage and attribute kill credit upon detonation.
-   **Pragmatic Exception:** While the Mesh Controller is primarily a Control Plane component, it acts as a high-level router for these infrequent, high-radius events to prevent P2P network saturation. In practice, these events represent <0.1% of combat traffic.
-   **Lock-Free Synchronized Execution:** Because all Arbiters share a synchronized global Shard Tick (see Section 7.1), the receiving Arbiters hold the command in a queue and independently process the event against their local entities the exact millisecond their local loop reaches `Shard Tick Y`. (Note: In the event of a severe datacenter outage that delays the reliable TCP command past `Tick Y`, the engine uses `>=` fallback logic to detonate the event immediately upon arrival, prioritizing event completion over perfect cross-server sync during disasters).
-   **Epoch Pinning Rule:** Before detonation, each Arbiter validates that the command's `data_epoch` matches its active SpellData dictionary. If mismatched, it must atomically activate that epoch (or delay execution until it can) rather than resolving under a newer/older balance version.
-   **Priority Interrupt (Dilation Override):** Global Events always override Tick Interleaving. Even if an Arbiter is currently skipping frames via Kinematic Dilation (Section 8.2), it is forced to wake up and execute a full simulation frame on the exact scheduled `Shard Tick Y`. This guarantees that simultaneous cross-shard events are never delayed by localized server load.

------------------------------------------------------------------------

# 6. Spatial Partitioning & Rebalancing

## 6.1 Dynamic Microcell Partitioning (R-Tree Hotspots)

The battlefield is not divided by rigid geographical lines. It uses a dynamic R-Tree to map load density.

-   **Empty Space:** Large, shallow nodes manage vast areas of empty map with near-zero CPU cost.
-   **Hotspots:** When player density increases (a battle), the Mesh dynamically spawns a deep, localized "Battle Node" that tightly wraps the combatants, allowing bounding boxes to overlap and slide as the battle moves.
-   **Minimum Cell Size Constraint:** To ensure that standard combat interactions never require more than one network hop, the Mesh Controller enforces a minimum bounding box dimension equal to the game's `MAX_SPELL_RANGE`. This structural constraint guarantees that a TTL=1 relay (Section 2.4) is always sufficient to resolve standard abilities.
-   **Load Shedding:** If a cell reaches the Minimum Cell Size but remains overloaded, the Arbiter transitions to Kinematic Dilation (Section 8.2) rather than further subdivision.
-   **Capacity:** Each leaf node maintains a bounded entity count and bounded event rate.

------------------------------------------------------------------------

## 6.2 Rebalancing Triggers (Deterministic Entity Counts)

Rebalancing is **not** triggered by reactive, hardware-dependent metrics like CPU load or memory pressure. Instead, it is orchestrated entirely by the **Mesh Controller** using deterministic actor counts. 

The Mesh Controller continuously monitors the entity distribution across the map and evaluates it against strict configuration thresholds (e.g., `max_entities_per_arbiter`).

**Rebalancing actions are triggered when:**
- **Splits:** A cell exceeds its `max_entities` limit and its current spatial dimensions are larger than the `min_cell_size` constraint.
- **Merges:** Adjacent sibling cells fall significantly below their entity limits, allowing the Mesh Controller to merge them and spin down the redundant Arbiter process to save server costs (executed via Section 6.4 merge protocol).
- **Boundary Sliding:** A hotspot moves geographically. The Mesh Controller shifts the bounding boxes to keep the mass of entities centered within the cell.

Because splits occur at a deterministic entity threshold (which is intentionally configured to be much lower than the actual hardware CPU limit), the Parent Arbiter is **guaranteed to have computational headroom** available to perform the Hitless Handoff state serialization without dropping 60Hz physics frames.

------------------------------------------------------------------------

## 6.3 Authority Transfer Protocol (Hitless Handoff for Splits)

To avoid latency spikes ("micro-stutters") during cell splits, the system uses a zero-downtime surrogate pattern rather than freezing state.

When a cell (e.g., Microcell A) needs to split into children (B and C):

1.  **Shadow Boot:** Microcells B and C are provisioned in "Shadow Mode" without accepting external traffic.
2.  **Surrogate Operation:** Microcell A continues to operate normally at 60Hz, maintaining absolute authority and acting as a surrogate for the split region.
3.  **State Streaming:** Microcell A streams a snapshot of its state to B and C, followed by a continuous Write-Ahead Log (WAL) of its 60Hz tick changes. To prevent "amnesia bugs" where a newly booted Arbiter double-applies a delayed network packet, **this serialized state transfer must strictly include the Arbiter's Event Idempotency Ledger and all in-flight Projectile Actors**. B and C fast-forward until their internal state exactly matches A.
4.  **Projectile Ownership Assignment at Cutover Tick X:** Before routing flips, A computes each in-flight projectile's authoritative child owner at `Tick X` using the same spatial jurisdiction tie-breaker used for entities (depth, then lowest Arbiter_ID). This decision is serialized with the handoff payload (`projectile_id`, `owner_child_id`, `cutover_tick`, `topology_epoch`).
5.  **Atomic Routing Flip:** Once synchronized (0 frames delta), Microcell A broadcasts a `RoutingUpdate` to the Edge Nodes: "Starting at Tick X, send West traffic to B, East traffic to C."
6.  **Forwarding & Drain:** Edge Nodes update their routes. Any late packets sent to Microcell A are immediately forwarded to the correct new Arbiter. Once drained, A terminates or converts to a Parent Node.

### Requirements & Implementation Constraints for Hitless Handoff:

-   **Strict Idempotency:** Edge proposals must use unique IDs (e.g., `action_id: 99482`). During the routing flip, Edge Nodes may send duplicate proposals to both the surrogate and the new authority. Arbiters must deduplicate these.
-   **Projectile Single-Simulator Rule:** During and after split cutover, only the assigned owner child may tick a projectile forward or generate `ImpactEvent`. Non-owner replicas are shadow-only and are forbidden from simulation side effects.
-   **Over-Provisioning:** The surrogate node will experience a CPU/Memory spike as it simulates combat *while* serializing state and streaming tick updates.
-   **Strict Determinism (The Floating-Point Problem):** Because B and C rely on "fast-forwarding" a WAL of inputs to mathematically catch up to A, the engine's physics simulation must be perfectly deterministic across different CPU architectures. Standard floating-point math (`f32/f64`) will cause microscopic state drift, preventing convergence. **The engine must utilize Fixed-Point Arithmetic** and enforce canonical iteration ordering (e.g., processing entities by ID) to guarantee a byte-for-byte identical state during handoff.

Invariant: > No entity is owned by two arbiters simultaneously, and the simulation never pauses.

------------------------------------------------------------------------

## 6.4 Merge Authority Transfer Protocol (Reverse Handoff)

Merges are not "implicit reversals." They follow an explicit protocol so two live sibling loops can collapse into one authority without double simulation.

When sibling Microcells B and C must merge:

1.  **Deterministic Winner Election:** The Mesh Controller chooses a single `winner_arbiter_id` (default tie-breaker: lowest Arbiter_ID) and a `loser_arbiter_id`, then schedules `cutover_tick = X`.
2.  **Dual-Live Prephase:** B and C continue simulating only their existing regions until `Tick X`. Neither claims merged ownership early.
3.  **Snapshot + WAL Stream (Loser -> Winner):** The loser streams a merge snapshot plus continuous WAL deltas to the winner. The snapshot must include:
    -   all loser-owned entities and authoritative runtime fields
    -   all in-flight Projectile Actors
    -   ghost tables/index state
    -   pending schedulers/queued deterministic commands
    -   the full Event Idempotency Ledger ring with bucket tick metadata
4.  **Catch-Up Barrier:** The winner replays WAL deterministically until it is in-sync and sends `CatchupAck`. The loser forwards this readiness signal to the Mesh Controller.
5.  **Controller-Driven Commit at Tick X:** The Mesh Controller issues `CommitMerge` (reliable TCP, retryable/idempotent). On commit, the winner atomically imports staged state, unions idempotency ledgers, and becomes sole simulator for the merged region; the loser flips immediately to forwarding-only mode (no simulation side effects).
6.  **Drain & Finalize:** For `MAX_EVENT_AGE_TICKS`, the loser forwards late external/internal packets to the winner. After drain completion, controller sends `FinalizeMerge` and the loser process is terminated or returned to pool.

### Merge-Specific Invariants
- **Single-Simulator Invariant:** At any tick, exactly one Arbiter simulates any entity/projectile in the merged region.
- **Ledger Union Rule:** The winner computes `merged_ledger[bucket] = union(winner[bucket], loser[bucket])` for all ring buckets before enabling ownership at `Tick X`.
- **Identity Collision Policy:** `EntityID` must be globally unique. Any collision during import is a protocol fault and forces merge abort/quarantine. Projectile deduplication is keyed by `projectile_id` (UUID) and monotonic handoff metadata.
- **Ghost Promotion Rule:** If an incoming real entity collides with a local ghost of the same `EntityID`, the winner atomically removes the ghost and promotes the real entity in the same frame (never both simultaneously present as active state).
- **Epoch Safety:** Merge stream packets stamped with stale/new topology epochs follow the same surrogate-forwarding or short-buffer rules as proposal epoch handshake.
- **Commit Reliability Rule:** `CommitMerge` is control-plane authoritative and must be retried until acknowledged by both winner and loser. Replays are safe due to `merge_id` idempotency guards.

Invariant: > A merge may change routing, never simulation correctness.

------------------------------------------------------------------------

# 7. The Mesh Controller and Topology Epochs

During dynamic R-Tree rebalancing (splits, merges, or boundary sliding), there is a transient network window where Proxy Actors and Spatial Arbiters might disagree on the current topology. If two overlapping Arbiters both temporarily believe they hold jurisdiction, a "double-write" or double-damage scenario could occur.

To solve this transient disagreement, the architecture introduces a **Mesh Controller** and **Topology Epochs**.

## 7.1 The Mesh Controller (Master Node)

The Mesh Controller lives within the **Tier 2 Simulation Core**. While the Spatial Arbiters act as the *Data Plane* (running the 60Hz physics), the Mesh Controller acts as the *Control Plane*. 

It is a highly consistent, non-spatial service (e.g., a 3-node Raft cluster like etcd) co-located in the same regional datacenter network as the Arbiters. It does not simulate physics and, with the exception of high-radius Global Event routing (Section 5.3), it does not participate in combat resolution. Its primary responsibility is to monitor the entity distribution across the Arbiters and dictate the official shape of the R-Tree based on strict capacity thresholds.

When a rebalance is required, the Mesh Controller calculates the new R-Tree boundaries and publishes a new **Topology Epoch** (a monotonically increasing integer) exclusively to the Arbiters. 

### Edge Node Routing Discovery (Piggyback & Pull)
To prevent the Mesh Controller from becoming a global fan-out bottleneck, Edge Nodes (Proxy Actors) do *not* receive topology updates directly from the Controller. Instead, the architecture utilizes a decentralized discovery mechanism:
1.  **Piggybacking:** Every 60Hz `StateUpdate` packet sent downstream from an Arbiter to an Edge Node includes the Arbiter's current `topology_epoch` in the header.
2.  **Detection:** If an Edge Node receives a packet with an epoch higher than its current known version, it immediately realizes its routing table is stale. 
3.  **Pull Request:** The Edge Node sends an asynchronous `RequestRoutingDelta` back to its Host Arbiter.
4.  **Delivery:** The Arbiter responds with the specific R-Tree boundary changes, allowing the Edge Node to update its local map and begin routing traffic to the correct new spatial owners.

### Reliable Command Transport
To ensure system-wide consistency without the performance cost of distributed locks or quorums, the architecture utilizes three distinct transport channels:
-   **Unreliable Mesh Traffic (Raw UDP):** High-frequency kinematics, continuous movement, and delta-compressed ghost updates. If a packet drops, it is ignored because a newer state will arrive in 16ms.
-   **Reliable Mesh Traffic (RUDP):** Discrete combat events (e.g., relaying an `ActionProposal` or forwarding a cross-boundary `ImpactEvent`). These utilize an application-layer Reliable-UDP implementation (with ACKs and retries) to prevent head-of-line blocking while guaranteeing that damage is never "lost in the ether" when crossing server boundaries. The receiving Arbiter's Idempotency Ledger safely absorbs any duplicate retries.
-   **Control Traffic (TCP):** All top-down Mesh Controller commands (e.g., Global Events, Topology Updates). Because Global Events are scheduled for future Shard Ticks, this reliable layer handles packet loss organically without blocking the 60Hz physics loop.
-   **Intra-Mesh Authentication (RUDP Security):** All intra-mesh RUDP envelopes (`MeshInternalEvent`, `ProjectileHandoff`, merge stream/control messages, reliable ghost corrections) are wrapped with an authenticated header (`auth_epoch`, monotonic nonce, HMAC). Packets failing auth or replay checks are dropped before simulation ingress.

### Global Tick Synchronization (The Metronome)
To allow bullets and entities to seamlessly cross boundaries, the entire Arbiter mesh must operate on a unified temporal baseline, independent of absolute OS wall-clocks.
-   **The Genesis Tick:** The Mesh Controller establishes `Tick = 0` when the shard boots. All Arbiters use this as their absolute timeline integer.
-   **Self-Pacing:** Arbiters run a strict `while(true)` loop, calculating simulation duration and sleeping for the remainder of the 16.6ms frame budget to naturally maintain 60Hz.
-   **Heartbeat Correction:** To prevent micro-drift across different physical machines, the Controller broadcasts a low-frequency UDP Heartbeat (e.g., once per second): *"The current Shard Tick is exactly 360,000."* Arbiters running slightly too fast extend their sleep cycle by 1ms; Arbiters running too slow skip a sleep cycle to snap back into perfect integer alignment.

### Failure State: Topology Freeze
Because the Mesh Controller is the single source of truth for R-Tree boundaries, its availability is critical for dynamic scaling. If the Mesh Controller cluster becomes temporarily unreachable:
-   **The R-Tree Freezes:** Spatial Arbiters lock their current boundaries. No splits, merges, or Hitless Handoffs can occur.
-   **The Simulation Continues:** Because the 60Hz physics loop does not rely on the Mesh Controller, combat and gameplay continue uninterrupted within the frozen topology.
-   **Global Event Rejection:** If an Arbiter attempts to escalate a `TriggerGlobalEvent` (e.g., a Nuke) while the Controller is down, the RPC call will time out. The Arbiter safely aborts the execution and sends an `ActionFailed` payload back to the Proxy Actor to immediately refund the player's cooldown and resources.
-   **Fallback to Kinematic Dilation:** If a localized hotspot grows out of control while the topology is frozen, the overloaded Arbiter relies entirely on **Kinematic Dilation** (Section 8.2) to gracefully degrade and survive until the Mesh Controller recovers and issues a new Epoch.
-   **Expected Survival Window (RTO):** The system is designed to flawlessly absorb standard Raft leader-election outages (2 to 5 seconds) with zero dropped packets and only minor kinematic dilation. However, the degradation cliff occurs around **~30 seconds** of sustained outage. Beyond 30 seconds, severe hotspots will dilate to unacceptable "slideshow" speeds (<0.2x) and risk saturating OS-level connection buffers. Therefore, the Control Plane SLA mandates a Recovery Time Objective (RTO) of < 10 seconds.

## 7.2 The Epoch Handshake Protocol
To guarantee that the Proxy Actor and the Spatial Arbiter agree on the rules of jurisdiction, the map version is strictly enforced at the packet level.

1.  **Epoch Stamping:** When a Proxy Actor generates an `ActionProposal`, it stamps the packet with its currently known `topology_epoch`.
2.  **Epoch Validation:** When a Spatial Arbiter receives the proposal, it checks the epoch before applying the deterministic depth/ID tie-breaker math:
    -   **Epoch Match:** The packet is processed normally.
    -   **Proxy is Stale (Late Packet):** If the packet's epoch is older than the Arbiter's epoch, the map has changed. The Arbiter uses the old map rules to act as a **Forwarding Surrogate**, routing the packet to the newly authoritative Arbiter.
    -   **Arbiter is Stale (Split in Progress):** If the packet's epoch is newer than the Arbiter's epoch, the Arbiter buffers the packet for a few milliseconds until it receives the official epoch update from the Mesh Controller. To prevent infinite stalling if the Controller's update is permanently lost, this buffer enforces a strict timeout tied to the engine's global memory horizon (e.g., 1.0 second). If the timeout expires, the Arbiter rejects the proposal and triggers an `ActionFailed` refund back to the Edge Node.
    -   **Stale Buffer Saturation:** If the stale buffer reaches capacity, Arbiters must reject new non-movement proposals immediately with `ActionFailed { reason: "Arbiter Queue Saturated" }` (never silent drop). `Movement` proposals may be coalesced to latest-per-entity and reconciled via downstream `StateUpdate`.
    -   **Ingress Fairness Guard:** Before a proposal enters `external_inbox`, the Arbiter applies a per-entity token bucket. Over-budget non-movement proposals are rejected with `ActionFailed { reason: "Rate Limited" }`; movement is dropped/coalesced. This isolates compromised sessions and prevents one entity from starving queue capacity for everyone else.

By binding every action to a specific, agreed-upon version of the R-Tree map, the architecture completely eliminates the transient "double-write" vulnerability without requiring distributed locks during the 60Hz tick.

------------------------------------------------------------------------

# 8. Load Management and Graceful Degradation

A key requirement for a 4k+ player mesh is surviving "Blackhole" scenarios, where thousands of players intentionally gather in a microscopic spatial area (e.g., a single room) that the R-Tree cannot meaningfully subdivide without breaking game logic. 

The architecture manages this through a two-tiered defense system:

## 8.1 Prevention via Soft Collision (Incompressible Fluid)
To prevent players from stacking on a single `[x, y]` coordinate, Arbiters enforce **Soft Collision (Separation Steering)** rather than rigid-body physics. 
-   As players crowd together, the steering behavior physically pushes them outward.
-   This acts as an "incompressible fluid," forcing the physical radius of the crowd to expand.
-   As the crowd expands geographically, the dynamic R-Tree regains the ability to slice the hotspot into multiple Arbiter nodes, naturally load-balancing the mass.

## 8.2 Containment via Kinematic Dilation (Tick Interleaving)

If the spatial density exceeds the `max_entities_per_arbiter` limit, but the Arbiter cannot be geographically split further because it has hit the `min_cell_size` structural constraint (e.g., 4,000 players intentionally squeezed into a single room), the architecture does *not* slow down the global clock. Doing so would break cross-boundary bullet travel and Mesh Controller synchronization. 

Instead, the overloaded Arbiter implements **Kinematic Dilation**:

### 8.2.1 The "Temporal Swamp" Philosophy (Diegetic Load Balancing)
Unlike traditional server-side lag, Kinematic Dilation is treated as an **intentional, diegetic environmental hazard**. It is a "Temporal Swamp" that physically slows down the world as density increases.

- **Self-Correcting Incentive:** By making overloaded zones unpleasant to play in (slow movement, delayed ability execution), the engine creates a natural, systemic incentive for players to disperse. This "pushes" the load back out to the R-Tree, allowing the Mesh to subdivide the hotspot naturally.
- **Predictable Degradation:** Because dilation is tied to spatial coordinates and propagated to the Edge Node, it is a deterministic part of the simulation. A player shooting into a dilated zone will see their projectile smoothly decelerate at the boundary.
- **Transparency:** This architecture turns a backend infrastructure limitation (CPU ceiling) into a canon gameplay mechanic.

### 8.2.2 Technical Implementation Details
- **Dynamic Ramp-Up (The Illusion of Time):** The Arbiter continues to increment its global `Shard Tick` at exactly 60Hz. However, as server load increases, it dynamically ramps up a physical slowdown multiplier (e.g., a sliding scale from `dilation = 0.9` down to `0.1`). This multiplier is applied to all physics velocities and game rules (cooldowns). The more people that enter the blackhole, the slower the physical world becomes.
- **CPU Savings (Tick Interleaving):** Because the entities are moving slower, the Arbiter safely skips running heavy $O(N^2)$ collision checks every frame. It may only resolve combat once every 10 ticks, sleeping through the intermediate frames to shed CPU load.
- **Continuous Collision Detection (CCD):** To prevent fast-moving objects from "tunneling" through targets during these skipped frames, the Arbiter dynamically shifts from discrete hitboxes to Swept-Volume raycasts (evaluating the entire path traveled across the interleaved window) to guarantee collision correctness.
- **Per-Session Throttling & Upstream Bandwidth Reduction:** The Arbiter broadcasts this `dilation_factor` downstream. The Edge Node receives it and applies the multiplier **strictly to the specific user's Proxy Actor session state**. Because the Proxy Actor dilates its local prediction loop and ability cooldowns, it creates a self-healing throttle: players physically cannot move or cast spells as fast, which drastically reduces the volume of upstream `ActionProposals` spamming the Arbiter.
- **The Damping Field:** Because dilation is tied to the game's spatial zone and the user's specific session state, a player fighting in the 4,000-player blackhole will experience a cinematic slow-motion battle, while another player connected to the *exact same physical Edge Node* but standing in a quiet forest will continue playing at a flawless 100% speed.

------------------------------------------------------------------------

# 9. The Meta Services Layer (The Platform)

To maintain a lock-free 60Hz physics simulation, the architecture explicitly separates **Spatial Services** (Combat/Movement) from **Meta Services** (Social/Economy). This bifurcated architecture ensures that non-spatial interactions (like Global Chat or Guild Banking) never block the performance of the simulation loop.

## 9.1 The Dual-Layer Architecture

1.  **The Spatial Mesh (The Engine):** A distributed, peer-to-peer mesh of Spatial Actors (R-Tree leaf nodes) simulating 2D physics, combat, and ephemeral Soft State at 60Hz.
2.  **The Meta Services (The Platform):** A suite of horizontally scaled, stateless microservices handling non-spatial logic on **Eventual Consistency**. This layer manages:
    -   **Social Actors:** Guilds, Parties, Friends Lists, Global Chat.
    -   **Economic Actors:** Inventory, Trading, Auction House, Currency.
    -   **Progression Actors:** Quests, Leveling, Achievement Tracking, WAL Persistence.
    -   **Session Manager:** A fast, in-memory registry (e.g., Redis) mapping active User Accounts to their current `EntityID` and Host Arbiter.

## 9.2 The "Sidecar" Dispatch Pattern
The **Proxy Actor (Edge Node)** acts as the primary router for the client. It dispatches traffic to the correct layer based on the semantic intent of the packet:

-   **Simulation Traffic:** Movement, Combat, Interactions -> Dispatched to the **Spatial Mesh** (Single Upstream Dispatch).
-   **Meta Traffic:** Chat, Invites, Trading, Inventory Management -> Dispatched directly to the **Meta Services**.

## 9.3 Cross-Layer Handshake (The Event Bus)
The Spatial Mesh and Meta Services are decoupled but interact through an asynchronous **Hard State Event Bus** (e.g., Kafka or NATS). 

-   **Outbound (Mesh -> Meta):** When a Spatial Actor resolves a hard state transition (e.g., `PlayerDied`), it emits an event to the bus. Meta Services consume this to update quest progress, XP, and durable database records.
-   **Inbound (Meta -> Mesh):** When a Meta Service needs to mutate the simulation (e.g., applying a "Party Heal" buff or a "Banned" status), it sends an asynchronous mutation request to the relevant Spatial Actor, which applies the change in its next 60Hz tick.

Invariant: > The Spatial Mesh never waits for a response from Meta Services. The simulation loop is entirely non-blocking.

## 9.4 Reconnection and Entity Recovery
If a player disconnects during combat, their `Session` on the Edge Node is destroyed, but their `Entity` persists in the Spatial Arbiter under AI control until the combat timer expires. To allow the player to seamlessly rejoin the fight:
1. **The Query:** The player logs back in, potentially hitting an entirely different Edge Node. This new Edge Node queries the **Session Manager** in the Meta Services layer.
2. **The Registry:** The Session Manager responds with the player's active `EntityID` and the IP address of the Spatial Arbiter currently hosting that entity.
3. **The Hijack & Bootstrap:** The new Edge Node connects directly to that Spatial Arbiter, presenting the player's auth token and claiming the `EntityID`. The Arbiter verifies the token, halts the AI control, and immediately pushes a complete `StateUpdate` (HP, coordinates, cooldowns) down to the new Edge Node.
4. **Resumption:** The Edge Node uses this initial snapshot to bootstrap its local prediction loop, and the player resumes combat seamlessly.

------------------------------------------------------------------------

# 10. Divergence Philosophy

The system does not aim for ACID global consistency.

Instead:

-   Soft state may diverge briefly.
-   Outcomes must converge deterministically.
-   There must be exactly one final authoritative ruling for contested
    events.

------------------------------------------------------------------------

# 11. Summary of Authority Model

| Layer | Role |
| :--- | :--- |
| **Client** | Prediction & rendering |
| **Proxy Actor** | Input validation, upstream dispatch, and layer-specific dispatch |
| **Spatial Actor** | 60Hz deterministic conflict resolution & Soft-State authority |
| **Meta Services** | Asynchronous social, economic, and persistent Hard-State authority |
