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

Temporal Trap is now a canonical hostile bookmark plus delayed `restore_from_state` reference.

The recommended lowering is:

1. on cast, write the target's current position into one `bookmark(position)` runtime state with
   topology-epoch capture enabled
2. apply one negative `temporal_trap` status to the target for 180 ticks
3. that status authors:
   - `cc_category = displacement`
   - optional countdown/marker presentation
   - `on_expire_effects = [restore_from_state(target = target, state_id = temporal_trap_bookmark, apply_position = true, position_validation = nearest_walkable)]`

This keeps the mechanic inside existing canonical surfaces:

- the stored location is a normal runtime bookmark
- the delay is just the status duration / expiry hook
- the return snap is ordinary `restore_from_state` / `P-01` relocation using the current topology

The hostile delayed return is therefore a negative displacement-class status, not a bespoke timer
subsystem.

## Cross-Boundary Concerns

Temporal Trap follows the canonical absolute-bookmark relocation rule.

1. `bookmark(position)` stores absolute world coordinates plus topology epoch when authored.
2. When the delayed `restore_from_state` fires, the target's CURRENT owner resolves the stored
   coordinate under the CURRENT topology.
3. If the stored point is now in another Arbiter's region, the snap follows the ordinary
   destination-based teleport / handoff rule.
4. `position_validation = nearest_walkable` gives the canonical answer when later geometry makes the
   exact stored coordinate invalid.

## Compiler Requirements

Designer specifies:

- target range
- delay duration
- whether the debuff is cleansable
- countdown / marker presentation

Compiler emits:

- one `bookmark(position)` runtime state
- one hostile `write_state` on cast
- one negative delayed-return status
- one expiry `restore_from_state` snap

Compiler validates:

1. the referenced runtime state exists and is `bookmark(position)`
2. the delayed return is expressed through a negative status plus `restore_from_state`, not a
   bespoke hostile teleport timer
3. the snap uses one canonical `position_validation` rule

## Resolved Interaction Notes

- This reference is cleansable: removing the negative status before expiry prevents the delayed
  return because the expiry hook never fires.
- Because the delayed return lives on a negative displacement-class status, displacement-category
  status-immunity effects can block the trap at admission time.
- The countdown is not shortened by status resistance in this reference unless the designer opts
  into that by authoring the status with `duration_scaling = status_resistance`.
- The delayed snap itself deals no damage. It is ordinary hostile repositioning only.
- If the target later teleports or crosses multiple Arbiters before expiry, the stored absolute
  bookmark remains the same; only the current owner/topology used to execute the return changes.
