# SK-83: Next-Cast Empowerment

## Designer Intent

I activate my trait to empower my next ability. The next Q, W, or E I cast will be enhanced — more damage, larger AoE, additional effects, or modified behavior. The empowerment is consumed on the next ability cast. If I don't cast within 6 seconds, the empowerment expires unused.

## Primitive Composition

P-16 (Stat Layering) → P-40 (On-Cast Intercept)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Trait activation (separate from Q/W/E)
- Then: any ability cast consumes the empowerment

## Observable Behavior

1. Activate trait — gain "Empowered" buff
2. Next Q cast while empowered: enhanced Q (e.g., larger AoE, extra damage)
3. OR next W cast while empowered: enhanced W (e.g., spreads to additional targets)
4. OR next E cast while empowered: enhanced E (e.g., stuns instead of slows)
5. The empowerment is consumed on the first ability cast
6. Only ONE ability is empowered per trait activation
7. If 6 seconds pass without casting: empowerment expires (wasted)
8. Trait has its own cooldown separate from Q/W/E
9. Visual: glowing hands indicator, enhanced ability has flashier visual effect

## Engine Primitives Required

### Cross-Ability Modifier Buff

This is the first ability where a **buff modifies OTHER abilities' resolution**. Existing buffs modify stats (attack speed, damage, movement speed) or suppress capabilities (CC). This buff modifies the BEHAVIOR of the next ability used.

```
status_effect: EmpowermentBuff {
    expires_at_tick: u64,
    consumed: bool,
    // Per-ability enhancement definitions:
    q_enhancement: Option<AbilityModifier>,
    w_enhancement: Option<AbilityModifier>,
    e_enhancement: Option<AbilityModifier>,
}

enum AbilityModifier {
    DamageMultiplier(SimFixed),
    RadiusMultiplier(SimFixed),
    AddEffect(StatusEffectDefinition),  // e.g., add stun to an ability that normally doesn't stun
    ReplacePayload(ActionPayload),      // Completely different ability behavior
}
```

### Resolution Hook Integration

When the `resolve_external` hook processes an ability:
1. Check: does the caster have an EmpowermentBuff?
2. If yes: look up the enhancement for this specific ability
3. Apply the modifier to the ability's resolution (bigger AoE, more damage, extra CC)
4. Consume the buff (remove it, mark as used)
5. If no: resolve normally

The enhancement must be checked BEFORE the ability resolves — it modifies the resolution parameters, not the outcome.

### Selective Enhancement

Each ability (Q, W, E) has a DIFFERENT enhancement. The empowerment buff must carry per-ability modifier data. The compiler pre-defines what each ability looks like when empowered. At runtime, the Arbiter reads the modifier for the specific ability being cast.

This is different from a flat damage buff (which affects all abilities equally). The empowerment is ability-specific and can fundamentally change behavior (add CC, change targeting, etc.).

## Cross-Boundary Concerns

TODO: Minimal. The empowerment buff is on the caster's entity (local SoftState). When the caster casts an empowered ability targeting a Ghost (cross-boundary), the enhanced CombatContext is pre-rolled on the caster's Arbiter with the modifier applied, then relayed normally. The target's Arbiter doesn't need to know the ability was empowered.

## Compiler Requirements

TODO: Designer specifies: trait activation (applies empowerment buff), per-ability enhancements (Q: bigger AoE, W: extra targets, E: add stun), buff duration (6s), consumed on first ability cast, one empowerment per activation. Compiler produces:
- EmpowermentBuff status effect with per-ability modifiers
- Per-ability enhancement definitions (how each ability changes when empowered)
- Resolution hook: check for empowerment → apply modifier → consume
- Two versions of each ability in SpellData: normal and empowered (or: one version with conditional modifier)

The compiler needs to support **ability modifiers** — data that transforms an ability's parameters at resolution time based on active buffs. This is a general mechanism that could support many "enhance next cast" patterns.

## Open Questions

- Can the empowerment be consumed by auto-attacks, or only Q/W/E abilities?
- If SK-12 Spell Echo triggers, does the echo also benefit from the empowerment (consumed on first cast, echo is the second)?
- Can enemies cleanse the empowerment buff (removing it before it's used)?
- If the caster is silenced (SK-26) while empowered, does the timer keep ticking (wasting the empowerment)?
- Can multiple empowerment buffs stack (activate trait twice quickly)?
- Does the empowered ability have a different cooldown than the normal version?
- How does the UI communicate which abilities are enhanced (all three glow? Or just a generic indicator)?
- Can SK-67 Entity Clone use the empowerment (clone has the caster's buffs)?
- Does the empowerment modify the ability BEFORE or AFTER other damage modifiers (SK-14 Execute Threshold)?
