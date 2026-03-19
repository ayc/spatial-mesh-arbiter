# SK-85: Ring Geometry

## Designer Intent

I cast a ring of frost at a target position. After a brief delay, the ring activates — enemies standing ON THE RING (the circumference) are damaged and rooted. Enemies standing INSIDE the ring (at the center) are completely safe. The ring is a donut shape — only the edge matters.

## Primitive Composition

P-09 (Shape Overlap Query) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Cast at target position — ring indicator appears (brief delay before activation)
2. After 0.5 second delay: ring activates
3. Enemies ON the ring (within the band between inner and outer radius) are hit: damage + root
4. Enemies INSIDE the ring (within inner radius) are NOT hit — safe zone
5. Enemies OUTSIDE the ring (beyond outer radius) are NOT hit
6. One-time activation (not a persistent zone — single check on activation)
7. Visual: frost ring on the ground, enemies caught on the edge are frozen

## Engine Primitives Required

### Ring/Donut Spatial Query

All existing spatial queries:
- Circle (SK-29): `distance(entity, center) <= radius`
- Cone (SK-49): `distance <= range AND angle <= half_angle`
- Line (SK-63): `distance_to_line(entity, line) <= width`

Ring adds:
```
struct RingQuery {
    center: Vec2F,
    inner_radius: SimFixed,
    outer_radius: SimFixed,
}
```

Match condition: `inner_radius <= distance(entity, center) <= outer_radius`

Entities CLOSER than `inner_radius` are NOT hit. Entities FURTHER than `outer_radius` are NOT hit. Only entities in the band between the two radii are hit.

### New Geometry Primitive

The engine's geometry system needs ring/donut as a supported shape:

```
enum AoEGeometry {
    Circle { radius: SimFixed },
    Cone { half_angle: SimFixed, range: SimFixed },
    Line { length: SimFixed, width: SimFixed },
    Ring { inner_radius: SimFixed, outer_radius: SimFixed },
}
```

The ring query is computationally cheap — two distance comparisons per entity, same cost as a circle query plus one extra comparison.

### Delayed Activation

The ring has a brief delay (0.5s) between cast and activation. During the delay:
- The ring indicator is visible to all players (friend and foe)
- Enemies can react by moving INTO the center (safe) or AWAY from the ring
- The ring is a "scheduled event" — the Arbiter processes it at activation_tick

This is a standard delayed AoE (like SK-29 Blizzard's first pulse) but with ring geometry instead of circle.

## Cross-Boundary Concerns

TODO: Standard AoE cross-boundary pattern. The ring is centered at a position on one Arbiter. Entities on the ring that are Ghosts receive damage/root relays. The ring's band might straddle an Arbiter boundary — part of the ring is in one region, part in another. Only entities in the local portion + Ghosts in the remote portion are checked.

## Compiler Requirements

TODO: Designer specifies: shape (ring), inner radius, outer radius, delay (0.5s), one-time activation, damage + root on entities in the ring band, center is safe. Compiler produces:
- AoE definition with `Geometry::Ring { inner_radius, outer_radius }`
- Delayed activation timer
- Spatial query using ring geometry (two-distance-comparison check)
- Damage + CC payload applied to matched entities

The compiler adds Ring to the geometry type system alongside Circle, Cone, and Line.

## Open Questions

- Can the ring be used as a persistent zone (like SK-29 Blizzard but ring-shaped)?
- Can the inner and outer radii be different sizes to create thin or thick rings?
- Does the ring's root duration vary based on position within the band (edge = longer root)?
- Can the ring be combined with other shapes (ring + cone = arc)?
- Does the ring check use entity center-point or hitbox edge (entity partially on the ring)?
- Can ring geometry be used for beneficial effects (SK-16 Holy Ground as a ring — healing on the edge)?
- How does the ring interact with forced displacement (SK-01 Toss landing on the ring)?
- Can the ring be placed so its center is on an Arbiter boundary?
