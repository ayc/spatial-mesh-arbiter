# SK-04: Tether

## Designer Intent

My character links to an ally. While the link is active, we share 30% of damage taken and 50% of healing received. The tether is visible as a beam between us. If the distance between us exceeds a threshold, the tether snaps and the effect ends.

## Primitive Composition

P-34 (Persistent Linkage) → P-04 (Positional Clamping)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Tether establishes between caster and target — visible beam connects them
2. While active: when either entity takes damage, 30% is redirected to the partner
3. While active: when either entity receives healing, 50% is copied to the partner
4. Distance is checked continuously — if distance exceeds break threshold, tether snaps
5. Tether has a maximum duration (e.g., 12 seconds) even if distance is maintained
6. Either player dying breaks the tether
7. The tether can be dispelled/cleansed

## Engine Primitives Required

TODO: How is the persistent link represented? A status effect on both entities referencing each other? A standalone actor? How does damage sharing work — is it a reactive trigger that intercepts damage resolution and splits it? Does healing sharing work the same way?

## Cross-Boundary Concerns

TODO: If caster and target are on different Arbiters, every damage/healing event on either entity requires a cross-boundary relay to the partner. The distance check needs both positions — if they're on different Arbiters, one sees the other as a Ghost. Is Ghost position accuracy sufficient for break-distance checks?

## Compiler Requirements

TODO: What does the designer write to express "share 30% damage, 50% healing, break at distance X"? What runtime structures does this compile into?

## Open Questions

- Does the damage sharing reduce the original damage, or is it additional damage on the partner? (30% redirect vs 30% copy)
- Can the damage sharing trigger proc effects on the partner (e.g., thorns, on-hit)?
- If both linked entities take damage simultaneously, does sharing recurse (A shares to B, B shares back to A)?
- What is the minimum tick cadence for the distance check — every tick (60Hz) or lower frequency?
- Can multiple tethers exist on the same entity simultaneously?
- How does the tether interact with displacement (SK-01 Toss) — does tossing one partner pull the other, or does the tether snap?
