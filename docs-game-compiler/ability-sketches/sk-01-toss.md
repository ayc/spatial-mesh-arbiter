# SK-01: Toss

## Designer Intent

My character is within range to target an enemy. I "toss" the target unit — the enemy is thrown through the air to a position I define (submitted as a requested ground-target position). When the target lands at that position, it takes X damage. Any other enemy units within radius of the landing position also take damage.

## Primitive Composition

P-02 (Forced Displacement) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target entity (must be in range)
- Landing position (requested ground-target position)

## Observable Behavior

1. Target is lifted and displaced along an arc toward the requested landing point.
2. The final landing point is the actual committed stop position after range/world clamping, not
   necessarily the raw requested cursor point.
3. During the flight window, the target is under an airborne lockout and cannot move, attack, or
   cast.
4. On landing, the primary target takes impact damage.
5. An AoE damage check then resolves from the ACTUAL committed landing position.
6. The caster is free to act during the toss flight time; the throw does not root the caster in
   place.

## Engine Primitives Required

Toss is already the canonical `displacement + landing query` example in the compiler docs.

The recommended lowering is:

1. validate one hostile single target in range
2. apply one `displacement` to the target:
   - `destination = cursor_position`
   - `arc = true`
   - `duration_ticks = ...`
   - `max_distance = ...`
   - `output_binding = landing_pos`
3. apply one sibling fixed-duration airborne lockout on the target for the same flight window
4. apply one primary-target `damage` payload
5. apply one `aoe_damage` payload centered on `{ binding: landing_pos }`

This keeps the mechanic inside existing surfaces:

- the tossed unit remains an ordinary entity, not a carrier projectile actor
- the flight path is ordinary `P-02` forced displacement
- the landing blast is an ordinary PostKinematic `P-09` overlap query keyed to the committed
  `landing_pos` binding
- the airborne "cannot act" rule is a sibling authored lockout window, not a bespoke flight-only
  subsystem

## Cross-Boundary Concerns

Toss follows the canonical target-owner displacement path.

1. If the targeted enemy is remote/Ghosted, the hostile cast resolves on the target's CURRENT owner
   before the displacement begins.
2. The tossed entity remains the authoritative entity during flight. No second actor takes
   ownership of it.
3. If the tossed target crosses an Arbiter boundary mid-flight, the displacement state, landing
   binding, and airborne lockout transfer with the target through ordinary handoff.
4. The landing AoE query resolves on the authoritative owner that commits the actual `landing_pos`.
   Local admitted victims resolve there; remote/Ghost victims follow the same target-owner relay
   path as other hostile AoE results.
5. If the requested landing point is inside blocking terrain or beyond max distance, the committed
   landing position clamps to the legal stop point and the AoE centers on that committed result.

## Compiler Requirements

Designer specifies:

- target range
- maximum throw distance
- flight duration / arc behavior
- primary impact damage
- landing AoE radius and damage
- whether the airborne lockout is cleansable

Compiler emits:

- one hostile single-target admission check
- one authored `displacement(..., output_binding = landing_pos)`
- one sibling flight-duration lockout on the target
- one primary-target `damage`
- one PostKinematic `aoe_damage(center = { binding: landing_pos }, ...)`

Compiler validates:

1. the landing query consumes the displacement binding AFTER kinematic resolution, not at
   TargetResolution
2. the tossed unit stays the displacement owner; the compiler MUST NOT synthesize a separate
   projectile/carrier actor
3. `max_distance` / targeting range / AoE radius all satisfy ordinary schema bounds

## Resolved Interaction Notes

- This reference follows the canonical schema/IR example: the landing blast keys off the ACTUAL
  committed `landing_pos`, not the raw requested cursor point.
- Cleanse or purge of the sibling airborne lockout does not rewind an already-committed toss path.
  Once launched, the displacement continues until it reaches its legal stop.
- Displacement immunity / Unstoppable rejects the toss on admission the same way it rejects other
  forced movement.
- If the designer wants the landing blast to exclude the primary target strictly, that exclusion has
  to be authored explicitly. This reference guarantees separate primary impact damage plus an
  ordinary landing AoE centered on `landing_pos`.
