# SK-50: Blind

## Designer Intent

I flash a blinding light at enemies in a cone. For 2 seconds, their auto-attacks miss completely — no damage, no on-hit effects. Abilities are unaffected. Only basic/auto attacks are blinded.

## Primitive Composition

P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (for cone targeting — can combine with SK-49 Cone Strike)

## Observable Behavior

1. Enemies in the cone are blinded for 2 seconds
2. While blinded: auto-attacks miss 100% of the time
3. Miss means: no damage dealt, no on-hit effects trigger, attacker sees "Miss!" indicator
4. Abilities are NOT affected — only auto-attacks
5. Blind does not prevent movement, casting, or any action — it only causes auto-attacks to whiff
6. Duration reduced by Tenacity
7. Subject to Diminishing Returns (SK-28) — in the soft CC category
8. Cleansable by SK-15 Purify
9. Visual: bright flash, blinded enemies have a visual indicator (darkened screen/stars)

## Engine Primitives Required

### New CC Type: Blind

Blind is distinct from all existing CC types:
- Stun (SK-24): blocks everything
- Root (SK-25): blocks movement only
- Silence (SK-26): blocks casting only
- Sleep (SK-27): blocks everything, breaks on damage
- Slow (SK-28): reduces movement speed

Blind: **causes auto-attacks to miss**. It doesn't block the attack — the blinded entity still performs the attack animation, still consumes attack cooldown/timing, but the attack doesn't connect.

The miss check happens during Phase 1 (offense resolution) on the ATTACKER's Arbiter:
1. Attacker performs auto-attack
2. Check: does the attacker have a Blind debuff?
3. If yes: attack result = Miss. No CombatContext is generated. No damage. No on-hit procs.
4. If no: normal hit/crit resolution continues.

### Miss vs Block vs Evasion

Three ways an attack can fail to deal damage:
- **Evasion** (defender stat): checked on the defender, the attack doesn't land. No on-hit effects for the attacker.
- **Block** (SK-21, defender): checked on the defender, the attack lands but damage is negated. On-block procs fire.
- **Blind** (attacker debuff): checked on the attacker, the attack whiffs before it even reaches the defender. Nothing fires.

Blind is the earliest check in the pipeline — it happens before the attack generates a CombatContext. Block and evasion happen during Phase 2 on the defender. Blind short-circuits Phase 1 on the attacker.

### Auto-Attack vs Ability Classification

Blind only affects auto-attacks, not abilities. The engine needs a definitive classification:
- **Auto-attack**: the default attack action, continuous, no explicit ability activation
- **Ability**: an explicitly activated skill from the ability bar

This classification must be deterministic. When the Arbiter processes an attack, it needs to know: "is this an auto-attack or an ability?" to apply the blind check.

## Cross-Boundary Concerns

TODO: Blind is a debuff applied to an enemy. If the target is a Ghost, the blind is relayed to the target's owning Arbiter. The owning Arbiter applies the blind and enforces the miss check locally — all the blinded entity's auto-attacks miss on their own Arbiter. No special cross-boundary handling needed for the miss resolution itself.

The cone application (if combined with SK-49) has the same cross-boundary concerns as any AoE near a boundary.

## Compiler Requirements

TODO: Designer specifies: CC type (blind), duration (2s), affects auto-attacks only, causes 100% miss, does not affect abilities, Tenacity-reducible, DR category (soft CC), cleansable. Compiler produces:
- Status effect with `is_blinded: true` flag
- Phase 1 check: if attacker `is_blinded` and attack is auto-attack → result = Miss, skip CombatContext generation
- Auto-attack classification tag on attack action types

The compiler needs to add Blind to the CC type system alongside Stun, Root, Silence, Sleep, Slow. Each CC type defines which capability it affects and where in the pipeline it's checked.

## Open Questions

- Does blind affect abilities that "enhance" auto-attacks (e.g., an ability that empowers the next auto-attack)?
- Does blind cause abilities with auto-attack components to miss (some abilities include an auto-attack as part of their sequence)?
- Can blind chance be less than 100% (e.g., 50% miss chance as a weaker version)?
- Does the miss consume the attack's cooldown/timing, or does the blinded entity get to "re-try"?
- Does blind interact with SK-42 Withering Fire (charge-based auto-targeting)? Is Withering Fire an "auto-attack" or an "ability"?
- Does the miss trigger any on-miss effects (some games have "on miss" procs)?
- Does blind work against SK-06 Summon Swarm minions' auto-attacks?
- How does blind interact with SK-13 Counter-Strike — if the auto-attack misses, there's no hit to block, so Counter-Strike can't trigger.
- Does blind stack from multiple sources (two blinds = still 100% miss)?
