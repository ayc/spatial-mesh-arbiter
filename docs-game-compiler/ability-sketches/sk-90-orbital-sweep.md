# SK-90: Orbital Sweep

## Designer Intent

I latch onto an enemy with a grappling hook and swing around them in a circle. While swinging, I deal damage to any enemies my body passes through. After 2 revolutions, I can detach — slamming into the ground at a chosen angle, dealing AoE damage and stunning nearby enemies.

## Primitive Composition

P-06 (Attached Kinematics) → P-07 (Entity-as-Kinematic-Volume) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range — the orbit anchor)
- Detach timing (player-controlled while the orbit is active)

## Observable Behavior

1. Cast on enemy — caster attaches and begins orbiting around the target
2. The caster physically moves in a circle around the target at a fixed radius (e.g., 3 meters)
3. Orbit speed is constant (e.g., 1 revolution per second)
4. Enemies in the orbital path take damage as the caster passes through them
5. The orbit anchor (target enemy) can still move — the orbit center moves with them
6. While the orbit is active: the player can press the detach key to end it early
7. On detach: caster slams to the ground at the current orbital position, AoE damage + stun around
   the landing point
8. If the player doesn't detach: orbit continues for up to 4 revolutions then auto-detaches
9. If the orbit anchor dies: caster auto-detaches at current position
10. Visual: grappling hook swing, trail of energy, slam effect on detach

## Engine Primitives Required

Orbital Sweep is now a canonical `kinematic_sweep(mode = orbit_entity)` reference.

The recommended lowering is:

1. the opening cast starts one self-owned `kinematic_sweep` with:
   - `target = self`
   - `mode = orbit_entity`
   - `anchor = targeted enemy`
   - `duration_ticks = full orbit window`
   - `collision_radius = body radius`
   - `unique_hit_scope = entity_once_per_revolution`
   - `on_hit_effects = pass-through damage payload`
   - `orbit = {`
     `radius = 3.0,`
     `angular_velocity_per_tick = 1 revolution / 60 ticks,`
     `max_revolutions = 4,`
     `end_on_anchor_removed = true`
     `}`
   - `output_binding = orbit_position`
2. author the detach slam as an ordinary same-slot follow-up through `ActivationModes`, reusing the
   sweep's current `output_binding` position as the AoE center
3. gate that follow-up behind a compiler-owned active-orbit predicate so the slot only detaches
   while the orbit is live
4. let sweep expiry or anchor loss end the orbit at the current committed position; the same
   ordinary landing payload may be reused for auto-detach if the designer wants that behavior

This keeps the mechanic inside existing surfaces:

- derived orbit motion is the canonical `OrbitSweepBlock`
- pass-through body hits are just sweep `on_hit_effects`
- per-revolution dedup is the canonical `unique_hit_scope = entity_once_per_revolution`
- manual detach reuses `ActivationModes` rather than introducing a new client input type

## Cross-Boundary Concerns

Orbital Sweep stays on the anchor's current owner.

1. `orbit_entity` mode keeps the moving caster authoritative on the anchor's current owner instead
   of handoff-oscillating every time the orbit radius crosses a seam.
2. If the anchor hands off, the orbiting caster follows through the same co-located sweep handoff
   path and the new owner continues deriving orbit motion from the anchor's live pose.
3. Remote/Ghost targets struck by the sweeping body still resolve through the ordinary target-owner
   relay path. The orbiting caster does not damage Ghost state locally.
4. Manual detach runs on whichever owner currently holds the orbit sweep, using the same locally
   authoritative `output_binding` position that ended the orbit.

## Compiler Requirements

Designer specifies:

- hostile anchor target
- orbit radius
- angular velocity
- maximum revolutions / lifetime
- pass-through hit filter and damage payload
- detach landing payload

Compiler emits:

- one self `kinematic_sweep(mode = orbit_entity)` with the authored orbit block
- one sweep output binding exposing the current landing position
- one same-slot `ActivationModes` detach follow-up that consumes the live orbit and resolves the
  landing AoE / stun at the bound current position

Compiler validates:

1. `radius > 0`
2. `angular_velocity_per_tick > 0`
3. `max_revolutions > 0`
4. `unique_hit_scope = entity_once_per_revolution` is only used with `mode = orbit_entity`
5. manual detach is expressed through `ActivationModes` / runtime-state gating, not a bespoke orbit
   input plane

## Resolved Interaction Notes

- If the anchor moves, dashes, or blinks, the orbit center updates with the anchor's current
  authoritative position on the next tick.
- The orbiting caster remains targetable unless some other authored status or protection changes
  that; this sketch does not grant free untargetability during the swing.
- Multiple casters may orbit the same anchor if separate casts admit successfully; each sweep keeps
  its own orbit state and per-revolution hit ledger.
- The detach landing point is chosen entirely by timing, not by a second direction cursor.
