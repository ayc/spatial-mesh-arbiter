# SK-79: Charge-Up Shot

## Designer Intent

I hold down the ability button to charge my bow. The longer I hold, the more damage and range the shot has. When I release, the arrow fires. Minimum charge fires a weak short-range shot. Maximum charge (after 2 seconds) fires a powerful long-range shot. I can move slowly while charging.

## Primitive Composition

P-43 (Charge-Up State) → P-32 (Actor Spawning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Button HOLD duration (continuous input, not discrete press)
- Release timing (player-controlled)
- Aim direction (requested aim direction at release time)

## Observable Behavior

1. Press and hold ability button — charging begins
2. Charge bar fills over 2 seconds
3. While charging: caster moves at 50% speed, cannot use other abilities
4. At any point: release to fire at current charge level
5. Minimum charge (instant release): low damage, short range
6. Maximum charge (2 seconds): high damage, long range
7. Charge level scales linearly: damage and range interpolate between min and max
8. If held beyond max charge: stays at max, doesn't overcharge
9. Visual: bow draw animation intensifies, glowing effect increases with charge

## Engine Primitives Required

Charge-Up Shot is now a canonical `input_mode = hold_release` reference.

The recommended lowering is:

1. author the public ability with:
   - `input_mode = {`
     `type = hold_release,`
     `min_charge_ticks = 0,`
     `max_charge_ticks = 120,`
     `move_speed_multiplier_while_holding = 0.5,`
     `blocks_other_abilities = true,`
     `retains_max_charge_until_release = true`
     `}`
2. let release fire one ordinary projectile using the authoritative held duration clamped into
   `[min_charge_ticks, max_charge_ticks]`
3. scale projectile damage / range from that authoritative charge duration through ordinary fixed-
   point authored formulas

This keeps the mechanic inside the canonical input-mode surface:

- charge start still begins from the ordinary discrete cast intent
- release is derived from the continuous held-button state, not a new external intent type
- the owner stamps the authoritative hold start tick and clamps the final duration
- movement slowdown and ability lockout are already part of the compiled hold-release contract

## Cross-Boundary Concerns

Charge-Up Shot is caster-owner authoritative.

1. The owner records the authoritative hold start tick and current hold state.
2. If the caster hands off mid-charge, that hold state transfers as ordinary SoftState and the new
   owner continues the same charge window.
3. On release, the projectile is just an ordinary spawned hostile shot. Any later cross-boundary
   target resolution is the normal projectile story, not a special charge-up relay.
4. Edge prediction may animate the charge bar locally, but the final damage/range always derive
   from the authoritative held duration on the current owner.

## Compiler Requirements

Designer specifies:

- min / max charge ticks
- movement speed while holding
- whether other abilities are blocked while holding
- min / max damage
- min / max range

Compiler emits:

- one public ability using canonical `input_mode = hold_release`
- one projectile payload whose damage / range scale from authoritative charge duration

Compiler validates:

1. `max_charge_ticks > 0`
2. `min_charge_ticks <= max_charge_ticks`
3. the charge behavior is authored through canonical `hold_release`, not through a separate
   "start charging" / "release shot" public ability pair
4. all scaling remains deterministic fixed-point math

## Resolved Interaction Notes

- Holding beyond max charge does not overcharge in this reference; the held duration clamps at the
  authored maximum and remains there until release.
- CC that cancels the cast window ends the held state and no projectile fires.
- The latest accepted aim state at release time determines the final shot direction.
- Kinematic Dilation does not change the authored charge window itself. The hold duration is measured
  in simulation ticks, just like other time-based ability windows.
- Replay or echo mechanics that repeat the final shot use the already-resolved release payload; they
  do not reopen the hold window.
