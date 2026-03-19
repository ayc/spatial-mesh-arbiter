# SK-58: Cocoon

## Designer Intent

I encase an enemy in a cocoon for 8 seconds. While cocooned, they cannot act, cannot take damage, and cannot be targeted — but the cocoon itself is a visible, attackable object. The enemy's allies can break the cocoon by destroying it (it has HP). If destroyed, the enemy is freed early. If the timer expires, the enemy is freed at full cocoon duration.

## Primitive Composition

P-53 (Entity Suspension) → P-33 (Entity Dormancy)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy — cocoon wraps around them instantly
2. Cocooned entity: cannot move, attack, cast, or be targeted by abilities
3. Cocooned entity: takes no damage from any source (invulnerable while cocooned)
4. A Cocoon object appears at the entity's position — it has its own HP pool (e.g., 600 HP)
5. The enemy's allies can attack the Cocoon object to destroy it and free their teammate
6. If Cocoon HP reaches 0: cocoon breaks, enemy is freed immediately
7. If 8 seconds pass: cocoon dissolves, enemy is freed
8. On release: enemy is briefly slowed (0.5s, 30%) as they shake off the cocoon
9. DoT timers on the cocooned entity: paused (they don't lose buff/debuff duration while cocooned)
10. Visual: amber cocoon shell, cracks as it takes damage, shatters on break

## Engine Primitives Required

### Stasis + Destructible Container

This combines two concepts:
- **Stasis** on the target entity: invulnerable + untargetable + cannot act (similar to SK-44 Burrow, but applied to an enemy, not self)
- **Container entity**: a separate destructible object at the same position that the stasis is tied to

```
struct CocoonActor {
    cocoon_id: EntityID,
    contained_entity_id: EntityID,
    hp: SimFixed,
    max_hp: SimFixed,
    expires_at_tick: u64,
}
```

The cocoon is its own entity in the entity map — it has a position, HP, and can be targeted and damaged. When the cocoon's HP reaches 0 or the timer expires, it despawns and removes the stasis from the contained entity.

### Linked Lifecycle

The stasis effect on the target and the cocoon entity have a **linked lifecycle**:
- Cocoon destroyed → remove stasis from target
- Timer expires → remove stasis + despawn cocoon
- If the contained entity somehow dies while cocooned (edge case) → despawn cocoon

This link must be bidirectional — either entity's lifecycle event affects the other.

### Targeting Rules

The cocooned entity is untargetable. The cocoon object IS targetable — but only by the cocooned entity's ALLIES. The caster's team cannot attack the cocoon (they want it to stay). This is the first entity with team-restricted INCOMING damage:
- Allies of the cocooned entity: can attack the cocoon
- Team of the caster: cannot attack the cocoon
- The cocooned entity's team is the cocoon's "enemy" for targeting purposes

## Cross-Boundary Concerns

TODO: The cocoon entity spawns at the target's position. If the target is near a boundary, the cocoon is a static entity on the target's Arbiter. Allies from a neighboring Arbiter (Ghosts) can attack it — damage relays cross-boundary. Standard damage relay pattern.

If the cocooned entity was on a different Arbiter than the caster (caster cocooned a Ghost), the stasis is applied on the target's Arbiter and the cocoon entity spawns there. The caster's Arbiter doesn't need to manage the cocoon.

## Compiler Requirements

TODO: Designer specifies: target (enemy), stasis (invulnerable + untargetable + cannot act), cocoon HP, duration (8s), cocoon targetable by enemy's allies only, on-break (free + slow), on-expiry (free + slow), timer pause on contained entity's effects. Compiler produces:
- Stasis status effect on target entity
- CocoonActor entity definition (HP, position, lifetime)
- Linked lifecycle between stasis and cocoon
- Team-inverted targeting rules on cocoon
- On-destroy/on-expiry hooks to remove stasis

## Open Questions

- Can the caster attack their own cocoon to free the enemy early (misplay correction)?
- Does the cocoon block pathing (enemies walk around it) or is it passable?
- Can the cocoon be healed by the caster's team (to extend the stasis)?
- Does the cocooned entity's position remain fixed, or can they be displaced (SK-01 Toss the cocoon)?
- Can multiple enemies be cocooned simultaneously (multiple cocoon entities)?
- Does the cocoon interact with SK-38 Contagion — if the cocooned entity had contagion, does it still spread while cocooned?
- Can SK-15 Purify be cast on the cocooned entity (they're untargetable — Purify can't select them)?
- Does SK-51 Unstoppable prevent cocooning?
- If the cocoon straddles an Arbiter boundary, which Arbiter owns it?
