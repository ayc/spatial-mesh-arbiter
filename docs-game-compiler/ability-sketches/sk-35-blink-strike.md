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

Blink Strike is canonical `P-01` instant translation with a destination derived from a target entity
rather than from a fixed ground point.

The resolving owner must:

1. Read the target's current authoritative pose and `facing_direction`
2. Compute the behind-target offset from that pose/facing
3. Run the normal `P-01` destination validation and nearest-valid-position resolution
4. Commit the snap atomically
5. Resolve the immediate follow-up strike from the post-snap position in the same tick

This is not ordinary movement and not `P-02` displacement. There is no traversed path, no
intermediate collision history, and no travel window. The caster is never "between" origin and
destination for collision or overlap purposes.

The target-facing dependency is also canonical, not sketch-local. `docs-core/` already requires a
`facing_direction` in kinematic state, so "behind target" is derived from formal engine-facing
state rather than from a vague animation concept.

## Cross-Boundary Concerns

Blink Strike follows the canonical `CG-01` cross-boundary snap rule.

1. If the target is local and the resolved destination stays local, the current owner computes the
   behind-target point, validates it, commits the snap, and resolves the strike locally.
2. If the target is remote/Ghost, or if the computed behind-target destination belongs to another
   Arbiter, the origin owner emits a `cross_boundary_snap` request instead of treating Ghost data as
   authoritative.
3. The destination owner re-derives the behind-target point from the target's authoritative
   pose/facing, validates walkability, commits the snap, and resolves the follow-up strike there in
   the same tick.

This is destination-based handoff, not travel-based handoff. There is no dual ownership window and
no mid-path authority sharing. Ghost pose/facing can be used for admission or preview only; final
coordinates and strike resolution are always recomputed on the authority that already owns the
target-side spatial state.

## Compiler Requirements

Designer specifies:

- hostile target entity
- cast range / admission constraints
- behind-target offset distance
- instant-translation behavior (no travel time)
- follow-up strike payload, including any backstab bonus

Compiler emits:

- one `P-01`-style instant translation whose destination is derived from the target entity's
  current pose/facing
- one immediate follow-up hostile strike payload
- cross-boundary relay metadata carrying the relative-offset rule, not guessed world coordinates

Compiler validates:

1. the target reference is entity-targeted and hostile
2. the authored offset is positive and bounded
3. the ability is lowered as teleport/snap behavior, not as displacement or sweep
4. cross-boundary lowering carries only parameters needed to recompute the destination on the
   authoritative owner

## Resolved Interaction Notes

- Blink has no traversed path, so it does not collide with or trigger path-intermediate effects on
  the route between origin and destination.
- `P-01` still enforces collision safety at the final location; if the authored behind-target point
  is invalid, the engine resolves to the nearest valid position instead of placing the caster inside
  static geometry.
- Facing is a formal engine property via `facing_direction`, so backstab-style "behind target"
  logic is grounded in canonical kinematic state.
- Remote-target Blink Strike is allowed, but the final destination and strike resolve on the
  destination/target owner, not from origin-side Ghost guesses.
- Root, tether, and leash-style movement constraints only block or clamp Blink if their authored
  status metadata applies to teleports (`apply_to_teleports = true`).
