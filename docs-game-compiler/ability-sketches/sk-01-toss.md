# SK-01: Toss

## Designer Intent

My character is within range to target an enemy. I "toss" the target unit — the enemy is thrown through the air to a position I define (submitted as a requested ground-target position). When the target lands at that position, it takes X damage. Any other enemy units within radius of the landing position also take damage.

## Primitive Composition

P-02 (Forced Displacement) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target entity (must be in range)
- Landing position (requested ground-target position)

## Observable Behavior

1. Target is lifted and displaced along an arc from current position to landing position
2. Target cannot act during displacement (CC'd — airborne state)
3. On landing: target takes X impact damage
4. On landing: AoE damage check at landing position — all enemies within radius take Y damage
5. Caster is free to act during the toss flight time

## Engine Primitives Required

TODO: Break down into actor chain, status effects, spatial queries, cross-boundary concerns.

## Cross-Boundary Concerns

TODO: What happens if the target is a Ghost? What if the landing position is on a different Arbiter? What about the AoE hitting entities on multiple Arbiters?

## Compiler Requirements

TODO: What would the designer write? What does the compiler produce?

## Open Questions

- Is the target displacement a status effect on the target, or a temporary actor (like a projectile carrying the target)?
- Who owns the displaced entity during flight — the caster's Arbiter or the target's Arbiter?
- If the landing position crosses an Arbiter boundary, is this a handoff?
- Can the toss be interrupted mid-flight (e.g., target gets cleansed)?
- What happens if the landing position is inside static geometry (wall)?
