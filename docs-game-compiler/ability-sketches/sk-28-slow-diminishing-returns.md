# SK-28: Slow + Diminishing Returns

## Designer Intent

I apply a 50% movement speed reduction to an enemy for 3 seconds. Repeated slows should become less
oppressive so the game does not devolve into permanent near-immobilization.

## Primitive Composition

P-16 (Stat Layering) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. The slow applies a 50% movement-speed reduction for 3 seconds.
2. The target can still attack and cast; only movement speed is reduced.
3. Duration is reduced by the target's `status_effect_resistance`.
4. Reapplying slow effects follows the game's ordinary status refresh/stack rules rather than a
   bespoke per-slow geometric reduction formula.
5. Slow remains a soft-disable effect for cleanse/immunity interactions.
6. Visual: frost / sluggish FX whose intensity matches the authored slow.

## Engine Primitives Required

The canonical closure for this sketch is an ordinary negative slow status, not a special second DR
subsystem for repeated slow strength halving.

The recommended lowering is:

1. define one negative status with:
   - `polarity = negative`
   - `duration_ticks = 180`
   - `cc_category = soft_disable`
   - `duration_scaling = status_resistance`
   - `stat_modifiers = [`
     `{ stat_id = movement_speed, operation = add_percent, value = -0.50 }`
     `]`
2. apply that status through `apply_debuff`

This keeps the mechanic inside existing canonical surfaces:

- movement reduction is ordinary P-16 stat layering
- tenacity is the standard `duration_scaling = status_resistance` path
- cleanse/immunity uses the same `soft_disable` category as other movement-suppression effects

## Cross-Boundary Concerns

Slow follows the normal target-owner debuff path.

1. Remote/Ghost targets receive the debuff application on their authoritative owner.
2. The target owner inserts the negative status, applies duration scaling, and computes effective
   movement speed locally from ordinary stat layering.
3. If the target hands off while slowed, the active status transfers as ordinary SoftState.
4. No attacker-side DR bookkeeping is required for this canonical slow reference.

## Compiler Requirements

Designer specifies:

- hostile target filter and range
- slow duration
- movement-speed reduction amount
- whether the slow is cleansable

Compiler emits:

- one negative `StatusEffectDefinition` using `cc_category = soft_disable`
- one `apply_debuff` payload applying that status to the target

Compiler validates:

1. the status uses a negative `movement_speed` modifier
2. the status is `negative`
3. `duration_ticks > 0`
4. the sketch stays inside ordinary slow/status-resistance behavior instead of inventing a separate
   exponential slow-strength DR subsystem

## Resolved Interaction Notes

- This reference narrows "diminishing returns" to the already-canonical soft-disable status path:
  ordinary refresh/stack policy, cleanse/immunity behavior, and tenacity-based duration reduction.
- Root remains a separate mechanic. A slow does not become a root just by stacking harder.
- If the game wants hard geometric reapplication decay or a dedicated slow-only DR tracker, that is
  a future design extension, not part of the current canonical compiler surface.
- Movement-speed floors remain a broader game-balance policy layered on top of the ordinary derived
  movement-speed stat, not a sketch-local rule.
