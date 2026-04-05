# SK-18: Resurrect

## Designer Intent

I channel for 3 seconds on the corpse of a dead ally. If the channel completes, the ally is
revived at the corpse's position with 50% HP and all abilities on cooldown. The ally can
immediately move and act after revival, but cannot cast until those cooldowns recover.

## Primitive Composition

P-43 (Charge-Up State) → P-47 (Spatial Corpse Registry)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target: a dead ally's corpse (must be in range)

## Observable Behavior

1. Target a dead ally corpse within range and begin a 3-second rooted channel.
2. The cast publishes a visible cast bar and can be interrupted before completion.
3. If the channel survives to completion and the corpse record still exists, the ally
   re-materializes at the corpse's stored death position.
4. The revived ally returns with 50% max HP.
5. The revived ally returns with all abilities on full cooldown and with no active buffs or debuffs.
6. The revived ally may move, attack, and otherwise participate immediately after re-materializing;
   only ability cooldowns remain locked.
7. If the channel breaks early or the corpse becomes invalid, no revive occurs and the ability only
   takes the authored partial cooldown.
8. Visual: resurrection circle around the corpse while channeling and a completion beam on
   successful revival.

## Engine Primitives Required

Resurrect is now a canonical local corpse-return reference built from `channel(complete_only)` plus
`revive_corpse`.

The recommended lowering is:

1. author one corpse-targeted cast using `filter = ally_dead`
2. give the ability `cast_time_ticks = 180` with:
   - `channel = {`
     `execution_mode = complete_only,`
     `movement_lock = root,`
     `break_on_target_invalid = true,`
     `partial_cooldown_refund = ...`
     `}`
3. on successful completion emit:
   - `revive_corpse(corpse = target, hp_ratio = 0.50, clear_statuses = true,`
     `cooldown_policy = full_cooldown, consume_corpse = true)`

This keeps the mechanic inside existing canonical surfaces:

- the cast-time bar and interruption rules come from the normal channel lifecycle
- dead-ally targeting is ordinary corpse-registry targeting
- the actual return to play is Stage 10 `revive_corpse`, not a bespoke reconstruction path
- successful revival emits the ordinary `PlayerResurrected` cancel path for any pending Meta
  respawn timer

## Cross-Boundary Concerns

Resurrect follows the current canonical corpse rule: corpse access is local to the corpse's current
owner.

1. `revive_corpse` resolves only against the CURRENT Arbiter's authoritative corpse registry.
   Remote/Ghost corpse revival is not part of the current profile.
2. Cast admission succeeds only when the targeted corpse record exists locally at cast start.
3. If topology changes during the channel, ordinary cast-state and corpse-registry handoff carry
   the cast instance and corpse record to the new authoritative owner. No second revive-control
   plane is introduced.
4. If the corpse is consumed, expires, or otherwise invalidates before completion,
   `break_on_target_invalid = true` ends the channel and no revival fires.
5. On successful completion, the corpse owner performs the re-materialization locally at the stored
   death position and emits `PlayerResurrected` if Meta had already scheduled a default respawn.

## Compiler Requirements

Designer specifies:

- dead-ally corpse target filter and cast range
- channel duration and any partial cooldown refund on failure
- revive HP ratio
- cooldown policy on return
- whether statuses are cleared on return
- whether the corpse is consumed on success

Compiler emits:

- one corpse-targeted cast with `channel(complete_only)`
- one `revive_corpse` effect using the targeted corpse handle
- the ordinary visible cast-state publication for the non-zero cast time

Compiler validates:

1. the targeted entity resolves to a corpse-registry entry, not a living entity
2. `hp_ratio` is in `(0, 1]`
3. the corpse's source entity type defines `corpse_profile`
4. the sketch stays inside canonical local corpse revival rather than authoring remote/Ghost corpse
   access or alternate Meta respawn routing

## Resolved Interaction Notes

- This reference revives the same gameplay entity identity carried by the corpse record; it is not a
  fresh clone or a separate summon.
- Because `cooldown_policy = full_cooldown`, the ally returns unable to cast immediately even
  though movement/basic participation resumes as soon as the revive commits.
- Corpse lifetime remains governed by `corpse_profile.persist_ticks`. The resurrection channel does
  not extend that timer while it is in progress.
- If multiple allies channel the same corpse, the first successful `revive_corpse(consume_corpse =
  true)` clears the record; later channels fail through ordinary target invalidation.
- This sketch is the in-combat corpse-return path only. Alternate post-terminal respawn locations or
  timers remain the separate `SK-89 Respawn Anchor` contract.
