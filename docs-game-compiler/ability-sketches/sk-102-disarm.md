# SK-102: Disarm

## Designer Intent

I curse nearby enemies so they can't auto-attack for 2 seconds. They can still move freely and cast abilities — only their basic attacks are disabled. This shuts down auto-attack-reliant enemies while leaving casters mostly unaffected.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- AoE centered on caster (or targeted)

## Observable Behavior

1. Cast — enemies in radius are disarmed for 2 seconds
2. Disarmed enemies CANNOT auto-attack (basic attacks are blocked)
3. Disarmed enemies CAN move (full movement control)
4. Disarmed enemies CAN cast abilities (all abilities functional)
5. Duration reduced by Tenacity
6. Subject to Diminishing Returns (SK-28) — soft CC category
7. Cleansable by SK-15 Purify
8. Visual: weapon-broken icon, disarmed enemies show a "no attack" indicator

## Engine Primitives Required

### New CC Type: Disarm

Complete CC capability matrix with Disarm added:

| CC Type | Can Move? | Can Attack? | Can Cast? | Other |
|---|---|---|---|---|
| Stun (SK-24) | No | No | No | Full disable |
| Root (SK-25) | No | Yes | Yes | Movement disable |
| Silence (SK-26) | Yes | Yes | No | Cast disable |
| Blind (SK-50) | Yes | Yes (miss) | Yes | Attack miss |
| Taunt (SK-65) | Yes | Yes (forced) | Yes | Target override |
| Fear (SK-78) | Yes (forced) | No | No | Forced flee |
| Charm (SK-101) | Yes (forced) | No | No | Forced approach |
| **Disarm (SK-102)** | **Yes** | **No** | **Yes** | **Attack disable** |

Disarm is the complement of Silence:
- Silence: can attack, can't cast
- Disarm: can't attack, can cast

Together, silence + disarm = stun (with movement). Individually, they target different playstyles.

```
status_effect: DisarmDebuff {
    expires_at_tick: u64,
}
```

The flag is simple: `can_attack: false` while `can_move: true, can_cast: true`.

### Auto-Attack vs Ability Classification (Revisited)

SK-50 Blind already required distinguishing auto-attacks from abilities. Disarm uses the same classification:
- **Auto-attack**: the entity's basic/default attack action. Blocked by Disarm.
- **Ability**: an explicitly activated skill. NOT blocked by Disarm.

The Arbiter rejects auto-attack proposals while the entity has `DisarmDebuff`. Ability proposals are accepted normally.

### Interaction With Auto-Attack-Enhancing Abilities

Some abilities modify or empower the next auto-attack (like SK-83 Next-Cast Empowerment applied to auto-attacks). If disarmed:
- The empowerment buff sits unused (can't auto-attack to consume it)
- Empowerment timer might expire while disarmed (wasted)
- If the empowerment changes the attack into an "ability" (like a special strike), does disarm block it? Design choice: empowered auto-attacks are still auto-attacks → blocked.

## Cross-Boundary Concerns

TODO: Standard CC relay pattern. Disarm is applied to the target's entity as a status effect. The target's Arbiter enforces the auto-attack block locally. No special cross-boundary handling.

## Compiler Requirements

TODO: Designer specifies: AoE CC, duration (2s), disarm (blocks auto-attacks only), does not affect movement or abilities, Tenacity-reducible, DR category (soft CC), cleansable. Compiler produces:
- DisarmDebuff status effect with `can_attack: false`
- Auto-attack validation check: reject auto-attack proposals while disarmed
- Ability proposals unaffected

The compiler adds Disarm to the CC type system. The capability flag system now has: `can_move`, `can_attack`, `can_cast` as independently suppressible flags.

## Open Questions

- Does disarm block SK-42 Withering Fire (charge-based auto-targeting)? Is it an "auto-attack" or "ability"?
- Does disarm block SK-13 Counter-Strike (automatic counter-attack on block)? Counter is triggered by being hit, not by attacking.
- Does disarm affect SK-06 Summon Swarm minions' auto-attacks (disarm the owner → minions stop attacking)?
- Can disarm and silence be applied simultaneously? (Effectively a stun that allows movement)
- Does disarm prevent SK-23 Thorns from triggering? (Thorns triggers on being HIT, not on attacking)
- How does disarm interact with SK-65 Taunt (forced to auto-attack → but can't auto-attack)? Which wins?
- Does disarm block attack-move commands (move + auto-attack nearest)?
- Is there a visual distinction between "can't attack" (disarm) and "attacks miss" (blind)?
