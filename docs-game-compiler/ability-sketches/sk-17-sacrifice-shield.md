# SK-17: Sacrifice Shield

## Designer Intent

I pay a meaningful chunk of my own life to protect an ally. In the canonical profile, the clean
expression is: pay a fixed 20% max-HP self cost up front, then grant the ally a 5-second
absorption shield worth 150% of that authored sacrifice amount.

## Primitive Composition

P-18 (Absorption Barrier) -> P-21 (Value Conversion)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- caster entity
- ally target entity
- caster max HP

## Observable Behavior

1. The cast is legal only if the caster can pay the full authored life cost.
2. On cast, the caster pays a 20% max-HP self cost immediately.
3. The ally gains an absorption shield worth 150% of that authored sacrifice amount.
4. Incoming damage on the ally is absorbed by the shield first.
5. When the shield is depleted, remaining damage carries through to HP normally.
6. The shield expires after 5 seconds if it is not fully consumed.
7. Visual presentation may render a brief self-sacrifice hit on the caster and a golden barrier on
   the ally.

## Engine Primitives Required

Sacrifice Shield is the canonical ally-shield transfer reference using one bounded procedural
formula fallback plus ordinary shield runtime.

The recommended lowering is:

1. require `hp_above(caster, 0.20)` at admission so the caster can pay the full authored cost
2. compute `sacrifice_amount` from the caster's max HP through the bounded deterministic formula
   fallback
3. apply one self-targeted true-damage cost for `sacrifice_amount`
4. apply one ally absorption shield with:
   - `target = ally`
   - `shield_type = absorption`
   - `amount = sacrifice_amount * 1.5`
   - `duration_ticks = 300`

This keeps the mechanic inside existing surfaces:

- the protection itself is an ordinary canonical absorption shield
- the coupled self-cost / shield-amount math stays inside the bounded formula fallback surface
- no bespoke HP-resource system or custom shield actor is introduced

## Cross-Boundary Concerns

Sacrifice Shield splits cleanly across the two already-authoritative owners.

1. The caster's owner computes `sacrifice_amount` from the caster's max HP and applies the self
   cost locally.
2. The same owner then emits the shield grant toward the ally's current owner with the already
   computed shield amount.
3. If the ally is remote/Ghost, the shield begins only when that ordinary target-owner relay
   commits. There is no retroactive mitigation for damage taken before arrival.
4. Once applied, later shield absorption and expiry are fully local to the ally's owner just like
   any other absorption shield.

## Compiler Requirements

Designer specifies:

- self-cost ratio
- shield multiplier
- shield duration
- ally targeting/range
- whether the cast is full-cost-or-reject or allows some other partial-cost variant

Compiler emits:

- one admission guard requiring the caster to satisfy the full life cost
- one bounded formula/fallback to compute `sacrifice_amount` from caster max HP
- one self `apply_damage`
- one target `apply_shield(shield_type = absorption, ...)`

Compiler validates:

1. the self-cost ratio is in `(0, 1)`
2. the shield multiplier is non-negative
3. `duration_ticks > 0`
4. this reference uses the canonical full-cost-or-reject profile rather than a partial-cost/min-1
   variant

## Resolved Interaction Notes

- This reference rejects the cast below the full 20% life cost instead of allowing a reduced
  partial-cost version at 1 HP.
- The self-cost is ordinary self-targeted true damage in the current profile. It is not a special
  execute/bypass kill path.
- Because the self-cost is ordinary damage, existing self-protection layers interact with it
  according to the normal combat rules unless the game later adds a stricter HP-cost contract.
- The shield amount is based on the authored sacrifice amount, not on later shield consumption or
  expiry state.
- Shield stacking, priority, redirect interaction, and overflow behavior are all the ordinary
  canonical absorption-shield rules.
