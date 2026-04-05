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

Escalating Cost is now a canonical `resource_cost.escalation` reference.

The recommended lowering is:

1. author the base resource cost normally:
   - `resource_cost = {`
     `pool = mana,`
     `amount = 30,`
     `escalation = {`
       `multiplier_per_stack = 1.5,`
       `decay_interval_ticks = 240,`
       `shared_counter_id = ability_id`
     `}`
     `}`
2. let Stage 2 compute
   `effective_cost = amount * multiplier_per_stack ^ current_stacks`
   before affordability checks
3. increment the counter only when the cast commits successfully
4. decay one stack at a time after each full interval with no qualifying cast on the same counter

This keeps the mechanic inside existing surfaces:

- the stack counter is canonical compiler-owned escalation state, not a visible status by default
- affordability and deduction already happen through the Stage 2 `P-51` cost policy
- the multiplier is multiplicative per current stack, matching the authored exponential growth

## Cross-Boundary Concerns

Escalating Cost is entirely caster-owner local.

1. The escalation counter is keyed on the casting entity and read during Stage 2 affordability on
   that entity's current owner.
2. If the caster hands off, the counter transfers with the entity as ordinary SoftState and the new
   owner continues the same escalation history.
3. Edge prediction may mirror the current displayed cost, but authoritative affordability and stack
   mutation always happen on the caster owner.

## Compiler Requirements

Designer specifies:

- base resource pool and amount
- escalation multiplier per stack
- decay interval
- optional max stacks
- optional shared counter ID when multiple abilities should share the same desperation counter

Compiler emits:

- one ordinary `resource_cost`
- one canonical `CostEscalationBlock`
- one compiler-owned escalation counter keyed by `shared_counter_id`

Compiler validates:

1. `multiplier_per_stack > 0`
2. `decay_interval_ticks > 0`
3. if authored, `max_stacks > 0`
4. escalating cost is expressed through canonical `resource_cost.escalation`, not a bespoke
   visible status or custom validation script

## Resolved Interaction Notes

- The multiplier is multiplicative per current stack: `30, 45, 67.5, 101.25, ...` before ordinary
  fixed-point rounding.
- If the effective cost exceeds the caster's current or maximum resource pool, the cast simply
  fails the normal affordability check.
- By default the counter is ability-local because `shared_counter_id` falls back to the owning
  `ability_id`.
- The baseline reference does not expose the desperation counter as a public buff/debuff bar.
