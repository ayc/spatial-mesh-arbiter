# SK-113: Hit-Count Shield

## Designer Intent

I gain a shield that blocks the next 6 instances of damage. Each attack that would damage me is completely negated — whether it deals 10 damage or 10,000 damage. After 6 hits are blocked, the shield breaks and I take damage normally.

## Primitive Composition

P-19 (Instance Barrier)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (self-cast)
- No target

## Observable Behavior

1. Activate — gain Hit-Count Shield with 6 charges
2. Each instance of damage: shield absorbs the ENTIRE hit (regardless of damage amount), lose 1 charge
3. Hit 1: blocked (5 charges remain)
4. Hit 2: blocked (4 charges remain)
5. ... Hit 6: blocked (0 charges remain, shield breaks)
6. Hit 7: normal damage (shield gone)
7. Duration: 17 seconds or until all charges consumed
8. Visual: crystalline shield layers, one layer shatters per hit

## Engine Primitives Required

Hit-Count Shield is already the canonical `apply_shield(shield_type = instance)` path.

The recommended lowering is:

1. apply one self shield with:
   - `shield_type = instance`
   - `charges = 6`
   - `duration_ticks = ...`
   - optional lifecycle hooks if the design wants break/expiry effects
2. let the runtime consume one charge for each admitted damage event and negate the entire residual
   hit value for that event
3. let the shield remove itself automatically when charges reach zero or the duration expires

This keeps the mechanic entirely inside the canonical shield surface:

- hit-count shielding is not a second bespoke barrier type outside `apply_shield`
- `P-19` already fixes ordering ahead of absorption barriers (`shield_type = absorption`)
- one charge maps to one damage event, not to raw damage magnitude
- charge depletion and removal are ordinary shield lifecycle behavior

## Cross-Boundary Concerns

Hit-Count Shield is target-owner authoritative.

1. The shield instance lives on the protected entity's current owner.
2. Local and relayed damage events both reach that owner, which alone decides whether a charge is
   consumed and the hit is fully negated.
3. If the protected entity hands off, the remaining-charge count transfers with the shield instance
   as ordinary shield SoftState.
4. No special cross-boundary protocol is needed beyond the ordinary target-owner combat path.

## Compiler Requirements

Designer specifies:

- charge count
- duration
- optional priority and lifecycle effects

Compiler emits:

- one canonical `apply_shield(shield_type = instance, charges = ...)`
- ordinary shield instance state tracking remaining charges
- standard break/expiry removal when charges hit zero or the timer ends

Compiler validates:

1. `shield_type = instance` uses `charges`, not `amount`
2. `charges > 0`
3. the mechanic uses canonical `apply_shield`, not a bespoke "next N hits ignored" interceptor

## Resolved Interaction Notes

- Instance barriers are checked before absorption shields, so a consumed hit-count charge leaves any
  HP-based shield untouched.
- DoT ticks and multi-hit abilities consume one charge per damage event, which is the canonical
  "one hit" definition for `P-19`.
- If an instance barrier consumes a charge and negates the hit, the event does not continue into
  ordinary damage resolution, so later HP-shield absorb hooks do not see that hit.
- Movement-damage ticks are still damage events, so they consume charges one tick at a time while
  the barrier lasts.
- Pure/true-damage amounts are still fully negated by the instance barrier unless the effect uses a
  bypass-marked prevention path such as a `P-24` bypass execute.
