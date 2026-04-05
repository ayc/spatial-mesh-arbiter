# SK-03: Terrain Wall

## Designer Intent

My character creates a temporary wall at a target position that blocks all movement and projectiles for 5 seconds, then crumbles. I can use this to cut off escape routes, split enemy formations, or block incoming projectiles.

## Primitive Composition

P-08 (Dynamic Collision Injection) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Wall placement position (requested ground-target position)
- Wall orientation (perpendicular to caster-to-target vector, or explicit angle)

## Observable Behavior

1. Wall appears instantly at the targeted placement point.
2. The wall is a fixed corridor barrier, not a summoned creature or attackable object.
3. All ordinary movement/pathing treats the wall as impassable while it lasts.
4. Projectiles and other collision-tested lines hit the wall while it is active.
5. The wall persists for 5 seconds.
6. After expiry, the injected geometry is removed and movement/projectile travel pass freely again.
7. The base reference wall has no HP and cannot be destroyed early.

## Engine Primitives Required

Terrain Wall is now the canonical `inject_geometry(mode = segment)` reference.

The recommended lowering is:

1. author one `inject_geometry` effect with:
   - `position = cursor_position`
   - `mode = segment`
   - `duration_ticks = 300`
   - `blocks_movement = true`
   - `blocks_projectiles = true`
   - authored `length` and `width`
   - `heading_from = caster_position`
   - `heading_to = cursor_position`
   - `orientation = perpendicular_to_heading`
2. let the runtime lower that to one fixed `P-57` corridor centered on the placement point
3. remove it automatically on ordinary duration expiry

This keeps the mechanic inside the existing dynamic-geometry surface:

- no wall actor or HP shell is required
- the barrier is one timed corridor record in the runtime collision structure
- the geometry participates in ordinary pathing, skillshot collision, and world-block tests while
  active
- removal is just timed lifetime cleanup, not an extra destruction subsystem

## Cross-Boundary Concerns

Terrain Wall follows the canonical injected-geometry replication rules.

1. If the wall overlaps or approaches an Arbiter boundary, the injected corridor is mirrored into
   the neighboring authority/query structures through the same core dynamic-geometry replication
   rules from `docs-core/`.
2. Movement/pathing and projectile collision on either side of the seam therefore see the same
   blocker without inventing a second wall actor.
3. Projectiles crossing a boundary continue to test against the replicated corridor on their current
   authoritative owner just like they test against other dynamic blockers.
4. The wall itself never hands off because it is not an autonomous actor. It is one timed geometry
   record replicated to the relevant neighboring owners/query structures.
5. If an entity is already overlapping the placement when the wall appears, this reference does not
   teleport that entity. Subsequent movement and forced displacement resolve against the newly
   injected blocker through the ordinary clamp/separation path.

## Compiler Requirements

Designer specifies:

- placement range
- corridor length and width
- duration
- whether movement is blocked
- whether projectiles are blocked
- the orientation rule (this reference uses the perpendicular-to-cast heading)

Compiler emits:

- one `inject_geometry(mode = segment)` effect
- the authored corridor dimensions and lifetime
- heading data derived from `caster_position -> cursor_position`

Compiler validates:

1. `duration_ticks > 0`
2. `length > 0` and `width > 0`
3. at least one of `blocks_movement` or `blocks_projectiles` is `true`
4. segment mode has both heading inputs
5. the wall is expressed as one timed corridor injection, not as a spawned actor with hidden
   collision side effects

## Resolved Interaction Notes

- This reference is intentionally non-destructible. A destructible wall is a different authored
  variant and should use a spawned actor shell instead.
- Placements that would embed the whole corridor in forbidden static geometry should be rejected by
  ordinary placement validation; this reference does not auto-trim or partially carve the wall.
- Forced displacement, dash, and landing-resolution mechanics still use ordinary movement clamps, so
  a Toss or Charge trying to end inside the wall stops at the nearest legal committed position.
- Simultaneous wall count/area is bounded by the same core `max_dynamic_geometry_per_arbiter` and
  `max_dynamic_geometry_area` limits as other injected geometry.
