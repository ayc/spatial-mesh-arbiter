# Mesh Controller Architecture

This document is the canonical architecture specification for the **Mesh Controller** — the Control Plane service that manages topology, orchestrates splits and merges, synchronizes the global tick, and routes high-radius events.

Canonical split:
- The full `ControllerCommand` enum and `ArbiterHeartbeat` struct are defined in [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md).
- Arbiter-side handling of Controller commands is defined in [Mesh Arbiter State](../2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md).
- Deployment topology and Kubernetes orchestration are canonical in [Deployment & Orchestration](../4-infrastructure/01-deployment-and-orchestration.md).
- Configuration thresholds (`max_entities_per_arbiter`, `min_cell_size_meters`) are canonical in [Configuration Registry](../4-infrastructure/02-configuration-registry.md).

This document is normative. Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used in RFC-style.

---

## 1. Role and Identity

The Mesh Controller is a **non-spatial, highly available service** that acts as the Control Plane for the Spatial Mesh. While Spatial Arbiters are the Data Plane (running 60Hz physics), the Controller:

- maintains the authoritative R-Tree topology,
- orchestrates all split, merge, and boundary-slide operations,
- manages the Warm Pool of idle Arbiters,
- synchronizes the global Shard Tick (the Metronome),
- routes high-radius Global Events to affected Arbiters,
- distributes live game-balance updates (Data Epochs),
- monitors Arbiter health and declares crashes.

The Controller does **not** simulate physics and, with the sole exception of Global Event fan-out routing, does **not** participate in combat resolution.

### 1.1 Deployment Model

The Controller MUST be deployed as a **3-node or 5-node Raft/etcd cluster** co-located in the same regional datacenter as the Arbiters. This provides:
- strong consistency for topology epoch assignment,
- leader election with sub-5-second failover,
- no cross-region latency on the control path.

### 1.2 Transport

| Direction | Protocol | Notes |
| :--- | :--- | :--- |
| Controller → Arbiter | TCP (`tokio::net::TcpStream` with `tokio-util::codec`) | All `ControllerCommand` variants |
| Arbiter → Controller | TCP | `ArbiterHeartbeat`, escalation RPCs, readiness signals |
| Controller → Arbiter (Metronome) | UDP | Low-frequency `SyncHeartbeat` broadcast (~1 Hz) |

### 1.3 Implementation Crate

The Controller lives in the `crates/mesh-controller/` workspace member. It uses a multi-threaded `tokio` runtime (unlike the Arbiter which uses a single-threaded runtime to preserve lock-free invariants).

---

## 2. R-Tree Topology Management

The spatial world is partitioned as a **dynamic R-Tree (Bounding Volume Hierarchy)** rather than a rigid quadtree. This allows the Controller to create tightly-fitting bounding boxes around player hotspots without static geographical constraints.

### 2.1 Core Ownership Invariant

> At any instant, each entity has exactly one authoritative Mesh Arbiter.

Because R-Tree bounding boxes can overlap, Arbiters use a deterministic tie-breaker for jurisdiction:
1. **Depth:** The Arbiter deepest in the R-Tree (most localized) wins.
2. **ID Tie-Breaker:** If depth is equal, the lowest `arbiter_id` wins.

The Controller MUST enforce this invariant when computing new boundaries.

### 2.2 Topology Epochs

Every topology mutation (split, merge, slide) produces a new **Topology Epoch** — a monotonically increasing `u32`. The Controller is the sole authority for epoch assignment.

- Arbiters include their current `topology_epoch` in every `ArbiterHeartbeat`.
- Proposals from Edge Nodes carry a `topology_epoch`; Arbiters use this for stale-detection (see [Core Concepts](01-core-concepts-and-mesh.md) §7.2).
- Edge Nodes learn topology changes indirectly via Arbiter `TopologyUpdate` downstream payloads, **not** from the Controller directly. This prevents the Controller from becoming a global fan-out bottleneck.

### 2.3 Minimum Cell Size Constraint

The Controller MUST enforce a minimum bounding box dimension equal to the game's `max_spell_range` (default: 40m). This guarantees that standard combat interactions never require more than one network hop.

If a cell reaches the minimum size but remains overloaded, the Controller MUST NOT subdivide further. The Arbiter transitions to Kinematic Dilation instead.

---

## 3. Rebalancing Triggers

Rebalancing is triggered by **deterministic entity counts**, not reactive hardware metrics (CPU, memory). The Controller continuously monitors entity distribution via `ArbiterHeartbeat.entity_count` and evaluates against configuration thresholds.

