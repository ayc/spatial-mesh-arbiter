# SK-26: Silence

## Designer Intent

I silence an enemy for 4 seconds. They cannot cast any abilities, but they can move and
auto-attack. Active channels are interrupted immediately. Passive abilities continue to function.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. The ability lands and applies silence for 4 seconds.
2. While silenced, the target cannot cast abilities.
3. Movement remains available.
4. Auto-attacks remain available.
5. Active casts and active channels are interrupted immediately on admission.
6. Passive effects continue to function because silence does not clear `PASSIVES_ACTIVE`.
7. Duration is reduced by the target's `status_effect_resistance`.
8. Diminishing returns follow the shared soft-disable DR policy.
9. Purify-style cleanse removes the silence early.
10. Visual: muzzle/gag effect and a clear silenced-state indicator.

## Engine Primitives Required

Silence is authored through canonical `apply_cc`.

The runtime contract is:

1. the ability emits `apply_cc { cc_type = silence, category = soft_disable, duration_ticks = 240,
   dr_category = soft_disable }`
2. `apply_cc` lowers to a generated negative status carrying:
   - `cc_behavior_profile = silence`
   - `cc_category = soft_disable`
   - `duration_scaling = status_resistance`
   - ordinary status metadata such as `is_cleansable`
3. if admitted, that generated status suppresses `CAN_CAST` only
4. the `silence` behavior profile immediately interrupts active casts/channels on admission

This keeps the mechanic inside existing canonical surfaces:

- cast suppression is the built-in silence profile
- channels/casts break through the shared CC interruption contract
- passives keep running because only `mute` clears `PASSIVES_ACTIVE`

## Cross-Boundary Concerns

Silence uses the ordinary target-owner CC relay story.

1. Remote/Ghost targets receive the `apply_cc` payload on their authoritative owner.
2. The target owner performs immunity checks, duration scaling, DR application, and status insert
   locally.
3. Later ability proposals are rejected on the target owner through the ordinary `CAN_CAST` gate,
   while movement and auto-attacks continue to route normally.
4. If the target hands off while silenced, the active status transfers as ordinary SoftState.

## Compiler Requirements

Designer specifies:

- hostile target filter and range
- `cc_type = silence`
- silence duration
- whether the effect is cleansable
- the DR category for the effect

Compiler emits:

- one canonical `apply_cc` payload with `cc_type = silence`
- one generated negative status entry using the canonical silence behavior profile
- target-side `duration_scaling = status_resistance` and the authored `dr_category`

Compiler validates:

1. `cc_type = silence` pairs only with canonical `category = soft_disable`
2. `duration_ticks > 0`
3. the authored `dr_category` is a supported DR domain
4. silence remains a cast-only disable and does not silently widen into mute or stun behavior

## Resolved Interaction Notes

- Silence blocks self-cast Purify in this reference because Purify is itself an ability cast.
- Counter-Strike, thorns, and other automatic reactive effects continue because they are not manual
  casts gated by player ability input.
- Already-admitted passive effects continue. Already-admitted active channels or casts do not: the
  canonical silence profile interrupts them immediately on admission.
- If a target is both rooted and silenced, the two statuses compose cleanly without turning into a
  different bespoke CC type.
- Echo/replay behavior from other mechanics follows the normal reactive/runtime rules for those
  mechanics. Silence itself only governs present and future cast admission on the silenced entity.
