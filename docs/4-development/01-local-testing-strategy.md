# Local Development & Testing Strategy (The "Mini-Mesh")

Testing a dynamically scaling, geographically partitioned server mesh on a single local development machine is notoriously difficult. A modern CPU can easily simulate thousands of entities on a single core, meaning a local developer will rarely, if ever, trigger the R-Tree splitting, Hitless Handoffs, or Ghost Propagation logic organically.

To ensure engineers can actively debug and observe the distributed systems logic without needing a massive cloud deployment, the engine utilizes a **"Mini-Mesh" Configuration Profile**.

---

## 1. The "Sandbox" Configuration Profile

The core of local testing is artificially shrinking the engine's capacity limits so that standard developer tests immediately trigger structural mesh events.

Developers should run the engine using a specific `config.dev.yaml` that aggressively overrides the production thresholds:

```yaml
# config.dev.yaml

mesh_controller:
  # Artificially force the R-Tree to split when as few as 10 entities gather
  max_entities_per_arbiter: 10
  
  # Prevent the R-Tree from slicing the map into microscopic 1-meter boxes
  # This forces the engine to test Kinematic Dilation (Blackhole events) locally
  min_cell_size_meters: 20.0 

spatial_arbiter:
  # Force high-frequency Ghost updates to easily monitor UDP traffic
  keyframe_interval_ticks: 10 
```

---

## 2. The Headless Swarm Tester

Running 30 full 3D game clients on a local machine to trigger a 10-player split is inefficient and resource-heavy. 

Engineers should utilize a **Headless Swarm Tester**—a lightweight Rust script that bypasses the graphical rendering engine and communicates directly with the local Edge Node (Proxy Actor) over WebSockets.

The Swarm Tester acts as an army of automated bots. It constructs client WebSocket frames that follow [Client <-> Edge Message Contract](../1-architecture-and-engine/03-client-edge-message-contract.md), primarily `SimulationInput` and discrete simulation intents. The Edge Node then translates those intents into mesh `ActionProposal`s (ability semantics defined in [Ability Framework](../2-gameplay-and-design/02-ability-framework.md)).

### Recommended Test Scenarios

#### Scenario A: The Organic Split (Testing Hitless Handoffs)
1. **Action:** The Swarm Tester spawns 15 bots and commands them to walk toward coordinate `[0,0]`.
2. **Observation:** As the 11th bot enters the bounding box, developers can observe the Mesh Controller instantly provision a secondary Arbiter process on `localhost`.
3. **Debugging:** Engineers can attach a debugger to verify the state serialization, fast-forward catch-up, and Edge Node routing flips occur without dropping the bots' movement packets.

#### Scenario B: Cross-Border Combat (Testing Ghost Relays)
1. **Action:** The Swarm Tester spawns 5 bots at `[-50, 0]` (Arbiter West) and 5 bots at `[50, 0]` (Arbiter East), commanding them to fire `SpawnProjectile` rockets at each other.
2. **Observation:** Developers can monitor the `Unreliable UDP` channel to ensure `GhostUpdates` are flowing across the border.
3. **Debugging:** When a rocket intersects a Ghost, engineers can trace the `MeshInternalEvent` via the `RUDP` channel to guarantee the Idempotency Ledger on the receiving Arbiter correctly applies the damage exactly once.

#### Scenario C: The Blackhole (Testing Kinematic Dilation)
1. **Action:** The Swarm Tester spawns 30 bots and forces them all to stand on the exact same `[0,0]` coordinate.
2. **Observation:** The Mesh Controller attempts to split the node but hits the `min_cell_size_meters: 20.0` limit. Unable to split geographically, the Arbiter is forced to handle 30 entities (3x its capacity).
3. **Debugging:** Developers will see the Arbiter automatically trigger **Kinematic Dilation**. The physical speed of the bots will slow down, and the Arbiter will begin interleaving its collision checks to survive the artificial load.

