# SK-05: Global Strike

## Designer Intent

My character channels for 3 seconds, then deals damage to all enemy heroes across the entire map,
regardless of distance or line of sight. The channel can be interrupted by stuns, silences, or
displacement.

## Primitive Composition

P-43 (Charge-Up State) → P-46 (Global Event Scheduler)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (hits all enemies globally)

## Observable Behavior

1. Caster begins channeling; movement is locked and the cast bar is visible.
2. Enemy players see a warning indicator while the channel is in progress.
3. If the channel completes after 3 uninterrupted seconds, every enemy hero on the map takes the
   authored damage payload.
4. Damage is applied simultaneously on all targets at the same execute tick.
5. If the channel is interrupted by stun, silence, displacement, or death, the ability fizzles and
   the authored cooldown refund is applied.
6. Each target's defensive stats are still evaluated independently.

## Engine Primitives Required

Global Strike is now a canonical `channel(complete_only) + global_event` reference.

The recommended lowering is:

- `cast_time = 180`
- `channel = {`
  `execution_mode = complete_only,`
  `movement_lock = root,`
  `allow_other_abilities = false,`
  `break_on_displacement = true,`
  `partial_cooldown_refund = ...`
  `}`
- `global_event = {`
  `schedule_lead_ticks = 1,`
  `filter = enemy_hero_alive,`
  `target_class = heroes_only,`
  `geometry = whole_mesh,`
  `cancel_if_owner_removed = false`
  `}`
- root `effects = [damage(target = target, ...)]`

This keeps the mechanic inside existing surfaces:

- the 3-second cast bar is an ordinary interruptible `ChannelBlock`
- the map-wide fan-out is canonical `global_event` schedule metadata, not a hidden second spell
- damage is still one ordinary hostile damage effect resolved independently on each target owner
- the warning indicator is downstream observer/UI presentation tied to the visible channel state

## Cross-Boundary Concerns

Global Strike follows the canonical controller-escalated global-event contract.

1. The caster's current owner runs the 180-tick channel locally. If the channel breaks early, no
   controller request is emitted.
2. On successful completion, that owner bakes the offense-side context once and schedules one
   `global_event` for `current_tick + 1`.
3. At the execute tick, every Arbiter evaluates the event only against its own currently
   authoritative enemy heroes and resolves the root damage effect locally on each admitted target.
4. Target defenses remain target-local. Shields, evasion, spell immunity, invulnerability, and
   later reactive hooks all evaluate on the local target owner at execute time.
5. Because this reference uses `cancel_if_owner_removed = false`, once the channel completes
   successfully the scheduled strike still lands even if the caster is removed before the execute
   tick.

## Compiler Requirements

Designer specifies:

- channel time
- partial cooldown refund on interruption
- hostile hero filter
- damage payload
- whether post-completion owner removal cancels the scheduled strike

Compiler emits:

- one interruptible `ChannelBlock` on the ability
- one `global_event` block with `geometry = whole_mesh`
- one root hostile `damage` effect that is replayed against each admitted target at execute time

Compiler validates:

1. `targeting.type` is `none` or `self` because `global_event` is present
2. `cast_time > 0` because the ability authors a channel
3. `schedule_lead_ticks > 0`
4. the global-event target filter is compatible with `heroes_only`
5. the controller request is emitted only after the channel commits successfully, never on a broken
   or interrupted channel

## Resolved Interaction Notes

- Offensive context is baked once at schedule time. Each target still resolves that payload against
  its own defenses, so the strike can be blocked, shielded, evaded, or nullified by ordinary
  target-side rules.
- Membership is evaluated at execute time, not locked when the channel starts. Newly matching enemy
  heroes can be hit; targets that die or otherwise stop matching before the execute tick are
  skipped.
- Kinematic Dilation does not change the 180-tick authored channel. It remains 180 simulation ticks
  under the normal 60 Hz contract.
- Channel interruption from stun, silence, displacement, or death prevents scheduling entirely and
  uses the authored partial cooldown refund path.
- This reference uses a 1-tick schedule lead after successful completion, so the coordinated strike
  lands on the next controller-synchronized tick.
