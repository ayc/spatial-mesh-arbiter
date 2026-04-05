# SK-47: Shield Burst

## Designer Intent

I activate an ability that grants me a massive shield. When the shield expires naturally or is fully consumed by damage, it explodes — dealing AoE damage to nearby enemies proportional to how much shield was REMAINING when it broke. A shield that expires at full value deals maximum damage. A shield that was chipped down deals less.

## Primitive Composition

P-18 (Absorption Barrier) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — gain a large shield (e.g., 800 HP)
2. Shield absorbs incoming damage normally (same as SK-17)
3. If shield expires (3 seconds) with remaining value: explosion deals damage = remaining_shield * 1.0
4. If shield is fully consumed by damage before expiry: explosion deals 0 damage (nothing remained)
5. If shield is partially consumed: explosion deals proportional damage (e.g., 400 remaining = 400 damage explosion)
6. Explosion hits all enemies within blast radius
7. Visual: golden shield grows brighter as it nears expiry, detonates in a nova

## Engine Primitives Required

Shield Burst is now a canonical shield-lifecycle callback reference.

The recommended lowering is:

1. apply one self absorption shield with:
   - `amount = ...`
   - `duration_ticks = 180`
   - `bind_remaining_value_as = remaining_shield`
   - `on_expire_effects = [aoe_damage(center = caster_position, shape = circle, radius = ... , filter = enemy_alive, amount = 0, scaling = { binding = remaining_shield, coefficient = 1.0 })]`
   - `on_break_effects = [aoe_damage(center = caster_position, shape = circle, radius = ... , filter = enemy_alive, amount = 0, scaling = { binding = remaining_shield, coefficient = 1.0 })]`

Because `bind_remaining_value_as` snapshots the shield value immediately before removal:

- natural expiry sees the real remaining shield value
- break-by-damage sees `0`
- partial consumption produces proportionally smaller burst damage

This keeps the mechanic inside the canonical shield lifecycle surface. No bespoke shield event
subsystem is needed.

## Cross-Boundary Concerns

Shield Burst stays on the shield owner's current Arbiter.

1. Shield absorption, remaining-value snapshots, and lifecycle callbacks all resolve on the shielded
   entity's current owner.
2. If cross-boundary damage depletes the shield, that depletion still resolves locally on the
   shield owner, which immediately records `remaining_shield = 0` for the break callback.
3. The explosion is just a local AoE query from the shield owner's position. Remote/Ghost enemies in
   the radius are handled through the same local-query / target-owner damage relay path used by
   other AoE effects.

## Compiler Requirements

Designer specifies:

- shield amount and duration
- burst radius
- damage coefficient from remaining shield value
- whether break and expiry use the same payload or different payloads

Compiler emits:

- one absorption shield
- one lifecycle binding for `remaining_shield`
- one expiry AoE payload
- one break AoE payload

Compiler validates:

1. the shield is an absorption shield
2. `duration_ticks > 0`
3. lifecycle damage scaling reads only the bound remaining shield value
4. any difference between break and expiry is expressed through separate authored callback payloads,
   not through a bespoke shield-burst primitive

## Resolved Interaction Notes

- In this reference, the burst damage is driven only by `remaining_shield * coefficient`. It is not
  separately multiplied by weapon damage or other offensive formulas unless the designer layers
  those in elsewhere.
- Purging/removing the shield before natural expiry prevents the expiry burst. Only natural expiry
  or damage depletion fire the authored lifecycle hooks in this reference.
- Damage redirected onto the shielded entity consumes the shield normally and therefore reduces the
  later burst, because the remaining-value snapshot reads the shield's actual final state.
- Multiple shield instances may coexist if the broader design allows them, and each shield fires its
  own lifecycle callback using its own snapped remaining value.
- The burst is ordinary AoE damage after the reactive callback re-enters on the next tick, so later
  proc consumers can see it the same way they see other AoE damage events.
