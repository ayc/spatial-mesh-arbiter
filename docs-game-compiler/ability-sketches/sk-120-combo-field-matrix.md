# SK-120: Combo Field Matrix

## Designer Intent

When I place a fire zone on the ground and my teammate fires a projectile through it, the
projectile becomes a burning projectile that deals bonus fire damage on hit. If instead my teammate
leaps through the fire zone, they gain a fire shield. The effect depends on the combination of zone
type and finisher type. Any field and any finisher can combine, creating emergent cross-player
synergies.

## Primitive Composition

P-14 (Continuous Proximity Monitor) → P-64 (Combo Field × Finisher Matrix)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- A placed combo field (zone or field-emitting entity with `combo_field_type`)
- A combo finisher ability (`combo_finisher = projectile | blast | whirl | leap`)
- A `combo_matrix` table entry matching the field/finisher pair
- The combination determines the resulting effect

## Observable Behavior

1. Player A places a Fire Field
2. Player B fires a projectile through it
3. The projectile gains the fire/projectile combo effect
4. Or Player B uses a Blast finisher inside it and gets the fire/blast combo effect
5. Or Player C leaps through it and gets the fire/leap combo effect
6. Different field types can produce different results for the same finisher type
7. Each successful combo produces the authored combo effect plus any presentation cue such as a
   "Combo!" indicator
8. Any player's field plus any player's finisher is a valid combo candidate by default

## Engine Primitives Required

Combo Field Matrix is now a canonical game-data-driven systemic mechanic, not a sketch-local engine
subsystem.

It uses three existing surfaces together:

1. an optional `combo_field_type` tag on a field-emitting zone or entity
2. an optional `combo_finisher` tag on an ability definition
3. a game-data `combo_matrix` table mapping `(field_type, finisher_type)` to an authored effect

### Combo Field Tags

Any zone or field-emitting entity may carry one `combo_field_type` tag. Not every zone is a combo
field; only authored fields opt in.

Current canonical field enum:

- `fire`
- `water`
- `lightning`
- `poison`
- `smoke`
- `ice`
- `light`
- `dark`
- `ethereal`
- `oil`

### Combo Finisher Tags

Any ability may carry one optional `combo_finisher` tag.

Current canonical finisher enum:

- `projectile`
- `blast`
- `whirl`
- `leap`

### Combo Matrix Table

The actual combo outcomes live in game data, not in engine code.

Example entries:

- `(fire, projectile) -> apply burn-on-hit payload`
- `(fire, blast) -> aoe might around the blast`
- `(fire, leap) -> fire shield on the leaper`
- `(water, blast) -> aoe heal`
- `(smoke, blast) -> aoe stealth`
- `(lightning, whirl) -> spawn lightning bolts`

The compiler serializes this as `ComboMatrixDefinition` into the static combo-matrix table section
of the game image. Duplicate `(field, finisher)` entries are rejected at compile time.

### Combo Detection

Detection follows the canonical `P-64` rules:

1. **Projectile:** checked per tick during flight; the first eligible field intersection triggers.
2. **Blast:** checked at the blast resolution point; if the blast center is inside a field, the
   combo triggers there.
3. **Leap:** checked against the leap path; if the path crosses a field, the combo triggers.
4. **Whirl:** checked during the active whirl or channel; each eligible field can trigger once for
   the whirl, not once per tick.

A finisher can combo with each field at most once. Multiple finishers may still combo with the same
field. A projectile or leap that encounters multiple eligible fields uses the first eligible field
in deterministic local query order, which follows the ordinary overlap ordering rules.

### Cross-Player Semantics

Cross-player combos are the intended default.

1. The field owner and finisher user may be different players.
2. Self-combos are also valid because the system does not special-case the field creator.
3. The effect resolves in the finisher's local execution context, using the authored effect payload
   for that matrix entry rather than a hardcoded team-sharing rule.

## Cross-Boundary Concerns

This sketch follows the current canonical `P-64` boundary rule: combos are detected only when the
finisher and field are on the same Arbiter.

That yields the following behavior:

1. **Projectile into field after handoff:** if the projectile hands off into the Arbiter that owns
   the field, combo detection happens there and works normally.
2. **Blast near a seam with the field only on the neighbor:** no combo is detected in the current
   canonical profile. Combo evaluation is not a cross-Arbiter relay or ghost-field feature today.
3. **Leap through a field during boundary traversal:** combo is detected only on the Arbiter that
   authoritatively evaluates the leap segment and also has the field locally.
4. **Whirl in an overlap band:** only the local authoritative field/finisher pairing counts; there
   is no separate neighbor-side combo replay.

## Compiler Requirements

Designer specifies:

- which zone or entity definitions emit a `combo_field_type`
- which abilities emit a `combo_finisher`
- the `combo_matrix` lookup table
- the authored effect payload for each supported `(field, finisher)` pair

Compiler emits:

- `combo_field_type` metadata on the relevant zone and entity definitions
- `combo_finisher` metadata on the relevant ability IR entries
- a serialized `combo_matrix` static-data table in the game image
- the ordinary combo-detection hooks already implied by the finisher type
- per-finisher dedup state so one finisher does not repeatedly trigger on the same field

Compiler validates:

1. every `(field, finisher)` pair appears at most once in the combo matrix
2. only the canonical field enum values are used
3. only the canonical finisher enum values are used
4. combo effects are expressible as ordinary authored effect payloads
5. field tagging lives on field emitters and finisher tagging lives on ability definitions, not in
   sketch-local runtime flags

## Resolved Interaction Notes

- Enemy fields can still be used for combos in this canonical profile because combo detection does
  not check field ownership before consulting the matrix.
- Self-combos are valid for the same reason; the finisher user may also be the field creator.
- Overlapping eligible fields resolve by ordinary deterministic overlap ordering, so the first
  eligible field wins for a one-shot finisher.
- The matrix lives in game data and is serialized in the game image; the engine provides detection,
  not hardcoded field-specific content.
- Field and finisher enum spaces are currently fixed to the canonical sets above. New combo effects
  are data-only; new enum categories would still require canonical-doc expansion.
- Kinematic Dilation affects the underlying projectile, leap, or whirl timing the same way it
  affects those abilities normally; combo detection itself does not add a special dilation rule.
