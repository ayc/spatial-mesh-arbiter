# SK-14: Execute Threshold

## Designer Intent

My attacks against enemies below 25% HP deal 200% bonus damage. If this empowered hit kills the target, the ability's cooldown is instantly reset.

## Primitive Composition

P-17 (Conditional Thresholds)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Any damage event from caster to target
- Target's current HP percentage
- Ability cooldown state

## Observable Behavior

1. I attack an enemy
2. Before damage is applied, check: is target HP below 25%?
3. If yes: damage is multiplied by 3x (base + 200% bonus)
4. Damage is applied (potentially killing the target)
5. If the target dies from this hit: the ability's cooldown resets to 0
6. Visual: execute indicator when targeting low-HP enemies, enhanced hit effect

## Engine Primitives Required

TODO: This is a conditional damage modifier that checks target state during damage resolution. Where in the 11-step apply_combat_math pipeline (T1-03) does this check occur? It needs to happen AFTER the target's current HP is known but BEFORE final damage is applied. The HP threshold check is on the DEFENDER's Arbiter (since that's where authoritative HP lives). But the damage multiplier modifies the ATTACKER's damage. In cross-boundary combat, Phase 1 (offense) happens on the attacker's Arbiter without access to the target's HP.

## Cross-Boundary Concerns

TODO: The fundamental problem: the attacker's Arbiter runs Phase 1 and pre-rolls CombatContext with offensive stats. But the execute check depends on the target's current HP, which is only known on the defender's Arbiter during Phase 2. Options: (1) the execute modifier is applied during Phase 2 by the defender's Arbiter, (2) the attacker uses the Ghost's HP (approximate, possibly stale), (3) the execute flag is always set and the defender conditionally applies the multiplier.

## Compiler Requirements

TODO: Designer specifies: condition (target HP < 25%), damage modifier (200% bonus), secondary trigger (on-kill → cooldown reset). Compiler produces: conditional modifier in the combat resolution pipeline + on-kill proc for cooldown manipulation. The compiler needs to understand WHERE in the pipeline this modifier applies — it's not a flat buff, it's a conditional evaluated at resolution time.

## Open Questions

- Is the 25% HP check based on the target's HP before or after the current hit's base damage?
- If the target is at 26% HP and the base hit would bring them to 24%, does the execute bonus apply to the same hit or the next one?
- Does the execute bonus apply to DoT ticks (SK-02 Poison Shot) or only direct hits?
- In cross-boundary combat, is the Ghost's HP accurate enough for the threshold check? What if the Ghost shows 30% but the real HP is 24%?
- Does the cooldown reset apply to the specific ability used, or a different ability (e.g., "killing blow with basic attack resets ultimate cooldown")?
- Can the execute bonus itself crit? If so, is the crit calculated on the base damage or the execute-amplified damage?
- Does the execute modifier stack with other conditional damage modifiers (e.g., "bonus damage to slowed targets")?
