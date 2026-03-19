# SK-80: Wall Bounce

## Designer Intent

I fire an arrow that bounces off walls. After hitting a wall, it reflects at the appropriate angle and continues, potentially hitting enemies around corners. The arrow can bounce up to 3 times before expiring. Each bounce maintains the arrow's speed.

## Primitive Composition

P-32 (Actor Spawning) → P-10 (Swept-Segment Raycast)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (from requested aim direction)

## Observable Behavior

1. Arrow fires in the cast direction
2. If the arrow hits static geometry (wall): it reflects off the surface at the angle of incidence
3. The reflected arrow continues with the same speed
4. Each bounce can hit enemies in its new path
5. Maximum 3 bounces — after the 3rd bounce, the arrow expires
6. If the arrow hits an enemy at any point: it deals damage and expires (consumes on hit)
7. Visual: arrow with trail, visible bounce off walls, potentially hitting enemies behind cover

## Engine Primitives Required

### Projectile Wall Reflection

Standard projectiles either pass through geometry or stop on impact. Wall-bouncing adds a third behavior: **reflect and continue**:

```
enum WallCollisionMode {
    Stop,         // Projectile stops/detonates (standard)
    PassThrough,  // Projectile ignores walls (rare)
    Reflect {     // Projectile reflects off wall surface
        max_bounces: u8,
        current_bounces: u8,
    },
}
```

Each tick during projectile movement:
1. Raycast along the projectile's velocity vector
2. Check for entity collision (first-hit, like SK-43)
3. Check for static geometry collision (wall hit)
4. If entity hit first: deal damage, despawn
5. If wall hit first: calculate reflection vector, update velocity, increment bounce counter
6. If bounce counter exceeds max: despawn

### Reflection Vector Calculation

On wall collision, the projectile's velocity is reflected:
```
let normal = wall_surface_normal;  // Normal of the wall face hit
let reflected = velocity - 2 * dot(velocity, normal) * normal;
projectile.velocity = reflected;
```

The wall surface normal must be available from the static_grid collision query. Currently, `static_grid.query_segment_aabb()` returns whether a segment intersects an AABB — it may need to also return the collision normal for the reflection calculation.

### Multi-Segment Path Per Tick

A fast projectile might bounce multiple times within a single tick. The Arbiter must handle:
1. Raycast from position A in direction D
2. Hit wall at point B — reflect to direction D'
3. Raycast from B in direction D'
4. Hit wall at point C — reflect to direction D''
5. Continue until: max bounces reached, enemy hit, or remaining distance exhausted

This is a **multi-segment raycast within a single tick** — the projectile's path is a polyline, not a straight line.

## Cross-Boundary Concerns

TODO: The bouncing projectile might bounce toward and across an Arbiter boundary. After reflecting off a wall, the new direction could point into a neighbor's region. Standard projectile handoff applies, but the handoff must include the bounce count and current velocity (including reflection).

If the wall is near a boundary, the reflection might send the projectile into a region the current Arbiter doesn't fully know about. Ghost geometry awareness matters — does the Arbiter know about walls in the neighbor's region?

## Compiler Requirements

TODO: Designer specifies: projectile speed, max bounces (3), first-hit collision with entities, reflect on wall collision, damage on hit, consume on entity hit, expire after max bounces. Compiler produces:
- ProjectileActor with `WallCollisionMode::Reflect { max_bounces: 3 }`
- Per-tick multi-segment raycast logic
- Reflection vector calculation using wall normals
- Bounce counter tracking

The compiler needs to support wall reflection as a projectile behavior mode alongside Stop and PassThrough.

## Open Questions

- Does the arrow lose speed on each bounce, or maintain full speed?
- Can the arrow bounce off SK-03 Terrain Wall (player-placed walls)?
- Does each bounce segment independently check for entity collision?
- Can the arrow bounce off the edge of SK-60 Bunker?
- If the arrow bounces back toward the caster, can it hit allies (friendly fire)?
- Does the reflection angle use perfect physics or is there a spread/randomness?
- Can enemies predict the bounce path (visual telegraph showing the reflection trajectory)?
- How does the multi-segment-per-tick raycast interact with the frame budget?
- Can wall-bouncing be combined with other projectile modes (bounce + pierce)?
- What happens if the arrow bounces into a corner (two walls) — does it reflect correctly off both?