### 3.1 Split Trigger

A split is triggered when **both** conditions are true:
1. An Arbiter's `entity_count` exceeds `max_entities_per_arbiter` (default: 400).
2. The Arbiter's current spatial dimensions are larger than `min_cell_size_meters`.

### 3.2 Merge Trigger

A merge is triggered when adjacent sibling cells in the R-Tree **both** fall significantly below their entity limits. The Controller merges them and returns the redundant Arbiter to the Warm Pool.

### 3.3 Boundary Slide Trigger

When a hotspot moves geographically (e.g., a raid marching across the map), the Controller detects center-of-mass drift and shifts bounding boxes to keep entities centered within their cell. This avoids unnecessary handoffs for the bulk of the population.

---

## 4. Warm Pool Management

Standard Kubernetes HPA is fundamentally incompatible with the engine's millisecond-scale split requirements. The infrastructure maintains a **Warm Pool** of idle Arbiter pods.

### 4.1 Registration Handshake

1. Kubernetes boots surplus "Idle" Arbiter pods.
2. Each pod binds to its host network port, opens a TCP connection to the Controller, and reports: `"I am alive, my routable UDP address is 10.x.x.x:7000."` (In Docker Compose, nodes register by hostname, not internal IP.)
3. The Controller assigns a permanent `arbiter_id` and adds the pod to the Service Registry in a **Ready** (suspended) state.

### 4.2 Instant Allocation

When the Controller needs to execute a `BeginSplit` or provision a merge target, it instantly claims a Ready Arbiter from the pool, injects the split geometry, and provides neighbor IP addresses. No Kubernetes scheduler delay is incurred.

### 4.3 Return to Pool

When a cell is dissolved via `FinalizeMerge` or `FinalizeSplit`, the drained Arbiter clears its memory and transitions back to Ready state in the Warm Pool.

### 4.4 Pod Lifecycle Authority

Only the Mesh Controller is legally allowed to terminate an Allocated Arbiter (via the Merge/Drain protocol). The Kubernetes scheduler MUST be prevented from evicting Allocated Arbiters — enforced via Pod Disruption Budgets and Guaranteed QoS class.

### 4.5 Capacity Provider (Warm Pool Replenishment)

The Warm Pool is finite. Sustained player influx (e.g., a world event drawing thousands of players into a region over minutes) will drain the pool faster than merges return Arbiters to it. The Controller MUST proactively replenish the pool before exhaustion.

#### Watermark Model

The Controller maintains two configurable watermarks against the Warm Pool size:

| Threshold | Default | Trigger |
|:---|:---|:---|
| `warm_pool_low_watermark` | 10 Arbiters | Controller begins requesting new capacity from the Capacity Provider |
| `warm_pool_critical_watermark` | 3 Arbiters | Controller enters **conservation mode** (see §4.6) |
| `warm_pool_target_size` | 25 Arbiters | Desired steady-state pool size; replenishment stops when reached |

The Controller evaluates watermarks on every heartbeat cycle (~1 Hz). When the pool drops below `warm_pool_low_watermark`, it issues a capacity request for `warm_pool_target_size - current_pool_size` Arbiters.

#### CapacityProvider Trait

The Controller interacts with the underlying infrastructure through a `CapacityProvider` trait, decoupling topology logic from cloud/orchestration specifics:

```rust
#[async_trait]
trait CapacityProvider: Send + Sync {
    /// Request `count` new Arbiter instances. Returns immediately — provisioning is async.
    /// The Controller learns about new Arbiters when they complete the Registration Handshake (§4.1).
    async fn request_capacity(&self, count: u32) -> Result<CapacityRequestId>;

    /// Query the current provisioning status of a previous request.
    async fn check_request(&self, id: CapacityRequestId) -> Result<CapacityRequestStatus>;

    /// Signal that the fleet should scale down by `count`. The Controller has already
    /// drained the Arbiters and returned them to Ready state — this releases the underlying
    /// compute resources.
    async fn release_capacity(&self, arbiter_ids: Vec<u32>) -> Result<()>;

    /// Query the provider's current headroom (how many more instances can be provisioned
    /// without hitting account/quota limits).
    async fn available_headroom(&self) -> Result<u32>;
}

enum CapacityRequestStatus {
    Pending { requested: u32, provisioned_so_far: u32 },
    Complete { total_provisioned: u32 },
    PartialFailure { provisioned: u32, failed: u32, reason: String },
}
```

#### Implementation: Agones Fleet Autoscaler

