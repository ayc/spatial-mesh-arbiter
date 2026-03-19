# SK-22: Damage Reflection

## Designer Intent

A buff or passive that reflects a percentage of incoming damage back to the attacker. When I take 100 damage and have 30% reflection, I take the full 100 but the attacker also takes 30 damage. The reflected damage uses the attacker's own defensive stats for mitigation.

## Primitive Composition

P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Incoming damage event (any source)
- Defender's reflection percentage (from buff, item, or passive)
- Attacker entity (damage source)

## Observable Behavior

1. Attack lands on me — normal damage is applied
2. Reflection calculates: reflected_amount = incoming_damage * reflection_percentage
3. Reflected damage is sent back to the attacker as a new damage event
4. Attacker's defensive stats mitigate the reflected damage independently
5. Reflection damage type matches the original damage type (fire reflected as fire)
6. Reflected damage can trigger procs on the attacker (they are "taking damage")
7. Visual: mirror/shimmer effect on the defender, reflected damage number on the attacker

## Engine Primitives Required

TODO: Reflection is evaluated during Phase 2 AFTER the damage amount is known (post-mitigation on the defender? or pre-mitigation?). The reflected damage becomes a new outgoing damage event from the defender to the attacker. This reverse damage event needs to go through Phase 2 on the ATTACKER's Arbiter. How is this different from SK-23 Thorns — reflection scales with incoming damage, thorns is flat.

## Interaction With Other Defensive Mechanics

Ordering within Phase 2 is critical:
- **Block (SK-21)** — if blocked, incoming damage is zero, so reflected amount is zero. No reflection on blocked hits.
- **Evasion** — if evaded, no hit occurred, no reflection.
- **Shield (SK-17)** — is reflection calculated on pre-shield or post-shield damage? If the shield absorbs 80 of 100 damage, is reflection 30% of 100 or 30% of 20?
- **Guardian Angel (SK-19)** — if 50% of damage is redirected to the guardian, does the ward reflect 30% of their 50%, the guardian reflects 30% of their 50%, or reflection is calculated on the full 100 before redirect?
- **Thorns (SK-23)** — reflection and thorns both send damage back. Are they additive? Do they trigger independently?

## Cross-Boundary Concerns

TODO: The reflected damage is a reverse relay. The defender's Arbiter calculates the reflected amount during Phase 2, then sends a damage event back to the attacker's Arbiter for Phase 2 resolution against the attacker's defenses. Same reverse relay pattern as SK-13 Counter-Strike. Can the reflected damage itself be reflected (attacker also has reflection → infinite loop)? Must be bounded by proc_depth.

## Compiler Requirements

TODO: Designer specifies: reflection percentage, damage type matching, what it calculates from (pre or post mitigation). Compiler produces: Phase 2 hook that calculates reflected amount and emits a reverse damage event. The compiler needs to ensure the reverse event is tagged to prevent infinite reflection loops (proc_depth or a "reflected" flag that prevents re-reflection).

## Open Questions

- Is reflection calculated on pre-mitigation or post-mitigation damage?
- Can reflected damage crit?
- Can reflected damage trigger on-hit procs on the attacker (SK-09 Chain Lightning)?
- Can reflected damage be reflected back again (attacker also has reflection)? If so, how is this bounded?
- Does reflection apply to DoT ticks (SK-02 Poison) — each tick reflects a portion back to the DoT caster?
- Does reflection apply to AoE damage (SK-10 Crit Explosion) — is it reflected to the original caster or the explosion source?
- Can reflection percentage exceed 100% (reflecting more than received)?
- How does reflection interact with damage that has multiple sources (e.g., SK-04 Tether shared damage — who gets the reflection)?
