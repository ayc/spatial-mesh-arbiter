# SK-43: Drag

## Designer Intent

I shoot my tongue out in a line. If it hits the first enemy in its path, I latch on and drag them toward me over 1.75 seconds. During the drag, I can move — and the enemy is pulled toward wherever I currently am. If I miss, the ability goes on a short cooldown. If I hit, full cooldown after the drag completes.

## Primitive Composition

P-02 (Forced Displacement) → P-34 (Persistent Linkage)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (skillshot — from requested aim direction)

## Observable Behavior

1. Tongue launches as a line projectile in the cast direction
2. Tongue travels at high speed — hits the FIRST enemy entity in its path (skillshot)
3. If no enemy is hit before max range: tongue retracts, short cooldown (e.g., 6s)
4. If enemy is hit: latch on — enemy is dragged toward the caster over 1.75 seconds
5. During the drag: the caster CAN move. The drag destination moves with the caster.
6. During the drag: the target cannot act (hard CC — functionally a stun)
7. The target is pulled along a direct line toward the caster's current position each tick
8. At the end of the drag: target is released at their current position, near the caster
9. Visual: tongue extending out, latching, enemy being reeled in

## Engine Primitives Required

### Skillshot (First-Hit Line Collision)
This is the first sketch testing a **non-targeted, non-pass-through projectile**. The tongue projectile:
- Travels in a straight line from the caster in the cast direction
- Checks for collision with enemy entity hitboxes along its path each tick
- Detonates on the FIRST entity hit (not pass-through like SK-41, not targeted like SK-02)
- If no entity is hit by max range, the projectile expires (miss)

This is the classic "skillshot" pattern. The engine's ProjectileActor needs a collision mode:
```
enum ProjectileCollisionMode {
    Targeted { target_id: EntityID },     // Homes toward target (SK-02)
    PassThrough,                          // No entity collision (SK-39, SK-41)
    FirstHit,                             // Detonates on first entity in path (SK-43)
    Pierce { max_hits: u8 },              // Hits multiple entities along path
}
```

`FirstHit` uses the same raycast/capsule sweep as normal collision detection but returns only the first intersection.

### Pull Toward Moving Entity
On hit, the target enters a forced-movement state where each tick:
1. Calculate direction vector from target toward caster's CURRENT position
2. Move target along that vector at pull speed
3. Caster can move freely during this time — pull destination updates every tick

This is different from:
- SK-31 Vortex (pull toward a FIXED point)
- SK-01 Toss (one-time displacement along a predetermined arc)
- SK-34 Charge (caster moves, carries pinned entity)

In Drag, the target moves independently toward the caster — they're not pinned to the caster's position. If the caster moves away, the target follows at pull speed. If the caster moves toward the target, they close distance faster.

```
status_effect: DragLatch {
    puller_id: EntityID,      // The caster — pull destination updates from their position
    pull_speed: SimFixed,
    remaining_ticks: u64,
}
```

Each tick during the drag, the target's Arbiter must:
1. Look up the puller's position (might be local entity or Ghost)
2. Calculate pull vector
3. Override the target's movement with the pull vector

## Cross-Boundary Concerns

TODO: The pull destination is the caster's position, which the target's Arbiter needs each tick. Scenarios:

1. **Both on same Arbiter:** Simple — puller's position is local.
2. **Target on Arbiter A, caster on Arbiter B:** The target's Arbiter sees the caster as a Ghost. It pulls the target toward the Ghost's position. Ghost position updates are UDP/dead-reckoned — some position lag. The pull direction might be slightly stale.
3. **Target is pulled across a boundary toward the caster:** Entity handoff mid-drag. The drag effect must survive the handoff. After handoff, the target is on the caster's Arbiter — now both are local.
4. **Caster moves away across a boundary during drag:** Caster hands off to a new Arbiter. Now the caster is a Ghost from the target's perspective. Pull continues using Ghost position.

The cross-boundary pull is a per-tick dependency on another entity's position — similar to SK-04 Tether's distance check but more critical (it drives movement, not just a break condition).

## Compiler Requirements

TODO: Designer specifies: skillshot projectile (direction, speed, max range, FirstHit collision), on-hit effect (apply DragLatch to target), drag parameters (pull speed, duration 1.75s, target fully disabled), miss behavior (short cooldown). Compiler produces:
- ProjectileActor with `CollisionMode::FirstHit`
- On-hit: apply DragLatch status effect to the hit target
- DragLatch: per-tick pull toward `puller_id`'s position + hard CC
- Two cooldown paths: hit (full cooldown) vs miss (short cooldown)

## Open Questions

- Does the drag respect static geometry — can you pull an enemy through a wall?
- If you pull an enemy through SK-29 Blizzard, do they take damage from the zone?
- Can the drag be cleansed by SK-15 Purify (ally cleanses the target mid-drag)?
- Does Tenacity reduce the drag duration?
- What happens if two Drag abilities latch the same target simultaneously?
- If the caster is stunned during the drag, does the drag continue (target keeps being pulled)?
- Can the dragged entity be hit by other abilities mid-drag, or are they untargetable during displacement?
- Does the drag trigger Diminishing Returns (SK-28) as a hard CC?
- If the tongue hits a Ghost, is the latch relayed to the Ghost's owning Arbiter? Does the drag begin on the target's Arbiter or the caster's?
- Can the tongue hit non-hero entities (minions, summons from SK-06)?
