# SK-68: Multi-Entity Control

## Designer Intent

I permanently control three independent characters simultaneously, not as a temporary summon spell
but as my core gameplay identity. Each character has its own HP, position, abilities, and respawn
state. I can select one, multiple, or all of them to issue commands, and I can split them across
the map.

## Primitive Composition

P-30 (Input Multiplexing) → P-32 (Actor Spawning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- One player session
- Three controlled entities
- Selection input: select individual member, selected subset, or all members
- Movement and ability commands routed only to the currently selected members

## Observable Behavior

1. The player starts with three independently targetable entities
2. Each entity has its own HP pool, position, movement, abilities, buffs, and debuffs
3. Selecting one entity routes commands only to that member
4. Selecting multiple or all members routes the command to that selected subset
5. The entities can split across the map and operate independently
6. Each entity can die and respawn independently
7. The player is eliminated only when all controlled members are removed under the authored group
   elimination rule
8. Buffs, heals, crowd control, and damage target individual members rather than an abstract shared
   player body
9. Visual: separate health bars, separate selection indicators, ordinary per-entity world presence

## Engine Primitives Required

Multi-Entity Control is now a canonical static `control_topology` pattern, not a sketch-local
"break the one-session-to-one-entity rule" proposal.

### Persistent One-To-Many Control Topology

The game authors one `ControlTopologyDef` with:

1. `mode = one_to_many`
2. `input_policy = adapter_routed`
3. `selection_mode = multiple`
4. `elimination_policy = all_members_removed`
5. one primary controller member plus additional controlled members

Each `ControlMemberDef` declares the controlled archetype and the member's routing role. This is
static entity-definition metadata installed at spawn, reconnect, and handoff, not an ability-local
runtime patch.

### Spawn And Session Shape

The game-mode or adaptation layer materializes the three controlled entities as ordinary spawned or
placed entities, then installs the shared `one_to_many` topology. The engine does not create one
special three-body kernel actor. It creates three ordinary entities plus one bounded routing group.

That means:

1. each entity has its own `entity_id`
2. each entity keeps its own HP, cooldowns, buffs, and positions
3. each entity is targeted, healed, crowd-controlled, and killed independently
4. the topology only changes which proposals the player session may route to which members

### Selection And Routed Commands

This sketch uses `adapter_routed` rather than unconditional mirroring.

The player's current selection is session-owned routing state. When the player issues a command:

1. Stage 1 input routing resolves the currently selected members
2. the engine routes the proposal only to those members
3. each receiving entity then validates and resolves the proposal independently on its own owner

Selecting all members and issuing a move command therefore becomes "route the same move intent to
all selected members," not "invent formation movement in the kernel." Any formation offsets or
client-side convenience behavior are outside the core routing contract.

### Independent Death And Elimination

Each controlled member dies, respawns, and re-enters the topology as an ordinary entity. The
topology's `elimination_policy = all_members_removed` means the grouped player identity is only
considered out once all members are gone at the same time. Per-member respawn timing remains a
game-mode concern layered on top of the ordinary spawn and death contracts.

## Cross-Boundary Concerns

Multi-Entity Control uses the canonical `P-30` coordinator model.

1. The topology is re-installed from static `control_topology` metadata whenever a member spawns,
   reconnects, or hands off.
2. If selected members live on different Arbiters, the routing coordinator relays proposals to the
   current owners of those members; each owner still resolves its member locally.
3. When one member crosses a boundary, only that member's authority changes. The rest of the group
   continues normally.
4. The player's effective area of interest is the union of the controlled members' surroundings,
   but that is an observer/session concern rather than a new combat-authority exception.
5. Respawning one dead member simply re-materializes that member and re-attaches it to the same
   topology; it does not require rebuilding the whole group.

## Compiler Requirements

Designer specifies:

- the member roster for the controlled group
- each member's archetype
- the allowed selection model
- the grouped elimination policy
- any game-mode respawn or progression policy layered on top of the group

Compiler emits:

- one static `control_topology` definition with `mode = one_to_many`
- one authored `members` list describing the controlled roster
- Stage 1 routing metadata that survives spawn, reconnect, and handoff
- no bespoke multi-character kernel type beyond the existing multiplex group

Compiler validates:

1. `members` count is within `max_multiplex_group_size`
2. `one_to_many` defines exactly one primary member
3. member entries are unique
4. each referenced `entity_type_id` exists
5. the topology uses canonical `selection_mode` and `elimination_policy` values rather than
   sketch-local flags

## Resolved Notes

- Each controlled member keeps its own per-entity token bucket. Proposal fairness is still enforced
  per entity, not per grouped player session.
- Other players target, heal, buff, crowd-control, or consume individual members normally because
  they are ordinary separate entities.
- XP sharing, level progression, camera layout, and UI selection presentation are game-mode/client
  concerns outside this sketch's routing contract.
- Taunt, tether, containment, and similar mechanics apply to whichever controlled member they
  actually target; they do not automatically affect the whole group.
- The grouped spawn flow may be orchestrated together by the game-mode layer, but the runtime state
  remains "three entities plus one topology," not one composite actor.
- This sketch no longer requires new `docs-core` session-model work. `ControlTopologyDef` and the
  existing `P-30` coordinator model are already sufficient.
