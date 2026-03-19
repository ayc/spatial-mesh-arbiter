# SK-111: Soulbind

## Designer Intent

I link two enemy heroes together with dark magic for 8 seconds. Any single-target ability that hits one of them ALSO hits the other. Stun one → both stunned. Silence one → both silenced. The link doubles the impact of every targeted ability against the pair.

## Primitive Composition

P-34 (Persistent Linkage) → P-60 (Event Cloning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- First target: enemy hero (hit by the ability)
- Second target: nearest enemy hero within range of the first (auto-selected)

## Observable Behavior

1. Cast hits first enemy — dark tether links them to the nearest other enemy hero
2. For 8 seconds: any single-target ability that hits either linked enemy also hits the other
3. Stun on A → B is also stunned (same duration)
4. Damage ability on A → B also takes the damage (same amount, using same CombatContext)
5. Heal reduction on A → B also gets heal reduction
6. AoE abilities are NOT duplicated (only single-target)
7. The link is one-way per ability: ability hits A, duplicates to B. It does NOT bounce back (no infinite loop)
8. Both entities can be linked for the full duration — breaking LOS doesn't break the link
9. Visual: dark chain connecting both enemies, mirrored effect visuals on both

## Engine Primitives Required

### Targeted Ability Duplication

After a single-target ability resolves on entity A (who has a Soulbind link to entity B), the engine must:
1. Detect: entity A just had a single-target ability resolved on them
2. Check: does entity A have a Soulbind link?
3. If yes: REPLAY the same ability resolution on entity B
4. The replay uses the SAME parameters (same CombatContext, same CC duration, same effect)

```
status_effect: SoulbindLink {
    linked_entity_id: EntityID,
    expires_at_tick: u64,
}
```

### Ability Resolution Replay

The engine needs to capture the "input" of a single-target ability resolution and replay it on a second entity. This is NOT "deal the same damage" — it's "resolve the same ability":
- If the ability was a stun + damage: both entities get stunned + damaged
- If the ability was a heal reduction: both entities get heal reduction
- The damage on B uses B's OWN defensive stats (not A's mitigation result)

The replay is a NEW resolution of the same ability against a different target:
```
fn on_ability_resolved(target: &Entity, ability: &ResolvedAbility) {
    if let Some(link) = target.find_effect::<SoulbindLink>() {
        let linked = get_entity(link.linked_entity_id);
        resolve_ability_on_target(linked, ability.original_params);
    }
}
```

### Single-Target vs AoE Classification

The duplication only applies to SINGLE-TARGET abilities. AoE abilities are not duplicated (they already hit both if both are in the area). The engine must classify each ability resolution:
- **Single-target**: one specific entity was targeted. Duplicated by Soulbind.
- **AoE**: area-based, hits all entities in area. NOT duplicated.

The compiler must tag abilities as `targeting_type: SingleTarget | AoE | Self` so the Soulbind check knows whether to duplicate.

### Loop Prevention

If both A and B have Soulbind links to each other (symmetrical), an ability on A duplicates to B, which would duplicate back to A → infinite loop. The engine must prevent this:
- Flag the replayed resolution as "soulbind-replayed"
- Soulbind duplication only fires on ORIGINAL resolutions, not on replays

```
fn on_ability_resolved(target: &Entity, ability: &ResolvedAbility, is_soulbind_replay: bool) {
    if is_soulbind_replay { return; }  // Don't re-duplicate
    if let Some(link) = target.find_effect::<SoulbindLink>() {
        resolve_ability_on_target(linked, ability.original_params, is_soulbind_replay: true);
    }
}
```

## Cross-Boundary Concerns

TODO: Entity A on Arbiter X, entity B on Arbiter Y. A single-target ability hits A on Arbiter X.

1. Arbiter X resolves the ability on A
2. Arbiter X checks: A has Soulbind → linked to B
3. Arbiter X must relay "replay this ability on entity B" to Arbiter Y
4. Arbiter Y resolves the ability on B using B's defensive stats

The relay carries the ability's original parameters (not A's resolution result). B gets an independent resolution.

This is one relay per single-target ability hit on either linked entity — bounded by ability cast rate.

## Compiler Requirements

TODO: Designer specifies: link two enemies (8s), single-target abilities on one hit both, AoE not duplicated, no infinite loop, link persists through distance/LOS. Compiler produces:
- SoulbindLink status effect on both entities (symmetrical)
- Post-resolution hook: check for link → replay on linked entity
- Single-target vs AoE classification on all abilities
- Loop prevention flag on replayed resolutions
- Cross-boundary replay relay

The compiler adds `targeting_type` to all ability definitions and adds a post-resolution duplication hook to the ability pipeline.

## Open Questions

- Does the duplicated ability use the original caster's offensive stats or re-roll with the original caster's stats?
- Does the duplicated ability trigger on-hit procs (SK-09 Chain Lightning on B's hit)?
- Can Soulbind duplicate Soulbind application (applying Soulbind on A duplicates to B → B also gets Soulbound to... who?)
- Does the duplication work with SK-14 Execute Threshold (execute on A duplicates to B)?
- Does SK-51 Unstoppable on entity B prevent the duplicated CC?
- Can SK-15 Purify cleanse the Soulbind link?
- If the linked entity dies, does the link transfer to another nearby enemy?
- Does the link duplicate beneficial effects (ally heals one → the other is also healed)?
- How does the link interact with SK-104 Zone-Conditional Invulnerability (ability from outside the zone hits A inside, duplicates to B outside)?
