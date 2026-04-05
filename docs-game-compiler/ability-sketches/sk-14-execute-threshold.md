# SK-14: Execute Threshold

## Designer Intent

My attacks against enemies already below 25% HP deal 200% bonus damage. If that empowered hit
kills the target, the ability's cooldown is instantly reset.

## Primitive Composition

P-17 (Conditional Thresholds)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- hostile target
- target's current HP percentage
- base damage payload for the ability
- cooldown ID for the originating ability

## Observable Behavior

1. I use the ability on an enemy.
2. The target's CURRENT HP percentage is checked before this hit's damage is applied.
3. If the target is already below 25% HP, the hit deals triple total damage.
4. If the target is not already below 25% HP, the hit deals only its normal base damage.
5. If the empowered hit gets kill credit, the same ability's cooldown is reset to 0.
6. Visual presentation may show a low-HP execute indicator plus a stronger hit effect on the
   empowered branch.

## Engine Primitives Required

Execute Threshold is the canonical low-HP conditional-damage reference.

The recommended lowering is:

1. keep one ordinary targeted hostile damage ability
2. branch its damage coefficient through the canonical target-state threshold guard:
   - normal branch: base damage
   - low-HP branch: base damage with total coefficient `3.0`
3. attach one kill-follow-up tied to the empowered branch that sets the originating ability's
   cooldown to `0`

In the current compiler profile, the clean expression is:

- a guarded low-HP damage branch using `hp_below(target, 0.25)`
- plus the bounded `set_cooldown` fallback for the kill-reset side effect

This keeps the mechanic inside existing surfaces:

- the threshold is an ordinary canonical `P-17` HP-percentage check
- the empowered hit is still ordinary damage, not a special execute kill
- cooldown reset is a bounded follow-up mutation rather than a second hidden ability identity

## Cross-Boundary Concerns

Execute Threshold follows the canonical target-owner threshold rule.

1. The origin owner may use Ghost HP only for UI/admission preview.
2. The authoritative low-HP check is recomputed on the target owner at resolution time.
3. If Ghost HP was stale, the target owner simply chooses the correct branch there: empowered or
   normal.
4. Because the empowered hit is still ordinary damage, later mitigation, shields, and death checks
   remain target-owner authoritative as usual.
5. The cooldown reset is emitted only when the empowered branch gets the terminal kill attribution.

## Compiler Requirements

Designer specifies:

- low-HP threshold
- normal damage payload
- empowered damage coefficient
- which ability cooldown is reset on empowered kill

Compiler emits:

- one hostile damage ability
- one target-state threshold guard using `hp_below(target, 0.25)`
- one normal-damage branch
- one empowered-damage branch
- one kill-follow-up cooldown reset using bounded `set_cooldown`

Compiler validates:

1. the threshold is based on the target's HP BEFORE this hit is applied
2. the empowered branch still uses ordinary damage resolution, not `execute`
3. the cooldown reset is tied to empowered-kill attribution, not any unrelated kill by the caster
4. target-side threshold authority is preserved for remote/Ghost targets

## Resolved Interaction Notes

- A target at 26% HP that would fall to 24% from the base hit does NOT get the empowered branch on
  that same hit. The branch checks pre-hit current HP only.
- The empowered hit may still crit, but crit is applied to the empowered damage branch the same way
  it would be applied to any other ordinary damage packet.
- Because this is not `execute`, shields, floor-clamps, death prevention, and other protective
  mechanics still work normally.
- The cooldown reset is ability-local in this reference: the killing empowered hit resets the same
  ability that produced it.
- DoT ticks or other later damage sources do not inherit this threshold bonus unless the designer
  explicitly attaches the same low-HP branch to those damage sources too.
