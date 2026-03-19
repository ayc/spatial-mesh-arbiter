# SK-61: Spirit Split

## Designer Intent

I split into three elemental spirits — Storm, Earth, and Fire. Each spirit is an independent entity with its own HP and one unique ability. I control one spirit at a time and can swap between them. When a spirit dies, it's gone. When the duration expires (or I reactivate), I reform at the position of the spirit I'm currently controlling.

## Primitive Composition

P-32 (Actor Spawning) → P-56 (Spatial Instance Forking) → P-30 (Input Multiplexing)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)
- Tab/swap input to rotate control between spirits

## Observable Behavior

1. Activate — caster disappears, three spirits spawn at caster's position
2. Each spirit has 1/3 of the caster's max HP
3. Each spirit has one unique ability (Storm: ranged AoE, Earth: AoE slow, Fire: dash + damage)
4. Player controls one spirit at a time — movement and abilities
5. The other two spirits follow the controlled one (AI leash behavior)
6. Press swap key to rotate control: Storm → Earth → Fire → Storm
7. Spirits can be killed independently — dead spirits are gone
8. If all three die: caster dies (real death)
9. Duration expires or reactivate: spirits merge, caster reforms at the controlled spirit's position
10. Caster's HP on reform = sum of surviving spirits' remaining HP
11. Visual: three distinct elemental spirits, active one highlighted, merge effect on reform

## Engine Primitives Required

### Entity Splitting

One entity becomes three. The Arbiter must:
1. Remove the original entity from the entity map
2. Mint 3 new EntityIDs
3. Create 3 new entities at the caster's position
4. Each gets 1/3 of the caster's max HP
5. Each gets a unique ability set (from SpellData)
6. Link all three to a shared `SplitState` that tracks the group

```
struct SplitState {
    original_entity_id: EntityID,
    original_soft_state: SoftStateSerialized,  // For reform
    spirit_ids: [Option<EntityID>; 3],         // None if dead
    active_spirit_index: u8,                   // Currently controlled
    expires_at_tick: u64,
}
```

### Control Rotation

The player's Edge Node sends input. Normally, input maps to one entity. During Spirit Split, input maps to whichever spirit is "active." The swap command rotates `active_spirit_index`.

The Arbiter must:
- Route movement input to the active spirit only
- Route ability input to the active spirit only (which has its own unique ability)
- Inactive spirits follow via AI leash (simple: move toward active spirit, stay within radius)

This means the entity-to-Edge-Node mapping is temporarily 1-to-3: one Edge session controls three entities, one at a time.

### Reform / Recombine

When the duration expires or the player reactivates:
1. Read the controlled spirit's position
2. Sum surviving spirits' HP
3. Despawn all surviving spirits
4. Re-create the original entity at the controlled spirit's position
5. Set HP = summed HP (capped at original max HP)
6. Restore original ability set
7. Update the Edge Node's entity mapping back to the original entity

### Death Handling

If a spirit dies:
- Remove it from `spirit_ids` (set to None)
- If all three are None: the caster ACTUALLY dies (trigger death flow)
- If at least one survives: caster is alive, will reform at a survivor's position

## Cross-Boundary Concerns

TODO: Three spirits can move independently (AI follows, but they have separate positions). They could spread across Arbiter boundaries:

1. **All three on same Arbiter:** Simple. Control rotation and AI are local.
2. **Spirits on different Arbiters:** The active spirit (player-controlled) is on Arbiter A. An inactive spirit (AI leash) is on Arbiter B. Control rotation would switch the player's input to an entity on Arbiter B. The Edge Node's routing must change dynamically.
3. **Reform position on different Arbiter:** If the controlled spirit is on Arbiter B but the original entity was on Arbiter A, the reform creates the entity on Arbiter B. The Edge Node is redirected.

The simplest approach: constrain spirits to stay within leash range so they don't cross boundaries. Or: allow cross-boundary spirits but handle the control rotation as an entity handoff.

## Compiler Requirements

TODO: Designer specifies: 3 spirits, HP split (1/3 each), per-spirit ability sets (3 unique abilities), control rotation, AI leash for inactive spirits, reform on expiry/reactivation (sum HP, reform at active spirit), death if all spirits die. Compiler produces:
- Entity split action: despawn original, spawn 3 spirits with linked SplitState
- Per-spirit ability definitions (3 separate ability sets in SpellData)
- Control rotation input handler
- AI leash behavior for inactive spirits
- Reform action: despawn spirits, recreate original, restore state
- Death check: all spirits dead → original entity dies

## Open Questions

- Can spirits be CC'd independently (stun one spirit while controlling another)?
- Can allies heal/buff individual spirits?
- Can enemies tell which spirit is player-controlled vs AI-controlled?
- If a spirit is cocooned (SK-58), can the player swap to another spirit?
- Do spirits inherit the caster's buffs/debuffs, or start clean?
- Can spirits enter a bunker (SK-60)?
- How do spirits interact with SK-04 Tether — if the original entity was tethered, which spirit inherits the tether?
- Does reform trigger SK-32 Minefield at the reform position?
- Can the player reform early if only one spirit remains (forced reform)?
- Performance: 3 entities instead of 1, each with their own AI tick, ability set, and potential cross-boundary concerns
