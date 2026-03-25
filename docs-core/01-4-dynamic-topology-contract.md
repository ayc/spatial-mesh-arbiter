# Dynamic Topology Contract

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define engine-level operations that dynamically modify the spatial topology at runtime — visibility filtering, spatial instance forking, incremental geometry construction, entity containment, and portal networks. This contract is Amendment E from `PRIMITIVE_IMPACT_ASSESSMENT.md`.

**Primitives formalized:** P-52 (Asymmetric Team-Rendering), P-56 (Spatial Instance Forking), P-57 (Polyline Collision Generator), P-58 (Container/Vehicle Logic), P-59 (N-Way Portal Network)

**Note:** P-08 (Dynamic Collision Injection) is already specified in `01-1-spatial-primitive-catalog.md` §3.8. P-57 and P-58 build on P-08 and P-06 respectively.

---

## 1. Scope

This contract covers engine operations that reshape the spatial world at runtime in response to game events. These operations go beyond the static R-Tree topology managed by the Mesh Controller (`01-spatial-runtime-kernel.md` §4) — they are game-triggered, bounded-lifetime spatial modifications that the adapter requests and the engine enforces.

---

## 2. Asymmetric Team-Rendering (P-52)

### 2.1 Definition

Per-entity visibility flags that control which teams can observe the entity in downstream payloads. An entity can be visible to allies but invisible to enemies, or vice versa.

### 2.2 Visibility State

```
TeamVisibility {
    visibility_mask:    u64,        // Bitmask: bit N = visible to team N
    default_visible:    bool,       // Visibility for teams not in the mask
    expiry_tick:        u64,        // Auto-revert to full visibility (0 = permanent until changed)
}
```

The engine MUST track `TeamVisibility` as kernel state (not game extension state) because it directly affects downstream payload construction — an engine-owned operation.

### 2.3 Engine Behavior

**Setting visibility:**
1. The adapter emits a visibility mutation in a `StageOutcome` (typically during Stage 12 `ObserverScopedPayloadEmission`, but MAY be set during any stage).
2. The engine updates the entity's `TeamVisibility`.
3. The change takes effect on the NEXT downstream payload build.

**Downstream payload filtering (Stage 12 engine boundary):**
1. For each Edge Node receiving a downstream payload, the engine determines the player's `team_id`.
2. For each entity in the payload, the engine checks `visibility_mask` bit for that `team_id`.
3. If the bit is clear (not visible) and `default_visible` is false, the entity is EXCLUDED from that player's payload.
4. If the bit is set (visible) or `default_visible` is true, the entity is INCLUDED.

**Interaction with other visibility systems:**
- P-53 (Entity Suspension): Suspended entities are excluded from ALL payloads regardless of `TeamVisibility`.
- P-27 (Targetability Overrides): `TeamVisibility` affects rendering/awareness only. An invisible-to-enemies entity MAY still be targetable by AoE if `is_targetable` is true. The adapter decides whether invisible entities should also be untargetable.

### 2.4 Cross-Boundary

Ghost entities carry `TeamVisibility` in their Ghost update payloads. Neighboring Arbiters apply the same per-team filtering when building downstream payloads for their local Edge Nodes that include Ghosts.

### 2.5 Bounds

| Bound | Description | Baseline Key |
|-------|-------------|-------------|
| `max_team_count` | Maximum team IDs supported (determines `visibility_mask` width) | `00-1-core-baseline-profile.md` |

`max_team_count` MUST be <= 64 (constrained by the `u64` bitmask). If more teams are needed, the mask type must be widened.

---

## 3. Spatial Instance Forking (P-56)

### 3.1 Definition

Dynamically create a private spatial partition ("Pocket Arena") that is isolated from the parent R-Tree. Entities migrated into the instance are invisible and unreachable from outside.

### 3.2 Instance State

```
SpatialInstance {
    instance_id:        u64,            // Engine-allocated
    parent_arbiter_id:  ArbiterID,      // The Arbiter that created the instance
    instance_r_tree:    RTree,          // Private spatial index
    migrated_entities:  Vec<EntityID>,  // Entities currently in the instance
    exit_positions:     HashMap<EntityID, Vec2F>,  // Where each entity returns on exit
    expiry_tick:        u64,            // Auto-close tick
    max_entities:       u32,            // Capacity bound
}
```

### 3.3 Engine Behavior

**Creation:**
1. The adapter emits an instance-fork directive in a `StageOutcome`.
2. The engine allocates `instance_id` and creates an empty `instance_r_tree` on the same Arbiter.
3. The instance is NOT a separate Arbiter — it is a secondary R-Tree within the same `SpatialActor`. Authority remains with the original Arbiter.

