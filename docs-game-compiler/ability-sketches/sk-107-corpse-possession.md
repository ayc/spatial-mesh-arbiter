# SK-107: Corpse Possession

## Designer Intent

When an enemy champion dies near me, I can interact with their corpse to BECOME them temporarily. I take over their body — gaining their model, abilities, and items — for 10 seconds. My own body is stored. After the duration (or on reactivation), I revert to my original form at the corpse's position.

## Primitive Composition

P-47 (Spatial Corpse Registry) → P-31 (Identity/Loadout Swap) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target: a recently dead enemy champion's corpse (must be in range)

## Observable Behavior

1. Enemy champion dies near me — their corpse is available for 8 seconds
2. I interact with the corpse — my body disappears, I become the dead enemy
3. I have their model, their abilities (Q/W/E — not ultimate), and their items/stats
4. My HP is set to the dead enemy's max HP (I start at full HP in their body)
5. I can move, attack, and use their abilities freely for 10 seconds
6. After 10 seconds (or reactivation): I revert to my original form at my current position
7. On revert: my original HP is restored (as it was before possession)
8. If I die during possession: I revert to my original form with a brief untargetable phase
9. Visual: take on the dead enemy's appearance, dark aura to distinguish from the real champion

## Engine Primitives Required

### Dead Entity Data Persistence

Currently, when an entity dies, its data (abilities, stats, items) is lost — the entity is removed from the Arbiter. For Corpse Possession to work, the dead entity's data must persist for a window after death:

```
struct CorpseData {
    entity_id: EntityID,
    character_id: UUID,
    death_position: Vec2F,
    death_tick: u64,
    ability_set: AbilitySetId,        // Which abilities the dead entity had
    offensive_stats: OffensiveStats,   // Their stats at time of death
    defensive_stats: DefensiveStats,
    items: Vec<ItemInstance>,          // Their equipment (affects stats)
    corpse_ttl_tick: u64,             // How long the corpse is available
}
```

The Arbiter must retain `CorpseData` after entity removal. This is a new retention requirement — dead entities leave behind a data snapshot that can be accessed by gameplay abilities.

### Ability Set Loading From Corpse

When the caster possesses the corpse:
1. Read the corpse's `ability_set`
2. Load those ability definitions from SpellData
3. Replace the caster's current ability set with the corpse's
4. Replace the caster's stats with the corpse's offensive/defensive stats
5. Store the caster's original state for restoration

This is like SK-67 Entity Clone (copy abilities from another entity) but:
- Source is DEAD (not living)
- Source is an ENEMY (not an ally)
- The caster BECOMES the source (model swap, not new entity creation)
- Items are included (SK-67 doesn't consider items)

### Body Storage and Restoration

Like SK-54 Entity Consumption (self-consumption) and SK-57 Form Transformation:
1. Serialize the caster's original state (SoftState, stats, ability set, position, HP)
2. Store it on the entity
3. Apply the corpse's data
4. On revert: restore original state

```
struct PossessionState {
    original_soft_state: SoftStateSerialized,
    original_offensive: OffensiveStats,
    original_defensive: DefensiveStats,
    original_ability_set: AbilitySetId,
    original_hp: SimFixed,
    corpse_source_id: EntityID,
    expires_at_tick: u64,
}
```

### Model/Visual Swap

The caster's entity visually becomes the dead enemy. The downstream payload must send the corpse's model/appearance data to all Edge Nodes. This is like SK-86 Decoy's per-team visual deception but applied to the caster's own entity — everyone sees the caster as the dead enemy.

Unlike SK-86 (enemies see a fake, allies see the real thing), possession makes the caster look like the enemy to EVERYONE. Allies might need a subtle indicator to distinguish (similar to SK-86's ally indicator).

### Item/Stat Integration

The corpse's items affect their stats. If the game has an item system, the possessed form uses the dead enemy's items:
- Their weapon (determines auto-attack damage)
- Their armor (determines defensive stats)
- Their unique item effects (passives, on-hit effects from items)

This means the Arbiter must be able to load another entity's item set and resolve abilities using those items' stats.

## Cross-Boundary Concerns

TODO: The corpse data might be on a different Arbiter than the caster:

1. **Enemy dies on caster's Arbiter:** CorpseData is local. Possession is straightforward.
2. **Enemy dies on a different Arbiter (Ghost dies):** The corpse data is on the enemy's Arbiter, not the caster's. The caster needs to access remote corpse data. Options:
   - The death event includes corpse data broadcast to nearby Arbiters (large payload)
   - The caster's Arbiter requests corpse data from the dead entity's Arbiter
   - Possession is only available for entities that died on the caster's Arbiter

3. **During possession, crossing boundaries:** The caster (in possessed form) moves normally. Handoff transfers the current entity state (possessed stats/abilities, stored original state). On the new Arbiter, the entity continues in possessed form.

4. **Revert on different Arbiter:** If the caster moved cross-boundary during possession, they revert on the new Arbiter. The original body materializes at the current position, not the corpse position.

## Compiler Requirements

TODO: Designer specifies: interact with dead enemy corpse (within range, within 8s of death), become the dead enemy (model, abilities minus ultimate, stats, items), duration (10s), revert on expiry/reactivation/death, original state stored and restored, start at full HP in possessed form. Compiler produces:
- CorpseData retention after entity death (new data lifecycle)
- Corpse interaction definition (proximity, timer, team filter)
- Ability set + stat loading from CorpseData
- Body storage (serialize original state)
- Restoration on expiry/reactivation/death
- Model swap for downstream payloads

The compiler needs to support **dead entity data access** — a new capability where abilities can read a dead entity's stats, abilities, and items.

### docs-core/ Impact

This may require a `docs-core/` change:
- Entity lifecycle must support a "corpse data retention" phase between death and full removal
- The durability bridge must define how long corpse data persists and what it contains

## Open Questions

- Does the possessed form use the caster's level or the dead enemy's level?
- Does the possessed form have the dead enemy's cooldowns (fresh) or their pre-death cooldowns?
- Can the caster possess the same corpse twice (if the ability comes off cooldown before the corpse despawns)?
- Can the caster's allies heal the possessed form? Is the possessed form on the caster's team or the enemy's team?
- Do on-hit procs from the dead enemy's items work during possession?
- If the dead enemy had SK-46 Adaptation active at death, does the possessed form inherit it?
- Can the possessed form use SK-69 Portal Pair (team affiliation question)?
- Does the corpse data include the dead enemy's current buffs/debuffs at death?
- If the caster has SK-08 Aura, does the aura persist during possession (caster's passive, not the corpse's)?
- Can multiple casters attempt to possess the same corpse? First-come-first-served?
- How does the corpse data interact with the data_epoch — corpse's abilities use the epoch active at their death?
