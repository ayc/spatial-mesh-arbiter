# SK-19: Guardian Angel

## Designer Intent

I mark an ally for 5 seconds. During this time, 50% of all damage they would take is redirected to me instead. I take the redirected damage using my own defensive stats.

## Primitive Composition

P-34 (Persistent Linkage) → P-20 (Damage Redirection)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the guardian)
- Target ally entity (the ward)

## Observable Behavior

1. Cast on ally — mark appears on the target for 5 seconds
2. When the marked ally takes damage: 50% of pre-mitigation damage is redirected to the guardian
3. The ally receives the remaining 50%, mitigated by their own defensive stats
4. The guardian receives the redirected 50%, mitigated by the guardian's own defensive stats
5. Both entities independently apply their own resistances, block, evasion to their respective portions
6. If the guardian dies from redirected damage, the mark breaks — ally takes full damage for the remaining duration
7. Visual: golden link between guardian and ward, flashes on each redirect

## Engine Primitives Required

TODO: The damage redirect intercepts during Phase 2 (defense resolution) on the WARD's Arbiter. Before the ward's defensive stats are applied, the damage is split: 50% stays, 50% is relayed to the guardian. The guardian's portion goes through its own Phase 2 (on the guardian's Arbiter). This is similar to SK-04 Tether but one-directional. The ward's Arbiter must know the guardian exists and relay damage to them. How is this tracked — a status effect on the ward referencing the guardian's EntityID?

## Cross-Boundary Concerns

TODO: If guardian and ward are on different Arbiters, every damage event on the ward triggers a cross-boundary relay of the guardian's damage portion. The ward's Arbiter splits the damage, applies the ward's 50% locally, and sends a relay to the guardian's Arbiter for the other 50%. The guardian's Arbiter then applies the guardian's defensive stats to the redirected portion. This adds one relay per damage event on the ward for the duration.

## Compiler Requirements

TODO: Designer specifies: target (ally), duration (5s), redirect percentage (50%), redirect applies guardian's own defenses, breaks on guardian death. Compiler produces: status effect on ward with redirect parameters + cross-entity relay trigger + death-break condition. How does the compiler express "intercept damage during Phase 2 before mitigation"?

## Open Questions

- Is the redirect based on pre-mitigation or post-mitigation damage? (Pre means the guardian could take more or less than the ward depending on relative defenses.)
- Can the guardian redirect damage from multiple wards simultaneously (cast on multiple allies)?
- Does the redirected damage trigger on-hit procs on the guardian (SK-13 Counter-Strike on block of redirected damage)?
- If the ward has a shield (SK-17), does the shield absorb before or after the redirect split?
- Can the guardian use SK-15 Purify to cleanse the mark from their ward?
- How does this interact with SK-04 Tether — if the ward has both a tether and a guardian mark, in what order do damage splits apply?
- If the guardian has their own Guardian Angel mark from another support, does redirected damage get re-redirected (chain of guardians)?
