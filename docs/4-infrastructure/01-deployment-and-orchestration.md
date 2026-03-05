# Deployment & Orchestration Strategy

This document defines the infrastructure, containerization, and orchestration requirements for the Spatial Mesh engine. It serves as a guide for DevOps and Infrastructure Engineers to deploy the 60Hz deterministic engine safely onto cloud or bare-metal Kubernetes clusters.

---

## 1. Containerization Strategy

The engine is designed around a strictly decoupled container model. 
Every node type in the architecture is packaged as a standalone Linux container.

*   **Spatial Arbiter (The Physics Node):** A single-threaded, lock-free Rust process. Maps 1:1 with a Kubernetes Pod. It maintains ephemeral state in memory.
*   **Proxy Actor (Edge Node):** A lightweight routing and prediction container deployed in Edge Datacenters (e.g., AWS Local Zones, Cloudflare Edge) to minimize client-to-server ping.
*   **Mesh Controller (The Control Plane):** A highly available 3-node or 5-node cluster (using Raft/etcd) managing the R-Tree topology.

---

## 2. The "Warm Pool" (Fleet) Strategy

Standard Kubernetes Horizontal Pod Autoscaling (HPA) is fundamentally incompatible with the engine's `Hitless Handoff` scaling requirements. When a localized "Blackhole" event occurs (e.g., 2,000 players rushing a boss), the Mesh Controller must split the spatial cell in **milliseconds**. Waiting 15–30 seconds for a standard Kubernetes scheduler to pull an image and boot a new Pod is unacceptable.

### The Implementation
Instead of reactive scaling, the infrastructure maintains a **Warm Pool** of idle Arbiter pods.

1.  **Pre-Provisioning:** Kubernetes boots a surplus of "Idle" Arbiter Pods. 
2.  **The Registration Handshake:** Upon boot, a new Arbiter Pod binds to its host network port and opens a TCP connection to the Mesh Controller. It reports: *"I am alive, and my routable UDP address is `10.x.x.x:7000`."* The Mesh Controller assigns the pod a permanent `arbiter_id` and adds it to the Service Registry in a suspended `Ready` state.
3.  **Instant Allocation:** When the Mesh Controller needs to execute a `BeginSplit` (or `BeginMerge`), it instantly claims an Idle Arbiter from the Warm Pool, injecting the split geometry, and explicitly providing the necessary neighbor IP addresses so the Arbiters don't have to perform DNS lookups.
4.  **Return to Pool:** When a Spatial Cell is dissolved via a `CommitMerge`, the Loser Arbiter drains its packets. Upon receiving `FinalizeMerge`, the Loser Arbiter clears its memory and returns itself to the Warm Pool, or exits gracefully if the overall cluster is scaling down.

### Capacity Replenishment

The Warm Pool is finite. The Mesh Controller monitors pool size against configurable watermarks and proactively requests new Arbiter instances from the infrastructure via a `CapacityProvider` trait. In the Agones deployment, this maps to patching the `Fleet` replica count, which triggers the Kubernetes Cluster Autoscaler to add nodes if needed.

The full watermark model, `CapacityProvider` interface, conservation mode behavior, and exhaustion fallback are specified in [Mesh Controller §4.5–4.6](../1-architecture/03-mesh-controller.md).

**Infrastructure requirement:** The Kubernetes Cluster Autoscaler (or equivalent) MUST be configured for the Arbiter node pool with:
- **Scale-up response time** target of < 60 seconds (cloud-provider dependent).
- **Scale-down cooldown** of at least 10 minutes to prevent flapping during intermittent load spikes.
- **Node taints** (`game-server=arbiter:NoSchedule`) to prevent non-Arbiter workloads from consuming Arbiter-reserved compute.

---

## 3. Kubernetes Anti-Patterns & Critical Mitigations

A 60Hz deterministic game engine operates fundamentally differently from a stateless HTTP microservice. The infrastructure *must* bypass standard Kubernetes abstractions that introduce latency or jitter.

### 3.1 The Network Overlay Trap (UDP Jitter)
*   **The Problem:** Standard Kubernetes CNIs (like Flannel or Calico) wrap packets in software overlays (VXLAN/IPIP) and route them through `kube-proxy` iptables. This introduces severe jitter and CPU overhead for high-frequency P2P UDP traffic (like `GhostUpdates` and RUDP Handoffs).
*   **The Mandate:** Arbiter Pods **must** bypass the overlay. 
    *   *Option A:* Use `hostNetwork: true` to bind directly to the underlying Node's Network Interface.
    *   *Option B:* Use a dedicated Game Server Orchestrator (like Agones) that automatically provisions direct host-port mappings for UDP traffic.
    *   *Option C:* Use an eBPF-based CNI (like Cilium) configured for direct routing.

