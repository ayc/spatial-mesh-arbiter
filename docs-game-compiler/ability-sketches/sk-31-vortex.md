# SK-31: Vortex

## Designer Intent

I create a vortex at a target position that pulls all nearby enemies toward its center. Enemies inside take damage every second and are continuously dragged toward the center point. The vortex lasts 4 seconds.

## Primitive Composition

P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-02 (Forced Displacement)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Vortex appears at target position (circular, fixed radius)
2. Every tick: all enemies within radius have their velocity modified toward the vortex center
3. Pull strength increases closer to the center (gravity well)
4. Every 1 second: all enemies inside take X damage
5. Enemies can attempt to walk out — if their movement speed exceeds the pull strength at their distance, they escape
6. Enemies at the center are trapped unless they use a mobility ability (dash/blink)
7. Vortex lasts 4 seconds then dissipates
8. Visual: swirling dark energy, particles flowing inward, affected enemies sliding toward center

## Engine Primitives Required

TODO: This introduces **continuous forced movement** — not a one-time displacement (SK-01 Toss) but a per-tick velocity modification. Every tick, the Arbiter must:
1. For each enemy in the vortex radius, calculate a pull vector toward the center
2. Pull magnitude scales with distance (stronger near edge to pull in, or stronger near center to trap?)
3. Add the pull vector to the entity's velocity
4. The entity's own movement input also applies — net velocity = player input + pull force
5. If net velocity points away from center and magnitude > 0, entity escapes

This is a force applied during `apply_kinematics` — a new concept. Currently kinematics processes movement input and collision. The vortex adds an external force source. How are external forces represented — a list of `ForceSource { position, magnitude, falloff }` that the kinematics step evaluates?

## Cross-Boundary Concerns

TODO: The vortex pulls entities toward its center. If the center is near an Arbiter boundary, entities being pulled toward it might cross the boundary — triggering an entity handoff. In the worst case, the vortex is centered ON a boundary and continuously pulls entities from one Arbiter into the other. This could cause rapid handoff oscillation if the entity gets pushed back by collision or movement input. Also: the vortex's pull force needs to affect Ghost entities (to show them being dragged), but Ghosts are read-only. The pull relay goes to the Ghost's owning Arbiter.

## Compiler Requirements

TODO: Designer specifies: zone shape (circle), radius, pull force profile (constant? distance-scaled?), damage per pulse, pulse interval, duration, mobility abilities can escape. Compiler produces: ZoneActor with per-tick force application + pulse damage + force profile function. The compiler needs to express the force profile as a deterministic function of distance.

## Open Questions

- Does the pull affect allies (friendly vortex for repositioning)?
- Does the pull affect projectiles in flight, or only entities?
- Can a rooted entity (SK-25) resist the pull? Root prevents voluntary movement, but is forced movement different?
- Can a vortex pull entities through SK-03 Terrain Walls?
- If two vortexes overlap, do their forces stack?
- Does the pull interact with the entity's collision — if pulled into a wall, does the entity slide along it?
- How does the pull interact with SK-01 Toss displacement — does the vortex redirect a tossed entity's trajectory?
- Performance: per-tick force calculation for every enemy in radius, every tick for 4 seconds — what's the entity count bound?
- Is pull strength affected by the target's "weight" or mass stat (heavy enemies resist more)?
