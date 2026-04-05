# SK-41: Detonation Arrow

## Designer Intent

I fire a projectile in a line. The projectile keeps flying until I reactivate the ability (or it reaches max range). On detonation, it explodes dealing AoE damage and silencing all enemies in the blast radius. I control WHERE it detonates by choosing WHEN to press the button.

## Primitive Composition

P-32 (Actor Spawning) → P-09 (Shape Overlap Query) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (from requested aim direction)
- Detonation input (reactivation of same ability key, while projectile is in flight)

## Observable Behavior

1. Cast — projectile launches in the specified direction
2. Projectile travels at constant speed in a straight line
3. Projectile passes through all entities (does not detonate on contact)
4. While in flight: ability icon changes to "Detonate"
5. If reactivated: projectile explodes at its current position — AoE damage + 2.5s silence to all enemies in blast radius
6. If not reactivated: projectile detonates automatically at max range
7. Caster can move and act normally while the projectile is in flight
8. Visual: glowing arrow with a trail, expanding explosion on detonation

## Engine Primitives Required

Detonation Arrow is now a canonical manual-trigger projectile pattern built from one live projectile
reference plus one same-key detonate variant.

The recommended lowering is:

1. Define one runtime state:
   - `state_id = detonation_arrow_projectile_ref`
   - `kind = bookmark(entity_ref)`
   - `expires_after_ticks = projectile_lifetime_ticks`
   - `clear_on_owner_death = true`
2. Base cast variant:
   - `spawn_actor {`
     `count = 1,`
     `output_binding = detonation_arrow_projectile,`
     `projectile = {`
       `speed = ... ,`
       `detonation_policy = {`
         `manual_trigger = true,`
         `entity_impact = ignore,`
         `world_impact = ignore,`
         `expiry = detonate`
       `}`
     `}`
   - `write_state(state_id = detonation_arrow_projectile_ref, capture = entity_ref, entity = { binding: detonation_arrow_projectile })`
3. The projectile's authored detonation payload is one hostile AoE centered on its CURRENT position:
   - ordinary AoE damage
   - ordinary `apply_cc(cc_type = silence)` to admitted hostile targets in the blast
4. Reactivation variant:
   - `when = { state_present: detonation_arrow_projectile_ref }`
   - resolve the stored projectile's authored `manual_trigger`
   - `clear_state(state_id = detonation_arrow_projectile_ref)`

This keeps the mechanic inside existing canonical surfaces:

- the projectile owns its own detonation behavior through `detonation_policy`
- the live actor reference is stored as `bookmark(entity_ref)` runtime state
- same-key reactivation uses ordinary `ActivationModes` rather than a second public ability ID

## Cross-Boundary Concerns

Detonation Arrow follows the ordinary live-projectile routing model.

1. The projectile hands off normally when it crosses an Arbiter boundary.
2. The stored runtime state keeps only the stable projectile actor ID; the manual detonate action
   resolves against the projectile's current authoritative owner at the moment of reactivation.
3. The actual explosion runs on that projectile owner using the projectile's CURRENT position. Any
   remote/Ghost victims then follow the ordinary target-owner damage / CC relay path.
4. Natural expiry detonation and manual detonation use the same live projectile state, so handoff
   does not create a duplicate or source-side detonation race.
5. If the projectile is already gone when reactivation would occur, the stored state is cleared and
   the same-slot detonate variant disappears cleanly.

## Compiler Requirements

Designer specifies:

- projectile speed and lifetime / max range
- blast radius and hostile targeting filter
- explosion damage payload
- silence duration
- observer presentation

Compiler emits:

- one single-spawn projectile actor with `detonation_policy.manual_trigger = true`
- one `bookmark(entity_ref)` runtime state that stores the live projectile
- one hidden same-key detonate variant gated on `state_present`
- one projectile detonation payload that resolves AoE damage plus canonical `apply_cc(cc_type = silence)`

Compiler validates:

1. `count = 1` because this reference stores one live projectile ID for reactivation
2. the referenced runtime state exists and is `bookmark(entity_ref)`
3. `expiry = detonate` for the intended max-range fallback
4. the projectile's pass-through policy remains explicit through `entity_impact = ignore` and
   `world_impact = ignore`; the compiler/runtime do not silently re-enable contact detonation

## Resolved Interaction Notes

- This reference supports one active Detonation Arrow at a time. While the projectile is in flight,
  the same public slot is redirected to the detonate variant instead of allowing a second launch.
- The projectile ignores both entity and world collision until manual or expiry detonation. It is a
  timing-controlled explosive, not a contact-trigger missile in this reference.
- The silence from the blast is canonical `apply_cc(cc_type = silence)` and therefore interrupts
  active casts and channels normally.
- Explosion damage uses the projectile's carried offensive context baked at launch; each struck
  target still resolves mitigation on its own authoritative owner at detonation time.
- If the caster dies, reactivation disappears with the cleared state. The projectile itself then
  follows its own authored lifetime / expiry behavior unless some other rule removes it first.