### 3.2 The CPU Throttling Trap (CFS Quotas)
*   **The Problem:** By default, Linux enforces Kubernetes CPU limits using the Completely Fair Scheduler (CFS). If an Arbiter completes its 16.6ms frame math in 5ms, the kernel might decide it has used its quota and forcibly sleep the container for 50ms. This destroys the `Global Tick Synchronization` Metronome.
*   **The Mandate:** Arbiter Pods must be deployed with **Guaranteed QoS**.
    *   The Pod's CPU `requests` must exactly equal its `limits` (e.g., `requests: cpu: "1", limits: cpu: "1"`).
    *   The Kubernetes Node pool must be configured with the `Static` CPU Manager policy (`--cpu-manager-policy=static`). This pins the Arbiter's single thread to a dedicated physical CPU core, preventing the kernel from context-switching noisy neighbors onto that core.

### 3.3 The Pod Lifecycle Trap (Random Evictions)
*   **The Problem:** Kubernetes natively views pods as disposable and will happily kill an active Arbiter to balance cluster load, instantly disconnecting 400 players.
*   **The Mandate:** The Kubernetes scheduler must be stripped of its authority to randomly evict `Allocated` Arbiters. 
    *   Only the **Mesh Controller** is legally allowed to mark an Arbiter for termination (via the Merge/Drain protocol).
    *   Infrastructure must respect Pod Disruption Budgets (PDB) and utilize custom controllers (like Agones) that explicitly block Kubernetes from evicting a game server that is currently hosting an active spatial cell.

---

## 4. Recommended Infrastructure Stack

To satisfy the above constraints without writing custom Kubernetes controllers from scratch, the following stack is recommended:

1.  **Base Orchestration:** Kubernetes (EKS / GKE / Bare Metal).
2.  **Game Server Management:** **Agones** (Open-source K8s extension by Google/Ubisoft).
    *   Provides the `Fleet` CRD to manage the Warm Pool natively.
    *   Handles direct UDP port allocation.
    *   Provides a native SDK allowing the Arbiter to signal `Ready`, `Allocated`, and `Shutdown` to prevent random K8s evictions.
3.  **Networking:** Cilium (eBPF) or AWS VPC CNI for low-latency, overlay-free routing.
4.  **Compute:** Compute-optimized node pools (e.g., AWS C6i or AMD EPYC equivalents) with Static CPU pinning enabled. Memory requirements per pod are low, but CPU cache frequency is paramount.

---

## 5. Binary Deployment Strategy (Blue/Green Stack Replacement)

Game data updates (balance patches, new abilities, new items) are handled live via the **Data Epoch** hot-patching pipeline — no downtime, no restart (see [Mesh Controller §7](../1-architecture/03-mesh-controller.md)).

**Binary updates** (engine code changes, game logic changes, Rust recompilation) require replacing running processes. Because the engine uses monomorphized generics (see [Framework Boundary §9](../1-architecture/07-framework-boundary.md)), a code change to either the engine or the game layer produces a new binary. There is no binary compatibility between versions — old and new arbiters cannot participate in the same topology, perform handoffs, or relay events to each other.

The deployment model is **blue/green stack replacement with forced relog**.

### 5.1 Infrastructure Topology

The deployment is split into **shared long-lived infrastructure** and **per-version game stacks**:

```
┌─────────────────────────────────────────────────────────┐
│                  Shared Infrastructure                   │
│                  (persists across deploys)               │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │ Postgres │   │ Redpanda │   │  Redis   │            │
│  │ (Meta DB)│   │(Event Bus)│   │(Sessions)│            │
│  └──────────┘   └──────────┘   └──────────┘            │
└─────────────────────────────────────────────────────────┘

┌──────────────────────┐    ┌──────────────────────┐
│   Stack v1 (Blue)    │    │   Stack v2 (Green)   │
│                      │    │                      │
│  Mesh Controller     │    │  Mesh Controller     │
│  Arbiter Warm Pool   │    │  Arbiter Warm Pool   │
│  Edge Nodes          │    │  Edge Nodes          │
│  AI Nodes            │    │  AI Nodes            │
│  Meta Service Workers│    │  Meta Service Workers│
└──────────────────────┘    └──────────────────────┘
```

