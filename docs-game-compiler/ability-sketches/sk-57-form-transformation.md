# SK-57: Form Transformation

## Designer Intent

I activate my ultimate ability to transform into a powerful alternate form for 15 seconds. While transformed, my stats change (bonus HP, bonus damage, bonus armor), my abilities are replaced with a different set, and my model/appearance changes. When the duration expires, I revert to my original form with my original abilities.

## Primitive Composition

P-31 (Identity/Loadout Swap) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — caster transforms (instant or brief animation)
2. Stats change: gain bonus max HP (and current HP increases proportionally), bonus damage, bonus armor
3. Ability bar changes: 3-4 abilities are replaced with alternate-form abilities
4. Basic attack may change (different damage, range, speed)
5. Existing buffs/debuffs persist through transformation
6. After 15 seconds: revert to original form, original stats, original abilities
7. If bonus HP exceeded original max HP: current HP is capped at original max HP on revert (no over-heal)
8. Cooldown begins after revert
9. Visual: dramatic transformation animation, different model, visual revert

## Engine Primitives Required

### Stat Block Swap

The entity's OffensiveStats and DefensiveStats change during transformation. This could be implemented as:

**Option A: Stat overlay** — Apply a "transformation buff" that modifies stats additively/multiplicatively:
```
status_effect: TransformationBuff {
    bonus_max_hp: SimFixed,
    bonus_damage_pct: SimFixed,
    bonus_armor: SimFixed,
    duration_ticks: u64,
}
```
Simple, works with existing buff system. But doesn't support ability replacement.

**Option B: Full stat block replacement** — Swap the entity's OffensiveStats/DefensiveStats to a pre-compiled alternate set:
```
status_effect: FormTransformation {
    original_offensive: OffensiveStats,    // Stored for revert
    original_defensive: DefensiveStats,
    alternate_offensive: OffensiveStats,   // Loaded from SpellData
    alternate_defensive: DefensiveStats,
    original_ability_set: AbilitySetId,    // Stored for revert
    alternate_ability_set: AbilitySetId,   // Loaded from SpellData
    expires_at_tick: u64,
}
```
More complex but supports full ability replacement.

### Ability Set Swapping

The entity's available abilities change during transformation. This means:
1. The `validate_intent` hook must reference the CURRENT ability set (original or alternate)
2. Abilities from the wrong set must be rejected
3. Cooldowns for the alternate set are independent (don't share with original abilities)
4. On revert: original ability set is restored with its own cooldown state

The SpellData dictionary needs to contain BOTH ability sets for the entity. The transformation switches which set the adapter hooks reference.

### HP Scaling on Transform/Revert

On transformation:
- Max HP increases (e.g., 4000 → 6000)
- Current HP scales proportionally (if at 50% before, still at 50% after = 3000 HP)

On revert:
- Max HP decreases (6000 → 4000)
- Current HP is capped at new max (if at 5000 during transform, reverts to 4000)
- Or: scale proportionally again (if at 83% during transform = 5000/6000, revert to 83% = 3333/4000)

The HP scaling formula must be explicit and deterministic.

### Death-Triggered Variant

Mekkatorque-style: when the entity's main form reaches 0 HP, instead of dying, they transform into a weaker form. This is Form Transformation triggered by a death event instead of an activation:
- On 0 HP: don't die, instead transform to pilot form (lower stats, different abilities)
- Pilot form has its own HP pool
- If pilot form reaches 0 HP: actually die
- Can earn a new mech to return to mech form

This requires the death resolution pipeline to check "does this entity have a death-transformation effect?" before confirming the kill.

## Cross-Boundary Concerns

TODO: The transformation is local to the entity's Arbiter. The entity's stats change, which affects:
1. Ghost representation — neighbors see the transformed model/stats? Or just position/velocity?
2. If the entity is in combat cross-boundary, the CombatContext carries the CURRENT (transformed) offensive stats. After revert, new combat uses original stats. No special handling needed.
3. If the entity crosses a boundary while transformed, the transformation state (alternate stats, ability set, remaining duration) transfers with the handoff.

## Compiler Requirements

TODO: Designer specifies: two full stat blocks (original form, alternate form), two ability sets (original, alternate), transformation trigger (activation or death), duration, HP scaling formula, revert behavior. Compiler produces:
- Two complete entity profiles in SpellData (one per form)
- FormTransformation status effect that stores/restores the original profile
- Ability set routing in `validate_intent` and subsequent stage execution
- HP scaling logic on transform and revert
- Optional death-trigger variant (intercept death → transform instead)

The compiler needs to support **entity profiles** — named stat/ability configurations that can be swapped at runtime. Each profile is a complete set of OffensiveStats, DefensiveStats, and ability definitions.

## Open Questions

- Can the transformation be cleansed/purged (forced revert to original form)?
- Do cooldowns transfer between forms (if alternate ability 1 is on cooldown, does it affect original ability 1)?
- Can the entity transform while CC'd (stunned in original form → activate transform)?
- Does transformation break CC (self-cleanse on transform, like SK-51 Unstoppable on activation)?
- Does the transformation interact with SK-07 Ability Steal — can someone steal an alternate-form ability?
- If the entity has SK-08 Aura in original form but not in alternate form, does the aura stop during transformation?
- How does the death-triggered variant interact with SK-18 Resurrect — if the mech dies and you eject as pilot, can someone resurrect the mech?
- Can an entity have more than two forms (triple transformation)?
- Does the transformation's stat change affect existing buffs that reference stats (e.g., a buff that gives +10% of max HP as shield — recalculated on transform)?
- Performance: swapping stat blocks + ability sets mid-tick — is this bounded? Does it require recompilation?
