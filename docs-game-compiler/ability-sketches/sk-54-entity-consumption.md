# SK-54: Entity Consumption

## Designer Intent

I devour an enemy and carry them inside me for a short duration. While consumed, they are removed
from the spatial world. I can move while carrying them, and later spit them out at my current
position, optionally early.

## Primitive Composition

P-58 (Container/Vehicle Logic) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Enemy target in melee range
- Optional same-key reactivation for early spit-out

## Observable Behavior

1. Cast on a valid nearby enemy to swallow them.
2. While swallowed, the target is off-world: no position in the spatial index, no targeting, no
   collision, no manual action, and no downstream world payloads.
3. The caster remains in the world and can move while carrying the swallowed target.
4. In this reference, the caster suffers a movement-speed penalty while carrying.
5. After 4 seconds, the target is ejected at the caster's current position and is briefly stunned.
6. The caster may reactivate early to spit the target out sooner.
7. If the caster is removed while carrying the target, the target is force-ejected automatically.

## Engine Primitives Required

The canonical path is `off_world_stored` containment, not bespoke entity serialization.

1. The devouring archetype exposes a `container_profile` with:
   - `max_capacity = 1`
   - `allowed_filter = enemy_alive`
   - `occupant_storage_mode = off_world_stored`
   - `occupant_can_be_targeted = false`
   - `occupant_cast_policy = none`
   - `allow_manual_exit = false`
   - `eject_on_removed = true`
2. The consume ability enters the target into that container with `eject_after_ticks = 240`.
3. The caster gains a carrying debuff using ordinary `stat_modifiers` for the movement-speed penalty.
4. Forced expiry or manual `exit_container` ejects the occupant at `container_position` and applies
   a brief stun through ordinary `on_forced_eject_effects` / `on_exit_effects`.
5. A runtime-state `bookmark(entity_ref)` stores the swallowed target so the same public ability can
   redirect to an early-spit `ActivationModes` variant while the container is occupied.

## Cross-Boundary Concerns

The reference version stays on the safe side of the current containment contract:

1. Consumption requires the target to be authoritative locally at admission time; the reference does
   not try to devour Ghost targets.
2. Once the target is inside the container, the preserved off-world occupant state moves with the
   container owner through ordinary handoff exactly like other container-owned state.
3. If the caster crosses an Arbiter boundary while carrying the target, the occupant remains inside
   the container and later ejects on the caster's then-current Arbiter.
4. Because `eject_on_removed = true`, caster death/removal still releases the target before any
   later container-owner follow-up effects run.

## Compiler Requirements

Designer specifies:

- melee consume range
- carry duration
- carry speed penalty
- optional early-reactivation behavior
- spit-out stun duration

Compiler emits:

- a carrier `container_profile` using `occupant_storage_mode = off_world_stored`
- one consume cast that enters the target into the caster container and stores the swallowed target
  ref in runtime state
- one carrying debuff on the caster
- one hidden same-key reactivation variant that exits the stored occupant early
- one forced-expiry eject with a brief stun payload on the ejected target

Compiler validates:

1. the container profile satisfies `off_world_stored` rules
   (`occupant_can_be_targeted = false`, `occupant_cast_policy = none`)
2. the target is local/non-Ghost at consume admission time
3. the stored swallowed-target runtime state exists and is an `entity_ref` bookmark
4. ejection effects are authored through ordinary exit/eject payloads, not a bespoke restore path

## Resolved Interaction Notes

- The swallowed target is not dead and does not create a corpse record. This is containment, not a
  death/lifecycle transition.
- Because the target is off-world stored, allies cannot target or rally them while they are inside
  the carrier.
- The carried target does not get a manual "leave container" action in this reference.
- The reference version allows the caster to continue using ordinary abilities while carrying unless
  the game separately authors more restrictions.
- Tethers and other live spatial relations break when the target leaves the spatial world unless the
  specific mechanic has its own persisted non-spatial representation.
