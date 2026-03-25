# SK-116: Charge-Finisher

## Designer Intent

My martial arts abilities are split into two categories: charge-up skills and finishing moves. Charge-up skills build charges (up to 3). Each charge-up skill does minor damage AND adds 1 charge to a shared pool. When I'm ready, I use a finishing move — it CONSUMES all charges and deals a powerful effect that scales with the number of charges consumed. More charges = stronger finisher.

## Primitive Composition

P-50 (Typed Multi-Charge Pool) → P-42 (Stacking Counters w/ Decay)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Charge-up abilities: standard targeted attacks that also build charges
- Finisher abilities: consume all accumulated charges for an empowered effect

## Observable Behavior

1. Use Fists of Fire (charge-up): deal minor fire damage + gain 1 charge (max 3)
2. Use Claws of Thunder (charge-up): deal minor lightning damage + gain 1 charge (now at 2)
3. Use Blades of Ice (charge-up): deal minor cold damage + gain 1 charge (now at 3)
4. Use Dragon Talon (finisher): consume all 3 charges → kick with massive damage + elemental effects from all 3 charge types
5. Each charge-up skill adds a DIFFERENT elemental charge — the finisher's effect depends on WHICH charge-ups were used
6. Charges decay after 15 seconds of not using a charge-up skill
7. Visual: glowing charge indicators (1, 2, 3), flashy finisher with combined elemental effects

## Engine Primitives Required

### Shared Cross-Ability Charge Pool

SK-42 Withering Fire has charges on ONE ability (fire → consume charge → recharge). SK-52 Combo Strike has a sequential counter on ONE ability (press → advance step). The Charge-Finisher system has a SHARED charge pool across MULTIPLE abilities:

```
struct ChargePool {
    charges: Vec<ChargeType>,   // What type each charge is (fire, lightning, cold)
    max_charges: u8,            // 3
    decay_timer_tick: u64,      // Reset on each charge-up use
    decay_timeout_ticks: u64,   // 900 ticks (15 seconds)
}

enum ChargeType {
    Fire,
    Lightning,
    Cold,
}
```

**Charge-up abilities** (generators): add a charge of their element type to the pool:
```
fn on_charge_up_resolve(pool: &mut ChargePool, charge_type: ChargeType) {
    if pool.charges.len() < pool.max_charges as usize {
        pool.charges.push(charge_type);
    }
    pool.decay_timer_tick = current_tick() + pool.decay_timeout_ticks;
}
```

**Finisher abilities** (consumers): read and consume all charges, scale effect:
```
fn on_finisher_resolve(pool: &mut ChargePool) -> FinisherParams {
    let charge_count = pool.charges.len();
    let charge_types = pool.charges.clone();
    pool.charges.clear();

    FinisherParams {
        damage_multiplier: 1.0 + (charge_count as f32 * 0.5),  // More charges = more damage
        elemental_effects: charge_types,  // Apply effects from each charge type
    }
}
```

### Generator-Spender Pattern

This is a formalization of the generator-spender pattern common in ARPGs:
- **Generators**: abilities that produce a resource (charges, fury, combo points)
- **Spenders**: abilities that consume the resource for a scaling effect

The engine needs:
- A charge pool/resource that multiple abilities can WRITE to (generators)
- A charge pool/resource that multiple abilities can READ and CONSUME from (spenders)
- The pool is per-entity, not per-ability
- The consumed charges affect the spender's resolution (scaling, elemental effects)

### Typed Charges

The charges carry TYPE INFORMATION — not just a count, but WHAT KIND of charges were built. The finisher's behavior depends on the charge composition:
- 3 fire charges → fire finisher (maximum fire damage)
- 1 fire + 1 lightning + 1 cold → tri-element finisher (moderate damage of each type)
- 2 cold + 1 lightning → cold-heavy finisher (strong cold + moderate lightning)

The finisher's stage-execution path must read the charge types and produce different effects based on the composition. This is more complex than a simple count-based scaling — it's COMPOSITION-BASED resolution.

### Charge Decay

Charges decay if the caster doesn't use a charge-up skill within the decay window. This prevents "bank charges and wait forever":
- Each charge-up resets the decay timer
- If the timer expires: ALL charges are lost
- The decay is binary (all or nothing), not gradual (losing one charge at a time)

### Ability Category Classification

The compiler must classify abilities into two categories:
- **Generator**: ability that adds charges to the pool on hit
- **Spender**: ability that consumes charges from the pool on cast

A single ability cannot be both. The classification determines how the ability interacts with the charge pool.

## Cross-Boundary Concerns

TODO: The charge pool is entirely local to the caster's entity (SoftState). Charge-up abilities that hit enemies generate charges locally. Finisher abilities consume charges locally. No special cross-boundary handling needed.

If the caster crosses a boundary (handoff), the charge pool transfers with the entity's state. Charges are preserved through handoffs.

## Compiler Requirements

TODO: Designer specifies: charge pool (max 3, typed charges, 15s decay), charge-up abilities (each adds a specific charge type on hit), finisher abilities (consume all charges, scale damage/effects by count and composition), decay on timeout. Compiler produces:
- ChargePool as per-entity ability state
- Per-charge-up ability: on-hit hook → add charge of specific type to pool, reset decay timer
- Per-finisher ability: on-cast → read pool → calculate scaling → consume charges → resolve
- Composition-based resolution in finisher (charge types affect outcome)
- Decay timer management

The compiler needs to support **shared ability state pools** — per-entity resources that multiple abilities can independently produce and consume. This generalizes the generator-spender pattern.

## Relationship to Other Resource Systems

| System | Sketch | Produced by | Consumed by | Scaling |
|---|---|---|---|---|
| Mana | Built-in | Passive regen | Ability casts | Flat cost |
| Charges | SK-42 | Time (recharge) | Same ability | Per-charge fixed |
| Essence | SK-45 | Death pickups | Trait activation | Proportional |
| Energy | SK-70 | Shield absorption | Passive (damage bonus) | Per-point |
| Escalating Cost | SK-97 | Ability casts (stacking) | Same ability (increased cost) | Exponential penalty |
| **Charge-Finisher** | **SK-116** | **Generator abilities (typed)** | **Finisher abilities** | **Count + composition** |

## Open Questions

- Can finishers be used with 0 charges (weak version, no consumption)?
- If a charge-up ability misses (skillshot), does it still generate a charge?
- Does SK-12 Spell Echo interact — if a charge-up echoes, does it generate an extra charge?
- Can charges be generated by procs (SK-09 Chain Lightning bounce generates a charge)?
- Is the charge pool visible to enemies (they can see you have 3 charges ready)?
- Can the charge composition be reordered (replace a fire charge with a cold charge)?
- Does SK-91 Stasis pause the decay timer?
- Can the charge pool exceed max (with special buffs/items)?
- Does the finisher's damage use the charge-up abilities' offensive stats or the finisher's?
- How does the typed charge system interact with the compiler's ability definition format — is each charge type an enum value in SpellData?
