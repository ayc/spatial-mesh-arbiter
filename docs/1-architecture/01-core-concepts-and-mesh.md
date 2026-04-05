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

-   Maintain client connection (WebSocket).
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

### 2.1.2 EntityID Allocation Contract

`EntityID` must be globally unique at runtime and safe against delayed-packet ABA hazards.

- **Single allocator authority:** Meta Services allocates `EntityID` values (Arbiters never mint IDs locally).
- **Bit layout:** `[32-bit slot index | 32-bit generation]`.
- **Spawn rule:** New entities receive a globally unique slot index with generation initialized to `1`.
- **Reuse rule:** If a slot is reused after despawn, Meta must increment generation before reassignment.
- **Handoff rule:** Splits/merges transfer `EntityID` unchanged; ownership may move, identity never does.
- **Validation rule:** Any duplicate `EntityID` observed during merge import is a protocol fault and must trigger merge abort/quarantine.

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
-   **Ledger Capacity Contract:** `MAX_EVENT_AGE_TICKS` defines replay horizon, not memory safety by itself. Memory is bounded by a per-bucket cap: max keys ~= `MAX_EVENT_AGE_TICKS * idempotency_bucket_capacity`. Capacity planning should assume merge/import headroom and expected key size (`estimated_budget_bytes ~= max_keys * bytes_per_key_estimate`).
-   **Ledger Overflow Policy:** If a dedupe key cannot be inserted because the target bucket is full, Arbiter behavior is fail-closed for cross-boundary impacts: do not apply/relay the impact and increment overflow metrics. This preserves no-double-damage guarantees under pressure at the cost of rare dropped impacts.
-   **Synchronization:** Ghosts are synchronized via intra-mesh UDP streams at 60Hz (using delta-compression) and are evaluated solely against the current authoritative tick.

------------------------------------------------------------------------

## 2.4 The Arbiter Relay Protocol (Margin of Relevancy)

To solve cross-boundary combat without creating a massive centralized bottleneck at the Parent Node (LCA) or saturating public internet bandwidth with client-side multicasting, the Mesh utilizes a localized peer-to-peer relay protocol.

