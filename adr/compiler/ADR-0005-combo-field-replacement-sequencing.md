# ADR-0005: Combo-Field Replacement via Explicit Context and Ordinary Sequencing

## Status

Accepted

## Date

2026-04-05

## Context

`SK-59 Oil-Ignite` exposed that the existing `combo_matrix` surface could detect a field/finisher
interaction, but could not:

- identify the specific live field actor that was comboed
- replace that field deterministically

The project needed to decide whether to add a bespoke `transform_field` primitive or solve the gap
through better combo callback context.

## Decision

Keep combo execution in the finisher's normal context and add explicit combo callback refs:

- `combo_field_entity`
- `combo_field_owner`
- `combo_field_position`
- `finisher_position`

Allow combo results to carry an `EffectList` so field replacement happens through ordinary authored
sequencing, typically:

1. `despawn_entity(combo_field_entity)`
2. spawn replacement field/zone at `combo_field_position`
3. preserve attribution explicitly with `owner = combo_field_owner` when needed

## Consequences

Positive:

- avoids a one-off combo-only transform subsystem
- keeps combo behavior compositional and compatible with the existing finisher-context model
- supports ally/enemy/self field interactions with one shared contract

Negative:

- combo effect context is richer and therefore slightly harder to reason about

Rejected alternatives:

- bespoke `transform_field`
- switching combo execution into field-owner context wholesale
- leaving field replacement as sketch-local special casing
