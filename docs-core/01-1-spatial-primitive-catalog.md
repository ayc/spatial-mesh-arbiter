# Spatial Primitive Catalog

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Specify the engine-provided spatial operations that game adapters depend on for movement, targeting, and geometry. This contract is Amendment A from `PRIMITIVE_IMPACT_ASSESSMENT.md`.

**Primitives formalized:** P-01 through P-14 (8 kinematic mutations + 6 spatial queries)

---

## 1. Scope

This catalog defines the spatial operations the engine MUST expose to the game adapter via the `dispatch_stage` pipeline. The adapter invokes these operations by emitting IR instructions tagged to specific pipeline stages. The engine executes them against the R-Tree spatial index and returns results through binding values or committed state changes.

This contract extends `01-spatial-runtime-kernel.md` §1 ("movement integration and collision primitives") with concrete operation specifications.

## 2. Conventions

### 2.1 Types

| Type | Definition |
|------|-----------|
| `Vec2F` | Two-component fixed-point vector (`I32F32 × I32F32`) |
| `SimFixed` | Single fixed-point scalar (`I32F32`) |
| `EntityID` | Generational entity identifier |
| `EntitySet` | Bounded list of `EntityID` values (max size configurable) |
| `ShapeDef` | Discriminated union: `Circle { center: Vec2F, radius: SimFixed }`, `Box { center: Vec2F, half_extents: Vec2F }`, `Cone { origin: Vec2F, direction: Vec2F, half_angle: SimFixed, radius: SimFixed }`, `Ring { center: Vec2F, inner_radius: SimFixed, outer_radius: SimFixed }` |

### 2.2 Ghost Inclusion Policy

Each operation specifies whether Ghost entities (cross-boundary visibility proxies from `01-spatial-runtime-kernel.md`) are included in results. When Ghosts ARE included, the adapter is responsible for emitting relay events to the Ghost's authoritative Arbiter for any mutations that affect the Ghost.

### 2.3 Stage Binding

Each operation specifies which pipeline stage(s) it executes in. These bindings are authoritative — they override any conflicting stage assignments in other documents. The compiler MUST tag IR instructions to match these bindings.

### 2.4 Design Rationale: Algorithm Neutrality
This catalog defines the **WHAT** (inputs, outputs, Ghost policy, determinism guarantees), not the **HOW**. 
- **Implementation Freedom:** Developers MAY choose any intersection algorithm (e.g., SAT, Arvo’s method, Gilbert-Johnson-Keerthi) for primitives such as `P-09` or `P-10`. 
- **Performance:** Algorithms SHOULD be optimized for the specific hardware/SIMD targets of the implementation.
- **Compliance:** As long as the implementation (1) uses `SimFixed` arithmetic, (2) follows the rounding/overflow rules of the kernel, and (3) passes the machine-checkable **Conformance Test Matrix (05-1)**, the specific math implementation is non-normative.

---

## 3. Kinematic Mutations (P-01 through P-08)

Operations that change entity positions or spatial geometry. Executed during the kinematic phases of the pipeline (Stages 4, 5, 6).

### 3.1 P-01: Instant Translation

**Operation:** Reposition an entity to a target coordinate without physical traversal.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | `EntityID` | Entity to teleport |
| `destination` | `Vec2F` | Target position |
| `max_distance` | `SimFixed` | Optional distance clamp (0 = unlimited) |

**Output:** `resolved_position: Vec2F` — the actual position after clamping and collision checks.

**Stage:** `KinematicResolution` (5)

**Engine behavior:**
1. Compute displacement vector from current position to destination.
2. If `max_distance > 0` and displacement exceeds it, clamp to max distance along the displacement vector.
3. Validate the resolved position is not inside static collision geometry. If it is, find the nearest valid position.
4. Update the entity's authoritative position atomically.
5. If the resolved position falls outside the current Arbiter's R-Tree partition, queue an immediate handoff.

