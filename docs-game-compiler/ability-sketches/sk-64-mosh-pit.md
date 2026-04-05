# SK-64: Mosh Pit

## Designer Intent

I channel a short-range performance that keeps nearby enemies locked down for as long as the
channel survives. The crowd control belongs to the channel, not to an independent timed effect.

## Primitive Composition

P-09 (Shape Overlap Query) → P-26 (Capability Bitmask) → P-14 (Continuous Proximity Monitor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target; the area is centered on the channeler

## Observable Behavior

1. The channel begins and establishes a crowd-control field around the caster.
2. Enemies already inside the radius are caught immediately.
3. Enemies entering later are also caught while the channel remains active.
4. Enemies leaving the area are freed.
5. If the caster is interrupted, the maintained field ends and the effect is removed immediately.
6. The caster is rooted/vulnerable while channeling.

## Engine Primitives Required

The canonical path is a channel-owned persistent area effect.

1. The ability uses `channel.execution_mode = tick_while_active` with `movement_lock = root`.
2. The channel owns one centered area output around the caster for the duration of the cast.
3. Entering that area applies one exact source-tagged negative control status.
4. Leaving the area removes that exact maintained status by source match.
5. When the channel ends or breaks, the maintained area output is torn down automatically, which
   also removes the maintained CC it owned.

This keeps the control effect tied to the channel instance instead of treating it as an independent
fixed-duration stun.

## Cross-Boundary Concerns

1. The channeler's current owner maintains the area query each tick.
2. Ghosts entering the radius receive the ordinary target-owner relay for the maintained control
   status.
3. Because the maintained effect is source-tagged and channel-owned, handoff and break teardown
   still remove the correct status instance on the target owner.

## Compiler Requirements

Designer specifies:

- channel duration
- radius
- maintained crowd-control behavior
- caster movement lock / vulnerability

Compiler emits:

- one maintained channel
- one centered area query owned by that channel instance
- one source-tagged exact control status on enter
- one matching status-removal path on leave / channel teardown

Compiler validates:

1. the channel uses a maintained execution mode
2. the maintained effect has a bounded radius and duration
3. removal keys exact status ID + source identity so overlapping Mosh Pit sources do not erase one
   another incorrectly

## Resolved Interaction Notes

- Unstoppable and other CC-immunity windows prevent admission of the maintained control status.
- If an enemy is cleansed while still inside the field, the next maintained tick may reapply the
  effect because the channel is still active.
- Overlapping sources remain distinct because removal is keyed to exact source-tagged status
  instances, not to a generic "stunned somehow" bucket.
- Silence, stun, or displacement on the channeler ends the maintained effect through the ordinary
  channel-break path.
