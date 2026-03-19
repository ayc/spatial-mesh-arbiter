# SK-65: Taunt

## Designer Intent

I taunt all nearby enemies for 1.5 seconds. Taunted enemies are forced to auto-attack me — they can still move freely and use non-auto-attack abilities, but their basic attacks MUST target me. They cannot choose a different auto-attack target.

## Primitive Composition

P-03 (Trajectory Steering) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the taunter)
- No target required (AoE centered on caster)

## Observable Behavior

1. Cast — all enemies within radius are taunted for 1.5 seconds
2. Taunted enemies' auto-attacks are redirected to the taunter
3. Taunted enemies CAN still move (they can walk away, walk toward, etc.)
4. Taunted enemies CAN still cast abilities (they're not silenced)
5. Taunted enemies CANNOT choose a different auto-attack target — all auto-attacks must target the taunter
6. If the taunter dies during taunt: taunt breaks immediately
7. If the taunted entity moves out of auto-attack range: they stop auto-attacking (but taunt persists — if they move back in range, they auto-attack the taunter again)
8. Duration reduced by Tenacity
9. Subject to Diminishing Returns (SK-28)
10. Cleansable by SK-15 Purify
11. Visual: rage/aggro effect on taunted enemies, "Taunted" indicator pointing to the taunter

## Engine Primitives Required

### New CC Type: Taunt (Forced Target)

Taunt is distinct from all existing CC types:

| CC Type | Can Move? | Can Attack? | Can Cast? | Target Override? |
|---|---|---|---|---|
| Stun (SK-24) | No | No | No | N/A |
| Root (SK-25) | No | Yes | Yes | No |
| Silence (SK-26) | Yes | Yes | No | No |
| Blind (SK-50) | Yes | Yes (miss) | Yes | No |
| **Taunt (SK-65)** | **Yes** | **Yes** | **Yes** | **Yes — forced to taunter** |

Taunt doesn't disable any capability — it overrides the target selection for auto-attacks. The taunted entity's Edge Node might send input targeting a different enemy, but the Arbiter overrides the auto-attack target to the taunter.

```
status_effect: TauntDebuff {
    forced_target_id: EntityID,  // The taunter — all auto-attacks must target this entity
    expires_at_tick: u64,
    breaks_on_taunter_death: bool,
}
```

### Auto-Attack Target Override

During the Arbiter's resolution of auto-attacks for a taunted entity:
1. The entity's intended auto-attack target is ignored
2. The auto-attack target is replaced with `forced_target_id`
3. Range check is still performed — if the taunter is out of range, the auto-attack doesn't fire (but taunt persists)
4. The auto-attack goes through normal resolution (can crit, can trigger on-hit procs, can be blocked/evaded)

This is a **proposal mutation** — the Arbiter rewrites the target of an incoming ActionProposal before resolution. This is different from all other CC types which suppress capabilities rather than modify inputs.

### Taunter Death Break

If the taunter dies, all taunt debuffs referencing their EntityID must be immediately removed. The Arbiter needs to track "which entities are currently taunted by EntityID X" so that on X's death, all taunts are cleared.

This is similar to SK-64 Mosh Pit's "channel end → remove all stuns" — but triggered by death rather than channel break.

### Interaction with Auto-Targeting

SK-42 Withering Fire auto-targets the nearest enemy hero. If the Withering Fire user is taunted, does the taunt override the auto-targeting? The taunted entity's auto-attacks must go to the taunter, but Withering Fire is ability-based auto-targeting, not a basic auto-attack. Design choice: does taunt affect ability-based attacks or only true auto-attacks?

## Cross-Boundary Concerns

TODO: If the taunter and taunted entity are on different Arbiters:

1. Taunt is applied via standard CC relay to the target's Arbiter.
2. The target's Arbiter enforces the auto-attack target override locally.
3. The target's auto-attacks now target the taunter — who is a Ghost from the target's Arbiter's perspective. Auto-attack damage is relayed cross-boundary to the taunter's Arbiter.
4. On taunter death: the taunter's Arbiter broadcasts a death event. The target's Arbiter must detect "my taunter died" and remove the taunt. This requires the death event to propagate cross-boundary.

The death-break relies on timely cross-boundary death notification. If there's a few ticks of delay, the taunted entity might continue attacking a dead entity's Ghost before the taunt clears.

## Compiler Requirements

TODO: Designer specifies: AoE radius, duration (1.5s), forced auto-attack target (caster), does not affect movement or casting, breaks on taunter death, Tenacity-reducible, DR category, cleansable. Compiler produces:
- Snapshot AoE query for enemies in radius (like SK-20 Battle Cry)
- TauntDebuff status effect with forced_target_id
- Auto-attack target override in the proposal resolution path
- Death-break hook: taunter death → remove all taunts referencing their EntityID
- CC classification: Taunt is its own category for DR purposes

The compiler needs to add Taunt to the CC type system. Taunt is unique because it modifies intent (target selection) rather than suppressing capability.

## Open Questions

- Does taunt affect abilities that happen to be targeted (SK-02 Poison Shot), or only true auto-attacks?
- Can an entity be taunted by multiple sources? If so, which taunter takes priority (most recent? closest?)?
- Does taunt force the entity to WALK toward the taunter if out of range, or just redirect attacks if in range?
- Does SK-50 Blind interact with taunt — taunted + blinded = forced to auto-attack but attacks miss?
- Does taunt affect SK-06 Summon Swarm minions (redirect their AI targeting)?
- Does SK-51 Unstoppable prevent taunt?
- If the taunted entity uses SK-35 Blink Strike to teleport away, does taunt persist (they blink, then their auto-attacks still target the taunter if in range)?
- Can a taunted entity use SK-44 Burrow to avoid auto-attacking (burrow = can't act, so taunt is moot)?
- Does the auto-attack override happen at the Edge Node (prediction) or only at the Arbiter (authority)?
- How does taunt interact with SK-40 Mind Control — mind control overrides ALL input, taunt only overrides auto-attack target?
