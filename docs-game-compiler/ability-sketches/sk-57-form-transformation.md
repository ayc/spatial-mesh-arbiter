# SK-57: Form Transformation

## Designer Intent

I transform into a stronger alternate form for a limited time. My ability bar and appearance
change, and I gain a timed stat package for the duration, then revert automatically.

## Primitive Composition

P-31 (Identity/Loadout Swap) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Self-cast only

## Observable Behavior

1. Activate to enter the alternate form immediately.
2. The entity keeps the same `entity_id`, position, and Arbiter ownership; only loadout/profile and
   timed stats change.
3. The alternate form uses a different loadout/profile, including any alternate basic attack or
   alternate-form abilities.
4. A simultaneous timed positive status grants the bonus max HP, damage, armor, and other stat
   modifiers for the form duration.
5. Existing buffs/debuffs persist through the transformation in this reference.
6. The transform preserves current HP ratio on entry.
7. When the duration ends, the entity reverts automatically to the original loadout/profile and the
   stat-bonus status expires.
8. As the max-HP bonus falls off on revert, current HP is naturally capped by ordinary max-HP
   recomputation.
9. In this reference, the cooldown begins on activation, not after revert.

## Engine Primitives Required

The clean canonical model is profile swap plus a timed buff overlay.

1. The entity definition provides one named alternate `loadout_profile`.
2. Activation applies `swap_identity(target = caster, source = { self_profile: alternate_form },
   duration_ticks = 900, hp_policy = preserve_ratio, cooldown_policy = store_and_restore)`.
3. The same activation also applies one positive status carrying the alternate form's stat
   modifiers for the same duration.
4. When `swap_identity` expires, the runtime restores the original loadout/profile automatically.
5. When the stat-bonus status expires, the entity loses the alternate-form stat package through the
   ordinary status-expiry path.

This keeps the form swap compositional:

- `swap_identity` handles loadout/profile/appearance routing
- the timed status handles bonus stats
- ordinary status persistence means existing unrelated buffs/debuffs remain unless the game authors
  a separate cleanse on transform

## Cross-Boundary Concerns

Transformation stays entirely on the transforming entity's authority:

1. The entity's current owner applies `swap_identity` and the timed stat status locally.
2. If the entity crosses an Arbiter boundary while transformed, the remaining duration plus the
   transformed loadout/profile state transfer with the entity through ordinary handoff.
3. Future combat uses whatever transformed offensive/defensive state is current at the moment each
   attack resolves. There is no special cross-boundary exception for transformed combat.

## Compiler Requirements

Designer specifies:

- alternate loadout/profile ID
- transform duration
- alternate-form stat modifiers
- entry HP policy (`preserve_ratio` in this reference)

Compiler emits:

- one named alternate `loadout_profile` in the entity definition
- one `swap_identity` activation using `{ self_profile: alternate_form }`
- one positive timed stat-buff status for the same duration

Compiler validates:

1. the referenced `self_profile` exists on the entity definition
2. `duration_ticks > 0`
3. any stat-bonus status used for the form is `positive`
4. the transform does not change ownership or create a second body

## Resolved Interaction Notes

- Alternate-form cooldowns are separate from the original form according to
  `cooldown_policy = store_and_restore`.
- The reference version does not self-cleanse on transform. If a game wants that behavior, it
  should author it explicitly as a separate cleanse or immunity effect.
- The death-triggered "eject into a weaker form instead of dying" variant is not part of this
  closed reference. That is a separate death-intercept design, not a requirement of the basic
  timed transform contract.
- Because the transform uses a named self profile, ability-steal or loadout-snapshot mechanics read
  whichever profile is currently active at the time they snapshot/copy it.
