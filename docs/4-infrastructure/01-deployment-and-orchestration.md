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