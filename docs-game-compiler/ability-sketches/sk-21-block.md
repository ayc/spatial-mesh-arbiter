# SK-21: Block

## Designer Intent

My character has a chance to fully block incoming attacks, negating all damage from that hit. Block chance is derived from my shield/armor stats. After a successful block, block chance is temporarily reduced (diminishing returns) to prevent permanent invulnerability under rapid attacks.

## Primitive Composition

P-38 (On-Block/Defend Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Incoming damage event (any source)
- Defender's block chance (derived stat)
- Defender's current block penalty (accumulated from recent blocks)

## Observable Behavior

1. Attack lands on me — block check is evaluated
2. If block succeeds: damage is reduced to zero, "Blocked!" indicator shown
3. After a successful block: block chance is reduced by a penalty (e.g., -15% per recent block)
4. Block penalty decays over time (e.g., recovers fully over 3 seconds)
5. Block can trigger SK-13 Counter-Strike (on-block proc)
6. Block does NOT prevent non-damage effects (debuffs, displacement) unless specifically stated
7. Visual: shield raise animation, spark effect on block

## Engine Primitives Required

TODO: Block is evaluated early in Phase 2 (defense resolution), before damage mitigation (armor, resistances). If block succeeds, the entire damage pipeline short-circuits — no mitigation calc, no shield consumption, no thorns trigger. The block chance is a derived stat on DefensiveStats, but the diminishing returns penalty is a dynamic value on SoftState that changes per-tick. How is the block roll deterministic — engine-provided RNG seeded by tick + entity_id?

## Interaction With Other Defensive Mechanics

This is where ordering matters. The Phase 2 pipeline must define when block is checked relative to:
- **Evasion** — does evasion check happen before or after block? (Typically evasion first: evade = miss entirely, block = hit but negated)
- **Shield (SK-17)** — if block fails, does the shield absorb? (Yes — block is checked first, shield is the next layer)
- **Reflection (SK-22)** — if blocked, is there anything to reflect? (No — block negates the damage, nothing to calculate reflection on)
- **Thorns (SK-23)** — if blocked, do thorns still fire? (Debatable — "you were hit" is ambiguous when the hit was blocked)
- **Guardian Angel (SK-19)** — if damage is redirected, does the redirected portion get its own block check on the guardian?
- **Counter-Strike (SK-13)** — triggers on successful block (confirmed interaction)

## Cross-Boundary Concerns

TODO: Block is resolved entirely on the defender's Arbiter during Phase 2. The attacker's CombatContext arrives with pre-rolled offensive data. The defender rolls the block check locally. If blocked, no damage is applied and no relay is needed — the event terminates. The only cross-boundary message would be if Counter-Strike triggers (SK-13), sending a counter-attack back to the attacker.

## Compiler Requirements

TODO: Designer specifies: block chance source (derived stat), diminishing returns (penalty per block, decay rate), what block negates (damage only? effects too?), proc triggers (on-block). Compiler produces: Phase 2 check point in the mitigation pipeline + diminishing returns state tracking + proc trigger hook. The compiler needs to place this at the correct position in the `apply_combat_math` step ordering.

## Open Questions

- Is block chance a flat percentage or does it scale with attacker stats (accuracy vs block)?
- Does block work against all damage types (melee, ranged, spell, DoT ticks) or only specific types?
- Can block chance exceed 100% (from stacking buffs), and if so is it capped?
- Does the diminishing returns penalty apply per-source or globally (getting hit by 5 enemies simultaneously)?
- Is the block roll per-hit or per-tick (matters for multi-hit abilities)?
- Does blocking a DoT tick (SK-02 Poison pulse) block just that tick, or remove the DoT?
- How does the deterministic RNG for block rolls work — seeded how to prevent prediction/manipulation?
