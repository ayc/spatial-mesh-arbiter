# SK-24: Stun

## Designer Intent

I hit an enemy with a stunning blow. They cannot move, attack, or cast abilities for 2 seconds. After the stun expires, they gain a brief CC immunity window.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Ability lands on target — stun is applied for 2 seconds
2. Target cannot move (movement input ignored)
3. Target cannot attack (auto-attack disabled)
4. Target cannot cast abilities (all ability inputs blocked)
5. Active channels (SK-05 Global Strike) are interrupted immediately
6. Stun duration is shortened by the target's `status_effect_resistance` because the canonical
   `stun` profile uses `duration_scaling = status_resistance`
7. After the stun expires: target gains a 1-second immunity window against the authored CC
   categories for the follow-up status (for this sketch: `hard_disable`)
8. Repeated hard-disable applications are reduced by the game's shared diminishing-returns table
   for the authored `dr_category`; the stun does not define a sketch-local DR formula
9. Visual: stars/dizzy effect over the target's head, frozen pose

## Engine Primitives Required

Stun is authored through canonical `apply_cc`, not through a bespoke per-skill rule.

The runtime contract is:

1. The ability emits `apply_cc { cc_type = stun, duration_ticks = 120, dr_category = hard_disable }`.
2. `apply_cc` lowers to a generated negative status entry carrying:
   - `cc_behavior_profile = stun`
   - `cc_category = hard_disable`
   - `duration_scaling = status_resistance`
   - ordinary status metadata such as `is_cleansable`
3. On admission, the target's authoritative owner evaluates:
   - P-62 immunity (`cc_immunity_categories`)
   - target-side duration scaling from `status_effect_resistance`
   - P-41 diminishing returns for the authored `dr_category`
4. If admitted, the generated status suppresses `CAN_MOVE`, `CAN_ATTACK`, and `CAN_CAST`.
5. The `stun` behavior profile also interrupts any active cast or channel immediately on
   admission.
6. When the stun expires, the authored follow-up positive status grants a 60-tick
   `cc_immunity_categories = [hard_disable]` window.

The capability suppression is therefore not sketch-local state. It is the canonical `stun`
behavior profile compiled into the target's active status registry and enforced through the normal
capability / interruption checks.

## Cross-Boundary Concerns

If the target is a Ghost, the caster's Arbiter does NOT apply the stun locally. It relays the
`apply_cc` parameters to the target's authoritative owner, and that owner performs admission,
duration scaling, DR, immunity checks, and status insertion.

This keeps all target-side state authoritative in one place:

1. Ghost data is advisory only.
2. The target owner owns `active_status_effects`, `status_effect_resistance`, and any P-41 DR
   tracker state for `hard_disable`.
3. The resulting stun status transfers normally on handoff if the entity crosses a boundary while
   still stunned.
4. Neighboring Arbiters only observe the outcome through later Ghost updates and relayed combat
   consequences, not through speculative local CC application.

## Compiler Requirements

Designer specifies:

- Single-target hostile ability targeting
- `apply_cc` with:
  - `cc_type = stun`
  - `duration_ticks = 120`
  - `dr_category = hard_disable`
  - default `duration_scaling = status_resistance`
- A follow-up positive immunity status with:
  - `duration_ticks = 60`
  - `cc_immunity_categories = [hard_disable]`

Compiler emits:

- A generated negative status entry for the stun admission path
- Canonical `cc_behavior_profile = stun` metadata on that generated entry
- The authored `dr_category` and `duration_scaling` metadata for target-side admission
- A follow-up positive status application granting the brief hard-disable immunity window

Compiler validates:

1. `cc_type = stun` pairs only with canonical `category = hard_disable`.
2. `duration_ticks > 0`.
3. Any authored `dr_category` references a supported DR domain.
4. The immunity follow-up uses valid `cc_immunity_categories`.
5. Any generated or follow-up statuses remain polarity-consistent and compatible with cleanse /
   status-admission rules.

## Resolved Interaction Notes

- Tenacity is the target's ordinary `status_effect_resistance` path, because canonical stuns default
  to `duration_scaling = status_resistance`.
- The immunity window applies only to the authored categories. For this sketch, the canonical
  follow-up is `cc_immunity_categories = [hard_disable]`, not universal CC immunity.
- If the target is currently immune to `hard_disable`, only the CC component is rejected; sibling
  damage or other non-CC effects from the same ability continue.
- Stun does not disable passives by itself. Only `mute` clears `PASSIVES_ACTIVE`.
- If a displacement has already committed into movement resolution, later stun admission does not
  retroactively rewind the movement. The stun suppresses subsequent voluntary movement/attacks/casts.
- DR is shared game policy on the target's P-41 tracker. The ability opts into that policy through
  `dr_category = hard_disable`; it does not define its own reset or tier table.
- Echoed or repeated stuns are separate admissions. Each one re-checks immunity and DR against the
  target's current authoritative state.
