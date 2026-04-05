# SK-82: Projectile Deflect

## Designer Intent

I enter a short deflect stance for 1.25 seconds. While active, incoming projectile hits are caught
and returned to their source. Non-projectile damage is still negated by the stance, but only true
projectile actors are returned. The stance can be interrupted by ordinary cast-interrupting CC.

## Primitive Composition

P-61 (Projectile Ownership Hijacking) → P-03 (Trajectory Steering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only activation)

## Observable Behavior

1. Activate a self-only deflect stance for 1.25 seconds
2. While active, damage is negated
3. Incoming projectile actors are intercepted and retargeted to their original source
4. The returned projectile preserves the original carried payload
5. Melee hits, instant damage, beam damage, and zone pulses are negated by the stance but are not
   returned
6. The stance does not grant CC immunity; ordinary cast-interrupting CC can end it early
7. Returned projectiles can hit the original attacker's allies/body-blockers through ordinary
   projectile rules on the way back
8. Infinite "deflect tennis" is not allowed

## Engine Primitives Required

Projectile Deflect is now a canonical short maintained self-defense pattern:

1. the ability authors a short `channel`
2. the channel owns a maintained self-status for the duration
3. that status carries:
   - protection through canonical invulnerability authoring
   - `projectile_intercept = {`
     `mode = reflect_to_source,`
     `max_redirect_generations = 1,`
     `fallback_target = despawn,`
     `preserve_original_payload = true`
     `}`

The recommended channel shape for this sketch is:

- `cast_time_ticks = 75`
- `channel = {`
  `execution_mode = tick_while_active,`
  `movement_lock = none,`
  `allow_other_abilities = false,`
  `break_on_displacement = false`
  `}`

The key point is that the stance is maintained, not fire-and-forget. Stage 11 teardown removes the
channel-owned protection/intercept status immediately if the channel expires or breaks early.

`projectile_intercept` is only for true projectile actors. It does not apply to melee, instant
targeted damage, zone pulses, or other non-projectile delivery paths. Those are simply negated by
the protection state and produce no returned projectile.

## Cross-Boundary Concerns

Projectile Deflect follows the canonical `P-61` return path.

1. A projectile can cross into the deflector's Arbiter through ordinary projectile handoff
2. If it impacts during the active stance, the deflector's owner applies the local intercept rule
3. The projectile's redirect-generation counter increments
4. Control of the returned projectile transfers to the intercepting side
5. The returned projectile is retargeted to the original source and then follows the ordinary
   projectile/handoff rules back through the mesh
6. If the redirect would exceed `max_redirect_generations`, it is rejected instead of creating a
   ping-pong loop

Because the returned projectile becomes an ordinary live projectile again, any later collision,
body-block, mitigation, or kill-credit handling follows the same canonical rules as a normal
projectile after interception.

## Compiler Requirements

Designer specifies:

- stance duration
- whether movement is allowed during the stance
- early-break behavior through ordinary channel policy
- projectile return policy (`reflect_to_source`, payload preservation, redirect bound)

Compiler emits:

- one self-only maintained-cast/channel
- one channel-owned self-status that grants protection and projectile interception
- `projectile_intercept` metadata with `max_redirect_generations = 1`
- maintained-output teardown so interruption cleanly ends the stance

Compiler validates:

1. `cast_time_ticks > 0` when the channel is authored
2. `projectile_intercept.max_redirect_generations > 0`
3. the deflect path uses canonical projectile interception rather than a sketch-local damage-reflect clone
4. non-projectile negation comes from the stance's protection state, not from `projectile_intercept`

## Resolved Interaction Notes

- Because ownership transfers to the intercepting side, kill credit from a lethal returned
  projectile belongs to the deflector, not to the original attacker.
- `fallback_target = despawn` is used here: if the original source no longer exists, the caught
  projectile is simply removed instead of flying to a stale last-known position.
- All projectile hits during the active stance may be returned; the one-bounce limit is per
  projectile redirect generation, not per stance activation.
- The stance does not make the user untargetable or immune to CC. Stun, silence, and sleep follow
  the canonical channel-break rules and end the maintained stance early.
