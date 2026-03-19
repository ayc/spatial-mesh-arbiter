# SK-54: Entity Consumption

## Designer Intent

I devour an enemy hero, swallowing them whole. For 4 seconds, the enemy is completely removed from the game world — no position, no collision, no targeting, no interaction. They're stored inside me. I can move while they're inside. After 4 seconds, I spit them out at my current position.

## Primitive Composition

P-33 (Entity Dormancy) → P-47 (Spatial Corpse Registry)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in melee range)

## Observable Behavior

1. Cast on enemy hero at melee range
2. Enemy is swallowed — their entity is removed from the game world entirely
3. For 4 seconds: enemy has no position, cannot be targeted, cannot act, takes no damage, is invisible
4. The caster can move freely while carrying the consumed entity
5. The caster takes a movement speed penalty while carrying (e.g., -20%)
6. After 4 seconds: enemy is spit out at the caster's current position
7. The spit-out enemy is briefly stunned (0.5s)
8. The caster can optionally reactivate early to spit out sooner
9. Visual: gulp animation, caster's model shows distended belly, spit-out with stun effect

## Engine Primitives Required

### Entity Removal From World

This goes beyond untargetable (SK-44 Burrow — entity still has a position and exists in the entity map). The consumed entity is **completely removed from the spatial world**:

- Removed from the entity map
- Removed from the spatial index (no collision, no proximity queries find it)
- No Ghost updates sent to neighbors (entity doesn't exist)
- No downstream payloads sent to the consumed entity's Edge Node (except a "you are consumed" state notification)
- Status effect timers on the consumed entity: paused? Or keep ticking while consumed?

The entity's full state must be **stored somewhere** for later restoration. Options:
- Stored on the caster's entity as an extension field (serialized SoftState + OffensiveStats blob)
- Stored in a separate "consumed entities" table on the Arbiter
- Stored as a dormant entity in the entity map with a "consumed" flag (simpler but less clean)

### Restoration

After 4 seconds (or on reactivation), the consumed entity must be re-inserted into the world:
1. Set the entity's position to the caster's current position
2. Re-insert into the entity map and spatial index
3. Resume Ghost updates to neighbors
4. Resume downstream payloads to the entity's Edge Node
5. Apply a brief stun (0.5s) to the restored entity
6. Resume all status effect timers (if they were paused)

The restored entity must have exactly the state it had when consumed (minus any timer ticking). This is essentially a save/restore of entity state.

### Interaction With Existing Systems

While consumed:
- Does the consumed entity's Edge Node show a special UI (swallowed screen)?
- Does the consumed entity's session remain active (not orphaned)?
- Do DoTs on the consumed entity tick? If yes, is the damage applied (to nothing?) or deferred?
- Does the consumed entity retain their buffs/debuffs on restoration?
- If the caster dies while carrying a consumed entity, is the entity released at the caster's death position?

## Cross-Boundary Concerns

TODO: This is extremely challenging:

1. **Consuming a Ghost:** The target might be a Ghost (owned by another Arbiter). To consume them, the caster's Arbiter must coordinate with the target's Arbiter to: remove the entity from the target's Arbiter, serialize their full state, transfer it to the caster's Arbiter. This is similar to an entity handoff but the entity doesn't go to a new Arbiter — it goes into storage on the caster.

2. **Caster moves cross-boundary while carrying:** The consumed entity's stored state transfers with the caster during handoff. When the caster is spit out, the entity materializes on the caster's current Arbiter — which might be different from where they were consumed.

3. **Restoration after boundary change:** The consumed entity was originally on Arbiter A. The caster walked to Arbiter B while carrying them. On spit-out, the entity materializes on Arbiter B. The entity's Edge Node needs to be redirected to Arbiter B. The entity's old Arbiter A needs to know the entity no longer exists there.

4. **Meta Services:** The consumed entity's session mapping points to their old Arbiter. During consumption, the mapping is stale. On restoration, the mapping must be updated to the caster's current Arbiter.

## Compiler Requirements

TODO: Designer specifies: target (enemy hero, melee range), consumption duration (4s), target state during consumption (removed from world, cannot act, takes no damage), caster penalty (movement speed -20%), restoration behavior (spit out at caster position, 0.5s stun), reactivatable (early spit-out), caster death releases consumed entity. Compiler produces:
- Consumption action: remove target from world + serialize + store on caster
- Caster debuff: movement speed penalty + carrying state flag
- Timer: 4-second duration or reactivation
- Restoration action: deserialize + re-insert at caster position + stun
- Death hook on caster: emergency restoration

This is the most complex ability in terms of entity lifecycle management. The compiler needs to express "temporarily remove an entity from existence and restore it later."

## Open Questions

- Can multiple enemies be consumed simultaneously (Gorge two heroes)?
- Can allies be consumed (for protection — swallow an ally to save them)?
- What happens if the caster is consumed BY ANOTHER consumption ability? (Russian nesting dolls?)
- Does the consumed entity accumulate death timer (if applicable in the game mode)?
- Can the consumed entity's allies still see them on the minimap?
- How does this interact with SK-04 Tether — if a tethered entity is consumed, does the tether snap?
- If the consumed entity had SK-46 Adaptation active, does the 4-second window pause or keep ticking?
- What happens to SK-06 summoned minions if their owner is consumed?
- Can the caster use abilities while carrying (other than spit-out)?
- Performance: serializing a full entity state mid-tick — is this bounded in time?
