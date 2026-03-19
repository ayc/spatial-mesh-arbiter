# SK-63: Steerable Beam

## Designer Intent

I channel a continuous beam of lightning in front of me for 4 seconds. The beam deals heavy damage per second to all enemies in its path. While channeling, I can slowly rotate the beam's direction with steering input — sweeping it across the battlefield. I cannot move while channeling, but I can aim.

## Primitive Composition

P-10 (Swept-Segment Raycast) → P-03 (Trajectory Steering) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Initial beam direction (from requested aim direction at cast time)
- Continuous steering input (requested aim target/direction, updated in real time during channel)

## Observable Behavior

1. Channel begins — beam fires from caster in the initial direction
2. Beam is a continuous line from the caster extending to max range (e.g., 12 meters)
3. All enemies in the beam's path take X damage per second (continuous, not pulsed)
4. Caster can slowly rotate the beam direction (e.g., max 90° per second turn rate)
5. Caster cannot move while channeling (movement locked)
6. Channel can be interrupted by stuns, silences, displacement
7. After 4 seconds: channel ends, beam disappears
8. Visual: bright lightning beam, scorch marks along the swept path

## Engine Primitives Required

### Continuous Line Damage

Unlike projectiles (travel and hit) or zones (area check), the beam is a **continuous line segment** that deals damage every tick to entities intersecting it:

```
struct BeamState {
    origin: Vec2F,           // Caster's position (fixed during channel)
    direction: Vec2F,        // Current beam direction (rotates per tick)
    max_range: SimFixed,
    turn_rate_per_tick: SimFixed,  // Max rotation per tick
    dps: SimFixed,
    damage_per_tick: SimFixed,     // dps / 60
}
```

Each tick:
1. Update beam direction based on caster's steering input (clamped by turn rate)
2. Cast a ray from `origin` in `direction` for `max_range`
3. Find all entities intersecting the ray (line segment collision against entity hitboxes)
4. Apply `damage_per_tick` to each intersected entity

This is a per-tick raycast against all entities — similar to a continuous version of SK-43 Drag's skillshot, but repeated every tick with changing direction.

### Steering Input During Channel

Like SK-40 Mind Control, the caster sends continuous input during the channel. But instead of controlling another entity's movement, it controls the beam's rotation:

1. Caster's Edge Node sends steering input each tick
2. Arbiter calculates desired beam direction from caster → requested aim target (or directly from requested orientation)
3. Clamp rotation to `turn_rate_per_tick` (smooth, not instant)
4. Update `direction`

The beam doesn't snap to the requested aim target/orientation — it smoothly rotates toward it, limited by turn rate. This prevents instant 180° sweeps.

### Per-Tick Line Collision

The spatial query is a line segment intersection test, not a radius test. Each tick, the Arbiter must:
- Define the line segment: `origin → origin + direction * max_range`
- Check all entities within the beam's "corridor" (line + small width)
- Apply damage to intersections

This is similar to the raycast used for line-of-sight (T0-03 static_grid), but against dynamic entities rather than static geometry. Does the beam stop at the first entity (blocked) or pass through all of them?

## Cross-Boundary Concerns

TODO: The beam extends from the caster up to 12 meters. If the caster is near a boundary, the beam may extend into the neighbor's region. Entities in the beam's path on the neighbor's Arbiter are Ghosts — the beam's Arbiter can raycast against Ghost positions and relay damage.

As the beam rotates, it may sweep across the boundary — some ticks hitting local entities, some ticks hitting Ghosts. The cross-boundary traffic is proportional to how many Ghosts the beam sweeps over.

The beam is also a continuous damage source — every tick that a Ghost is in the beam generates a damage relay. At 60Hz for 4 seconds, that's up to 240 relays per Ghost in the beam path.

## Compiler Requirements

TODO: Designer specifies: channel duration (4s), beam range (12m), DPS, turn rate (90°/s), caster immobile during channel, interruptible, hits all enemies in path (pass-through). Compiler produces:
- Channel definition with per-tick steering input
- BeamState with direction, turn rate, range
- Per-tick line segment collision query
- Continuous damage application (per-tick, not pulsed)
- Turn rate clamping (smooth rotation, not instant snap)

The compiler needs to support **line-segment geometry** for damage queries, alongside circle (SK-29) and cone (SK-49).

## Open Questions

- Does the beam stop at the first enemy (blocked) or pass through all (penetrating)?
- Does the beam hit static geometry (SK-03 Terrain Wall blocks the beam)?
- Can the beam hit allies (friendly fire)?
- Does beam damage trigger on-hit procs per tick per enemy, or once per enemy per channel?
- Does the beam's DPS scale with cast time (more damage at the end of the channel)?
- How does Kinematic Dilation affect the turn rate (slower rotation in dilated zones)?
- Can the beam interact with SK-59 Oil Ignite (beam passes through oil, ignites it)?
- Does the beam have width (capsule/corridor) or is it zero-width (pure raycast)?
- Performance: per-tick raycast against all entities in range — is this more expensive than radius queries?
- Can two beams from different casters intersect or interact?
