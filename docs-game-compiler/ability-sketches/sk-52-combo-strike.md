# SK-52: Combo Strike

## Designer Intent

One button advances through a three-hit combo if I keep pressing it within a short window. The
first two hits are quick slashes; the third is the payoff hit that deals extra damage and heals me.

## Primitive Composition

P-42 (Stacking Counters w/ Decay)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Same public ability key pressed repeatedly
- Target chosen independently for each committed hit

## Observable Behavior

1. First cast uses step 0: a quick slash dealing base damage.
2. If I cast again within 2 seconds, step 1 fires: another quick slash.
3. If I cast again within 2 seconds after that, step 2 fires: a heavier slash that deals bonus
   damage and heals me.
4. After the third hit, the combo resets to step 0.
5. If I fail to continue the combo within the 2-second window, the combo resets to step 0.
6. Each hit may target a different enemy; the combo tracks the caster's sequence state, not a
   locked target chain.
7. In this reference, the opener uses the short/base cooldown, step 1 is a mid-combo free continue,
   and the finisher applies the full cooldown.
8. Visual: escalating slash presentation, with the third hit clearly telegraphed as the payoff
   strike.

## Engine Primitives Required

Combo Strike is already the canonical `sequence_window` + `ActivationModes` pattern.

1. The owning entity carries a `sequence_window` runtime state for this ability, with
   `max_step = 2`, `window_ticks = 120`, and `reset_to_step = 0`.
2. The public ability uses `ActivationModes` keyed by `sequence_step`:
   - base mode / step 0: damage + `advance_sequence(advance)`
   - step 1 mode: damage + `advance_sequence(advance)`
   - step 2 mode: heavier damage + self-heal + `advance_sequence(reset)`
3. Step 1 overrides cooldown to `0` so the continue hit does not start the base cooldown.
4. Step 2 overrides cooldown to the full finisher cooldown.
5. If the window expires before the next input, the sequence state resets automatically and the next
   cast uses the base mode again.

No separate combo state machine is needed beyond the canonical sequence-window runtime state.

## Cross-Boundary Concerns

The combo state is entirely caster-owned:

1. `sequence_window` lives on the caster's runtime state and transfers on ordinary handoff if the
   caster crosses an Arbiter boundary mid-combo.
2. Each committed hit resolves against the current target independently. A local first hit and a
   cross-boundary second hit are fine; the combo state remains on the caster.
3. Because each step is just an ordinary cast variant, all the usual relay rules for damage/heal
   payloads still apply per target. The combo itself does not need a second authority channel.

## Compiler Requirements

Designer specifies:

- combo window duration
- per-step damage values
- finisher heal amount
- base cooldown and finisher cooldown

Compiler emits:

- one `sequence_window` runtime state for the combo
- one public ability definition with ordered `ActivationModes` keyed by `sequence_step`
- per-step effects:
  - step 0: damage + `advance_sequence(advance)`
  - step 1: damage + `advance_sequence(advance)`
  - step 2: bonus damage + self-heal + `advance_sequence(reset)`
- cooldown overrides so the finisher, not the mid-combo continue, applies the long reset

Compiler validates:

1. the referenced combo runtime state exists and is a `sequence_window`
2. activation modes are ordered deterministically so step 2 is checked before step 1, and step 1
   before the base mode
3. the combo window is positive
4. any finisher self-heal uses ordinary heal authoring, not a bespoke combo-only recovery path

## Resolved Interaction Notes

- On-hit procs evaluate independently on each committed hit because each step is still an ordinary
  resolved attack.
- The finisher's heal is ordinary healing and therefore respects healing bonuses and anti-heal.
- Crowd control does not need bespoke combo logic. If I cannot continue the sequence before the
  window expires, it resets naturally to step 0.
- Propagation/replay mechanics may repeat the resolved hit payload, but the combo step itself
  advances only once per committed cast envelope in this reference.
- Each combo hit still spends its own ingress/token-bucket budget because each hit is a separate
  committed cast.
- Attack-speed buffs do not change the authored sequence-window duration unless the game explicitly
  authors a different `window_ticks` value.
