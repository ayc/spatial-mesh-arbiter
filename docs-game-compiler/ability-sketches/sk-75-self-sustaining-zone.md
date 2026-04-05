# SK-75: Self-Sustaining Zone

## Designer Intent

I cast a dark feast on a target area. Every second, it erupts dealing damage to all enemies inside. If a pulse hits at least one enemy, the zone persists and pulses again. If a pulse hits ZERO enemies, the zone ends. The zone could theoretically last forever if enemies keep standing in it.

## Primitive Composition

P-32 (Actor Spawning) → P-44 (Pulse Timer) → P-09 (Shape Overlap Query) → P-17 (Conditional Thresholds)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Cast — zone appears at target position (circular, fixed radius)
2. First pulse: deal damage to all enemies inside
3. If pulse hit at least 1 enemy: schedule next pulse in 1 second
4. If pulse hit 0 enemies: zone ends immediately
5. Each subsequent pulse follows the same rule: hit someone → continue, hit nobody → end
6. In this reference, the zone still has a generous hard cap, but it ordinarily ends early the
   first time a pulse finds no occupants
7. Enemies can walk in and out — the zone only checks occupancy on pulse ticks
8. Visual: dark maw chomping every second, fades when no targets remain

## Engine Primitives Required

Self-Sustaining Zone is now a canonical `zone.pulse_effects` plus `persistence.mode =
until_empty_on_pulse` reference.

The recommended lowering is:

1. spawn one stationary zone at the requested ground target
2. author:
   - `pulse_interval_ticks = 60`
   - `pulse_effects = [aoe_damage(...)]`
   - `persistence = { mode = until_empty_on_pulse, count_ghost_hits_as_occupants = true }`
   - a generous authored `duration_ticks` hard cap
3. let the zone end early whenever a pulse finds no admitted occupants

This keeps the mechanic inside the canonical zone surface:

- the zone still pulses on a fixed cadence
- the occupant check happens on pulse cadence, not continuously
- occupancy on a pulse keeps the zone alive for the next pulse
- `duration_ticks` remains a hard safety cap, as required by the current zone contract

## Cross-Boundary Concerns

Self-Sustaining Zone follows the canonical stationary-zone authority model.

1. The zone actor stays on one Arbiter and performs its pulse query there.
2. Remote/Ghost occupants are handled through the ordinary local-query / target-owner damage relay
   path.
3. `count_ghost_hits_as_occupants = true` means the zone owner counts admitted Ghost occupants when
   deciding whether the zone persists to the next pulse.
4. If Ghost data is slightly stale, the zone may persist one extra pulse, which is already the
   canonical tradeoff exposed by `ZonePersistenceBlock`.

## Compiler Requirements

Designer specifies:

- zone radius
- pulse interval
- pulse damage
- hard-cap duration
- whether Ghost occupants count for sustain
- whether source death ends the zone early

Compiler emits:

- one stationary zone actor
- one pulse damage payload
- one `ZonePersistenceBlock(mode = until_empty_on_pulse, ...)`

Compiler validates:

1. `duration_ticks > 0`
2. `pulse_interval_ticks > 0`
3. `until_empty_on_pulse` is only used on a pulsing zone, per the canonical validation rule
4. the sustain mechanic is expressed through `ZonePersistenceBlock`, not through a bespoke
   zone-owned script loop

## Resolved Interaction Notes

- This reference is not truly unbounded forever. The canonical zone contract still requires an
  authored hard cap even when the zone usually ends early on an empty pulse.
- Untargetable or filtered-out entities do not count as occupants for sustain because they are not
  admitted by the pulse query.
- Shield absorption still counts as a successful occupied pulse in this reference because the sustain
  test is occupancy/admission based, not "did someone lose HP" based.
- If the designer does not set `end_on_source_removed`, the zone persists independently of the
  caster until it empties or hits its hard cap.
- Kinematic Dilation does not change the authored pulse cadence. The zone pulses every 60
  simulation ticks in this reference.