**Shared (long-lived):**
- **Postgres** — Character data, inventory, progression, account state. Schema migrations run before the new stack boots.
- **Redpanda** — Hard state event bus. Both stacks publish and consume from the same topics. Consumer group IDs are version-namespaced (e.g., `loot-service-v2`) so old and new consumers don't compete for the same offsets.
- **Redis** — Session manager. Session keys are ephemeral (6s heartbeat TTL). Old stack's sessions expire naturally after disconnect.

**Per-version (ephemeral):**
- Mesh Controller, Arbiter warm pool, Edge Nodes, AI Nodes, Meta Service worker pods. Each version is a fully independent game stack. They share the backing data stores but never communicate with each other.

### 5.2 Deployment Sequence

```
Time ──────────────────────────────────────────────────────────►

1. Pre-deploy          2. Boot green        3. Flip routing
   Schema migrations      New stack idle       New logins → green
   Asset upload to CDN    Health checks pass   Old logins blocked

4. Graceful drain      5. Old stack empty   6. Teardown
   Staggered disconnect   Last player relogs   Blue pods terminated
   Players relog → green  Hard events flushed  Consumer groups removed
```

**Step 1 — Pre-deploy.** Run any Postgres schema migrations (must be backward-compatible with the old binary until the old stack is fully drained). Upload new Data Epoch assets to CDN.

**Step 2 — Boot green stack.** Deploy the new binary as a parallel set of Kubernetes resources (namespaced or label-differentiated). The new Mesh Controller boots, provisions its own warm pool, and waits. New Meta Service workers start consuming from Redpanda with version-namespaced consumer group IDs.

**Step 3 — Flip login routing.** Update the load balancer (or DNS) so that new client connections are directed to the green stack's Edge Nodes. The old stack stops accepting new WebSocket connections (Edge Nodes enter `DrainingMode`).

**Step 4 — Graceful drain.** The old stack's Edge Nodes send a `ServerShutdown` downstream message to connected clients:

```rust
DownstreamPayload::ServerShutdown {
    reason: ShutdownReason::UpdateAvailable,
    message: "A game update is available. You will be reconnected shortly.",
    grace_period_seconds: u16,  // Time before forced disconnect
}
```

The client displays a notice and reconnects to the new stack. To avoid a thundering herd on the green stack, disconnects are **staggered in waves**:

- **Wave 1 (t+0s):** Players in safe zones (towns, lobbies) — these are cheap to respawn.
- **Wave 2 (t+15s):** Players in the open world not currently in combat.
- **Wave 3 (t+30s):** Players in active combat — given a grace period to finish their current encounter.
- **Wave 4 (t+60s):** Hard disconnect for any remaining sessions.

The wave assignment is determined by the Edge Node, which knows the player's current state from the last `StateUpdate` it received.

**Step 5 — Old stack empty.** Once all players have relogged, the old stack's entity count reaches zero. Old Meta Service workers finish processing any remaining Redpanda events in their consumer groups.

**Step 6 — Teardown.** Old stack's Kubernetes resources are deleted. Old Redpanda consumer groups are cleaned up (or left to expire).

### 5.3 Player Experience

From the player's perspective:

1. A banner appears: *"Game update available. Reconnecting in 15 seconds..."*
2. The client disconnects and immediately reconnects (automated, no manual action).
3. The spawn pipeline reads the player's last save from Postgres and places them in the world.
4. Total interruption: **5–15 seconds** per player. No data loss — all hard state (loot, kills, progression) was durably committed to Redpanda/Postgres before the disconnect.

Players who were mid-combat lose their combat encounter state (active buffs, projectiles in flight, cooldown timers). This is acceptable — `SoftState` is ephemeral by design. The architecture already handles this identically to an arbiter crash (see [Core Architecture §9.7](../1-architecture/01-core-concepts-and-mesh.md)).

### 5.4 Rollback

If the green stack is unhealthy after routing flip:

1. Flip routing back to the old stack (which is still running and accepting connections during the drain period).
2. Send `ServerShutdown` to any players who connected to the green stack.
3. Tear down the green stack.

This is safe as long as the old stack hasn't been fully drained. The rollback window is the duration of step 4 (the staggered drain). Once the old stack is torn down, rollback requires redeploying the old binary as a new stack.

### 5.5 Meta Service Deployment

Meta Services (stateless workers consuming from Redpanda) can be deployed **independently** of the game stack, since they only interact through the shared event bus and Postgres. This means:

- Bug fixes or optimizations to Meta logic (loot formulas, inventory rules) can be rolled out as a standard Kubernetes rolling deployment without any player-visible interruption.
- Meta schema changes that don't affect the game binary can ship at any time.
- Only changes that affect the arbiter/edge/controller binaries (new action types, protocol changes, physics changes) require the full blue/green stack replacement.