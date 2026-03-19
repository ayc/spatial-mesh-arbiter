# SK-33: Shifting Sands

## Designer Intent

I cast a sandstorm zone that starts at a target position and slowly drifts in a direction over 6 seconds. Enemies caught inside have their movement speed reduced by 40% and take damage every second. The zone moves independently — I don't control it after casting.

## Primitive Composition

P-32 (Actor Spawning) → P-03 (Trajectory Steering) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted, zone start position)
- Drift direction (caster-to-target vector, or explicit angle)

## Observable Behavior

1. Sandstorm zone appears at target position (circular, fixed radius)
2. Zone begins drifting in the specified direction at a constant speed
3. Every 1 second: enemies inside take X damage and are slowed by 40%
4. As the zone moves, new enemies are caught and previously-inside enemies may escape
5. Zone travels for 6 seconds then dissipates
6. Caster is free to act — zone is autonomous after cast
7. Visual: moving sandstorm cloud, visibility reduction inside the zone

## Engine Primitives Required

TODO: This is a **ZoneActor with velocity** — unlike SK-29 Blizzard (stationary) or SK-08 Aura (attached to entity), this zone moves independently along a vector. Each tick, the zone's position updates: `zone.position += zone.velocity * dt`. The spatial query for "who's inside" must use the zone's CURRENT position, not its spawn position.

The ZoneActor struct needs:
- `position: Vec2F` (changes each tick)
- `velocity: Vec2F` (constant drift vector)
- `radius: SimFixed`
- Pulse timer and damage/debuff payload

This is a new capability — existing ZoneActors are either stationary or attached to an entity. A self-propelled zone is a third mode.

## Enter/Leave Detection

TODO: Because the zone moves, entities can enter and leave without moving themselves — the zone passes over them. The enter/leave detection must account for both entity movement and zone movement. Each tick:
1. Update zone position
2. Query enemies within new radius
3. Diff against previous tick's occupants
4. Apply effects to new entrants, remove effects from those who left

This is more expensive than a stationary zone because the occupant set changes every tick even if no entities move.

## Cross-Boundary Concerns

TODO: A moving zone can cross Arbiter boundaries during its lifetime. At spawn, it's on one Arbiter. As it drifts, it may enter a neighbor's region. Does the zone get handed off like a projectile (3-phase handoff protocol)? Or does it stay on the original Arbiter and relay effects to Ghosts? If it drifts entirely out of the original Arbiter's region, the original Arbiter can't query for local entities in the zone — they're all in the neighbor's region now.

This is architecturally similar to the projectile handoff problem but for a zone with area (not a point). The handoff protocol may need to account for zone geometry.

## Compiler Requirements

TODO: Designer specifies: zone shape (circle), radius, drift velocity (speed + direction), duration (6s), pulse interval (1s), damage per pulse, slow per pulse (40%), targeting filter (enemies). Compiler produces: ZoneActor with velocity field + per-tick position update + pulse behavior + enter/leave tracking. The compiler needs to distinguish three zone mobility modes: stationary, entity-attached, self-propelled.

## Open Questions

- Can the drift direction be curved (arc) or only linear?
- Does the zone accelerate, decelerate, or maintain constant speed?
- If the zone hits static geometry (wall), does it stop, pass through, or deflect?
- Can multiple Shifting Sands zones overlap, and do their slows stack?
- How does the zone interact with SK-31 Vortex — does the vortex pull the zone, or only entities?
- When the zone crosses an Arbiter boundary, is this a full handoff or a relay arrangement?
- Does the zone inherit the caster's offensive stats at cast time (epoch-pinned like projectiles)?
- If the caster dies, does the zone persist?
- Performance: moving zone = changing occupant set every tick = N spatial queries per second. What's the entity count bound?
- Can enemies use SK-03 Terrain Wall to block the zone's path?
