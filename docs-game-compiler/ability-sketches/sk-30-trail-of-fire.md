# SK-30: Trail of Fire

## Designer Intent

As I move, I leave a burning trail behind me. The trail persists for 4 seconds after I pass through. Enemies who walk through the trail take fire damage and are ignited (short DoT). The trail follows my exact movement path.

## Primitive Composition

P-57 (Polyline Collision Generator) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (passive or toggled — active while moving)
- Caster's movement path

## Observable Behavior

1. As the caster moves, fire appears along the path they traveled
2. The trail is not a circle — it's a line/path with width following the caster's exact route
3. Each segment of trail persists for 4 seconds from when it was deposited
4. Enemies who touch any trail segment take fire damage
5. Enemies who linger in the trail are ignited (DoT, 2 seconds, refreshed on continued contact)
6. The caster is immune to their own trail
7. Trail segments expire individually (oldest segments fade first)
8. Visual: burning ground along the path, fading from back to front

## Engine Primitives Required

Trail of Fire is the canonical `polyline_zone` pattern.

The compiler lowers it to one bounded `P-57` corridor generator keyed to the caster's committed
movement path, with:

1. `source = caster`
2. authored `width`
3. `duration_ticks` for the generator's own hard cap
4. `segment_ttl_ticks = 240` for the four-second trailing persistence window
5. authored `sample_interval_ticks` for how often the path is sampled
6. hostile `filter`
7. authored contact payloads through `pulse_effects` and/or `enter_effects`

This is not a stack of detached mini-zones and not a client-side breadcrumb effect. The runtime
owns one corridor-local ring buffer of sampled points and active segments. After each movement
commit, the current authoritative source position is sampled, appended to the corridor, and old
segments expire FIFO by `segment_ttl_ticks`.

Damage and ignite are ordinary authored effects, not special trail-only logic. A designer may tune
the contact cadence with `pulse_interval_ticks`; a short ignite DoT is just an ordinary negative
status applied by the trail's contact payload.

## Cross-Boundary Concerns

`polyline_zone` samples committed source motion, not client intent, so the trail follows the same
authoritative path already used by kinematics and handoff.

1. While the caster is local, the current owner appends new samples after movement commit.
2. Trail collision and pulse effects use the active corridor geometry from that authoritative path.
3. If hostile targets near the corridor are Ghosts, trail effects use the ordinary target-owner
   relay path; the trail owner does not mutate Ghost state locally.
4. If the caster hands off, the corridor generator continues from the same authoritative path on the
   new owner rather than being recomputed from client movement guesses.

So Trail of Fire is not a special boundary object. It is one canonical corridor effect tied to the
source entity's authoritative motion history.

## Compiler Requirements

Designer specifies:

- the tracked source entity
- trail width
- segment lifetime (`240` ticks for the four-second trail)
- optional total generator duration
- sampling cadence
- hostile admission filter
- contact payloads (fire damage and ignite status)
- whether the source is ignored by the corridor

Compiler emits:

- one `polyline_zone` effect bound to the caster
- corridor-local occupancy / pulse behavior instead of detached segment actors
- one compiled ignite `StatusEffectDefinition` if the trail applies a burn DoT

Compiler validates:

1. `width > 0`
2. `segment_ttl_ticks > 0`
3. `sample_interval_ticks > 0`
4. at least one blocking or effect payload is present
5. the ignite payload uses ordinary negative-status authoring rather than sketch-local trail logic

## Resolved Interaction Notes

- The trail follows committed movement only. Standing still deposits no new segments unless the
  designer explicitly enables `sample_on_stationary`.
- Segment expiry is FIFO by authored TTL, so old sections fade from back to front without bespoke
  cleanup code.
- The trail is passable by default; blocking movement or projectiles is only enabled if the
  designer explicitly authors those `polyline_zone` flags.
- Being displaced still paints the actual committed path. The mechanic keys off the source's final
  movement result, not on whether the movement came from voluntary input or forced displacement.
- The source can be made immune to the trail through the canonical `ignore_source = true` path,
  rather than by a sketch-local exception.
