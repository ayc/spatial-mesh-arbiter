# SK-27: Sleep

## Designer Intent

I put an enemy to sleep for 5 seconds. They cannot act at all, like a stun, but the sleep breaks
instantly if the sleeping entity takes damage. This creates tactical tension: the CC is powerful
but fragile.

## Primitive Composition

P-26 (Capability Bitmask) → P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. The ability lands and applies sleep for 5 seconds.
2. While asleep, the target cannot move, attack, or cast.
3. Active casts and channels are interrupted immediately on admission.
4. Any non-zero committed damage instance breaks the sleep immediately.
5. The hit that breaks sleep still resolves normally; sleep does not absorb that damage.
6. Duration is reduced by the target's `status_effect_resistance`.
7. Diminishing returns follow the shared hard-disable DR policy.
8. When the sleep expires or breaks, the authored follow-up CC-immunity window applies.
9. Purify-style cleanse removes the sleep early.
10. Visual: sleeping/zzz presentation on the disabled target.

## Engine Primitives Required

Sleep is authored through canonical `apply_cc`; its break-on-damage rule is part of the built-in
sleep profile rather than a bespoke sketch-local callback.

The runtime contract is:

1. the ability emits `apply_cc { cc_type = sleep, category = hard_disable, duration_ticks = 300,
   dr_category = hard_disable }`
2. `apply_cc` lowers to a generated negative status carrying:
   - `cc_behavior_profile = sleep`
   - `cc_category = hard_disable`
   - `duration_scaling = status_resistance`
   - ordinary status metadata such as `is_cleansable`
3. if admitted, that generated status suppresses `CAN_MOVE`, `CAN_ATTACK`, and `CAN_CAST`
4. the sleep behavior profile interrupts active casts/channels on admission and breaks after any
   non-zero committed damage instance
5. an authored `on_expire_effects` follow-up may grant the brief post-sleep hard-disable immunity
   window

This keeps the mechanic inside existing canonical surfaces:

- the full-disable behavior is the built-in sleep profile
- the break condition is profile-defined and does not need a bespoke extra trigger
- the post-sleep immunity window is just an ordinary positive follow-up status

## Cross-Boundary Concerns

Sleep uses the ordinary target-owner CC path, and the break check is also target-owner local.

1. Remote/Ghost targets receive the `apply_cc` payload on their authoritative owner.
2. That same owner evaluates later break conditions when any local or relayed damage arrives on the
   sleeping entity.
3. If a qualifying hit deals non-zero committed damage, the target owner removes the sleep status
   before later same-stage timer firings; the hit that broke sleep still resolves normally.
4. If the target hands off while asleep, the active status transfers as ordinary SoftState and the
   new owner continues evaluating later break checks.

## Compiler Requirements

Designer specifies:

- hostile target filter and range
- `cc_type = sleep`
- sleep duration
- whether the effect is cleansable
- the DR category for the effect
- any follow-up post-sleep immunity status

Compiler emits:

- one canonical `apply_cc` payload with `cc_type = sleep`
- one generated negative status entry using the canonical sleep behavior profile
- target-side `duration_scaling = status_resistance` and the authored `dr_category`
- any optional positive follow-up immunity status on break/expiry

Compiler validates:

1. `cc_type = sleep` pairs only with canonical `category = hard_disable`
2. `duration_ticks > 0`
3. the authored `dr_category` is a supported DR domain
4. sleep uses the canonical built-in break-on-damage profile rather than inventing a second custom
   damage-intercept path

## Resolved Interaction Notes

- Only non-zero committed damage breaks sleep in this reference. Fully blocked hits or zero-damage
  branches do not break it.
- Shield-absorbed hits break sleep only if some non-zero committed damage still gets through to the
  sleeping target's branch. Full negation does not break it.
- DoT ticks break sleep if the tick deals non-zero damage, because the sleep profile keys from any
  committed damage instance.
- The hit that breaks sleep may still drive later non-sleep consequences of that same hit. Sleep
  does not retroactively cancel the damage source that woke the target.
- Root, silence, and stun interactions are just ordinary CC composition/admission rules. Sleep does
  not need a bespoke queueing system beyond the shared target-side CC registry and DR policy.
