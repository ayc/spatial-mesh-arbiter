# SK-99: Target-Tracking Zone

## Designer Intent

I summon a beam from the sky that locks onto an enemy hero and chases them for 8 seconds. The beam deals heavy damage per second at the target's position. Enemies near the tracked target take collateral AoE damage. The target can try to outrun the beam or lead it into their own allies to force them to scatter.

## Primitive Composition

P-32 (Actor Spawning) → P-06 (Attached Kinematics) → P-09 (Shape Overlap Query) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range at cast time)

## Observable Behavior

1. Cast on enemy hero — beam locks onto them
2. The beam follows the target's position every tick
3. The target takes X damage per second while the beam catches and stays on them
4. All enemies within AoE radius of the beam's current position ALSO take damage (collateral)
5. The beam moves at a speed slightly slower than normal movement (target can kite it)
6. If the target moves fast enough, the beam falls behind — dealing damage at the beam's position, not the target's
7. The beam persists for 8 seconds regardless of line of sight or distance
8. The caster can act freely after casting (fire and forget)
9. If the target dies, the beam dissipates early
10. Visual: golden beam from the sky, scorched ground, follows the target

## Engine Primitives Required

Target-Tracking Zone is now a canonical `zone.mobility(mode = tracking_entity)` reference.

The recommended lowering is:

1. spawn one damaging zone actor with:
   - `duration_ticks = 480`
   - `pulse_interval_ticks` matching the desired DPS cadence
   - `pulse_effects = [ aoe_damage(center = zone_self, shape = circle, radius = aoe_radius, ...) ]`
   - `mobility = {`
     `mode = tracking_entity,`
     `target = targeted enemy,`
     `speed = tracking_speed,`
     `on_target_removed = dissipate`
     `}`
2. let the zone move toward the tracked target's current position at capped speed each tick
3. resolve damage from the zone's committed current position, not the target's position, so the
   target may kite the beam and cause collateral hits around the trailing zone center

This keeps the mechanic inside existing surfaces:

- the moving beam is an ordinary spawned zone actor
- target-following is the canonical `tracking_entity` mobility mode
- collateral damage is ordinary zone pulse damage from the zone's current center
- early end on target death is the canonical `on_target_removed = dissipate` rule

## Cross-Boundary Concerns

Target-Tracking Zone uses the canonical moving-zone authority story.

1. The zone actor stays authoritative on its own current owner and samples the tracked target's
   current local-or-Ghost position there.
2. If the target crosses a seam first, the zone may continue tracking the Ghost and visibly lag
   behind because `tracking_entity` uses capped-speed pursuit instead of teleporting to the target.
3. If the zone itself crosses a seam while chasing, it hands off through the ordinary spawned-actor
   moving-zone path and resumes tracking from the new owner.
4. Pulse damage still resolves through the ordinary target-owner relay path for any admitted remote
   targets caught near the zone center.

## Compiler Requirements

Designer specifies:

- hostile tracked target
- tracking speed
- zone radius
- pulse cadence and damage
- lifetime
- target-loss behavior

Compiler emits:

- one spawned zone actor
- one canonical `ZoneMobilityBlock(mode = tracking_entity)`
- one pulse-damage payload centered on the zone's committed current position

Compiler validates:

1. `speed > 0`
2. `on_target_removed = dissipate` for this reference
3. the mechanic uses canonical moving-zone mobility rather than a bespoke target-following actor

## Resolved Interaction Notes

- If the tracked target blinks or otherwise jumps ahead, the zone does not snap; it continues
  pursuing the target's new position at the authored capped speed.
- If the target becomes stationary or enters stasis, the zone can catch up and continue pulsing at
  its own center.
- The base reference assumes no friendly fire; collateral damage applies only to admitted hostile
  occupants near the zone center.
- Fire-and-forget means the caster is free after spawn commit; later beam motion is entirely zone
  actor-owned.
