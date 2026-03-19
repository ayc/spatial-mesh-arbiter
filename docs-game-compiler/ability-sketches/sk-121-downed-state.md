# SK-121: Downed State

## Designer Intent

When my HP reaches 0, I don't die immediately. Instead, I enter a Downed State — I collapse to the ground with a new, smaller HP pool and 4 limited abilities. I can crawl slowly and try to fight back. My teammates can channel on me to RALLY me (revive to partial HP). Enemies can channel on me to FINISH me (instant kill). If I manage to kill an enemy while downed, I self-rally automatically. If my downed HP reaches 0, I actually die.

## Primitive Composition

P-39 (On-Death Hook) → P-25 (Multi-Phase Vitals) → P-31 (Identity/Loadout Swap) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Entity reaches 0 HP (automatic transition)
- Downed abilities (4 new limited abilities)
- Ally interaction: channel to rally (revive)
- Enemy interaction: channel to finish (execute)

## Observable Behavior

1. Main HP reaches 0 → enter DOWNED STATE (not dead)
2. Downed state has its own HP pool (e.g., 30% of max HP)
3. While downed: can crawl slowly (25% movement speed)
4. While downed: ability bar replaced with 4 downed abilities (weak attack, self-heal, CC, last resort)
5. While downed: allies can channel on you for 3 seconds to RALLY you (restore to 25% main HP)
6. While downed: enemies can channel on you for 2 seconds to FINISH you (instant kill, bypasses everything)
7. If you kill an enemy while downed (with downed abilities): SELF-RALLY (auto-revive to 25% HP)
8. If downed HP reaches 0 (enemies damage you while downed): ACTUALLY DIE (death event, respawn flow)
9. If rallied: return to standing with 25% main HP, all main abilities restored
10. Visual: character on the ground, crawling animation, rally/finish progress bars

## Engine Primitives Required

### Three-Phase Health System

The current entity lifecycle is: Alive (HP > 0) → Dead (HP ≤ 0). Downed State adds a middle phase:

```
enum EntityLifePhase {
    Alive,       // Main HP pool, full abilities
    Downed,      // Downed HP pool, limited abilities
    Dead,        // Entity removed, respawn flow
}

struct DownedState {
    downed_hp: SimFixed,
    max_downed_hp: SimFixed,
    downed_ability_set: AbilitySetId,
    rally_channel_ticks: u64,      // Time for ally to rally
    finish_channel_ticks: u64,     // Time for enemy to finish
    downed_movement_speed: SimFixed, // 25% of normal
}
```

The death check is modified:
```
fn check_death(entity: &mut Entity) -> bool {
    if entity.hp <= SimFixed::ZERO {
        match entity.life_phase {
            Alive => {
                // Don't die — transition to downed
                entity.life_phase = Downed;
                entity.downed_state.downed_hp = entity.downed_state.max_downed_hp;
                swap_ability_set(entity, entity.downed_state.downed_ability_set);
                entity.movement_speed = entity.downed_state.downed_movement_speed;
                return false;  // Not dead yet
            },
            Downed => {
                if entity.downed_state.downed_hp <= SimFixed::ZERO {
                    entity.life_phase = Dead;
                    return true;  // Actually dead now
                }
                return false;
            },
            Dead => return true,
        }
    }
    false
}
```

### Downed HP as Separate Pool

