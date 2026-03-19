# SK-90: Orbital Sweep

## Designer Intent

I latch onto an enemy with a grappling hook and swing around them in a circle. While swinging, I deal damage to any enemies my body passes through. After 2 revolutions, I can detach — slamming into the ground at a chosen angle, dealing AoE damage and stunning nearby enemies.

## Primitive Composition

P-06 (Attached Kinematics) → P-07 (Entity-as-Kinematic-Volume) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range — the orbit anchor)
- Detach direction (chosen by the player during the orbit)

## Observable Behavior

1. Cast on enemy — caster attaches and begins orbiting around the target
2. The caster physically moves in a circle around the target at a fixed radius (e.g., 3 meters)
3. Orbit speed is constant (e.g., 1 revolution per second)
4. Enemies in the orbital path take damage as the caster passes through them
5. The orbit anchor (target enemy) can still move — the orbit center moves with them
6. After ~2 revolutions: the player can press the detach key
7. On detach: caster slams to the ground at the current orbital position, AoE damage + stun around the landing point
8. If the player doesn't detach: orbit continues for up to 4 revolutions then auto-detaches
9. If the orbit anchor dies: caster auto-detaches at current position
10. Visual: grappling hook swing, trail of energy, slam effect on detach

## Engine Primitives Required

### Circular Orbital Movement

This is a completely new movement type. The caster's position is calculated each tick as a function of the orbit:

```
struct OrbitalState {
    anchor_entity_id: EntityID,
    orbit_radius: SimFixed,
    angular_velocity: SimFixed,  // Radians per tick
    current_angle: SimFixed,     // Current position on the circle
    max_revolutions: SimFixed,
    revolutions_completed: SimFixed,
    pass_through_damage: SimFixed,
    detach_aoe_damage: SimFixed,
    detach_stun_ticks: u64,
}
```

Each tick:
1. Read the anchor entity's current position (the orbit center)
2. `current_angle += angular_velocity`
3. `caster.position = anchor.position + Vec2F::from_angle(current_angle) * orbit_radius`
4. `revolutions_completed += angular_velocity / (2 * PI)`
5. Check for entity collisions along the arc swept this tick (damage pass-through entities)

The caster's position is DERIVED from the anchor's position + angle. The caster doesn't use normal movement — their position is overridden by the orbit formula.

### Pass-Through Damage During Orbit

As the caster sweeps through a circular arc each tick, enemies in the arc take damage. This requires:
- Calculate the arc swept this tick (from old_angle to new_angle at orbit_radius around anchor)
- Check for entity intersections with this arc
- Apply pass-through damage to intersected entities (like SK-56 Knockback Projectile's pass-through)
- Dedup: don't hit the same entity twice per revolution (hit list per revolution)

### Orbit Anchored to Moving Entity

The orbit center is the anchor ENTITY, not a fixed position. If the anchor moves (walks, dashes, is displaced), the orbit moves with them. Each tick, the orbit center updates to the anchor's current position.

This means: if the anchor is dragged by SK-43, the orbiting caster follows. If the anchor blinks (SK-35), the caster snaps to the new orbit position. The caster's movement is entirely derived.

### Detach With Directional Slam

On detach:
1. The caster's position becomes their actual position (no longer orbit-derived)
2. AoE damage + stun at the caster's landing position
3. The player chooses the detach timing (and thus the angular position = where they land)

The detach direction is implicitly chosen by WHEN the player presses the button — different timing = different position on the circle = different landing spot.

## Cross-Boundary Concerns

TODO: The caster's position is derived from the anchor's position. If the anchor is near or across an Arbiter boundary:

1. **Both on same Arbiter:** Simple. Orbit calculated locally.
2. **Anchor is a Ghost:** The caster orbits around a Ghost's position. Ghost position is approximate (dead-reckoned). The orbit might be slightly off from the actual anchor position.
3. **Caster's orbit crosses a boundary:** The orbit radius (3m) might extend across a boundary. Each tick, the caster's calculated position might alternate between "in this Arbiter's region" and "in the neighbor's region." This would cause constant handoff oscillation — very bad.

The simplest solution: while orbiting, the caster stays on the anchor's Arbiter. If the anchor crosses a boundary, the caster is handed off WITH the anchor (atomic two-entity movement, similar to SK-34 Charge with a pinned entity but different topology).

## Compiler Requirements

TODO: Designer specifies: target (enemy), orbit radius (3m), orbit speed (1 rev/s), max revolutions (4), pass-through damage, detach action (AoE + stun), detach timing (player-controlled), anchor death → auto-detach. Compiler produces:
- OrbitalState status effect with per-tick position derivation
- Orbit formula: position = anchor.position + Vec2F::from_angle(angle) * radius
- Arc-sweep collision detection for pass-through damage
- Detach action: AoE + stun at current orbital position
- Anchor death hook: auto-detach

The compiler needs to support **derived position** — an entity whose position is a function of another entity's position rather than its own movement input. This is a new movement category.

## Open Questions

- Can the orbiting caster be CC'd during the orbit (stunned mid-orbit = fall off)?
- Can the orbiting caster be targeted by enemies during the orbit?
- Does the orbit inherit the anchor's Kinematic Dilation (slower orbit in dilated zones)?
- Can the anchor use SK-35 Blink Strike — does the orbiting caster teleport with them?
- If the anchor enters SK-44 Burrow (untargetable), does the orbit continue around the burrowed entity?
- Can the orbiting caster use abilities during the orbit, or only the detach action?
- Does the pass-through damage trigger on-hit procs (SK-09 Chain Lightning)?
- Can two casters orbit the same anchor simultaneously?
- How does the orbit interact with collision (does the caster pass through walls during orbit)?
- If the caster has SK-08 Aura, does the aura sweep enemies during the orbit?
