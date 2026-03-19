# SK-105: Pocket Arena

## Designer Intent

I drag a target enemy into a shadow realm — a private 1v1 arena where only the two of us exist. For 7 seconds, no other players can see us, help us, or interfere. We fight it out alone. After 7 seconds (or if one of us dies), we return to the main world at our original positions.

## Primitive Composition

P-56 (Spatial Instance Forking) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy — both entities are pulled into the pocket arena
2. In the main world: both entities DISAPPEAR (untargetable, invisible, no position)
3. In the pocket arena: both entities exist in a small enclosed area, can fight normally
4. Other players cannot see, target, heal, buff, or interact with either entity
5. All abilities work normally between the two entities inside the arena
6. After 7 seconds: both entities return to the main world at their original positions
7. If one entity dies in the arena: the survivor returns immediately with their current HP
8. Status effects persist from the main world into the arena and back
9. Visual: dark swirling portal effect on entry, shadow realm environment, return flash

## Engine Primitives Required

### Separate Spatial Context

This is the most architecturally significant ability in the entire sketch set. The engine must support a **temporary private spatial instance** containing exactly two entities:

```
struct PocketArena {
    arena_id: UUID,
    entity_a: EntityID,       // Caster
    entity_b: EntityID,       // Target
    original_position_a: Vec2F,
    original_position_b: Vec2F,
    original_arbiter_a: u32,
    original_arbiter_b: u32,
    arena_bounds: Rect,       // Small enclosed area
    expires_at_tick: u64,
}
```

The pocket arena is a SEPARATE SIMULATION CONTEXT:
- Its own spatial bounds (small rectangle)
- Only two entities exist in it
- No Ghosts from the main world
- No zone effects from the main world
- Standard combat resolution between the two entities
- Its own collision geometry (arena walls)

### Entity Extraction From Main World

On activation:
1. Remove entity A from the main world's Arbiter entity map
2. Remove entity B from the main world's Arbiter entity map (may be a different Arbiter)
3. Create the pocket arena (where does it run? see below)
4. Place both entities inside the arena at starting positions
5. Begin independent simulation

On the main world side:
- Both entities cease to exist (no Ghost updates, no downstream payloads)
- All effects targeting either entity from external sources are severed
- SK-04 Tether breaks (partner gone), SK-19 Guardian Angel breaks, etc.

### Where Does The Arena Run?

Option A: **Dedicated mini-Arbiter** — spawn a temporary Arbiter process for the 1v1. Clean isolation but expensive (new process for 7 seconds).

Option B: **Quarantined section on an existing Arbiter** — one of the two entities' Arbiters hosts the arena as an isolated sub-context. The arena entities don't interact with the Arbiter's other entities. Simpler but requires the Arbiter to support isolated entity groups.

Option C: **Same Arbiter, invisible entities** — both entities stay in the main Arbiter's entity map but are flagged as "in pocket arena" and excluded from all normal queries. They can only interact with each other. Simplest implementation but leaks arena state into the main world's Arbiter.

Option B is likely the best balance: the caster's Arbiter hosts the arena. The target entity is transferred from their Arbiter to the caster's Arbiter for the duration.

### Return To Main World

On arena expiry or death:
1. Read both entities' current state (HP, buffs, debuffs, cooldowns)
2. Remove entities from the arena
3. Re-insert entity A at `original_position_a` on `original_arbiter_a`
4. Re-insert entity B at `original_position_b` on `original_arbiter_b`
5. Resume Ghost updates, downstream payloads, normal simulation

If one entity died in the arena:
- Dead entity enters normal death flow (Meta respawn)
- Survivor returns to main world at their original position with current HP

### Edge Node Handling

Both entities' Edge Nodes must:
- Stop receiving main-world state updates (they're not in the main world)
- Start receiving arena state updates (small arena, two entities)
- On return: resume main-world state updates from their original Arbiter

## Cross-Boundary Concerns

TODO: This ability is INHERENTLY cross-boundary if the two entities are on different Arbiters:

1. **Both on same Arbiter:** Simple — create arena on that Arbiter, quarantine both entities.
2. **Different Arbiters:** Entity B must be transferred from Arbiter B to the caster's Arbiter A for the arena. This is an entity handoff triggered by the ability, not by movement. On return, entity B is transferred back.
3. **Topology changes during arena:** The main world might split/merge while the arena is active. The original positions' owning Arbiters might change. On return, the engine must re-query which Arbiter owns each original position.

## Compiler Requirements

TODO: Designer specifies: target (enemy), both entities removed from main world, private 1v1 arena, duration (7s), return to original positions on expiry or death, status effects persist, full combat inside arena. Compiler produces:
- PocketArena definition (bounds, entity pair, timer)
- Entity extraction from main world (remove + serialize)
- Arena creation (quarantined spatial context)
- Independent simulation within arena
- Return action: re-insert entities at original positions
- Death handling: dead entity enters normal flow, survivor returns

### docs-core/ Impact

This almost certainly requires `docs-core/` changes:
- The spatial runtime kernel must support isolated spatial contexts (sub-arenas)
- Entity handoff must support "transfer for arena purposes" (not just boundary crossing)
- The authority model must account for entities temporarily outside the main mesh

## Open Questions

- Can abilities inside the arena affect the main world (SK-05 Global Strike from inside the arena)?
- Do cooldowns that started in the main world continue ticking in the arena?
- If entity B's Arbiter crashes while B is in the arena, what happens?
- Can the arena be entered by other abilities (SK-69 Portal Pair — portal to entity in arena)?
- Does Kinematic Dilation from the main world affect the arena?
- If the caster dies in the arena, does the target return to their original position with full HP?
- Can the arena be cleansed/dispelled by an ally in the main world (they can't target either entity — so no)?
- Does the 7-second timer pause during SK-91 Stasis inside the arena?
- What happens to SK-06 summoned minions when the owner enters the arena? Do they enter too?
- How does the arena interact with the scoring/objective system (is it a timeout if neither dies)?
- Performance: creating and destroying a spatial context for 7 seconds — what's the overhead?
