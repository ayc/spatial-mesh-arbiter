# SK-43: Drag

## Designer Intent

I shoot my tongue out in a line. If it hits the first enemy in its path, I latch on and drag them toward me over 1.75 seconds. During the drag, I can move — and the enemy is pulled toward wherever I currently am. If I miss, the ability goes on a short cooldown. If I hit, full cooldown after the drag completes.

## Primitive Composition

P-02 (Forced Displacement) → P-34 (Persistent Linkage)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (skillshot — from requested aim direction)

## Observable Behavior

1. Tongue launches as a line projectile in the cast direction
2. Tongue travels at high speed — hits the FIRST enemy entity in its path (skillshot)
3. If no enemy is hit before max range: tongue retracts, short cooldown (e.g., 6s)
4. If enemy is hit: latch on — enemy is dragged toward the caster over 1.75 seconds
5. During the drag: the caster CAN move. The drag destination moves with the caster.
6. During the drag: the target cannot act (hard CC — functionally a stun)
7. The target is pulled along a direct line toward the caster's current position each tick
8. At the end of the drag: target is released at their current position, near the caster
9. Visual: tongue extending out, latching, enemy being reeled in

## Engine Primitives Required

Drag is now a canonical first-hit projectile plus cleansable drag-debuff pattern.

The recommended lowering is:

1. one tongue projectile `spawn_actor` with:
   - authored speed / max range
   - `detonation_policy = { entity_impact = detonate, world_impact = stop, expiry = despawn }`
   - no homing and no pierce
2. on the first admitted enemy impact:
   - apply one cleansable `tongue_latch` link between caster and struck target for the drag window
   - apply one negative `dragged` status to the target for 105 ticks
   - use the bounded Lua helper `set_cooldown` to move the caster from the short miss cooldown to
     the full hit cooldown
3. `dragged` status authors:
   - capability suppression for voluntary movement / attacks / casts
   - `periodic_effects = {`
     `interval_ticks = 1,`
     `effects = [displacement(target = target, destination = caster_position, max_distance = pull_step)]`
     `}`
   - `duration_scaling = fixed`
   - `is_cleansable = true`
4. `tongue_latch` link authors:
   - `duration_ticks = 105`
   - `break_on_source_removed = true`
   - `break_on_target_removed = true`
   - optional `origin_override = { observer_anchor = true }` if the design wants the tongue visuals
     and observer payloads anchored to the current partner pair

This keeps Drag inside existing canonical surfaces:

- the tongue is just a first-hit projectile
- the reel-in is a status-owned per-tick `displacement` toward `caster_position`
- the latch itself is a normal cleansable `link`
- miss-versus-hit cooldown branching uses the existing bounded `set_cooldown` fallback rather than
  inventing a dedicated dual-cooldown primitive

## Cross-Boundary Concerns

Drag follows the canonical target-owner pull model.

1. The projectile's first-hit admission follows the ordinary hostile projectile contract. If the
   tongue hits a Ghost/remote target, the impact payload is relayed to the target's owner before the
   latch/status commit.
2. Once `dragged` is active, the target's CURRENT owner runs the per-tick `displacement` locally.
   `caster_position` resolves from the source entity's current local-or-Ghost pose, so the pull
   destination keeps following the dragger even when the dragger is remote.
3. If the dragged target crosses a boundary mid-reel, the `dragged` status and `tongue_latch`
   binding survive handoff as ordinary SoftState. The new owner continues the same per-tick pull.
4. If the dragger crosses a boundary first, the target owner keeps reading the dragger through the
   same current local-or-Ghost partner-pose rule used by `link` break-distance and origin-anchor
   consumers.
5. If either endpoint is removed, the latch is cleaned up through the ordinary binding-removal
   rules and the drag debuff expires or is cleansed independently on the target's owner.

## Compiler Requirements

Designer specifies:

- skillshot projectile speed / range
- drag duration and pull step per tick
- full cooldown on hit and short cooldown on miss
- whether the latch is cleansable
- whether observer payloads anchor to the latch pair

Compiler emits:

- one first-hit projectile spawn
- one cleansable `tongue_latch` binding on hit
- one negative `dragged` status with per-tick `displacement(target = target, destination = caster_position)`
- one hit-only `set_cooldown` mutation to replace the short miss cooldown with the full cooldown

Compiler validates:

1. the projectile uses first-hit collision semantics (`entity_impact = detonate`, no pierce)
2. `duration_ticks > 0`
3. `pull_step > 0`
4. the drag movement is expressed through canonical per-tick `displacement` toward
   `caster_position`, not through a bespoke per-ability tether physics loop
5. the hit-only cooldown branch stays inside the bounded `set_cooldown` helper rather than a hidden
   second public skill

## Resolved Interaction Notes

- The drag uses ordinary movement resolution, so blocking geometry / pathing clamps still apply. The
  target is reeled through legal committed movement, not tunneled through walls.
- The target remains targetable during the drag unless some other status changes that, so zones and
  other overlapping effects such as Blizzard continue to affect it normally.
- Purify or other ordinary cleanse effects can break the drag by removing the cleansable `dragged`
  status and the cleansable `tongue_latch` binding.
- This reference uses `duration_scaling = fixed`, so Tenacity / status-effect-resistance does not
  shorten the reel-in window.
- If the dragger is stunned after a successful latch, the reel-in still continues in this reference
  because the target's pull loop reads `caster_position`; it does not require the dragger to keep
  channeling or recasting.
- The projectile may hit any entity admitted by its authored hostile filter, including minions and
  summons if the designer leaves the targeting filter broad enough.
