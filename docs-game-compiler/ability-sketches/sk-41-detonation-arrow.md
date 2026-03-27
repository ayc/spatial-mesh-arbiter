# SK-41: Detonation Arrow

## Designer Intent

I fire a projectile in a line. The projectile keeps flying until I reactivate the ability (or it reaches max range). On detonation, it explodes dealing AoE damage and silencing all enemies in the blast radius. I control WHERE it detonates by choosing WHEN to press the button.

## Primitive Composition

P-32 (Actor Spawning) → P-45 (Delay Timer) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (from requested aim direction)
- Detonation input (reactivation of same ability key, while projectile is in flight)

## Observable Behavior

1. Cast — projectile launches in the specified direction
2. Projectile travels at constant speed in a straight line
3. Projectile passes through all entities (does not detonate on contact)
4. While in flight: ability icon changes to "Detonate"
5. If reactivated: projectile explodes at its current position — AoE damage + 2.5s silence to all enemies in blast radius
6. If not reactivated: projectile detonates automatically at max range
7. Caster can move and act normally while the projectile is in flight
8. Visual: glowing arrow with a trail, expanding explosion on detonation

## Engine Primitives Required

### Player-Controlled Detonation
Normal projectiles have two detonation triggers: entity collision (hit something) and fuse expiry (max lifetime/range). This projectile adds a third: **player command**.

The ProjectileActor needs a detonation policy:
```
ProjectileDetonationPolicy {
    manual_trigger_enabled: true,
    proximity_trigger_radius: None,
    entity_impact_behavior: Ignore,
    world_impact_behavior: Ignore,
    expiry_behavior: Detonate,
}
```

For this policy, the projectile flies until either:
- The caster sends a `DetonateOwnedProjectile { projectile_id }` command (reactivation)
- The projectile reaches its lifetime expiry and detonates as a safety cap

### Caster-Projectile Link
The caster must be able to send a command to a specific live projectile. This is similar to SK-39 Spectral Dash (reactivating a live projectile), but instead of teleporting TO the projectile, the caster tells it to EXPLODE.

```
status_effect: DetonationArrowLink {
    projectile_id: EntityID,
    can_detonate: bool,
}
```

On reactivation:
1. Look up projectile by ID
2. Trigger detonation at projectile's current position
3. Resolve AoE damage + silence against all entities in blast radius
4. Despawn projectile

### Pass-Through Projectile
The projectile ignores entity collisions during flight — it only responds to the player's detonation command or lifetime expiry. This is a flag on the projectile: `collides_with_entities: false`.

## Cross-Boundary Concerns

TODO: Same pattern as SK-39 — the projectile might cross a boundary before the caster detonates it. The detonation command must reach the projectile's current Arbiter:

1. Projectile launched on Arbiter A, still on Arbiter A: detonation is local.
2. Projectile handed off to Arbiter B: caster's detonation command goes from Arbiter A (caster) to Arbiter B (projectile). The AoE resolves on Arbiter B.
3. The explosion hits entities on Arbiter B, but some might be Ghosts from Arbiter C — damage relays fan out.

The caster's Arbiter needs to know which Arbiter currently hosts the projectile to route the detonation command. Or: the detonation command is broadcast to all Arbiters that might have the projectile (based on its trajectory).

## Compiler Requirements

TODO: Designer specifies: projectile speed, max range, pass-through (no entity collision), detonation policy (player command or lifetime expiry), AoE blast radius, AoE damage, silence duration (2.5s), targeting filter (enemies). Compiler produces:
- ProjectileActor with `ProjectileDetonationPolicy { manual_trigger_enabled: true, entity_impact_behavior: Ignore, expiry_behavior: Detonate, ... }` and `collides_with_entities: false`
- Status effect on caster linking to the projectile
- Multi-phase ability: Phase 1 (launch), Phase 2 (detonate)
- AoE resolution + silence application on detonation

## Open Questions

- Can the caster fire a second Detonation Arrow while the first is still in flight? (Two active projectiles?)
- Does the projectile pass through SK-03 Terrain Walls, or does it detonate on wall collision?
- Can the silence from the explosion interrupt channels (SK-05 Global Strike)?
- Does the AoE damage use the caster's stats at cast time (epoch-pinned) or at detonation time?
- If the caster dies while the projectile is in flight, does it detonate automatically, keep flying until fuse, or despawn?
- Can enemies see the projectile coming (giving them time to dodge before detonation)?
- If the projectile is mid-handoff between Arbiters when the detonation command arrives, what happens?
- Does the explosion damage trigger on-hit procs for the caster (SK-09 Chain Lightning, SK-10 Crit Explosion)?
- Can the caster detonate while CC'd (stunned/silenced)?
