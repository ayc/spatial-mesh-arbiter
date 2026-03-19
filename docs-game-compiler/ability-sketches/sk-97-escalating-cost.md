# SK-97: Escalating Cost

## Designer Intent

My primary heal is spammable but each cast stacks "Desperation" on me, increasing the mana cost of the next cast. Cast it once: normal cost. Twice quickly: 1.5x cost. Three times: 2.25x cost. Stacks decay over time — if I wait a few seconds between casts, the cost resets. Spam healing is powerful but drains mana rapidly.

## Primitive Composition

P-42 (Stacking Counters w/ Decay) → P-51 (Desperation Cost Modifiers)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Standard ability cast (targeted heal)

## Observable Behavior

1. First cast: costs 30 mana. Gain 1 stack of Desperation.
2. Second cast (within decay window): costs 45 mana (30 × 1.5). Gain 2nd stack.
3. Third cast (within decay window): costs 67 mana (30 × 1.5 × 1.5). Gain 3rd stack.
4. Each stack increases the cost multiplier by 50%
5. Stacks decay one at a time every 4 seconds of not casting
6. At 0 stacks: cost returns to base (30 mana)
7. No maximum stack count (but mana runs out naturally)
8. Visual: increasing desperation/strain indicator, mana bar draining faster

## Engine Primitives Required

### Self-Stacking Cost Modifier

All existing abilities have a FIXED cost (flat mana, flat HP, charges). Escalating Cost introduces a **dynamic cost that changes based on a self-applied stack counter**:

```
struct EscalatingCostState {
    current_stacks: u32,
    cost_multiplier_per_stack: SimFixed,  // 1.5 (50% increase per stack)
    stack_decay_interval_ticks: u64,      // 240 ticks (4 seconds)
    last_cast_tick: u64,
}
```

On ability cast:
1. Calculate effective cost: `base_cost * (cost_multiplier_per_stack ^ current_stacks)`
2. Check: does the caster have enough mana?
3. If yes: deduct effective cost, increment stacks, set last_cast_tick
4. If no: reject (can't afford)

On tick (decay check):
1. If `current_tick - last_cast_tick >= stack_decay_interval_ticks`: remove one stack, update last_cast_tick
2. Repeat until stacks = 0 or within decay window

### Cost Calculation in Validation

The `validate_intent` hook must calculate the DYNAMIC cost before accepting the proposal. The Edge Node's prediction must also calculate the dynamic cost for client-side mana prediction. Both must agree (deterministic).

The ability definition needs: `cost_type: Escalating { base: 30, multiplier_per_stack: 1.5, decay_interval: 4s }`.

### Stack as Ability State (Not Status Effect?)

Desperation stacks could be implemented as:
- **Status effect**: a visible debuff with stack count. Cleansable? Probably not — it's a self-imposed resource mechanic.
- **Ability state**: part of the ability's runtime data on the entity. Not visible as a buff/debuff.

Design choice: if implemented as a status effect, enemies can see how desperate the healer is (counterplay information). If implemented as ability state, it's hidden.

### Exponential Cost Growth

The cost grows exponentially: `30, 45, 67, 101, 152, 228...`. By stack 5, the cost is 7.6x base. This naturally limits spam — even with a full mana pool, you can only spam 5-6 casts before going OOM.

The exponential formula must use fixed-point exponentiation. For integer stack counts, this is repeated multiplication (not transcendental functions).

## Cross-Boundary Concerns

TODO: None. The escalating cost state is entirely local to the caster's entity on their Arbiter. It affects ability validation and mana deduction — both are local operations. No cross-boundary relay needed.

## Compiler Requirements

TODO: Designer specifies: base cost (30 mana), cost multiplier per stack (1.5x), stack decay (one stack every 4 seconds of not casting), no max stacks. Compiler produces:
- EscalatingCostState as ability runtime data
- Cost calculation in validate_intent: `base * multiplier ^ stacks`
- Stack increment on cast
- Stack decay on timer
- Edge Node prediction must mirror the cost calculation

The compiler adds Escalating to the cost model system alongside Flat, Percentage, and Charges (SK-42).

## Open Questions

- Are Desperation stacks visible to enemies (buff bar indicator)?
- Can stacks be cleared by any ability (self-cleanse? Or only by waiting?)
- Does SK-91 Stasis pause the stack decay timer?
- Does Kinematic Dilation affect the stack decay interval?
- Can multiple abilities share the same Desperation stack counter (all heals increase the same stacks)?
- Does the Edge Node accurately predict the dynamic cost (for client-side mana bar)?
- Is the multiplier per-stack (1.5x per stack) or cumulative (stack 1 = 1.5x, stack 2 = 2x, stack 3 = 2.5x)?
- Can the cost exceed the caster's maximum mana pool (making the ability literally uncastable)?
- Does SK-83 Next-Cast Empowerment interact with escalating cost (empowered cast has different cost)?
