# SK-60: Bunker

## Designer Intent

I deploy a bunker at a target position. Allies can right-click the bunker to enter it. While inside, they are untargetable and protected, but they can shoot out through firing ports. The bunker has HP and can be destroyed. When destroyed (or expired), all occupants are ejected.

## Primitive Composition

P-32 (Actor Spawning) → P-58 (Container/Vehicle Logic) → P-06 (Attached Kinematics)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted)
- Allies interact with the bunker to enter/exit

## Observable Behavior

1. Bunker is placed at target position (has HP, is destructible, blocks pathing)
2. Allies within interact range can enter the bunker (up to 4 occupants)
3. While inside: occupants are untargetable and take no direct damage
4. While inside: occupants can use their auto-attacks through firing ports (reduced range)
5. While inside: occupants cannot move or use most abilities (only basic attacks)
6. Occupants can exit the bunker voluntarily at any time
7. Bunker has a duration (10 seconds) or HP pool — whichever runs out first
8. When bunker is destroyed or expires: all occupants are ejected at the bunker's position
9. Damage dealt to the bunker is split across its HP pool — occupants take no damage
10. Visual: military bunker structure, visible firing ports, explosion on destruction

## Engine Primitives Required

Bunker is now a canonical stationary `attached_visible` container shell.

The recommended lowering is:

1. one `spawn_actor` bunker shell at the ground-targeted position
2. one bunker archetype with:
   - HP and ordinary enemy targetability
   - `container_profile = {`
     `max_capacity = 4,`
     `entry_range = ... ,`
     `allowed_filter = ally_alive,`
     `occupant_storage_mode = attached_visible,`
     `occupant_can_be_targeted = false,`
     `occupant_cast_policy = basic_attacks_only,`
     `allow_manual_exit = true,`
     `eject_on_removed = true`
     `}`
   - pathing / projectile collision authored like an ordinary destructible structure

This uses the canonical bunker/vehicle branch of `P-58`:

- occupants remain spatially attached to the bunker through the `attached_visible` container mode
- occupants are not directly targetable while inside
- occupants may still basic-attack, but cannot use arbitrary abilities because
  `occupant_cast_policy = basic_attacks_only`
- bunker destruction or expiry force-ejects all occupants automatically through `eject_on_removed`

So the sketch does not need a separate damage-redirection subsystem. The bunker shell simply takes
the damage because it is the targetable body; the occupants are protected by container policy.

## Cross-Boundary Concerns

Bunker follows the ordinary stationary-container authority model.

1. The bunker shell is a stationary spawned actor with one authoritative owner based on its current
   position.
2. If an ally enters from another Arbiter, `enter_container` commits on the bunker shell's current
   owner. The occupant then follows the bunker through the canonical `attached_visible` container
   path rather than remaining independently authoritative elsewhere.
3. Occupant auto-attacks still originate from the bunker shell's current position and use the
   occupant's own combat path. Remote/Ghost targets are handled through ordinary hostile relays.
4. If the bunker is near a seam, the shell's pathing / projectile collision is mirrored through the
   same boundary-obstacle / Ghost admission model used by other targetable structures.
5. If the bunker is destroyed or expires near a seam, the eject happens on the bunker shell's owner
   at the bunker position, and any newly ejected occupant that belongs in a neighbor region then
   follows ordinary post-eject handoff rules.

## Compiler Requirements

Designer specifies:

- bunker shell position / lifetime / HP
- max occupants
- ally-only entry filter
- entry range
- occupant cast policy
- structure collision / pathing policy

Compiler emits:

- one bunker shell spawned actor
- one bunker entity archetype with canonical `container_profile`
- ordinary `enter_container` / `exit_container` interaction paths
- force-eject-on-removal behavior through `eject_on_removed = true`

Compiler validates:

1. `max_capacity > 0`
2. `entry_range > 0`
3. `occupant_storage_mode = attached_visible`
4. `occupant_cast_policy = basic_attacks_only`
5. the mechanic is expressed through canonical `container_profile` and container entry/exit effects,
   not a bespoke bunker-only occupant list subsystem

## Resolved Interaction Notes

- The caster may enter their own bunker because the entry filter is ally-based and includes the
  owner's team.
- Enemies cannot enter this reference bunker because the container profile's `allowed_filter` is
  `ally_alive`.
- Occupants cannot cast healing or other ordinary abilities while inside, because the cast policy is
  `basic_attacks_only`.
- Incoming damage is applied to the bunker shell only. Occupants do not share bunker damage in this
  reference.
- The bunker may be healed/repaired by allies through ordinary beneficial targeting if the bunker
  archetype leaves allied beneficial effects enabled.
- Occupants are container-attached, so outside displacement effects such as Vortex do not pull them
  out. Entry is voluntary `enter_container`; forced hostile throws do not automatically become valid
  bunker entry.
- Projectile blocking is an ordinary bunker-shell archetype choice. This reference assumes the
  shell blocks both pathing and hostile projectiles like a small destructible structure.