**Ghost policy:** N/A — teleportation operates on the authoritative entity only. Cross-boundary teleports trigger handoff, not Ghost queries.

**Cross-boundary:** If destination is on a different Arbiter, the engine initiates a handoff to the destination Arbiter at the end of Stage 5. The entity does not exist on both Arbiters simultaneously.

**Determinism:** The resolved position MUST be identical for identical inputs across hosts.

---

### 3.2 P-02: Forced Displacement

**Operation:** Apply an involuntary velocity impulse to an entity with friction/decay over time.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | `EntityID` | Entity to displace |
| `destination` | `Vec2F` | Target landing position (for arc/linear displacement) |
| `velocity` | `Vec2F` | Alternative: raw velocity impulse (for knockback) |
| `arc` | `bool` | Whether displacement follows a parabolic arc |
| `duration_ticks` | `u32` | Displacement duration |
| `max_distance` | `SimFixed` | Optional distance clamp |

**Output:** `resolved_destination: Vec2F` — the actual landing position after clamping.

**Stage:** `KinematicResolution` (5)

**Engine behavior:**
1. Compute the displacement path (linear or arc) from current position to destination over `duration_ticks`.
2. Each tick during the displacement, advance the entity along the path by `1/duration_ticks` of the total distance.
3. During displacement, the entity's voluntary movement is suppressed (engine sets internal `displacement_active` flag).
4. On each step, check collision against static geometry. If collision, stop at the collision point.
5. If `max_distance > 0`, clamp total displacement.
6. Expose `resolved_destination` as a binding value for downstream PostKinematic queries.

**Ghost policy:** N/A — displacement operates on the authoritative entity.

**Cross-boundary:** If the displacement path crosses an Arbiter boundary, the entity hands off mid-displacement. The receiving Arbiter continues the displacement from the handoff position with the remaining duration.

**Determinism:** Path interpolation MUST use `I32F32` arithmetic. Arc height is computed as `arc_height = displacement_distance * arc_height_ratio` (configurable, default 0.25).

---

### 3.3 P-03: Trajectory Steering

**Operation:** Continuously adjust an entity's movement direction toward or away from a reference point each tick.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | `EntityID` | Entity being steered |
| `mode` | `enum` | `toward_source`, `away_from_source`, `toward_target` |
| `reference_entity` | `EntityID` | The entity to steer toward/away from |
| `max_steer_rate` | `SimFixed` | Maximum angular change per tick (prevents instant snapping) |

