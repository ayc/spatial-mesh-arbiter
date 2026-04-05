# SK-55: Growing Projectile

## Designer Intent

I roll a giant snowball in a target direction. As the snowball travels, it grows in size — its collision radius and damage increase with distance traveled. Enemies hit are pushed along with the snowball, adding to its mass. The snowball keeps rolling until it hits a wall or reaches max distance.

## Primitive Composition

P-32 (Actor Spawning) → projectile travel scalars → `ProjectileCarryBlock`

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

This sketch now uses the canonical projectile travel-scalar surface:

1. `spawn_actor.projectile.radius_growth_per_unit`
2. `spawn_actor.projectile.payload_scale_per_unit`
3. optional `spawn_actor.projectile.max_scaled_radius`

The runtime derives current collision radius and payload multiplier from authoritative
`distance_traveled`, so growth survives handoff without bespoke state.

### Entity Accumulation

Unlike `SK-34 Charge`, which uses entity-local `kinematic_sweep.capture_first`, this sketch uses
the canonical projectile-local `carry_policy`.

The projectile owns:

- a bounded ordered carried-target roster
- a front offset (`carry_offset_distance`)
- a perpendicular spacing value (`lateral_spacing`)

Each newly admitted impact appends the target to that roster until `max_carried_targets` is
reached. Carried targets remain ordinary entities in the authoritative R-tree, but while carried
their independent movement, casts, attacks, and item use are suppressed. Their positions are
derived each tick from the snowball's current heading and slot order. On wall impact, expiry, or
projectile removal, all carried entities are released at the snowball's current position in the
same preserved order.

### Growing Collision Radius

The spatial query uses the projectile's CURRENT derived radius, not its spawn radius. As the
snowball grows, later entities can be admitted even if they would have been missed early in flight.
This is already covered by the canonical travel-scalar projectile contract.

## Cross-Boundary Concerns

The snowball uses ordinary projectile handoff plus a bounded carried-target roster.

1. The projectile snapshot transfers travel state plus the ordered carried-target ID list.
2. The carried entities themselves remain ordinary authoritative entities and therefore continue
   through co-located entity handoff, not inside the projectile snapshot.
3. If the projectile handoff commits one tick before a carried entity's co-located handoff
   finishes, that entity follows the projectile shadow/ghost until the receiver owns both again.
4. Static blocking geometry near a boundary follows the ordinary replicated projectile/world-impact
   contract, so authored terrain walls still count as valid snowball stops.

## Compiler Requirements

Designer specifies:

- initial radius and optional radius cap
- growth rate per world unit traveled
- initial damage and payload scaling per world unit traveled
- speed and max lifetime/range
- `max_carried_targets`
- front offset and lateral spacing for carried targets
- wall-impact and expiry consequences

Compiler produces:

- one projectile archetype with canonical travel scalars
- one canonical `ProjectileCarryBlock`
- deterministic projectile-local carried-target roster handling
- ordinary projectile handoff with carried-target ID transfer
- ordinary release behavior on world impact / expiry / removal

## Resolved Notes

- `max_carried_targets` is the performance bound for rolling capture.
- This sketch uses ordinary hostile target admission (`enemy_alive`); allied or neutral capture
  remains a game-data filter choice, not a second carry subsystem.
- Carried entities remain targetable/healable unless other authored effects say otherwise; the carry
  contract suppresses independent action, not targetability.
- Terrain walls and other valid projectile-blocking geometry count as world impact and therefore
  trigger release/detonation normally.
- Projectile interception, redirect, and kinematic dilation follow the same canonical projectile
  rules as other advanced projectile actors. Because growth derives from world distance traveled,
  slower travel in dilated space naturally slows growth per tick without changing the formula.
