# SK-56: Knockback Projectile

## Designer Intent

I punch an enemy so hard they fly backward in a straight line. Any enemies that the flying body passes through take damage and are briefly knocked aside. The punched enemy takes damage on impact with a wall (or at max knockback distance).

## Primitive Composition

P-32 (Actor Spawning) → P-02 (Forced Displacement)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in melee range)

## Observable Behavior

1. Punch the target — they are launched backward (away from the caster) at high speed
2. The launched enemy travels in a straight line
3. Any enemies the launched body passes through take X damage and are briefly knocked aside (mini-stun, 0.25s)
4. If the launched enemy hits a wall: they take Y bonus impact damage and stop
5. If no wall is hit: they travel max distance and stop
6. The launched enemy takes base damage from the punch + optional wall impact damage
7. The launched enemy is CC'd during flight (cannot act)
8. Visual: haymaker punch, enemy ragdolls through the air, bowling-pin effect on pass-through targets

## Engine Primitives Required

### Entity As Projectile

The punched enemy's entity becomes a projectile temporarily:
- Their position is updated by a knockback velocity vector (not their own movement input)
- They have a collision hitbox that checks against OTHER entities along the path
- Entities they collide with take damage and are briefly displaced

This is similar to SK-34 Charge (entity moving at high speed with collision), but it's the TARGET moving (not the caster), and pass-through targets take damage (unlike Charge which only captures the first).

The displaced entity temporarily has projectile-like properties:
```
status_effect: KnockbackFlight {
    velocity: Vec2F,            // Knockback direction + speed
    remaining_ticks: u64,
    pass_through_damage: SimFixed,
    pass_through_stun_ticks: u64,
    wall_impact_damage: SimFixed,
    entities_already_hit: HashSet<EntityID>,  // No double-hits
}
```

Each tick during flight:
1. Move the entity by `velocity`
2. Check for collision with static geometry (wall impact)
3. Check for collision with other entities (pass-through damage)
4. For each new entity hit: apply pass-through damage + mini-stun
5. On wall hit or max distance: stop, apply wall damage if applicable

### Pass-Through Collision

Unlike normal entity collision (soft collision, pushes apart), the flying entity PASSES THROUGH enemies while dealing damage. This requires a different collision response:
- Normal: entities collide → push apart
- Knockback flight: entity collides → damage + mini-stun to the other entity, flying entity continues

The collision detection is the same (check entity overlap), but the response is different. The engine needs to know "this entity is in knockback flight mode" to switch collision response.

### Knockback Source Resolution

The pass-through damage is dealt by... whom? The flying entity? The caster who punched them? For kill credit and on-hit procs:
- **Caster owns the damage** — the caster punched, the flying body is a weapon wielded by the caster
- This means the pass-through damage uses the CASTER's offensive stats, not the flying entity's
- On-hit procs (SK-09 Chain Lightning) from the caster can trigger on pass-through hits

## Cross-Boundary Concerns

TODO: The flying entity crosses space at high speed, potentially crossing Arbiter boundaries. During flight:
1. The entity's position updates per tick via the knockback velocity
2. If the entity crosses a boundary, standard handoff occurs — but mid-knockback
3. The KnockbackFlight effect (with its remaining velocity, hit list, damage values) must transfer with the handoff
4. Pass-through targets on the new Arbiter take damage from the flying entity — but the CombatContext carries the original caster's offensive stats (who may be on a different Arbiter)

The flying entity is essentially a projectile with a full entity state. It's the most complex handoff scenario: an entity with movement override + collision response override + damage payload from a remote caster.

## Compiler Requirements

TODO: Designer specifies: melee range target, knockback direction (away from caster), knockback speed, max distance, pass-through damage + mini-stun, wall impact damage, flying entity CC'd during flight, caster's stats for pass-through damage. Compiler produces:
- KnockbackFlight status effect with velocity, collision behavior, damage payloads
- Pass-through collision mode (damage + continue, not push-apart + stop)
- Entity-as-projectile property override during flight
- CombatContext pre-rolled with caster's offensive stats for pass-through hits
- Hit-list dedup (no double-hits on pass-through)

## Open Questions

- Can the flying entity be healed by allies mid-flight?
- Can the flying entity be intercepted (SK-03 Terrain Wall placed in their path)?
- Does the flying entity trigger SK-32 Minefield if they pass over mines?
- Can the flying entity collide with another flying entity (two knockbacks collide)?
- Does pass-through damage trigger on-hit procs for the CASTER (not the flying entity)?
- Does pass-through damage trigger SK-22 Reflection / SK-23 Thorns on the pass-through targets (damage source is ambiguous)?
- If the flying entity has SK-22 Damage Reflection active, does the wall impact damage reflect back to... the caster?
- Can SK-51 Unstoppable prevent the knockback entirely (immune to displacement)?
- Does the flying body block projectiles from other abilities, or do projectiles pass through the flying entity?
- How does the flying entity's Ghost update look to neighbors — high-speed discontinuous movement?