The production implementation uses Agones, which provides native Warm Pool semantics via the `Fleet` CRD:

1. **`request_capacity`** — Patches the Agones `Fleet` spec to increase `replicas` by the requested count. Agones + the Kubernetes Cluster Autoscaler handle node provisioning if the cluster lacks available compute.
2. **`release_capacity`** — Calls the Agones SDK `Shutdown()` on drained pods. Agones marks them for deletion and the Cluster Autoscaler reclaims empty nodes.
3. **`available_headroom`** — Queries the Kubernetes API for schedulable capacity on existing nodes (CPU cores with Guaranteed QoS headroom). This does not account for Cluster Autoscaler scale-up, which is opaque to the Controller.

**Lead time budget:** Cloud VM provisioning (Cluster Autoscaler adding a new node) takes 30–90 seconds. Agones pod scheduling on an existing node takes 2–5 seconds. The watermark model is designed to absorb this gap:

| Scenario | Pool Behavior |
|:---|:---|
| Steady state | Pool hovers at `target_size`. Splits consume Arbiters, merges return them. |
| Gradual influx | Pool dips below `low_watermark`. Controller requests capacity. New pods register within 2–5s if nodes are available, 30–90s if Cluster Autoscaler must add a node. |
| Sudden spike (world event) | Pool drains rapidly. If it hits `critical_watermark`, conservation mode activates (§4.6) to buy time while capacity provisions. |
| Sustained overload | Pool exhausted despite replenishment. Controller refuses splits and Arbiters dilation-only. An operational alert fires. |

The Controller MUST emit the following metrics for capacity monitoring:
- `warm_pool_size` (gauge) — current Ready Arbiter count
- `capacity_requests_pending` (gauge) — outstanding unfulfilled requests
- `capacity_request_latency_ms` (histogram) — time from request to first pod registration
- `warm_pool_exhausted_events` (counter) — number of times pool hit 0

### 4.6 Conservation Mode (Pool Exhaustion)

When the Warm Pool drops to or below `warm_pool_critical_watermark`, the Controller enters **conservation mode** to extend the remaining pool lifetime while new capacity provisions:

1. **Split suppression:** The split threshold is temporarily raised by a configurable multiplier (default: `1.5×`). An Arbiter that would normally split at 400 entities now tolerates 600 before the Controller allocates a pool Arbiter. This forces heavier reliance on Kinematic Dilation but preserves pool inventory.
2. **Merge eagerness:** The merge threshold is temporarily lowered, aggressively reclaiming Arbiters from underpopulated cells and returning them to the pool.
3. **Slide preference:** The Controller preferentially uses boundary sliding (§7) instead of splits where possible, since slides consume zero pool Arbiters.
4. **Operational alert:** The Controller emits a `WarmPoolCritical` alert (via metrics and optionally a webhook) so operators can intervene (e.g., manually scaling the node pool, diverting traffic from the shard).

Conservation mode exits automatically when the pool recovers above `warm_pool_low_watermark`.

If the pool reaches **0 Available Arbiters**:
- All split requests are **refused**. Overloaded Arbiters rely entirely on Kinematic Dilation.
- The Controller continues issuing capacity requests on every heartbeat cycle until capacity arrives.
- An `EmergencyPoolExhausted` alert fires. This is the highest-severity infrastructure alert in the system.

---

## 5. Split Orchestration Protocol

When a cell (Arbiter A) needs to split into children (B and C):

| Step | Actor | Action |
| :--- | :--- | :--- |
| 1. Shadow Boot | Controller | Provisions B and C from the Warm Pool in Shadow Mode. Issues `BeginSplit { split_id, region_b, region_c, new_epoch }` to A. |
| 2. Surrogate Operation | Arbiter A | Continues normal 60Hz simulation. B and C exist but do not yet own any entities. |
| 3. State Streaming | Arbiter A | Filters authoritative state by new boundaries. Streams `SplitSnapshot` chunks plus a continuous WAL of every tick's mutations to B and C. |
| 4. Catch-up | B and C | Fast-forward through the WAL until their state matches A's current tick. Send `CatchupAck` to A, which A forwards to the Controller. |
| 5. Controller Commit | Controller | Once B and C are ready, issues `CommitSplit { split_id, cutover_tick, new_epoch }`. Reliable TCP, retryable/idempotent. |
| 6. Atomic Routing Flip | Arbiter A | At `cutover_tick`, broadcasts `TopologyUpdate` to its Edge Nodes with redirect to B or C based on entity position. B and C begin authoritative simulation. |
| 7. Drain & Finalize | Arbiter A → Controller | For `MAX_EVENT_AGE_TICKS` (1 second), A forwards late packets to B/C. After drain, Controller sends `FinalizeSplit` and A returns to the Warm Pool. |

