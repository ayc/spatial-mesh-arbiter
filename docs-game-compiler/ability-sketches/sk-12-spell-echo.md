# SK-12: Spell Echo

## Designer Intent

25% chance when I cast an ability to automatically repeat the same ability immediately at no resource cost. The echo targets the same target (or position for ground-targeted abilities). The echo can itself echo with halved probability (25% → 12.5% → 6.25%...).

## Primitive Composition

P-40 (On-Cast Intercept) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Triggering cast event (on-cast proc)
- The ability that was just cast
- Original target/position

## Observable Behavior

1. Cast an ability normally (resource cost paid, cooldown starts)
2. 25% chance: the same ability fires again immediately at the same target — no resource cost, no cooldown consumed
3. The echo is a full repeat — projectile, travel time, hit, damage, effects
4. The echo itself has a 12.5% chance to echo again (halved each time)
5. Theoretically infinite but probability converges to zero rapidly
6. Visual: rapid-fire repetition of the same ability with a "ghostly" echo effect

## Engine Primitives Required

TODO: The on-cast proc fires at the START of the ability pipeline, after validation but before (or immediately after) the primary cast resolves. The echo re-enters the full pipeline — it spawns a new projectile, which travels, hits, and resolves damage independently. The echo must NOT consume resources or trigger cooldown. How is this represented — a flag on the ActionProposal marking it as "echoed"? Does the echo go through validate_intent again (it should skip resource/cooldown checks)?

## Cross-Boundary Concerns

TODO: The echo targets the same target — if the target has moved or crossed a boundary between the original cast and the echo, what happens? For projectile abilities, the echo spawns a new projectile that may need its own handoff. For instant abilities, the echo resolves immediately on the same tick.

## Compiler Requirements

TODO: Designer specifies: trigger (on-cast), chance (25%), probability decay (halve each echo), cost bypass (no resource, no cooldown). Compiler produces: on-cast proc trigger with echo parameters. The compiler needs to verify that the echoed ability is compatible with re-casting (what about abilities with charges? Abilities that consume a target like SK-07 steal?).

## Open Questions

- Does the echo fire on the same tick as the original cast, or on the next tick?
- If the ability is a projectile, does the echo projectile spawn from the caster's current position or the original cast position?
- Can the echo trigger other on-cast effects (e.g., another ability's on-cast proc)?
- Does the echo interact with proc_depth, or is it a separate recursion system (probability-bounded)?
- If the echoed ability is a channel (SK-05 Global Strike), does the echo also channel?
- Can the echo trigger on-hit procs (SK-09 Chain Lightning, SK-10 Crit Explosion) when it lands?
- How does the engine distinguish "echoed cast" from "player cast" for purposes of cooldown tracking and anti-spam rate limiting (token bucket)?
