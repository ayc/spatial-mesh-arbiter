# SK-117: Stagger Bar

## Designer Intent

Boss enemies have a secondary bar above their HP — the Stagger Bar. My abilities deal stagger damage alongside regular HP damage. When the team depletes the stagger bar, the boss is STAGGERED: stunned for a long duration and takes increased damage. If we don't deplete the bar fast enough, it regenerates and we miss the window. Coordinating stagger damage is a core raid mechanic.

## Primitive Composition

P-48 (Secondary Stagger Bar) → P-26 (Capability Bitmask) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Multiple attacker entities (team effort)
- Target entity (boss/elite with a stagger bar)
- Each ability has a stagger value (alongside its normal damage value)

## Observable Behavior

1. Boss spawns with a full Stagger Bar (e.g., 1000 stagger HP)
2. Players use abilities — each ability deals normal HP damage AND stagger damage to the bar
3. High-stagger abilities (big slow swings) deal more stagger; fast abilities deal less
4. As the bar depletes, visual indicator shows progress (bar turning yellow → orange → red)
5. If stagger bar reaches 0: boss enters STAGGER STATE for 5 seconds (stunned + 20% damage vulnerability)
6. After stagger state ends: stagger bar resets to full
7. If players don't deplete the bar within a time window (e.g., 30 seconds): bar regenerates to full (failed check)
8. Some boss phases have MANDATORY stagger checks — failure triggers a wipe mechanic
9. Visual: visible stagger bar under HP bar, screen shake on stagger, boss collapse animation

## Engine Primitives Required

### Secondary Breakable Bar

The entity state gains a new resource bar alongside HP:

```
struct StaggerBar {
    current: SimFixed,
    max: SimFixed,
    regen_rate_per_tick: SimFixed,     // Regeneration when not taking stagger damage
    regen_delay_ticks: u64,            // Ticks after last stagger damage before regen starts
    last_stagger_tick: u64,
    is_staggered: bool,
    stagger_duration_ticks: u64,
    damage_vulnerability_bonus: SimFixed,  // e.g., 0.20 for 20% bonus damage during stagger
}
```

### Stagger Damage as a Parallel Damage Channel

Every ability has TWO damage values:
- `hp_damage: SimFixed` — normal damage to the entity's HP
- `stagger_damage: SimFixed` — damage to the entity's stagger bar

Both are calculated and applied during the same damage resolution:
```
fn resolve_damage(target: &mut Entity, hp_damage: SimFixed, stagger_damage: SimFixed) {
    // Normal HP damage resolution (shields, mitigation, etc.)
    apply_hp_damage(target, hp_damage);

    // Stagger damage — separate resolution, may have its own mitigation
    if let Some(bar) = &mut target.stagger_bar {
        bar.current = max(SimFixed::ZERO, bar.current - stagger_damage);
        bar.last_stagger_tick = current_tick();

        if bar.current == SimFixed::ZERO && !bar.is_staggered {
            trigger_stagger(target);
        }
    }
}
```

### Stagger State

When the stagger bar is depleted:
1. Entity enters STAGGER STATE (effectively a stun — SK-24)
2. All actions are disabled (can't move, attack, cast)
3. Damage vulnerability is applied (all incoming damage increased by bonus %)
4. Duration is fixed (5 seconds)
5. On expiry: stagger bar resets to max, entity resumes acting

The stagger state is like a CC but it's triggered by a RESOURCE DEPLETION, not by a CC ability. It's not subject to Tenacity or DR (SK-28) — it's a mechanical check, not a CC effect.

### Stagger Regeneration

The stagger bar regenerates when not taking stagger damage:
- If `current_tick - last_stagger_tick > regen_delay_ticks`: begin regenerating
- Regen rate: `bar.current += regen_rate_per_tick` each tick
- Regen stops when bar reaches max or when new stagger damage is dealt

This creates a DPS CHECK — the team must deal enough stagger damage to outpace regeneration and deplete the bar before the regen delay kicks in.

### Per-Ability Stagger Value

The compiler must assign a `stagger_damage` value to every ability alongside `hp_damage`:
- Heavy, slow abilities: high stagger (e.g., 150)
- Light, fast abilities: low stagger (e.g., 30)
- Some abilities: zero stagger (DoTs, certain magic abilities)

This is a new field on every ability definition in SpellData.

### Team-Wide Contribution

Unlike most combat mechanics (one attacker vs one defender), the stagger bar is a SHARED TARGET for the entire team. All players' stagger damage contributes to the same bar. This creates coordination pressure — "everyone use your high-stagger abilities NOW."

The engine doesn't need special handling for this — all damage events from all sources naturally reduce the same bar. The team coordination is emergent from the shared resource.

## Cross-Boundary Concerns

TODO: The stagger bar is on the boss entity's Arbiter. Players on different Arbiters attack the boss:
1. Local players: stagger damage applied directly to the bar
2. Cross-boundary players (boss is a Ghost? or players relay damage to boss's Arbiter): stagger damage relays alongside HP damage

In a raid scenario, the boss is likely on one Arbiter with many players nearby. Cross-boundary concerns are minimal unless the boss is near an Arbiter boundary with players on both sides. Standard damage relay carries both HP damage and stagger damage.

## Compiler Requirements

TODO: Designer specifies: per-entity stagger bar (max value, regen rate, regen delay), per-ability stagger damage value, stagger state on depletion (stun + vulnerability + duration), bar reset after stagger, optional mandatory stagger check (failure triggers wipe). Compiler produces:
- StaggerBar as an optional entity component (only on bosses/elites)
- Per-ability `stagger_damage` field in SpellData
- Damage resolution: apply HP damage + stagger damage in parallel
- Stagger state trigger on bar depletion
- Regeneration logic with delay timer
- Downstream payload: stagger bar value for client rendering

The compiler adds a new optional entity component and a new field on every ability definition.

## Open Questions

- Does stagger damage go through the same mitigation as HP damage (armor reduction)?
- Can shields (SK-17) absorb stagger damage, or only HP damage?
- Does SK-114 Piercing Execute instantly deplete the stagger bar?
- Can stagger damage be reflected (SK-22) or thorned (SK-23)?
- Does SK-92 Anti-Heal affect stagger bar regeneration (anti-heal reduces healing, stagger regen isn't healing)?
- Can players' stagger contributions be individually tracked (for scoring/contribution meters)?
- Does SK-110 Mute disable the boss's stagger bar regeneration (it's a passive)?
- Can the stagger bar have multiple depletion thresholds (half-stagger at 50%, full stagger at 0%)?
- Does Kinematic Dilation affect stagger bar regeneration rate?
- Can the stagger bar exist on player entities (PvP stagger mechanic)?
