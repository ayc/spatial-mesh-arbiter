# SK-34: Charge

## Designer Intent

My character lowers their shoulder and charges forward in a straight line at high speed. If I collide with an enemy during the charge, they are pinned to me and carried along. The charge ends when I hit a wall — the pinned enemy takes massive impact damage from being slammed into the wall. If no wall is hit, the charge ends after a maximum distance or duration.

## Primitive Composition

P-07 (Entity-as-Kinematic-Volume) → P-02 (Forced Displacement)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Charge direction (from requested aim direction or facing direction)

## Observable Behavior

1. Cast — caster begins charging in the specified direction at high speed
2. Caster cannot steer during the charge (locked direction, no turning)
3. Caster is unstoppable during the charge (immune to CC? or reduced CC? Design choice)
4. If caster collides with an enemy entity: enemy is "pinned" — attached to the caster's position and carried along
5. Only the first enemy hit is pinned (subsequent enemies are knocked aside for minor damage)
6. If caster hits a wall with a pinned enemy: charge ends, pinned enemy takes X impact damage + Y wall-slam bonus damage
7. If caster hits a wall with no pinned enemy: charge ends, caster takes a brief self-stun (recovery frames)
8. If no wall is hit: charge ends after max distance or max duration (e.g., 3 seconds)
9. On charge end: pinned enemy is released at the caster's current position
10. Visual: dust trail, shoulder-down running animation, wall impact crater

## Engine Primitives Required

TODO: This introduces several new concepts:

### Caster as Projectile
The caster's own entity moves at charge speed, overriding normal movement input. The Arbiter needs to:
1. Lock the caster's movement to the charge vector (ignore player input)
2. Apply charge velocity each tick via `apply_kinematics`
3. Run collision detection against the caster's moving hitbox — both against entities (capture check) and static geometry (wall impact check)

This is different from normal entity movement because the speed exceeds normal movement caps and the caster is treated as a moving collision source, not just a receiver.

### Entity Pinning
When the caster hits an enemy, the enemy is "attached" to the caster:
1. Enemy's position is locked to caster's position (offset by collision geometry)
2. Enemy's movement input is suppressed (effectively a specialized stun)
3. Enemy moves wherever the caster moves — they share a physics body temporarily
4. The pin is a status effect on the enemy with a reference to the caster's EntityID

How is this represented? A status effect that overrides the entity's position each tick to match the caster's position plus an offset?

### Wall Impact Detection
The charge needs to detect "caster hit static geometry" as a distinct event that triggers:
1. Stop the charge
2. Apply wall-slam damage to the pinned enemy
3. Apply self-stun to the caster
4. Release the pinned enemy

This is different from normal collision (which just prevents movement through walls). Here, wall collision is a gameplay trigger, not just a physics boundary.

## Cross-Boundary Concerns

TODO: The caster is moving at high speed, potentially crossing Arbiter boundaries during the charge. Two scenarios:

1. **Caster crosses boundary alone (no pinned enemy yet):** Normal entity handoff, but mid-ability. The charge state (direction, speed, remaining duration) must transfer with the entity. The new Arbiter continues the charge.

2. **Caster crosses boundary WITH a pinned enemy:** Two entities must hand off simultaneously. The pinned enemy's position is derived from the caster's — they can't be on different Arbiters. Does the engine support atomic two-entity handoffs? If not, there's a brief window where the caster is on the new Arbiter and the pinned enemy is still on the old one.

Additionally: at charge speed, the caster might cross multiple boundaries in quick succession. Each crossing is a handoff.

## Compiler Requirements

TODO: Designer specifies: charge speed, charge direction (requested aim direction/facing), max duration/distance, collision behavior (pin first enemy, knock aside others), wall impact damage, self-stun on wall hit without pin, CC immunity during charge. Compiler produces: self-displacement state machine + entity capture mechanic + wall collision trigger + damage payloads. This is a complex multi-phase ability with conditional branching (hit enemy → pin → find wall vs. hit wall alone vs. charge expires).

## Open Questions

- Can the charge be interrupted by hard CC (stun, sleep), or is the caster unstoppable?
- If the caster is rooted (SK-25) before charging, does root prevent the charge?
- What happens if the pinned enemy is cleansed (SK-15 Purify) mid-charge — are they released?
- Can the caster charge through SK-03 Terrain Wall, or does it count as a wall for impact purposes?
- If the pinned enemy is a Ghost (owned by another Arbiter), how does the pin work? Does the Ghost become a real entity on the caster's Arbiter?
- Does the charge interact with SK-31 Vortex — can a charging caster be pulled off course?
- Can the caster charge off map edges or into deep terrain?
- What happens if the caster charges into SK-29 Blizzard — do they take damage while charging through?
- Does the knocked-aside damage (non-pinned enemies) trigger on-hit procs?
- Can two chargers collide head-on? What happens — both stop? One wins? Mutual stun?
