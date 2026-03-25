# T3-05: Threat Table & Leash Mechanics

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/04-npc-and-world-interaction.md`

## Problem Statement

NPC archetypes reference aggro, threat tables, and leash mechanics but no formulas are provided.

## Resolution

### 1. Threat Formula

```
threat_generated = (damage_dealt × threat_multiplier) + flat_threat
```

| Source | `threat_multiplier` | `flat_threat` | Notes |
|--------|:---:|:---:|---|
| Direct damage | 1.0 | 0 | Base: 1 threat per 1 damage |
| Healing (on ally in combat) | 0.5 | 0 | Half threat, split among all enemies in combat with the healed target |
| Taunt ability (SK-65) | 0.0 | current_top_threat × 1.1 | Forces aggro swap by setting threat 10% above current leader |
| AoE damage | 1.0 per target | 0 | Full threat per target hit |
| CC application | 0.0 | 100 | Flat threat for applying crowd control |
| Buff on ally | 0.25 | 0 | Low threat, split among enemies in combat |
| Resurrection | 0.0 | 500 | High flat threat for reviving |

`threat_multiplier` can be modified by game-adapter buffs (e.g., tank stance = 2.0× threat, rogue passive = 0.7× threat). These are P-16 (Stat Layering) modifiers evaluated during Stage 11.

### 2. Threat Decay

| Mode | Rate | Condition |
|------|------|-----------|
| In-combat | 0 (no decay) | While any entity on the threat table is within aggro range |
| Out-of-combat | 100% instant reset | When ALL threat sources leave aggro range or die |
| Death penalty | Threat zeroed for the dead entity | On entity death — removes them from the table |
| Range penalty | -5% per tick beyond aggro range | Entity is alive but out of range — threat bleeds over ~1.3 seconds to zero |

### 3. Aggro Swap Threshold

The NPC does NOT instantly swap targets when another entity gains more threat. A **swap threshold** prevents jittery target changes:

```
swap_required = current_target_threat × (1.0 + swap_threshold_pct)
```

| NPC Type | `swap_threshold_pct` | Notes |
|----------|:---:|---|
| Standard monster | 10% | Must exceed current target by 10% |
| Boss / elite | 20% | Harder to pull aggro from tank |
| Add / minion | 0% | Swaps immediately to highest threat |

If `challenger_threat > swap_required`, the NPC swaps to the challenger. Otherwise, it stays on the current target. Evaluated once per NPC decision tick (Tier 0: every tick, Tier 1: every 6 ticks).

### 4. Leash Mechanics

**Leash anchor:** The NPC's spawn point (or current patrol waypoint, if on patrol).

**Leash range:** Per-archetype configurable value (default: 40 units).

```rust
struct LeashConfig {
    anchor:         Vec2F,      // Spawn point or current patrol waypoint
    max_range:      SimFixed,   // Default: 40.0
    return_speed:   SimFixed,   // Speed when returning (default: 2.0× normal move speed)
}
```

**Leash trigger:** When the NPC's position exceeds `max_range` from its anchor:
1. NPC enters `Evading` state.
2. NPC becomes untargetable (P-27) and immune to damage.
3. NPC moves toward anchor at `return_speed`.
4. Threat table is fully cleared.
5. On reaching anchor (within 1.0 unit): NPC enters `Idle` state, HP resets to max, all status effects removed.

**Player perspective:** The boss "resets" — runs back to its spawn, heals to full, and threat is gone. Standard MMO leash behavior.

### 5. Leash + Dilation Interaction

Under kinematic dilation, the NPC's movement speed is dilated (`speed × dilation_factor`). This means:
- Leash return takes longer in dilated zones
- The leash range check uses absolute spatial distance (not dilated distance)
- A dilated NPC in Evading state still returns at `return_speed × dilation_factor`

### 6. Configuration

```json
"threat": {
    "healing_threat_multiplier": 0.5,
    "cc_flat_threat": 100,
    "buff_threat_multiplier": 0.25,
    "resurrect_flat_threat": 500,
    "range_decay_per_tick": 0.05,
    "default_swap_threshold_pct": 0.10,
    "boss_swap_threshold_pct": 0.20
},
"leash": {
    "default_max_range": 40.0,
    "default_return_speed_multiplier": 2.0,
    "arrival_tolerance": 1.0
}
```

## References

- `docs/3-gameplay-systems/04-npc-and-world-interaction.md` — NPC archetypes, state machines
- `docs/1-architecture/02-npc-architecture.md` — Runtime tiers, AI Node archetypes
- `docs-game-compiler/ability-primitives/02-targeting-query.md` — P-13 Tag/Allegiance Filtering (for combat membership)