**Entity Migration (Enter):**
1. The adapter emits a migration mutation listing entity IDs to move into the instance.
2. The engine validates: each entity is on this Arbiter, the instance has capacity, and the entity is not already in another instance.
3. For each entity: remove from the parent R-Tree, insert into `instance_r_tree`, record `exit_position` (current position).
4. The entity's `dispatch_stage` evaluation continues normally — it is evaluated by the same Arbiter. The difference is that spatial queries (P-09, P-11, P-14) for this entity run against `instance_r_tree` instead of the parent R-Tree.

**Isolation:**
1. Entities inside the instance are invisible to entities outside (excluded from parent R-Tree queries).
2. Entities outside are invisible to entities inside (excluded from instance R-Tree queries).
3. Downstream payloads for players inside the instance include only instance entities.
4. Downstream payloads for players outside exclude instance entities.

**Entity Migration (Exit):**
1. The adapter emits an exit mutation, or the instance expires.
2. The engine removes the entity from `instance_r_tree` and re-inserts into the parent R-Tree at the stored `exit_position` (or a designated exit point).
3. The entity becomes visible to outside entities on the next tick.

**Instance Expiry:**
1. When `current_tick >= expiry_tick`, the engine forces all entities to exit.
2. All entities are re-inserted into the parent R-Tree at their stored exit positions.
3. The `instance_r_tree` is destroyed.

### 3.4 Cross-Boundary

Spatial instances do NOT cross Arbiter boundaries. An instance exists entirely within one Arbiter. If the parent Arbiter undergoes a topology split, the instance and all its entities stay with whichever partition contains the instance's origin point.

Entities inside an instance do NOT participate in handoff. If an entity inside an instance needs to hand off (because the parent Arbiter is splitting), the instance MUST be closed first (all entities exit), then normal handoff proceeds.

### 3.5 Bounds

| Bound | Description | Baseline Key |
|-------|-------------|-------------|
| `max_instances_per_arbiter` | Maximum concurrent spatial instances | `00-1-core-baseline-profile.md` |
| `max_entities_per_instance` | Maximum entities in a single instance | `00-1-core-baseline-profile.md` |
| `max_instance_duration_ticks` | Maximum instance lifetime | `00-1-core-baseline-profile.md` |

Instance creation exceeding `max_instances_per_arbiter` MUST be rejected with fault code `INSTANCE_LIMIT_EXCEEDED`.

---

## 4. Polyline Collision Generator (P-57)

### 4.1 Definition

Build collision and/or damage geometry incrementally from a sequence of points, creating a swept corridor that entities can collide with. Extends P-08 (Dynamic Collision Injection) with incremental construction and segment expiry.

### 4.2 Polyline State

```
PolylineGeometry {
    geometry_id:        u32,            // Engine-allocated (same ID space as P-08)
    segments:           RingBuffer<PolylineSegment>,
    width:              SimFixed,       // Half-width of the swept corridor
    max_segments:       u32,            // Capacity bound
    segment_ttl_ticks:  u32,            // Per-segment expiry (FIFO decay)
    blocks_movement:    bool,
    blocks_projectiles: bool,
}

PolylineSegment {
    start:              Vec2F,
    end:                Vec2F,
    created_at_tick:    u64,
}
```

### 4.3 Engine Behavior

**Construction:**
1. The adapter emits a polyline-creation directive, specifying width, max segments, segment TTL, and collision flags.
2. The engine allocates the `geometry_id` and creates an empty polyline.

**Incremental Extension (each tick):**
1. During PostKinematic, the adapter emits an extend-polyline mutation with a new point.
2. The engine creates a new segment from the previous tail point to the new point.
3. If the segment count exceeds `max_segments`, the oldest segment is removed (FIFO).
4. Each segment is a rectangle (the swept corridor between start and end, with half-width on each side).

**Segment Expiry:**
1. Each tick, the engine checks all segments: if `current_tick - segment.created_at_tick >= segment_ttl_ticks`, the segment is removed.
2. This creates a trail effect — the head grows while the tail decays.

**Collision:**
1. Each active segment participates in the static collision grid (same as P-08 injected geometry).
2. Entity movement that intersects any segment is blocked (if `blocks_movement`).
3. Projectiles that intersect are stopped (if `blocks_projectiles`).
4. Spatial queries (P-09) can detect entities within the polyline corridor.

### 4.4 Cross-Boundary

Polyline segments near an Arbiter boundary are replicated to the neighbor (same mechanism as P-08 geometry replication). New segments are replicated as they are added; expired segments are removed on both Arbiters.

### 4.5 Bounds