-   **Single Upstream:** Proxy Actors (Edge Nodes) send `ActionProposals` to exactly **one** Host Arbiter (the primary owner of the player's coordinate).
-   **Intent vs Authority Split:** Edge-originated payloads remain intent-only (e.g., `TargetedAbility { target_id, ability_id }`). Authoritative precomputed combat envelopes (e.g., Thorns/proc reflections) are internal-only `MeshInternalEvent` payloads and are never accepted directly from Edge Nodes.
-   **The Overlap Buffer:** Every Spatial Arbiter maintains an internal geographic "Buffer Zone" along its borders (sized to the maximum range of the game's longest spell/projectile). 
-   **Internal Relaying (TTL=1):** If an Arbiter receives an original `ActionProposal` from a Proxy Actor for an entity standing inside this Buffer Zone, the Arbiter instantly relays a copy to the relevant neighboring Arbiters. To prevent broadcast storms, the Arbiter wraps the payload in a `MeshInternalEvent` envelope. An Arbiter that receives a `MeshInternalEvent` will **never** forward it again, enforcing a strict 1-hop limit based purely on the envelope type.
-   **Terminal Authority Rule:** For any `proposal_id`, only the Arbiter owning the proposing `actor_id` may emit terminal `ActionApplied`/`ActionFailed` downstream. Relayed peers never issue terminal outcomes.
-   **Border Target-Locked Rule:** For cross-boundary target-locked hits, the actor-owner Arbiter pre-rolls offensive context and relays an internal authoritative hit envelope to the target-owner Arbiter. The target-owner performs mitigation and state mutation. This prevents fail-vs-hit split-brain outcomes.
-   **Lock-Free Resolution:** All receiving Arbiters simulate the relayed action simultaneously against their local entities and Ghosts. The deterministic depth/ID tie-breaker ensures only the rightful owner mutates the state.

------------------------------------------------------------------------

# 3. State Model

## 3.1 The Classification Rule

> **If losing the data creates an exploit or an inconsistency between two players, it is hard state.** Everything else is soft state.

Apply this test: the arbiter crashes and all in-memory state is lost. For each piece of data, ask:

- **"Can a player profit from the loss?"** If a gold transfer vanishes mid-transaction and one player keeps both the gold and the item, that's an exploit. The transfer must be hard state.
- **"Do two players now disagree about reality?"** If player A believes they own a sword but player B's client shows it in their own inventory, the game is inconsistent. Ownership must be hard state.
- **"Does the player just walk back from town?"** If the only consequence is the player relogs at a save zone with full HP and has to run back to where they were, no harm is done. Position, HP, buffs, and cooldowns are soft state.

When in doubt, ask: *"Would I file a bug report if this data was lost?"* A player losing their position in the world is a minor inconvenience. A player losing a Legendary drop is a support ticket.

## 3.2 Hard State (Durably Committed)

Hard state represents irreversible or economically meaningful transitions:

-   Player death (the *fact* of death — penalties, durability loss, respawn timer)
-   Inventory / Equipment changes
-   Loot ownership (ROLLED → SPAWNED → CLAIMED)
-   Currency transfers (gold, trade, auction)
-   Objective completion
-   Quest / Progression milestones
-   Last save zone (for respawn location on relog)

Hard state is:
- Finalized by the Mesh Arbiter at the moment of transition
- Published as a `HardEvent` to the Event Bus (Redpanda)
- Consumed and persisted by Meta Services into Postgres
- Recoverable after any crash — if the arbiter dies, Meta's `PendingTransaction` ledger reconciles

**Not hard state:** Player x/y coordinates, current HP/mana, active buffs, cooldown timers. These are high-frequency, low-consequence values. Publishing them durably would saturate the event bus for data nobody needs after a crash.

------------------------------------------------------------------------

## 3.3 Soft State (Ephemeral but Authoritative)

Soft state includes:

-   HP / MP / Resource bars
-   Position / Velocity
-   Shields
-   Buffs / Debuffs
-   Stuns / CC
-   Knockback
-   Cooldowns
-   Active status effects

Soft state:
- Is **not** durably committed — lives only in Arbiter memory
- Is authoritative within the owning Mesh Arbiter
- May be predicted by Edge Nodes for client responsiveness
- Must converge deterministically at conflict boundaries
- Is **lost on arbiter crash** — the player relogs with a fresh `SoftState` at their last save zone

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

    -   ActionApplied (ephemeral terminal ack for accepted non-movement proposals; in cross-boundary target-locked races this acknowledges accepted/forwarded intent, not guaranteed remote damage commit)
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
-   **Cross-Border Ownership Rule:** If the target is represented locally as a Ghost, the actor-owner Arbiter must not finalize the target mutation locally. It relays a pre-rolled authoritative hit payload to the target-owner Arbiter for final mitigation/state mutation.
-   **Anti-Cheat Posture:** Because this margin does not compensate for the player's public internet ping, it is immune to "Lag Switching" or "Long-Arm" exploits. A player intentionally delaying their packets will simply cause the Edge Node to generate the proposal late, resulting in a natural miss.

------------------------------------------------------------------------

## 5.2 Target-Favoring Resolution (Projectiles)

Used for: - Rockets - Grenades - Slow spells - Traps

Because these objects have a travel time and can cross server boundaries, they are promoted to **Ephemeral Actors** within the Mesh.
-   **Creation:** The Arbiter instantiates the projectile as an independent Actor with its own velocity and ownership receipt (`owner_id`).
-   **Runtime Boundary Handoff (RUDP):** If a projectile crosses a normal sibling boundary, Arbiters use a dedicated lightweight `ProjectileHandoff` protocol over Reliable-UDP (not the split WAL path). This carries a full mid-flight snapshot so the receiver can reconstruct exact state (position, velocity, fuse/lifetime timers, target lock, pierce counters, ordered carried-target roster, impact sequence, data epoch).
-   **Split-Safe Ownership:** Projectile Actors obey the exact same single-owner spatial invariant as standard entities. During a split, the surrogate Arbiter assigns each in-flight projectile to exactly one child at the cutover tick using the same jurisdiction tie-breaker (depth, then lowest Arbiter_ID). The non-owner child may keep a shadow copy for observability but must never advance simulation or emit `ImpactEvent`.
-   **Resolution:** The projectile itself carries the detonation logic. When it calculates an impact, it submits a `MeshInternalEvent` (containing an `ImpactEvent` payload) to its host Arbiter. The host Arbiter applies the damage based on Target-Favoring rules (evaluating the victim's position at the exact moment of impact). 
-   **Cross-Boundary Kill Credit:** If a long-range projectile kills a player several Arbiters away, the receiving Arbiter will not have the original attacker in its local memory. This is by design. The receiving Arbiter simply emits the `PlayerDied { killer, victim, respawn_delay_credit_ticks, respawn_override }` event to the **Meta Services Event Bus** (Section 9.3). The Meta Services layer resolves the global IDs and distributes the XP/Loot without the Spatial Mesh ever needing to verify the distant attacker's existence.

### 5.2.1 ProjectileHandoff Protocol (Prepare -> Ack -> Commit)
- **Prepare:** Sender packages `ProjectileSnapshot` plus transfer metadata (`handoff_seq`, `topology_epoch`, `source_tick`, `commit_tick`, `prepare_expiry_tick`) and sends to target Arbiter over RUDP.
- **Ack:** Receiver validates epoch/sequence and acks if accepted. Sender remains authoritative until ack is received.
- **Commit:** Authority flips at deterministic `commit_tick`. Before `commit_tick`, sender simulates; after `commit_tick`, receiver simulates. The prior owner transitions to shadow mode.
- **Single-Simulator Invariant:** At any tick, only one Arbiter may advance projectile simulation or emit impacts.
- **Idempotency & Ordering:** Receiver only accepts strictly newer `handoff_seq` for each `projectile_id`. Duplicate/stale Prepare packets are rejected safely.
- **Epoch Change During Transfer:** If handoff `topology_epoch` is stale/new, apply the same surrogate-forwarding or short buffer timeout strategy used by proposal epoch handshake before accepting transfer. Never commit under unresolved epoch disagreement.
- **Carried Target Roster:** If a projectile owns a bounded carried-target roster, `ProjectileSnapshot`
  transfers only the ordered entity IDs. The carried entities themselves remain ordinary entities and
  continue through co-located entity handoff or temporary projectile-shadow following until
  reunified on the receiver.

### 5.2.2 Cross-Boundary Dilation Blend Contract (No Snap)
The overlap buffer is also the deterministic transition band for kinematic dilation during projectile travel.

- **Blend Band Width:** Let `w = cross_boundary_blend_width_meters`, where `0 < w <= overlap_buffer_width_meters`.
- **Signed Distance:** Let `s` be signed distance from projectile position to the shared boundary plane, measured along the source->destination normal.
- **Blend Factor:** `alpha = clamp((s + w/2) / w, 0, 1)`.
- **Effective Dilation:** `effective_dilation = lerp(source_dilation, destination_dilation, alpha)`.
- **Step Integration:** `position_next = position + (velocity * effective_dilation)`.

Normative rules:
- Both Arbiters MUST compute this in fixed-point (`SimFixed`) against the same `topology_epoch` boundary geometry.
- `Prepare`/`Ack`/`Commit` MUST NOT rewrite projectile position or velocity to "force" zone speed changes.
- `commit_tick` flips authority only; kinematics remain continuous by continuing the same blend equation on the receiver.
- Edge prediction SHOULD apply the same blend equation from `TopologyUpdate` (`my_dilation` + neighbor dilation) to avoid client/server divergence near boundaries.

### 5.2.3 Projectile Handoff Failure Semantics (Fail-Closed)
Rare packet-loss + crash windows MUST resolve in favor of safety (no double-simulation), even if this occasionally cancels a projectile.

- **Prepare Expiry:** `Prepare` includes `prepare_expiry_tick` (typically `commit_tick + MAX_EVENT_AGE_TICKS`).
- **No Ack Path:** If sender does not receive `Ack` before `prepare_expiry_tick`, it MUST NOT transfer ownership. It either retries with a newer sequence or deterministically cancels the projectile.
- **No Commit Path:** Receiver keeps prepared state as shadow-only. If `Commit` is not received by `prepare_expiry_tick`, receiver MUST garbage-collect the prepared shadow and MUST NOT simulate it.
- **Crash Declaration Cleanup:** When Controller declares an Arbiter dead, it issues `AbortPendingHandoffs { crashed_arbiter_id }` to neighbor Arbiters so they purge uncommitted prepared shadows sourced from that Arbiter.
- **Restart Safety:** Runtime projectile handoff state is non-durable. On Arbiter restart, pending handoff records are treated as aborted unless a fresh valid `Prepare` arrives under current topology epoch.
- **Invariant Priority:** `Single-Simulator Invariant` takes precedence over continuity. In ambiguous ownership windows, the engine must drop/cancel rather than allow potential dual simulation.

------------------------------------------------------------------------

## 5.3 Zone-Favoring Resolution (Large AoE / Global Events)

Used for: - Massive explosions (Nukes) - Environmental destruction - Server-wide objective captures

For abilities whose Area of Effect is larger than the standard Overlap Buffer (e.g., a radius spanning multiple Arbiters), the system cannot rely on the peer-to-peer Relay Protocol, as it would cause a cascading routing flood.

Instead, these events utilize the **Global Event Escalation Protocol**:
-   **Escalation:** The Host Arbiter recognizes the ability radius exceeds its local buffer and asynchronously forwards the `ActionProposal` (including the launch `origin_tick` and effect delay) to the **Mesh Controller**.
-   **Fan-Out & Scheduling:** The Mesh Controller calculates exactly which Arbiters intersect with the event's massive radius. It then schedules the explosion by issuing a top-down command: *"Execute Event X at exactly Future Shard Tick Y."* Crucially, this command includes the full combat identity (Caster ID, Spell ID, **Data Epoch**, Damage Context, deterministic geometry, and optional target filters/pulse metadata) to ensure the Arbiters can accurately apply localized damage and attribute kill credit upon detonation.
-   **Pragmatic Exception:** While the Mesh Controller is primarily a Control Plane component, it acts as a high-level router for these infrequent, high-radius events to prevent P2P network saturation. In practice, these events represent <0.1% of combat traffic.
-   **Lock-Free Synchronized Execution:** Because all Arbiters share a synchronized global Shard Tick (see Section 7.1), the receiving Arbiters hold the command in a queue and independently process the event against their local entities the exact millisecond their local loop reaches `Shard Tick Y`. (Note: In the event of a severe datacenter outage that delays the reliable TCP command past `Tick Y`, the engine uses `>=` fallback logic to detonate the event immediately upon arrival, prioritizing event completion over perfect cross-server sync during disasters).
-   **Epoch Pinning Rule:** Before detonation, each Arbiter validates that the command's `data_epoch` matches its active SpellData dictionary. If mismatched, it must atomically activate that epoch (or delay execution until it can) rather than resolving under a newer/older balance version.
-   **No Special Dilation Handling:** Because every Arbiter tick is a full simulation tick regardless of Kinematic Dilation (see [Kinematic Dilation](06-kinematic-dilation.md)), Global Events execute on their scheduled tick like any other tick. No priority interrupt or dilation override is needed.

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

1.  **Shadow Boot:** The Mesh Controller provisions Microcells B and C from the Warm Pool in "Shadow Mode" and issues `BeginSplit { split_id, region_b, region_c, new_epoch }` to Arbiter A.
2.  **Surrogate Operation:** Microcell A continues to operate normally at 60Hz, maintaining absolute authority and acting as a surrogate for the split region.
3.  **State Streaming:** Microcell A filters its authoritative state based on the new boundaries and streams `SnapshotChunks` plus a continuous Write-Ahead Log (WAL) of its 60Hz tick changes to B and C. To prevent "amnesia bugs," this serialized state transfer must strictly include the Arbiter's Event Idempotency Ledger and all in-flight Projectile Actors.
4.  **Catch-up:** B and C fast-forward until their internal state exactly matches A. Upon synchronization, they each send `CatchupAck` to A, which A forwards to the Mesh Controller.
5.  **Controller-Driven Commit at Tick X:** Once B and C are ready, the Mesh Controller issues `CommitSplit { split_id, cutover_tick, new_epoch }`. 
6.  **Atomic Routing Flip & Redirect:** At `cutover_tick`, Microcell A broadcasts a final `TopologyUpdate` to its Edge Nodes: "Starting at Tick X, send traffic for Region B to B, and Region C to C." Microcell A then flips to forwarding-only mode. B and C simultaneously promote themselves to authoritative status for their respective regions.
7.  **Drain & Finalize:** For `MAX_EVENT_AGE_TICKS`, A forwards late packets to the new owners. After the drain window, the controller sends `FinalizeSplit` and A returns to the Warm Pool.

### Requirements & Implementation Constraints for Hitless Handoff:

-   **Strict Idempotency:** Edge proposals must use unique IDs (e.g., `action_id: 99482`). During the routing flip, Edge Nodes may send duplicate proposals to both the surrogate and the new authority. Arbiters must deduplicate these.
-   **Projectile Single-Simulator Rule:** During and after split cutover, only the assigned owner child may tick a projectile forward or generate `ImpactEvent`. Non-owner replicas are shadow-only and are forbidden from simulation side effects.
-   **Over-Provisioning:** The surrogate node will experience a CPU/Memory spike as it simulates combat *while* serializing state and streaming tick updates.
-   **Strict Determinism (The Floating-Point Problem):** Because B and C rely on "fast-forwarding" a WAL of inputs to mathematically catch up to A, the engine's physics simulation must be perfectly deterministic across different CPU architectures. Standard floating-point math (`f32/f64`) will cause microscopic state drift, preventing convergence. **The engine must utilize Fixed-Point Arithmetic** (`I32F32` via the `fixed` crate) and enforce canonical iteration ordering to guarantee a byte-for-byte identical state during handoff. The determinism contract is:
    -   **WAL Self-Containment:** Every WAL entry and inter-Arbiter message MUST be self-contained. Any non-deterministic value (RNG roll, external input) used during event resolution MUST be captured in the entry, so that replay produces byte-identical state without re-executing non-deterministic operations.
    -   **RNG is Local:** Combat rolls (crit, evasion, block) use a local PRNG (`WyRand`, OS entropy seed). Roll results are baked into outgoing messages (`CombatContext.is_critical_strike`, `InternalPreparedHit.base_damage`, etc.) and WAL entries. No cross-Arbiter RNG synchronization is needed.
    -   **Rounding:** All `SimFixed` arithmetic uses the `fixed` crate's default truncation toward zero. No banker's rounding. Division and `to_num` truncate.
    -   **Overflow:** All `SimFixed` arithmetic in the simulation loop MUST use saturating variants (`saturating_mul`, `saturating_add`, `saturating_div`). The default `*` operator panics in debug and wraps in release — both unacceptable.
    -   **Iteration Order:** Entity collections use `BTreeMap<EntityID, _>` for deterministic iteration in ascending EntityID order. `HashMap` is permitted only for collections where iteration order does not affect authoritative state (e.g., `ghost_entities`).

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
5.  **Controller-Driven Commit at Tick X:** The Mesh Controller issues `CommitMerge` (reliable TCP, retryable/idempotent). On commit, the winner atomically imports staged state, unions idempotency ledgers, and becomes sole simulator for the merged region. Before the loser enters forwarding-only mode, it must broadcast a final downstream `TopologyUpdate` stamped with `new_epoch` that explicitly redirects its connected Edge Nodes to the winner Arbiter.
6.  **Drain & Finalize:** For `MAX_EVENT_AGE_TICKS`, the loser forwards late external/internal packets to the winner and continues serving (or proxying) `RequestRoutingDelta` for lagging Edge Nodes so all sessions can converge routing without disconnect. After drain completion, controller sends `FinalizeMerge` and the loser process is terminated or returned to pool.

### Merge-Specific Invariants
- **Single-Simulator Invariant:** At any tick, exactly one Arbiter simulates any entity/projectile in the merged region.
- **Ledger Re-Mapping Rule:** The winner does not attempt a naive array-index union of the idempotency ledgers, as the two servers may have slight modulo phase drift. Instead, the Winner iterates over the Loser's `LedgerBucketSnapshot`, reads the absolute `bucket_tick`, calculates its own local index (`bucket_tick % MAX_EVENT_AGE_TICKS`), and extends the records into its own ring buffer. This simple mapping guarantees 100% protection against double-damage without complex phase-alignment math.
- **Identity Collision Policy:** `EntityID` must be globally unique. Any collision during import is a protocol fault and forces merge abort/quarantine. Projectile deduplication is keyed by `projectile_id` (UUID) and monotonic handoff metadata.
- **Ghost Promotion Rule:** If an incoming real entity collides with a local ghost of the same `EntityID`, the winner atomically removes the ghost and promotes the real entity in the same frame (never both simultaneously present as active state).
- **Epoch Safety:** Merge stream packets stamped with stale/new topology epochs follow the same surrogate-forwarding or short-buffer rules as proposal epoch handshake.
- **Commit Reliability Rule:** `CommitMerge` is control-plane authoritative and must be retried until acknowledged by both winner and loser. Replays are safe due to `merge_id` idempotency guards.
- **Edge Reroute Guarantee:** Merge commit is not complete from a networking perspective until loser-connected Edge Nodes receive a deterministic reroute signal (`TopologyUpdate` with redirect) and have a drain window to pull deltas.

Invariant: > A merge may change routing, never simulation correctness.

------------------------------------------------------------------------

## 6.5 Boundary Sliding & Traveling Nodes (The Spotlight Optimization)

While Splits and Merges add or remove server capacity, **Boundary Sliding** addresses a different problem: the moving dense mass. If a 400-player raid runs East across the map, transferring 400 `SoftState` structures and forcing 400 Edge Nodes to reconnect to a new Arbiter every time they cross a static grid line would cause massive latency spikes and RUDP saturation.

Instead, the R-Tree implements **Traveling Nodes**. Because the dynamic R-Tree allows overlapping regions, a deep, localized "Battle Node" essentially acts as a spotlight that floats above the larger, shallow "Background Nodes."

### The Sliding Mechanics (Zero Handoffs for the Mass)
1. **Center of Mass Tracking:** The Mesh Controller monitors the geographic center of mass of the entities within a Battle Node.
2. **The Shift Command:** As the raid moves East, the controller issues an `UpdateTopology` command with a precise `cutover_tick` to the Battle Node and its affected neighbors, shifting the Battle Node's `region_bounds` East.
3. **Continuous Simulation:** Because the 400 raid members remain inside the shifting bounding box, they experience **zero network handoffs, zero RUDP traffic, and no routing flips**. The simulation simply continues uninterrupted while the server's jurisdiction coordinates translate underneath them.

### The Fringe Handoffs (The "Swallow" and the "Drop")
While the massive raid remains stable, the edges of the sliding Battle Node will inevitably sweep over or leave behind scattered players in the Background Nodes. These transitions trigger the **Entity Handoff Protocol** (a lightweight Prepare -> Ack -> Commit sequence over RUDP, identical in shape to the Projectile Handoff).

*   **The Leading Edge (The Swallow):** As the Battle Node slides East, its bounding box overlaps a solo player in the Background Node. Because the Battle Node has a higher `rtree_depth`, it claims jurisdiction. The Background Node detects the overlap, relinquishes authority, and initiates an `EntityHandoff` to push the player *into* the Battle Node.
*   **The Trailing Edge (The Drop):** A raid member goes AFK and stops running. As the Battle Node slides East, the AFK player eventually falls out of the western edge of the bounding box. The Battle Node detects the out-of-bounds entity and initiates an `EntityHandoff` to drop them down into the underlying Background Node.
*   **Standard Boundary Crossing:** This exact same `EntityHandoff` protocol is used when a player normally walks across any static R-Tree boundary.

### Edge Node Routing Migration
During an `EntityHandoff` (whether from walking or sliding), the transition must be seamless for the client. At the `commit_tick` of the handoff, the losing Arbiter sends a `TopologyUpdate` stamped with `redirect_arbiter_id` down to the specific Edge Node. The Edge Node instantly updates its `authoritative_mesh_node` address, seamlessly migrating its UDP upstream stream without dropping the player's connection.

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
-   **Heartbeat Correction:** To prevent micro-drift across different physical machines, the Controller broadcasts a low-frequency UDP Heartbeat (e.g., once per second): *"The current Shard Tick is exactly 360,000."* Arbiters do not instantly snap their clocks; they smoothly adjust their frame sleep duration (+/- a few microseconds) to elegantly catch up or fall back without causing time-travel anomalies.

### Live Game Data Distribution (Hot-Patching)
To support live balance updates ("Hot-Patching") without restarting the server cluster, the Mesh Controller orchestrates the distribution of the `SpellData` dictionaries.
-   **The Command:** The Mesh Controller issues `PrepareDataEpoch { new_epoch, asset_uri }` over TCP.
-   **Asynchronous Loading:** Arbiters spin up a background thread to download the Flatbuffer/JSON assets from the CDN. This ensures the heavy I/O and deserialization do not stall the 60Hz deterministic physics loop.
-   **Atomic Activation:** Once parsed, the background thread pushes the new dictionary into a lock-free queue. The Arbiter adopts the new dictionary and successfully activates the new `data_epoch` for incoming proposals.

### Failure State: Topology Freeze
Because the Mesh Controller is the single source of truth for R-Tree boundaries, its availability is critical for dynamic scaling. If the Mesh Controller cluster becomes temporarily unreachable:
-   **The R-Tree Freezes:** Spatial Arbiters lock their current boundaries. No splits, merges, or Hitless Handoffs can occur.
-   **The Simulation Continues:** Because the 60Hz physics loop does not rely on the Mesh Controller, combat and gameplay continue uninterrupted within the frozen topology.
-   **Global Event Rejection:** If an Arbiter attempts to escalate a `TriggerGlobalEvent` (e.g., a Nuke) while the Controller is down, the RPC call will time out. The Arbiter safely aborts the execution and sends an `ActionFailed` payload back to the Proxy Actor to immediately refund the player's cooldown and resources.
-   **Fallback to Kinematic Dilation:** If a localized hotspot grows out of control while the topology is frozen, the overloaded Arbiter relies entirely on **Kinematic Dilation** (Section 8.2) to gracefully degrade and survive until the Mesh Controller recovers and issues a new Epoch.
-   **Expected Survival Window (RTO):** The system is designed to flawlessly absorb standard Raft leader-election outages (2 to 5 seconds) with zero dropped packets and only minor kinematic dilation. However, the degradation cliff occurs around **~30 seconds** of sustained outage. Beyond 30 seconds, severe hotspots will dilate to unacceptable "slideshow" speeds (<0.2x) and risk saturating OS-level connection buffers. Therefore, the Control Plane SLA mandates a Recovery Time Objective (RTO) of < 10 seconds.

## 7.2 The Epoch Handshake Protocol
To guarantee that the Proxy Actor and the Spatial Arbiter agree on the rules of jurisdiction and balance data, topology and spell-data epochs are strictly enforced at the packet level.

1.  **Epoch Stamping:** When a Proxy Actor generates an `ActionProposal`, it stamps the packet with its currently known `topology_epoch` and `data_epoch`.
2.  **Epoch Validation:** When a Spatial Arbiter receives the proposal, it checks the epoch before applying the deterministic depth/ID tie-breaker math:
    -   **Epoch Match:** The packet is processed normally.
    -   **Proxy is Stale (Late Packet):** If the packet's epoch is older than the Arbiter's epoch, the map has changed. The Arbiter uses the old map rules to act as a **Forwarding Surrogate**, routing the packet to the newly authoritative Arbiter.
    -   **Arbiter is Stale (Split in Progress):** If the packet's epoch is newer than the Arbiter's epoch, the Arbiter buffers the packet for a few milliseconds until it receives the official epoch update from the Mesh Controller. To prevent infinite stalling if the Controller's update is permanently lost, this buffer enforces a strict timeout tied to the engine's global memory horizon (e.g., 1.0 second). If the timeout expires, the Arbiter rejects the proposal and triggers an `ActionFailed` refund back to the Edge Node.
    -   **Stale Buffer Saturation:** If the stale buffer reaches capacity, Arbiters must reject new non-movement proposals immediately with `ActionFailed { reason: "Arbiter Queue Saturated" }` (never silent drop). `Movement` proposals may be coalesced to latest-per-entity and reconciled via downstream `StateUpdate`.
    -   **Ingress Fairness Guard:** Before a proposal enters `external_inbox`, the Arbiter applies a per-entity token bucket. Over-budget non-movement proposals are rejected with `ActionFailed { reason: "Rate Limited" }`; movement is dropped/coalesced. This isolates compromised sessions and prevents one entity from starving queue capacity for everyone else.
    -   **Data Epoch Gate:** If proposal `data_epoch` is stale, reject with `ActionFailed { reason: "Data Epoch Mismatch" }`. If proposal `data_epoch` is newer than local dictionary, Arbiter must atomically activate/buffer with timeout and never resolve under the wrong balance version.

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

## 8.2 Containment via Kinematic Dilation

If the spatial density exceeds the `max_entities_per_arbiter` limit, but the Arbiter cannot be geographically split further because it has hit the `min_cell_size` structural constraint (e.g., 4,000 players intentionally squeezed into a single room), the architecture does *not* slow down the global clock or skip simulation frames. Doing so would break cross-boundary bullet travel and Mesh Controller synchronization.

Instead, the overloaded Arbiter implements **Kinematic Dilation** — a per-entity time multiplier that physically slows all entities within the zone. The Arbiter always runs at full 60Hz; every tick is a full simulation tick. Entities move slower, cast slower, and recover slower — as if wading through thick temporal mud.

**Kinematic Dilation is a core feature of this engine.** The authoritative reference for KiDi — including the formula, what gets dilated, how load reduction works, cross-boundary blending, the client-side KiDi Pressure Gauge, patterns and anti-patterns — is in [Kinematic Dilation](06-kinematic-dilation.md).

### 8.2.1 Summary

- **KiDi is a gameplay mechanic, not a server optimization.** It creates a diegetic "Temporal Swamp" that incentivizes players to disperse.
- **The Arbiter does not skip frames.** Every tick runs the full simulation loop. Entities are slower, not the server.
- **Load reduction is indirect:** the Edge Node throttles player input proportionally to dilation, reducing upstream proposal volume. Slower entities also generate fewer collision and combat events per tick.
- **Cross-boundary blending** ensures smooth projectile deceleration at zone boundaries (see Section 5.2.2).
- **The KiDi Pressure Gauge** is a client-side UI indicator (displayed when `dilation_factor < 1.0`) that telegraphs to players that they are in or approaching a Temporal Swamp.

See [Kinematic Dilation](06-kinematic-dilation.md) for the full specification.

------------------------------------------------------------------------

# 9. The Meta Services Layer (The Platform)

To maintain a lock-free 60Hz physics simulation, the architecture explicitly separates **Spatial Services** (Combat/Movement) from **Meta Services** (Social/Economy). This bifurcated architecture ensures that non-spatial interactions (like Global Chat or Guild Banking) never block the performance of the simulation loop.

## 9.1 The Dual-Layer Architecture

1.  **The Spatial Mesh (The Engine):** A distributed, peer-to-peer mesh of Spatial Actors (R-Tree leaf nodes) simulating 2D physics, combat, and ephemeral Soft State at 60Hz.
2.  **The Meta Services (The Platform):** A suite of horizontally scaled, stateless microservices handling non-spatial logic on **Eventual Consistency**. This layer manages:
    -   **Social Actors:** Guilds, Parties, Friends Lists, Global Chat.
    -   **Economic Actors:** Inventory, Trading, Auction House, Currency.
    -   **Progression Actors:** Quests, Leveling, Achievement Tracking, Hard-State persistence.
    -   **Session Manager:** A fast, in-memory registry (Redis) mapping active User Accounts to their current `EntityID`, Host Arbiter, and serving Edge Node. Also monitors Edge Node liveness via heartbeat TTLs (see Section 9.11).

## 9.2 The "Sidecar" Dispatch Pattern (The Edge Gateway)
The **Proxy Actor (Edge Node)** acts as the primary API Gateway and router for the client. The client sends a multiplexed stream of data, which the Edge Node inspects and dispatches based on semantic intent:

-   **Simulation Traffic (High-Frequency UDP):** Movement, Combat, Interactions -> Dispatched upstream to the currently assigned **Spatial Arbiter**.
-   **Meta Traffic (Reliable gRPC/TCP):** Chat, Invites, Trading, Inventory Management -> Dispatched directly to the **Meta Services**.

**Security Invariant:** The Edge Node is a trusted server. When it dispatches Meta Traffic, it explicitly injects the user's verified `character_id` into the envelope. This prevents spoofing exploits where a compromised client attempts to delete another player's inventory by forging an ID. The Meta Services blindly trust the identity headers provided by the Edge Node.

## 9.3 Cross-Layer Handshake (The Event Bus)
The Spatial Mesh and Meta Services are decoupled but interact through an asynchronous **Hard State Event Bus** backed by **Redpanda (Kafka API)**.

### Why Redpanda
The Event Bus carries Hard State transitions and control commands that need durable replay, consumer fan-out, and clear lag observability while keeping the 60Hz loop isolated from storage and broker latency. Redpanda gives Kafka-compatible semantics (topics, partitions, consumer groups, offsets) without changing game logic contracts.

Redis remains in the stack for Session Manager registry and caching; it is no longer the primary event transport.

### The Durability Contract
All producers and consumers of the Event Bus must satisfy the following guarantees:

| Property | Guarantee |
|:---|:---|
| **Delivery** | **At-least-once.** Every published event will be delivered to each subscribed consumer group at least once. |
| **Consumer Acknowledgment** | Consumers must commit offsets only after durable processing (e.g., Postgres transaction commit). Uncommitted offsets are replayed after restart/rebalance. |
| **Idempotency** | All consumers must be idempotent. Events carry a unique `event_id` (UUID) that consumers use to deduplicate. |
| **Ordering** | Ordered per topic partition (not global). Consumers must not depend on cross-partition ordering. |
| **Retention** | Topic retention is configured by time and/or size. Events older than retention are discarded by broker policy. |
| **Persistence** | Production topics MUST use replicated log durability (`replication.factor >= 3`, `min.insync.replicas >= 2`, producer `acks=all`). |

### Trait Abstraction
To decouple application logic from transport implementation, Arbiters and Meta Services interact with the bus through an `EventBus` trait defined in `shared-types`:

```rust
type MessageRef = (i32, i64); // (partition, offset)

#[async_trait]
trait EventBus: Send + Sync {
    /// Publish a serialized event to a named topic.
    async fn publish(&self, topic: &str, event_id: UUID, payload: &[u8]) -> Result<()>;

    /// Subscribe to a topic as part of a named consumer group.
    async fn subscribe(&self, topic: &str, group: &str, consumer: &str) -> Result<Box<dyn EventStream>>;

    /// Commit progress for a delivered message after durable processing.
    async fn ack(&self, topic: &str, group: &str, message_ref: &MessageRef) -> Result<()>;
}
```

The production implementation targets Redpanda via Kafka protocol clients. Transport can still be swapped through this abstraction if requirements change.

### Event Flow

-   **Outbound (Mesh → Meta):** When a Spatial Actor resolves a hard state transition (e.g., `PlayerDied`), it pushes the event to a non-blocking internal channel. A dedicated async worker publishes it to the Arbiter topic (e.g., `hard_state.arbiter.42`). Meta Services consume via consumer groups to update quest progress, XP, and durable records.
-   **Inbound (Meta → Mesh):** When a Meta Service needs to mutate simulation state (e.g., `SpawnEntity`, `UpdateEntityStats`, ban status), it publishes to a per-Arbiter command topic (e.g., `arbiter.42.commands`). The Arbiter async worker reads and forwards commands into the 60Hz loop through a lock-free channel. Failed commands are retried by Meta; Arbiter deduplicates by `event_id`.

Invariant: > The Spatial Mesh never waits for a response from Meta Services. The simulation loop is entirely non-blocking.

### Topic Partitioning and Surge Resilience

The baseline design uses **per-Arbiter topics** instead of a single shared topic to isolate surges:

```
hard_state.arbiter.{arbiter_id}    // e.g., hard_state.arbiter.42
```

Each Arbiter publishes exclusively to its own topic. Meta service consumer groups subscribe to all active Arbiter topics using a fan-in pattern:

1. **Topic discovery:** Meta services query the Controller's Service Registry to discover active `arbiter_id` values.
2. **Dynamic subscription:** A coordinator task maintains one consumer assignment per active topic. When Arbiters are added (splits) or removed (merges/crashes), assignments are updated.
3. **Per-service consumer groups:** Each Meta service (`group.progression`, `group.loot`, etc.) joins all active Arbiter topics with horizontally scaled workers.

**Why per-Arbiter topics eliminate head-of-line blocking:** A catastrophic AoE wipe in one Arbiter's cell spikes only `hard_state.arbiter.42`. Consumers working other Arbiter topics remain unaffected.

#### Producer Side (Arbiter → Broker)

The HardStatePublisher runs on a dedicated async task and cannot block the 60Hz loop. If broker I/O slows, events queue in the publisher channel plus overflow ring buffer. This is acceptable because:

1. **Bounded channel with overflow ring buffer:** preserves hard-event delivery while keeping push non-blocking from simulation code.
2. **Batched produce calls:** publisher drains channel in batches and emits batched broker writes per wakeup.
3. **No simulation impact:** delayed hard-event propagation only delays durable bookkeeping; it does not stall combat simulation.

#### Consumer Side (Broker → Meta Services)

Each Meta service consumer group scales horizontally. Scaling policy:

| Metric | Threshold | Action |
|:---|:---|:---|
| Consumer lag | > 1000 events | Scale up consumer workers for that group |
| Consumer lag | > 5000 events | Emit `EventBusLagCritical` alert |
| Processing latency p99 | > 500ms | Scale up or investigate slow consumer |
| Consumer lag | < 100 events sustained | Scale down consumer workers |

Lag is measured via broker end offsets minus committed group offsets per topic/partition. The Meta observability stack (§7.2) MUST emit these metrics.

#### Surge Budget Analysis

Worst-case surge scenario: 4,000 players in a single dilated Arbiter cell. A catastrophic AoE wipe kills all 4,000 in a single tick.

| Event Type | Count | Size (est.) | Total |
|:---|:---|:---|:---|
| `PlayerDied` | 4,000 | ~64 bytes | 256 KB |
| Durability loss (via Meta) | 4,000 | N/A (Meta-internal) | N/A |
| `MonsterDied` (if AoE also kills mobs) | ~200 | ~128 bytes | 25 KB |
| `LootSpawned` (from monster deaths) | ~200 | ~256 bytes | 50 KB |

Total burst: ~4,400 events, ~331 KB. This burst is small relative to broker throughput; the real bottleneck remains consumer-side game logic (XP awards, loot processing). Per-Arbiter topic isolation keeps one hotspot from starving global progression processing.

#### Inbound Command Topic (Meta → Arbiter)

The inbound path (`arbiter.{arbiter_id}.commands`) is already per-Arbiter and low-volume. No additional partitioning is required.

### Topic Contract Table (Normative)

The following topic templates are mandatory for production deployments:

| Topic Template | Direction | Key | Partitions | Durability | Retention | Producer | Primary Consumers | Dead Letter Topic |
|:---|:---|:---|:---:|:---|:---|:---|:---|:---|
| `hard_state.arbiter.{arbiter_id}` | Arbiter -> Meta | `event_id` | `1` per topic | `replication.factor=3`, `min.insync.replicas=2` | `72h` | `acks=all`, idempotent producer | `group.progression`, `group.loot`, `group.quest`, other Meta groups | `deadletter.meta.{service}.hard_state` |
| `arbiter.{arbiter_id}.commands` | Meta/Session -> Arbiter | `entity_id` when present, else `event_id` | `1` per topic | `replication.factor=3`, `min.insync.replicas=2` | `6h` | `acks=all`, idempotent producer | Arbiter command worker for that `arbiter_id` | `deadletter.mesh.commands` |
| `controller.mesh.events` | Controller -> Meta | `arbiter_id` | `3` | `replication.factor=3`, `min.insync.replicas=2` | `24h` | `acks=all`, idempotent producer | `group.transaction_reconcile`, `group.spawn_lifecycle` | `deadletter.meta.{service}.controller` |
| `deadletter.meta.{service}.hard_state` | Meta consumer quarantine | source-topic key passthrough | `3` | `replication.factor=3`, `min.insync.replicas=2` | `14d` | produced by failing consumer after retry budget exhausted | Ops/replay tooling only | N/A |
| `deadletter.mesh.commands` | Arbiter command quarantine | source-topic key passthrough | `3` | `replication.factor=3`, `min.insync.replicas=2` | `7d` | produced by Arbiter command worker after retry budget exhausted | Ops/replay tooling only | N/A |

Operational rules:
1. Production MUST disable broker auto-topic-creation. Topics are provisioned by deployment automation.
2. Consumers MUST commit offsets only after durable side effects (database commit or equivalent durable state transition).
3. DLQ payloads MUST include `source_topic`, `source_partition`, `source_offset`, `event_id`, `consumer_group`, `error_code`, and `failed_at_unix_ms`.
4. Topic naming is lower-case, dot-separated, and stable. Renames require dual-write migration.

## 9.4 Reconnection and Entity Recovery
If a player disconnects during combat (client-side network loss or individual session drop), their `Session` on the Edge Node is destroyed, but their `Entity` persists in the Spatial Arbiter under AI control until the combat timer expires. To allow the player to seamlessly rejoin the fight:
1. **The Query:** The player logs back in, potentially hitting an entirely different Edge Node. This new Edge Node queries the **Session Manager** in the Meta Services layer.
2. **The Registry:** The Session Manager responds with the player's active `EntityID` and the IP address of the Spatial Arbiter currently hosting that entity.
3. **The Hijack & Bootstrap:** The new Edge Node connects directly to that Spatial Arbiter, presenting the player's auth token and claiming the `EntityID`. The Arbiter verifies the token, halts the AI control, atomically swaps the downstream `StateUpdate` address to the new Edge Node, and immediately pushes a complete `StateUpdate` (HP, coordinates, cooldowns) down to it.
4. **Resumption:** The Edge Node uses this initial snapshot to bootstrap its local prediction loop, and the player resumes combat seamlessly.

> **Note:** This section covers individual player disconnections. For bulk session loss caused by an Edge Node crash, see Section 9.11.

## 9.5 The Spawn & Logout Protocol (Game Logic Boundaries)
The Spatial Mesh is strictly a physics and combat runner. It does not query databases to find out where a player should spawn. That business logic (e.g., JRPG "Save Zones", Newbie Spawns, and Logout penalties) is entirely orchestrated by the Meta Services.

### The Initial Spawn Handshake
When a player logs in for the first time, or spawns after a death/logout:
1. **The Login (Client -> Meta):** The Edge Node proxies the user's auth directly to the Meta Services (Login Service).
2. **Database / Lifecycle Resolution (Meta):** The Meta Service checks the database for the character's `last_save_zone` coordinates (or defaults to the `NEWBIE_ZONE`), then applies any still-active bounded respawn override for the current death.
3. **Topology Discovery (Meta -> Mesh Controller):** The Meta Service queries the Mesh Controller: *"Which Arbiter currently owns coordinate [x, y]?"* The Controller replies with the target Arbiter's IP.
4. **Engine Injection (Meta -> Arbiter):** The Meta Service sends a `SpawnEntity` command containing the player's compiled `SoftState`, coordinates, and any optional `respawn_context` directly to the target Arbiter via the internal Event Bus.
5. **Connection Handoff (Meta -> Edge Node):** The Meta Service replies to the Edge Node with the target Arbiter's IP address. The Edge Node initiates its UDP stream, and the game begins.

### The Logout Protocol (Combat Logging Prevention)
To prevent players from force-quitting to avoid death, the engine enforces strict logout rules driven by JRPG Save Zones.
*   **Safe Zone Logout:** If a player clicks "Log Out" while standing inside a designated Safe Zone, Meta validates the coordinates and sends an `InitiateLogout { is_safe_zone: true }` command to the Arbiter. The Arbiter instantly despawns the entity.
*   **Wilderness Logout / Force Quit:** If a player logs out in the wild, or their router disconnects, the Arbiter flags their `SoftState` with a 60-second `logout_fuse_ticks`. The character remains fully targetable and killable in the simulation for 60 seconds.
*   **The Next Login:** Regardless of how the player left the game (Safe Zone, survived the 60s fuse, or died), their next login will *always* trigger the Spawn Handshake using the currently active lifecycle route. In the normal case that route is the last recorded JRPG Save Zone. This heavily incentivizes returning to town before logging off.

## 9.6 The Death & Respawn Lifecycle (With Resurrection)
To keep the Spatial Mesh hyper-optimized, the engine uses strictly decoupled death logic, leaning heavily on the Meta Services for spawn orchestration, but preserving a local "Corpse" state for in-combat resurrections.

### Player Death & The Healer Window
When a player's HP reaches 0:
1. **The Kill & Corpse State:** The Arbiter flags the player's `SoftState` as `is_dead = true` and strips their collision geometry. However, the player remains in the Arbiter's memory as a targetable "Corpse" for a brief window (e.g., `resurrect_window_ticks` = 10 seconds). 
2. **The Meta Handoff:** Simultaneously, the Arbiter emits a `PlayerDied` event to the Meta Service. The Meta Service begins ticking down the total MOBA-style base respawn penalty timer (e.g., 15 seconds) and, if the death carried a supported respawn override, also tracks that bounded alternate route until it is either consumed or revoked.
3. **Branch A: The Healer Succeeds:** Before the 10-second corpse window expires, an ally casts a Resurrection spell on the corpse. The Arbiter flips `is_dead = false`, restores HP/collision, and emits `PlayerResurrected` to the Meta Service. Meta instantly cancels the pending 15-second respawn timer. The player is back in the fight.
4. **Branch B: The Hard Wipe:** The 10-second corpse window expires with no heal. The Arbiter permanently deletes the player from its memory and broadcasts a `GhostUpdate { is_despawning: true }` to instantly clear neighboring ghosts. 
5. **The Re-Injection:** When the active respawn timer finishes, the Meta Service automatically executes the **Spawn Handshake (Section 9.5)**, injecting the player at either their designated JRPG Save Zone or one supported bounded override location and redirecting their Edge Node to the new location.

### Monster Death (ARPG Style)
Monsters must leave a presence in the world for players to see and loot.
1. **The Kill:** When a monster dies, the Arbiter removes its AI and attack capabilities but leaves it in a non-colliding `Corpse` state for a set duration to allow client-side death animations to play out.
2. **Loot Generation (Meta):** The Arbiter emits `MonsterDied` to the Meta Service. The Meta Service calculates RNG drop tables and economy limits asynchronously.
3. **Loot Spawning (Meta -> Mesh):** If an item drops, the Meta Service sends a command back to the Arbiter to spawn an ephemeral `LootInteractable` actor at the corpse's coordinates, which players can then interact with to claim the item.

## 9.7 Arbiter Crash Recovery Protocol

The Spatial Arbiter is an ephemeral process. All soft state (HP, position, buffs, projectiles, cooldowns) lives exclusively in memory. When an Arbiter crashes — whether from a process panic, OOM kill, or hardware failure — that state is **irrecoverably lost**. The architecture does not attempt WAL-based recovery for Arbiters; doing so would violate the lock-free, zero-I/O-in-the-hot-loop invariant that makes 60Hz simulation possible.

Instead, the system treats Arbiter crashes as a total-loss event and relies on the Meta Services layer to restore players to a safe, consistent state.

### 9.7.1 Detection

The Mesh Controller monitors Arbiters via periodic `ArbiterHeartbeat` messages over TCP. When heartbeats cease:

1. **Declaration:** After 3 consecutive missed heartbeats (~3 seconds), the Controller declares the Arbiter dead and removes it from the active topology.
2. **Topology Repair:** The Controller issues `UpdateTopology` to neighboring Arbiters, expanding their boundaries to cover the dead cell's region. If the dead cell was too large for a single neighbor to absorb, the Controller may split the region across multiple neighbors.
3. **Ghost Cleanup:** Neighboring Arbiters receive the topology update and garbage-collect all Ghost entities that were sourced from the dead Arbiter (identified by `source_arbiter_id`).
4. **Event Bus Notification:** The Controller publishes an `ArbiterCrashed { arbiter_id, topology_epoch }` event to the Meta Services Event Bus.

### 9.7.2 Entity Fate

All entities (players, monsters, NPCs, projectiles) that were hosted on the dead Arbiter are destroyed. There is no partial recovery from neighbor Ghosts — Ghosts are intentionally lightweight (position, velocity, radius) and lack the full `SoftState` required to reconstruct an entity.

**Player entities:**
- The Session Manager still maps each affected `character_id` → the dead Arbiter's `arbiter_id`.
- On the player's next login, the Spawn Handshake (Section 9.5) detects that the mapped Arbiter is no longer in the active topology.
- Meta clears the stale mapping and executes a standard respawn at the player's last recorded save zone.
- If the player's Edge Node is still connected and attempting to send proposals, the proposals will fail (dead UDP endpoint). The Edge Node detects the connection loss and initiates reconnection through the standard flow (Section 9.4), which routes through Meta and discovers the stale mapping.

**Monster entities:**
- Monsters are ephemeral. The world simulation layer (if applicable) re-spawns them according to its standard spawn schedules. No recovery action is needed.

**In-flight projectiles and active effects:**
- Lost. Projectiles mid-flight are destroyed. Buffs and DoTs active on entities in the dead cell cease to exist. This is consistent with the architecture's position that soft state is expendable — the player simply needs to re-cast.

### 9.7.3 Player Experience

From the player's perspective, an Arbiter crash looks like a brief disconnection followed by respawning at their last save zone. This is identical to the experience of dying and waiting out the respawn timer — a flow the game already supports. The key difference is that the crash bypasses the death penalty (since no `PlayerDied` event was emitted for a crash — the player didn't "die," the server did).

Edge Nodes should present a clear UI message: *"Connection to the battle was lost. You have been returned to your last safe location."* This distinguishes the experience from a player-side network issue.

### 9.7.4 What Is NOT Lost

Because the Meta Services layer is the durable authority, the following survive an Arbiter crash completely intact:

| Data | Why it survives |
|:---|:---|
| Inventory & equipment | Stored in Meta's database. The Arbiter never modifies inventory directly. |
| Currency & gold | Stored in Meta's database. |
| Level, XP, quest progress | Updated by Meta when it consumes `HardEvent` from the Event Bus. Any event published before the crash is durable in Redpanda. |
| Kill credit & boss participation | `MonsterDied` / `PlayerDied` events are published at the moment of death, before loot spawning. If the event reached the broker, it's durable. |
| Loot table rolls | Meta rolls the drop table upon consuming `MonsterDied` and records the results in its database before sending `SpawnLootInteractable` to the Arbiter. |
| Last save zone | Updated by Meta whenever the player visits a save point. |

## 9.8 Cross-Layer Transaction Ledger

Some game actions consume a durable resource (e.g., destroy a potion from inventory) and deliver the value as ephemeral state (e.g., apply a buff in the Arbiter). If the Arbiter crashes after the resource is consumed but before the ephemeral effect is confirmed, the player loses both the item and the benefit.

To prevent this, Meta maintains a **Pending Transaction Ledger** for cross-layer operations.

### 9.8.1 The Pattern

```
Player uses "Elixir of Rage" (consumable item → offensive buff)

1. Edge Node sends "UseItem { item_id: ELIXIR_RAGE }" to Meta (via Meta Traffic path)
2. Meta opens a database transaction:
   a. Removes the Elixir from the player's inventory
   b. Writes PendingTransaction {
        tx_id: UUID,
        character_id,
        tx_type: ConsumeItem,
        item_id: ELIXIR_RAGE,
        arbiter_id,       // The Arbiter that should receive the effect
        created_at: now,
        status: PENDING
      }
   c. Commits both atomically
3. Meta publishes "ApplyBuff { effect_id: EFFECT_ELIXIR_RAGE }"
   to the Arbiter's command stream
4. Arbiter applies the buff and publishes an ack:
   "TransactionConfirmed { tx_id }" to the Event Bus
5. Meta consumes the ack → updates PendingTransaction status to CONFIRMED
```

If step 4 never arrives (Arbiter crash, or timeout), the transaction remains `PENDING` and is eligible for refund.

### 9.8.2 Scope

Not every interaction requires the ledger. It only applies to operations where:

- A **durable resource is consumed** (item destroyed, currency spent), AND
- The **value is delivered as ephemeral state** (buff applied, heal delivered, teleport executed)

Operations that do NOT require the ledger:

| Operation | Why |
|:---|:---|
| Equipment swap | Durable-to-durable. Both old and new states are in Meta's database. |
| Player-to-player trade | Atomic database transaction in Meta. |
| Sell item to NPC vendor | Atomic: item removed, gold added, same transaction. |
| Casting a spell (no consumable) | No durable resource consumed. Cooldowns are ephemeral. |

### 9.8.3 Reconciliation (Login-Time)

Reconciliation is triggered **on the player's next login**, during the Spawn Handshake (Section 9.5):

1. Meta queries: *"Are there any `PENDING` transactions for this `character_id` older than `TRANSACTION_TIMEOUT` (e.g., 30 seconds)?"*
2. For each expired pending transaction:
   a. Mark status as `REFUNDED`
   b. Restore the consumed item to the player's **Recovery Inbox** (Section 9.9)
   c. Log the refund for auditing
3. The Spawn Handshake continues normally.

This approach avoids real-time crash detection complexity on the Meta side. If the Arbiter was alive and just slow, the confirmation ack will arrive and flip the status to `CONFIRMED` before the timeout expires. If the Arbiter crashed, the timeout catches it naturally.

## 9.9 Recovery Inbox (Mail System)

Every character has a **Recovery Inbox** — a durable, append-only collection in Meta's database that serves as a holding area for items that could not be delivered to the player in the simulation.

### 9.9.1 Structure

```rust
struct InboxEntry {
    entry_id: UUID,
    character_id: UUID,
    item_id: u16,
    quantity: u32,
    reason: InboxReason,
    source_tx_id: Option<UUID>,  // Links back to PendingTransaction for audit trail
    created_at: Timestamp,
    claimed: bool,
}

enum InboxReason {
    CrashRefund,          // Item consumed but Arbiter crashed before effect was applied
    DeferredLoot,         // Boss loot eligible for deferred recovery (see Section 9.10)
    AuctionPurchase,      // Bought an item while offline
    GmCompensation,       // Manual grant by game operations
    EventReward,          // Seasonal/promotional reward
}
```

### 9.9.2 Player Flow

1. On login, the Edge Node queries Meta: *"Does this character have unclaimed inbox entries?"*
2. If yes, the client displays a notification (e.g., a mailbox icon or NPC indicator).
3. The player opens the inbox UI and sees entries with human-readable reasons:
   - *"Server disruption — your Elixir of Rage has been returned."* (`CrashRefund`)
   - *"Unclaimed reward from the Dragon of Ashenvale."* (`DeferredLoot`)
4. The player clicks "Claim" → Meta moves the item from the inbox to the player's inventory (a standard atomic database transaction).
5. Unclaimed entries persist indefinitely (or are pruned after a configurable retention period, e.g., 30 days).

### 9.9.3 Design Rationale

The Recovery Inbox is intentionally general-purpose. While its immediate use case is crash recovery refunds, it provides the foundation for any system that needs to deliver items to a player who may not be online or may not be in a location where direct inventory modification is possible. This includes:
- Offline auction house purchases
- Guild bank withdrawals
- GM compensation for bugs or exploits
- Seasonal event rewards

## 9.10 Deferred Loot Recovery

When an Arbiter crashes after a boss kill but before loot is claimed, the loot is **not** automatically mailed to players. Unclaimed loot from a crash is treated as a **deferred recovery opportunity**, not an automatic grant.

### 9.10.1 Why Not Auto-Mail

Auto-mailing boss loot on crash creates exploit vectors and design problems:
- **Duplication risk:** If a player picked up the loot but the `LootClaimed` ack was lost in the crash, auto-mailing would duplicate the item.
- **Loot rules:** Boss loot often requires player interaction (Need/Greed rolls, party leader distribution, DKP systems). Auto-mailing bypasses these social contracts.
- **Economy impact:** Rare items entering the economy without player agency undermines the value of the drop.

### 9.10.2 What Meta Knows After a Crash

The data required for deferred recovery is fully durable:

| Data | Source | Durable? |
|:---|:---|:---|
| Boss identity and kill event | `MonsterDied` published to Event Bus at moment of death | Yes — in Redpanda before crash |
| Kill credit / eligible party | `participating_entities` field in `MonsterDied` | Yes |
| Loot table roll results | Computed and recorded by Meta upon consuming `MonsterDied` | Yes — in Meta's database |
| Whether loot was claimed | Absence of a `LootClaimed` event for this drop | Yes — provable by absence |

### 9.10.3 V1 Recovery Contract (Specified)

V1 deferred loot recovery is implemented as a strict state machine in Meta:

1. `ROLLED`: Meta records loot at `MonsterDied` consume time.
2. `SPAWNED`: Meta issues `SpawnLootInteractable` to the Arbiter.
3. `CLAIMED`: Meta receives `LootClaimed` and finalizes distribution.
4. `DEFERRED`: Arbiter crashes while drop is `SPAWNED` and no `LootClaimed` exists.
5. `EXPIRED`: Deferred claim window ends without valid claim.

V1 player flow:
- Deferred drops are surfaced through a dedicated **Loot Reclamation NPC** (not auto-mailed).
- Eligibility is restricted to the original `participating_entities` set captured on `MonsterDied`.
- Claim window is fixed at `24 hours` from crash declaration (`ArbiterCrashed.declared_dead_at`).
- Distribution rules must reuse the same party loot policy as live drops (Need/Greed/DKP/leader assignment).

The critical invariant is unchanged: **deferred loot must pass through the same social distribution rules as live loot.** It must never bypass Need/Greed, DKP, or party leader authority.

## 9.11 Edge Node Crash Recovery

Edge Nodes are **ephemeral but stateful**. As "Trusted Headless Game Clients" (Section 2.1), they run a full local copy of the game engine scoped to each player's session. This includes a prediction simulation loop, the `SpellData` dictionary for semantic translation, cooldown tracking, anti-cheat input history, entity interpolation buffers, and topology routing state. This is significant runtime state — an Edge Node is not a thin proxy.

However, none of this state is **authoritative**. The Arbiter is the sole source of truth for entity state, and the `SpellData` dictionary is available from the CDN. When an Edge Node crashes, no game state is permanently lost — but the replacement Edge Node must execute a multi-step bootstrap sequence to reconstruct its runtime state before the player can resume (see Section 9.11.5). The challenge is detecting the crash quickly, cleaning up stale sessions, and minimizing the bootstrap time for reconnecting players.

### 9.11.1 Edge Node Registration and Heartbeat

Edge Nodes register with the Session Manager on boot and maintain liveness via a heartbeat contract:

1. **Registration:** On startup, the Edge Node authenticates with the Session Manager and registers itself, providing its routable address and capacity metadata. The Session Manager records the Edge Node in an active registry.
2. **Heartbeat:** Every 2 seconds, the Edge Node writes a heartbeat to the Session Manager. This is implemented as a Redis `SET` with a short TTL (e.g., 6 seconds / 3 missed beats):
   ```
   SET edge:{edge_node_id}:heartbeat ALIVE EX 6
   ```
3. **Liveness Check:** The Session Manager considers an Edge Node dead when its heartbeat key expires. No polling is required — Redis key expiry handles detection automatically.

### 9.11.2 Crash Detection and Session Orphaning

When an Edge Node's heartbeat TTL expires:

1. **Declaration:** The Session Manager marks the Edge Node as `DEAD` in its registry.
2. **Bulk Session Orphaning:** The Session Manager queries all session mappings associated with the dead Edge Node and marks them as `ORPHANED`. This is a fast batch operation on a Redis set/index keyed by `edge_node_id`.
3. **Arbiter Notification:** For each unique Arbiter hosting entities from orphaned sessions, the Session Manager publishes an `EdgeNodeDead { edge_node_id, affected_entities: Vec<EntityID> }` notification to the Arbiter's command topic on the Event Bus.
4. **Arbiter Response:** Upon receiving the notification, the Arbiter:
   - Stops sending `StateUpdate` packets to the dead Edge Node's UDP address for the affected entities (eliminates wasted bandwidth).
   - Starts the `logout_fuse_ticks` timer for each affected entity (same as a wilderness disconnect — the entity persists under AI control for 60 seconds).
   - Does **not** immediately despawn the entities. Players have the full fuse window to reconnect.

### 9.11.3 Client Reconnection Policy

From the client's perspective, an Edge Node crash is indistinguishable from a network interruption — the WebSocket connection drops. The client is responsible for initiating reconnection.

**The Reconnection Flow:**

1. **Detection:** The client detects the WebSocket drop (TCP RST, timeout, or clean close).
2. **UI Feedback:** The client immediately displays a "Reconnecting..." overlay. Player input is buffered locally but not sent.
3. **Jittered Backoff:** The client waits a randomized delay before attempting reconnection:
   - First attempt: 0.5–1.5 seconds (uniform random jitter)
   - Subsequent attempts: exponential backoff with jitter, capped at 10 seconds
   - The jitter prevents 100 clients from hitting the Edge Node pool simultaneously.
4. **Load Balancer Routing:** The client connects to the Edge Node pool address (not the specific dead instance). The load balancer routes the connection to any healthy Edge Node.
5. **Standard Reconnection:** The new Edge Node runs the standard Section 9.4 flow — queries Session Manager, discovers the `ORPHANED` session and the entity's Arbiter, claims the entity.
6. **Fast-Path Claim:** Because the session is already marked `ORPHANED`, the new Edge Node skips the "is the old Edge Node still alive?" verification. It presents the player's auth token directly to the Arbiter. The Arbiter validates the token, atomically swaps the downstream address, and pushes a full `StateUpdate` bootstrap snapshot.
7. **Session Update:** The Session Manager updates the mapping: `character_id → (entity_id, arbiter_id, new_edge_node_id)` and clears the `ORPHANED` flag.
8. **Resumption:** The new Edge Node executes the full bootstrap sequence (Section 9.11.5) — loading `SpellData`, initializing the prediction loop from the snapshot, deriving cooldowns, and resetting anti-cheat baselines. The player resumes with a brief visual stutter (typically 2-5 seconds total from crash to resumption).

### 9.11.4 Stale Session Cleanup

Not all players will reconnect after an Edge Node crash (some may have already closed the game, lost power, etc.). Orphaned sessions that are never reclaimed must be cleaned up:

| Timer | Duration | What happens |
|:---|:---|:---|
| **Logout fuse** (`logout_fuse_ticks`) | 60 seconds | The entity in the Arbiter runs under AI control. If the player reconnects within this window, they resume seamlessly. If not, the entity is despawned and `PlayerDied` is emitted (if in combat) or the entity is cleanly removed (if in a safe zone). |
| **Session mapping TTL** | 5 minutes | The `ORPHANED` session mapping in the Session Manager persists for 5 minutes to support delayed reconnections (e.g., client restarting). After TTL, the mapping is pruned. |
| **Next login** | Indefinite | If a player returns after both timers have expired, the Session Manager finds no active mapping. Meta executes a standard Spawn Handshake (Section 9.5), respawning the player at their last save zone. |

### 9.11.5 Edge Node Runtime State and Bootstrap Sequence

Edge Nodes hold significant per-session runtime state. While none of it is authoritative, all of it must be reconstructed before the player can resume gameplay. The following table inventories this state and its recovery path:

| Runtime State | Description | Recovery Source | Bootstrap Cost |
|:---|:---|:---|:---|
| **`SpellData` dictionary** | The full ability/balance data required for semantic translation (converting raw inputs into `ActionProposals`). Without it, the Edge Node cannot validate ranges, resolve targeting, or enforce cooldowns. | CDN download or local cache. If the Edge Node pool shares a warm cache (e.g., a local volume mount), this is near-instant. Cold download from CDN adds 100-500ms depending on asset size. | Medium — can be pre-warmed |
| **Topology routing table** | The current `topology_epoch` and Arbiter boundary map. Required to route proposals to the correct Arbiter. | Pushed by the Arbiter as a `TopologyUpdate` during the claim handshake (step 6 in Section 9.11.3). | Negligible — single packet |
| **Player entity state** | The player's authoritative position, velocity, HP, resource, buffs, and all visible nearby entities. Seeds the prediction loop. | Pushed by the Arbiter as a full `StateUpdate` bootstrap snapshot during the claim handshake. | Negligible — single packet |
| **Ability cooldown timers** | Per-ability remaining cooldown times. Required so the Edge Node doesn't propose abilities the player can't cast. | Derived from the owning entity's `active_effects_detailed` field in the bootstrap `StateUpdate`. Each effect with a matching cooldown `effect_id` provides `remaining_ticks`. The Edge Node reconstructs the cooldown table on first frame. | Negligible — computed locally |
| **Prediction simulation state** | The local simulation loop that provides immediate movement and combat feedback to the client. | Initialized from the bootstrap `StateUpdate`. The first 2-3 frames may feel slightly "snappy" as the prediction loop converges with the authoritative state. | Low — converges within ~50ms |
| **Entity interpolation buffers** | Smoothing buffers for rendering nearby entities. Requires a short history of `StateUpdate` frames to interpolate between. | Rebuilt naturally from the first few `StateUpdate` frames after reconnection. During the buffer fill period (~100-200ms), nearby entities may appear to "pop" slightly. | Low — fills within 3-5 frames |
| **Anti-cheat accumulators** | Input velocity history, action frequency baselines, anomaly detection state. | **Not reconstructable.** Reset to zero. This is intentionally acceptable — a fresh baseline is safer than stale state from a security perspective. A reconnecting player gets a clean slate, which eliminates the risk of false positives from pre-crash input anomalies. | None — fresh start |

### The Bootstrap Sequence

When a new Edge Node claims a session (step 6 in Section 9.11.3), the following sequence executes:

```
1. [Edge Node]  Load SpellData dictionary (from warm cache or CDN)
2. [Edge Node]  Present auth token to Arbiter, claim EntityID
3. [Arbiter]    Validate token, swap downstream address
4. [Arbiter]    Push TopologyUpdate (routing table + neighbors)
5. [Arbiter]    Push full StateUpdate bootstrap snapshot
               (player entity + all visible entities + active_effects_detailed for owner entity)
6. [Edge Node]  Initialize prediction loop from snapshot
7. [Edge Node]  Derive cooldown table from active_effects_detailed
8. [Edge Node]  Reset anti-cheat baselines to zero
9. [Edge Node]  Begin accepting client input and streaming predictions
```

**Total bootstrap time:** Steps 2-5 are bounded by a single Arbiter round-trip (~1-5ms intra-datacenter). Step 1 is the variable cost — with a warm `SpellData` cache, the full bootstrap completes in under 10ms. With a cold CDN fetch, it may take 100-500ms. The total player-visible disruption (including client reconnection jitter) is typically 2-5 seconds.

> **Implementation note:** Edge Nodes should pre-load and cache the active `SpellData` dictionary on boot (as part of the `PrepareDataEpoch` flow). A reconnecting session on an already-running Edge Node will always hit the warm path. The cold path only applies if the replacement Edge Node itself just booted.

### 9.11.6 Capacity and Surge Absorption

When an Edge Node serving N players crashes, those N players will reconnect across the remaining healthy Edge Nodes. The infrastructure must have headroom to absorb this surge:

- **Edge Node Pool Sizing:** The pool should be sized with N+1 redundancy (or a percentage-based buffer) so that losing one Edge Node does not push remaining nodes above capacity.
- **Kubernetes Auto-Scaling:** If Edge Nodes are deployed as a Kubernetes Deployment, the pod replacement is automatic. However, the new pod takes time to boot and register. The reconnection surge will be absorbed by the existing healthy pods, not the replacement.
- **Load Balancer Health Checks:** The load balancer must remove the dead Edge Node from its rotation immediately (via TCP health check failure) so that reconnecting clients are never routed to the dead instance.

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
