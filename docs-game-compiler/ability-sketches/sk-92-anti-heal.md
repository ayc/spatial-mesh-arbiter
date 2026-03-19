# SK-92: Anti-Heal

## Designer Intent

I throw a grenade at a target area. Enemies hit receive a debuff that reduces all healing they receive by 100% for 2 seconds. Allies hit receive a buff that increases healing received by 25% for 2 seconds. The grenade itself deals damage to enemies and heals allies.

## Primitive Composition

P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted)

## Observable Behavior

1. Grenade lands at target position — AoE affects all entities in radius
2. Enemies: take damage + receive "Healing Blocked" debuff (100% healing reduction, 2 seconds)
3. Allies: receive heal + receive "Healing Amplified" buff (25% bonus healing, 2 seconds)
4. While Healing Blocked: any heal on the target is reduced to 0 (DoT heals, direct heals, passive heals — all blocked)
5. While Healing Amplified: any heal on the target is increased by 25%
6. Both effects are cleansable by SK-15 Purify
7. Visual: purple anti-heal indicator on enemies, green amplification glow on allies

## Engine Primitives Required

### Heal Resolution Modifier

All existing mechanics modify the DAMAGE pipeline (block, reflect, absorb, etc.). Anti-heal modifies the HEAL pipeline. The engine needs a heal resolution path that checks for modifiers:

```
fn resolve_heal(target: &Entity, base_heal: SimFixed) -> SimFixed {
    let mut effective_heal = base_heal;

    // Check for healing modifiers
    for effect in target.active_effects.iter() {
        match effect {
            HealingReduction { percentage } => {
                effective_heal = effective_heal * (SimFixed::ONE - *percentage);
            },
            HealingAmplification { percentage } => {
                effective_heal = effective_heal * (SimFixed::ONE + *percentage);
            },
            _ => {}
        }
    }

    effective_heal = max(SimFixed::ZERO, effective_heal);
    effective_heal
}
```

Every heal source must pass through this resolution: SK-16 Holy Ground pulses, SK-02 Poison Shot drain, SK-18 Resurrect revival HP, SK-46 Adaptation burst heal — ALL heals are affected.

### Dual-Effect AoE

The grenade is a SK-48 Death Coil-style dual-mode ability but as an AoE: enemies receive damage + anti-heal debuff, allies receive heal + amplification buff. The single AoE applies different effects based on target allegiance.

### Interaction With Every Heal Source

Anti-heal must affect ALL healing:
- Direct heals (SK-16 Holy Ground, SK-94 Placed Potion)
- Drain heals (SK-02 Poison Shot drain to caster)
- Passive heals (SK-44 Burrow self-heal)
- Shield-to-heal conversions (if any)
- SK-46 Adaptation burst heal
- SK-93 Death Prevention full heal
- SK-37 Time Rewind HP restoration (is this a "heal" or an HP overwrite? Design choice)

## Cross-Boundary Concerns

TODO: Standard AoE application with relay to Ghost targets. The anti-heal debuff is a status effect on the target's Arbiter. All heal resolution happens locally on the target's Arbiter, so the anti-heal check is local. No special cross-boundary handling beyond initial debuff application.

## Compiler Requirements

TODO: Designer specifies: AoE ground-targeted, enemies (damage + anti-heal 100% for 2s), allies (heal + amplification 25% for 2s), cleansable. Compiler produces:
- Dual-effect AoE (SK-48 dual-mode pattern)
- HealingReduction status effect definition
- HealingAmplification status effect definition
- Heal resolution hook: check for healing modifiers before applying any heal

The compiler needs to add heal modifiers to the status effect system and insert a heal resolution check wherever heals are applied.

## Open Questions

- Does anti-heal affect SK-37 Time Rewind HP restoration (it's an overwrite, not technically a "heal")?
- Does anti-heal affect SK-93 Death Prevention's full heal (death prevention → heal → anti-healed to 0 → entity dies anyway)?
- Does anti-heal affect lifesteal/drain from SK-02 Poison Shot?
- Can healing reduction exceed 100% (healing becomes damage — "heal" deals damage)?
- Do multiple anti-heal debuffs stack (two Ana grenades = 200% reduction)?
- Does anti-heal affect shield generation (SK-70 Energy Shield, SK-17 Sacrifice Shield)?
- Is healing amplification applied before or after healing reduction (order matters if both are active)?
- Does anti-heal affect self-healing differently from external healing?
