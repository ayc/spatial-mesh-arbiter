# SK-78: Fear

## Designer Intent

I terrify all nearby enemies for 2 seconds. Feared enemies run away from me uncontrollably — they cannot choose their direction, they just flee. They can't attack, cast, or control their movement during fear.

## Primitive Composition

P-03 (Trajectory Steering) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the fear source)
- No target required (AoE centered on caster)

## Observable Behavior

1. Cast — all enemies within radius are feared for 2 seconds
2. Feared enemies automatically run directly away from the caster's position
3. Feared enemies cannot move voluntarily, attack, or cast (full disable + forced movement)
4. The flee direction is calculated relative to the caster's position at the moment of application (not updated per-tick)
5. If a feared enemy hits a wall, they stop moving but remain feared (can't act)
6. Duration reduced by Tenacity
7. Subject to Diminishing Returns (SK-28) — hard CC category
8. Cleansable by SK-15 Purify
9. Visual: purple terror effect, enemy runs with panic animation

## Engine Primitives Required

### New CC Type: Fear (Forced Flee)

Fear combines hard disable (can't act) with forced movement (involuntary direction):

| CC Type | Can Move? | Can Attack? | Can Cast? | Movement Override? |
|---|---|---|---|---|
| Stun (SK-24) | No | No | No | None (frozen) |
| Sleep (SK-27) | No | No | No | None (frozen) |
| Taunt (SK-65) | Yes (free) | Yes (forced target) | Yes | None |
| Mind Control (SK-40) | Yes (caster-directed) | No | No | Caster steers |
| **Fear (SK-78)** | **Yes (forced away)** | **No** | **No** | **Auto-flee from source** |

```
status_effect: FearDebuff {
    fear_source_position: Vec2F,  // Position of caster at time of application
    flee_direction: Vec2F,        // Pre-calculated: normalize(target.pos - source.pos)
    flee_speed: SimFixed,         // Movement speed during fear (100% of target's base speed)
    expires_at_tick: u64,
}
```

Each tick while feared:
1. Entity's movement is overridden to `flee_direction * flee_speed`
2. Collision detection applies normally (wall stops movement)
3. No voluntary input accepted (movement, abilities, auto-attacks all blocked)

### Flee Direction: Static vs Dynamic

Two options:
- **Static (recommended):** Flee direction is calculated once at application and doesn't change. The feared entity runs in a straight line away from where the caster WAS. Simple, deterministic.
- **Dynamic:** Flee direction updates per tick based on the caster's CURRENT position. The feared entity continuously recalculates "away from caster." More realistic but more expensive (requires tracking the caster's position per tick, potentially cross-boundary).

Static is standard for most games and avoids cross-boundary position tracking.

### Forced Movement + Collision

The feared entity moves at full speed in the flee direction. If they hit a wall:
- Stop moving (collision prevents further movement)
- Remain feared (can't act — they just stand there trembling against the wall)
- If the wall is a corner, they might slide along it (standard collision response)

Forced movement respects the same collision system as voluntary movement. SK-03 Terrain Wall blocks feared entities.

## Cross-Boundary Concerns

TODO: Fear is applied as a standard CC via AoE. Enemies near the boundary who are Ghosts receive the fear via relay. The feared entity's Arbiter manages the forced flee movement locally — no per-tick cross-boundary dependency (if using static flee direction).

If a feared entity runs across a boundary during their flee, the fear effect transfers with the handoff. The flee direction is a static vector, so it works on any Arbiter.

## Compiler Requirements

TODO: Designer specifies: AoE radius, duration (2s), forced flee direction (away from caster), full disable (no move/attack/cast control), flee speed (100% base), static direction, Tenacity-reducible, DR category (hard CC), cleansable. Compiler produces:
- Snapshot AoE query for enemies in radius
- FearDebuff status effect with pre-calculated flee_direction
- Per-tick movement override (flee_direction * flee_speed)
- Full capability suppression (can_move=false for voluntary, can_attack=false, can_cast=false)
- Collision-aware forced movement

The compiler adds Fear to the CC type system alongside Stun, Root, Silence, Sleep, Slow, Blind, Taunt.

## Open Questions

- Does SK-51 Unstoppable prevent fear (yes — CC immunity)?
- Does fear break on damage (like SK-27 Sleep) or persist regardless?
- If the feared entity has SK-23 Thorns, does thorns trigger on melee hits during fear?
- Can a feared entity be displaced by OTHER abilities (SK-01 Toss overrides fear direction)?
- Does fear interact with SK-31 Vortex — vortex pulls inward, fear pushes outward. Who wins?
- If the feared entity is rooted (SK-25), does fear override the root (forced movement) or does root prevent fear movement?
- Does the flee direction account for the entity's position at fear start, or the caster's position?
- Can SK-65 Taunt override fear (taunt says "attack me," fear says "run away from me")?
- Does fear push the entity toward danger (off cliffs, into SK-29 Blizzard zones)?
