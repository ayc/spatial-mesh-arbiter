# SK-55: Growing Projectile

## Designer Intent

I roll a giant snowball in a target direction. As the snowball travels, it grows in size — its collision radius and damage increase with distance traveled. Enemies hit are pushed along with the snowball, adding to its mass. The snowball keeps rolling until it hits a wall or reaches max distance.

## Primitive Composition

P-32 (Actor Spawning) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (from requested aim direction)

## Observable Behavior

1. Snowball launches in the cast direction at moderate speed
2. As the snowball travels, its visual size and collision radius grow (e.g., starts at radius 1, grows to radius 4 at max range)
3. Damage scales with distance traveled (further = more damage)
4. The first enemy hit is pushed along with the snowball (captured, similar to SK-34 Charge)
5. Subsequent enemies hit are also pushed — the snowball accumulates entities
6. If the snowball hits a wall: detonates, dealing damage to all pushed enemies and enemies in the impact zone
7. If no wall is hit: snowball expires at max range, releasing pushed enemies
8. Visual: growing snowball, enemies visibly stuck to the front, explosion on wall impact

## Engine Primitives Required

### Dynamic Projectile Properties

All existing ProjectileActors have fixed properties (speed, radius, damage). The Growing Projectile has **properties that change per tick**:

```
struct GrowingProjectile {
    base_radius: SimFixed,
    growth_rate_per_tick: SimFixed,
    current_radius: SimFixed,       // Recalculated each tick
    base_damage: SimFixed,
    damage_growth_per_unit: SimFixed,
    distance_traveled: SimFixed,    // Accumulated each tick
    captured_entities: Vec<EntityID>,
}
```

Each tick:
1. Move the projectile forward by its velocity
2. `distance_traveled += velocity_magnitude`
3. `current_radius = base_radius + (distance_traveled * growth_rate_per_tick)`
4. Collision check uses `current_radius` (growing hitbox)
5. Damage on hit = `base_damage + (distance_traveled * damage_growth_per_unit)`

### Entity Accumulation

Unlike SK-34 Charge (captures one entity), the Growing Projectile captures ALL enemies it hits:
- Each captured entity's position is locked to the snowball's front face
- Multiple entities share the front — they stack or spread along the snowball's surface
- Captured entities are displaced (hard CC, cannot act)
- On detonation/expiry: all captured entities are released at the snowball's current position

The projectile maintains a `captured_entities` list. Each tick, all captured entities' positions are updated to track the snowball.

### Growing Collision Radius

The spatial query for collision must use the CURRENT radius, not the original. As the snowball grows, it sweeps a wider path. Entities that were safe at distance might be caught as the snowball approaches and its radius grows to encompass them.

This means the collision query changes shape each tick — the swept area per tick is not a fixed capsule but a widening one.

## Cross-Boundary Concerns

TODO: The snowball is a projectile that can cross Arbiter boundaries — standard projectile handoff. But it carries a growing list of captured entities. Handoff must transfer:
- The projectile state (position, velocity, distance_traveled, current_radius)
- The entire `captured_entities` list
- Each captured entity's state

If the snowball captures a Ghost, the Ghost's owning Arbiter must release the entity to the snowball's Arbiter. As the snowball crosses a boundary with 3 captured entities, that's 1 projectile handoff + 3 entity handoffs simultaneously.

Wall collision near a boundary: if the wall is in the neighbor's static_grid, does the snowball's Arbiter know about it? Ghost-range static geometry awareness matters here.

## Compiler Requirements

TODO: Designer specifies: initial radius, growth rate, initial damage, damage scaling, speed, max range, capture behavior (push all hit enemies), wall detonation behavior, release on expiry. Compiler produces:
- ProjectileActor with per-tick mutable properties (radius, damage scaling)
- Entity capture list (extending SK-34's single capture to multi-capture)
- Growth formula as a deterministic function of distance_traveled
- Wall collision trigger (detonation)
- Release behavior on detonation and expiry

The compiler needs to support **dynamic projectile properties** — projectile stats that are functions of runtime state, not fixed at spawn time.

## Open Questions

- Is there a maximum number of entities the snowball can capture (bounded for performance)?
- Can the snowball capture allied entities (friendly fire push)?
- Does the snowball pass through minions/summons or capture them too?
- Can captured entities be healed by allies (SK-16 Holy Ground) while being pushed?
- Does the snowball's damage use caster's stats at cast time (epoch-pinned) or scale independently?
- If the snowball is very large (max radius) in a dense area, how many collision checks per tick?
- Can the snowball be destroyed by enemies (does it have HP)?
- How does the snowball interact with SK-03 Terrain Wall — does a player-placed wall stop it?
- Can the snowball be deflected or redirected by abilities (SK-31 Vortex pull)?
- Does the growth rate account for Kinematic Dilation (snowball grows slower in dilated zones)?
