# SK-09: Chain Lightning

## Designer Intent

On hit, my attack has a 30% chance to arc lightning to the nearest enemy within range. Each arc deals reduced damage (70% of the previous arc) and can chain to another nearby enemy. Maximum 5 bounces. An enemy can only be hit once per chain.

## Primitive Composition

P-32 (Actor Spawning) → P-11 (N-Nearest Neighbor) → P-35 (On-Hit Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Triggering hit event (on-hit proc)
- Initial target entity
- Caster's offensive stats

## Observable Behavior

1. Normal attack lands on target
2. 30% chance: lightning arcs from the target to the nearest unhit enemy within arc range
3. Arc deals 70% of the previous arc's damage
4. Each arc can trigger another arc (up to 5 total bounces)
5. Each enemy can only be hit once per chain (no ping-pong)
6. Visual: lightning bolt effect between each pair

## Engine Primitives Required

TODO: Each bounce is a spatial query ("nearest enemy within R that hasn't been hit by this chain"). The chain needs to track a "hit list" (set of EntityIDs already hit). Each bounce resolves damage independently against the target's defensive stats. The proc_depth guard limits total recursion. How does the chain state propagate — is it a field on the CombatContext? A separate chain actor?

## Cross-Boundary Concerns

TODO: The nearest unhit enemy might be a Ghost owned by a different Arbiter. The arc needs to relay to that Arbiter, which then does its own spatial query for the next bounce. A single chain could ping across 3+ Arbiters. Each relay carries the hit list and remaining bounce count. Latency accumulates per hop — is this visible to players?

## Compiler Requirements

TODO: Designer specifies: trigger (on-hit), chance (30%), max bounces (5), damage falloff (0.7x per bounce), range per arc. Compiler produces: proc trigger definition with chain parameters. How does the compiler validate that the chain is bounded (max bounces finite, hit-list prevents cycles)?

## Open Questions

- Does each arc roll its own crit chance, or inherit the original hit's crit status?
- Can each arc trigger other on-hit procs (e.g., another chain lightning, or SK-02 poison)?
- If proc_depth is reached mid-chain, does the chain stop or does it continue without triggering sub-procs?
- How is the "nearest unhit enemy" query ordered deterministically if two enemies are equidistant?
- Does the chain continue if a bounce kills its target?
- Performance: in a dense area with many enemies, 5 spatial queries in sequence per proc — is this bounded well enough?
