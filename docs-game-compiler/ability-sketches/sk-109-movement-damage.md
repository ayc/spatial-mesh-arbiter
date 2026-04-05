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

Movement Damage is now a canonical status-owned `movement_damage` reference.

The recommended lowering is:

1. apply one negative status to the target with:
   - `movement_damage = {`
     `damage_per_unit = ...`
     `damage_type = ...`
     `max_damage_per_tick = ...` (if the design wants a teleport/burst cap)
     `}`
   - `duration_scaling = fixed` or `status_resistance`, depending on the design
   - `is_cleansable = true`
2. let the runtime evaluate displacement after all movement for the tick is committed
3. let the resulting amount enter ordinary combat resolution rather than inventing a bespoke
   post-movement true-damage path

This keeps the mechanic inside the canonical compiler surface:

- the status tracks absolute world position delta, not path length
- voluntary movement, forced displacement, and teleports all contribute because the check runs after
  committed movement for the tick
- armor, shields, anti-heal bypass rules, block, and other ordinary downstream combat rules depend
  on the authored `damage_type`; the movement scalar itself is not a separate mitigation system
- optional burst capping is the canonical `max_damage_per_tick`, not a special teleport exception

## Cross-Boundary Concerns

Movement Damage is entirely target-owner authoritative.

1. The negative status lives on the target's current owner and stores the previous absolute world
   position in ordinary status runtime state.
2. If the target hands off, that previous position transfers with the status as ordinary SoftState.
3. Cross-boundary teleports and long displacements still work because the canonical contract uses
   absolute world coordinates, not owner-local cell coordinates.
4. Ghosts do not predict or apply movement-damage hits. Only the target owner computes displacement
   and emits the resulting damage event.

## Compiler Requirements

Designer specifies:

- duration
- damage per unit of displacement
- damage type
- optional per-tick cap
- whether the debuff is cleansable / status-resistance-scaled

Compiler emits:

- one negative status carrying the canonical `movement_damage`
- runtime state that stores the previous absolute world position for the status carrier
- one ordinary per-tick hostile damage emission whose amount is derived from committed displacement

Compiler validates:

1. `damage_per_unit > 0`
2. `max_damage_per_tick`, if authored, is non-negative
3. the mechanic uses canonical `movement_damage`, not a bespoke movement hook or path-integration
   script

## Resolved Interaction Notes

- The scalar uses tick-boundary 2D displacement only. Arc height / vertical presentation does not
  contribute.
- Forced movement, teleports, drags, fears, charms, and other committed relocation effects all
  trigger the damage because the status only cares that the entity's final committed position
  changed.
- If the target stands still, the emitted amount is zero and no damage instance is produced.
- The resulting damage uses the authored `damage_type`, so ordinary mitigation/shield rules still
  apply. This reference does not force pure damage.
- Stasis or other states that prevent movement naturally suppress the damage by producing zero
  displacement; they do not need a second special-case movement-damage rule.
- Burrow/invulnerability style effects can still negate the resulting hit through their ordinary
  defensive admission/mitigation rules if they overlap.
- Kinematic Dilation lowers committed displacement per tick, so it also lowers movement-damage
  intake per tick under the canonical movement model.
