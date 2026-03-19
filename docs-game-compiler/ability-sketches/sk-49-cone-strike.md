# SK-49: Cone Strike

## Designer Intent

I swing my weapon in a wide arc in front of me, dealing damage and slowing all enemies in a cone-shaped area. The cone extends from my position outward in the direction I'm facing, like a fan or pizza slice.

## Primitive Composition

P-09 (Shape Overlap Query) → P-12 (Facing/Dot-Product Check)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (caster's facing direction or requested aim direction)

## Observable Behavior

1. Cast — instant AoE in a cone shape in front of the caster
2. Cone has an angle (e.g., 90 degrees) and a range (e.g., 6 meters)
3. All enemies within the cone take X damage
4. All enemies within the cone are slowed by 40% for 2 seconds
5. Allies are not affected
6. The cone is anchored to the caster's position and oriented in the cast direction
7. This is instant (not a zone that persists) — snapshot query at cast time
8. Visual: sweeping arc slash effect

## Engine Primitives Required

### Cone/Fan-Shaped Spatial Query

All existing spatial queries are circular (radius-based):
- SK-08 Aura: "entities within radius R of caster"
- SK-29 Blizzard: "entities within radius R of zone center"
- SK-20 Battle Cry: "allies within radius R"

A cone query needs:
```
struct ConeQuery {
    origin: Vec2F,         // Caster's position
    direction: Vec2F,      // Normalized direction vector
    half_angle: SimFixed,  // Half the cone's opening angle (e.g., 45° for a 90° cone)
    range: SimFixed,       // Maximum distance from origin
}
```

For each candidate entity, the query checks:
1. Is the entity within `range` distance from `origin`?
2. Is the angle between `direction` and the vector from `origin` to `entity` less than `half_angle`?

Both checks use fixed-point math. The angle check can be done via dot product (avoid trig functions for determinism):
```
let to_target = normalize(entity.position - origin);
let cos_angle = dot(direction, to_target);
let cos_threshold = cos(half_angle); // Pre-computed at compile time
return cos_angle >= cos_threshold;
```

### New Geometry Type in the Engine

The engine currently supports:
- Circle (radius-based queries)
- AABB rectangles (static_grid for collision)
- Line segments (raycast for LOS, projectile paths)

Cone is a new geometry primitive. It needs to be:
- Expressible in ability definitions (compiled by the game compiler)
- Supported by the Arbiter's spatial query system
- Deterministic (fixed-point angle math)

### Direction Dependency

Unlike circular AoEs (which are symmetric), cone queries depend on a **direction**. The cast direction comes from the caster's facing or requested aim direction. The ability definition must specify "cone oriented in cast direction" — the engine resolves the direction at cast time from the submitted input.

This is the first geometry that requires orientation, not just position + size.

## Cross-Boundary Concerns

TODO: The cone query originates from the caster's position on the caster's Arbiter. Enemies in the cone might be Ghosts near the boundary. Standard damage relay applies — same as any AoE hitting Ghosts.

One concern: the cone extends in a direction. If the cone points toward a boundary, most of its area might be in the neighboring Arbiter's region. The caster's Arbiter can only query locally + Ghosts. Enemies deep in the neighbor's region (beyond Ghost range) won't be detected. Is this acceptable, or does the cone need to be escalated to the neighbor (similar to Global Events for large radii)?

For short-range cones (6 meters), this shouldn't be an issue — Ghost range covers the cone. For long-range cones, it could matter.

## Compiler Requirements

TODO: Designer specifies: shape (cone), angle (90°), range (6m), damage, slow (40%, 2s), targeting filter (enemies), instant (snapshot, not persistent). Compiler produces:
- ConeQuery geometry definition with half_angle and range
- Pre-computed `cos_threshold` from half_angle (compile-time trig, not runtime)
- Snapshot AoE resolution: query → apply damage + slow to all results
- Direction binding: "use cast direction" or "use caster facing"

The compiler needs to support cone as a geometry type alongside circle. The geometry type determines which spatial query function the Arbiter uses.

## Open Questions

- Can cone abilities be used with auto-targeting, or do they always use the caster's facing/requested aim direction?
- Does the cone check use the center of the enemy's hitbox or the edge (an enemy partially inside the cone)?
- Can cone geometry be used for persistent zones (a cone-shaped Blizzard)?
- Are there other non-circular geometries needed (rectangle, line AoE, ring/donut)?
- How does the cone interact with SK-03 Terrain Wall — does the wall block the cone (LOS check per target)?
- Does the cone angle need to be configurable per ability, or are there standard angle presets (narrow 30°, medium 90°, wide 180°)?
- Can the cone be aimed independently of movement direction (explicit aim input vs facing aim)?
- Performance: is the dot-product angle check more expensive than a radius check? By how much per entity?
