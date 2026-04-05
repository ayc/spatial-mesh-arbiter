# SK-77: Two Players, One Entity (Cho'Gall)

## Designer Intent

Two players share one body. Player A controls movement and has tank or melee abilities. Player B
controls ranged or damage abilities but has no movement control. They share one HP pool, one
position, and one entity, but each has their own role-scoped ability access and input stream.

## Primitive Composition

P-30 (Input Multiplexing) → P-31 (Identity/Loadout Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Two player sessions
- One shared entity
- Role A: movement input plus role-A abilities
- Role B: role-B abilities only

## Observable Behavior

1. One entity exists on the map with one shared HP pool and one world position
2. Role A controls movement
3. Role A can use the tank or melee ability subset
4. Role B can use the ranged or damage ability subset
5. Both players can submit legal proposals in the same tick
6. Both players observe the same world position and die or respawn together with the shared entity
7. Buffs, debuffs, crowd control, and incoming damage all land on the same shared body
8. Movement from the non-movement role is rejected

## Engine Primitives Required

Two-Players-One-Entity is now a canonical `many_to_one` control-topology pattern.

### Shared Entity, Multiple Sessions

The game authors one `ControlTopologyDef` with:

1. `mode = many_to_one`
2. `input_policy = role_split`
3. `elimination_policy = shared_entity_removed`
4. one control member for each player-facing role

Each `ControlMemberDef` uses `control_scope` plus optional `loadout_profile_id` to define what that
role is allowed to do:

- Role A can be `full` with a loadout profile exposing movement and the tank subset
- Role B can be `abilities_only` with a loadout profile exposing only the damage subset

The entity itself is still one ordinary entity. The topology only determines which session may send
which kinds of proposals and which authored abilities are legal for each role.

### Shared Body, Role-Scoped Ability Access

The shared entity owns:

- one HP pool
- one position
- one authoritative Arbiter owner
- one status registry
- one CC state
- one incoming-damage and death lifecycle

The roles own:

- distinct input streams
- distinct allowed control scopes
- distinct allowed ability subsets through loadout profiles

This is not two hidden entities fused together. It is one entity with many-to-one routing metadata.

### Role-Based Proposal Admission

Stage 1 tags proposals with their contributing session role before Stage 2 validation.

That yields the intended behavior:

1. movement proposals from Role A are legal
2. movement proposals from Role B are rejected
3. Role-A abilities are checked against Role A's allowed loadout subset
4. Role-B abilities are checked against Role B's allowed loadout subset
5. both proposal streams still resolve through the same shared entity state

If both players submit legal proposals in the same tick, they are processed as ordinary routed
proposals against the same entity. If two proposals conflict, the shared entity's normal cast,
channel, movement, and capability rules decide which one commits or breaks.

## Cross-Boundary Concerns

This sketch uses the ordinary `many_to_one` routing contract.

1. Both player sessions route to the current authoritative owner of the shared entity.
2. If the entity crosses a boundary, both sessions are redirected to the new owner together.
3. The shared entity still has one authoritative Arbiter at a time; many-to-one does not create
   dual authority.
4. Reconnect re-installs the same static `control_topology` from the entity definition, so the role
   binding survives handoff and reconnect boundaries.

If one player disconnects, the entity does not die automatically. The remaining player keeps only
their own role. There is no automatic role reassignment in this sketch.

## Compiler Requirements

Designer specifies:

- that the entity uses `many_to_one` control topology
- the per-role control scopes
- the per-role loadout profiles
- the shared-entity elimination rule

Compiler emits:

- one static `control_topology` definition with `mode = many_to_one`
- one `members` list defining the participating roles
- any referenced `loadout_profiles` needed to restrict ability access per role
- Stage 1 routing metadata that attributes proposals to the correct role

Compiler validates:

1. `many_to_one` defines at least 2 members
2. at most one member is marked primary
3. at least one role provides movement or full control
4. every referenced `loadout_profile_id` exists on the same entity definition
5. the topology uses canonical `control_scope` restrictions rather than sketch-local role flags

## Resolved Notes

- The shared body counts as one entity for Arbiter load, split decisions, targeting, and KiDi.
- The per-entity token bucket is shared because proposals still target one entity.
- Crowd control, damage, buffs, and debuffs apply to the shared entity and therefore affect both
  players' experience together.
- Simultaneous casting is allowed when both routed proposals are legal under the shared body's
  current state; otherwise ordinary validation or channel-break rules reject the conflicting action.
- If Role A disconnects, movement stops unless another explicit game rule reassigns that role. If
  Role B disconnects, the body still moves and Role A keeps their own role-scoped abilities.
- This sketch no longer requires new `docs-core` session-model work. `many_to_one`,
  `control_scope`, and role-scoped `loadout_profile_id` are already the canonical surface.
