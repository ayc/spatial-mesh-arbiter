# High-Blast-Radius Assessment: Game Compiler Primitives vs. Core Engine

**Objective:** Identify the highest-blast-radius architectural gaps between the canonical ability primitive taxonomy in `docs-game-compiler/ability-primitives/` and the current technical specifications in `docs-core/`.
**Goal:** Highlight the core-engine subsystems most likely to require new contracts or major expansion before the game compiler's "Virtual Instruction Set" can be supported end-to-end.

**Scope note:** This is a selective architecture assessment, not an exhaustive primitive-by-primitive audit. It focuses on the engine-facing subsystems with the largest design impact. For a fuller contract-planning view, pair this document with `docs-core/PRIMITIVE_IMPACT_ASSESSMENT.md`.

---

## Executive Summary

The core spatial engine (`docs-core/`) is currently designed as a highly optimized, distributed systems kernel. It handles fixed-point spatial partitioning (R-Trees), rigid 60Hz tick loops, and baseline network routing (idempotency, RUDP epochs, ghost synchronization).

However, a subset of the Game Compiler primitives assume the engine natively supports complex, systemic relational logic (hierarchies, dynamic topologies, distributed bindings, and observer-aware filtering). Bridging this gap requires expanding the `Spatial Runtime Kernel` and `Spatial Messaging Plane` to support stateful relationships without violating strict deterministic contracts.

---

## Selected Core Engine Deltas & Required Subsystems

### 1. Temporal State Registry (Impacts P-05)
*   **Current State:** `docs-core` provides replay buffers for *event idempotency* (`max_event_age_ticks`), but lacks a system for querying historical entity state for gameplay mechanics like time rewind.
*   **New Requirement:** 
    *   **Tick Loop:** Implement a post-resolution hook to store bounded `(position, hp, tick)` tuples for opted-in entities.
    *   **Cross-Boundary:** This buffer must be serialized as `SoftState` and transferred atomically during spatial handoffs between Arbiters.
    *   **API:** The Game Adapter needs a fast-path query (`get_historical_state(entity_id, tick_offset)`) exposed in the resolution context.

### 2. Kinematic Transform Graph (Impacts P-06, P-58)
*   **Current State:** Movement integration assumes independent entities on a flat global coordinate plane. There is no concept of hierarchical transforms or input suppression.
*   **New Requirement:**
    *   **Tick Loop:** The movement integration phase must evaluate a directed acyclic graph (DAG) of transforms, ensuring parent positions are integrated before children.
    *   **Cross-Boundary (Critical):** If a parent entity (e.g., a vehicle or an aura-host) crosses an Arbiter boundary, the engine must perform an **atomic, grouped handoff** of the parent *and all attached children*. Standard single-entity handoff will break the hierarchy and cause desyncs.

### 3. Dynamic Spatial Index (Impacts P-08, P-57)
*   **Current State:** Assumes static spatial topology for collision and pathing.
*   **New Requirement:**
    *   **Tick Loop:** The collision R-Tree must support lock-free insertion, querying, and FIFO decay of temporary geometry (terrain walls, swept polylines) within the strict authoritative tick budget.
    *   **Cross-Boundary:** Dynamically injected geometry overlapping an Arbiter boundary must be replicated to neighboring Arbiters via the Messaging Plane to ensure consistent pathfinding across the network.

### 4. Stateful Spatial Triggers (Impacts P-14)
*   **Current State:** Supports stateless spatial overlap queries per tick, but lacks edge-triggered events (`OnEnter`/`OnLeave`).
*   **New Requirement:**
    *   **Tick Loop:** A monitor must maintain a `Set<EntityID>` of overlapping entities per zone from the previous tick, diff it against the current tick's query, and emit discrete internal events.
    *   **Cross-Boundary:** Ghost entities (cross-boundary proxies) must be fully integrated into this system so that proximity triggers fire seamlessly across Arbiter boundaries.

### 5. Dynamic Input Router (Impacts P-29, P-30)
*   **Current State:** The envelope contract enforces a strict 1:1 static mapping between `source_identity` (Edge Node session) and the authoritative entity host.
*   **New Requirement:**
    *   **Messaging Plane:** External intent routing must be decoupled. The ingress layer needs a **Control Authority Map** capable of fan-out (1 player &rarr; N entities) or hijacking (Player A &rarr; Player B's entity).
    *   **Safety:** Requires strict deterministic rules for resolving conflicting multi-player inputs (P-30) and split-brain scenarios during disconnects.

### 6. Distributed Binding Registry (Impacts P-34, P-60)
*   **Current State:** Entities are distinct, isolated actors. Internal events support one-off cross-boundary relays, but there is no mechanism for persistent relational lifecycles.
*   **New Requirement:**
    *   **Tick Loop:** A graph subsystem to track two-way dependencies (soulbinds, tethers) and ensure synchronized cleanup when either entity dies.
    *   **Cross-Boundary (Critical):** When Entity A hands off to a new Arbiter while bound Entity B remains behind, the registry must establish a persistent cross-Arbiter relay. For Event Cloning (P-60), a new synchronized "Binding Relay Event" is needed to guarantee damage/healing mirroring across nodes without triggering infinite loops.

### 7. Hierarchical Spatial Instances (Impacts P-56)
*   **Current State:** Spatial partitioning is strictly used for load-balancing a single, contiguous global coordinate space (split/merge).
*   **New Requirement (Massive Impact):**
    *   **Kernel:** The Spatial Runtime Kernel must be refactored to support "Pocket Arenas" — spawning multiple isolated spatial indexes (R-Trees) within a single Arbiter tick loop.
    *   **Messaging Plane:** Routing must understand `(Instance_ID, Entity_ID)` rather than relying purely on global 2D/3D coordinate proximity. Migrating entities into/out of an instance bypasses standard visibility logic.

### 8. Observer-Aware Payload Filtering (Impacts P-52)
*   **Current State:** The kernel handles distance-based visibility proxies but lacks context-aware payload filtering based on game logic.
*   **New Requirement:**
    *   **Serialization Pipeline:** The engine's state replication pipeline must evaluate `visible_to_team[team_id] = bool` before generating downstream Edge Node payloads.
    *   **Adapter Contract:** Because `team_id` is a Game Adapter domain concept, the Game Adapter contract (`04-1-game-adapter-contract.md`) must be updated to expose an observer's properties to the engine's serialization filter safely, without breaking the framework boundary.

---

## Conclusion

The 65 compiler primitives successfully prove that the game design can be reduced to a finite instruction set. This selective assessment shows that the highest-blast-radius parts of that instruction set push significant complexity down into the engine's distributed architecture.

The `docs-core` framework should prioritize the design of the **Distributed Binding Registry**, the **Kinematic Transform Graph**, and **Hierarchical Spatial Instances** before the Game Compiler can safely emit the most demanding capability chains.

This document should not be read as claiming that every primitive requires a new engine subsystem. Many primitives remain adapter-level or can be addressed through narrower contract additions rather than kernel expansion.
