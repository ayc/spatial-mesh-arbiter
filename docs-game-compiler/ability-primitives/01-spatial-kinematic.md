# 1. Spatial & Kinematic Primitives

*How things move and exist in space.*

---

### P-01: Instant Translation

**Description:** Teleportation — repositioning an entity to a target coordinate without physical traversal of intermediate space.

**Sketches:** SK-35 (Blink Strike), SK-36 (Shadow Step), SK-69 (Portal Pair), SK-72 (Nydus Network)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Must update the entity's authoritative position atomically within a single tick. Cross-boundary teleports trigger an immediate handoff to the destination Arbiter. The displacement is visible to P-63 (Movement-Damage Scalar) — a teleport under Rupture deals damage proportional to the straight-line distance.

---

### P-02: Forced Displacement

**Description:** Modifying an entity's velocity over time with friction/decay, causing involuntary movement (knockback, pull, drag).

**Sketches:** SK-01 (Toss), SK-31 (Vortex), SK-43 (Drag), SK-56 (Knockback Projectile)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Displacement vectors are applied during the kinematic phase and resolved before combat. Must interact with P-04 (Positional Clamping) — a leashed entity's displacement is bounded. Subject to P-62 (Categorized CC Immunity) displacement immunity. All arithmetic uses `I32F32` saturating ops.

---

### P-03: Trajectory Steering

**Description:** Continuously adjusting an entity's velocity vector toward or away from a moving target each tick (homing, fleeing, charming).

**Sketches:** SK-78 (Fear), SK-101 (Charm), SK-55 (Growing Projectile — homing variant)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The steering force is capped per tick to prevent instant snapping. Fear inverts the vector (away from source). Charm steers toward the source. The entity retains its base movement speed — only direction is overridden. Subject to P-62 (Categorized CC Immunity) forced-movement immunity.

---

### P-04: Positional Clamping

**Description:** Hard distance limits that zero-out or reverse velocity when an entity crosses a spatial threshold relative to an anchor point.

**Sketches:** SK-04 (Tether), SK-88 (Positional Leash)

**Engine layer:** `docs-core/`

**Dependencies:** P-34 (Persistent Linkage) — the anchor relationship must survive handoffs.

**Key constraints:** Evaluated after all movement resolution each tick. If the entity exceeds the max-distance radius, its position is clamped to the boundary. The anchor can be another entity (tether) or a fixed world coordinate (leash). Breaking the leash (if the ability allows it) triggers a snap-back or a damage event.

---

### P-05: Historical State Buffer

**Description:** Opt-in rolling memory of `(position, hp, tick)` tuples over the last N seconds for an entity, enabling temporal rewind.

**Sketches:** SK-37 (Time Rewind)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The buffer is bounded: at 60Hz and 4 seconds, that is 240 entries per entity. Only entities with an active rewind ability allocate the buffer — not all entities. On rewind, the entity's position and HP are restored from the buffer entry, and the buffer is cleared. Buffer entries are part of SoftState and transfer on handoff.

---

### P-06: Attached Kinematics

**Description:** Parenting a volume or entity to another moving entity so that it follows the parent's transform each tick.

**Sketches:** SK-08 (Aura), SK-66 (Symbiote), SK-71 (Sticky Bomb), SK-99 (Target-Tracking Zone)

**Engine layer:** `docs-core/`

**Dependencies:** P-34 (Persistent Linkage) — the parent-child relationship is a binding.

**Key constraints:** The attached entity's position is overwritten each tick to match the parent's position plus an optional offset. The attached entity does not participate in independent kinematic resolution. If the parent crosses an Arbiter boundary, the attached entity must hand off with it or be orphaned (design choice per ability).

---

### P-07: Entity-as-Kinematic-Volume

**Description:** Temporarily promoting an entity's hitbox to a sweeping collision volume that deals damage or applies effects to anything it passes through.

**Sketches:** SK-34 (Charge), SK-39 (Spectral Dash), SK-74 (Hit-Confirmed Dash)

**Engine layer:** `docs-core/`

**Dependencies:** P-09 (Shape Overlap Query) — the sweep checks overlap each tick.

**Key constraints:** The entity moves along a path for a fixed number of ticks. Each tick, the engine performs a shape overlap query at the entity's current position to detect collisions. A hit-list prevents the same target from being hit twice during one sweep. On collision, the entity may stop (charge pin) or continue through (spectral dash).

---

### P-08: Dynamic Collision Injection

**Description:** Temporarily adding or removing static geometry from the spatial grid at runtime.

**Sketches:** SK-03 (Terrain Wall), SK-76 (Build Zone)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Injected geometry participates in pathfinding and collision queries immediately on the next tick. The geometry has a bounded lifetime and a bounded maximum area (prevents griefing/server overload). Removal restores the previous collision state. The geometry is replicated to neighboring Arbiters via the standard zone replication path if it overlaps a boundary.
