# SK-110: Mute

## Designer Intent

I doom an enemy, disabling ALL their passive abilities and item effects for the duration. Their aura stops, their thorns stop, their lifesteal stops, their item procs stop. They become a basic entity with only their active abilities (which are also silenced by Doom). They're stripped of everything.

## Primitive Composition

P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. Cast on enemy — Mute debuff applied
2. All PASSIVE abilities are disabled: SK-08 Aura stops pulsing, SK-23 Thorns stops firing, passive regen stops
3. All ITEM passive effects are disabled: on-hit procs, passive stat bonuses from items, lifesteal
4. Active abilities may or may not also be silenced (Doom silences + mutes; Mute alone is separable)
5. Duration: typically long (15+ seconds for Doom)
6. The target retains their base stats — only bonus effects from passives/items are suppressed
7. Cleansable? Design choice (Doom is typically NOT cleansable)
8. Visual: heavy debuff indicator, suppressed ability icons greyed out

## Engine Primitives Required

Mute is already one of the canonical `apply_cc` behavior profiles.

The recommended lowering is:

1. apply one hostile CC with:
   - `cc_type = mute`
   - `category = mute`
   - `duration_ticks = ...`
   - `duration_scaling = status_resistance` or `fixed`, depending on the design
2. let the generated negative status use the canonical mute profile:
   - clear `PASSIVES_ACTIVE` while the status is present
   - suspend passive statuses, aura pulses, passive item effects, and passive proc registrations
   - resume them when the status ends instead of removing and rebuilding them from scratch
3. if the design is Doom-style "mute plus silence," author a sibling `apply_cc(cc_type = silence, ...)`
   instead of inventing a bespoke combined suppression type

This keeps the mechanic entirely inside the canonical CC / capability surface:

- mute is not a second passive-disable subsystem
- passive suspension is driven by the canonical `PASSIVES_ACTIVE` bit
- compile-time passive classification already exists through `StatusEffectDefinition.is_passive`
- mute and silence remain separable because `mute` only suspends passives; it does not inherently
  suppress active casts

## Cross-Boundary Concerns

Mute follows the canonical target-owner CC contract.

1. The target's current owner admits the mute status through the ordinary CC relay path.
2. While the status is active, that owner clears `PASSIVES_ACTIVE` during passive evaluation and
   stops emitting passive outputs from that entity.
3. Remote observers and neighboring Arbiters do not need a second "mute passive off" protocol.
   Aura loss, passive proc removal, and other downstream effects disappear through the same
   authoritative status/output replication path that already carries passive state.
4. If the target hands off mid-mute, the generated status transfers as ordinary SoftState and the
   new owner continues the same passive-suspension behavior.

## Compiler Requirements

Designer specifies:

- duration
- whether mute is cleansable
- whether it uses ordinary status-resistance duration scaling
- whether a sibling silence is also applied

Compiler emits:

- one hostile `apply_cc` with `cc_type = mute`
- the generated negative status carrying canonical mute behavior metadata
- any optional sibling silence application if the design wants Doom-style active-cast lockout too

Compiler validates:

1. `cc_type = mute` pairs only with `category = mute`
2. the mechanic is expressed through canonical `apply_cc`, not a bespoke per-effect passive
   blacklist
3. passive suppression relies on `PASSIVES_ACTIVE` and compiled passive metadata, not on deleting
   passive statuses from the registry

## Resolved Interaction Notes

- Base stats remain. Mute suspends passive statuses and passive item effects, not the entity's base
  definition data.
- Passive stat bonuses that are authored as passive statuses or passive item effects are suspended
  while mute is active and resume afterward.
- `SK-100 Ally-Untargetable` is authored as a permanent passive status, so its CC-immunity layer is
  suspended while muted.
- Mute does not automatically affect summoned entities owned by the target. It is a per-entity
  status on the muted target, not an owner-wide pet command.
- Mute and silence can be applied independently. Mute alone still allows active casting unless a
  sibling silence or other cast suppression is also present.
- Because mute is canonical CC in the `mute` category, Unstoppable / CC-immunity effects that block
  `mute` reject it on admission the same way they reject other supported CC categories.
- Duration scaling and DR are ordinary authored CC metadata for this reference; mute does not need
  a bespoke duration system.
