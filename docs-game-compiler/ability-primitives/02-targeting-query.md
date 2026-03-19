# 2. Targeting & Query Primitives

*How the engine asks "who is involved?"*

---

### P-09: Shape Overlap Query

**Description:** Spatial intersection test — `is_inside_with_tolerance` for Box, Circle, Cone, and Donut/Ring geometries against entity positions.

**Sketches:** SK-01 (Toss impact AoE), SK-16 (Holy Ground), SK-29 (Blizzard), SK-32 (Minefield trigger), SK-49 (Cone Strike), SK-64 (Mosh Pit), SK-85 (Ring Geometry), SK-95 (Mass Effect Detonation)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Query runs against the R-Tree spatial index. All shape dimensions use `I32F32`. The tolerance parameter prevents false negatives at shape boundaries. Ghost entities are included in the query result set so that cross-boundary AoE can relay damage. Query results are bounded by a configurable max-entity cap to prevent degenerate O(n) explosions.

---

### P-10: Swept-Segment Raycast

**Description:** Line-of-sight and reflection vector queries — casting a ray from origin to direction and returning the first (or all) intersections.

**Sketches:** SK-63 (Steerable Beam), SK-80 (Wall Bounce — reflection vector)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The raycast tests against both entity hitboxes and P-08 (Dynamic Collision Injection) geometry. Reflection requires computing the surface normal at the hit point and reflecting the direction vector. Ray length is bounded to prevent unbounded computation. Results include hit position, hit entity ID, and surface normal.

---

### P-11: N-Nearest Neighbor Selection

**Description:** Spatial sorting to find the N closest valid targets to a given point, used for chain-targeting and bounce mechanics.

**Sketches:** SK-09 (Chain Lightning), SK-11 (On-Kill Cascade), SK-115 (Corpse Economy — nearest N corpses)

**Engine layer:** `docs-core/`

**Dependencies:** P-13 (Tag/Allegiance Filtering) — results are filtered by team/tag before distance sorting.

**Key constraints:** The query accepts a "visited set" of entity IDs to exclude (preventing Chain Lightning from bouncing back to the same target). Sorting is by squared distance to avoid sqrt. The result count N is bounded by the ability definition. Uses the R-Tree for efficient spatial lookup.

---

### P-12: Facing/Dot-Product Check

**Description:** Determining whether a target is facing toward or away from the source entity by computing the dot product of their facing vectors.

**Sketches:** SK-13 (Counter Strike — backstab detection), SK-103 (Facing-Dependent Effect)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Entities must have a facing direction in their kinematic state (derived from last movement vector or explicit facing). The dot-product threshold is configurable per ability (e.g., > 0.5 = "facing toward," < -0.5 = "facing away"). Result is a boolean used to branch ability resolution.

---

### P-13: Tag/Allegiance Filtering

**Description:** Filtering spatial query results by team ID, alive/dead state, structural tags, or custom classification flags.

**Sketches:** SK-100 (Ally Untargetable), SK-106 (Berserk — hostility inversion alters filtering), SK-13 (Tag-based target selection)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Every entity carries a team ID and a tag bitfield. Filters are composable: "enemies AND alive AND NOT untargetable." Filtering runs after spatial queries (P-09, P-11) but before combat resolution. The tag bitfield is bounded (e.g., 64 bits) and defined at compile time.

---

### P-14: Continuous Proximity Monitor

**Description:** Edge-triggered `OnEnter` and `OnLeave` events for spatial zones — detecting when entities cross a zone boundary rather than polling overlap each tick.

**Sketches:** SK-08 (Aura enter/leave), SK-30 (Trail of Fire), SK-33 (Shifting Sands), SK-75 (Self-Sustaining Zone), SK-120 (Combo Field — finisher enters field)

**Engine layer:** `docs-core/`

**Dependencies:** P-09 (Shape Overlap Query) — the proximity check uses the same shape definitions.

**Key constraints:** The monitor maintains a per-zone set of currently-overlapping entity IDs. Each tick, the current overlap set is compared to the previous set to emit enter/leave events. The per-zone entity set is bounded. Enter/leave events are the triggers for P-44 (Pulse Timer) zone effects. Ghost entities generate enter/leave events to enable cross-boundary zone damage relay.
