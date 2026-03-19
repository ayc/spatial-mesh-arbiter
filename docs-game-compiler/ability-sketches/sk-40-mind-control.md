# SK-40: Mind Control

## Designer Intent

I channel on an enemy hero, forcing them to walk toward me for 2.5 seconds. While channeling, I control the direction the enemy walks — they move at reduced speed in the direction I steer. The enemy cannot act during mind control. If the channel is interrupted, the effect ends immediately.

## Primitive Composition

P-29 (Control Authority Swap) → P-26 (Capability Bitmask) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)
- Caster's steering input (requested steering target/direction, updated in real time during channel)

## Observable Behavior

1. Cast on enemy hero — channel begins
2. Target is forced to walk in the direction the caster steers (derived from the caster's requested steering input relative to the target)
3. Target moves at 50% of their normal speed
4. Target cannot act — movement input overridden, abilities blocked, auto-attack blocked
5. Caster is locked in place while channeling (cannot move, cannot cast other abilities)
6. If channel is interrupted (caster takes damage above threshold? stun? silence?): effect ends immediately, enemy regains control
7. Channel lasts 2.5 seconds maximum
8. Visual: purple mind control beam between caster and target, target's eyes glow, puppet-like movement

## Engine Primitives Required

### Real-Time Input Override
This is the first ability where the **caster's input stream controls another entity's movement**. Each tick during the channel:
1. Read the caster's current steering input
2. Calculate a movement direction for the target (e.g., direction from target toward the caster's requested steering target, or direction explicitly specified by the caster)
3. Override the target's movement input with this calculated direction
4. Apply movement at 50% of the target's base speed

This means the caster's Edge Node is sending input that the Arbiter interprets as movement commands for a DIFFERENT entity. The Arbiter needs to:
- Accept "steering input" from the caster as part of the channel state
- Map that input to the target's movement system
- Suppress the target's own movement input entirely

### Channel With External Input
SK-05 Global Strike is a channel, but it's fire-and-forget — no input during the channel. Mind Control requires **continuous caster input during the channel**. The channel state must include:
- Target EntityID
- Current steering direction (updated each tick from caster input)
- Remaining duration
- Break conditions

### Input Routing
The caster's Edge Node sends movement/steering data. Normally this controls the caster. During Mind Control, the Arbiter must route the caster's steering input to the target's movement system instead. How is this expressed:
- A special ActionProposal type: `SteerMindControl { target_id, direction }`?
- Continuous input on the caster that the Arbiter reinterprets based on active channel state?

## Cross-Boundary Concerns

TODO: This is architecturally challenging. If the caster and target are on different Arbiters:

1. **Caster on Arbiter A, target on Arbiter B:** The caster's steering input arrives at Arbiter A (where the caster lives). But the target's movement is resolved on Arbiter B. Every tick, Arbiter A must relay the steering direction to Arbiter B. That's 60 cross-boundary messages per second for the duration of the channel.

2. **Target walks toward the caster, crosses a boundary:** If the forced movement brings the target from Arbiter B into Arbiter A's region, a handoff occurs mid-mind-control. The channel and steering must survive the handoff.

3. **Caster and target start on the same Arbiter but target is forced to walk away:** If the target is walked toward the boundary and crosses it, the mind control channel must continue across boundaries.

4. **Channel break on distance?** If the target is forced too far from the caster (or the caster is displaced), does the channel break?

## Compiler Requirements

TODO: Designer specifies: channel duration (2.5s), target movement speed (50%), caster locked, target fully disabled, steering input (caster controls direction), break conditions (interrupt, distance, caster death). Compiler produces:
- Channel state machine with per-tick input consumption
- Status effect on target: full disable + movement override
- Input routing: caster's steering → target's movement
- Break condition checks per tick

The compiler needs to express "this channel consumes real-time input and applies it to a different entity" — a pattern unlike any other ability.

## Open Questions

- Does the caster control the exact direction, or just "walk toward my requested steering target"?
- Can the caster steer the target off cliffs, into lava, into SK-29 Blizzard zones?
- Does the forced movement respect collision with static geometry (can't walk through walls)?
- Can the target be walked into SK-32 Minefield to trigger mines?
- Does Tenacity reduce the Mind Control duration?
- Is Mind Control affected by Diminishing Returns (SK-28)?
- Can SK-15 Purify be cast on the mind-controlled target by an ally (if Purify requires the target to be in range of the purifier, not the mind-controlled entity)?
- What happens if two casters attempt Mind Control on the same target simultaneously?
- Does the 60Hz steering relay create unacceptable cross-boundary traffic for a single ability?
- Can the mind-controlled target's passive effects still function (SK-23 Thorns, SK-08 Aura)?
