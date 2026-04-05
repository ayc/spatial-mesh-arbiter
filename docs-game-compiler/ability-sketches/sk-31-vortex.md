# SK-31: Vortex

## Designer Intent

I create a vortex at a target position that pulls nearby enemies toward its center for 4 seconds.
Enemies inside are continuously dragged inward and take periodic damage while they remain in the
zone. Strong movement or instant mobility can escape the pull; staying near the center is the
dangerous state.

## Primitive Composition

P-32 (Actor Spawning) → P-44 (Pulse Timer) → P-14 (Continuous Proximity Monitor) → P-02 (Forced Displacement)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted)

## Observable Behavior

1. A circular vortex appears at the target position
2. The vortex lasts 4 seconds
3. Every tick, hostile occupants are pulled toward the center
4. Every 1 second, hostile occupants take one damage pulse
5. Escape is determined by net movement after the entity's own input plus the vortex pull for that tick
6. Blink/dash-style mobility can leave the zone immediately if the destination is outside the radius
7. The vortex affects entities only, not projectiles
8. Visual: a stationary swirling field with visible inward drag on affected targets

## Engine Primitives Required

Vortex is now a canonical stationary `zone` pattern with one pulse payload and one continuous force
profile.

The compiler lowers it to one `zone` effect with:

1. `shape = circle`
2. authored `radius`
3. `duration_ticks = 240`
4. `pulse_interval_ticks = 60`
5. `pulse_effects = [damage(...)]`
6. `continuous_force = {`
   `filter = enemy_alive,`
   `direction = toward_center,`
   `strength_at_edge = ... ,`
   `strength_at_center = ...`
   `}`

This is not a bespoke "external force list" in the kinematics engine. It is the canonical
`ZoneForceBlock` surface. The force profile is a deterministic linear interpolation from
`strength_at_edge` to `strength_at_center`, evaluated every tick for currently admitted occupants
before the next kinematic resolution.

For the intended "gravity well" feel, this sketch assumes `strength_at_center > strength_at_edge`,
so escaping becomes harder once an entity is already close to the center.

## Cross-Boundary Concerns

Vortex follows the ordinary zone-authority model.

1. The vortex is one stationary zone actor with one authoritative owner
2. Occupancy and pulse membership are evaluated from the zone's committed current position using the
   canonical occupant-set / diff rules
3. No Arbiter directly mutates Ghost velocity or Ghost HP. Remote occupants are affected through the
   standard authority model for zone overlaps and target-side movement/damage resolution
4. If the pull causes an entity to cross a seam, the entity hands off normally and the new owner
   continues applying the same live zone force on subsequent ticks
5. Because the zone is stationary, topology changes affect it only through ordinary zone-actor handoff;
   there is no special oscillation rule beyond normal movement/collision/handoff semantics

## Compiler Requirements

Designer specifies:

- vortex radius
- lifetime
- hostile filter
- pulse interval
- pulse damage payload
- inward force profile (`strength_at_edge`, `strength_at_center`)

Compiler emits:

- one stationary `zone` actor
- one periodic hostile pulse payload
- one continuous radial force profile using `direction = toward_center`
- ordinary zone lifetime and occupant-set tracking

Compiler validates:

1. `duration_ticks > 0`
2. `pulse_interval_ticks > 0` when `pulse_effects` are authored
3. `strength_at_edge >= 0`
4. `strength_at_center >= 0`
5. the sketch uses canonical `zone.continuous_force` rather than a custom kinematic-force subsystem

## Resolved Interaction Notes

- Root does not imply displacement immunity. A rooted target still suffers the vortex pull unless
  another canonical effect grants forced-movement/displacement immunity.
- Multiple vortexes stack through ordinary net pre-kinematic movement influence; there is no
  special non-stacking rule for this sketch.
- Collision and clamping still resolve after the net movement vector is computed for the tick, so
  a pulled target slides/clamps according to ordinary movement resolution.
- Weight/mass is not implicitly part of `ZoneForceBlock`. If the game wants heavy targets to resist
  vortex pull, that must be authored through other canonical combat/movement policy rather than an
  automatic vortex rule.
