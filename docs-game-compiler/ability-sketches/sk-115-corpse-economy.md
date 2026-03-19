# SK-115: Corpse Economy

## Designer Intent

When enemies die, they leave corpses on the ground. My class has multiple abilities that CONSUME corpses for different effects. Corpse Explosion detonates a corpse for AoE damage. Raise Skeleton consumes a corpse to summon a minion. Corpse Lance fires projectiles from corpse positions. Each ability eats one corpse. Corpses are a spatial resource — where they are matters, and managing them is core to my gameplay.

## Primitive Composition

P-39 (On-Death Hook) → P-47 (Spatial Corpse Registry) → P-11 (N-Nearest Neighbor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Dead enemy entities leave corpse objects at their death position
- Caster chooses which ability to use on/near a corpse
- Each ability consumes one or more corpses

## Observable Behavior

1. Enemy dies → corpse object appears at death position
2. Corpse persists for 30 seconds (or until consumed)
3. **Corpse Explosion**: target a corpse → it explodes dealing AoE damage scaled by the dead enemy's max HP
4. **Raise Skeleton**: target a corpse → it's consumed, a skeleton minion spawns at the corpse position
5. **Corpse Lance**: target an enemy → the nearest N corpses each launch a projectile at the target, each corpse consumed
6. Each corpse can only be consumed ONCE (first ability to use it claims it)
7. Multiple corpses from a big fight = more resources to spend
8. Visual: corpse objects on ground (bone piles, bodies), consumed with appropriate effect (explosion, skeleton rising, projectile launching)

## Engine Primitives Required

### Multi-Consumer Spatial Resource

SK-45 Essence Collection has one pickup type consumed by one ability (collect essence → activate trait to heal). Corpse Economy has one resource type (corpses) consumed by MULTIPLE DIFFERENT abilities, each producing a different outcome:

```
struct CorpseEntity {
    corpse_id: EntityID,
    position: Vec2F,
    source_entity_max_hp: SimFixed,  // For Corpse Explosion damage scaling
    source_entity_level: u16,        // For Raise Skeleton stat scaling
    created_at_tick: u64,
    expires_at_tick: u64,
    consumed: bool,
}
```

The key difference from single-consumer pickups:
- SK-45: walk over orb → one effect (credit essence)
- SK-115: target corpse with ability A → effect A (explosion). OR target with ability B → effect B (summon). OR ability C auto-selects nearest corpses → effect C (projectiles)

The engine must support: "this ability consumes a corpse entity" as a COST, where the consumed entity's data is available to the ability resolution.

### Corpse as Ability Input

When an ability targets or consumes a corpse, the ability resolution receives the CORPSE'S DATA as input:
- Corpse Explosion: `damage = corpse.source_entity_max_hp * percentage` — damage scales with the dead enemy's stats
- Raise Skeleton: `skeleton_hp = base + corpse.source_entity_level * scaling` — minion stats scale with corpse quality
- Corpse Lance: `projectile_count = nearby_corpses.len()` — more corpses = more projectiles

The ability's resolve_external hook must receive the consumed corpse's data alongside the normal CombatContext. This is a new input type for ability resolution — not just "caster stats + target stats" but also "consumed entity stats."

### Spatial Resource Management

Corpses are POSITIONED resources. Their location matters:
- Corpse Explosion: AoE originates at the CORPSE's position, not the caster's
- Raise Skeleton: minion spawns at the CORPSE's position
- Corpse Lance: projectiles launch FROM corpse positions

The caster must be near corpses to use them (range check against corpse positions). Abilities that consume corpses perform a spatial query for "nearest corpse within range."

### Contention: Multiple Consumers

If multiple Necromancers are in the same fight, they compete for corpses. Corpse consumption must be atomic — the first ability to claim a corpse gets it. The second ability targeting the same corpse fails (corpse already consumed).

```
fn try_consume_corpse(corpse: &mut CorpseEntity) -> bool {
    if corpse.consumed { return false; }
    corpse.consumed = true;
    true
}
```

This is a contention lock on a resource — similar to the contention lock algorithm gap (T1-04) in the spec.

### Corpse Generation Rate

In a big fight, many enemies die = many corpses = lots of resources. In a quiet area, few corpses = limited ability usage. The corpse economy creates a **fight-dependent resource cycle**: the more enemies you kill, the more corpses you get, the more abilities you can use. This is intrinsically tied to the ARPG combat loop.

## Cross-Boundary Concerns

TODO: Corpses are stationary entities on whichever Arbiter the enemy died on. Cross-boundary concerns:

1. **Corpse near boundary**: A corpse is on Arbiter A near the boundary. A Necromancer on Arbiter B wants to consume it. The Necromancer's Arbiter needs to know about the corpse (is it visible as a Ghost-like entity?). If yes, the consume command relays to Arbiter A.

2. **Corpse Lance from cross-boundary corpses**: Corpse Lance consumes the nearest N corpses. Some might be on the local Arbiter, some near the boundary on a neighbor. Multi-Arbiter corpse consumption in a single ability.

3. **Corpse explosion near boundary**: The AoE originates at the corpse position on Arbiter A. Enemies in the AoE might be Ghosts from Arbiter B. Standard AoE relay.

Simplest approach: corpses are only consumable by entities on the same Arbiter. You must walk to where the corpses are.

## Compiler Requirements

TODO: Designer specifies: death-spawned corpse entities (position, source stats, lifetime), multiple abilities that consume corpses for different effects (explosion, summon, projectile), corpse as ability cost + data input, spatial resource (position matters), contention resolution (first-claim-wins). Compiler produces:
- CorpseEntity definition (spawned on qualifying entity death)
- Per-ability corpse consumption logic (atomic claim)
- Per-ability resolution using corpse data as input (damage from corpse HP, minion from corpse level)
- Spatial query for nearby corpses (range check from caster)
- Corpse lifetime management (expiry timer)

The compiler needs to support **entity-as-ability-cost** — abilities that consume a spatial entity and use that entity's data in resolution. This generalizes beyond corpses to any consumable placed entity.

## Open Questions

- Do all enemy deaths produce corpses, or only specific types (monsters, not summons)?
- Can allies' deaths produce corpses (consume your own team's corpses)?
- Do corpses block pathing?
- Can enemies interact with corpses (deny them by destroying/consuming them)?
- Does the corpse's source_entity_max_hp use pre-buff or base max HP?
- How many corpses can exist simultaneously on one Arbiter (entity_count concern)?
- Can corpses be created by abilities (e.g., "create a corpse at target position" for setup)?
- Does SK-107 Corpse Possession compete with Corpse Economy for the same corpses?
- How does the corpse economy interact with SK-06 Summon Swarm — do killed summons leave corpses?
- Does Kinematic Dilation affect corpse expiry timers?
