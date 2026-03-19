# SK-36: Shadow Step

## Designer Intent

I blink to a target position instantly. For the next 3 seconds, I can reactivate the ability to teleport back to my original position. If I don't reactivate, the bookmark expires and I stay where I am. This lets me dive into a fight, burst a target, and escape back to safety.

## Primitive Composition

P-01 (Instant Translation) → P-05 (Historical State Buffer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)
- Reactivation input (same ability key, within 3-second window)

## Observable Behavior

1. First cast: caster blinks to target position (instant, like SK-35)
2. A shadow/marker is left at the original position (visible to allies, optionally to enemies)
3. For 3 seconds: ability icon changes to "Return" — pressing it again teleports the caster back to the shadow position
4. If reactivated: caster snaps back to the shadow position instantly
5. If not reactivated within 3 seconds: shadow fades, caster stays at current position, ability goes on full cooldown
6. If the caster dies during the 3-second window: no return (shadow fades)
7. Visual: dark shadow at the bookmark position, trail effect on return blink

## Engine Primitives Required

### Positional Bookmark
The first blink stores the caster's pre-blink position as a field on a status effect:

```
status_effect: ShadowStepBookmark {
    bookmark_position: Vec2F,
    bookmark_tick: u64,
    bookmark_topology_epoch: u32,
    bookmark_arbiter_id: u32,
    expires_at_tick: u64,
}
```

This is a lightweight status effect — one Vec2F, a few u32/u64 fields. No per-tick cost beyond the normal effect expiry check. The Arbiter doesn't maintain any global tracking — the bookmark is just data on the caster's effect list.

### Reactivation
The ability has two phases (cast modes):
- Phase 1 (no active bookmark): blink forward, apply ShadowStepBookmark effect
- Phase 2 (bookmark active): read bookmark position, snap caster to it, remove effect

The engine needs to support **multi-phase abilities** — an ability whose behavior changes based on whether a specific status effect is active on the caster. The `validate_intent` hook checks: does the caster have ShadowStepBookmark? If yes, this is a return cast. If no, this is a forward blink.

### Blink Mechanics
Both the forward blink and the return blink are instant position snaps (same as SK-35 Blink Strike). No travel time, no intermediate positions.

## Cross-Boundary Concerns

TODO: The forward blink may cross an Arbiter boundary (same as SK-35). The bookmark stores the position AND the Arbiter context (`bookmark_arbiter_id`, `topology_epoch`). On return:

1. **Bookmark is in same Arbiter region:** Simple position snap. No handoff.
2. **Bookmark is in a different Arbiter's region (caster blinked cross-boundary):** Return requires an instant handoff back to the original Arbiter.
3. **Topology changed since bookmark was set (split/merge happened):** The `bookmark_topology_epoch` is stale. The bookmark position might now be owned by a different Arbiter than `bookmark_arbiter_id`. The return needs to query the current owner of the bookmark position.
4. **Bookmark position is no longer valid (SK-03 Terrain Wall placed on top of it):** Snap to nearest valid position, or fail the return?

## Compiler Requirements

TODO: Designer specifies: blink (instant teleport to requested ground-target position), bookmark (store origin position), reactivation window (3s), return (instant teleport to bookmark). Compiler produces:
- Phase 1: position snap + apply ShadowStepBookmark status effect
- Phase 2: read bookmark → position snap → remove effect
- Multi-phase ability routing via validate_intent hook (check for active bookmark)
- Bookmark data as a status effect extension field

The compiler validates that the bookmark is bounded (single position, fixed expiry) and that the reactivation is a deterministic check.

## Open Questions

- Can the shadow/marker be attacked or destroyed by enemies to prevent the return?
- Does the return blink trigger SK-32 Minefield at the bookmark position?
- If the caster is rooted (SK-25) during the return window, can they still reactivate (is the return a "teleport" that bypasses root)?
- Does the return blink break SK-04 Tether if it exceeds break distance?
- If the caster picks up a flag/objective between blink and return, does the objective travel back with them?
- Can the return be used while CC'd (stun/silence)? Silence blocks casts, but is reactivation a "cast"?
- Does the bookmark persist through SK-15 Purify (is the bookmark a positive effect that could be accidentally cleansed)?
