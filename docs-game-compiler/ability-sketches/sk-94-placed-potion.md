# SK-94: Placed Potion

## Designer Intent

I throw a healing potion on the ground. The potion sits there as a glowing pickup. Any ally who walks over it picks it up and is healed. If nobody picks it up within 20 seconds, it despawns. I can have up to 5 potions on the ground at once. I'm pre-positioning healing for my team.

## Primitive Composition

P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted)

## Observable Behavior

1. Cast — potion appears at target position on the ground
2. Potion is visible to all players (allies see heal amount, enemies see the potion exists)
3. First ally to walk within pickup radius collects it → healed for X HP
4. The collector chooses WHEN to pick it up (by walking over it)
5. Potion persists for 20 seconds if not collected
6. Maximum 5 potions on the ground simultaneously (oldest despawns if 6th is placed)
7. Potions can be placed pre-fight (set up healing stations)
8. Enemies CANNOT pick up or destroy potions (in base version)
9. Visual: glowing flask on the ground, absorption effect on pickup

## Engine Primitives Required

### Friendly Placed Consumable

SK-45 Essence Collection has death-spawned pickups collected by the killer. Placed Potion is different:
- PLACED by a healer (not spawned by death)
- COLLECTED by any ally (not just the placer)
- HEALS on collection (not resource credit)
- Multiple can exist simultaneously (up to 5)
- Persists for a long duration (20 seconds)

```
struct PotionPickup {
    potion_id: EntityID,
    position: Vec2F,
    heal_amount: SimFixed,
    owner_team: TeamId,
    caster_id: EntityID,        // For pickup limit tracking
    pickup_radius: SimFixed,
    expires_at_tick: u64,
}
```

### Proximity Collection for Allies

Each tick, the Arbiter checks: is any allied entity within pickup_radius of any uncollected potion? On collection:
1. Heal the collecting entity for `heal_amount`
2. Despawn the potion entity
3. The heal goes through normal heal resolution (affected by SK-92 Anti-Heal)

### Per-Caster Pickup Limit

The caster can have at most 5 potions on the ground. The Arbiter must track: how many active potion entities belong to this caster? If placing a 6th, the oldest potion despawns.

This is a **per-caster entity count limit** for a specific entity type. Different from the global entity_count limit for Arbiter splits.

### Agency Split: Healer vs Recipient

The unique design aspect: the HEALER decides WHERE healing is available, the RECIPIENT decides WHEN to use it. The healer pre-positions potions; allies collect when they need healing. This creates:
- Strategic potion placement (chokepoints, retreat paths, objectives)
- Ally skill expression (walking over a potion at the right moment)
- Enemy awareness (seeing potions and playing around them)

No other heal has this agency split — all other heals are healer-targeted (SK-16 zone), healer-auto-targeted (Li Li), or instant (direct heal).

## Cross-Boundary Concerns

TODO: Potions are stationary entities on one Arbiter. An allied Ghost walking over a potion:
- The potion's Arbiter detects the Ghost within pickup radius
- Relay "heal for X" to the Ghost's owning Arbiter
- Despawn the potion locally

The per-caster limit must track potions across Arbiters if the caster places potions in different regions. Or: potions are always on the caster's current Arbiter (can only place nearby).

## Compiler Requirements

TODO: Designer specifies: ground-targeted placement, heal on ally pickup, 20s lifetime, max 5 per caster (oldest despawns), ally-only collection, pickup radius. Compiler produces:
- PotionPickup entity definition (position, heal, team, lifetime)
- Per-tick proximity collection check (allies within radius)
- Heal application through standard heal pipeline
- Per-caster instance limit (max 5, FIFO despawn)

## Open Questions

- Can enemies destroy potions (attack them)?
- Can enemies see the heal amount, or just that a potion exists?
- Does the potion heal go through SK-92 Anti-Heal?
- Can the caster pick up their own potions?
- Can SK-31 Vortex pull allies onto potions (forced collection)?
- Do potions block pathing?
- Can potions be placed inside SK-60 Bunker?
- Do potions count toward entity_count for split triggers?
- Can potions be placed on top of each other (stacking)?
- Does SK-91 Team-Agnostic Stasis freeze potion expiry timers?