### Split Invariants

- The `cutover_tick` is deterministic — all participants agree on the exact tick.
- During surrogate operation, A remains the sole authority. No split-brain is possible.
- `SplitSnapshot` uses `Vec<(EntityID, EntityRecord)>` to bundle `SoftState` + `OffensiveStats` for transfer (see [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)).
- Pending `ControllerCommand::ExecuteGlobalEvent` entries are transferred via the snapshot to prevent scheduled events from being lost.

---

## 6. Merge Orchestration Protocol

When adjacent cells B and C should merge:

| Step | Actor | Action |
| :--- | :--- | :--- |
| 1. Winner Election | Controller | Chooses `winner_arbiter_id` (default: lowest `arbiter_id`), designates the other as loser. Issues `BeginMerge { merge_id, winner_arbiter_id, loser_arbiter_id, merged_region, cutover_tick, new_epoch }`. |
| 2. Dual-Live Prephase | B and C | Both continue simulating their own regions until `cutover_tick`. |
| 3. Snapshot + WAL Stream | Loser | Streams `MergeSnapshot` plus continuous WAL deltas to the winner. |
| 4. Catch-up Barrier | Winner | Replays WAL deterministically. Sends `CatchupAck` to loser, which forwards readiness to the Controller. |
| 5. Controller Commit | Controller | Issues `CommitMerge { merge_id, cutover_tick, new_epoch }`. Reliable TCP, retryable/idempotent. |
| 6. Authority Flip | Winner | At `cutover_tick`, takes over the merged region. Edge Nodes of the loser are redirected. |
| 7. Drain & Finalize | Loser → Controller | Forwards late traffic to winner for `MAX_EVENT_AGE_TICKS`. Controller sends `FinalizeMerge`. Loser returns to pool. |

### Merge Invariants

- `CommitMerge` is control-plane authoritative and MUST be retried until acknowledged by both winner and loser.
- Merge commit is not complete from a networking perspective until loser-connected Edge Nodes receive a deterministic reroute signal.
- The Event Idempotency Ledgers of both Arbiters are unioned during merge to prevent duplicate impact processing in the transition window.

---

## 7. Boundary Sliding (Spotlight Optimization)

For hotspots that move geographically (e.g., a 400-player raid marching east):

1. **Center-of-Mass Tracking:** The Controller monitors the geographic centroid of entities within each cell via `ArbiterHeartbeat` data.
2. **Shift Command:** The Controller issues `UpdateTopology { my_region: <shifted_rect>, cutover_tick, new_epoch }` to the cell and its affected neighbors.
3. **Zero Handoffs:** Because the entity mass remains inside the sliding bounding box, entities experience no routing flips, no RUDP traffic, and no handoff latency.

Only entities at the trailing edge (leaving the old boundary) or leading edge (entering from a neighbor) require individual handoffs. The bulk of the population is unaffected.

---

## 8. Global Tick Synchronization (The Metronome)

### 8.1 Genesis Tick

The Controller establishes `Tick = 0` when the shard boots. All Arbiters use this as their absolute timeline.

### 8.2 Self-Pacing

Arbiters run a strict `while(true)` loop sleeping for 16.6ms per frame. They do not poll the Controller on every tick.

### 8.3 Heartbeat Correction

To prevent micro-drift across physical machines, the Controller broadcasts a low-frequency UDP `SyncHeartbeat { controller_shard_tick }` (~1 Hz).

Arbiters do **not** snap their clocks. They compute the signed drift:
```
diff = controller_shard_tick - self.current_tick
```
and apply the following correction contract:

1. `desired_offset_us = clamp(diff * 50, -1000, 1000)`
2. `target_frame_pacing_offset_micros = desired_offset_us`
3. Once per frame, Arbiter slews toward target:
   `frame_pacing_offset_micros += clamp(target - current, -50, 50)`
4. Frame sleep budget is computed as:
   `sleep_us = max(0, 16_666 - sim_elapsed_us + frame_pacing_offset_micros)`

This preserves a strict monotonic local tick while converging gradually.

### 8.4 Outlier and Heartbeat-Loss Behavior

Arbiters MUST apply the following guards:

