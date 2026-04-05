# SK-53: HP Swap

## Designer Intent

I channel on an enemy and, if the channel completes, our current HP percentages are swapped in one
instant overwrite. It is a dramatic reversal tool, not a damage or healing spell.

## Primitive Composition

P-17 (Conditional Thresholds) → P-15 (Value Modification)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Enemy target
- Interruptible 2-second channel

## Observable Behavior

1. Start channel on an enemy target for 2 seconds.
2. During the channel, both entities keep taking normal damage/healing; the swap uses whatever HP
   percentages exist at completion time, not at channel start.
3. On successful completion, the engine captures both current HP percentages before either write.
4. The caster's HP becomes `(target_pct * caster_max_hp)` and the target's HP becomes
   `(caster_pct * target_max_hp)`.
5. In this reference, both entities are clamped to a minimum of 1 HP after the overwrite.
6. The overwrite is instantaneous and does not count as damage, healing, lifesteal, or shield
   interaction.
7. Shields are untouched; only base HP is swapped.

## Engine Primitives Required

This is already the canonical `channel -> swap_hp_percent` path.

1. The ability uses an interruptible `ChannelBlock` with `execution_mode = complete_only`.
2. On successful completion, it emits `swap_hp_percent(target = target, min_hp = 1,
   same_arbiter_only = true)`.
3. `swap_hp_percent` captures both percentages before either write and then performs the paired
   overwrite atomically.
4. Because the overwrite is not damage or healing, it bypasses damage/heal hooks, mitigation,
   lifesteal, shields, reflection, and damage-accumulator mechanics.

## Cross-Boundary Concerns

The current canonical profile keeps HP swap same-Arbiter only:

1. The target must be authoritative locally at resolution time. Remote/Ghost targets are rejected
   by `swap_hp_percent(same_arbiter_only = true)`.
2. If the target handoffs away, becomes remote, dies, or otherwise becomes invalid before channel
   completion, the channel fails instead of attempting a cross-Arbiter paired write.
3. This keeps the paired read/write atomic without introducing a new multi-owner transactional
   protocol for one sketch.

## Compiler Requirements

Designer specifies:

- target filter (enemy in this reference)
- channel duration
- minimum post-swap HP clamp

Compiler emits:

- one interruptible complete-on-finish channel
- one `swap_hp_percent` completion effect with `same_arbiter_only = true`

Compiler validates:

1. the target is not a Ghost/remote entity at completion time
2. `min_hp >= 0`
3. the channel still satisfies normal target-validity checks at completion

## Resolved Interaction Notes

- Different max HP pools are fine. The mechanic swaps percentages, then rescales to each entity's
  local max HP.
- If either side dies before completion, there is nothing to swap and the channel fails.
- Unstoppable does not block the swap because this is not crowd control.
- Invulnerability does not by itself block the swap because the overwrite is not damage; becoming
  untargetable or otherwise invalid during the channel still breaks the cast normally.
- Adaptation-style damage tracking only counts real damage taken before the swap. The overwrite
  itself does not feed those accumulators.
