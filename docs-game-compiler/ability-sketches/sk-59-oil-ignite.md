# SK-59: Oil Ignite

## Designer Intent

I drop an oil spill on the ground that slows enemies who walk through it. I can reactivate the ability to ignite the oil — transforming the zone from a slow field into a fire zone that deals heavy damage. The fire burns for a duration then the zone disappears.

## Primitive Composition

P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-64 (Combo Field × Finisher Matrix)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)
- Reactivation input (same ability key, while oil zone is active)

## Observable Behavior

1. Cast — oil zone appears at target position (circular, fixed radius)
2. **Oil phase:** Enemies inside are slowed by 40%. No damage. Oil persists until ignited or expired (8 seconds).
3. Reactivate — oil ignites, transforming into fire
4. **Fire phase:** Enemies inside take X fire damage per second. Slow is removed (fire doesn't slow). Fire lasts 4 seconds.
5. If not reactivated: oil evaporates after 8 seconds with no fire phase
6. Oil can also be ignited by any fire ability passing through it (SK-30 Trail of Fire, fire projectiles)
7. Visual: dark oil pool → reactivation → blazing fire

## Engine Primitives Required

Oil Ignite is now a canonical combination of one ordinary zone actor, one reactivation link, and one
`combo_matrix` replacement result. It does not require a bespoke per-zone state machine in engine
code.

### Canonical Oil Phase

The initial cast lowers to one stationary `zone` with:

- `shape = circle`
- authored `radius`
- `duration_ticks = 480`
- `enter_effects` / `pulse_effects` applying the slow
- `combo_field_type = oil`
- `output_binding = oil_zone`

The cast also stores that live zone actor in runtime state so same-key reactivation can still find
the exact oil field while it exists.

### Canonical Fire Transition

There are two supported ignition paths:

1. **Same-key reactivation:** the hidden reactivation variant reads the stored oil-zone actor,
   captures its current position, `despawn_entity`s it, and then spawns a replacement fire `zone`
   at that same position.
2. **External ignition:** a qualifying fire finisher that has opted into one of the supported
   `combo_finisher` tags (`projectile`, `blast`, `whirl`, or `leap`) triggers the `combo_matrix`
   entry for `(oil, finisher)`. That combo result uses the canonical combo-field callback context:
   `combo_field_entity`, `combo_field_owner`, `combo_field_position`, and `finisher_position`.

For this sketch, the external combo result is:

- `despawn_entity(target = combo_field_entity, reason = "oil_ignite")`
- spawn a replacement fire `zone` at `combo_field_position`
- set `owner = combo_field_owner` so the burning field keeps the original oil owner's attribution

This means allies, enemies, and self-casts can all ignite the oil if they are authored as
qualifying fire finishers, but the burning field still belongs to the oil owner rather than to the
igniting ability's caster.

### Fire Phase

The replacement fire field is an ordinary hostile `zone` with:

- the same footprint as the oil field
- `duration_ticks = 240`
- periodic damage pulse payloads
- no slow payloads

The transition is therefore "replace one live field actor with another," not "mutate one zone actor
through a bespoke internal enum."

## Cross-Boundary Concerns

Oil Ignite follows the canonical zone + combo-matrix authority rules.

1. The oil/fire field is a stationary zone actor owned by the Arbiter where it was created.
2. Same-key reactivation resolves on that zone actor's current authoritative owner through the stored
   zone reference, even if the caster and field are no longer co-located.
3. External ignition is detected only when the finisher and the oil field are on the same Arbiter,
   following the existing `P-64` same-Arbiter rule.
4. A projectile handed off into the field owner's Arbiter can ignite the oil there normally, because
   the handoff preserves the finisher's authored combo metadata.
5. There is no cross-Arbiter ghost-combo replay. If the finisher is only present as a Ghost relative
   to the field, no ignition occurs in the current canonical profile.

## Compiler Requirements

Designer specifies:

- oil-zone radius, slow percentage, and 8-second oil duration
- fire-zone damage payload and 4-second burn duration
- one live-zone reactivation rule
- which authored fire abilities opt into the canonical `combo_finisher` tags and therefore count as
  qualifying external igniters

Compiler emits:

- one ordinary oil `zone` definition tagged `combo_field_type = oil`
- one runtime-state link storing the live oil-zone actor for same-key reactivation
- one hidden reactivation variant that replaces the stored oil zone with a fire zone
- one or more `combo_matrix` rows for `(oil, finisher)` whose effect list despawns the interacting
  oil field and spawns the replacement fire field using combo-field callback refs

Compiler validates:

1. the initial oil field and the replacement fire field are both expressible as ordinary `zone`
   effects rather than a bespoke zone-state subsystem
2. any external igniter is an authored qualifying finisher, not an untagged arbitrary ability
3. same-key reactivation stores and resolves exactly one live oil-zone actor at a time
4. combo-driven replacement uses the canonical combo callback refs plus ordinary effect sequencing
   (`despawn_entity` followed by replacement spawn)

## Resolved Interaction Notes

- This sketch assumes one live oil zone per caster for the reactivation path; a later cast replaces
  the stored prior zone rather than maintaining a multi-zone selector.
- Allies, enemies, and the caster can all ignite the oil if their ability is authored as a
  qualifying fire finisher.
- Ignition does not transfer ownership. The replacement fire zone keeps the original oil owner's
  attribution and therefore uses that owner's ordinary zone-source scaling and proc identity.
- Neither the oil phase nor the fire phase blocks projectiles by default. Projectile blocking would
  require separate injected geometry authoring, not just a zone field.