#### Scenario D: Data Epoch Drift (Testing Proposal Epoch Rejection + Recovery)
1. **Action:** Force one Edge Node to keep an outdated `data_epoch`, then submit non-movement proposals while Arbiters are already on a newer epoch.
2. **Observation:** Stale proposals are rejected with explicit `ActionFailed { reason: "Data Epoch Mismatch" }`.
3. **Debugging:** After Edge Node refreshes from downstream epoch fields, proposals should succeed without server restart.

#### Scenario E: Topology Stale Buffer Timeout (Testing Arbiter-Stale Timeout Contract)
1. **Action:** Artificially delay `UpdateTopology` delivery to one Arbiter while continuing proposal ingress with newer topology epochs.
2. **Observation:** Proposals buffer up to `MAX_EVENT_AGE_TICKS`; timed-out non-movement proposals are rejected with explicit timeout reasons (never silently dropped).
3. **Debugging:** Verify stale-buffer saturation emits deterministic `ActionFailed { reason: "Arbiter Queue Saturated" }`.

#### Scenario F: Controller Outage During Global Event (Testing Refund Path)
1. **Action:** Trigger a map-wide event cast while Mesh Controller RPC is intentionally unavailable.
2. **Observation:** Arbiter aborts escalation and returns `ActionFailed` to Edge Node so cooldown/resources are refunded immediately.
3. **Debugging:** Confirm no partial detonation occurs on any Arbiter and no orphaned scheduled global event remains queued.

#### Scenario G: Projectile Handoff Replay (Testing `handoff_seq` Deduplication)
1. **Action:** Inject duplicate/stale `ProjectileHandoffMessage::Prepare` packets with lower/equal `handoff_seq` during cross-boundary projectile transfer.
2. **Observation:** Receiver rejects stale sequences and sender remains single authoritative simulator until a valid handoff commits.
3. **Debugging:** Confirm impacts are emitted exactly once across retries/replays.

#### Scenario H: Merge Ledger Union (Testing No Double-Damage After Merge Commit)
1. **Action:** Force sibling merge while replaying delayed `ImpactEvent` packets that existed on both winner and loser ledger rings.
2. **Observation:** Winner unions ledger buckets at commit and suppresses duplicate damage post-merge.
3. **Debugging:** Validate `MAX_EVENT_AGE_TICKS` drain window forwarding completes, then loser can be finalized safely.

#### Scenario I: Arbiter Crash Recovery (Testing Total-Loss + Transaction Refund)
1. **Action:** Spawn 10 bots on a single Arbiter. Have one bot consume an item (creating a `PendingTransaction` in Meta). Force-kill the Arbiter process (`docker kill`) while bots are active.
2. **Observation:** The Mesh Controller detects the crash via missed heartbeats, publishes `ArbiterCrashedEvent`, and expands neighbor boundaries to cover the dead cell. Neighboring Arbiters garbage-collect ghost entities sourced from the dead Arbiter.
3. **Debugging:** Reconnect the bots (simulating player re-login). Verify that the Spawn Handshake routes them to their last save zone, the `PendingTransaction` for the consumed item is reconciled as `REFUNDED`, and the item appears in the Recovery Inbox.

#### Scenario J: Crash During Boss Loot Window (Testing Deferred Loot Data Integrity)
1. **Action:** Spawn bots, have them kill a boss. Wait for `MonsterDied` to be published and Meta to roll the loot table and send `SpawnLootInteractable`. Force-kill the Arbiter before any bot claims the loot.
2. **Observation:** Meta's database contains the `MonsterDied` event with `participating_entities`, the rolled loot table results, and no `LootClaimed` record for that drop.
3. **Debugging:** Verify the data trail is complete: kill credit, loot roll results, and absence of claim are all queryable. This validates that deferred loot recovery (when implemented) will have the data it needs.

