# SK-34: Charge

## Designer Intent

My character lowers their shoulder and charges forward in a straight line at high speed. If I collide with an enemy during the charge, they are pinned to me and carried along. The charge ends when I hit a wall — the pinned enemy takes massive impact damage from being slammed into the wall. If no wall is hit, the charge ends after a maximum distance or duration.

## Primitive Composition

P-07 (Entity-as-Kinematic-Volume) → P-02 (Forced Displacement)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Charge direction (from requested aim direction or facing direction)

## Observable Behavior

1. Cast — caster begins charging in the specified direction at high speed
2. Caster cannot steer during the charge (locked direction, no turning)
3. Caster is unstoppable during the charge (immune to CC? or reduced CC? Design choice)
4. If caster collides with an enemy entity: enemy is "pinned" — attached to the caster's position and carried along
5. Only the first enemy hit is pinned (subsequent enemies are knocked aside for minor damage)
6. If caster hits a wall with a pinned enemy: charge ends, pinned enemy takes X impact damage + Y wall-slam bonus damage
7. If caster hits a wall with no pinned enemy: charge ends, caster takes a brief self-stun (recovery frames)
8. If no wall is hit: charge ends after max distance or max duration (e.g., 3 seconds)
9. On charge end: pinned enemy is released at the caster's current position
10. Visual: dust trail, shoulder-down running animation, wall impact crater

## Engine Primitives Required

Charge is the canonical `kinematic_sweep` + `capture_first` pattern.

The compiler lowers it as one `kinematic_sweep` on the charging entity with:

1. `mode = toward_position`
2. bounded `duration_ticks`
3. authored `collision_radius`
4. `hit_filter = enemy_alive`
5. `on_entity_hit = capture_first`
6. `capture.carry_offset_distance` for the pinned target
7. `on_hit_effects` for the first pin and any later incidental hits
8. `world_impact_effects` for wall-slam damage / self-stun
9. optional `self_cc_immunity_during_cast` if the design wants the charge to be push-immune or
   full-super-armor while active

The important runtime rule is that the moving entity remains the sole authoritative actor. The
first admitted hit installs a transient `P-06` attachment from the captured target to the charger;
the pinned enemy is carried by ordinary attached kinematics, not by shared authority or a bespoke
"pin state." Subsequent enemies can still receive authored `on_hit_effects`, but only the first
admitted target is captured.

World collision is already a first-class sweep outcome. `world_impact_effects` fires when the
sweep stops on static geometry, which is the canonical place to apply wall-slam damage to the
captured target and a recovery/self-stun effect to the charger.

## Cross-Boundary Concerns

Charge uses the ordinary `P-07` / `P-06` handoff model.

1. If the charger crosses a boundary before any capture, the sweep state transfers with the moving
   entity and the destination owner continues the charge.
2. If a target has already been captured, the carried entity follows through the ordinary
   co-located attached-kinematics handoff path. The compiler docs already define this as temporary
   attachment, not as a second authority owner.
3. Multiple boundary crossings during one charge are just repeated handoffs of the same bounded
   sweep state; there is no special two-entity atomic teleport rule beyond the existing attached
   motion contract.

## Compiler Requirements

Designer specifies:

- charge destination/direction
- charge duration or max path length
- collision radius
- first-hit capture behavior
- incidental hit payload for non-captured targets
- wall-impact payloads
- optional self-CC immunity while the charge is active

Compiler emits:

- one `kinematic_sweep` with `capture_first`
- one `SweepCaptureBlock` for the carried target
- ordinary `on_hit_effects`, `world_impact_effects`, and `on_complete_effects`
- optional cast-time CC-immunity metadata when the charge should be unstoppable

Compiler validates:

1. the sweep is bounded (`duration_ticks > 0`)
2. capture is only authored with `on_entity_hit = capture_first`
3. world-impact consequences live in `world_impact_effects`, not in bespoke collision code
4. any unstoppable behavior is authored explicitly through the existing self-immunity surface

## Resolved Interaction Notes

- Charge itself does not imply free implicit CC immunity. If the design wants the move to be
  unstoppable, it authors that through `self_cc_immunity_during_cast`.
- Root or other movement-preventing states stop the charge from being admitted unless the charge's
  authored immunity/profile overrides them.
- The pinned target is carried by temporary attachment, so release conditions follow the capture
  block and ordinary attached-kinematics cleanup rather than a bespoke cleanse-only rule.
- Static blocking geometry, including authored terrain walls, counts as world impact for the sweep
  and therefore drives `world_impact_effects`.
- The charge path is still ordinary world space. Environmental hazards or zones along the route are
  resolved by the existing targeting/damage contracts; the sweep does not create a separate physics
  world.