1. **Outlier guard:** if `abs(diff) > 300` ticks, ignore the heartbeat sample and increment an outlier metric/counter.
2. **Short heartbeat loss (>3s):** freeze target updates and decay `frame_pacing_offset_micros` toward `0` at `10us/frame`.
3. **Extended heartbeat loss (>10s):** emit a degraded-control-plane warning metric/event once, continue decaying offset.
4. **Recovery:** on first valid heartbeat after outage, resume normal correction contract in §8.3.

### 8.5 Conformance Targets

Metronome behavior SHOULD satisfy:

1. **Steady-state drift:** `abs(diff)` <= `1` tick for at least 99% of samples in a 5-minute window.
2. **Step recovery:** from an induced `+10` tick drift, recover to `abs(diff)` <= `1` tick within `5s`.
3. **No time travel:** Arbiter local `current_tick` MUST remain strictly monotonic (no backward jumps, no snap-to-controller).
4. **Bounded correction:** per-frame slew <= `50us`; absolute pacing offset <= `1000us`.

---

## 9. Heartbeat Monitoring and Crash Detection

### 9.1 ArbiterHeartbeat

Arbiters send periodic heartbeats to the Controller over TCP:

```rust
struct ArbiterHeartbeat {
    arbiter_id: u32,
    topology_epoch: u32,
    entity_count: u32,          // Driving metric for rebalancing
    current_dilation: SimFixed,
    cpu_usage_pct: u8,          // Telemetry only; not used for rebalancing
}
```

`entity_count` is the authoritative signal for split/merge decisions. Hardware metrics like `cpu_usage_pct` are collected for observability but MUST NOT drive rebalancing logic.

### 9.2 Crash Declaration

When heartbeats from an Arbiter cease:

1. **Declaration:** After 3 consecutive missed heartbeats (~3 seconds), the Controller declares the Arbiter dead and removes it from the active topology.
2. **Topology Repair:** The Controller issues `UpdateTopology` to neighboring Arbiters, expanding their boundaries to cover the dead cell's region.
3. **Ghost Cleanup:** Neighbors receive the update and garbage-collect all Ghost entities that belonged to the dead Arbiter.
4. **Handoff Cleanup:** The Controller issues `AbortPendingHandoffs { crashed_arbiter_id }` to neighboring Arbiters so they purge uncommitted `ProjectileHandoff` shadows from the crashed source.
5. **Event Bus Notification:** The Controller publishes `ArbiterCrashedEvent { arbiter_id, topology_epoch, declared_dead_at }` to Meta Services via Redpanda. Meta's reconciliation service uses this to refund in-flight transactions.

---

## 10. Global Event Routing

When an ability's geometry exceeds `max_spell_range`, the originating Arbiter cannot resolve it locally. The event is escalated to the Controller.

### 10.1 Pipeline

1. **Escalation:** The Arbiter detects `ability.geometry.get_max_extent() > MAX_SPELL_RANGE` and sends the spell with its finalized `CombatContext` to the Controller via RPC.
2. **Fan-Out Calculation:** The Controller queries the R-Tree to determine which Arbiters intersect the event's geometry.
3. **Scheduling:** The Controller issues `ExecuteGlobalEvent { execute_at_tick, ... }` to each affected Arbiter. The `execute_at_tick` is a synchronized future Shard Tick.
4. **Execution:** Each Arbiter holds the command in `pending_global_events` and independently executes at the scheduled tick.

### 10.2 Invariants

- **Epoch Pinning:** Before detonation, each Arbiter validates `data_epoch` matches its active `SpellData` dictionary.
- **Dilation Override:** Global Events override Kinematic Dilation. Even if an Arbiter is skipping frames, it MUST wake up and execute a full simulation frame on the scheduled tick.
- **Controller Offline:** If the Controller is unreachable, the Arbiter aborts the escalation and sends `ActionFailed` to the Edge Node so cooldowns/resources are refunded immediately. No partial detonation is allowed.

### 10.3 Traffic Profile

Global Events represent <0.1% of combat traffic. The Controller acts as a high-level router for these infrequent events to prevent P2P network saturation between Arbiters.

---

## 11. Live Data Distribution (Hot-Patching)

The Controller distributes game-balance updates at runtime without restarts.

### 11.1 Pipeline

1. **Command:** The Controller issues `PrepareDataEpoch { new_epoch, asset_uri, checksum }` over TCP.
2. **Asynchronous Loading:** Each Arbiter spins up a background task to download the asset from the CDN URI (e.g., `s3://game-assets/balance/v1.02.fb`).
3. **Validation:** The Arbiter verifies the checksum.
4. **Atomic Activation:** The parsed dictionary is pushed into a lock-free queue. The 60Hz loop picks it up at the next frame boundary and atomically swaps to the new `SpellData`.

