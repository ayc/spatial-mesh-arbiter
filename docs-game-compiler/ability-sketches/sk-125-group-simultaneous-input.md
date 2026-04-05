# SK-125: Group Simultaneous Input

## Designer Intent

A fellowship maneuver triggers during combat. All group members see a selection wheel with a small
set of options, such as Red (damage), Blue (power restore), Green (heal), and Yellow (buff). Each
player independently chooses one option within a shared time window. Once all choices are in, or
the timer expires, the combination of selections determines the final group effect.

## Primitive Composition

P-54 (Group Choice Aggregator)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- An opening ability or combat event that starts the maneuver
- A bounded option list
- One selection from each participant in the scoped group

## Observable Behavior

1. A fellowship maneuver opens and all eligible participants see the selection UI
2. Each participant chooses one option independently within the shared time window
3. Combat continues while the selection window is open
4. Missing participants are filled with the authored default option at deadline
5. When the session resolves, the runtime checks for special ordered patterns first
6. If no ordered pattern matches, the runtime checks generic count-based patterns
7. The matched result applies the authored group effect
8. Visual: shared wheel UI, local choice feedback, dramatic combined resolution effect

## Engine Primitives Required

Group Simultaneous Input is now the canonical simultaneous `group_interaction` pattern.

### Simultaneous Group Session

The opening ability authors one `group_interaction` block with:

1. `participant_scope = party` or `raid_subgroup`
2. `mode = simultaneous`
3. `timeout_ticks`
4. one `simultaneous.options` list
5. one `default_option_id`
6. optional `allow_reselection`
7. optional `ordered_patterns`
8. required `count_patterns`

This is not a special "meta-input" transport. It is one bounded `P-54` session opened after the
triggering ability commits.

### Selections Are Temporary Public Option Abilities

The canonical surface does not add a second input lane beside combat. Instead, while the session is
active, the runtime exposes one temporary public option ability per authored option.

That means:

1. selecting Red, Blue, Green, or Yellow is implemented as casting a temporary option ability
2. Stage 2 admits or rejects that selection through the normal intent path
3. if `allow_reselection = true`, the last admitted option before the deadline overwrites the
   participant's earlier choice
4. if `allow_reselection = false`, later submissions are rejected after the first admitted choice

### Pattern Evaluation Order

When the window resolves, the session owner evaluates patterns in fixed order:

1. `ordered_patterns` first, against the authored `participant_order`
2. if no ordered pattern matches, `count_patterns` against the completed option counts

Missing participants are filled with `default_option_id` before either pattern pass runs.

This gives the intended behavior:

- exact ordered sequences can unlock named special results
- generic distributions like three Red and one Green can still map to a fallback effect

## Cross-Boundary Concerns

This sketch uses the canonical `P-54` session-owner relay contract.

1. The opening ability assigns one Arbiter as the session owner.
2. Each participant's local owner admits their temporary option-ability cast first.
3. Admitted selections are relayed to the session owner as contribution tuples.
4. The deadline is deterministic because it is measured against the shared authoritative tick.
5. When the result resolves, any participant-scoped heal, buff, damage, or resource restore still
   applies on the relevant authoritative owners through the ordinary relay rules.

So the maneuver is cross-Arbiter safe without needing a new controller-managed vote service.

## Compiler Requirements

Designer specifies:

- participant scope
- timeout
- option IDs
- default option
- whether reselection is allowed
- ordered special patterns
- count-based fallback patterns
- the `GroupResultBlock` for each pattern

Compiler emits:

- one `group_interaction(mode = simultaneous)` directive on the opening ability
- compiler-generated temporary option abilities for the active session
- the ordered and count-pattern tables
- participant-order metadata for ordered matching

Compiler validates:

1. `timeout_ticks > 0`
2. `options` is non-empty and unique
3. `default_option_id` is one of the declared options
4. `count_patterns` is non-empty
5. every `ordered_patterns.option_sequence` entry references a declared option
6. every `count_patterns.required_counts.option_id` references a declared option

## Resolved Notes

- Combat continues during the selection window. The session is an overlay on ordinary real-time
  play, not a pause state.
- Because selections are temporary public option abilities, ordinary crowd control and capability
  rules can stop a participant from making or changing a choice.
- If `allow_reselection = true`, later admitted choices overwrite earlier ones until deadline. If
  it is false, the first admitted choice sticks.
- Missing participants default at deadline; the session does not wait forever for disconnected or
  incapacitated members.
- Ordered patterns use the authored `participant_order` (`party_slot`, `raid_subgroup_slot`, or
  stable `entity_id` order). They are not inferred from join timing or network arrival order.
- The session timeout is an authoritative tick deadline owned by the group session, not a
  participant-local dilated timer.
- This sketch no longer requires a new "meta-input" transport. The canonical simultaneous
  `group_interaction` contract already covers it.
