# SK-25: Root

## Designer Intent

I snare an enemy's feet to the ground. They cannot move for 3 seconds, but they can still attack
and cast abilities. They can be freed early by `SK-15 Purify`.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. The ability lands and applies root for 3 seconds.
2. While rooted, the target cannot move.
3. Auto-attacks remain available.
4. Non-movement abilities remain available.
5. Movement abilities are rejected because relocation abilities must require `can_move`.
6. Root does not interrupt active channels in this reference.
7. Duration is reduced by the target's `status_effect_resistance`.
8. Cleansing the root removes it early.
9. Diminishing returns follow the shared soft-disable DR policy rather than a sketch-local formula.
10. Visual: vines, ice, chains, or other feet-binding FX on the target.

## Engine Primitives Required

Root is authored through canonical `apply_cc`, not through a bespoke movement-lock subsystem.

The runtime contract is:

1. the ability emits `apply_cc { cc_type = root, category = soft_disable, duration_ticks = 180,
   dr_category = soft_disable }`
2. `apply_cc` lowers to a generated negative status carrying:
   - `cc_behavior_profile = root`
   - `cc_category = soft_disable`
   - `duration_scaling = status_resistance`
   - ordinary status metadata such as `is_cleansable`
3. if admitted, that generated status suppresses `CAN_MOVE` only
4. movement abilities are blocked because relocation abilities must already require `can_move` in
   their authored `requirements`

This keeps the mechanic inside existing canonical surfaces:

- voluntary movement suppression is the built-in `root` behavior profile
- duration reduction is the normal `status_resistance` path
- DR comes from the shared target-side P-41 tracker, not a sketch-local counter

## Cross-Boundary Concerns

Root uses the ordinary target-owner CC relay path.

1. If the target is remote/Ghost, the caster owner relays the `apply_cc` payload to the target's
   authoritative owner.
2. The target owner performs immunity checks, duration scaling, DR application, and status insert
   locally.
3. While rooted, later movement proposals are rejected on the target owner through the ordinary
   `CAN_MOVE` gate.
4. If the target hands off while rooted, the active status transfers as ordinary SoftState.

## Compiler Requirements

Designer specifies:

- hostile target filter and range
- `cc_type = root`
- root duration
- whether the root is cleansable
- the DR category for the effect

Compiler emits:

- one canonical `apply_cc` payload with `cc_type = root`
- one generated negative status entry using the canonical root behavior profile
- target-side `duration_scaling = status_resistance` and the authored `dr_category`

Compiler validates:

1. `cc_type = root` pairs only with canonical `category = soft_disable`
2. `duration_ticks > 0`
3. the authored `dr_category` is a supported DR domain
4. root remains a movement-only disable and does not silently widen into stun-like full lockout

## Resolved Interaction Notes

- Root does not stop forced displacement in this reference. Effects like Toss still move the target
  because root suppresses voluntary movement, not external relocation.
- Because the root profile does not interrupt channels, an already-active channel continues unless
  some other effect breaks it.
- Purify-style cleanse removes the generated negative status through the ordinary cleanse path.
- If the rooted target is also silenced, the two statuses simply compose: `CAN_MOVE = false` from
  root and `CAN_CAST = false` from silence.
- Tether distance, zones, and other spatial mechanics continue updating normally while the target is
  rooted. Root only stops the target from leaving under their own voluntary movement.
