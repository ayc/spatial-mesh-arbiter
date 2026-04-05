# SK-81: Remote Control Summon

## Designer Intent

I deploy a motorized bomb. While the bomb is active, I directly control its movement with my movement keys — my character becomes immobile. I steer the bomb around the battlefield. When I press the detonation button (or after a timeout), the bomb explodes dealing massive AoE damage. Enemies can destroy the bomb if they hit it.

## Primitive Composition

P-32 (Actor Spawning) → P-29 (Control Authority Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Movement/aim input redirected to the summon
- Detonation input (reactivation key)

## Observable Behavior

1. Activate — bomb spawns at caster's position
2. Caster becomes immobile and channeling (vulnerable, can be interrupted)
3. Movement input controls the bomb, not the caster
4. The bomb moves at fixed speed, can be steered freely
5. The bomb has HP and can be destroyed by enemies
6. Reactivate or timeout: bomb detonates, AoE damage at bomb's position
7. If the bomb is destroyed: no detonation (reduced cooldown)
8. If the caster is interrupted (stunned): bomb detonates immediately at current position
9. Visual: rolling bomb entity, caster in trance state

## Engine Primitives Required

Remote Control Summon is now the canonical "single spawned shell plus `control_projection`
callbacks" pattern.

### Canonical Controlled Bomb Shape

The recommended lowering is one `spawn_actor` shell plus a `control_projection` block:

- bomb shell archetype with HP, collision, movement speed, and hostile targetability
- `control_projection = {`
  `controller = caster,`
  `owner_body_policy = root_owner,`
  `control_scope = movement_only,`
  `on_actor_removed = release_control,`
  `on_expire = release_control,`
  `manual_trigger_effects = [aoe_damage(center = projected_actor_position, ...), despawn_entity(target = projected_actor, reason = "manual_detonate")],`
  `on_expire_effects = [aoe_damage(center = projected_actor_position, ...), despawn_entity(target = projected_actor, reason = "timeout_detonate")],`
  `on_controller_break_effects = [aoe_damage(center = projected_actor_position, ...), despawn_entity(target = projected_actor, reason = "control_break_detonate")]`
  `}`

The caster body stays rooted in-world through ordinary channel/status authoring. It is not
suspended. Steering input is redirected to the bomb through `control_projection`, and the detonation
button is the generated same-slot manual trigger exposed while that control session remains active.

### Source and Position Semantics

The callback context solves the old ambiguity directly:

- `caster` remains the summoner/controller, so detonation damage scales from the summoner's stats
- `projected_actor_position` is the bomb's current authoritative position, so the explosion happens
  where the bomb actually is
- `despawn_entity(target = projected_actor)` consumes the shell only for the authored detonation
  paths

### Enemy Destruction vs Detonation

The bomb is a normal targetable spawned actor with HP.

- If enemies destroy it, the actor is removed and control ends through `on_actor_removed`
- enemy destruction does **not** emit `manual_trigger_effects`, `on_expire_effects`, or
  `on_controller_break_effects`
- therefore destruction cleanly means "no explosion"

## Cross-Boundary Concerns

Remote Control Summon follows the ordinary single-actor control-projection boundary rules.

1. If the bomb crosses an Arbiter boundary, the bomb itself hands off normally as one authoritative
   spawned actor.
2. The control-routing overlay follows that actor through the existing Stage 1 routing rules, so the
   controller's steering input reaches the bomb's current owner without inventing a second transport.
3. The manual detonation button resolves against the bomb's current owner through the same
   control-projection path, and the callback explosion runs there using `projected_actor_position`.
4. If the controller is interrupted on another Arbiter, the routed control session breaks and
   `on_controller_break_effects` fire once on the bomb's current owner.
5. If the bomb is externally destroyed on another Arbiter, that owner applies normal actor removal,
   the control session ends, and no detonation callback is emitted.

## Compiler Requirements

Designer specifies:

- bomb shell archetype and lifetime
- rooted/channeling lockout on the summoner body
- movement-control projection from summoner to shell
- detonation payload (radius, damage, scaling)
- whether timeout and controller-break should emit the same detonation payload

Compiler emits:

- one spawned bomb shell actor
- one `control_projection` with `control_scope = movement_only`
- one temporary same-slot manual trigger action while control is active
- authored callback payloads for manual trigger, expiry, and controller-break
- ordinary actor removal cleanup for enemy destruction with no detonation callback

Compiler validates:

1. `count = 1` because `control_projection` is authored
2. `projected_actor` / `projected_actor_position` are used only inside the `control_projection`
   callback effect lists
3. the manual detonate path is authored through `manual_trigger_effects`, not by granting arbitrary
   additional ability control to the routed shell
4. enemy destruction is modeled through ordinary actor removal, not by overloading the detonation
   callbacks

## Resolved Notes

- The detonation control is a temporary same-slot/manual-trigger action that should appear in the UI
  only while the control session is active.
- Timeout and controller interruption both detonate at the bomb's current position using the
  summoner's offensive context.
- Enemy destruction ends the control session with no explosion.
- The bomb remains an ordinary spawned actor for terrain collision, zone interaction, portal entry,
  and handoff; there is no special "drone physics" subsystem for this sketch.
