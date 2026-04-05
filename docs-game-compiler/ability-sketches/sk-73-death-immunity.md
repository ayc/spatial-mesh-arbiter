# SK-73: Death Immunity

## Designer Intent

I activate this ability and for 4 seconds, I CANNOT DIE. I take full damage from everything — hits land, procs fire, HP decreases — but my HP cannot go below 1. When the duration expires, if I'm at 1 HP, I'm in extreme danger and can be killed by anything.

## Primitive Composition

P-23 (Floor Clamping) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — gain Death Immunity for 4 seconds
2. All incoming damage is applied normally (not reduced, not absorbed)
3. On-hit procs trigger normally (SK-09 Chain Lightning, SK-22 Reflection, etc.)
4. HP can decrease all the way to 1, but NEVER to 0
5. If incoming damage would reduce HP below 1: HP is set to 1 instead
6. Healing still works normally (can recover above 1 during the window)
7. When the duration expires: you're at whatever HP you have (potentially 1)
8. No special effect on expiry — you're just vulnerable again
9. Visual: fiery rage aura, HP bar flashes at low HP, "UNKILLABLE" indicator

## Engine Primitives Required

Death Immunity is now a canonical `hp_floor` reference.

The recommended lowering is:

1. apply one positive `death_immunity` status to the caster for 240 ticks
2. that status authors:
   - `hp_floor = { min_hp = 1 }`
   - optional presentation-only visuals / UI state
3. do NOT pair the status with `death_prevention`; this sketch is the sustained floor window, not the
   one-shot lethal intercept pattern

This keeps the mechanic entirely inside the canonical `P-23` floor-clamp contract:

- incoming damage is still resolved through the ordinary pipeline
- the entity remains targetable and CC-able
- Stage 10 clamps final HP to `1` while the status is active
- no death event is emitted unless the floor is gone and a later lethal event commits terminal death

## Cross-Boundary Concerns

Death Immunity is target-owner authoritative.

1. Incoming damage, including cross-boundary prepared-hit relays, still resolves on the defended
   entity's current owner.
2. The same owner applies the generated `hp_floor` status and therefore decides whether HP is
   clamped to `1` instead of committing terminal death.
3. Because `PlayerDied` is emitted only if terminal death actually commits, attacker-side kill
   consumers simply do not fire while the floor is active. No extra relay path is needed beyond the
   ordinary hostile-hit contract.
4. If the defended entity hands off while the window is active, the status transfers as ordinary
   SoftState and the new owner continues the same Stage 10 floor check.

## Compiler Requirements

Designer specifies:

- self-cast duration
- minimum HP floor
- whether the positive status is cleansable/purgeable

Compiler emits:

- one positive status
- one canonical `hp_floor` block on that status
- no `death_prevention` block and no expiry payload

Compiler validates:

1. `min_hp > 0`
2. this sketch's reference version uses `min_hp = 1`
3. the behavior is authored through `hp_floor`, not through invulnerability or a one-shot
   death-prevention rewrite
4. any purge interaction is expressed through ordinary status cleansability, not through a bespoke
   "turn off death immunity" hook

## Resolved Interaction Notes

- This reference still takes full incoming damage through the ordinary mitigation / shield path. The
  special rule is only the final minimum-HP clamp.
- Execute-style threshold checks may still qualify for bonus damage, but a non-bypassing execute
  does not kill through the active floor.
- If the beneficial status is purged early and the entity is still at lethal HP, the next lethal
  damage event kills normally; purge does not retroactively emit a death for already-resolved hits.
- Death Immunity may coexist with other defensive layers such as shields. Those layers resolve in
  their ordinary order before the Stage 10 floor check.
- Kinematic Dilation does not alter the authored 240-tick window. The status lasts for 240
  simulation ticks unless some other canonical timer-pause state says otherwise.
