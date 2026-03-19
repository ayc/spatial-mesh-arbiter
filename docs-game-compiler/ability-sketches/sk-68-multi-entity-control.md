# SK-68: Multi-Entity Control

## Designer Intent

I permanently control three independent characters simultaneously — not as a temporary ability, but as my core gameplay identity. Each character has its own HP, position, abilities, and can die independently. I can select one, two, or all three to issue commands. I can split them across the map to soak multiple lanes.

## Primitive Composition

P-30 (Input Multiplexing) → P-32 (Actor Spawning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- One player session
- Three entities (e.g., Olaf, Baleog, Erik)
- Selection input: select individual, select group, select all
- Each selected entity receives movement and ability input independently

## Observable Behavior

1. Player starts the game with 3 entities, each at the spawn point
2. Each entity has its own HP pool, movement speed, and one unique ability
3. Player can select one entity: movement and ability commands apply to that entity only
4. Player can select all three: movement commands move all three (formation/group movement)
5. Entities can be split across the map — sent to different locations independently
6. Each entity can die independently. Dead entities respawn after a timer.
7. The player is only eliminated when all three are dead simultaneously
8. If one entity levels up or gains a buff, only that entity benefits (no sharing)
9. Visual: three distinct characters with individual health bars and selection indicators

## Engine Primitives Required

### One Session, Multiple Entities

The fundamental assumption across the entire engine is: **one Edge Node session maps to one entity**. Multi-Entity Control breaks this.

The Edge Node (`ProxyActor`) currently has:
- `entity_id: EntityID` (singular)
- `authoritative_mesh_node: IPAddress` (one Arbiter)
- Input processing maps input → one entity's proposals

Multi-Entity Control requires:
```
struct MultiEntitySession {
    entities: Vec<EntitySessionBinding>,
    selected: Vec<usize>,  // Indices into entities, currently receiving input
}

struct EntitySessionBinding {
    entity_id: EntityID,
    arbiter_address: IPAddress,
    is_alive: bool,
}
```

The Edge Node must:
1. Maintain multiple entity bindings
2. Route input to selected entities only
3. Receive downstream payloads from multiple Arbiters (if entities are split)
4. Handle death/respawn per entity independently

### Split Across Arbiters

The three entities can be on three different Arbiters simultaneously. This means:
- The Edge Node sends proposals to up to 3 different Arbiters
- The Edge Node receives downstream state updates from up to 3 different Arbiters
- The client renders 3 different viewports (or switches camera between them)

This is a **persistent multi-Arbiter session** — not a temporary cross-boundary relay, but an ongoing data flow between one Edge Node and multiple Arbiters.

### Selection and Input Routing

The player selects which entities to command. The Edge Node must:
1. Track the current selection (1, 2, or 3 entities)
2. When one entity is selected: send movement/ability input to that entity's Arbiter
3. When all are selected: send movement input to all three Arbiters (group move)
4. Handle per-entity ability usage (entity A has ability X, entity B has ability Y)

The Arbiter doesn't need to know about the multi-entity session — it just receives proposals for the entities it hosts. The multi-entity routing is an Edge Node concern.

### Group Movement

When all three are selected and the player issues a move command:
- All three entities receive the same destination
- They move independently (different speeds, different paths)
- The Edge Node sends three separate movement proposals

Formation movement (triangle, line, etc.) is a client-side convenience — the Arbiter just sees individual movement commands.

### Death and Respawn Per Entity

Each entity has an independent death/respawn lifecycle:
- Entity A dies → respawn timer starts for A. B and C continue.
- All three dead simultaneously → player is eliminated (game-level death)
- Each entity's respawn is a mini-spawn-handshake with Meta

## Cross-Boundary Concerns

TODO: This is the most boundary-intensive pattern in the entire sketch set:

1. **Three entities on three Arbiters:** The Edge Node maintains connections to up to 3 Arbiters simultaneously. Proposals go to different destinations. Downstream payloads arrive from different sources.

2. **Dynamic Arbiter mapping:** As entities move, they may cross boundaries. Each entity's Arbiter mapping changes independently. The Edge Node must handle topology updates per entity.

3. **Spawn across map:** Entities can be sent to completely different parts of the map. They may have no spatial relationship to each other. The Edge Node's "area of interest" is the union of all three entities' surroundings.

4. **Death on one Arbiter, respawn on another:** Entity A dies on Arbiter X. Respawn might place it at a spawn point on Arbiter Y. The Edge Node's binding for entity A changes.

## Compiler Requirements

TODO: This isn't really a "compiled ability" — it's a **game mode / hero archetype** that the game adapter must support. The compiler needs to express:
- Hero definition with N entities (not just 1)
- Per-entity stat blocks and ability sets
- Session binding: one Edge session → N entities
- Selection/input routing rules
- Death condition: all N dead simultaneously
- Respawn: per-entity independent

The engine needs to support this at the adapter level — the game adapter must tell the engine "this player session controls 3 entities" during the spawn handshake.

## Open Questions

- How does the Edge Node handle receiving downstream payloads from 3 Arbiters simultaneously?
- Does each entity have its own token bucket for ingress fairness, or is there one per session?
- How does the camera/viewport work — can the player see all three simultaneously (minimap only)?
- Can other players heal/buff individual Vikings, or do they always target "the Vikings player"?
- Do all three entities share XP/level, or level independently?
- How does SK-65 Taunt interact — taunted Viking must attack the taunter, but the other two are free?
- Can SK-54 Entity Consumption swallow one Viking while the others continue?
- How does SK-04 Tether work — tether to one Viking?
- Does the spawn handshake (Meta → Controller → Arbiter) happen once for all three or three times?
- Performance: one player generating 3× the proposals, 3× the downstream payloads, 3× the entity updates
- Does this require changes to `docs-core/` (the session model assumes one entity per session)?
