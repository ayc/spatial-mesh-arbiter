# SK-62: Boomerang

## Designer Intent

I unleash fire waves that travel outward from me in all directions. After reaching max range, the waves reverse direction and return to me. Enemies can be hit on the way out AND on the way back — potentially taking damage twice.

## Primitive Composition

P-32 (Actor Spawning) → P-03 (Trajectory Steering) → P-35 (On-Hit Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (fires in all directions from caster)

## Observable Behavior

1. Cast — fire waves launch outward from the caster in multiple directions (e.g., 8 waves in a radial pattern)
2. Waves travel outward at constant speed, damaging enemies they pass through
3. At max range: waves stop, reverse direction, and travel back toward the caster
4. On the return trip: waves damage enemies again (double-hit possible)
5. Waves disappear when they reach the caster's CURRENT position (which may have moved)
6. Each enemy can be hit once per direction (once on outward, once on return — max 2 hits)
7. Visual: fire waves rippling outward then collapsing back inward

## Engine Primitives Required

### Reversing Projectile

Standard projectiles travel in one direction until they hit something or expire. Boomerang projectiles have a **two-phase trajectory**:

```
enum BoomerangPhase {
    Outbound { remaining_distance: SimFixed },
    Returning { target_position: Vec2F },
}
```

Phase 1 (outbound): travel in initial direction at constant speed until max range.
Phase 2 (returning): reverse velocity, travel toward the caster's CURRENT position (homing return).

The return is homing — the caster may have moved since the waves were cast. The return trajectory adjusts each tick to track the caster's position.

### Double-Hit Prevention

Each wave maintains two hit lists:
- `outbound_hits: HashSet<EntityID>` — entities hit on the way out
- `return_hits: HashSet<EntityID>` — entities hit on the way back

An entity can be in BOTH lists (hit twice — once per direction) but cannot be in the same list twice (no double-hit within a single direction).

### Multi-Projectile Spawn

The ability spawns multiple projectiles simultaneously (e.g., 8 waves in radial directions). Each is an independent ProjectileActor with its own trajectory and hit list. The Arbiter must handle N simultaneous projectile spawns in a single tick.

### Return Homing

On phase transition to `Returning`, the projectile switches to homing behavior:
- Target: the caster's EntityID (not a position — the caster moves)
- Each tick: recalculate velocity toward the caster's current position
- Despawn when the projectile reaches within contact range of the caster

If the caster dies or becomes untargetable (SK-44 Burrow) during the return, the waves should continue to the caster's last known position and then despawn.

## Cross-Boundary Concerns

TODO: The waves travel outward, potentially crossing boundaries, then return. A wave that crosses a boundary on the outbound trip needs to be handed off. On the return trip, it crosses back — another handoff. A single wave could require two handoffs (out and back).

The return phase homes toward the caster. If the caster is on Arbiter A and the wave was handed off to Arbiter B during outbound, the return phase needs to home toward a Ghost (the caster from B's perspective). Ghost position accuracy affects return trajectory precision.

Multi-projectile spawns near boundaries: 8 waves in all directions — some go into neighbor territory. Multiple simultaneous handoffs.

## Compiler Requirements

TODO: Designer specifies: radial pattern (8 directions), outbound range, damage per hit, pass-through (hits all enemies, not just first), double-hit (once per direction), return homing to caster, despawn on reaching caster. Compiler produces:
- N ProjectileActors with radial direction vectors
- Two-phase trajectory (outbound → return)
- Per-direction hit list dedup
- Return homing targeting caster EntityID
- Despawn condition (reach caster or caster gone)

## Open Questions

- Can the waves be blocked by SK-03 Terrain Wall?
- Does each wave's return damage use the same CombatContext as outbound (epoch-pinned at cast)?
- Can each hit (outbound and return independently) trigger on-hit procs?
- If the caster blinks (SK-35/SK-36) during return phase, do the waves adjust trajectory?
- Can the caster be hit by their own returning waves (self-damage)?
- Does each wave have its own collision radius, or are they zero-width lines?
- How many total collision checks per tick: 8 waves × enemies in path × 2 directions?
- If a wave is mid-return and crosses a boundary, does the handoff preserve the return homing target?
