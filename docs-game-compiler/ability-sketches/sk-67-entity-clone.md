# SK-67: Entity Clone

## Designer Intent

I create a temporary clone of an allied hero. The clone has all of the original hero's abilities (at reduced stats — 75% damage, 75% HP). I control the clone for 20 seconds. When the clone expires or dies, I return to my body. The clone cannot use heroic (ultimate) abilities.

## Primitive Composition

P-32 (Actor Spawning) → P-31 (Identity/Loadout Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Cast on ally — a clone of the targeted ally spawns at the caster's position
2. The caster's body disappears (stored, like SK-54 Entity Consumption on self)
3. The player controls the clone as if it were their own hero
4. Clone has 75% of the original hero's max HP and offensive stats
5. Clone has all of the original hero's basic abilities (Q, W, E) but NOT their ultimate (R)
6. Clone abilities use the clone's reduced stats
7. After 20 seconds: clone despawns, caster's body reappears at the clone's position
8. If clone dies: caster's body reappears at the clone's death position
9. The original hero is NOT affected — they keep their abilities and continue playing normally
10. Visual: ghostly/translucent version of the cloned hero

## Engine Primitives Required

### Ability Set Copying

The clone needs the target ally's ability definitions loaded into a new entity. The engine must:
1. Read the target's current ability set from SpellData
2. Create a new entity with those ability definitions (minus ultimate)
3. Apply stat reduction (75% multiplier on all offensive/defensive stats)
4. The clone's abilities reference the SAME SpellData entries as the original

This is different from SK-57 Form Transformation (switching the CASTER's abilities to a predefined alternate set). Here, the ability set is copied from ANOTHER entity at runtime — the caster doesn't know in advance what abilities the clone will have.

### Dynamic Entity Creation From Template

The clone is a new entity whose properties are derived from another entity AT RUNTIME:

```
struct CloneEntity {
    clone_id: EntityID,
    source_entity_id: EntityID,
    controller_entity_id: EntityID,  // The caster who controls the clone
    stat_multiplier: SimFixed,       // 0.75 for 75% stats
    excluded_abilities: Vec<AbilityId>,  // Ultimate excluded
    expires_at_tick: u64,
    controller_body_state: SoftStateSerialized,  // Stored for restoration
}
```

The Arbiter must:
1. Read the source entity's OffensiveStats and DefensiveStats
2. Apply the multiplier to create scaled copies
3. Read the source entity's ability set, exclude ultimates
4. Create the clone entity with these derived properties
5. Remap the caster's Edge Node to control the clone

### Edge Node Control Transfer

The caster's Edge Node must switch from controlling their original entity to controlling the clone. This is similar to SK-61 Spirit Split's control swap, but:
- The clone has a DIFFERENT ability set than the caster's original
- The Edge Node needs to update its UI to reflect the cloned hero's abilities
- On clone death/expiry, control returns to the original entity

### Original Hero Independence

The cloned hero continues playing normally — their entity is not affected. The clone is a COPY, not a transfer. Both the original hero and the clone can exist simultaneously, potentially using the same abilities.

## Cross-Boundary Concerns

TODO: The caster might clone an ally on a different Arbiter:

1. **Clone creation:** Caster on Arbiter A, ally on Arbiter B. Caster needs to read the ally's stats and ability set. If the ally is a Ghost, the Ghost doesn't carry ability/stat data. Arbiter A must request the ally's profile from Arbiter B.

2. **Clone entity location:** The clone spawns at the caster's position (Arbiter A). The clone's ability set is derived from the ally on Arbiter B. But the clone lives and is controlled on Arbiter A.

3. **Data epoch consideration:** The clone's abilities reference SpellData entries. If the ally's abilities were compiled under the current data epoch, the clone uses the same epoch. SK-07 Ability Steal's epoch questions apply here too.

4. **On expiry:** The caster's body reappears at the clone's position. If the clone walked cross-boundary, the caster materializes on a different Arbiter than where they started.

## Compiler Requirements

TODO: Designer specifies: target (ally), clone duration (20s), stat multiplier (0.75), ability copying (all except ultimate), caster body stored during clone, control transfer to clone, on-expiry/death restore caster body at clone position. Compiler produces:
- Clone creation action: read source entity stats/abilities → create scaled entity
- Ability set copying (runtime, not compile-time — the caster can clone different heroes each game)
- Edge Node control transfer
- Caster body serialization/storage (like SK-54 self-consumption)
- Restoration on clone death/expiry

The compiler can define the FRAMEWORK for cloning (stat multiplier, excluded abilities, duration), but the actual abilities are resolved at runtime based on who is cloned.

## Open Questions

- If the original hero changes equipment/stats while the clone is active, does the clone update?
- Can the clone use items/consumables?
- Do the clone's abilities trigger the caster's on-hit procs or the original hero's?
- Can the clone be cloned by another Entity Clone user (clone of a clone)?
- Does the clone inherit the original hero's current buffs/debuffs?
- Can the clone use SK-57 Form Transformation (transform within a clone)?
- If the clone kills an enemy, who gets kill credit — the caster or the original hero?
- Does the clone count toward entity_count for split triggers?
- Can the clone enter SK-60 Bunker?
- How does the ability set copy interact with SK-42 Withering Fire's charge state — does the clone get fresh charges?
