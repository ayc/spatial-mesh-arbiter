# SK-16: Holy Ground

## Designer Intent

I place a healing zone on the ground. All allies standing inside it are healed every second for 8
seconds. The zone is stationary, so allies must stay inside to keep receiving pulses. Enemies are
not affected.

## Primitive Composition

P-32 (Actor Spawning) -> P-14 (Continuous Proximity Monitor) -> P-44 (Pulse Timer) -> P-15 (Value
Modification)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- caster entity
- requested ground-target position

## Observable Behavior

1. A circular healing field appears at the targeted ground position.
2. Every 1 second, allies inside the field are healed.
3. Allies entering mid-duration start receiving healing on the next pulse.
4. Allies leaving the field stop receiving healing immediately and keep no lingering effect in this
   reference.
5. The field persists for 8 seconds, then expires.
6. Overlapping Holy Ground zones stack because each zone pulses independently.
7. Visual presentation may render a bright stationary ring plus periodic heal pulses.

## Engine Primitives Required

Holy Ground is the canonical stationary allied pulse-zone reference.

The recommended lowering is:

1. emit one stationary `zone` with:
   - `position = requested ground target`
   - `shape = circle`
   - authored `radius`
   - `duration_ticks = 480`
   - `pulse_interval_ticks = 60`
   - `pulse_effects = [heal]`
2. give the zone an allied admission filter for its pulse query
3. keep source identity linked to the caster through the zone actor's ordinary owner linkage

This keeps the mechanic inside existing surfaces:

- Holy Ground is an ordinary spawned zone actor, not a bespoke healing aura subsystem
- the pulse cadence is the canonical Stage 11 `P-44` timer
- each heal pulse is ordinary healing through the normal heal path
- allied filtering is data-driven rather than hardcoded in the zone actor

## Cross-Boundary Concerns

Holy Ground follows the same zone-owner relay model as other pulse zones, but with allied healing
instead of hostile damage.

1. The zone actor is authoritative on the Arbiter that owns its current center position.
2. On each pulse, that owner runs the allied overlap query from the zone's committed current
   position.
3. Local allies are healed locally.
4. Ghost/remote allies generate the same target-owner relay pattern used by other remote allied
   heals.
5. Because the zone is stationary in this reference, there is normally no zone-owner handoff after
   spawn. If topology changes still move the zone actor, ordinary spawned-actor handoff preserves
   its pulse timer and caster linkage.

## Compiler Requirements

Designer specifies:

- ground-targeted placement
- zone radius
- duration
- pulse interval
- heal amount per pulse
- allied-only filter

Compiler emits:

- one stationary `zone`
- one allied pulse query
- one per-pulse heal payload
- ordinary spawned-actor owner linkage back to the caster

Compiler validates:

1. `radius > 0`
2. `duration_ticks > 0`
3. `pulse_interval_ticks > 0`
4. the mechanic is expressed as a pulse zone, not as a snapshot AoE buff
5. the target filter is allied-only for this reference

## Resolved Interaction Notes

- The caster is healed too if standing inside, because this reference uses the ordinary allied
  filter and the caster is an ally to themself.
- Healing is ordinary HP restoration; overheal is wasted unless some other separately authored
  mechanic converts overheal into another benefit.
- Enemies are simply not admitted by the allied pulse query. They do not take damage and do not
  block healing pulses to allies.
- The zone does not pulse on placement in this reference. The first heal happens after the first
  full pulse interval.
- Kinematic Dilation does not alter the server's tick-based pulse cadence. The zone still pulses on
  its authored 60-tick interval.
