# SK-18: Resurrect

## Designer Intent

I channel for 3 seconds on the corpse of a dead ally. If the channel completes, the ally is revived at the corpse's position with 50% HP and all abilities on cooldown. The ally can immediately act after revival.

## Primitive Composition

P-43 (Charge-Up State) → P-39 (On-Death Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target: a dead ally's corpse (must be in range)

## Observable Behavior

1. Target a dead ally's corpse within range
2. Begin channeling — caster is movement-locked for 3 seconds
3. Channel can be interrupted by stuns, silences, displacement, caster death
4. On channel complete: ally entity is restored at corpse position with 50% max HP
5. Revived ally has all abilities on cooldown (cannot immediately cast)
6. Revived ally has no active buffs or debuffs — clean state
7. If channel is interrupted: ability goes on partial cooldown, ally remains dead
8. Visual: resurrection circle around the corpse, light beam on completion

## Engine Primitives Required

TODO: This is the hardest lifecycle question in the sketches. When an entity "dies," what happens to it in the Arbiter's entity map? Current spec (§9.7) suggests entities are destroyed on death. If destroyed, the corpse is just a position marker — the entity's SoftState, OffensiveStats, and EntityID are gone. Revival means: reconstructing the entity from Meta's persistent state (character data), minting or reusing an EntityID, inserting it into the Arbiter's entity map, and notifying Edge Nodes. This is essentially a mini-spawn handshake.

## Cross-Boundary Concerns

TODO: The dead ally's corpse position might be near or across an Arbiter boundary. The caster channels on their Arbiter, but the revived entity needs to be spawned on whichever Arbiter owns the corpse's position. If the corpse is in a different Arbiter's region, the caster's Arbiter needs to coordinate the revival with the target Arbiter. Also: during the 3-second channel, topology might change (split/merge) — the corpse position could shift ownership.

## Compiler Requirements

TODO: Designer specifies: channel duration (3s), revive HP (50%), cooldown state (all on cooldown), buff state (clean). Compiler produces: channel definition + entity reconstruction request + spawn parameters. How does the compiler express "revive" as an operation — is it a special action type, or does it compose existing primitives (despawn + spawn)?

## Open Questions

- Do dead entities persist in the Arbiter's entity map (with a "dead" state) or are they fully removed?
- If fully removed, how does the game track corpse positions for revival targeting?
- Is the corpse targetable by enemies (e.g., to prevent revival by destroying the corpse)?
- Does the revived entity keep their pre-death equipment/stats, or are stats recompiled from Meta?
- What is the corpse's persistence window — how long after death can an ally be revived?
- Does the revival go through the spawn handshake (Meta → Controller → Arbiter), or is it a local Arbiter operation?
- Can multiple supports attempt to revive the same corpse simultaneously? Who wins?
- How does this interact with the death/respawn lifecycle in the canonical spec (§9.6 of core-concepts)?
- If the ally had a deferred loot claim (§9.10), does revival cancel the deferred recovery flow?