#### Scenario K: Edge Node Crash (Testing Session Orphaning + Reconnection)
1. **Action:** Connect 10 bots through a single Edge Node. Force-kill the Edge Node process (`docker kill`).
2. **Observation:** The Session Manager detects heartbeat TTL expiry within ~6 seconds, marks all 10 sessions as `ORPHANED`, and publishes `EdgeNodeDead` to the affected Arbiters. Arbiters stop sending `StateUpdate` to the dead address and start logout fuse timers. Entities remain alive under AI control.
3. **Debugging:** Reconnect the bots through the Edge Node pool (load balancer routes to a healthy instance). Verify each bot's reconnection triggers the fast-path claim flow: Session Manager returns `ORPHANED` status, new Edge Node claims the entity on the Arbiter, Arbiter pushes full `StateUpdate` bootstrap, and the bot resumes movement/combat. Verify Session Manager mappings are updated to the new Edge Node.

#### Scenario L: Edge Node Crash + Reconnection Timeout (Testing Orphan Expiry)
1. **Action:** Connect 5 bots through a single Edge Node. Force-kill the Edge Node. Do NOT reconnect the bots.
2. **Observation:** After `logout_fuse_ticks` (60 seconds), the Arbiters despawn the entities. After the session mapping TTL (5 minutes), the Session Manager prunes the orphaned mappings.
3. **Debugging:** Reconnect one bot after both timers have expired. Verify it goes through the full Spawn Handshake (Section 9.5) — no active entity found, Meta respawns at last save zone. Confirm no stale session mappings or ghost entities remain.

#### Scenario M: Tiered NPC Cadence (Testing Runtime Tier Scheduler)
1. **Action:** Spawn mixed NPC archetypes (combat, lane creeps, ambient, social) in a single test region and force visibility transitions across `Near`, `Mid`, and `Far` rings while players move.
2. **Observation:** NPC updates follow tier defaults from [NPC Runtime and Replication Contract](../1-architecture-and-engine/04-npc-runtime-and-replication-contract.md): combat-critical entities remain high cadence, lane creeps downgrade on march state, ambient updates drop first under pressure.
3. **Debugging:** Inspect per-client batch logs to confirm cadence/tier transitions obey hysteresis and never violate reliable lifecycle ordering.

#### Scenario N: Mass On-Screen NPC Saturation (Testing Budget Degradation Priority)
1. **Action:** Place 200+ visible mixed-tier NPCs in one viewport and induce simultaneous movement plus periodic combat events.
2. **Observation:** Per-client NPC replication stays within budget while degradation remains deterministic: lifecycle and interaction events preserved first, ambient/background deltas reduced first.
3. **Debugging:** Verify no dropped `Spawned`, `Died`, `LootClaimed`, or objective progression events while best-effort movement deltas may be thinned.

#### Scenario O: Interaction Contention (Testing Deterministic Single-Winner Semantics)
1. **Action:** Have two bots issue `world.interact_entity` against the same loot/objective target within the same contention window.
2. **Observation:** Exactly one interaction resolves as winner; loser receives deterministic rejection/outcome path (`RejectedContended` class) as defined in [NPC and In-World Interaction Design](../2-gameplay-and-design/05-npc-and-world-interaction-design.md).
3. **Debugging:** Confirm winner/loser ordering remains stable across retries and that no duplicate claim side effects occur.

---

## 3. Visualizing the Mesh

Because the Headless Swarm Tester has no graphical client, it is highly recommended to build a simple **2D Debug Canvas** (using a lightweight framework like `macroquad` or an HTML5 Canvas hooked to a local WebSocket).

This Debug Canvas should connect directly to the Mesh Controller to visualize:
1. The dynamic Axis-Aligned Bounding Boxes (AABBs) of the active Arbiters (drawn as colored rectangles).
2. The `EntityIDs` (drawn as dots).
3. The `Ghost Entities` (drawn as hollow circles to prove propagation is working).

By watching the rectangles dynamically split, merge, and slide over the dots in real-time on the 2D canvas, engineers can visually confirm that the R-Tree is load-balancing the mesh correctly.
