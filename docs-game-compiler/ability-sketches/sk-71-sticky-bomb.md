# SK-71: Sticky Bomb

## Designer Intent

I throw a bomb that attaches to an enemy hero. The bomb sticks to them and follows their movement. After 2 seconds, the bomb detonates at the target's CURRENT position, dealing AoE damage to the target and all nearby enemies. The target can't remove the bomb — they can only try to run away from their allies to minimize collateral.

## Primitive Composition

P-06 (Attached Kinematics) → P-45 (Delay Timer) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy — bomb attaches to the target
2. The bomb is visible on the target (ticking indicator)
3. The bomb moves with the target — wherever they go, the bomb follows
4. After 2 seconds: bomb detonates at the target's current position
5. AoE damage: the target takes full damage, nearby enemies take AoE damage
6. The target cannot remove the bomb (not cleansable? Design choice)
7. Visual: glowing bomb attached to the target, countdown timer, explosion on detonation

## Engine Primitives Required

### Entity-Attached Delayed Effect

Unlike SK-29 Blizzard (AoE at a fixed position) or SK-02 Poison Shot (DoT on a target), the Sticky Bomb is a **delayed AoE whose position is determined at detonation time, not at cast time**:

```
status_effect: StickyBomb {
    caster_id: EntityID,
    detonation_tick: u64,
    aoe_radius: SimFixed,
    aoe_damage: SimFixed,
    combat_context: CombatContext,  // Pre-rolled at cast time
}
```

The key difference from a DoT: a DoT applies damage directly to the carrier. The Sticky Bomb applies AoE damage at the carrier's position — affecting OTHER entities nearby. The bomb is both a debuff on the carrier AND a deferred AoE centered on a moving entity.

### Detonation Resolution

On detonation tick:
1. Read the carrier's current position
2. Perform spatial query: all enemies within `aoe_radius` of carrier's position
3. Apply damage to the carrier (guaranteed hit)
4. Apply AoE damage to all other enemies in radius
5. Remove the bomb effect

This is a spatial query anchored to an entity's position at a future tick — not a fixed position. The carrier could be anywhere on the map by detonation time.

### Interaction With Displacement

The bomb creates emergent gameplay because the target is incentivized to move AWAY from allies. Displacement abilities interact interestingly:
- SK-01 Toss: ally tosses the bombed enemy into the enemy team → the bomb detonates among enemies (combo play)
- SK-43 Drag: drag the bombed enemy toward you → bomb detonates on your team (anti-combo)
- SK-35 Blink Strike: bombed enemy blinks away from allies → solo detonation

## Cross-Boundary Concerns

TODO: The bomb effect lives on the carrier's entity (their Arbiter). On detonation, the AoE spatial query is local to the carrier's Arbiter + Ghosts. If the carrier moved cross-boundary since the bomb was attached, the detonation happens on their current Arbiter — not the caster's. The CombatContext carries the caster's offensive stats (pre-rolled), so damage is resolved correctly regardless of which Arbiter the detonation occurs on.

The caster doesn't need to be involved at detonation — the bomb is a self-contained delayed effect on the carrier.

## Compiler Requirements

TODO: Designer specifies: target (enemy), attachment (follows target movement), detonation delay (2s), AoE radius, AoE damage, target takes full damage, cleansable (yes/no). Compiler produces:
- Status effect with detonation timer + AoE parameters + CombatContext
- On-expiry hook: spatial query at carrier's current position → AoE damage
- Pre-rolled CombatContext at cast time (epoch-pinned)

## Open Questions

- Can the bomb be cleansed by SK-15 Purify? If yes, the bomb is removed without detonating.
- Does the detonation AoE damage allies of the bomber (the caster's team) — i.e., is it enemy-only?
- Can the bomb be applied to untargetable entities (SK-44 Burrow)? If the target burrows after being bombed, does it detonate underground?
- If the carrier dies before detonation, does the bomb detonate at the death position or fizzle?
- Does the bomb damage trigger on-hit procs for the caster (SK-09 Chain Lightning)?
- Can multiple sticky bombs be on the same target simultaneously?
- Does the AoE damage hit the caster if they're near the target at detonation?
- How does the bomb interact with SK-54 Entity Consumption — if the carrier is consumed, does the bomb detonate inside the consumer?
