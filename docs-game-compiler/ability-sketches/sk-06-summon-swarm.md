# SK-06: Summon Swarm

## Designer Intent

My character summons 6 small minions around me. Each minion autonomously attacks the nearest enemy for 15 seconds, then expires. If I move, they follow me. If I die, they die.

## Primitive Composition

P-32 (Actor Spawning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (minions spawn around caster position)

## Observable Behavior

1. 6 minion entities spawn in a circle around the caster
2. Each minion acquires the nearest enemy and attacks autonomously (basic melee/ranged attack)
3. Minions follow the caster if no enemy is in range
4. Minions have their own HP and can be killed
5. After 15 seconds, surviving minions expire and despawn
6. If the caster dies, all minions immediately die
7. Each minion's attack deals damage and can trigger on-hit effects from the caster's stats

## Engine Primitives Required

TODO: Minting 6 new EntityIDs, inserting them into the Arbiter's entity map, assigning Arbiter-local AI FSM (simple: idle → chase → attack → follow-caster), lifecycle management (expiry timer, caster-death binding). What are the minions' stats — derived from caster? Fixed from SpellData?

## Cross-Boundary Concerns

TODO: If the caster crosses an Arbiter boundary, the minions need to follow — are they handed off as a group? What if some minions are near the boundary and some aren't? Each minion is an independent entity — does each get its own handoff? If a minion attacks a Ghost, the damage relays to the Ghost's owner. 6 minions × 60Hz = significant entity density increase — could this push the Arbiter toward a split threshold?

## Compiler Requirements

TODO: What does the designer write to define a minion — stats, AI behavior, attack pattern, lifetime? How does the compiler produce the FSM and stat block? Does the compiler validate that the summon count is bounded?

## Open Questions

- Do minions count toward the Arbiter's entity_count for split trigger purposes?
- Is there a maximum summon count per caster (to prevent entity flooding)?
- Can minions be targeted by enemies? Do they have collision?
- Do minions inherit any of the caster's stats/buffs, or are they fully independent?
- What happens if the caster summons again while previous minions are alive — replace, or stack?
- How does the Commander Pattern (docs/1-architecture/02-npc-architecture.md) relate to minion control?
- Performance: what is the per-entity cost of 6 additional FSMs ticking at 60Hz?
