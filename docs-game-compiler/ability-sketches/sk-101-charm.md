# SK-101: Charm

## Designer Intent

I blow a kiss that charms an enemy. For 1.5 seconds, the charmed enemy walks directly toward me uncontrollably. They can't attack, cast, or choose their direction — they're just drawn to me. This sets up follow-up abilities by bringing the enemy into my range.

## Primitive Composition

P-03 (Trajectory Steering) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the charm source)
- Target enemy entity (hit by skillshot or targeted)

## Observable Behavior

1. Ability hits enemy — charm applied for 1.5 seconds
2. Charmed enemy walks directly toward the caster at reduced speed (normal move speed or reduced)
3. Charmed enemy cannot attack, cast, or control their movement
4. The walk direction updates based on the caster's CURRENT position (if caster moves, the charmed entity follows)
5. Duration reduced by Tenacity
6. Subject to Diminishing Returns (SK-28) — hard CC category
7. Cleansable by SK-15 Purify
8. Visual: hearts floating above the charmed enemy, dreamy walk animation

## Engine Primitives Required

### New CC Type: Charm (Forced Approach)

Charm is the inverse of SK-78 Fear:

| CC Type | Movement Direction | Can Act? |
|---|---|---|
| SK-78 Fear | AWAY from source | No |
| **SK-101 Charm** | **TOWARD source** | **No** |
| SK-65 Taunt | Free (player-controlled) | Yes (forced auto-attack target) |
| SK-40 Mind Control | Caster-steered | No |

```
status_effect: CharmDebuff {
    charm_source_id: EntityID,  // Walk toward this entity
    walk_speed: SimFixed,       // Speed during charm (may be reduced)
    expires_at_tick: u64,
}
```

Each tick while charmed:
1. Read `charm_source_id`'s current position
2. Calculate direction: `normalize(source.position - entity.position)`
3. Override entity's movement: `direction * walk_speed`
4. Suppress all actions (can't attack, can't cast)

### Dynamic vs Static Direction

Unlike SK-78 Fear (which uses a STATIC flee direction calculated once at application), Charm should use a DYNAMIC direction — the charmed entity walks toward the caster's CURRENT position each tick. This is because:
- Fear: you flee in a straight line (simple, deterministic)
- Charm: you walk toward the caster, who might be moving (you need to track them)

Dynamic direction means the charmed entity's Arbiter needs the caster's position every tick. If the caster is a Ghost (cross-boundary), the direction uses Ghost position (approximate).

### Charm + Fear Interaction

If an entity has both Charm (walk toward source A) and Fear (walk away from source B):
- Which takes priority? Most recent? Highest CC tier?
- Can both exist simultaneously (conflicting movement directions)?
- Design: typically the most recent hard CC overrides the previous one

## Cross-Boundary Concerns

TODO: If the charmed entity is on a different Arbiter than the caster:
1. The charmed entity's Arbiter sees the caster as a Ghost
2. Each tick, the charm direction is calculated using the Ghost's position (dead-reckoned, possibly stale)
3. The charmed entity walks toward the Ghost's approximate position
4. Slight tracking inaccuracy is acceptable (the entity walks in roughly the right direction)

If the charmed entity walks toward the caster and crosses a boundary (approaching the caster's Arbiter), the handoff occurs mid-charm. The charm effect transfers with the handoff. On the new Arbiter, the caster is local — tracking becomes exact.

## Compiler Requirements

TODO: Designer specifies: CC type (charm — forced approach), target walks toward caster, walk speed, duration (1.5s), full disable (no attack/cast), dynamic direction (tracks caster position), Tenacity-reducible, DR category (hard CC), cleansable. Compiler produces:
- CharmDebuff status effect with charm_source_id
- Per-tick movement override: direction toward source entity's position
- Full capability suppression
- Dynamic direction update (source entity tracking)

The compiler adds Charm to the CC type system. Charm and Fear share the same implementation pattern (forced directional movement) but with opposite direction signs.

## Open Questions

- Does the charmed entity stop when they reach the caster, or walk through them?
- Does SK-51 Unstoppable prevent charm?
- Does SK-88 Positional Leash constrain the charm walk (leashed entity charmed → walks toward caster but can't leave leash radius)?
- Can the charmed entity be pushed/displaced by other abilities while charmed?
- Does the caster need to remain alive for the charm to persist? (If caster dies, does charm break?)
- Is the walk speed the charmed entity's normal speed or a fixed/reduced speed?
- Does the charmed entity's movement respect collision (can't walk through walls)?
- Does charm count as "taking damage" for SK-27 Sleep break check? (No — charm isn't damage)
- Can charm pull the target across Arbiter boundaries (walking toward caster on another Arbiter)?
