# SK-63: Steerable Beam

## Designer Intent

I channel a beam and sweep it across the battlefield while the cast is active. The damage source is
continuous and aimable, not a one-shot projectile.

## Primitive Composition

P-10 (Swept-Segment Raycast) → P-03 (Trajectory Steering) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Initial aim direction
- Continuous steering input while the channel remains active

## Observable Behavior

1. The beam begins immediately after channel admission and persists only while the channel is active.
2. The caster is rooted while channeling but may continue steering the beam.
3. Each tick, enemies currently intersecting the beam corridor take the authored per-tick damage.
4. The beam turns smoothly toward the requested aim direction, limited by the authored turn rate.
5. In this reference, the beam penetrates all enemies in its path rather than stopping on the first
   target.
6. If the channel is interrupted, the beam ends immediately and no further ticks occur.

## Engine Primitives Required

The canonical surface is `channel.execution_mode = tick_while_active` with `continuous_input =
steer_aim`.

1. The ability uses a bounded channel with:
   - `execution_mode = tick_while_active`
   - `continuous_input = steer_aim`
   - `movement_lock = root`
2. While active, the root effect list re-evaluates every tick using the current authoritative beam
   aim after turn-rate clamping.
3. The damage query is authored as one narrow forward corridor / line-style segment from the
   caster's current position out to max range.
4. Every tick that an enemy remains inside that corridor, the per-tick damage payload resolves
   again.

This is a maintained cast, not a persistent independent actor. The beam exists only as the current
tick's maintained query/effect output.

## Cross-Boundary Concerns

1. The caster's current owner evaluates the maintained beam every tick.
2. If the beam corridor intersects Ghosts, the caster owner uses the ordinary cross-boundary relay
   path for those damage payloads.
3. Steering state stays with the caster on handoff like any other channel-owned runtime state.

The beam does not need a second cross-Arbiter control plane beyond the existing maintained-channel
and Ghost-query rules.

## Compiler Requirements

Designer specifies:

- channel duration
- beam range / width
- per-tick damage
- turn rate
- interruptibility / movement lock

Compiler emits:

- one maintained channel with `tick_while_active`
- one `steer_aim` continuous-input policy
- one per-tick forward corridor/segment query from the caster
- one ordinary damage payload against all admitted enemies in that corridor

Compiler validates:

1. `tick_interval_ticks > 0`
2. `continuous_input = steer_aim` is used only with `tick_while_active`
3. beam range and width are positive

## Resolved Interaction Notes

- Because the beam is a maintained cast, crowd control that breaks channels ends it immediately.
- The reference version does not stop on static geometry; if the game wants wall-blocking beams, it
  should author that separately.
- Damage is evaluated every admitted tick. There is no once-per-channel dedup in this reference.
- Friendly fire is not part of the reference version; the corridor filters `enemy_alive` only.
