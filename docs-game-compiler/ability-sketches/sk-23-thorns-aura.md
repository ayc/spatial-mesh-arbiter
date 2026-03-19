# SK-23: Thorns Aura

## Designer Intent

Passive: whenever an enemy hits me with a melee attack, they take flat damage back. This damage is not based on how much they hit me for — it's a fixed amount derived from my stats. Ranged attacks and spells do not trigger thorns.

## Primitive Composition

P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Incoming melee attack event
- Defender's thorns damage value (derived stat or flat from item/buff)
- Attacker entity (must be melee range)

## Observable Behavior

1. Enemy hits me with a melee attack
2. Regardless of whether the attack is blocked, evaded, or mitigated — thorns fires
3. Attacker takes flat X damage (based on my thorns stat, not the incoming damage)
4. Thorns damage type is fixed (e.g., physical, or "true" — bypasses armor)
5. Thorns damage is mitigated by the attacker's defensive stats (unless true damage)
6. Thorns can trigger on-hit procs on the attacker (they are "taking damage from me")
7. Visual: spike/thorn burst effect on the defender when triggered

## Engine Primitives Required

TODO: Thorns is evaluated during Phase 2 after the "was I hit?" determination. Unlike block (which prevents damage) and reflection (which scales with damage), thorns fires on any melee hit regardless of outcome. The thorns damage is a fixed value, not derived from the incoming damage. This means thorns can fire even if the attack was fully absorbed by a shield (SK-17) — the entity was still "hit." The thorns damage is a new outgoing event from the defender to the attacker. Already partially spec'd in T1-06 (reactive proc cascade).

## Interaction With Other Defensive Mechanics

Thorns has the simplest interaction model because it doesn't care about the incoming damage amount:
- **Block (SK-21)** — does thorns fire on a blocked hit? The hit was blocked (no damage), but the entity was still targeted by a melee attack. Design choice.
- **Evasion** — if evaded, no hit occurred. Thorns should NOT fire on evaded attacks (the attack missed).
- **Shield (SK-17)** — shield absorbs the damage, but the entity was still hit. Thorns fires.
- **Reflection (SK-22)** — thorns and reflection are independent. Both can fire on the same hit. Thorns sends flat damage, reflection sends percentage-based damage. Attacker takes both.
- **Guardian Angel (SK-19)** — if damage is redirected, who triggers thorns? The ward was hit (thorns fires from ward). The guardian takes redirected damage but was not "hit by a melee attack" — so guardian's thorns should NOT fire.

## Cross-Boundary Concerns

TODO: Same reverse relay as SK-13 and SK-22 — the defender's Arbiter emits a thorns damage event targeting the attacker, relayed to the attacker's Arbiter for Phase 2. Thorns is specifically melee-only, which implies a range check — the attacker must be within melee range. Since the attacker's position might be approximate (Ghost), is the melee range check done on the defender's Arbiter using Ghost position, or is it implicit (the original attack was classified as melee by the attacker's Arbiter)?

## Compiler Requirements

TODO: Designer specifies: trigger (on melee hit received), thorns damage (flat value or derived stat), damage type, melee-only filter. Compiler produces: Phase 2 reactive trigger + outgoing damage event + attack type filter. The compiler must tag the outgoing thorns event with proc_depth to prevent infinite loops (attacker has thorns too → defender's thorns triggers attacker's thorns → infinite).

## Open Questions

- Does thorns trigger on blocked hits? On shielded hits?
- Does thorns trigger once per attack, or once per hit (multi-hit abilities)?
- Can thorns damage crit?
- Can thorns damage trigger the attacker's own thorns (mutual thorns → infinite loop bounded by proc_depth)?
- Can thorns damage trigger on-hit procs on the attacker (SK-09 Chain Lightning, SK-02 Poison)?
- Does thorns trigger on DoT ticks, or only on direct attacks?
- Is the melee-only restriction a range check, or an attack-type classification from the attacker's Arbiter?
- If multiple thorns sources are active (buff + item + passive), do they stack additively?
- How does thorns interact with SK-06 Summon Swarm — if a summoned minion melees me, does thorns hit the minion or the summoner?
