# SK-91: Team-Agnostic Stasis

## Designer Intent

I create a void prison at a target area. After a brief delay, ALL entities inside — enemies AND allies — are put in stasis for 5 seconds. Entities in stasis can't act, can't be damaged, can't be targeted. This is a strategic tool: freeze enemies to set up a combo, but accidentally freezing your own allies is a misplay.

## Primitive Composition

P-33 (Entity Dormancy) → P-27 (Targetability Overrides) → P-13 (Tag/Allegiance Filtering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Cast at target position — visible indicator appears (0.5s delay before activation)
2. After delay: ALL entities in the area enter stasis (friend AND foe, including the caster if inside)
3. Stasis: can't act, invulnerable, untargetable — effectively frozen in time
4. Duration: 5 seconds (not reduced by Tenacity — it's stasis, not CC?)
5. When stasis ends: all affected entities resume exactly where they were
6. Entities OUTSIDE the area when it activates are NOT affected (snapshot at activation)
7. Entities cannot enter the stasis zone after activation (it's a one-time effect, not a persistent zone)
8. The stasis is NOT cleansable (cannot be removed early by any means)
9. Visual: purple crystal prison effect, frozen entities, time-stopped area

## Engine Primitives Required

### Team-Agnostic Targeting

Every existing AoE has a targeting filter:
- `target_filter: Enemies` (SK-29 Blizzard, SK-08 Aura)
- `target_filter: Allies` (SK-16 Holy Ground, SK-20 Battle Cry)

Team-Agnostic Stasis introduces:
- `target_filter: All` — hits EVERY entity regardless of team affiliation

```
enum TargetFilter {
    Enemies,
    Allies,
    AlliesExcludingSelf,
    Self,
    All,            // NEW: all entities, both teams
}
```

The spatial query returns all entities in the area, with no team filtering. The effect is applied to everyone.

### Stasis as a Distinct State

Stasis is stronger than any existing CC:
- Not just stunned (stun still allows taking damage)
- Not just invulnerable (invulnerable can still be CC'd in some cases)
- Not just untargetable (untargetable can still have effects applied by area)

Stasis is the combination of: **can't act + invulnerable + untargetable + all timers paused**.

```
status_effect: StasisDebuff {
    expires_at_tick: u64,
    uncleansable: bool,   // Cannot be removed by SK-15 Purify
}
```

While in stasis:
- `can_move = false, can_attack = false, can_cast = false`
- `is_invulnerable = true`
- `is_untargetable = true`
- All status effect timers are PAUSED (DoTs don't tick, buffs don't expire, cooldowns don't reduce)
- All active channels are interrupted on stasis entry

### Timer Pausing

The most unique aspect of stasis: **time stops for the entity**. All counters, timers, and duration-based effects freeze:
- SK-02 Poison DoT: paused (doesn't tick during stasis, resumes after)
- SK-73 Death Immunity: paused (4-second window doesn't count down)
- SK-46 Adaptation: paused (damage accumulation window frozen)
- SK-88 Positional Leash: paused (duration doesn't tick)
- Ability cooldowns: paused (cooldowns don't reduce during stasis)

This requires the engine to support **per-entity time freeze** — all tick-based timers on the entity stop advancing. When stasis ends, they resume from where they were.

Implementation: rather than actually pausing every timer, the engine could track `stasis_start_tick` and on stasis end, add `stasis_duration` to all timer expiry ticks. This shifts all timers forward by the stasis duration.

### Friendly Fire Implication

The caster's allies can be caught. This means:
- Team coordination matters (don't stand in the void prison area)
- The caster can accidentally stasis their own team (misplay)
- The caster can intentionally stasis allies to protect them (save a low-HP ally by freezing them)

This dual-use (offensive + defensive depending on who's caught) is the strategic depth.

## Cross-Boundary Concerns

TODO: The stasis is a snapshot AoE at activation. All entities in the area at the activation tick are affected — local entities and Ghosts. For Ghosts, the stasis must be relayed to the Ghost's owning Arbiter.

Concern: an ally Ghost is caught in the stasis. The relay reaches the ally's Arbiter and applies stasis. The ally's Arbiter must pause all their timers. Meanwhile, the ally's allies might try to interact with the stasis'd entity — they can't (untargetable).

Timer pausing across boundaries: the stasis'd entity's Arbiter manages the timer pause locally. No special cross-boundary handling needed beyond the initial stasis application relay.

## Compiler Requirements

TODO: Designer specifies: ground-targeted AoE, delay (0.5s), target filter (ALL — both teams), stasis effect (can't act + invulnerable + untargetable + timers paused), duration (5s), not cleansable, snapshot (one-time check at activation). Compiler produces:
- Delayed snapshot AoE with `TargetFilter::All`
- StasisDebuff status effect with timer-pause semantics
- Uncleansable flag (cannot be removed by SK-15 Purify or any dispel)
- Timer shift on stasis end (resume all paused timers)
- Channel interrupt on stasis entry

The compiler adds `All` to the TargetFilter enum and adds Stasis as a distinct state type with timer-pause semantics.

## Open Questions

- Does the caster's own stasis apply if they're in the area? (Yes — consistent with "All" targeting)
- Can SK-51 Unstoppable prevent stasis entry? (Design choice — stasis might be "unstoppable-proof" given its power level)
- Does timer pausing affect SK-37 Time Rewind's rolling buffer (buffer stops recording during stasis)?
- Do effects applied DURING the stasis delay (0.5s warning) persist into stasis?
- Can entities at the edge of the area dodge out during the 0.5s delay?
- If an entity has SK-71 Sticky Bomb and enters stasis, is the bomb timer paused too?
- Does stasis prevent SK-54 Entity Consumption (can't consume a stasis'd entity)?
- If the stasis area overlaps an Arbiter boundary, do entities on both sides get frozen?
- Performance: pausing all timers for N entities simultaneously — is this a batch operation or per-entity?
- Can stasis be used on objectives/structures (freeze a capture point)?
