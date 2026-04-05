# SK-02: Poison Shot

## Designer Intent

My character performs a ranged attack, shooting poison at the target. The target gets a poison debuff — a DoT lasting 5 seconds. Any successive damage I deal to the target refreshes the DoT duration back to 5 seconds. Each DoT tick heals me for a portion of the damage dealt, and applies a stacking buff to me that increases my damage by 1% per stack.

## Primitive Composition

P-32 (Actor Spawning) → P-35 (On-Hit Hook) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target entity (must be in range)

## Observable Behavior

1. Projectile launches toward target
2. On hit: apply initial damage + apply Poison debuff (DoT, 5s duration)
3. Poison ticks every 1s for 5 pulses, dealing poison damage each tick
4. Later qualifying damaging hits from the same build refresh Poison back to the full 5-second
   window
5. Each DoT tick heals the caster for a portion of the actual damage dealt
6. Each DoT tick grants the caster one stack of a separate damage-up buff

## Engine Primitives Required

Poison Shot is a canonical projectile-on-hit negative-status reference with a bounded refresh
helper.

The recommended lowering is:

1. spawn one hostile first-hit projectile shell
2. on the first admitted hit:
   - apply the initial direct damage payload
   - apply one negative `poison_shot_dot` status to the struck target for 100 ticks
3. `poison_shot_dot` authors:
   - `periodic_effects = { interval_ticks = 20, max_ticks = 5, effects = [...] }`
   - one periodic poison `damage` effect on the target
   - one periodic `value_conversion(source_type = damage_dealt, target_type = healing, target = caster, ratio = ...)`
   - one periodic `apply_buff(target = caster, status_id = venom_fervor, duration_ticks = ..., stacks = 1)`
4. later qualifying damaging abilities in the same kit MAY carry one bounded refresh helper using
   the canonical Lua fallback:

```lua
if has_status(target, "poison_shot_dot") then
  apply_status(target, "poison_shot_dot", 100, 1)
end
```

This keeps the mechanic inside existing surfaces:

- the projectile is an ordinary hostile spawned actor
- the poison itself is one ordinary negative status with `periodic_effects`
- the drain heal uses canonical `value_conversion(damage_dealt -> healing)`
- the caster buff stacks are ordinary positive-status applications on the source
- refresh uses the bounded Lua fallback surface instead of inventing a global "refresh my DoTs on
  any damage" primitive

## Cross-Boundary Concerns

Poison Shot follows the canonical target-owner status model.

1. Initial projectile hit admission and Poison status application occur on the struck target's
   CURRENT owner.
2. While Poison is active, periodic ticks also execute on that target owner because the debuff lives
   in that owner's authoritative status registry.
3. The periodic damage stays local to the target owner. The paired drain heal and caster buff stack
   route to the caster's CURRENT owner if the caster is remote.
4. Later qualifying damage hits refresh Poison where those hits already resolve: on the target's
   current owner after authoritative hit admission.
5. If the target hands off mid-Poison, the status, remaining timer, and later refreshability all
   transfer as ordinary SoftState.

## Compiler Requirements

Designer specifies:

- projectile speed / range / impact presentation
- initial hit damage
- poison duration, pulse cadence, and per-tick poison damage
- drain ratio
- the buff status used for the caster's +1% per-stack damage gain
- buff duration / max stacks
- which later damaging abilities opt into the refresh helper

Compiler emits:

- one hostile projectile spawn / first-hit impact payload
- one negative `poison_shot_dot` status with `periodic_effects`
- one periodic `value_conversion(damage_dealt -> healing)` toward the caster
- one periodic positive buff application to the caster
- one bounded refresh helper on any later damaging abilities the designer marks as Poison refreshers

Compiler validates:

1. the Poison status is authored as an ordinary negative status, not as a bespoke projectile-owned
   timer
2. periodic drain uses canonical `value_conversion`, not hidden lifesteal math
3. the refresh helper stays inside the bounded `has_status` + `apply_status` fallback surface
4. the damage-up buff has an authored duration and stack cap instead of relying on unbounded
   implicit growth

## Resolved Interaction Notes

- This reference refreshes from later qualifying damaging ability hits authored with the helper. The
  Poison status's own periodic ticks do NOT self-refresh.
- Poison is cleansable like an ordinary negative status unless the designer explicitly marks it
  otherwise. Cleansing Poison stops future ticks immediately.
- Buff stacks already granted to the caster remain because they are separate positive statuses on
  the caster, not children of the target's debuff.
- Drain healing clamps at the caster's current max HP. Excess healing is lost.
- If the caster dies or is removed, the remaining Poison ticks still damage the target, but heal and
  buff follow-ups targeting the missing caster fail cleanly.
- This reference keeps one active Poison instance per target for this ability family. Reapplication
  refreshes/replaces that instance instead of keeping parallel independent Poison Shot stacks alive.
