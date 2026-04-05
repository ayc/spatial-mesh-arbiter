# SK-58: Cocoon

## Designer Intent

I encase an enemy in a cocoon for 8 seconds. While cocooned, they cannot act, cannot take damage, and cannot be targeted — but the cocoon itself is a visible, attackable object. The enemy's allies can break the cocoon by destroying it (it has HP). If destroyed, the enemy is freed early. If the timer expires, the enemy is freed at full cocoon duration.

## Primitive Composition

P-32 (Actor Spawning) → P-58 (Container/Vehicle Logic) → P-53 (Entity Suspension)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy — cocoon wraps around them instantly
2. Cocooned entity: cannot move, attack, cast, or be targeted by abilities
3. Cocooned entity: takes no damage from any source (invulnerable while cocooned)
4. A Cocoon object appears at the entity's position — it has its own HP pool (e.g., 600 HP)
5. The enemy's allies can attack the Cocoon object to destroy it and free their teammate
6. If Cocoon HP reaches 0: cocoon breaks, enemy is freed immediately
7. If 8 seconds pass: cocoon dissolves, enemy is freed
8. On release: enemy is briefly slowed (0.5s, 30%) as they shake off the cocoon
9. DoT timers on the cocooned entity: paused (they don't lose buff/debuff duration while cocooned)
10. Visual: amber cocoon shell, cracks as it takes damage, shatters on break

## Engine Primitives Required

Cocoon is now a canonical spawned shell plus contained target pattern.

The recommended lowering is:

1. spawn one cocoon actor at `target_position` with:
   - `owner = target`
   - a destructible cocoon archetype with authored HP
   - `container_profile = {`
     `max_capacity = 1,`
     `entry_range = ... ,`
     `allowed_filter = ally_alive,`
     `occupant_storage_mode = off_world_stored,`
     `occupant_can_be_targeted = false,`
     `occupant_cast_policy = none,`
     `allow_manual_exit = false,`
     `eject_on_removed = false`
     `}`
   - `targetability_policy = {`
     `hostile_effects = false,`
     `allied_beneficial_effects = false,`
     `allied_harmful_effects = true,`
     `self_effects = false`
     `}`
2. apply one negative `cocooned` status to the target with:
   - `suspension = {`
     `mode = stasis,`
     `invulnerable = true,`
     `pause_status_timers = true,`
     `pause_ability_cooldowns = false,`
     `exclude_from_payloads = true`
     `}`
3. immediately `enter_container(occupant = target, container = cocoon_actor, eject_after_ticks = 480,
   on_forced_eject_effects = [cleanse cocooned, apply_debuff release_slow])`
4. give the cocoon actor one passive/on-death cleanup ability that runs
   `exit_container(container = self, mode = all_occupants, on_exit_effects = [cleanse cocooned,
   apply_debuff release_slow])`

This keeps the player body itself out of the world while cocooned. The attackable object is the
spawned cocoon actor, not the stored target. The timer-pause behavior lives on the target's
`cocooned` status, while release-on-break / release-on-expiry uses ordinary container exit/eject
paths.

## Cross-Boundary Concerns

Cocoon follows the target-owner / spawned-shell authority model.

1. The cocoon actor spawns on the cocooned target's CURRENT owner, not on the caster's owner if
   those differ.
2. The contained target is carried as container-owned preserved state, so there is no separate
   target handoff while the target is cocooned. If topology changes, the cocoon actor hands off
   normally and carries the preserved occupant state with it.
3. The cocoon actor is the only thing neighboring allies can attack. If those attackers are remote
   relative to the cocoon's current owner, they use ordinary hostile relays against the cocoon
   actor's owner.
4. On timer expiry, the cocoon owner ejects the occupant locally and applies the authored release
   effects there. On early break, the cocoon actor's death cleanup performs the same local eject
   path before later cleanup finishes.

## Compiler Requirements

Designer specifies:

- hostile target
- cocoon duration
- cocoon HP
- release slow payload
- which relations can damage the cocoon shell
- whether target timers/cooldowns pause while cocooned

Compiler emits:

- one cocoon-shell spawned actor owned by the target
- one cocoon-shell entity archetype with static `container_profile`, HP, and relation-scoped
  targetability rules
- one negative `cocooned` status on the target using canonical `suspension.mode = stasis`
- one immediate `enter_container` mutation plus a timed forced eject
- one cocoon-shell death cleanup path that ejects stored occupants and applies the same release slow

Compiler validates:

1. the shell actor has `max_capacity = 1`
2. `occupant_storage_mode = off_world_stored` is paired with
   `occupant_can_be_targeted = false` and `occupant_cast_policy = none`
3. the shell is owned by the target so relation-scoped incoming attack rules line up with the
   cocooned target's allies
4. the release path clears the `cocooned` status and ejects the occupant on both timed expiry and
   shell destruction

## Resolved Interaction Notes

- The caster's team cannot attack or heal the cocoon shell in this reference. The cocoon is owned
  by the victim, and its targetability policy allows allied harmful effects only.
- The cocoon shell is a normal spawned actor body and therefore blocks pathing / skillshots through
  its ordinary targetability/collision policy unless the archetype is explicitly authored otherwise.
- The contained target is off-world stored and therefore cannot be displaced, targeted, or hit while
  cocooned. Attackers must interact with the shell actor instead.
- Multiple cocoons may exist simultaneously as ordinary independent shell actors unless another live
  limit is authored elsewhere.
- Because the target is under `stasis` with status timers paused and is removed from active spatial
  evaluation, contagion-style spread and other timer-driven status behavior do not advance while the
  target is cocooned.
- Purify cannot be cast on the cocooned target in this reference because the target is not
  targetable while contained. Breaking the shell is the intended counterplay.
- Unstoppable / relevant CC-immunity windows can reject the initial cocoon application before the
  shell/containment commit, using the same hostile-admission rules as other hard-disable effects.
