# SK-62: Boomerang

## Designer Intent

I unleash fire waves that travel outward from me in all directions. After reaching max range, the waves reverse direction and return to me. Enemies can be hit on the way out AND on the way back — potentially taking damage twice.

## Primitive Composition

P-32 (Actor Spawning) → P-03 (Trajectory Steering) → P-35 (On-Hit Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (fires in all directions from caster)

## Observable Behavior

1. Cast — fire waves launch outward from the caster in multiple directions (e.g., 8 waves in a radial pattern)
2. Waves travel outward at constant speed, damaging enemies they pass through
3. At max range: waves stop, reverse direction, and travel back toward the caster
4. On the return trip: waves damage enemies again (double-hit possible)
5. Waves disappear when they reach the caster's CURRENT position (which may have moved)
6. Each enemy can be hit once per direction (once on outward, once on return — max 2 hits)
7. Visual: fire waves rippling outward then collapsing back inward

## Engine Primitives Required

Boomerang is now a canonical multi-spawn projectile-return pattern.

The recommended lowering is:

1. one `spawn_actor` effect with:
   - `position = caster_position`
   - `count = 8` for the reference radial pattern
   - `placement.offsets` carrying eight explicit world-space launch headings, for example one
     entry per compass / diagonal spoke
   - a projectile archetype with authored speed, lifetime, and hit payload
2. `projectile.return_policy = {`
   `trigger = max_range,`
   `track = source_entity_current,`
   `despawn_radius = ... ,`
   `allow_repeat_hits_on_return = true,`
   `preserve_speed = true`
   `}`

Each derived projectile is an ordinary live projectile actor with one outbound leg and one return
leg. Return flight is not a second spawn. The same actor ID stays alive, flips into return mode at
max range, and then homes toward the source entity's CURRENT position.

The canonical double-hit rule is the one already attached to `allow_repeat_hits_on_return = true`:
the runtime keeps separate outbound and return hit ledgers. A target may therefore be hit once on
the outward leg and once on the return leg, but not repeatedly within the same leg.

For this sketch, the radial pattern does not come from player aim. It comes from the explicit
placement-authored heading lattice. That keeps the no-target "fire in all directions" cast fully
deterministic without inventing a second projectile-launch subsystem.

## Cross-Boundary Concerns

Boomerang follows the ordinary projectile-owner / Ghost / handoff model, even though one wave may
cross a seam twice.

1. Each wave is an independent projectile actor and hands off normally when its current position
   crosses into a neighbor's authority.
2. The return phase is just projectile SoftState. If a wave is currently owned by Arbiter B while
   the caster remains on Arbiter A, the return leg tracks the source entity through B's local-or-
   Ghost view of that source and updates cleanly as Ghost data refreshes.
3. If the caster blinks or otherwise relocates during the return leg, the wave adjusts on the next
   steering tick because `track = source_entity_current` samples the source entity's CURRENT
   position rather than the original cast position.
4. If the source entity is removed before the wave completes its return, the canonical fallback is
   `source_entity_last_known_on_loss`; the wave finishes its return toward the last authoritative
   known source position and then despawns there.
5. Outbound/return hit ledgers survive ordinary projectile handoff with the rest of the actor
   state, so a seam crossing does not reopen per-leg double-hit admission.

## Compiler Requirements

Designer specifies:

- wave count / launch lattice
- explicit placement offsets plus explicit per-wave launch headings
- projectile speed
- outbound range / lifetime
- per-hit hostile payload
- pass-through budget (`pierce`) for the intended density envelope
- return despawn radius
- whether same-target repeat hits are allowed on the return leg

Compiler emits:

- one multi-spawn `spawn_actor` effect
- one ordered `placement.offsets` lattice with per-derived heading vectors
- one projectile archetype using canonical `return_policy`
- one outbound/return hit-ledger contract through `allow_repeat_hits_on_return = true`
- one source-tracking fallback policy for source removal during the return leg

Compiler validates:

1. `count = len(placement.offsets)`
2. every placement-authored heading vector is non-zero
3. placement-authored heading vectors are used only on projectile spawns
4. `despawn_radius > 0`
5. pass-through remains bounded through authored projectile `pierce`; the compiler/runtime do not
   widen this into an unbounded per-wave hit list

## Resolved Interaction Notes

- The outward and return hits reuse the same carried offensive payload that was baked at cast time;
  each admitted hit still resolves independently against the struck target's OWN defenses.
- This reference assumes `detonation_policy.world_impact = ignore`, so temporary terrain blockers
  do not stop the waves before the return leg. A wall-blocked boomerang would be a different
  authored projectile profile.
- Each admitted hit may trigger ordinary on-hit downstream hooks. The dedup rule only prevents
  repeated hits within the same leg.
- The source entity does not damage itself on return in this reference, because the hostile target
  filter excludes the owner.
- Collision width is the projectile archetype's ordinary collision radius. The sketch does not
  require a special zero-width ray model.
