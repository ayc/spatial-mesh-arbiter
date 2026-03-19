# SK-10: Crit Explosion

## Designer Intent

When I land a critical hit, an explosion erupts at the target's position dealing AoE damage to all enemies within radius. The explosion damage can itself critically strike, triggering another explosion at each crit target's position. Damage diminishes with each generation.

## Primitive Composition

P-37 (On-Crit Hook) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Triggering crit event (on-crit proc)
- Target position (where the crit landed)
- Caster's offensive stats

## Observable Behavior

1. Normal attack crits on target
2. Explosion at target's position — all enemies within radius take X% of the original crit damage
3. Each explosion hit rolls its own crit chance
4. If an explosion hit crits, a new explosion occurs at that target's position
5. Each generation deals diminishing damage (e.g., 50% of the previous generation)
6. Bounded by proc_depth — maximum N generations
7. Visual: cascading explosions rippling outward through groups of enemies

## Engine Primitives Required

TODO: The on-crit proc spawns what is essentially a zone/AoE at the target's position. This AoE resolves damage against each entity in radius. Each damage resolution independently rolls crit. Crits spawn new AoEs. This is a recursive tree, not a linear chain (unlike SK-09). Each explosion is a spatial query. The proc_depth guard is critical — without it, a dense pack of enemies creates exponential explosions.

## Cross-Boundary Concerns

TODO: The explosion happens at the target's position, which may be on a different Arbiter than the caster. The caster's offensive stats need to be available (carried in CombatContext). Secondary explosions from Ghost targets relay to their owning Arbiters, which each spawn their own local AoEs. A single crit near a boundary could fan out across multiple Arbiters simultaneously.

## Compiler Requirements

TODO: Designer specifies: trigger (on-crit), AoE radius, damage scaling per generation, crit inheritance rules. Compiler produces: proc trigger + zone spawn definition + recursive generation tracking. How does the compiler statically verify that this terminates? (proc_depth + diminishing damage, but the compiler needs to know the depth is configured)

## Open Questions

- Does each explosion use the caster's crit chance or a reduced crit chance per generation?
- Can explosion hits trigger other on-hit procs beyond crit explosion (SK-09 chain lightning)?
- Is the explosion centered on the target's exact position or snapped to a grid?
- If multiple enemies are crit in the same explosion, do all of them spawn secondary explosions simultaneously?
- What is the worst-case entity count for proc_depth=3 in a dense area? Is the bound tight enough?
- Does the explosion damage the original target (self-overlap)?
