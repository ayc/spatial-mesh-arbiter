# SK-45: Essence Collection

## Designer Intent

When enemy minions and monsters die near me, they drop essence orbs. I passively collect orbs that are within a small pickup radius. Collected essence is stored as a secondary resource (separate from mana). I can activate this trait to consume all stored essence, healing myself over 5 seconds proportional to the amount consumed.

## Primitive Composition

P-14 (Continuous Proximity Monitor) → P-47 (Spatial Corpse Registry)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Passive: no input (automatic collection within radius)
- Active: self-cast to consume stored essence

## Observable Behavior

1. An enemy minion/monster dies within collection range of my character
2. An essence orb spawns at the death position
3. If I walk within pickup radius of the orb, it's automatically collected
4. Collected essence is added to my essence counter (secondary resource, e.g., 0/50 max)
5. Each minion death drops a fixed amount (e.g., 2 essence), elite monsters drop more (10 essence)
6. Orbs persist on the ground for 8 seconds if not collected, then despawn
7. Activate trait: consume all stored essence, heal for (essence_consumed * heal_per_essence) over 5 seconds
8. Visual: green orbs on the ground, absorption effect on pickup, green healing glow on activation

## Engine Primitives Required

### Death-Spawned Pickup Entities
When an entity dies (HP reaches zero), the engine needs to:
1. Check if the dead entity qualifies for essence drop (minion/monster, not hero)
2. Spawn a pickup actor at the death position
3. The pickup is a lightweight entity: position, value, lifetime timer, team affiliation (only the killer's team can collect)

Pickup actors are a new entity type distinct from:
- Full entities (players, NPCs — have SoftState, OffensiveStats, movement)
- ProjectileActors (have velocity, collision, damage)
- ZoneActors (have radius, pulse logic)

Pickups are the simplest actor: a position, a value, and a proximity trigger for collection. They don't move, don't deal damage, and don't participate in combat.

### Passive Collection Radius
Each tick (or at a lower cadence), the Arbiter checks: are any uncollected essence orbs within the collector's pickup radius? This is a spatial query similar to SK-08 Aura, but instead of applying damage/debuffs, it consumes the pickup and credits the resource.

Collection must be:
- Team-restricted (only the killer's team can collect)
- One-time (collected orbs are despawned, not re-collectable)
- Attributed (credited to the specific entity that collected it, not the team generally)

### Secondary Resource System
The entity needs a resource separate from mana/energy:
```
struct EssenceState {
    current: u32,
    max: u32,
}
```

This is part of the entity's SoftState. The resource is:
- Gained by collecting pickups (passive)
- Consumed by activating the trait (active)
- Not regenerated over time (unlike mana)
- Not spent on abilities (unlike energy)
- Persists through death? (Design choice)

### Activation: Resource → Heal Conversion
When activated, the trait:
1. Reads `current_essence`
2. Calculates heal amount: `essence * heal_per_essence`
3. Sets `current_essence = 0`
4. Applies a heal-over-time effect (similar to SK-16 Holy Ground heal pulses, but self-only)

## Cross-Boundary Concerns

TODO: Essence orbs are entities on a specific Arbiter. If a minion dies near a boundary:
1. The orb spawns on the dead minion's Arbiter
2. A collector on a neighboring Arbiter sees the orb as... what? Orbs aren't standard entities with Ghosts. Do pickup actors get Ghost representations?
3. If the collector walks across the boundary to where the orb is, they're now on the orb's Arbiter and can collect normally
4. If the collector is within pickup radius but across the boundary (the orb is on Arbiter A, the collector is on Arbiter B), can they collect? This requires cross-boundary pickup relay.

Simpler approach: pickups are only collectible by entities on the same Arbiter. You must walk to where the orb is. This avoids cross-boundary pickup complexity.

## Compiler Requirements

TODO: Designer specifies:
- Passive component: death trigger (minion/monster deaths within range), spawn pickup (essence orb, value per type, lifetime 8s, team-restricted)
- Collection: passive proximity pickup, credit to secondary resource
- Active component: consume all stored essence, convert to heal-over-time (5s, proportional)
- Resource definition: essence (0/50 max, no regen, gained by collection only)

Compiler produces:
- Death hook: on qualifying entity death within range → spawn pickup actor
- Pickup actor definition (position, value, lifetime, team, collection radius)
- Per-tick collection check (spatial query for nearby uncollected pickups)
- Secondary resource field on SoftState
- Active ability: read resource → apply HoT → zero resource

## Open Questions

- Do essence orbs persist through Arbiter crashes (they're soft state — likely lost)?
- Can allies collect your essence orbs, or only the specific hero with the trait?
- Do essence orbs block movement or projectiles (probably not — no collision)?
- Are essence orbs visible to enemies (revealing where deaths occurred)?
- Does essence persist through the collector's death (keep accumulated essence on respawn)?
- How many essence orbs can exist simultaneously on an Arbiter (bounded for entity_count)?
- If 50 minions die simultaneously in a large fight, that's 50 pickup actors spawned in one tick — performance concern?
- Does the heal-over-time from activation benefit from healing-received bonuses?
- Can the activation be interrupted (it's instant consumption, but the HoT could be cleansed)?
- How does Kinematic Dilation affect orb lifetime and collection radius checks?
