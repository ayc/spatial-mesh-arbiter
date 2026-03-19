# SK-38: Contagion

## Designer Intent

I throw a cursed dagger at an enemy. It deals initial damage and applies a spreading debuff. After 2 seconds, the debuff jumps to all enemies within range of the infected target. Each newly infected enemy can spread it again after another 2 seconds. The spread continues until no new targets are in range or a maximum generation is reached.

## Primitive Composition

P-44 (Pulse Timer) → P-09 (Shape Overlap Query) → P-35 (On-Hit Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Dagger hits target — initial damage + Contagion debuff applied
2. Contagion debuff deals damage over time while active (4 seconds per application)
3. After 2 seconds: the debuff autonomously spreads to all enemies within spread radius of the carrier
4. Newly infected enemies get their own Contagion debuff (fresh 4-second duration)
5. After 2 seconds on each new carrier: it spreads again to nearby uninfected enemies
6. An entity can only be infected once per cast (no re-infection from the same contagion chain)
7. Maximum 4 generations of spreading (initial target = gen 0, their spread = gen 1, etc.)
8. Visual: sickly green glow on infected targets, visible spread wave when it jumps

## Engine Primitives Required

TODO: The contagion debuff is a **status effect with an autonomous timer and spatial query**. Unlike procs (which trigger in response to external events), contagion triggers on its own internal timer — no external damage or action is needed. The Arbiter must:

1. Apply the initial debuff with metadata: `{ cast_id: UUID, generation: 0, spread_at_tick: current_tick + 120 }`
2. Each tick: check if any contagion effect has reached its `spread_at_tick`
3. On spread: perform spatial query for "enemies within spread radius of this carrier"
4. Filter: exclude entities that already have a contagion debuff with the same `cast_id`
5. Apply new contagion debuff to each result with `generation + 1`
6. If `generation >= max_generations`: this instance doesn't spread (terminal)

The `cast_id` is critical — it prevents re-infection within the same chain but allows a second cast from the same or different caster to infect independently.

### Self-Sustaining Effect
This is the first ability where a status effect **actively performs spatial queries and creates new effects on other entities** without any involvement from the caster. The effect is an autonomous agent. This has implications for:
- Who "owns" the damage from spread infections? (The original caster, for kill credit?)
- Which Arbiter runs the spread logic? (The carrier's Arbiter, not the caster's)
- The CombatContext for spread damage — is it pre-rolled at cast time, or re-evaluated at each spread?

## Cross-Boundary Concerns

TODO: The spread query happens on the carrier's Arbiter. Nearby enemies might be Ghosts. Spreading to a Ghost requires a relay to the Ghost's owning Arbiter to apply the contagion debuff. If the contagion then spreads from that newly infected entity, THAT Arbiter runs the next spread. A single contagion chain could cascade across 3-4 Arbiters, with each generation running independently on whichever Arbiter hosts the carrier.

The `cast_id` dedup must work cross-boundary — if Arbiter A spreads to a Ghost on Arbiter B, and Arbiter B's entity is also near a Ghost on Arbiter A, the `cast_id` check prevents re-infection back to Arbiter A's entities.

## Compiler Requirements

TODO: Designer specifies: initial hit damage, DoT damage/duration, spread delay (2s), spread radius, max generations (4), infection dedup (per cast_id). Compiler produces: status effect definition with autonomous timer + spatial query + child effect spawning + generation tracking + dedup via cast_id. The compiler validates that spread is bounded (max generations finite) and that the spatial query is performed on the carrier's Arbiter.

## Open Questions

- Does the DoT damage from spread infections use the caster's original offensive stats or the carrier's stats?
- Can contagion spread to stealthed/invisible entities?
- Does SK-15 Purify remove contagion AND prevent re-infection (immunity window blocks re-spread)?
- If a carrier dies, does the contagion still spread at the scheduled tick (spread from corpse position)?
- Can contagion spread to allied entities (friendly fire variant)?
- Does the spread respect line of sight, or does it jump through walls?
- How does contagion interact with SK-17 Sacrifice Shield — does the DoT tick against the shield?
- Performance: in a dense group, gen 0 → gen 1 could infect 20+ enemies, each of which does a spatial query 2 seconds later. What's the worst-case query count?
- Can multiple contagion casts from different casters infect the same entity simultaneously (different cast_ids)?