| Bound | Description | Baseline Key |
|-------|-------------|-------------|
| `max_polyline_geometries_per_arbiter` | Maximum active polylines | `00-1-core-baseline-profile.md` |
| `max_polyline_segments` | Maximum segments per polyline | `00-1-core-baseline-profile.md` |

---

## 5. Container/Vehicle Logic (P-58)

### 5.1 Definition

Lock N entities to a "parent" container entity's transform, suppressing their independent movement while optionally preserving their ability usage. Extends P-06 (Attached Kinematics) with capacity bounds, an explicit enter/exit protocol, and destruction ejection.

### 5.2 Container State

```
ContainerState {
    container_entity_id:    EntityID,
    occupants:              Vec<EntityID>,
    max_capacity:           u32,
    occupant_can_cast:      bool,       // Whether contained entities can use abilities
    occupant_can_be_targeted: bool,     // Whether contained entities appear in spatial queries
}
```

### 5.3 Engine Behavior

**Enter Protocol:**
1. The adapter emits an enter-container mutation (from the entering entity's stage evaluation).
2. The engine validates: the container has capacity, the entity is not already in a container, and the container entity exists.
3. The engine attaches the entity to the container via P-06 (Attached Kinematics) with zero offset.
4. The engine sets the entity's `CAN_MOVE = false` (P-26 Capability Bitmask).
5. If `occupant_can_be_targeted` is false, the engine sets `is_targetable = false` (P-27).
6. The entity's position is now locked to the container's position.

**During Containment:**
1. The entity follows the container's position (via P-06 attachment, evaluated in Stage 5).
2. If `occupant_can_cast` is true, the entity's ability intents are validated normally in Stage 2. Abilities resolve at the container's position.
3. If `occupant_can_cast` is false, all ability intents are rejected with `CONTAINED_ENTITY_CANNOT_CAST`.

**Exit Protocol:**
1. The adapter emits an exit-container mutation.
2. The engine detaches the entity from P-06 attachment.
3. The engine restores `CAN_MOVE = true` and `is_targetable` to its pre-containment value.
4. The entity resumes independent kinematic resolution from the container's current position on the next tick.

**Container Destruction:**
1. When the container entity transitions to `Removed` (death):
2. All occupants are force-ejected at the container's last position.
3. Attachment, capability overrides, and targetability overrides are reverted.
4. Occupants resume independent evaluation on the next tick.

### 5.4 Cross-Boundary

The container entity and all occupants hand off together as a group. When the container crosses an Arbiter boundary:
1. The container entity hands off normally.
2. All occupants hand off with it (their positions are at the container's position, which is in the new partition).
3. P-06 attachments and container state transfer as SoftState.

### 5.5 Bounds

| Bound | Description | Baseline Key |
|-------|-------------|-------------|
| `max_container_capacity` | Maximum entities per container | `00-1-core-baseline-profile.md` |
| `max_containers_per_arbiter` | Maximum active containers | `00-1-core-baseline-profile.md` |

---

## 6. N-Way Portal Network (P-59)

### 6.1 Definition

A registry of spatial anchors that enables any-to-any instant translation across the mesh, including cross-Arbiter teleportation.

### 6.2 Portal State

```
PortalAnchor {
    anchor_id:          u64,            // Engine-allocated
    network_id:         u32,            // Which portal network this belongs to
    position:           Vec2F,          // World position of the anchor
    arbiter_id:         ArbiterID,      // Which Arbiter hosts this anchor
    owner_entity_id:    EntityID,       // Entity that created the anchor (for cleanup)
    expiry_tick:        u64,            // Auto-destroy tick (0 = permanent)
}

PortalNetwork {
    network_id:         u32,
    anchors:            Vec<PortalAnchor>,
}
```

### 6.3 Engine Behavior

**Anchor Creation:**
1. The adapter emits a portal-anchor creation directive.
2. The engine registers the anchor on the local Arbiter.
3. If the portal network spans multiple Arbiters (anchors on different Arbiters), the engine notifies the Mesh Controller, which replicates the network registry to all Arbiters hosting anchors in that network.

**Portal Usage (Teleportation):**
1. The adapter emits a portal-teleport mutation specifying `source_anchor_id` and `destination_anchor_id`.
2. The engine validates: both anchors exist, both are in the same network, and the entity is within interaction range of the source anchor.
3. The engine executes a P-01 (Instant Translation) to the destination anchor's position.
4. If the destination anchor is on a DIFFERENT Arbiter, the engine initiates a handoff to the destination Arbiter (same protocol as cross-boundary P-01 teleportation).

**Network Discovery:**
1. An Arbiter hosting a portal anchor knows about ALL anchors in the same network (via Controller-mediated replication).
2. This enables the adapter to present portal destination choices to the player (e.g., Nydus Network exit selection).

**Anchor Destruction:**
1. The adapter emits an anchor-destroy mutation, OR the anchor reaches `expiry_tick`, OR the owner entity transitions to `Removed`.
2. The engine removes the anchor from the local registry.
3. If the network spans Arbiters, the engine notifies the Controller, which propagates the removal to all network participants.
4. If the network has fewer than 2 anchors remaining, it is effectively non-functional (no valid teleport pairs). The engine MAY garbage-collect empty networks.

### 6.4 Cross-Boundary

Portal networks are inherently cross-boundary — that's their purpose. The Mesh Controller is the coordination point:
1. Anchor creation/destruction events are relayed to the Controller.
2. The Controller maintains the authoritative network registry.
3. The Controller replicates network state to Arbiters hosting anchors in each network.
4. Portal teleportation to a cross-boundary destination uses the standard handoff protocol.

### 6.5 Displacement Interaction

Travel through portals produces displacement for the purpose of P-63 (Movement-Damage Scalar). The displacement is the straight-line distance between source and destination anchor positions. This is by design — Rupture (SK-109) deals massive damage if a cursed entity teleports through a portal.

### 6.6 Bounds

| Bound | Description | Baseline Key |
|-------|-------------|-------------|
| `max_portal_anchors_per_arbiter` | Maximum anchors on one Arbiter | `00-1-core-baseline-profile.md` |
| `max_portal_anchors_per_network` | Maximum anchors in one network | `00-1-core-baseline-profile.md` |
| `max_portal_networks` | Maximum active networks across the mesh | `00-1-core-baseline-profile.md` |

---

## 7. Conformance Requirements

Implementations MUST pass:

1. **Team visibility filtering:** An entity with `visibility_mask` bit clear for team N MUST NOT appear in team N's downstream payloads. Full-visibility entities MUST appear for all teams.
2. **Instance isolation:** Entities inside a spatial instance MUST NOT appear in parent R-Tree queries. Entities outside MUST NOT appear in instance R-Tree queries.
3. **Instance expiry:** On expiry, all entities exit to stored positions deterministically. The instance R-Tree is destroyed.
4. **Instance + handoff:** Instances block handoff for contained entities. If a topology split requires handoff, the instance MUST be closed first.
5. **Polyline construction:** Segment addition and FIFO expiry produce deterministic geometry across replay.
6. **Polyline collision:** Active segments participate in collision checks identically to P-08 injected geometry.
7. **Container grouping:** Container and all occupants hand off together. Occupant positions equal the container's position.
8. **Container destruction:** Container death force-ejects all occupants at the container's last position.
9. **Portal network consistency:** All Arbiters hosting anchors in a network have identical network state after Controller replication converges.
10. **Portal teleportation:** Cross-Arbiter portal usage triggers handoff to the destination Arbiter deterministically.
11. **Portal displacement:** Teleportation through portals is visible to P-63 (Movement-Damage Scalar) as straight-line displacement.

## 8. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `01-spatial-runtime-kernel.md` | Topology epochs (§4) — spatial instances are sub-partitions within a single Arbiter, not topology-level operations. Portal networks coordinate via the Controller but do not create new Arbiters. |
| `01-1-spatial-primitive-catalog.md` | P-08 (Dynamic Collision Injection) is the base for P-57. P-06 (Attached Kinematics) is the base for P-58. P-01 (Instant Translation) is the base for P-59 teleportation. P-09 (Shape Overlap) queries run against instance R-Trees when applicable. |
| `01-2-entity-lifecycle-contract.md` | Container destruction triggers occupant ejection (lifecycle interaction). Instance entity migration interacts with dormancy/suspension flags. |
| `01-3-entity-relationship-contract.md` | P-58 containers use P-06 attachment (from spatial catalog) and may use P-34 bindings for enter/exit tracking. Portal anchors carry owner entity linkage for death cleanup. |
| `04-1-game-adapter-contract.md` | Stage 12 (`ObserverScopedPayloadEmission`) is where P-52 visibility filtering is applied at the engine boundary. |
| `04-2-game-adapter-api-contract.md` | Portal network coordination uses Controller relay. Instance creation/destruction and container mutations flow through `StageOutcome`. |
| `00-1-core-baseline-profile.md` | Baseline bounds for team count, instance count, polyline capacity, container capacity, and portal network limits. |
| `docs-game-compiler/ability-primitives/08-visibility-ui.md` | Game-layer description of P-52. |
| `docs-game-compiler/ability-primitives/09-spatial-instance.md` | Game-layer descriptions of P-56, P-57, P-58, P-59. |
