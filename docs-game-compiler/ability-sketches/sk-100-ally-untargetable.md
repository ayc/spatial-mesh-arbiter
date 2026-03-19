# SK-100: Ally-Untargetable

## Designer Intent

My character is a massive dragon that is PERMANENTLY immune to all crowd control. However, as a tradeoff, my allies CANNOT target me with any beneficial effects — no heals, no shields, no buffs, no cleanses. I'm on my own. I must self-sustain through my own abilities. Enemies can target and damage me normally.

## Primitive Composition

P-27 (Targetability Overrides) → P-62 (Categorized CC Immunity)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- No input (permanent passive trait)

## Observable Behavior

1. Permanent: always immune to all CC (stuns, roots, silences, slows, fear, taunt, displacement, sleep — everything)
2. Permanent: allies cannot target me with any ability (heals, shields, buffs, cleanses all fail)
3. Enemies CAN target and damage me normally (I'm not invulnerable)
4. I CAN target allies with my own abilities (if I have ally-targeted abilities)
5. I have my own self-sustain abilities to compensate for lack of ally healing
6. This is my identity — it's always on, cannot be toggled off
7. Visual: massive model, no healing indicators from allies, self-sufficient aesthetic

## Engine Primitives Required

### Selective Targeting Flags

The current targeting flag set:
- `is_untargetable`: excluded from ALL targeting queries (SK-44 Burrow)

SK-100 requires splitting this into per-team targeting:

```
struct TargetingFlags {
    targetable_by_enemies: bool,   // true — enemies can hit me
    targetable_by_allies: bool,    // false — allies CANNOT target me
    targetable_by_self: bool,      // true — my own abilities work on me
}
```

Every ability that targets an entity must check:
1. Is the target valid for this ability? (enemy-targeted vs ally-targeted)
2. Is the target `targetable_by_X` where X = the caster's relationship to the target?

For enemy abilities: check `targetable_by_enemies` → true → allow.
For ally abilities: check `targetable_by_allies` → false → REJECT.
For self abilities: check `targetable_by_self` → true → allow.

### Impact on Every Ally Ability

EVERY ally-targeted ability in the game must check `targetable_by_allies`:
- SK-15 Purify: cannot cleanse this entity (can't target)
- SK-16 Holy Ground: heal pulses skip this entity (ally spatial query excludes it)
- SK-17 Sacrifice Shield: cannot shield this entity
- SK-19 Guardian Angel: cannot mark this entity for damage redirect
- SK-20 Battle Cry: buff application skips this entity
- SK-04 Tether: cannot tether to this entity
- SK-93 Death Prevention: cannot place the buff on this entity
- SK-94 Placed Potion: this entity cannot pick up potions (ally collection blocked)
- SK-60 Bunker: this entity cannot enter (ally interaction blocked)
- SK-69 Portal Pair: this entity cannot use portals (ally interaction blocked)
- SK-98 Mobile Transport: this entity cannot board (ally entry blocked)

This is a SYSTEM-WIDE exclusion — every ally-targeted spatial query and every ally-targeted ability must check this flag.

### Permanent CC Immunity

SK-51 Unstoppable is a temporary buff. SK-100 is PERMANENT — the `is_unstoppable` flag is always true, not tied to a status effect with a duration. This simplifies implementation (no effect to manage) but means:
- CC abilities that hit this entity: damage applies, CC is stripped (same as SK-51)
- DR (SK-28) tracking is irrelevant (CC never applies)
- SK-24 Stun, SK-25 Root, SK-26 Silence, SK-27 Sleep, SK-28 Slow, SK-50 Blind, SK-65 Taunt, SK-78 Fear, SK-40 Mind Control, SK-88 Positional Leash — ALL rejected

### Self-Sustain Requirement

Because allies can't heal this entity, the entity MUST have self-healing abilities to survive:
- Self-heal on ability casts
- Lifesteal/drain from damage dealt
- Passive regeneration
- Self-shielding

The entity's stat block and ability set must be designed for self-sufficiency. This is a compiler/design constraint, not an engine primitive.

### Ghost Representation

When this entity is a Ghost on a neighboring Arbiter, the Ghost data should carry the `targetable_by_allies: false` flag. This way, allies on the neighbor's Arbiter don't waste relay messages trying to heal/buff a Ghost that will reject the effect.

Currently, GhostUpdate doesn't carry targeting flags. This would need to be added — or the ally's Arbiter accepts the wasted relay and the target's Arbiter rejects it.

## Cross-Boundary Concerns

TODO: The ally-untargetable flag affects cross-boundary interactions:

1. **Ally on Arbiter A tries to heal this entity (Ghost on A):** The ally's Arbiter checks the Ghost's targeting flags. If the Ghost carries `targetable_by_allies: false`, the ability is rejected LOCALLY — no relay needed. If the Ghost doesn't carry the flag, the relay is sent and rejected on the target's Arbiter (wasted traffic).

2. **Ally AoE (SK-20 Battle Cry) near this entity:** The spatial query for allies must exclude entities with `targetable_by_allies: false`. If the entity is a Ghost, the query must check the Ghost's flags.

3. **Enemy AoE near this entity:** Normal processing — `targetable_by_enemies: true`.

Adding targeting flags to GhostUpdate avoids wasted cross-boundary relays. Without it, every ally heal attempt on this entity generates a relay → reject → waste.

## Compiler Requirements

TODO: Designer specifies: permanent trait, always CC-immune (unstoppable), allies cannot target with any beneficial effect, enemies target normally, self-abilities work normally. Compiler produces:
- Entity profile with permanent targeting flags: `{ targetable_by_enemies: true, targetable_by_allies: false, targetable_by_self: true }`
- Permanent `is_unstoppable: true` (not a status effect — hardcoded in entity state)
- Every ally-targeted ability's validation must check `targetable_by_allies`
- Ghost representation must carry targeting flags (or accept wasted relays)

The compiler needs to support **per-team targeting flags** on entity definitions. This is a new entity property that affects every targeting query in the game.

### docs-core/ Impact

This likely requires a `docs-core/` change:
- `docs-core/01-spatial-runtime-kernel.md`: entity state includes per-team targeting flags
- `docs-core/02-spatial-messaging-plane.md`: Ghost representation may need targeting flag fields
- The game adapter interface must support per-entity targeting flags in the entity schema

## Open Questions

- Can the entity target ITSELF with abilities (self-heal, self-shield)?
- If an ally's AoE ACCIDENTALLY includes this entity (SK-29 Blizzard from a team fight), does the damage portion apply (friendly fire) or is the entity excluded entirely?
- Can this entity use SK-69 Portal Pair (portals are ally-usable structures)?
- Does SK-91 Team-Agnostic Stasis affect this entity (it hits ALL entities regardless of team)?
- Can this entity be consumed by an ally's SK-54 Entity Consumption (is consumption "targeting")?
- If this entity has SK-08 Aura, does the aura affect allies (the entity can't be TARGETED by allies, but can the entity's effects APPLY to allies)?
- Can this entity receive the benefit of SK-20 Battle Cry if they're in range (passive AoE buff that doesn't require targeting)?
- Does the permanent CC immunity make the entity immune to SK-91 Stasis (which is "uncleansable" — does unstoppable override stasis)?
- How does this entity interact with SK-77 Two-Player Entity (can one head be ally-untargetable)?
- Should the flag be part of the entity's compiled profile (SpellData) or a runtime state flag?
