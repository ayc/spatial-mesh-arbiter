# SK-70: Energy Shield

## Designer Intent

I shield myself (or an ally). The shield absorbs incoming damage as normal. BUT: every point of damage the shield absorbs is converted into Energy — a secondary resource that increases my weapon damage. More damage absorbed = more Energy = stronger attacks. Energy decays over time if not refreshed.

## Primitive Composition

P-18 (Absorption Barrier) → P-21 (Value Conversion) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target: self or ally entity

## Observable Behavior

1. Cast — shield is applied to the target (e.g., 400 HP shield, 3 second duration)
2. Shield absorbs incoming damage normally
3. For each point of damage absorbed: the CASTER gains 1 Energy (secondary resource, max 100)
4. Energy increases the caster's damage output: each point of Energy = +0.5% damage bonus
5. At max Energy (100): caster deals +50% bonus damage
6. Energy decays over time (e.g., 3 Energy per second) if no new damage is absorbed
7. Shield on ally: damage absorbed by the ALLY's shield gives Energy to the CASTER
8. Visual: blue-white shield, caster's weapon glows brighter as Energy increases

## Engine Primitives Required

### Shield-to-Resource Conversion Pipeline

The shield absorption path currently:
1. Incoming damage arrives
2. Check for active shields (consume shield HP before real HP)
3. Apply remaining damage to real HP

Energy Shield adds a step:
1. Incoming damage arrives
2. Check for active shields
3. **Calculate damage absorbed by shield: `absorbed = min(damage, shield_hp)`**
4. **Credit `absorbed` to the caster's Energy resource**
5. Consume shield HP
6. Apply remaining damage to real HP

The shield needs metadata linking it back to the caster:
```
struct EnergyShield {
    shield_hp: SimFixed,
    max_shield_hp: SimFixed,
    expires_at_tick: u64,
    energy_recipient_id: EntityID,  // Who receives the Energy (the caster)
    conversion_rate: SimFixed,      // 1.0 = full conversion, 0.5 = half
}
```

### Cross-Entity Resource Credit

When the shield is on an ALLY, damage absorbed on the ally's Arbiter must credit Energy to the caster — who might be on a different Arbiter. Each time the ally's shield absorbs damage:
1. Calculate absorbed amount
2. If caster is local: credit Energy directly
3. If caster is cross-boundary: relay "credit X Energy to caster" to the caster's Arbiter

This is a per-damage-event cross-boundary relay from the shield bearer to the caster.

### Secondary Resource With Decay

Energy is a secondary resource (like SK-45 Essence, but with continuous decay):

```
struct EnergyState {
    current: SimFixed,
    max: SimFixed,
    decay_per_tick: SimFixed,
    damage_bonus_per_point: SimFixed,
}
```

Each tick: `current = max(0, current - decay_per_tick)`
On damage calculation: `effective_damage = base_damage * (1.0 + current * damage_bonus_per_point)`

### Feedback Loop

This creates a positive feedback loop:
1. Shield absorbs damage → gain Energy → deal more damage
2. Deal more damage → enemies try to focus you → shield absorbs more → gain more Energy

The loop is bounded by:
- Energy max cap (100)
- Shield HP limit (shield is consumed)
- Energy decay (fades without fresh shield absorption)
- Shield cooldown (can't have 100% shield uptime)

## Cross-Boundary Concerns

TODO: Two cross-boundary patterns:

1. **Self-shield:** Caster shields themselves. All absorption and Energy credit are local. No cross-boundary concern.

2. **Ally shield:** Caster on Arbiter A shields an ally on Arbiter B. The shield is applied on Arbiter B. When the ally takes damage, Arbiter B calculates the absorbed amount and relays an Energy credit to Arbiter A. Every damage event on the shielded ally generates a cross-boundary relay to the caster.

If the ally is frequently taking damage (in a teamfight), this could generate many relays. Bounded by: shield HP (once consumed, no more relays) and shield duration (3 seconds).

## Compiler Requirements

TODO: Designer specifies: shield amount, duration, energy conversion rate, energy max, energy decay rate, damage bonus per energy point, self-cast and ally-cast variants. Compiler produces:
- EnergyShield definition with recipient_id for cross-entity credit
- Shield absorption hook: calculate absorbed → credit Energy to recipient
- Energy resource definition with decay per tick
- Damage modifier: read Energy → apply bonus in Phase 1 offense calculation
- Cross-boundary relay for ally-shield Energy credit

The compiler needs to support **shields with absorption callbacks** — shields that do something with the damage they absorb, not just passively consume it.

## Open Questions

- Does Energy credit from ally shields count as "the caster received something" for any other mechanic?
- Can Energy be gained from multiple simultaneous shields (shield self + shield ally)?
- Does the damage bonus from Energy apply to ability damage, auto-attack damage, or both?
- Does Energy persist through death (reset to 0 on death)?
- Can enemies see the caster's Energy level (UI indicator visible to enemies)?
- Does SK-22 Damage Reflection interact — reflected damage hits the shield, absorbed damage credits Energy?
- Does SK-47 Shield Burst's explosion damage scale with Energy (bonus damage affects explosion)?
- If the shield is cleansed (removed by enemies), does the caster keep the Energy already gained?
- Does Kinematic Dilation affect Energy decay rate?
- Can Energy be consumed by other abilities (spend 50 Energy for a special attack)?
