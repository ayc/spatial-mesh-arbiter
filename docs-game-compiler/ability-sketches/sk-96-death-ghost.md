# SK-96: Death Ghost

## Designer Intent

When I die, instead of immediately despawning, I persist as a ghost for 8 seconds. Ghost form can still cast healing abilities on allies but cannot move, cannot attack, and cannot be targeted. After 8 seconds, the ghost fades and normal death/respawn begins.

## Primitive Composition

P-39 (On-Death Hook) → P-32 (Actor Spawning) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- No input (triggered automatically on death)

## Observable Behavior

1. HP reaches 0 — entity "dies" but instead of despawning, enters ghost form
2. Ghost form: can't move (fixed at death position), can't attack, can't be targeted
3. Ghost form: CAN cast healing abilities on allies (reduced selection)
4. Ghost form lasts 8 seconds
5. After 8 seconds: ghost fades, entity is truly removed, normal respawn timer begins
6. Ghost form has no HP (cannot be "killed again")
7. The death event IS triggered (kill credit given to the killer) — ghost is a post-death bonus
8. Visual: translucent/spectral appearance, restricted ability bar

## Engine Primitives Required

### Post-Death Active Phase

This is the first ability where an entity remains ACTIVE after death. The current death pipeline:
1. HP reaches 0 → death declared
2. Entity removed from Arbiter
3. Meta handles respawn

With Death Ghost:
1. HP reaches 0 → death declared (killer gets credit, HardEvent emitted)
2. Entity transitions to GHOST FORM instead of being removed
3. Ghost form runs for 8 seconds (entity stays in the Arbiter's entity map)
4. After 8 seconds: entity is truly removed, Meta handles respawn

```
struct DeathGhostState {
    expires_at_tick: u64,
    allowed_abilities: Vec<AbilityId>,  // Only healing abilities
    is_untargetable: bool,   // true
    is_immobile: bool,       // true
    is_dead: bool,           // true (death was declared, respawn timer started)
}
```

### Dead But Present

The entity is in a paradoxical state:
- **Dead** for game purposes (kill credit given, death events fired, respawn timer running)
- **Present** in the entity map (still has a position, still occupies space conceptually)
- **Active** for limited purposes (can cast healing abilities)
- **Untargetable** (cannot be targeted by any ability)
- **Immobile** (fixed at death position)

This requires the entity state to support "dead but not removed" — a new lifecycle phase.

### Respawn Timer Interaction

The 8-second ghost duration and the normal respawn timer run CONCURRENTLY:
- Normal respawn timer: 30 seconds (starts at death)
- Ghost duration: 8 seconds (also starts at death)
- After ghost expires: entity is removed from Arbiter
- Remaining respawn time: 30 - 8 = 22 seconds (entity waits in respawn queue)

The ghost doesn't delay respawn — it's bonus time. The total time from death to respawn is the same.

### Limited Ability Usage While "Dead"

The ghost can only use healing abilities. The `validate_intent` hook must check:
1. Is the entity in ghost form?
2. Is the attempted ability in the `allowed_abilities` list?
3. If yes: proceed with resolution. If no: reject.

The healing abilities use the entity's stats as they were at death (no stat updates in ghost form).

## Cross-Boundary Concerns

TODO: The ghost entity remains on the Arbiter where it died. It can target allies for healing — allies might be local or Ghosts (cross-boundary). Healing relays from the death ghost work the same as any other heal relay.

Since the ghost is immobile, it can't cross boundaries. No handoff concerns.

The only concern: the death event was fired (Meta starts respawn timer), but the entity is still in the Arbiter's map for 8 more seconds. Meta must know about the ghost duration — the entity isn't available for respawn relocation until the ghost expires.

## Compiler Requirements

TODO: Designer specifies: on-death trigger, ghost duration (8s), immobile + untargetable, can cast healing abilities only, death event still fires normally, respawn timer starts at death (not at ghost expiry). Compiler produces:
- Death interception hook: instead of removing entity, transition to ghost form
- DeathGhostState with timer, allowed abilities, capability restrictions
- Death event emission (kill credit, HardEvent) at the moment of death, not at ghost expiry
- Entity removal at ghost expiry
- Limited ability validation during ghost form

The compiler needs to support **post-death entity phases** — entity lifecycle states between "dead" and "removed."

## Open Questions

- Does the ghost's healing trigger on-heal effects (SK-04 Tether heal sharing)?
- Can the ghost be affected by SK-91 Team-Agnostic Stasis (it's untargetable but stasis hits everything)?
- Does the ghost block pathing (enemies walk through it)?
- Can the ghost's healing be anti-healed (SK-92)?
- If the ghost has SK-08 Aura, does the aura persist during ghost form (passive damage while dead)?
- Does the death ghost interact with SK-89 Respawn Anchor (egg respawn overrides normal respawn)?
- Can SK-93 Death Prevention trigger on the ghost (preventing "true death" at ghost expiry)? Probably no — the entity is already "dead."
- Does the ghost see the same area as when they died, or does their vision update?
- If the Arbiter crashes during the ghost phase, is the entity lost (soft state)?
- Can the ghost use non-healing abilities in a talented variant (e.g., one stun ability)?
