# SK-109: Movement Damage

## Designer Intent

I curse an enemy. For 12 seconds, every unit of distance they travel deals damage to them. If they stand perfectly still, they take zero damage. If they run, they bleed. This forces a terrible choice: move and take massive damage, or stand still and be helpless.

## Primitive Composition

P-63 (Movement-Damage Scalar)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. Cast on enemy — Rupture debuff applied for 12 seconds
2. Every tick: calculate how far the target moved since last tick
3. Target takes damage = distance_moved × damage_per_unit
4. Standing still = 0 distance = 0 damage
5. Walking = moderate damage per tick
6. Dashing/blinking = massive burst damage (large distance in one tick)
7. Forced movement (SK-78 Fear, SK-101 Charm, SK-43 Drag) ALSO triggers the damage
8. Only VOLUNTARY movement can be avoided — forced displacement still hurts
9. Visual: blood trail behind the moving target, intensifying with speed

## Engine Primitives Required

### Per-Tick Displacement Tracking

Each tick, the Arbiter must calculate the target's displacement:

```
struct MovementDamageDebuff {
    damage_per_unit: SimFixed,
    previous_position: Vec2F,
    expires_at_tick: u64,
}

// Each tick:
fn evaluate_movement_damage(entity: &Entity, debuff: &mut MovementDamageDebuff) -> SimFixed {
    let displacement = distance(entity.position, debuff.previous_position);
    debuff.previous_position = entity.position;
    displacement * debuff.damage_per_unit
}
```

The damage is proportional to DISPLACEMENT (straight-line distance between previous and current position), not DISTANCE TRAVELED (path length). A teleport of 10 units deals the same as walking 10 units.

### Displacement Includes ALL Movement Types

The damage triggers on any position change:
- Voluntary movement (WASD/click): yes
- Forced movement (SK-78 Fear flee): yes
- Displacement (SK-01 Toss): yes
- Teleport (SK-35 Blink Strike): yes — massive burst (large displacement in one tick)
- SK-43 Drag (pulled toward caster): yes
- SK-31 Vortex (pulled toward center): yes

The ONLY way to avoid damage is to not change position. The debuff doesn't care WHY the entity moved — only that it did.

### Damage Resolution Per Tick

The movement damage is calculated AFTER all movement for the tick is resolved (after `apply_kinematics` and any forced movement):
1. All movement sources apply (voluntary, forced, displacement)
2. Final position is determined
3. Displacement = distance(final_position, previous_position)
4. Damage = displacement × damage_per_unit
5. Apply damage through standard resolution (can be mitigated by armor, shields, etc.)

### Interaction With Instant Movement

Teleports (SK-35 Blink Strike, SK-36 Shadow Step return, SK-69 Portal) create large displacements in a single tick. The damage is proportional to the straight-line distance of the teleport. This can be MASSIVE — a global teleport could deal thousands of damage.

Design choice: should there be a per-tick displacement cap for damage calculation (preventing one-shot from teleport)?

## Cross-Boundary Concerns

TODO: The debuff tracks the entity's position each tick. This is entirely local to the entity's Arbiter. When the entity moves normally, displacement is calculated locally.

Concern: if the entity crosses an Arbiter boundary (handoff), the `previous_position` in the debuff was on the old Arbiter's coordinate system. After handoff, the entity is on a new Arbiter with the same world coordinates. The displacement calculation uses absolute coordinates, so it works correctly across handoffs.

If the entity teleports cross-boundary (SK-35 Blink Strike to another Arbiter), the handoff occurs, and the new Arbiter calculates displacement from the previous_position (on the old Arbiter) to the current position. The large displacement = large damage.

## Compiler Requirements

TODO: Designer specifies: target debuff, duration (12s), damage per unit of distance moved, applies to all movement types, standing still = no damage. Compiler produces:
- MovementDamageDebuff status effect with previous_position tracking
- Per-tick displacement calculation (after all movement resolution)
- Damage = displacement × damage_per_unit
- Standard damage resolution for the calculated amount

The compiler needs to support **displacement-based damage triggers** — effects where the damage amount is a function of the entity's spatial movement.

## Open Questions

- Is the damage per-unit-distance mitigable by armor/shields, or is it pure/true damage?
- Does the damage trigger on sub-tick movement (interpolation) or only on the tick-boundary position delta?
- Should teleport displacement be capped to prevent one-shot (e.g., max 1000 damage per tick)?
- Does SK-91 Stasis pause the debuff timer (entity can't move during stasis anyway)?
- Does SK-44 Burrow prevent movement damage (entity can't move, but they also have invulnerability)?
- If the entity is displaced by SK-01 Toss (forced movement by an ally trying to save them), does the debuff still damage?
- Does the displacement include vertical movement (SK-01 Toss arc)?
- Can the debuff be cleansed by SK-15 Purify?
- Does SK-51 Unstoppable prevent the debuff application (it's not CC — it's a damage debuff)?
- How does the debuff interact with Kinematic Dilation (dilated entity moves slower = less displacement per tick = less damage)?
