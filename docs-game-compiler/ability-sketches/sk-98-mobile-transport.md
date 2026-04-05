# SK-98: Mobile Transport

## Designer Intent

I summon a dropship at my position. Allies can enter the dropship (up to 4 passengers). Once loaded, I select a destination on the map and the dropship flies there. On arrival, all passengers exit at the destination. The dropship can be shot down during flight — if destroyed, passengers crash-land at the current position.

## Primitive Composition

P-32 (Actor Spawning) → P-58 (Container/Vehicle Logic) → P-06 (Attached Kinematics)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (summons the transport)
- Allies interact to enter
- Caster selects destination (ground-targeted, potentially global range)

## Observable Behavior

1. Summon dropship at caster's position — dropship entity appears
2. Allies walk near the dropship and interact to enter (like SK-60 Bunker entry)
3. Up to 4 allies can enter (+ caster = 5 total occupants)
4. Caster selects a destination on the map
5. Dropship lifts off and flies to the destination (travel time proportional to distance)
6. During flight: dropship is visible and targetable. It has HP.
7. During flight: occupants are untargetable and cannot act
8. On arrival: dropship lands, all occupants exit at the destination position
9. If dropship is destroyed mid-flight: all occupants are ejected at the crash position with a brief stun
10. Visual: military dropship, flight path line on minimap, landing effect

## Engine Primitives Required

Mobile Transport is now a canonical spawned shell + container + late-bound transit reference.

The recommended lowering is:

1. the summon cast spawns one dropship shell at `caster_position` and writes its actor ref into a
   runtime bookmark state for later launch
2. the dropship archetype carries:
   - authored HP and ordinary enemy targetability
   - optional allied-beneficial targetability if the design wants in-flight repairs
   - `container_profile = {`
     `max_capacity = 5,`
     `entry_range = ... ,`
     `allowed_filter = ally_alive,`
     `occupant_storage_mode = attached_visible,`
     `occupant_can_be_targeted = false,`
     `occupant_cast_policy = none,`
     `allow_manual_exit = false,`
     `eject_on_removed = true`
     `}`
3. allies (including the caster) enter through ordinary `enter_container` interactions while the
   shell is still grounded
4. the launch cast targets one ground position and emits:
   - `start_actor_transit(target = { state_entity: dropship_shell_state },`
     `destination = cursor_position,`
     `speed = ... ,`
     `arrival_radius = ... ,`
     `on_arrival_effects = [`
     `exit_container(container = transit_actor, mode = all_occupants, exit_position = container_position),`
     `despawn_entity(target = transit_actor)`
     `])`
5. the dropship shell's ordinary `on_death` cleanup emits:
   - `exit_container(container = caster, mode = all_occupants, exit_position = container_position,`
     `on_exit_effects = [apply_cc(target = target, cc_type = stun, category = hard_disable, duration_ticks = 30)])`

This keeps the mechanic inside the canonical compiler surface:

- `spawn_actor` provides the transport shell
- `P-58` / `container_profile` provide loading, occupancy, and occupant protection
- `start_actor_transit` provides the later "fly this already-live shell to the chosen point"
  contract
- ordinary `exit_container` and `on_death` hooks provide landing and crash handling

The transport does not need a bespoke vehicle state machine outside those bounded surfaces.

## Cross-Boundary Concerns

Mobile Transport follows the ordinary moving-shell boundary model.

1. The dropship shell is one authoritative spawned actor. `start_actor_transit` installs one
   destination/speed record on that shell; each shell owner continues the same transit record after
   handoff.
2. `attached_visible` occupants ride with the shell through `P-58`. They do not perform
   independent handoffs while contained; they follow the shell's current owner and position.
3. The launch destination is snapshotted to one absolute world position when the launch cast
   commits. Later shell owners do not recompute from fresh cursor input.
4. If the shell reaches a destination on another Arbiter, ordinary repeated shell handoff brings it
   there. `on_arrival_effects` then execute on the shell's current owner, ejecting occupants at the
   landed shell position before the shell despawns.
5. If the shell is destroyed mid-flight, its current owner runs the shell's ordinary `on_death`
   cleanup locally, ejects occupants at the crash position, and applies the crash stun there. Any
   occupant whose crash position belongs in a neighboring region then follows ordinary post-eject
   handoff rules.
6. Passenger sessions are not in a special out-of-band transport state. While contained, they follow
   the shell's current authoritative owner; on landing or crash they simply resume ordinary local
   control from the ejection position.

## Compiler Requirements

Designer specifies:

- dropship shell archetype / HP / lifetime
- occupant cap and entry range
- launch speed and arrival radius
- global-range destination-targeted launch ability
- crash stun payload
- whether allies may repair the shell in flight

Compiler emits:

- one summon ability that spawns the dropship shell and stores its actor ref in runtime state
- one shell archetype with canonical `container_profile`
- ordinary `enter_container` loading interactions
- one launch ability that uses `start_actor_transit` against the stored shell ref
- one arrival callback that ejects occupants and despawns the shell
- one shell `on_death` cleanup path that ejects occupants and applies crash stun

Compiler validates:

1. `max_capacity > 0`
2. `occupant_storage_mode = attached_visible`
3. `occupant_cast_policy = none`
4. `allow_manual_exit = false` for this reference transport
5. `speed > 0` and `arrival_radius > 0`
6. the launch ability uses canonical `start_actor_transit` against a live stored actor ref rather
   than inventing a bespoke transport phase machine

## Resolved Interaction Notes

- The shell remains a normal targetable body during flight. Enemies counter this mechanic by
  damaging or destroying the shell, not by targeting passengers directly.
- In this reference, passengers cannot act and cannot manually exit during flight because the
  container profile uses `occupant_cast_policy = none` and `allow_manual_exit = false`.
- If the shell archetype allows allied beneficial targeting, allies may repair the dropship during
  flight through ordinary beneficial effects. If not, the shell is simply not healable.
- This reference does not expose a manual early-landing / cancel action. The shell either reaches
  the authored destination or is destroyed first.
- The flight-path indicator is presentation-only. Enemies see the live shell if normal observer
  rules reveal it, but they are not entitled to a special destination preview by the transport
  contract itself.
- The shell counts as one entity and the contained passengers still count as their own entities for
  density / split-threshold accounting, so a full dropship is `N+1`, not one compressed object.
- The shell uses its own archetype collision policy while moving. This reference treats it as a
  flying shell, so ground obstacles like `SK-03 Terrain Wall` do not cancel the transit path.
- If the shell lands into an armed hostile area such as `SK-32 Minefield`, those interactions are
  evaluated only after the passengers are ejected and become ordinary active entities again.
