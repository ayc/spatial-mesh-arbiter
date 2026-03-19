# SK-24: Stun

## Designer Intent

I hit an enemy with a stunning blow. They cannot move, attack, or cast abilities for 2 seconds. After the stun expires, they gain a brief CC immunity window.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Ability lands on target — stun is applied for 2 seconds
2. Target cannot move (movement input ignored)
3. Target cannot attack (auto-attack disabled)
4. Target cannot cast abilities (all ability inputs blocked)
5. Active channels (SK-05 Global Strike) are interrupted immediately
6. Stun duration is reduced by target's tenacity/CC reduction stat
7. After stun expires: target gains CC immunity for 1 second (no new hard CC can be applied)
8. If target is stunned again within 8 seconds of the first stun expiring, diminishing returns apply (duration reduced by 50%)
9. Visual: stars/dizzy effect over the target's head, frozen pose

## Engine Primitives Required

TODO: The stun is a status effect that modifies the target's capability state. The Arbiter needs to track "what can this entity do?" per tick — a set of capability flags (can_move, can_attack, can_cast) that status effects can suppress. The stun effect sets all three to false. During the tick loop, the Arbiter must check capability flags before processing movement input, before resolving auto-attacks, and before accepting ability proposals. How are capability flags stored — bitmask on SoftState? Derived from active effects each tick?

## Diminishing Returns System

TODO: The Arbiter needs to track CC history per entity. Data required:
- Last hard CC expiry tick per CC category (stun, root, silence, etc.)
- Number of CC applications within the diminishing returns window
- Diminishing returns formula: `effective_duration = base_duration * (0.5 ^ applications_in_window)`
- CC immunity window after hard CC expires (e.g., 1 second)

Where does this state live — on the entity's SoftState? Is it a separate tracking structure? Is the CC history per-category or global across all CC types?

## Cross-Boundary Concerns

TODO: If the target is a Ghost, the stun needs to be relayed to the target's owning Arbiter. The owning Arbiter applies the stun and manages the capability suppression. The caster's Arbiter sees the Ghost stop moving (Ghost update reflects the stun). If the target crosses a boundary while stunned, the stun effect transfers with the entity during handoff.

## Compiler Requirements

TODO: Designer specifies: CC type (stun — hard disable), duration (2s), capability suppression (move + attack + cast), interrupts channels, diminishing returns category (hard CC), tenacity-reducible. Compiler produces: status effect definition with capability flags + DR category tag + channel interrupt flag. The compiler needs to validate that the DR system is correctly referenced.

## Open Questions

- Is tenacity a flat reduction (2s stun → 1.5s with 25% tenacity) or multiplicative?
- Does the CC immunity window apply to all CC types or just the same category (stunned → immune to stuns, but not roots)?
- Can stun be applied to CC-immune targets (application blocked) or does the ability fizzle entirely (cooldown refunded)?
- Does stun prevent passive effects from functioning (SK-08 Aura, SK-23 Thorns)?
- If an entity is stunned and displaced simultaneously (SK-01 Toss), which takes priority?
- Does the diminishing returns window reset after the immunity window, or does it decay gradually?
- How does stun interact with SK-12 Spell Echo — if the original cast stuns, does the echo also stun (applying DR)?
