# SK-35: Blink Strike

## Designer Intent

I instantly teleport behind a target enemy and strike them for bonus damage. There is no travel time — I disappear from my current position and appear at the destination in the same tick. The destination is calculated relative to the target's position and facing (behind them).

## Primitive Composition

P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on target enemy — instant, no travel time
2. Caster disappears from current position
3. Caster appears at a position directly behind the target (relative to target's facing direction)
4. Immediate strike on the target for X bonus damage (backstab bonus)
5. The strike benefits from "attacking from behind" modifiers if the game has facing-based mechanics
6. Caster can act normally after arriving (not locked)
7. Visual: puff of smoke at origin, flash appearance at destination, slash effect on target

## Engine Primitives Required

TODO: This is an **instant position snap** — the caster's position changes from A to B in a single tick with no intermediate positions. This is fundamentally different from:
- Normal movement (continuous, bounded by movement speed)
- Displacement (SK-01 Toss — trajectory over multiple ticks)
- Charge (SK-34 — continuous movement at high speed)

The Arbiter needs to:
1. Calculate destination: target's position + offset in the direction opposite to target's facing
2. Validate destination is walkable (not inside a wall, not off the map)
3. Snap the caster's position to the destination
4. Apply the strike damage to the target

### Position Snap Implications
A position snap bypasses all intermediate positions — the caster was never "between" A and B. This means:
- No collision with entities or geometry along the path (can blink through walls?)
- No triggering of SK-30 Trail of Fire or SK-32 Minefield between origin and destination
- Ghost updates for the caster show a discontinuous position jump — interpolation on other clients will look wrong unless the snap is flagged

### Destination Calculation
"Behind the target" requires knowing the target's facing direction. If the target is a Ghost, the Ghost's facing data may be stale or unavailable (current GhostUpdate only carries position, velocity, movement_class). Does the Arbiter need Ghost facing data for this ability to work?

## Cross-Boundary Concerns

TODO: The caster might blink from one Arbiter's region to another Arbiter's region in a single tick — no traversal, no intermediate position. This is an **instant cross-boundary handoff** with no travel window. The caster needs to be removed from Arbiter A and inserted into Arbiter B at the same tick.

Scenarios:
1. **Target is local, destination is local:** No boundary issues. Position snap + strike resolve locally.
2. **Target is a Ghost, destination is in target's Arbiter's region:** Caster blinks into a different Arbiter's territory. Instant handoff required.
3. **Target is local, but destination (behind target) is across a boundary:** Caster blinks past the boundary. Handoff triggered by the destination position, not by movement.

The existing entity handoff protocol is designed for continuous movement (entity approaches boundary, handoff initiated). An instant snap bypasses the approach — the entity was never near the boundary. Does the handoff protocol support "entity is now at position X which is in your region"?

## Compiler Requirements

TODO: Designer specifies: target (enemy), destination calculation (behind target, offset distance), instant teleport (no travel time), strike damage (bonus backstab modifier), range requirement. Compiler produces: position snap + destination function (relative to target position/facing) + immediate damage payload. The compiler needs to flag this as a "teleport" movement type that bypasses normal movement validation (speed caps, collision along path).

## Open Questions

- Can the caster blink through walls / terrain (since there's no traversal)?
- If the destination is inside a wall (target is backed against geometry), where does the caster appear? Closest valid position?
- Does the blink break SK-25 Root (root prevents movement, but is a teleport "movement")?
- Does the blink trigger SK-32 Minefield at the destination (caster appears on top of a mine)?
- Does the blink break SK-04 Tether if it exceeds the break distance?
- If the target moves or dies between cast and resolution (same tick?), what happens?
- How does the backstab bonus work — is "facing" a formal entity property, or derived from last movement direction?
- Can the caster blink to a target on a different Arbiter? This means the cast targets a Ghost but the resolution (strike + position snap) must happen on the target's Arbiter.
- Does the position snap generate a special Ghost update type (teleport flag) so clients don't interpolate through intermediate positions?
- How does the instant handoff interact with the topology epoch — if the caster blinks cross-boundary, the handoff must be immediate, not a 3-phase protocol.
