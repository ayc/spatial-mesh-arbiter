# SK-113: Hit-Count Shield

## Designer Intent

I gain a shield that blocks the next 6 instances of damage. Each attack that would damage me is completely negated — whether it deals 10 damage or 10,000 damage. After 6 hits are blocked, the shield breaks and I take damage normally.

## Primitive Composition

P-19 (Instance Barrier)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (self-cast)
- No target

## Observable Behavior

1. Activate — gain Hit-Count Shield with 6 charges
2. Each instance of damage: shield absorbs the ENTIRE hit (regardless of damage amount), lose 1 charge
3. Hit 1: blocked (5 charges remain)
4. Hit 2: blocked (4 charges remain)
5. ... Hit 6: blocked (0 charges remain, shield breaks)
6. Hit 7: normal damage (shield gone)
7. Duration: 17 seconds or until all charges consumed
8. Visual: crystalline shield layers, one layer shatters per hit

## Engine Primitives Required

### Charge-Based Shield (Not HP-Based)

SK-17 Sacrifice Shield absorbs based on DAMAGE AMOUNT (shield_hp). Hit-Count Shield absorbs based on HIT COUNT (charges):

```
struct HitCountShield {
    remaining_charges: u8,
    max_charges: u8,
    expires_at_tick: u64,
}
```

On incoming damage:
```
fn apply_damage_with_hit_shield(entity: &mut Entity, damage: SimFixed) {
    if let Some(shield) = entity.find_effect::<HitCountShield>() {
        if shield.remaining_charges > 0 {
            shield.remaining_charges -= 1;
            if shield.remaining_charges == 0 {
                entity.remove_effect(shield.effect_id);  // Shield breaks
            }
            return;  // ENTIRE hit absorbed, regardless of amount
        }
    }
    // Normal damage resolution
    entity.hp -= damage;
}
```

### Shield Ordering With HP-Based Shields

If an entity has BOTH a Hit-Count Shield and an HP-Based Shield (SK-17), which is checked first?
- **Hit-Count first**: the hit is absorbed by a charge, HP-shield is untouched. Optimal for the defender.
- **HP-Shield first**: the HP-shield absorbs damage, Hit-Count charge is NOT consumed. Suboptimal.

Design choice: typically Hit-Count shields are checked BEFORE HP-based shields (they're more valuable per-charge for large hits).

### What Counts As "One Hit"?

The definition of "one instance of damage" matters:
- Single auto-attack: 1 hit (1 charge consumed)
- SK-29 Blizzard pulse: 1 hit per pulse (1 charge per second)
- SK-09 Chain Lightning: 1 hit per chain bounce that reaches this entity (1 charge)
- SK-02 Poison Shot DoT tick: 1 hit per tick (1 charge per tick — DoTs shred the shield fast)
- SK-10 Crit Explosion: 1 hit (the explosion is one damage event)

DoTs are particularly effective against Hit-Count shields — a 5-tick DoT consumes 5 charges (one per tick), while dealing minimal damage per tick. This is intentional counterplay.

### Interaction With Damage Resolution Pipeline

The Hit-Count Shield check should happen EARLY in Phase 2 — before mitigation, before HP-shields, before reflection:
1. Check Hit-Count Shield → if charges remain, absorb entirely, skip everything else
2. If no Hit-Count Shield (or no charges): proceed with normal resolution (block check, shield absorption, mitigation, etc.)

This means a blocked hit doesn't trigger:
- SK-22 Damage Reflection (no damage to reflect)
- SK-23 Thorns (debatable — entity was "hit" but took no damage)
- SK-87 Conditional Counter (entity was hit — does the counter trigger?)
- SK-70 Energy Shield (no damage absorbed by HP-shield, so no Energy gain)

## Cross-Boundary Concerns

TODO: The Hit-Count Shield is a local status effect on the entity's Arbiter. All damage resolution (including charge consumption) is local. No special cross-boundary handling.

## Compiler Requirements

TODO: Designer specifies: self-cast, charges (6), blocks one hit per charge regardless of damage amount, duration (17s), breaks when charges = 0. Compiler produces:
- HitCountShield status effect with charge counter
- Damage interception: consume charge, negate entire hit
- Shield ordering rule (before HP-based shields)
- Expiry on timer or charge depletion

The compiler adds a new shield type alongside HP-based shields. The damage resolution pipeline must support both types with explicit ordering.

## Open Questions

- Does a blocked hit consume a charge from BOTH Hit-Count Shield AND SK-17 HP-Shield (if both active)?
- Do DoT ticks each consume a charge (making DoTs effective counters)?
- Does SK-114 Piercing Execute ignore Hit-Count Shield (pierces everything)?
- Does a blocked hit trigger SK-87 Conditional Counter (entity was "hit" even though no damage)?
- Does a blocked hit trigger SK-23 Thorns (entity was "hit by melee")?
- Does SK-92 Anti-Heal interact (anti-heal affects healing, not hit absorption)?
- Can the shield be purged by enemies (SK-15 Purify in reverse)?
- Does each hit from a multi-hit ability (SK-52 Combo Strike) consume one charge per hit?
- Does the shield block damage from SK-109 Movement Damage (each tick of movement damage = one charge)?
- Does the shield work against true/pure damage?
