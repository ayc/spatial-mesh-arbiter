# SK-02: Poison Shot

## Designer Intent

My character performs a ranged attack, shooting poison at the target. The target gets a poison debuff — a DoT lasting 5 seconds. Any successive damage I deal to the target refreshes the DoT duration back to 5 seconds. Each DoT tick heals me for a portion of the damage dealt, and applies a stacking buff to me that increases my damage by 1% per stack.

## Primitive Composition

P-32 (Actor Spawning) → P-35 (On-Hit Hook) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target entity (must be in range)

## Observable Behavior

1. Projectile launches toward target
2. On hit: apply initial damage + apply Poison debuff (DoT, 5s duration)
3. DoT ticks every 1s (5 pulses), dealing poison damage per tick
4. If caster deals any other damage to the target while Poison is active, Poison duration resets to 5s
5. Each DoT tick: heal caster for Z% of damage dealt (drain)
6. Each DoT tick: apply +1% damage buff stack to caster (stacking, no cap specified)

## Engine Primitives Required

TODO: Break down into actor chain, status effects, reactive triggers, cross-boundary relays.

## Cross-Boundary Concerns

TODO: DoT pulses on target's Arbiter but heal/buff apply to caster who may be on a different Arbiter. Duration refresh triggered by damage from a specific source. How does the target's Arbiter know about damage from the caster arriving via relay?

## Compiler Requirements

TODO: What would the designer write? What does the compiler produce?

## Open Questions

- Does the DoT refresh on ANY damage from the caster, or only direct ability damage (not other DoTs)?
- Is there a stack cap on the damage buff, or does it grow unboundedly?
- If the caster dies, does the DoT persist on the target? Do stacks on the caster persist through death?
- What happens to the drain heal if the caster is at full HP?
- Can the poison debuff be cleansed? If cleansed, do the caster's damage buff stacks remain?
- Does the 1% damage buff have its own duration, or does it last as long as the DoT is active?
