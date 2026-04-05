# SK-08: Aura

## Designer Intent

Passive ability: enemies within a radius around my character take X damage per second and have
their movement speed reduced by 20%. The effect applies as long as they are within range and ends
when they leave. No activation is required; it is always on while the passive is equipped/enabled.

## Primitive Composition

P-06 (Attached Kinematics) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer) → P-16 (Stat
Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (passive; no explicit activation)
- No target required

## Observable Behavior

1. The aura follows the caster continuously.
2. Enemies inside the radius take damage once per second.
3. Enemies inside the radius also carry a 20% movement slow while pulses keep refreshing it.
4. Enemies leaving the radius stop taking damage immediately and keep only their last slow instance
   until it expires naturally.
5. No cast time, cooldown, or resource cost is involved in the passive reference.
6. The aura may have an observer-visible ground ring or similar passive presentation.

## Engine Primitives Required

Aura is the canonical attached-zone passive pattern.

The recommended lowering is:

1. represent the trait as one passive/no-target output owned by the caster's loadout
2. that passive spawns one `zone` actor with:
   - `position = caster_position`
   - `shape = circle`
   - authored `radius`
   - `pulse_interval_ticks = 60`
   - `pulse_effects = [damage, apply_debuff(aura_slow)]`
   - `mobility = { mode = attached_entity, target = caster }`
3. author `aura_slow` as one ordinary negative status with:
   - movement-speed `stat_modifier`
   - `cc_category = soft_disable`
   - `duration_scaling = status_resistance`
   - `max_stacks = 1`

This keeps the mechanic inside existing surfaces:

- the aura is one attached zone actor, not a bespoke "every tick scan around me" subsystem
- damage pulses are ordinary `pulse_effects`
- the slow is an ordinary negative status re-applied each pulse
- explicit leave cleanup is unnecessary because the slow simply expires after the last pulse that
  touched the target

## Cross-Boundary Concerns

Aura follows the same zone-owner relay contract as other pulse zones, with the only difference that
the zone actor is attached to the caster.

1. The aura zone remains authoritative on the caster's current owner and samples the caster's
   committed position each tick through `mobility.mode = attached_entity`.
2. Each pulse runs a hostile overlap query from the zone's CURRENT committed position.
3. Local targets are resolved locally; Ghost/remote targets use the normal target-owner hostile
   relay path for damage and debuff admission.
4. If the caster moves along a seam or hands off, the aura zone and its pulse state move with the
   caster through the ordinary spawned-zone handoff story.
5. Because this reference uses only `pulse_effects`, not `enter_effects` or `leave_effects`, it
   does not require a persistent occupant set.

## Compiler Requirements

Designer specifies:

- passive/no-target ownership
- aura radius
- pulse cadence
- hostile filter
- damage payload per pulse
- slow payload per pulse
- whether the aura ends on source removal

Compiler emits:

- one attached `zone`
- one compiled negative slow status
- pulse payloads of `[damage, apply_debuff(aura_slow)]`

Compiler validates:

1. `radius > 0`
2. `pulse_interval_ticks > 0`
3. the aura uses `mobility.mode = attached_entity`, not a bespoke passive tick hook
4. the slow is expressed as a negative status with bounded stacks, not as direct movement mutation

## Resolved Interaction Notes

- This reference pulses once per second. It does not perform a full 60 Hz damage application.
- Stealthed/invisible enemies are affected only if the authored hostile filter admits them. The
  aura does not implicitly reveal or ignore stealth.
- Mute/passive suppression can disable the aura because the passive output is tied to the carrier's
  passive loadout state rather than to an untouchable hardcoded component.
- Kinematic Dilation does not slow the engine's pulse timer. The zone still pulses on the authored
  tick cadence.
- The slow is refresh-style because `max_stacks = 1`; it does not build an infinite slow ladder
  while an enemy stands in the aura.
