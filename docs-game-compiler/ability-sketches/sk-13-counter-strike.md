# SK-13: Counter-Strike

## Designer Intent

When I successfully block a melee attack, I automatically perform a counter-attack against the attacker, dealing 80% of my weapon damage. The counter-attack is instant and cannot be blocked or evaded by the attacker.

## Primitive Composition

P-12 (Facing/Dot-Product Check) → P-38 (On-Block/Defend Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Triggering block event (on-block proc)
- The attacker entity
- Blocker's offensive stats

## Observable Behavior

1. Enemy melee attack lands on me
2. Block check succeeds during Phase 2 (defense resolution) — attack is blocked
3. Immediately: counter-attack fires back at the attacker dealing 80% weapon damage
4. Counter-attack bypasses the attacker's block and evasion (guaranteed hit)
5. Counter-attack can crit (using blocker's crit chance)
6. Counter-attack can trigger on-hit procs (e.g., SK-09 Chain Lightning)
7. Visual: parry animation followed by an instant riposte

## Engine Primitives Required

TODO: The block event fires during Phase 2 (defense resolution) on the DEFENDER's Arbiter. The counter-attack is an offensive action using the DEFENDER's offensive stats targeting the ATTACKER. This reverses the normal flow — damage came in from the attacker's Arbiter, now a new attack goes back. Does the counter-attack go through the full two-phase pipeline (Phase 1 on defender's Arbiter, Phase 2 on attacker's Arbiter)? Or is it a shortcut since we already know the attacker?

## Cross-Boundary Concerns

TODO: In the standard two-phase combat pipeline, the attacker's Arbiter runs Phase 1 and relays CombatContext to the defender's Arbiter for Phase 2. The counter-attack reverses this — the defender's Arbiter now runs Phase 1 (offense) and needs to relay back to the attacker's Arbiter for Phase 2 (defense). This creates a round-trip: Arbiter A → Arbiter B → Arbiter B generates counter → Arbiter B → Arbiter A. Two cross-boundary relays for a single exchange.

## Compiler Requirements

TODO: Designer specifies: trigger (on-block), damage (80% weapon), guaranteed hit (bypass block/evasion), can crit, can proc. Compiler produces: on-block proc trigger with an embedded offensive action. The compiler needs to verify that the counter-attack's "guaranteed hit" modifier is expressible — is it a flag on the CombatContext? A bypass of specific defensive checks?

## Open Questions

- Can the counter-attack be countered? (Attacker has counter-strike too → infinite loop?)
- Does the counter-attack use the blocker's current position or the attacker's position for range checking?
- If the original attack was ranged (not melee), does counter-strike trigger? The designer said "melee attack" but the engine needs to know how to classify attacks.
- Does the counter-attack consume any resource or trigger any cooldown on the blocker?
- Does the "guaranteed hit" bypass evasion only, or also damage reduction (armor, resistances)?
- How does proc_depth interact — is the counter-attack at proc_depth=1, and its on-hit procs at depth=2?
- Timing: does the counter-attack resolve on the same tick as the block, or the next tick?
