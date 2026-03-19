# SK-75: Self-Sustaining Zone

## Designer Intent

I cast a dark feast on a target area. Every second, it erupts dealing damage to all enemies inside. If a pulse hits at least one enemy, the zone persists and pulses again. If a pulse hits ZERO enemies, the zone ends. The zone could theoretically last forever if enemies keep standing in it.

## Primitive Composition

P-32 (Actor Spawning) → P-44 (Pulse Timer) → P-09 (Shape Overlap Query) → P-17 (Conditional Thresholds)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Cast — zone appears at target position (circular, fixed radius)
2. First pulse: deal damage to all enemies inside
3. If pulse hit at least 1 enemy: schedule next pulse in 1 second
4. If pulse hit 0 enemies: zone ends immediately
5. Each subsequent pulse follows the same rule: hit someone → continue, hit nobody → end
6. No maximum duration (bounded only by enemy availability)
7. Enemies can walk in and out — the zone only checks occupancy on pulse ticks
8. Visual: dark maw chomping every second, fades when no targets remain

## Engine Primitives Required

### Conditional Zone Lifecycle

All existing zones have a fixed lifecycle:
- SK-29 Blizzard: fixed 8-second duration
- SK-08 Aura: permanent while caster is alive
- SK-75 Self-Sustaining Zone: **dynamic duration determined by pulse results**

```
struct SelfSustainingZone {
    position: Vec2F,
    radius: SimFixed,
    pulse_interval_ticks: u64,
    next_pulse_tick: u64,
    damage_per_pulse: SimFixed,
    combat_context: CombatContext,
    // No expires_at_tick — zone has no fixed expiry
}
```

Each pulse:
1. Spatial query: enemies within radius
2. If `hit_count > 0`: apply damage to all, set `next_pulse_tick = current_tick + interval`
3. If `hit_count == 0`: despawn zone

The zone has no `expires_at_tick` — it's purely event-driven. It ends when it fails to find targets.

### Unbounded Duration Concern

Without a fixed duration, the zone could persist indefinitely. This creates concerns:
- Entity count: the zone is an actor occupying entity map space permanently
- Memory: the zone's state persists as long as enemies keep entering
- Gameplay: an unattended zone in a high-traffic area could last the entire game

Should the compiler enforce a maximum duration as a safety bound? Or is the "pulse misses → end" rule sufficient?

### Pulse Timing vs Enter/Leave

The zone doesn't use enter/leave detection (unlike SK-29 Blizzard or SK-64 Mosh Pit). It only checks occupancy on pulse ticks — every 1 second. An enemy who enters between pulses takes no damage until the next pulse. An enemy who leaves between pulses avoids the next hit.

This means the zone's effectiveness depends on the TIMING of enemy movement relative to pulse ticks, not continuous presence.

## Cross-Boundary Concerns

TODO: Standard zone cross-boundary pattern. The zone is stationary on one Arbiter. Enemies in the zone that are Ghosts receive damage relays. The only unique concern: the zone's lifecycle depends on hit count. If all local enemies are Ghosts, the "hit count" includes Ghost hits — the zone owner's Arbiter determines "I hit N Ghosts" and keeps the zone alive, even though the actual damage resolution happens on the Ghosts' Arbiters.

Is a Ghost hit counted as a "hit" for sustain purposes? If yes, the zone persists. If the Ghost has since died or moved (stale Ghost data), the zone persists based on stale information. The zone might live one extra pulse beyond its usefulness.

## Compiler Requirements

TODO: Designer specifies: zone shape (circle), radius, pulse interval (1s), damage per pulse, sustain condition (hit_count > 0 → continue, hit_count == 0 → end), no fixed duration. Compiler produces:
- ZoneActor with conditional lifecycle (no fixed expiry)
- Per-pulse hit count check → continue or despawn
- Optional maximum duration safety bound (compiler-enforced)
- Standard AoE damage resolution per pulse

The compiler needs to support **conditional zone lifecycle** — zones whose persistence depends on runtime conditions, not just timers.

## Open Questions

- Should there be a maximum duration cap (e.g., 60 seconds) for safety?
- Does the zone count Ghosts as "hits" for sustain purposes?
- If only one enemy is in the zone and they have SK-44 Burrow (untargetable), does the pulse hit zero and end the zone?
- Does each pulse independently roll crit for each enemy hit?
- Does the zone persist if it only hits SK-17 shields (damage absorbed but not "dealing HP damage")?
- Can the zone's damage trigger on-hit procs for the caster per-pulse per-enemy?
- If the caster dies, does the zone persist (it has no expiry — caster death is the only external termination)?
- Does Kinematic Dilation affect the pulse interval?
- Performance: an indefinite zone doing spatial queries every second — bounded by pulse interval but unbounded in total queries over time
- Can multiple self-sustaining zones from the same caster overlap?
