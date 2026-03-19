# SK-27: Sleep

## Designer Intent

I put an enemy to sleep for 5 seconds. They cannot act at all — fully disabled like a stun, but with a longer duration. However, the sleep breaks instantly if the sleeping entity takes any damage. This creates tactical tension: the CC is powerful but fragile.

## Primitive Composition

P-26 (Capability Bitmask) → P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Ability lands on target — sleep is applied for 5 seconds
2. Target cannot move, attack, or cast (full disable like stun)
3. Active channels are interrupted
4. If the sleeping entity takes ANY damage: sleep breaks immediately
5. Damage from any source breaks sleep (allies, enemies, DoTs, environmental)
6. After sleep breaks (by damage or expiry): CC immunity window applies
7. Duration reduced by tenacity
8. Diminishing returns apply (same hard CC category as stun)
9. Cleansable by SK-15 Purify
10. Visual: zzz effect, entity in a resting pose

## Engine Primitives Required

TODO: Sleep is functionally identical to stun (all capabilities suppressed) but with a **break-on-damage condition**. Every incoming damage event targeting a sleeping entity must check the sleep status BEFORE applying damage. On break: remove the sleep effect, then apply the damage normally. The ordering is critical — does the full damage apply after the sleep breaks, or is the first tick of damage "absorbed" by the sleep?

## Break Condition Complexity

The break-on-damage check interacts with multiple damage sources:
- **Direct hits** — straightforward, breaks sleep, damage applies
- **DoT ticks (SK-02 Poison)** — a poison tick breaks the sleep. Was this intentional by the poisoner?
- **AoE damage (SK-08 Aura, SK-10 Crit Explosion)** — friendly AoE accidentally breaking a teammate's sleep setup
- **Thorns (SK-23)** — if a sleeping entity has thorns and someone melees them... the attacker takes thorns damage, but thorns doesn't damage the sleeping entity. Wait — the sleeping entity took a melee hit, which should break sleep. But thorns fires as a response. Does the hit break sleep, or does the sleep prevent the hit from being "received"?
- **Reflected damage (SK-22)** — if someone attacks a sleeping entity that has damage reflection... does the hit break sleep first, then reflection fires?

## Cross-Boundary Concerns

TODO: Sleep is applied via relay to the target's owning Arbiter. The owning Arbiter manages the break condition. Any damage event arriving on the sleeping entity — from local sources or cross-boundary relays — must check sleep status. The break is local to the owning Arbiter. The concern: if a DoT is ticking on the target from a caster on a different Arbiter, the DoT pulse arrives as a relay and triggers the break check.

## Compiler Requirements

TODO: Designer specifies: CC type (sleep — hard disable with break condition), duration (5s), capability suppression (all), break condition (any damage taken), interrupts channels, DR category (hard CC), tenacity-reducible, cleansable. Compiler produces: status effect with capability flags + break condition trigger registered in the damage resolution path. The compiler needs to express "on incoming damage, remove this effect before damage applies."

## Open Questions

- Does the damage that breaks sleep benefit from the target being "disabled" (bonus damage to CC'd targets)?
- Is there a minimum damage threshold to break sleep (to prevent 1-damage ticks from breaking it)?
- Does sleep break on damage-over-time application (when the DoT is first applied) or on each tick?
- If the sleeping entity is shielded (SK-17), does damage absorbed by the shield count as "taking damage" for break purposes?
- Does sleep break on self-damage (SK-17 Sacrifice Shield's self-damage cost)?
- Can sleep be applied to an entity that is already stunned (stun overrides, or sleep queues)?
- Does the break-on-damage check happen before or after block (SK-21)? If the hit is blocked (no damage), does sleep break?
