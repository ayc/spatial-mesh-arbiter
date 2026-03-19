# SK-89: Respawn Anchor

## Designer Intent

I place a hidden egg at a location. When I die, instead of the normal long respawn timer (30+ seconds), I respawn at the egg's location after only 5 seconds. The egg is invisible to enemies but can be found and destroyed — if destroyed, I respawn normally. I can reposition the egg by placing a new one (old one despawns).

## Primitive Composition

P-32 (Actor Spawning) → P-39 (On-Death Hook) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position for egg placement (ground-targeted)

## Observable Behavior

1. Place egg at target position — egg is hidden from enemies, visible to allies
2. Only one egg can exist at a time (placing a new one despawns the old)
3. When the caster dies: respawn at egg position after 5 seconds (instead of normal 30+ seconds)
4. On respawn: egg is consumed (must place a new one)
5. If the egg is destroyed by enemies before death: normal respawn applies
6. Enemies can find the egg by walking near it (revealed within close proximity?)
7. Egg has low HP (1-2 hits to destroy)
8. Visual: small egg (allies see it clearly, enemies can't see it unless very close)

## Engine Primitives Required

### Death Lifecycle Override

This is the first ability that **modifies the death/respawn lifecycle**. The current death flow:
1. Entity HP reaches 0 → death declared
2. Entity removed from Arbiter
3. Meta Services handles respawn (timer, spawn position = last save zone)
4. Player reconnects at respawn position

With the egg:
1. Entity HP reaches 0 → death declared
2. Check: does this entity have an active respawn anchor?
3. If yes: respawn at egg position with reduced timer (5 seconds)
4. If no: normal respawn flow

The death lifecycle must support a **respawn override hook** — the game adapter can intercept the death event and specify an alternate respawn position and timer.

### Hidden Placed Entity

The egg is a placed entity with stealth properties (same as SK-32 Minefield):
- Invisible to enemies (excluded from enemy downstream payloads)
- Visible to allies (included in ally downstream payloads)
- Low HP (destructible)
- Static position (doesn't move)
- One per caster (placing a new one despawns the old)

### Respawn Position Override

When the caster dies, the spawn handshake normally uses `last_save_zone` from Meta's database. The egg overrides this:

```
fn determine_respawn(entity: &Entity, meta: &MetaService) -> RespawnParameters {
    if let Some(egg) = entity.active_respawn_anchor {
        if egg.is_alive {
            return RespawnParameters {
                position: egg.position,
                timer: 5_seconds,
                consume_anchor: true,  // Egg is used up
            };
        }
    }
    // Fallback: normal respawn
    meta.get_last_save_zone(entity.character_id)
}
```

### Egg Persistence Across Death

The egg entity must survive the caster's death. Normally, some effects/summons are cleaned up when their owner dies. The egg must persist:
- Caster dies → egg still exists on the Arbiter
- Egg is used for respawn → THEN egg is consumed
- If the caster had SK-06 summoned minions, those die. But the egg survives.

The egg needs a **persistence flag**: "this entity survives its owner's death."

## Cross-Boundary Concerns

TODO: The egg is a stationary entity on one Arbiter. The caster might die on a completely different Arbiter (across the map from the egg).

1. **Death → respawn at egg:** The caster dies on Arbiter A. The egg is on Arbiter B. The respawn must create the entity on Arbiter B (where the egg is), not on Arbiter A (where they died). This requires the spawn handshake to route to the egg's Arbiter.

2. **Egg on a different Arbiter than Meta's expected spawn:** Meta normally queries the Controller for "which Arbiter owns this save zone?" For the egg, Meta must query "which Arbiter owns the egg's position?" The egg's position must be accessible to Meta (stored in the entity's persistent data? Or queried from the Arbiter?).

3. **Egg destroyed cross-boundary:** If the egg is destroyed while the caster is alive on another Arbiter, the caster must be notified (so the UI updates). On death, the caster's death flow checks the egg's status — if destroyed, normal respawn.

4. **Topology change:** If the egg's Arbiter splits, the egg transfers to the child that inherits its position. The respawn override must still find the egg.

## Compiler Requirements

TODO: Designer specifies: place hidden egg (one at a time), egg HP, egg stealthed to enemies, on caster death → respawn at egg with reduced timer, egg consumed on use, if egg destroyed → normal respawn. Compiler produces:
- Egg entity definition (stealth, low HP, persistence-on-owner-death flag)
- Death lifecycle hook: check for active egg → override respawn parameters
- Single-instance constraint: placing new egg despawns old
- Egg consumption on respawn use

The compiler needs to support **death lifecycle hooks** — the game adapter can intercept the death event and provide custom respawn parameters.

## Open Questions

- Can the egg be placed inside structures or only on open ground?
- Can allies see the egg's position on the minimap?
- Can the egg be placed inside SK-60 Bunker for protection?
- Does the 5-second respawn timer benefit from respawn reduction effects (if any)?
- If the caster has SK-73 Death Immunity and it expires while at 1 HP, then they die — does the egg still work?
- Can the respawn at egg be interrupted or prevented by enemies?
- Does the caster respawn with full HP at the egg, or reduced HP?
- Is the caster's respawn at the egg visible to enemies (they see where the egg was)?
- If the egg is on a different Arbiter than the caster's death location, how does Meta coordinate the alternate respawn?
- Can SK-54 Entity Consumption eat the egg (swallow the egg)?
- Does the egg count toward entity_count for split triggers?
