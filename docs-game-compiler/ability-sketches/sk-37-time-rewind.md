# SK-37: Time Rewind

## Designer Intent

I activate this ability to revert my position and HP to what they were 3 seconds ago. Everything
else stays current; only position and HP rewind.

## Primitive Composition

P-05 (Historical State Buffer) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target

## Observable Behavior

1. The entity continuously records its own position and HP into a bounded 3-second history buffer.
2. On activation, the runtime reads the sample from 3 seconds ago.
3. The caster snaps to that stored position instantly.
4. The caster's HP is overwritten with the stored HP sample from that same moment.
5. Cooldowns, buffs, debuffs, and resources remain at their CURRENT values.
6. Visual: reverse-time movement trail and an obvious rewind snap.

## Engine Primitives Required

Time Rewind is now a canonical passive snapshot recorder plus active `restore_from_state`
reference.

The recommended lowering is:

1. define one runtime state:
   - `state_id = time_rewind_buffer`
   - `kind = snapshot_buffer`
   - `window_ticks = 180`
   - `sample_interval_ticks = 1`
   - `fields = [position, hp]`
2. define one hidden passive status on the caster with:
   - `snapshot_recorder_state = time_rewind_buffer`
3. on cast, emit:
   - `restore_from_state(target = caster, state_id = time_rewind_buffer, apply_position = true,`
     `apply_hp = true, position_validation = nearest_walkable)`

This keeps the mechanic inside existing canonical surfaces:

- the recorder is opt-in and bounded through `snapshot_buffer`
- the rewind uses one canonical state read rather than a bespoke rollback subsystem
- HP rewind is an overwrite from stored state, not a heal/damage event

## Cross-Boundary Concerns

Time Rewind follows the canonical snapshot-buffer handoff rule.

1. The snapshot buffer transfers intact on handoff as ordinary bounded runtime state.
2. Stored positions are absolute world coordinates, so a rewind can resolve under the CURRENT
   topology even if older samples were recorded on a different Arbiter.
3. If the stored destination is now owned by another Arbiter, the instant relocation follows the
   same destination-based teleport/handoff path as other `P-01` snaps.
4. The HP overwrite happens on the caster's current authoritative owner at the same time as the
   relocation.

## Compiler Requirements

Designer specifies:

- rewind lookback horizon
- which fields are recorded (`position`, `hp`)
- whether the recorder is passive/always-on while the talent is equipped
- any rewind presentation rules

Compiler emits:

- one bounded `snapshot_buffer` runtime state
- one hidden recorder status using `snapshot_recorder_state`
- one self-targeted `restore_from_state` read applying position and HP

Compiler validates:

1. the buffer window and sampling interval stay within bounded runtime limits
2. the recorder references a runtime state of kind `snapshot_buffer`
3. the active rewind reads only the supported `position` / `hp` fields
4. the mechanic is expressed through `restore_from_state`, not a bespoke full-entity rollback

## Resolved Interaction Notes

- Rewinding HP is a direct state overwrite. It does not create heal/damage events and therefore
  does not trigger on-heal or on-hit consumers.
- If the stored HP sample is lower than the caster's current HP, the rewind lowers current HP to
  that stored value in this reference.
- If the stored destination has become invalid due to later geometry, `nearest_walkable` gives the
  canonical relocation answer.
- Because the rewind only restores recorded `position` and `hp`, current buffs, debuffs, cooldowns,
  and resource pools remain unchanged by design.
