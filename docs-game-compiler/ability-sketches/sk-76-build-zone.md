# SK-76: Build Zone

## Designer Intent

I place pylons that generate a power field around them. My turret structures can ONLY be placed within a pylon's power field. If a pylon is destroyed, any turrets in its field that are no longer covered by another pylon also shut down. The pylon network defines where I can build.

## Primitive Composition

P-08 (Dynamic Collision Injection) → P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Pylon placement: caster entity + target position (ground-targeted)
- Turret placement: caster entity + target position (must be within a pylon's power field)

## Observable Behavior

1. Place Pylon — creates a power field (visible circle on the ground)
2. Pylon has HP, can be destroyed by enemies
3. Place Turret — can ONLY be placed within a pylon's power field radius
4. If turret placement target is outside all power fields: placement fails (error message)
5. Turret auto-attacks nearby enemies while in a powered field
6. If the pylon powering a turret is destroyed AND no other pylon's field covers the turret: turret deactivates (stops attacking, loses shield, but doesn't die immediately — can be re-powered by placing a new pylon)
7. Multiple pylons' fields can overlap — turrets in overlap zones are safe if any one pylon survives
8. Visual: blue power field circles, turrets glow when powered, dim when depowered

## Engine Primitives Required

### Spatial Placement Prerequisite

This is the first ability with a **placement restriction based on another placed entity's zone**. The turret placement validation must check:

```
fn validate_turret_placement(position: Vec2F, pylons: &[PylonActor]) -> bool {
    for pylon in pylons {
        if pylon.is_alive && distance(position, pylon.position) <= pylon.power_radius {
            return true;  // Within at least one pylon's field
        }
    }
    false  // Not in any power field — placement denied
}
```

This validation runs during `validate_intent` for turret placement. The Arbiter needs to query all living pylons owned by the caster and check if the target position falls within any of their radii.

### Dependency Tracking (Pylon → Turret)

When a pylon dies, the engine must determine which turrets are affected:
1. Find all turrets within the dead pylon's power radius
2. For each affected turret: check if ANY other living pylon still covers it
3. If no pylon covers it: deactivate the turret (change state to `Depowered`)
4. If another pylon covers it: turret is unaffected

This is a **dependency graph** between placed entities. Pylons are providers, turrets are consumers. The graph changes when:
- A pylon is placed (new provider — reactivate turrets in its field)
- A pylon is destroyed (lost provider — check if turrets lose coverage)
- A turret is placed (new consumer — link to covering pylon)
- A turret is destroyed (removed consumer)

### Turret Activation State

Turrets have a binary state: `Powered` or `Depowered`:
- **Powered:** auto-attacks enemies, has shields (if applicable), fully functional
- **Depowered:** stops attacking, loses shields, sits idle, can be re-powered

Re-powering: if a new pylon is placed whose field covers a depowered turret, the turret reactivates. The engine must check turret coverage whenever a pylon is placed.

### Autonomous Turret Entity

The turret itself is an Arbiter-local NPC with simple AI:
- Stationary (never moves)
- Acquires nearest enemy in range
- Auto-attacks at a fixed interval
- Has HP, can be destroyed
- Deactivates when depowered

Similar to SK-06 Summon Swarm minions but stationary and with the pylon dependency.

## Cross-Boundary Concerns

TODO: Pylons and turrets are stationary structures. Cross-boundary concerns:

1. **Pylon near boundary:** The power field extends in a radius. Turrets on the other side of a boundary could be "within" the power field geometrically, but they're on a different Arbiter. Does the power field cross boundaries? If not, turrets must be on the same Arbiter as their powering pylon.

2. **Pylon on Arbiter A, turret on Arbiter B:** If allowed, pylon death on A must notify B to deactivate the turret. Cross-boundary dependency.

3. **Topology change:** If a split divides a pylon and its turrets onto different Arbiters, the dependency graph becomes cross-boundary.

Simpler approach: require turrets and their powering pylon to be on the same Arbiter. The power field radius is small enough (similar to `max_spell_range`) that this is reasonable.

## Compiler Requirements

TODO: Designer specifies:
- Pylon: placed structure, HP, power field radius, team-restricted
- Turret: placed structure, HP, auto-attack stats, REQUIRES pylon coverage for placement and operation
- Pylon death → coverage check → deactivate uncovered turrets
- New pylon → coverage check → reactivate depowered turrets in range

Compiler produces:
- PylonActor entity definition (HP, power_radius, team)
- TurretActor entity definition (HP, attack stats, powered/depowered state, auto-attack AI)
- Placement validation: turret requires pylon coverage
- Pylon death hook: coverage recalculation for affected turrets
- Pylon creation hook: coverage recalculation for depowered turrets
- Dependency graph maintenance

The compiler needs to support **inter-entity spatial dependencies** — placed entities whose operational state depends on proximity to other placed entities.

## Open Questions

- Is there a maximum number of pylons and turrets per caster?
- Can enemies see the power field boundaries (revealing where turrets can be placed)?
- Can turrets be placed outside of combat (pre-positioning for defense)?
- Do depowered turrets have reduced HP or become destructible more easily?
- Can a depowered turret be manually destroyed by the owning caster (to reclaim a build slot)?
- Does the turret inherit any of the caster's stats (damage scales with caster's offensive stats)?
- Can the pylon itself be attacked while powered turrets are near it (turrets defend their pylon)?
- How do pylons/turrets interact with SK-03 Terrain Wall (can you wall off a pylon fortress)?
- Do pylons and turrets count toward entity_count for Arbiter split triggers?
- Can the caster have pylons on multiple Arbiters (global building strategy)?
