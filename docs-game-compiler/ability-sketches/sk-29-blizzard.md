# SK-29: Blizzard

## Designer Intent

I cast a snowstorm at a target position. The storm persists for 8 seconds. Every second, enemies inside take cold damage and are slowed by 30%. The storm is stationary — I can walk away and it keeps going.

## Primitive Composition

P-32 (Actor Spawning) → P-09 (Shape Overlap Query) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Storm zone appears at target position (circular, fixed radius)
2. Every 1 second: all enemies inside take X cold damage
3. Every 1 second: all enemies inside receive 30% movement slow (refreshed each pulse, effectively permanent while inside)
4. Enemies entering mid-duration begin taking damage/slow on the next pulse
5. Enemies leaving the zone keep only the most recently applied slow instance, which expires naturally after its authored duration
6. Caster is free to move and act after casting — zone is independent
7. Zone persists for 8 seconds then dissipates
8. Visual: swirling snow/ice effect within the zone boundary

## Engine Primitives Required

This is the canonical stationary `zone` pattern. The compiler lowers Blizzard to one spawned zone
actor (`P-32`) with:

1. `position = requested ground target`
2. `shape = circle`
3. authored `radius`
4. `duration_ticks = 480`
5. `pulse_interval_ticks = 60`
6. `pulse_effects = [cold damage, apply_debuff(blizzard_slow)]`

The zone actor owns its own lifetime cap, pulse timer, and current center, but it also retains the
normal spawned-actor `owner_entity_id` linkage to the caster for source identity and kill credit.
That owner linkage survives ordinary handoff and is cleaned up through the normal `P-32` owner-death
notification path. Whether the storm despawns on caster death is not bespoke to Blizzard; it is
authored through `ZonePersistenceBlock.end_on_source_removed`, whose default is `false`.

The slow portion is not `apply_cc`. It is an ordinary negative `StatusEffectDefinition` authored
through `apply_debuff`, with a movement-speed `stat_modifier`, `cc_category = soft_disable`, and
`duration_scaling = status_resistance`. With `max_stacks = 1`, repeated pulses keep one live slow
instance on the target instead of building an unbounded stack ladder.

## Enter/Leave Detection

Blizzard does NOT need explicit leave cleanup or a persistent occupant set. Because the sketch only
authors `pulse_effects` and not `enter_effects`, `leave_effects`, or `persistence.mode =
until_empty_on_pulse`, the runtime can use a fresh hostile overlap query on each pulse from the
zone actor's committed current position.

That means:

1. Entities that are outside on a given pulse are simply not hit on that pulse.
2. The slow "cleanup" is just expiry of the last applied slow status instance.
3. If a designer later wants true enter/leave triggers or early-despawn-when-empty behavior, that
   is when the canonical occupant-set path is required.

## Cross-Boundary Concerns

Blizzard is still one zone actor with one authoritative owner. It does not split into multiple
Arbiters when its radius overlaps a boundary. The authoritative zone owner is whichever Arbiter owns
the spawned zone actor's center position; neighboring Arbiters participate through the Ghost/relay
model, not by creating duplicate half-zones.

Per pulse:

1. The zone owner runs the hostile overlap query.
2. Local targets are resolved locally.
3. Ghost targets generate the normal cross-boundary hostile relay path.
4. The target owner then performs target-side defense and status admission for the cold damage and
   slow application.

Because Blizzard is stationary, there is no zone-owner handoff after spawn in the normal case. If a
future moving-zone variant is authored, the zone actor would use ordinary spawned-actor handoff and
keep its `owner_entity_id` linkage intact.

## Compiler Requirements

Designer specifies:

- ground-targeted placement
- zone radius
- duration (`480` ticks)
- pulse interval (`60` ticks)
- hostile filter
- cold damage payload per pulse
- slow status payload per pulse (`30%` movement slow, short trailing duration)
- optional persistence override if the storm should end on caster removal

Compiler emits:

- one `zone` effect lowered to a spawned stationary zone actor
- one compiled `StatusEffectDefinition` for the Blizzard slow
- per-pulse overlap evaluation with `pulse_effects = [damage, apply_debuff]`
- spawned-actor owner linkage back to the caster

Compiler validates:

1. `radius > 0`
2. `duration_ticks > 0`
3. `pulse_interval_ticks > 0`
4. `pulse_effects` is present because the ability is pulse-driven
5. the slow status is a negative status and not a positive buff
6. any persistence override uses the canonical `ZonePersistenceBlock` fields instead of sketch-local flags

## Resolved Interaction Notes

- Friendly fire is controlled by the authored hostile filter. This sketch targets enemies only.
- Caster death does not automatically remove the zone; authored persistence decides that.
- Each pulse is its own hostile application. Crit, block, evade, and other ordinary combat outcomes
  are resolved per pulse through the standard combat pipeline.
- The slow is the same authored status re-applied on each pulse; with `max_stacks = 1`, Blizzard is
  a refresh-style 30% slow, not a self-stacking 60%/90% slow ladder.
- Kinematic Dilation does not change the engine's 60Hz clock. The zone pulse timer remains tick
  based; dilation changes entities' kinematic/cast rates, not the server tick schedule.
- The zone is a spawned actor and therefore counts against the normal spawned-actor / entity-count
  bounds while it exists.
