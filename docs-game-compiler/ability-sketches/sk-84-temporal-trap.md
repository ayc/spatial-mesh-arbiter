# SK-84: Temporal Trap

## Designer Intent

I target an enemy hero. Their current position is stored. After 3 seconds, they are forcibly teleported back to that stored position, regardless of where they've moved. The enemy sees a countdown indicator and knows it's coming — they have 3 seconds to prepare (use defensives, position near allies for protection).

## Primitive Composition

P-32 (Actor Spawning) → P-45 (Delay Timer) → P-05 (Historical State Buffer) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy — their current position is stored, countdown begins (3 seconds)
2. The enemy sees a visible countdown indicator and a marker at their stored position
3. The enemy can move freely, use abilities, fight normally during the countdown
4. After 3 seconds: the enemy is FORCIBLY teleported to the stored position (instant snap)
5. The teleport cannot be avoided by normal movement (you're pulled back regardless)
6. SK-51 Unstoppable can prevent the teleport (it's forced displacement — a form of CC)
7. The teleport deals no damage (purely repositioning)
8. Visual: hourglass marker at stored position, countdown clock on the enemy, time-warp effect on teleport

## Engine Primitives Required

### Hostile Positional Bookmark

SK-37 Time Rewind stores the CASTER's own position for self-use. SK-84 stores the TARGET's position for hostile use:

```
status_effect: TemporalTrapDebuff {
    stored_position: Vec2F,
    stored_arbiter_id: u32,
    stored_topology_epoch: u32,
    activates_at_tick: u64,
    caster_id: EntityID,  // For CC attribution and Tenacity/DR
}
```

On expiry (3 seconds later):
1. Read `stored_position`
2. Snap the target to `stored_position` (instant teleport, like SK-35)
3. Remove the debuff

### Forced Teleport as CC

The teleport is a form of forced displacement — the target is moved against their will. This means:
- SK-51 Unstoppable should prevent it (CC immunity blocks forced displacement)
- Tenacity could reduce the "severity" — but teleport is binary (you go or you don't). Should Tenacity reduce the countdown timer instead?
- DR (SK-28) applies — categorized as displacement CC

### Stale Position Handling

The stored position was valid 3 seconds ago. By the time the teleport fires:
- The stored position might now be inside SK-03 Terrain Wall (wall placed since storage)
- The stored position might be on a different Arbiter (topology changed)
- The stored position might be inside SK-29 Blizzard (zone placed since storage)

On teleport, the engine must validate the stored position:
1. Is it still walkable? If not, find nearest valid position.
2. Which Arbiter owns it? Might differ from when it was stored.
3. Teleport the entity there (instant cross-boundary handoff if needed).

### Countdown Visibility

The enemy (and their allies) can see:
- The countdown timer (3, 2, 1...)
- The stored position marker (where they'll be pulled back to)

This is a downstream payload to the target's Edge Node: "you have TemporalTrap, stored position is here, countdown is N ticks." The client renders the marker and countdown.

## Cross-Boundary Concerns

TODO: The stored position is an absolute world coordinate. In 3 seconds, the target may have moved far:

1. **Target moved within same Arbiter:** Simple snap back to stored position (local).
2. **Target crossed a boundary:** Target is now on Arbiter B but stored position is in Arbiter A's region. The teleport requires an instant handoff from B to A.
3. **Topology changed:** The Arbiter that owned the stored position 3 seconds ago may no longer exist (split/merged). The engine must resolve the current owner of the stored position using the Controller's R-Tree.
4. **Stored position absorbed by different Arbiter after crash:** The stored position's region was absorbed by a neighbor. The snap targets the absorbing Arbiter.

The stored `topology_epoch` helps detect staleness — if it differs from the current epoch, re-query the owner.

## Compiler Requirements

TODO: Designer specifies: target (enemy), store target's current position, countdown (3s), on-expiry force teleport to stored position, Unstoppable blocks it, Tenacity reduces countdown(?), visible countdown to target, no damage. Compiler produces:
- TemporalTrapDebuff status effect with stored position + countdown
- On-expiry hook: validate stored position → instant teleport
- CC classification: forced displacement category
- Downstream payload: countdown + position marker for client rendering
- Stale position validation on teleport

## Open Questions

- Can the debuff be cleansed by SK-15 Purify (preventing the teleport)?
- Does Tenacity reduce the countdown timer or is the teleport binary (happens or doesn't)?
- If the target enters SK-44 Burrow (invulnerable) when the countdown expires, does the teleport happen?
- If the target is inside SK-54 Entity Consumption (consumed) when the countdown expires, what happens?
- Can the caster place the trap on an ally (friendly use — save an ally by pulling them back to safety)?
- Does the teleport trigger SK-32 Minefield at the stored position?
- If the stored position is now inside SK-31 Vortex, does the target get pulled into the vortex?
- Can the target use SK-35 Blink Strike to escape the teleport (does it cancel the debuff)?
- Does the teleport count as "displacement" for SK-25 Root interaction (root prevents displacement)?
