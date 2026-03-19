# SK-77: Two Players, One Entity (Cho'Gall)

## Designer Intent

Two players share one body. Player A (Cho) controls movement and has melee/tank abilities. Player B (Gall) controls ranged/damage abilities but has no movement control. They share one HP pool, one position, and one entity — but each has their own ability bar, cooldowns, and input stream.

## Primitive Composition

P-30 (Input Multiplexing) → P-31 (Identity/Loadout Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Two player sessions (two Edge Nodes)
- One shared entity
- Player A: movement input + ability set A
- Player B: ability set B (no movement input)

## Observable Behavior

1. One entity exists on the map with a shared HP pool
2. Player A controls movement — WASD/click-to-move
3. Player A has tank abilities (stun, knockback, charge)
4. Player B has damage abilities (skillshots, AoE, channel)
5. Both players can use abilities simultaneously and independently
6. Both players see through the same entity's position (shared camera)
7. If the entity dies, both players die
8. Both players respawn together at the same time

## Engine Primitives Required

### Two Sessions, One Entity

SK-68 (Multi-Entity Control) breaks one-session-to-one-entity by mapping one session to three entities. Cho'Gall breaks it the OTHER direction: two sessions to one entity.

```
struct DualSessionBinding {
    entity_id: EntityID,
    session_a: SessionBinding,  // Cho — has movement + ability set A
    session_b: SessionBinding,  // Gall — has ability set B only
}
```

The Edge Node model must support:
- Two clients connected to one entity
- Input from both clients arriving at the same Arbiter for the same entity
- Ability proposals from either client accepted and resolved independently
- Movement input from only one client (Cho) accepted; movement from the other (Gall) rejected

### Input Multiplexing

The Arbiter receives proposals from TWO Edge Nodes for the SAME entity. It must:
1. Accept movement input from Session A only (reject movement from Session B)
2. Accept ability proposals from Session A (ability set A) and Session B (ability set B)
3. Validate abilities against the correct ability set per session
4. Both ability sets share the entity's offensive/defensive stats
5. Cooldowns are independent per ability set (Cho's stun cooldown is separate from Gall's skillshot cooldown)

### Shared State, Independent Abilities

Both players share:
- HP pool (one SoftState)
- Position and movement
- Buffs and debuffs applied to the entity
- Defensive stats (both take damage through the same pool)

Each player owns independently:
- Their ability set (different abilities)
- Their cooldowns
- Their ability-specific state (combo counters, charge counts, etc.)

### Token Bucket Fairness

The per-entity token bucket limits proposals per entity. With two players sending proposals for one entity, the bucket depletes twice as fast. Should there be one bucket per entity (shared) or one per session (independent)?

## Cross-Boundary Concerns

TODO: The entity is on one Arbiter, but TWO Edge Nodes connect to it. Both Edge Nodes send proposals to the same Arbiter. Both receive downstream payloads from the same Arbiter.

1. **Both Edge Nodes route to the same Arbiter:** Standard — both send to the entity's Arbiter.
2. **Entity crosses a boundary:** Both Edge Nodes must be notified of the new Arbiter. Both redirect simultaneously.
3. **Edge Node crash:** If Cho's Edge Node crashes, the entity can't move (no movement input). Gall can still cast. The entity is stranded but alive.
4. **Edge Node disconnect:** Reconnection must restore the dual-session binding. Both players must reconnect to the same entity.

## Compiler Requirements

TODO: Designer specifies: dual-player entity, per-player ability sets (A and B), movement restricted to player A, shared HP/stats, independent cooldowns per set. Compiler produces:
- Entity definition with two ability sets and session-role assignments
- Input routing rules: movement from role A only, abilities from respective roles
- Dual-session spawn handshake (Meta creates one entity bound to two sessions)
- Per-role ability validation in validate_intent hook

This likely requires `docs-core/` changes — the session model assumes one session per entity.

## Open Questions

- Can Cho and Gall cast abilities at the exact same tick (simultaneous proposals)?
- If both cast abilities that conflict (Cho charges forward, Gall channels — channel requires immobility), who wins?
- Does the entity count as one or two for Arbiter entity_count / split triggers?
- Can SK-40 Mind Control affect Cho'Gall — does it override Cho's movement, Gall's abilities, or both?
- Can SK-26 Silence affect only one player's abilities (silence Gall but not Cho)?
- If one player disconnects, can the other player solo-pilot with reduced capabilities?
- How does the spawn handshake work — does Meta create one entity or two sessions simultaneously?
- Does each player have independent CC tracking (stun affects both, but DR tracks per-player or per-entity)?
- Can SK-54 Entity Consumption swallow Cho'Gall (two players consumed together)?
- Performance: two input streams for one entity — double the proposal rate, double the validation cost
