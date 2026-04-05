# SK-40: Mind Control

## Designer Intent

I channel on an enemy hero, forcing them to walk under my steering for 2.5 seconds. While the
channel lasts, the target moves at reduced speed in the direction I steer, cannot act, and the
effect ends immediately if the channel is broken.

## Primitive Composition

P-29 (Control Authority Swap) → P-26 (Capability Bitmask) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity in range
- Channel duration
- Target movement-speed multiplier while controlled
- Continuous steering input from the caster during the channel

## Observable Behavior

1. Cast on an enemy hero and begin channeling
2. On the next Stage 1 routing boundary after channel admission, the target's movement is driven by
   the caster's steering input instead of by the target's own player
3. The controlled target moves at 50% of normal speed in the steered direction
4. The target cannot move on its own, cast abilities, or attack while the control override lasts
5. The caster is rooted in place and cannot use other abilities while maintaining the channel
6. If the channel is interrupted, expires, or either participant is removed, control ends
   immediately and normal routing resumes
7. Forced movement still respects ordinary collision, pathing, and boundary handoff rules; the
   target can be steered into hazards, zones, or mines only through legal movement
8. Visual: a maintained control beam, target eye-glow, and puppet-like locomotion

## Engine Primitives Required

Mind Control is now a canonical maintained-control channel built from the existing channel and
Stage 1 routing contracts. It does not require a bespoke "mind-control steering protocol."

### Canonical Channel Shape

The recommended lowering is:

- one channeled ability with:
  - `channel.execution_mode = tick_while_active`
  - `channel.tick_interval_ticks = 1`
  - `channel.continuous_input = steer_target_movement`
  - `channel.movement_lock = root`
  - `channel.break_on_target_invalid = true`
- one channel-owned `control_override` effect with:
  - `target = target`
  - `controller = caster`
  - `duration_ticks = 150` for the 2.5 second cap
  - `movement_speed_multiplier = 0.5`
  - `input_policy = adapter_routed`
  - `controller_lock_mode = all_actions`
  - `target_lock_mode = all_actions`

This yields the intended behavior without inventing a second input plane. The controlling player's
accepted steering stream remains the ordinary authoritative input source; the channel just routes it
to the target through `P-29`.

### Steering Semantics

For this sketch, the caster steers the target using the same accepted directional/steering state
the engine already records for the caster's own movement input. The target is not auto-walked
toward the caster or toward a separate reticle unless another authored effect adds that rule.

### Break / Revert Semantics

Because the effect is channel-owned:

1. expiration, interruption, silence, stun, sleep, owner removal, or target removal tears the
   control down through the ordinary maintained-effect teardown path
2. teardown reverts the Stage 1 routing atomically
3. there is no sketch-local cleanup logic or free-floating control state

## Cross-Boundary Concerns

Mind Control follows the canonical `P-29` cross-boundary relay model.

1. The controlled entity keeps its own authoritative Arbiter; control changes only the input source
2. If caster and target are on different Arbiters, accepted steering proposals from the caster's
   player are forwarded through the existing Stage 1 relay path to the target owner
3. This is ordinary routed-control traffic, not a new 60Hz bespoke message type
4. If the target crosses a seam while controlled, the control override and channel-owned teardown
   state hand off with the target like other authoritative routing state
5. Distance alone does not break the effect in this sketch. If a range clamp is desired, it should
   be authored separately as a channel guard or link break rule rather than assumed by `P-29`

## Compiler Requirements

Designer specifies:

- target filter and cast range
- channel duration
- target movement-speed multiplier while controlled
- controller and target lock profiles
- channel break policy and optional interrupt-on-damage threshold
- observer presentation for the beam / visual tell

Compiler emits:

- one channeled cast with `continuous_input = steer_target_movement`
- one channel-owned `control_override`
- the ordinary maintained-effect teardown / Stage 1 revert path
- no sketch-local control protocol, relay type, or alternate input message

Compiler validates:

1. `channel.execution_mode = tick_while_active`
2. `channel.tick_interval_ticks > 0`
3. `continuous_input = steer_target_movement` only appears on a ticking channel
4. the target filter excludes invalid control targets such as dead or non-controllable actors
5. the authored override never attempts controller chains or two controllers on one target; those
   cases are rejected by the canonical `P-29` constraints

## Resolved Notes

- Mind Control in this sketch is a channel-owned control override, not a generated `apply_cc`
  profile, so status-resistance scaling and DR do not shorten it unless a separate CC status is
  also authored
- Ally cleanse effects do not break this sketch by default because the effect is not represented as
  a removable status entry; interruption comes from the maintained-channel contract
- If a second caster attempts Mind Control on the same target while one override is active, the
  second attempt is rejected by the one-controller-per-entity `P-29` rule
- Passive effects on the controlled target continue unless a separate capability/status effect
  suppresses them; this sketch only locks movement, attacks, and casts