**Output:** None (modifies the entity's velocity direction in-place).

**Stage:** `PreKinematic` (4)

**Engine behavior:**
1. Compute the direction vector from the steered entity to the reference entity (or inverse for `away_from_source`).
2. Interpolate the entity's current facing/velocity direction toward the target direction by at most `max_steer_rate` per tick.
3. The entity retains its current speed — only direction is modified.
4. The steered entity's `CAN_MOVE` flag is NOT cleared. The entity "moves" under its own speed but in a direction it doesn't control.

**Ghost policy:** The reference entity MAY be a Ghost. The engine uses the Ghost's last-known position for direction computation. Stale Ghost position introduces directional error proportional to Ghost update cadence — this is acceptable for gameplay (fear/charm is approximate, not pixel-perfect).

**Cross-boundary:** If the reference entity is a Ghost and the steered entity crosses a boundary while being steered, the steering state (mode, reference entity ID, steer rate) transfers with the handoff. The new Arbiter continues steering using its own Ghost data for the reference entity.

---

### 3.4 P-04: Positional Clamping

**Operation:** Enforce a hard distance limit between an entity and an anchor point, zeroing or reversing velocity on threshold violation.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | `EntityID` | Entity being clamped |
| `anchor` | `EntityID` or `Vec2F` | Anchor point (entity or fixed position) |
| `max_distance` | `SimFixed` | Maximum allowed distance |
| `on_violation` | `enum` | `clamp` (snap to boundary), `reverse` (bounce back), `damage` (apply damage per unit exceeded) |

**Output:** None (modifies entity position in-place if violated).

**Stage:** `PostKinematic` (6)

**Engine behavior:**
1. After all kinematic resolution is committed (Stage 5 engine boundary), compute distance between entity and anchor.
2. If distance exceeds `max_distance`:
   - `clamp`: Move entity to the nearest point on the max-distance circle.
   - `reverse`: Reverse the entity's velocity component along the anchor axis.
   - `damage`: Calculate excess distance and emit a combat event (re-enters at Stage 7 PreMitigation next tick).
3. If the anchor is an `EntityID`, use the anchor entity's authoritative position (or Ghost position if cross-boundary).

**Ghost policy:** The anchor MAY be a Ghost. Distance is computed against the Ghost's last-known position. This introduces jitter proportional to Ghost update cadence — acceptable for tether/leash mechanics where the tolerance is large relative to Ghost error.

**Cross-boundary:** If the anchor entity is on a different Arbiter, the clamped entity uses the Ghost position. If the clamped entity would need to cross a boundary to satisfy the clamp, the engine moves it to the boundary and queues a handoff.

---

### 3.5 P-05: Historical State Buffer

**Operation:** Maintain a rolling buffer of `(position, hp, tick)` snapshots for an entity, enabling temporal rewind.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | `EntityID` | Entity whose history is recorded |
| `buffer_duration_ticks` | `u32` | How many ticks of history to retain |

**Output:** On rewind request: `rewound_position: Vec2F`, `rewound_hp: SimFixed`.

**Stage:** `PostKinematic` (6) for recording; rewind triggers execute via adapter `StageOutcome` mutations.

**Engine behavior:**
1. Each tick during PostKinematic, if the entity has an active history buffer, append `(position, phase_hp, current_tick)` to the buffer.
2. The buffer is a fixed-size ring buffer: `buffer_size = buffer_duration_ticks` entries. Oldest entries are overwritten.
3. On rewind (adapter emits a rewind mutation): the engine looks up the buffer entry at the requested tick offset and restores the entity's position and HP.
4. After rewind, the buffer is cleared (no rewind-of-rewind).

**Ghost policy:** N/A — the buffer is local to the authoritative entity.

**Cross-boundary:** The buffer is SoftState and transfers during handoff. If the entity hands off, the new Arbiter continues recording. Buffer entries from the old Arbiter remain valid (they store absolute positions, not relative).

**Bounds:** `max_history_buffer_ticks` defined in `00-1-core-baseline-profile.md`. At 60Hz and 4 seconds, this is 240 entries × ~20 bytes = ~4.8 KB per entity. Only entities with active rewind abilities allocate buffers.

---

### 3.6 P-06: Attached Kinematics

**Operation:** Parent one entity's position to another entity's transform, with an optional offset.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `child_entity_id` | `EntityID` | Entity being attached |
| `parent_entity_id` | `EntityID` | Entity to follow |
| `offset` | `Vec2F` | Positional offset from parent (default: zero) |

**Output:** None (child position updated each tick automatically).

**Stage:** `KinematicResolution` (5) — after voluntary and forced movement, before sweeps.

**Engine behavior:**
1. Each tick, set `child.position = parent.position + offset`.
2. The child entity does NOT participate in independent kinematic resolution — its velocity is ignored while attached.
3. The child remains in the R-Tree at its updated position (spatial queries include it).

**Ghost policy:** The parent MAY be a Ghost. If so, the child follows the Ghost's interpolated position. This produces smooth following for auras/symbiotes on cross-boundary entities, with latency proportional to Ghost update cadence.

**Cross-boundary:** If the parent entity crosses a boundary, the attached child SHOULD hand off with it (co-located handoff). If the child and parent end up on different Arbiters, the child follows the parent's Ghost position until reunited or the attachment is broken.

**Detach:** Setting `parent_entity_id` to null detaches the child. The child resumes independent kinematic resolution from its current position on the next tick.

---

### 3.7 P-07: Entity-as-Kinematic-Volume

**Operation:** Temporarily promote an entity's hitbox to a sweeping collision volume that checks overlap at each movement step.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | `EntityID` | Entity performing the sweep (e.g., charging entity) |
| `destination` | `Vec2F` | End point of the sweep |
| `duration_ticks` | `u32` | Duration of the sweep |
| `sweep_shape` | `ShapeDef` | Collision shape centered on the entity |
| `on_hit` | `enum` | `stop` (halt at first hit) or `pierce` (continue through) |
| `max_hits` | `u32` | Maximum entities to collide with |

**Output:** `hit_entities: EntitySet` — entities collided with during the sweep, in collision order.

**Stage:** `KinematicResolution` (5) — after attached kinematics, as the final kinematic sub-step.

**Engine behavior:**
1. Divide the path from current position to destination into `duration_ticks` steps.
2. At each step, advance the entity and perform a shape overlap query at the new position.
3. Newly overlapping entities are added to `hit_entities` (deduplication: each entity hit at most once per sweep).
4. If `on_hit == stop` and a hit occurs, halt the entity at the collision point.
5. If `on_hit == pierce`, continue through all collisions.
6. After the sweep completes (or stops), the entity's position is committed at the final point.

**Ghost policy:** Ghosts ARE included in sweep collision checks. A sweep that hits a Ghost generates a relay event to the Ghost's Arbiter for damage resolution.

**Cross-boundary:** If the sweep path crosses an Arbiter boundary, the entity hands off mid-sweep. The receiving Arbiter continues the sweep from the handoff point with remaining duration. Hit entities from the previous Arbiter are NOT included in the new Arbiter's `hit_entities` — the adapter must handle the combined hit list via relay events.

---

### 3.8 P-08: Dynamic Collision Injection

**Operation:** Temporarily insert or remove static geometry from the spatial collision grid.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `shape` | `ShapeDef` | Geometry to insert |
| `position` | `Vec2F` | World position |
| `duration_ticks` | `u32` | How long the geometry persists (0 = permanent until removed) |
| `blocks_movement` | `bool` | Whether entities collide with this geometry |
| `blocks_projectiles` | `bool` | Whether projectile actors collide with this geometry |

**Output:** `geometry_id: u32` — handle for later removal.

**Stage:** `PostKinematic` (6)

**Engine behavior:**
1. Insert the geometry into the static collision grid at the specified position.
2. The geometry participates in collision checks immediately on the next tick's kinematic resolution.
3. If `blocks_movement`, entity movement that would intersect the geometry is halted at the boundary.
4. If `blocks_projectiles`, projectile actors that intersect are stopped (triggering their on-hit logic).
5. On expiry (`current_tick >= insert_tick + duration_ticks`), the geometry is removed automatically.

**Ghost policy:** N/A — geometry is spatial data, not an entity. However, the geometry MUST be replicated to neighboring Arbiters if it overlaps the boundary overlap zone. Neighbors include it in their own collision checks for Ghost entities and projectiles crossing toward the injecting Arbiter.

**Cross-boundary:** If the geometry overlaps a partition boundary, the engine replicates the geometry definition to affected neighbors. Removal (expiry or explicit) also replicates.

**Bounds:** `max_dynamic_geometry_per_arbiter` and `max_dynamic_geometry_area` defined in `00-1-core-baseline-profile.md`. Injection attempts exceeding bounds MUST be rejected with a fault signal.

---

## 4. Spatial Queries (P-09 through P-14)

Operations that query the R-Tree for entities matching spatial and classification criteria. These are read-only — they return result sets but do not mutate state.

### 4.1 P-09: Shape Overlap Query

**Operation:** Return all entities whose positions fall within a given shape.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `shape` | `ShapeDef` | Query shape |
| `filter` | `FilterExpr` | Team/tag/alive filtering |
| `max_results` | `u32` | Result cap |

**Output:** `results: EntitySet` — matching entity IDs, ordered by distance from shape center.

**Stage:** `TargetResolution` (3) when center is intent-known; `PostKinematic` (6) when center depends on committed kinematic output.

**Engine behavior:**
1. Query the R-Tree for all entities within the shape's bounding box.
2. Refine with exact shape intersection test (`is_inside_with_tolerance`).
3. Apply `filter` (P-13 Tag/Allegiance Filtering) to exclude non-matching entities.
4. Sort by squared distance from shape center (ascending).
5. Truncate to `max_results`.

**Ghost policy:** Ghosts ARE included. When a Ghost appears in results and the adapter emits a damage event targeting that Ghost, the engine automatically generates a relay event to the Ghost's authoritative Arbiter.

**Tolerance:** The engine MUST use a configurable `shape_overlap_tolerance` (`SimFixed`, default: 0.01) to prevent false negatives at exact shape boundaries.

**Bounds:** `max_results` MUST be <= `selector_max_targets` from the baseline profile. The R-Tree broad-phase query is bounded by the shape's bounding box area.

---

### 4.2 P-10: Swept-Segment Raycast

**Operation:** Cast a ray from origin along a direction and return intersections with entities and static geometry.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `origin` | `Vec2F` | Ray start position |
| `direction` | `Vec2F` | Ray direction (normalized) |
| `max_length` | `SimFixed` | Maximum ray length |
| `filter` | `FilterExpr` | Entity filter |
| `mode` | `enum` | `first_hit` or `all_hits` or `reflect` |

**Output:**
- `first_hit` mode: `hit_entity: EntityID or null`, `hit_position: Vec2F`, `hit_normal: Vec2F`
- `all_hits` mode: `hits: list<RayHit>` ordered by distance
- `reflect` mode: `reflected_direction: Vec2F`, `reflect_position: Vec2F`

**Stage:** `TargetResolution` (3)

**Engine behavior:**
1. Cast the ray against the R-Tree (entity hitboxes) and static collision grid.
2. For `first_hit`: return the nearest intersection.
3. For `all_hits`: return all intersections sorted by distance, up to `max_results`.
4. For `reflect`: compute the reflection vector at the first static geometry intersection using the surface normal.

**Ghost policy:** Ghosts ARE included in entity intersection tests. Ghost intersection generates relay events for damage resolution.

**Cross-boundary:** The ray is clipped to the Arbiter's partition boundary. The engine does NOT extend rays across boundaries. If the adapter needs a cross-boundary raycast, it must emit a relay event to the neighboring Arbiter.

**Bounds:** Ray length is capped by `max_raycast_length` from the baseline profile.

---

### 4.3 P-11: N-Nearest Neighbor Selection

**Operation:** Find the N closest valid entities to a given point, supporting chain/bounce targeting.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `origin` | `Vec2F` | Search center |
| `n` | `u32` | Number of neighbors to find |
| `max_radius` | `SimFixed` | Search radius |
| `filter` | `FilterExpr` | Entity filter |
| `exclude_set` | `EntitySet` | Entities to skip (prevents chain bouncing back) |

**Output:** `neighbors: EntitySet` — the N nearest matching entities, ordered by distance.

**Stage:** `TargetResolution` (3)

**Engine behavior:**
1. Query the R-Tree for entities within `max_radius` of `origin`.
2. Apply `filter` and exclude `exclude_set`.
3. Sort by squared distance (ascending).
4. Return the first `n` results.

**Ghost policy:** Ghosts ARE included. Chain Lightning (SK-09) can bounce to a Ghost, generating a relay event.

**Bounds:** `n` MUST be <= `selector_max_targets`. `max_radius` MUST be <= `max_query_radius` from the baseline profile.

---

### 4.4 P-12: Facing/Dot-Product Check

**Operation:** Determine whether one entity is facing toward or away from another by computing the dot product of their facing vectors.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `viewer` | `EntityID` | Entity whose facing is checked |
| `target` | `EntityID` | Entity being looked at |
| `threshold` | `SimFixed` | Dot product threshold (e.g., 0.5 = roughly facing) |

**Output:** `result: bool` — true if the dot product meets the threshold.

**Stage:** `TargetResolution` (3)

**Engine behavior:**
1. Compute the direction vector from `viewer.position` to `target.position`.
2. Normalize both the direction vector and `viewer.facing_direction`.
3. Compute dot product.
4. Return `dot_product >= threshold` (for "facing toward") or `dot_product <= -threshold` (for "facing away").

**Ghost policy:** The target MAY be a Ghost. The engine uses the Ghost's last-known position. Facing checks against Ghosts have error proportional to Ghost update cadence — acceptable for backstab/cone gating.

**Entity facing:** Entities MUST have a `facing_direction: Vec2F` in their kinematic state, derived from last movement vector or set explicitly by the adapter.

---

### 4.5 P-13: Tag/Allegiance Filtering

**Operation:** Filter a set of entities by team ID, alive/dead state, structural tags, or targetability flags.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `input_set` | `EntitySet` | Entities to filter (from a prior query) |
| `filter` | `FilterExpr` | Composite filter expression |

**Output:** `filtered_set: EntitySet` — entities that pass the filter.

**Stage:** Applied as a sub-operation of P-09, P-10, P-11 — not invoked independently.

**Filter expressions:**
| Expression | Meaning |
|-----------|---------|
| `enemy_alive` | Different team AND `lifecycle_phase != Removed` AND `is_targetable` |
| `ally_alive` | Same team AND `lifecycle_phase != Removed` AND `is_targetable` |
| `all_alive` | Any team AND `lifecycle_phase != Removed` AND `is_targetable` |
| `enemy_dead` | Different team AND `lifecycle_phase == Removed` (for corpse queries) |

**Engine behavior:**
1. For each entity in the input set, evaluate the filter expression.
2. Entity `team_id` is a kernel-tracked field. The adapter sets it at spawn time.
3. `is_targetable` checks P-27 (Targetability Overrides) — untargetable entities are excluded.
4. Hostility Inversion (P-28): if the querying entity has `hostility_inverted = true`, `enemy` and `ally` are swapped.
5. Dormant entities: included or excluded based on the `dormant_targetable` flag (§3.3 of `01-2-entity-lifecycle-contract.md`).

**Ghost policy:** Ghosts carry `team_id` and `lifecycle_phase` in their Ghost update payloads. Filtering applies to Ghosts using these replicated fields.

---

### 4.6 P-14: Continuous Proximity Monitor

**Operation:** Track which entities are inside a zone and emit edge-triggered `OnEnter` and `OnLeave` events when entities cross the zone boundary.

**Input:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `zone_entity_id` | `EntityID` | The zone actor to monitor |
| `shape` | `ShapeDef` | Zone geometry |
| `filter` | `FilterExpr` | Entity filter for enter/leave |

**Output:** Per-tick: `entered: EntitySet`, `left: EntitySet`.

**Stage:** `PostKinematic` (6) — after all positions are committed.

**Engine behavior:**
1. The engine maintains a `current_occupants: HashSet<EntityID>` per monitored zone.
2. Each tick during PostKinematic, perform a P-09 Shape Overlap Query for the zone's shape.
3. Compare the new result set to `current_occupants`.
4. New entities (in result but not in occupants) → add to `entered`, add to `current_occupants`.
5. Departed entities (in occupants but not in result) → add to `left`, remove from `current_occupants`.
6. `entered` and `left` sets are available to the adapter as binding values for this stage.

**Ghost policy:** Ghosts ARE included in the overlap check. A Ghost entering a zone generates an `entered` event, enabling cross-boundary zone damage relay.

**Cross-boundary:** If a zone overlaps an Arbiter boundary, the zone entity's Ghost on the neighboring Arbiter carries the zone shape. The neighbor performs its own proximity monitoring for its local entities against the Ghost zone shape.

**Bounds:** `max_monitored_zones_per_arbiter` defined in `00-1-core-baseline-profile.md`. Each monitored zone incurs a per-tick overlap query cost.

---

## 5. Kinematic Resolution Order

Within Stage 5 (`KinematicResolution`), the engine MUST resolve kinematic primitives in this deterministic sub-order:

1. **P-02 Forced Displacement** — involuntary movement applied first.
2. **Voluntary movement** — player/AI-driven position changes.
3. **P-06 Attached Kinematics** — child positions updated to match parents.
4. **P-07 Entity-as-Kinematic-Volume** — sweeps executed last (they depend on final positions of other entities).

P-01 (Instant Translation) is atomic and executes before all other kinematic resolution (it sets position, not velocity).

P-03 (Trajectory Steering) executes in Stage 4 (PreKinematic), before kinematic resolution begins.

P-04, P-05, P-08 execute in Stage 6 (PostKinematic), after positions are committed.

This sub-order is normative and MUST NOT vary between ticks or between Arbiters.

---

## 6. Baseline Profile Keys

The following keys MUST be defined in `00-1-core-baseline-profile.md`:

| Key | Description |
|-----|-------------|
| `max_history_buffer_ticks` | Maximum rewind buffer depth per entity (P-05) |
| `max_dynamic_geometry_per_arbiter` | Maximum injected geometry objects (P-08) |
| `max_dynamic_geometry_area` | Maximum total area of injected geometry (P-08) |
| `selector_max_targets` | Maximum entities returned by any spatial query |
| `max_query_radius` | Maximum radius for spatial queries (P-09, P-11) |
| `max_raycast_length` | Maximum ray length (P-10) |
| `max_monitored_zones_per_arbiter` | Maximum active proximity monitors (P-14) |
| `shape_overlap_tolerance` | Tolerance for shape boundary intersection (P-09) |

---

## 7. Conformance Requirements

Implementations MUST pass:

1. **Kinematic determinism:** Same inputs produce identical positions across replay and across hosts.
2. **Sub-order enforcement:** Forced displacement resolves before voluntary movement, attached kinematics before sweeps.
3. **Ghost inclusion:** Spatial queries that specify Ghost inclusion MUST include Ghosts in results.
4. **Bounds enforcement:** Queries exceeding `selector_max_targets`, `max_query_radius`, or `max_raycast_length` MUST be rejected.
5. **Geometry lifecycle:** Injected geometry expires deterministically at the correct tick. Geometry replicates to neighbors when overlapping a boundary.
6. **Proximity monitor consistency:** `entered` and `left` sets are exact (no missed transitions, no duplicate events).
7. **Handoff preservation:** Displacement state, steering state, history buffers, attachment state, and occupant sets survive entity handoff.
8. **Collision safety:** Entities cannot be teleported or displaced into static geometry. The engine resolves to the nearest valid position.

## 8. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `01-spatial-runtime-kernel.md` | This catalog specifies the "movement integration and collision primitives" listed in §1. |
| `01-2-entity-lifecycle-contract.md` | Dormancy/suspension affect spatial query inclusion (§3.3, §4.2 of lifecycle contract). |
| `04-1-game-adapter-contract.md` | Pipeline stages 3-6 are where these operations execute. |
| `04-2-game-adapter-api-contract.md` | `DispatchStageRequest` carries IR instructions that reference these operations. |
| `00-1-core-baseline-profile.md` | Baseline bounds for query radii, buffer depths, geometry limits. |
| `docs-game-compiler/ability-primitives/01-spatial-kinematic.md` | Game-layer descriptions of P-01 through P-08. |
| `docs-game-compiler/ability-primitives/02-targeting-query.md` | Game-layer descriptions of P-09 through P-14. |
| `docs-game-compiler/03-1-compiler-ir-specification.md` | Stage assignments for IR instructions targeting these operations. |