Live configuration variables (interest radii, dilation curves, gameplay timers) are packaged inside the `SpellData` dictionary. See [Configuration Registry](../4-infrastructure/02-configuration-registry.md) for the full variable list.

---

## 12. Spawn Topology Lookup

When a new player connects:

1. Meta Services resolve the player's last known world position.
2. Meta queries the Controller: *"Which Arbiter currently owns coordinate [x, y]?"*
3. The Controller performs an R-Tree point query and returns the target Arbiter's address.
4. Meta injects the player's `EntityRecord` into the Arbiter and provides the Edge Node with routing information.

This is the only Meta → Controller query in the standard gameplay flow.

---

## 13. Failure Modes

### 13.1 Topology Freeze (Controller Unavailable)

When the Controller is down:
- The R-Tree **freezes**: no splits, merges, slides, or handoffs can occur.
- The 60Hz simulation **continues uninterrupted** within the frozen topology.
- Global Event escalations are **rejected**: Arbiters abort and refund.
- Overloaded cells fall back entirely to **Kinematic Dilation**.

### 13.2 Expected Survival Window

The system is designed to absorb standard Raft leader-election outages (2–5 seconds) with zero player-visible impact. The degradation cliff occurs around ~30 seconds of sustained outage under active load, as frozen topology prevents the system from adapting to density changes. The Control Plane SLA mandates a Recovery Time Objective (RTO) of **< 10 seconds**.

### 13.3 Stale Epoch Buffering

If an Arbiter receives a proposal with a topology epoch newer than its own (split in progress), it buffers the proposal for a short window until the Controller's `UpdateTopology` arrives. A strict timeout prevents infinite stalling if the Controller's update is permanently lost. See [Mesh Arbiter State](../2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md) for the buffering implementation.

---

## 14. Controller State Summary

The Controller maintains the following authoritative state:

| State | Type | Purpose |
| :--- | :--- | :--- |
| R-Tree | `RTree<ArbiterNode>` | Spatial topology — which Arbiter owns which region |
| Topology Epoch | `u32` | Monotonic version counter for topology mutations |
| Arbiter Registry | `HashMap<u32, ArbiterRecord>` | arbiter_id → address, status (Ready/Allocated/Draining), last heartbeat |
| Warm Pool | `Vec<u32>` | arbiter_ids in Ready state available for instant allocation |
| Capacity Provider | `Arc<dyn CapacityProvider>` | Interface to infrastructure for pool replenishment/release |
| Pending Capacity Requests | `HashMap<CapacityRequestId, u32>` | Outstanding requests to the Capacity Provider (id → count requested) |
| Conservation Mode | `bool` | True when pool is at or below `warm_pool_critical_watermark` |
| Active Splits | `HashMap<UUID, SplitState>` | In-flight split operations awaiting CatchupAck/Commit |
| Active Merges | `HashMap<UUID, MergeState>` | In-flight merge operations awaiting CatchupAck/Commit |
| Current Data Epoch | `u32` | The latest SpellData version distributed to Arbiters |
| Shard Tick | `u64` | The authoritative global tick (source for SyncHeartbeat) |

---

## 15. Debug Visualization

For local development, a 2D Debug Canvas SHOULD connect to the Controller to render:
1. Dynamic AABBs of active Arbiters (colored rectangles).
2. Entity positions (dots).
3. Ghost entities (hollow circles).

Watching rectangles split, merge, and slide over dots in real-time confirms the R-Tree is load-balancing correctly. See [Mini-Mesh Conformance](../5-testing-and-conformance/01-mini-mesh-conformance.md) §4.

---

## 16. Cross-References

- Controller command type definitions: [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md)
- Arbiter-side command handling: [Mesh Arbiter State](../2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md)
- Global Event pipeline and examples: [Global Events](../3-gameplay-systems/03-global-events.md)
- Deployment and Warm Pool infrastructure: [Deployment & Orchestration](../4-infrastructure/01-deployment-and-orchestration.md)
- Configuration thresholds: [Configuration Registry](../4-infrastructure/02-configuration-registry.md)
- Conformance and failure test scenarios: [Mini-Mesh Conformance](../5-testing-and-conformance/01-mini-mesh-conformance.md)
- Core architecture theory (splits, merges, sliding, epochs): [Core Concepts and Mesh](01-core-concepts-and-mesh.md)
