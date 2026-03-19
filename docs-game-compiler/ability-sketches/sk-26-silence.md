# SK-26: Silence

## Designer Intent

I silence an enemy for 4 seconds. They cannot cast any abilities, but they can move and auto-attack. Active channels are interrupted immediately. Passive abilities continue to function.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Ability lands on target — silence is applied for 4 seconds
2. Target cannot cast abilities (all ability inputs rejected)
3. Target CAN move (movement input functional)
4. Target CAN auto-attack
5. Active channels (SK-05 Global Strike) are interrupted immediately
6. Passive abilities (SK-08 Aura, SK-23 Thorns) continue functioning
7. Toggle abilities that are already active remain active (but cannot be toggled off/on)
8. Duration reduced by tenacity
9. Diminishing returns apply
10. Cleansable by SK-15 Purify
11. Visual: muzzle/gag effect, "silenced" indicator

## Engine Primitives Required

TODO: Silence suppresses casting capability — `can_cast = false` but `can_move = true`, `can_attack = true`. The Arbiter rejects any `ActionProposal` with an ability payload while the entity is silenced. Auto-attacks are a separate category — they bypass the silence check. How does the engine distinguish "ability cast" from "auto-attack"? Is it a field on the ActionPayload? Does the compiler classify each action type?

## Interaction With Other CC

- **Stun (SK-24)** applied while silenced: stun subsumes silence (all capabilities disabled). When stun expires, remaining silence continues.
- **Root (SK-25)** applied while silenced: both apply — can't move AND can't cast, but CAN auto-attack.
- **Sleep (SK-27)** applied while silenced: sleep subsumes silence. If sleep breaks on damage, does silence resume for remaining duration?

## Cross-Boundary Concerns

TODO: Same relay pattern. If the target is a Ghost, silence is relayed to the owning Arbiter. The silenced entity's movement and auto-attack proposals are still accepted, but ability proposals are rejected by the owning Arbiter. From the caster's perspective, they see the Ghost continuing to move but not casting.

## Compiler Requirements

TODO: Designer specifies: CC type (silence — cast disable), duration (4s), capability suppression (cast only), interrupts channels, passives unaffected, DR category, tenacity-reducible, cleansable. Compiler needs to classify every action type as "affected by silence" or "unaffected." Auto-attacks, movement, and passives are unaffected. Active ability casts are affected.

## Open Questions

- Does silence prevent item activation (consumables like potions)?
- Does silence interrupt SK-18 Resurrect (which is a channel)?
- Can a silenced entity activate SK-15 Purify on themselves to remove the silence? (Purify is an ability cast — should be blocked by silence)
- Does silence affect SK-13 Counter-Strike (an automatic proc, not a manual cast)?
- How does silence interact with SK-12 Spell Echo — if the original cast triggers an echo, but silence is applied between the cast and the echo, does the echo fire?
- Does silence prevent SK-07 Ability Steal from being used?
- Can silence suppress toggle abilities that are already active (SK-08 Aura turning off)?
