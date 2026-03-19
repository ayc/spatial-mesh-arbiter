# SK-07: Ability Steal

## Designer Intent

My character steals the last ability used by a target enemy. The stolen ability replaces one of my ability slots temporarily. I can cast it once using my own stats, then it reverts to my original ability.

## Primitive Composition

P-40 (On-Cast Intercept) → P-31 (Identity/Loadout Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy — identify the last ability they used
2. That ability is copied into one of my ability slots (replacing my normal ability temporarily)
3. I can cast the stolen ability once, using my own offensive stats
4. After casting (or after a timeout), my original ability returns
5. The enemy is not affected — they keep their ability
6. Visual: my character takes on a visual indicator of the stolen ability

## Engine Primitives Required

TODO: The Arbiter needs to look up "last ability used by entity X" — this requires tracking recent ability history per entity. Then it needs to dynamically assign a different ability definition to the caster's ability slot. The validate_intent and resolve_external hooks need to resolve against a different AbilityEntry than normal for that slot. How is this represented — a status effect that overrides the ability mapping?

## Cross-Boundary Concerns

TODO: If the target is a Ghost, the caster's Arbiter may not know what ability the target last used (Ghosts are lightweight — position/velocity only). Does this require a relay to the target's owning Arbiter to query their ability history? What if the target used the ability several ticks ago and the data is stale?

## Compiler Requirements

TODO: The compiler needs to produce ability definitions that are portable — any entity should be able to execute any ability, not just the original owner. How does the compiler ensure that ability definitions don't reference caster-specific state that wouldn't exist on the stealer? What about abilities that reference the caster's class-specific resources?

## Open Questions

- What if the enemy's last ability is a passive (aura, toggle)? Can those be stolen?
- What if the enemy hasn't used an ability yet? Does the steal fail?
- Does the stolen ability use the caster's stats (offensive stats) or the enemy's?
- What if the stolen ability references a resource the caster doesn't have (e.g., enemy uses "rage" but caster uses "mana")?
- How does this interact with data_epoch — if the enemy cast under epoch N and you steal under epoch N+1 (after a balance patch), which version of the ability definition applies?
- Can the stolen ability trigger the caster's own on-hit/on-cast proc effects?
- What if the stolen ability is itself a summon (SK-06) — who owns the summoned minions?
