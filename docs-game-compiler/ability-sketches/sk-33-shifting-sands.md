# SK-33: Shifting Sands

## Designer Intent

I cast a sandstorm zone that starts at a target position and slowly drifts in a direction over 6
seconds. Enemies caught inside have their movement speed reduced by 40% and take damage every
second. The zone moves independently after cast; I do not steer it once it is created.

## Primitive Composition

P-32 (Actor Spawning) → P-03 (Trajectory Steering) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted, zone start position)
- Drift heading (commonly caster-to-target, but still lowered through the canonical self-propelled
  heading pair)

## Observable Behavior

1. Sandstorm zone appears at target position (circular, fixed radius)
2. Zone begins drifting in the specified direction at a constant speed
3. Every 1 second, enemies inside take damage and receive a 40% movement slow
4. As the zone moves, new enemies are caught and previously-inside enemies may escape
5. Zone travels for 6 seconds, then dissipates
6. Caster is free to act; the zone is autonomous after cast
7. Visual: moving sandstorm cloud, visibility reduction inside the zone

## Engine Primitives Required

Shifting Sands is the canonical self-propelled `zone` pattern.

The compiler lowers it to one spawned zone actor with:

1. `position = requested ground target`
2. `shape = circle`
3. authored `radius`
4. `duration_ticks = 360`
5. `pulse_interval_ticks = 60`
6. `pulse_effects = [damage(...), apply_debuff(shifting_sands_slow)]`
7. `mobility = {`
   `mode = self_propelled,`
   `heading_from = ... ,`
   `heading_to = ... ,`
   `speed = ... ,`
   `world_impact = ignore`
   `}`
8. ordinary `owner_entity_id` linkage back to the caster for source identity and kill credit

This is not a bespoke "zone with velocity" subsystem anymore. It is the existing `ZoneMobilityBlock`
surface with `mode = self_propelled`. The runtime advances the zone by its authored heading and
speed every tick from the zone actor's current committed center.

The slow is an ordinary negative status effect reapplied each pulse. With `max_stacks = 1`, staying
inside the storm keeps one live 40% slow refreshed; leaving the storm keeps only the most recent
slow instance until that short trailing duration expires naturally.

## Enter/Leave Detection

This sketch is pulse-driven, not edge-triggered.

Because it only authors `pulse_effects` and not `enter_effects`, `leave_effects`, or
`persistence.mode = until_empty_on_pulse`, the runtime does not need a persistent occupant-set diff
for Shifting Sands. Each pulse simply queries hostile occupants against the zone actor's current
position for that tick.

That means:

1. the moving zone itself changes who is hit on the next pulse
2. enemies entering mid-drift begin taking damage and slow on the next pulse
3. enemies leaving keep only the most recent applied slow instance until it expires
4. if a later design wants true enter/leave triggers, it should use the canonical occupant-set
   path already defined for zones instead of adding Shifting-Sands-specific logic

## Cross-Boundary Concerns

Shifting Sands follows the ordinary moving-zone authority model.

1. The sandstorm is one zone actor with one authoritative owner at a time.
2. While the zone center remains local, that owner advances the drift and runs pulse queries from
   the zone's committed current position.
3. If the zone center crosses a seam, the zone actor hands off like any other moving spawned actor;
   there is no projectile-style three-phase impact protocol because the zone remains one persistent
   actor rather than a prepare/ack/commit hit packet.
4. Local targets resolve locally; Ghost targets use the ordinary target-owner relay path instead of
   mutating Ghost HP or Ghost status locally.
5. After handoff, the new owner continues the same authored drift heading, speed, and remaining
   lifetime cap from the transferred zone state.

## Compiler Requirements

Designer specifies:

- ground-targeted spawn position
- zone radius
- drift heading and speed
- lifetime (`360` ticks)
- pulse interval (`60` ticks)
- hostile filter
- damage payload per pulse
- slow status payload per pulse (`40%` movement slow, short trailing duration)
- optional persistence override if the storm should end on caster removal

Compiler emits:

- one `zone` effect lowered to a spawned zone actor
- `ZoneMobilityBlock { mode = self_propelled, heading_from, heading_to, speed }`
- per-pulse hostile overlap evaluation from the zone's current position
- one compiled slow `StatusEffectDefinition`
- ordinary spawned-actor owner linkage back to the caster

Compiler validates:

1. `radius > 0`
2. `duration_ticks > 0`
3. `pulse_interval_ticks > 0`
4. `speed > 0`
5. the self-propelled heading pair is non-degenerate
6. the slow is authored as an ordinary negative status, not as a custom moving-zone-only flag
7. any source-death or world-impact behavior uses canonical `ZonePersistenceBlock` /
   `ZoneMobilityBlock` fields instead of sketch-local booleans

## Resolved Interaction Notes

- This sketch uses constant-speed linear drift only. Curved or accelerating storm paths would need a
  different authored mobility profile.
- `world_impact = ignore` is the intended default here, so walls do not stop or deflect the storm.
- Caster death does not automatically remove the zone; authored persistence decides that, and the
  default remains `end_on_source_removed = false`.
- Multiple sandstorms are ordinary multiple zone actors. Damage and slow stacking follow the
  authored status and pulse rules rather than a sketch-local anti-stack rule.
- `SK-31 Vortex` pulls entities, not hostile zones. This sketch does not grant a generic
  zone-versus-zone force interaction system.
- The zone is still bounded by the normal spawned-actor and monitored-zone limits; self-propelled
  mobility does not create an unbounded per-tick query exception.