While downed, damage targets `downed_hp` instead of `hp`:
- `hp` stays at 0 (the entity's main health is depleted)
- `downed_hp` is the new health bar
- When `downed_hp` reaches 0: entity transitions to Dead

All damage resolution redirects to `downed_hp` during the Downed phase:
```
fn apply_damage_to_entity(entity: &mut Entity, damage: SimFixed) {
    match entity.life_phase {
        Alive => entity.hp -= damage,
        Downed => entity.downed_state.downed_hp -= damage,
        Dead => {}  // Can't damage dead entities
    }
}
```

### Downed Ability Set

While downed, the entity's abilities are replaced with a limited downed set:
- Ability 1: Weak attack (low damage projectile/melee)
- Ability 2: Self-heal (small, slow heal on downed HP)
- Ability 3: CC (knockback or daze to push enemies away)
- Ability 4: Last resort (high damage, long cooldown, or area denial)

The ability set swap uses the same mechanism as SK-57 Form Transformation. The validate_intent hook checks `life_phase == Downed` and routes to the downed ability set.

### Rally Mechanic (Ally Channel to Revive)

Allies can channel on a downed entity to rally them:
1. Ally starts channeling (like SK-18 Resurrect but target is downed, not dead)
2. Channel duration: 3 seconds (interruptible)
3. On complete: downed entity transitions back to Alive with 25% main HP
4. Ability set reverts to normal
5. Movement speed reverts to normal

Multiple allies can rally simultaneously (channel progress stacks? Or first to complete wins?).

### Finish Mechanic (Enemy Channel to Execute)

Enemies can channel on a downed entity to finish them:
1. Enemy starts channeling (interruptible)
2. Channel duration: 2 seconds (shorter than rally — offense advantage)
3. On complete: downed entity transitions to Dead (bypasses downed HP — instant kill)
4. Like SK-114 Piercing Execute but delivered as a channel

The finish is an execution mechanic specifically for downed entities.

### Self-Rally on Kill

If the downed entity kills an enemy (using their downed abilities):
1. Automatic rally: transition back to Alive with 25% main HP
2. No channel needed — instant
3. Creates a dramatic comeback opportunity

The engine must check: on enemy death, was the killer in Downed state? If yes, trigger self-rally.

### Interaction With Death Prevention Mechanics

How does the Downed State interact with existing death mechanics?
- **SK-73 Death Immunity**: Prevents main HP from reaching 0 → never enters Downed State (HP floors at 1)
- **SK-93 Death Prevention**: Prevents death by healing to full → prevents entering Downed State (main HP restored before transition)
- **SK-114 Piercing Execute**: Bypasses everything → entity goes straight to Dead, skipping Downed
- **SK-96 Death Ghost**: If entity is Downed and then downed HP reaches 0 → Dead → THEN Death Ghost activates

## Cross-Boundary Concerns

TODO: The downed entity remains on their Arbiter. They can crawl slowly (minimal movement, unlikely to cross boundaries). Rally/finish channels from nearby allies/enemies are local interactions.

If the downed entity crawls across a boundary: the Downed state (downed HP, downed abilities, life phase) transfers with the handoff. The new Arbiter continues the downed phase.

If an ally on a different Arbiter wants to rally: they need to walk to the downed entity's position. The rally channel is a proximity interaction — standard cross-boundary interaction if the ally is a Ghost.

## Compiler Requirements

TODO: Designer specifies: downed HP (30% of max HP), downed ability set (4 abilities), downed movement speed (25%), rally (ally channel 3s → revive at 25% HP), finish (enemy channel 2s → kill), self-rally on kill, transition Alive → Downed on main HP = 0, transition Downed → Dead on downed HP = 0. Compiler produces:
- DownedState entity component (optional — some entities might not have downed state)
- Three-phase life cycle: Alive → Downed → Dead
- Downed ability set definitions in SpellData
- Death check modification: intercept at main HP = 0, transition to Downed instead
- Damage routing: target downed_hp during Downed phase
- Rally interaction definition (ally channel → revive)
- Finish interaction definition (enemy channel → kill)
- Self-rally hook (on kill while downed → revive)

### docs-core/ Impact

This likely requires a `docs-core/` change:
- The entity lifecycle model must support a three-phase health system (Alive → Downed → Dead)
- The death pipeline must support interception at the Downed transition, not just at death prevention
- The game adapter must be able to define per-entity downed state parameters

## Open Questions

- Can a downed entity be healed by allies (healing downed HP without a rally channel)?
- Does being rallied trigger any immunity window (prevent immediate re-downing)?
- Can a downed entity use items/consumables?
- Does the downed entity generate aggro (PvE: do monsters keep attacking a downed player)?
- Can downed entities be affected by AoE damage (SK-29 Blizzard damages downed HP)?
- Can a downed entity be displaced (SK-01 Toss a downed ally to safety)?
- Does SK-91 Stasis affect downed entities (frozen while downed)?
- Can multiple allies rally the same downed entity simultaneously (faster rally)?
- Is the downed state optional per entity type (bosses don't enter downed state, players do)?
- Does Kinematic Dilation affect rally/finish channel times?
- Can the downed entity enter SK-44 Burrow while downed (invulnerable in downed state)?
- Does the downed ability set benefit from the entity's normal stats, or are downed abilities fixed?
