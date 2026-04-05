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

Wall Bounce is now a canonical projectile `bounce_policy` reference.

The recommended lowering is:

1. author one ordinary hostile projectile with:
   - `detonation_policy = { entity_impact = detonate, world_impact = bounce, expiry = despawn }`
   - `bounce_policy = { max_bounces = 3, preserve_speed = true }`
2. let entity impact still consume the projectile immediately
3. let world impact reflect the heading and continue until the projectile either:
   - hits an entity
   - spends its remaining travel distance for the tick
   - reaches `max_bounces`

This keeps the mechanic inside the canonical projectile surface:

- wall reflection is not a bespoke projectile class
- multi-segment same-tick reflection is already part of the bounce contract
- reflected heading and bounce count are ordinary projectile SoftState

## Cross-Boundary Concerns

Wall Bounce follows the canonical projectile-owner model.

1. Reflection is resolved on the projectile's current owner using the same swept-segment query that
   already returns world-hit normals for bounce math.
2. If a bounce redirects the projectile into a neighboring region, ordinary projectile handoff
   applies.
3. Bounce count and reflected heading survive handoff as part of the projectile's authoritative
   SoftState.
4. Injected geometry such as player-made walls participates through the same world-impact query
   surface as static geometry.

## Compiler Requirements

Designer specifies:

- projectile speed
- max bounces
- whether speed is preserved after bounce
- entity-hit damage and consume-on-hit behavior

Compiler emits:

- one projectile with canonical `bounce_policy`
- `detonation_policy.world_impact = bounce`

Compiler validates:

1. `max_bounces > 0`
2. `bounce_policy` is only used when world impact is `bounce`
3. entity impact remains ordinary projectile admission / detonation, not a second bounce channel

## Resolved Interaction Notes

- This reference preserves speed across bounces because `preserve_speed = true`.
- Each reflected segment still checks entity impact independently inside the same tick's multi-
  segment travel budget.
- Player-authored walls and other injected blocking geometry are eligible bounce surfaces through
  the same canonical world-impact query.
- There is no random spread in this reference. Reflection uses the deterministic surface normal from
  the raycast result.
- Friendly fire still follows the projectile's authored target filter. Bouncing does not widen the
  admitted relation filter on its own.
