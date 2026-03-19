# SK-60: Bunker

## Designer Intent

I deploy a bunker at a target position. Allies can right-click the bunker to enter it. While inside, they are untargetable and protected, but they can shoot out through firing ports. The bunker has HP and can be destroyed. When destroyed (or expired), all occupants are ejected.

## Primitive Composition

P-32 (Actor Spawning) → P-58 (Container/Vehicle Logic) → P-20 (Damage Redirection)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted)
- Allies interact with the bunker to enter/exit

## Observable Behavior

1. Bunker is placed at target position (has HP, is destructible, blocks pathing)
2. Allies within interact range can enter the bunker (up to 4 occupants)
3. While inside: occupants are untargetable and take no direct damage
4. While inside: occupants can use their auto-attacks through firing ports (reduced range)
5. While inside: occupants cannot move or use most abilities (only basic attacks)
6. Occupants can exit the bunker voluntarily at any time
7. Bunker has a duration (10 seconds) or HP pool — whichever runs out first
8. When bunker is destroyed or expires: all occupants are ejected at the bunker's position
9. Damage dealt to the bunker is split across its HP pool — occupants take no damage
10. Visual: military bunker structure, visible firing ports, explosion on destruction

## Engine Primitives Required

### Enterable Structure Entity

This is a completely new entity type — a **structure that contains other entities**:

```
struct BunkerActor {
    bunker_id: EntityID,
    position: Vec2F,
    hp: SimFixed,
    max_hp: SimFixed,
    expires_at_tick: u64,
    max_occupants: u8,
    occupants: Vec<EntityID>,  // Entities currently inside
    owner_team: TeamId,        // Only this team can enter
}
```

The bunker is:
- A targetable, destructible entity (enemies can attack it)
- A spatial obstacle (blocks pathing like SK-03 Terrain Wall)
- A container for multiple entities (like SK-54 Entity Consumption, but voluntary and multi-occupant)
- An enabler (occupants can still auto-attack out)

### Occupant State

Entities inside the bunker need a modified state:
- Position: locked to bunker position (no movement)
- Untargetable: excluded from targeting queries (like SK-44 Burrow)
- Can auto-attack: yes, but with modified range (firing port range, shorter than normal)
- Can use abilities: no (most abilities blocked, like SK-26 Silence)
- Can exit: voluntary action at any time

This is a unique capability combination — untargetable + can attack + can't move + can't cast. No existing sketch has this exact set.

### Enter/Exit Interaction

Entering the bunker is an **interact action** — the ally right-clicks the bunker and their entity enters. This is similar to SK-45 Essence Collection (proximity interaction) but with a different outcome (entity enters the structure rather than collecting a pickup).

The Arbiter must:
1. Validate the interact: is the ally in range? Is the bunker full? Is the ally on the correct team?
2. Remove the ally from the spatial world (like SK-54 consumption, but voluntary)
3. Add the ally to the bunker's occupant list
4. Enable firing-port auto-attack for the occupant

Exit is the reverse — the ally's entity re-enters the spatial world at the bunker's position.

### Firing Port Attacks

Occupants can auto-attack from inside the bunker. The attack originates from the bunker's position (not the occupant's original position). The occupant's offensive stats are used. The target must be within firing port range. The attack goes through normal Phase 1 → Phase 2 resolution.

Can occupants' auto-attacks trigger on-hit procs (SK-09 Chain Lightning)? Probably yes — the occupant is performing an auto-attack.

## Cross-Boundary Concerns

TODO: The bunker is a stationary entity on one Arbiter. Cross-boundary concerns:

1. **Allies from neighboring Arbiter entering:** An ally Ghost interacts with the bunker. The ally's Arbiter must hand off the entity to the bunker's Arbiter (the ally enters the bunker = their entity moves to the bunker's Arbiter). This is an entity handoff triggered by interaction, not by movement.

2. **Firing port attacks on Ghost targets:** Occupants auto-attack enemies that might be Ghosts. Standard damage relay.

3. **Bunker near boundary:** The bunker blocks pathing — neighbors need to know about it for their entities' collision. Does the bunker appear in the neighbor's static_grid? Or as a Ghost-like obstacle?

4. **Bunker destroyed, occupants ejected:** All occupants materialize at the bunker's position. If the bunker was near a boundary, some ejected entities might need handoff to a neighbor.

## Compiler Requirements

TODO: Designer specifies: bunker HP, duration, max occupants (4), team-restricted entry, occupant state (untargetable, can auto-attack with reduced range, can't move/cast), enter/exit interaction, destruction ejects all, blocks pathing. Compiler produces:
- BunkerActor entity definition with HP, occupant list, pathing obstruction
- Occupant state modification (untargetable + attack-only + immobile)
- Enter/exit interaction definitions
- Firing port attack range override
- On-destroy/on-expire: eject all occupants
- Linked lifecycle between bunker and occupant states

## Open Questions

- Can the caster enter their own bunker?
- Can enemies enter the bunker (contested bunker)?
- Can occupants use healing abilities on each other while inside?
- Do occupants share the bunker's damage (bunker takes 100 damage, each occupant takes 25)?
- Can the bunker be healed/repaired by allies?
- Does SK-31 Vortex pull entities out of the bunker?
- Can SK-01 Toss throw an enemy INTO the bunker (forced entry)?
- Does the bunker block projectiles (SK-02 Poison Shot can't pass through)?
- Can SK-54 Entity Consumption swallow the entire bunker (with occupants inside)?
- How does the bunker interact with Arbiter split/merge — it's a stationary multi-entity container?
