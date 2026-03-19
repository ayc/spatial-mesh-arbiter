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
3. The target takes X damage per second while the beam is on them
4. All enemies within AoE radius of the target ALSO take damage (collateral)
5. The beam moves at a speed slightly slower than normal movement (target can kite it)
6. If the target moves fast enough, the beam falls behind — dealing damage at the beam's position, not the target's
7. The beam persists for 8 seconds regardless of line of sight or distance
8. The caster can act freely after casting (fire and forget)
9. If the target dies, the beam dissipates early
10. Visual: golden beam from the sky, scorched ground, follows the target

## Engine Primitives Required

### Target-Following Zone

All existing zone mobility modes:
- **Stationary** (SK-29 Blizzard): fixed position, never moves
- **Caster-attached** (SK-08 Aura): follows the caster's position
- **Self-propelled** (SK-33 Shifting Sands): moves along a vector independently
- **Target-tracking** (SK-99): follows a specific ENEMY entity's position

```
struct TargetTrackingZone {
    zone_id: EntityID,
    tracked_entity_id: EntityID,
    tracking_speed: SimFixed,      // Max movement speed of the zone per tick
    aoe_radius: SimFixed,
    damage_per_tick: SimFixed,
    combat_context: CombatContext,  // Pre-rolled at cast time
    expires_at_tick: u64,
}
```

Each tick:
1. Read the tracked entity's current position
2. Calculate direction from zone's current position toward the tracked entity
3. Move the zone toward the target at `tracking_speed` (may not reach the target if target moves fast)
4. Spatial query: all enemies within `aoe_radius` of the zone's CURRENT position
5. Apply damage to all results (including the tracked target if the zone caught up)

### Tracking vs Locking

Two design options:
- **Locked on target (always on top):** The zone's position = target's position. No escape. This makes it a glorified DoT with collateral AoE.
- **Tracking with speed limit (can be kited):** The zone chases the target but has a max speed. If the target runs faster than the tracking speed, the zone falls behind. The target can outrun it but the beam still deals damage at its current position.

Option 2 is more interesting gameplay — the target can kite the beam and the beam's AoE damages the path, not just the target. This creates a "leaving a trail of destruction" effect as the beam chases.

### Zone Position vs Target Position

With speed-limited tracking, the zone has its OWN position that's distinct from the target's:
- `zone.position` moves toward `target.position` each tick, capped by tracking_speed
- Damage is dealt at `zone.position`, not `target.position`
- If the target stands still, the zone catches up and stays on top of them
- If the target runs, the zone trails behind

This means the zone is effectively a self-propelled zone (like SK-33) whose velocity is recalculated each tick to aim at the target.

### Target Death Handling

If the tracked target dies:
- The zone loses its tracking target
- Options: dissipate immediately, or continue moving in the last known direction for remaining duration
- Design choice: dissipate is simplest and prevents "orphan beam" edge cases

## Cross-Boundary Concerns

TODO: The zone tracks an enemy that can cross Arbiter boundaries:

1. **Target on same Arbiter as zone:** Zone tracks the target's position directly. Simple.
2. **Target crosses to different Arbiter:** Target becomes a Ghost. The zone tracks the Ghost's position (approximate, dead-reckoned). Zone stays on the original Arbiter.
3. **Zone chasing target toward boundary:** If the zone itself crosses a boundary (following the target), it needs a handoff. The zone is an entity that moves — standard entity handoff applies.
4. **Both cross boundary:** The zone follows the target. Both may end up on the same new Arbiter, or the zone might lag behind (on the old Arbiter) tracking a Ghost.

The key question: does the zone stay on one Arbiter and track via Ghost position, or does it hand off to follow the target? For an 8-second zone, staying put and using Ghost positions is simpler. The tracking speed limit means the zone moves slowly — it might not even reach the boundary.

## Compiler Requirements

TODO: Designer specifies: target (enemy hero), tracking speed (slightly less than normal move speed), AoE radius, DPS, duration (8s), fire-and-forget (caster is free), dissipate on target death. Compiler produces:
- TargetTrackingZone entity with tracked_entity_id
- Per-tick tracking: move toward target's position at capped speed
- Per-tick AoE damage at zone's current position
- Target death hook: dissipate zone
- CombatContext pre-rolled at cast time

The compiler adds a fourth zone mobility mode: `Tracking { target_id, speed }` alongside Stationary, CasterAttached, and SelfPropelled.

## Open Questions

- Does the tracking zone follow the target through SK-44 Burrow (target is untargetable but has a position)?
- If the target enters SK-91 Stasis, does the zone catch up and sit on them (they can't move)?
- Can the tracking zone be blocked by SK-03 Terrain Wall (zone stops at the wall)?
- Does the AoE damage hit allies of the caster who are near the target (friendly fire)?
- Can the tracking zone be dispelled/destroyed?
- Does the tracking zone trigger on-hit procs for the caster per tick per enemy?
- If the target uses SK-35 Blink Strike (instant teleport), does the zone snap to the new position or smoothly track toward it?
- Can the caster redirect the zone to a different target mid-duration?
- Does the zone's tracking speed scale with Kinematic Dilation?
- Performance: per-tick tracking calculation + AoE spatial query for 8 seconds — bounded?
