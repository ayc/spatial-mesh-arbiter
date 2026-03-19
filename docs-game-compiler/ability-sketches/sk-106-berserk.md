# SK-106: Berserk

## Designer Intent

I launch a wave of madness. Enemies hit go berserk for 2.5 seconds — they uncontrollably auto-attack their OWN ALLIES. They can't choose targets, they just lash out at the nearest teammate. If no allies are nearby, they auto-attack nothing (stand still, berserked). After the berserk ends, they regain control.

## Primitive Composition

P-28 (Hostility Inversion) → P-03 (Trajectory Steering) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- AoE or skillshot delivery (projectile wave)

## Observable Behavior

1. Wave hits enemies — berserk applied for 2.5 seconds
2. Berserked enemies auto-attack the nearest ALLY (their own teammate)
3. Berserked enemies deal their normal auto-attack damage to their own ally
4. Berserked enemies cannot move voluntarily, cast abilities, or choose targets
5. If no ally is within auto-attack range: berserked enemy stands still (no target)
6. The forced attacks use the berserked entity's own offensive stats
7. The attacked ally takes real damage (this is actual friendly fire)
8. Duration reduced by Tenacity
9. Subject to Diminishing Returns (SK-28) — hard CC category
10. Cleansable by SK-15 Purify
11. Visual: red rage effect, berserked enemies visibly hitting their own allies

## Engine Primitives Required

### New CC Type: Berserk (Forced Friendly Fire)

Complete CC targeting matrix with Berserk:

| CC Type | Movement | Attacks | Target Override |
|---|---|---|---|
| Stun (SK-24) | Blocked | Blocked | N/A |
| Taunt (SK-65) | Free | Forced (toward caster) | Attack caster |
| Fear (SK-78) | Forced away | Blocked | N/A |
| Charm (SK-101) | Forced toward | Blocked | N/A |
| **Berserk (SK-106)** | **Blocked** | **Forced (toward own ally)** | **Attack nearest ally** |

```
status_effect: BerserkDebuff {
    expires_at_tick: u64,
}
```

Each tick while berserked:
1. Find nearest ALLY of the berserked entity within auto-attack range
2. If found: force auto-attack against that ally
3. If not found: stand still (no movement, no attacks)
4. Block all voluntary movement and ability usage

### Team Allegiance Inversion for Targeting

The berserked entity's auto-attack targeting is INVERTED:
- Normally: auto-attack targets enemies
- Berserked: auto-attack targets allies

The Arbiter must:
1. Query for the nearest ALLY (same team) within auto-attack range
2. Generate an auto-attack proposal targeting the ally
3. Resolve the auto-attack normally (the ally takes damage through their own Phase 2 defenses)

The damage is "real" — it's the berserked entity's offensive stats vs their ally's defensive stats. On-hit procs from the berserked entity trigger on the ally (SK-09 Chain Lightning could chain to more allies).

### Friendly Fire Resolution

Normally, the engine prevents friendly fire — damage from allied sources is rejected. Berserk REQUIRES the engine to allow damage from an allied source when the attacker is berserked.

The damage resolution must check: "is the attacker berserked? If yes, allow ally-to-ally damage."

This means the "no friendly fire" rule has an EXCEPTION for berserk status. The engine needs a flag or check:
```
fn is_damage_allowed(attacker: &Entity, target: &Entity) -> bool {
    if same_team(attacker, target) {
        return attacker.has_berserk();  // Friendly fire only if berserked
    }
    true  // Normal enemy damage always allowed
}
```

### On-Hit Procs During Berserk

The berserked entity's auto-attacks are real attacks. Their on-hit effects trigger:
- SK-09 Chain Lightning: could chain from the attacked ally to other allies (spreading the damage)
- SK-02 Poison Shot's drain: berserked entity heals from damaging their own ally
- SK-23 Thorns: the attacked ally's thorns fire back at the berserked attacker (their own teammate)

These interactions are all logically correct but potentially devastating — berserk amplifies the berserked entity's kit against their own team.

## Cross-Boundary Concerns

TODO: The berserked entity attacks its nearest ally. If the nearest ally is a Ghost (on a different Arbiter):
1. The berserked entity's Arbiter generates the auto-attack targeting the Ghost ally
2. Damage is relayed to the ally's owning Arbiter (standard relay)
3. The ally's Arbiter must ACCEPT damage from a same-team source (normally rejected) because the source is berserked

The ally's Arbiter needs to know the attacker is berserked to allow the friendly fire. Options:
- CombatContext carries a `berserk: true` flag
- The ally's Arbiter checks the attacker's debuffs via Ghost data
- The relay includes a "friendly fire authorized" flag

## Compiler Requirements

TODO: Designer specifies: AoE CC, duration (2.5s), forced auto-attack against nearest own ally, cannot move or cast, full disable except forced attacks, Tenacity-reducible, DR category (hard CC), cleansable. Compiler produces:
- BerserkDebuff status effect
- Auto-attack targeting inversion: target nearest ALLY instead of nearest ENEMY
- Friendly fire authorization flag on berserk-generated attacks
- Full capability suppression except forced auto-attacks
- On-hit proc pass-through (procs trigger normally on allied targets)

The compiler adds Berserk to the CC type system. This is the first CC type that creates FRIENDLY FIRE, requiring the engine to support team-damage exceptions.

## Open Questions

- Does the berserked entity's auto-attack crit normally (crits against own allies)?
- Do on-hit procs trigger (SK-09 Chain Lightning chains to more allies)?
- Does the attacked ally's SK-13 Counter-Strike trigger (ally blocks the berserk attack → counter fires at own berserked teammate)?
- Can the berserked entity kill their own ally?
- Does the berserked entity gain benefits from hitting allies (lifesteal, SK-02 drain)?
- Does SK-51 Unstoppable prevent berserk?
- If only one enemy is hit by berserk and they have no nearby allies, do they just stand still?
- Does the berserk auto-attack count as "damage from an enemy" for the ally's defensive procs (SK-87 Conditional Counter)?
- Can the berserked entity be healed by their OWN allies during berserk (the ones they're attacking)?
- How does berserk interact with SK-65 Taunt (taunted to attack caster, berserked to attack ally — which wins)?
