# SK-49: Cone Strike

## Designer Intent

I swing my weapon in a wide arc in front of me, dealing damage and slowing all enemies in a cone-shaped area. The cone extends from my position outward in the direction I'm facing, like a fan or pizza slice.

## Primitive Composition

P-09 (Shape Overlap Query) → P-12 (Facing/Dot-Product Check)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (caster's facing direction or requested aim direction)

## Observable Behavior

1. Cast — instant AoE in a cone shape in front of the caster
2. Cone has an angle (e.g., 90 degrees) and a range (e.g., 6 meters)
3. All enemies within the cone take X damage
4. All enemies within the cone are slowed by 40% for 2 seconds
5. Allies are not affected
6. The cone is anchored to the caster's position and oriented in the cast direction
7. This is instant (not a zone that persists) — snapshot query at cast time
8. Visual: sweeping arc slash effect

## Engine Primitives Required

Cone Strike is now a canonical cone-targeting reference.

The recommended lowering is:

1. author `targeting = {`
   `type = area,`
   `shape = cone,`
   `range = 6m,`
   `radius = 6m,`
   `cone_angle = 45deg,`
   `filter = enemy_alive`
   `}`
2. resolve the cone from the caster's position using the cast direction / facing snapshot at cast
   commit
3. apply ordinary `damage` plus one generated slow debuff to every admitted enemy in the cone

This uses the existing canonical target geometry:

- `shape = cone` is already part of `TargetingBlock`
- the dot-product/facing gate is already part of the `P-12` targeting surface
- the result set is just a normal snapshot AoE query, not a persistent zone

## Cross-Boundary Concerns

Cone Strike follows the ordinary short-range AoE rule.

1. The caster's owner performs the cone query locally against current local entities plus
   Ghost-visible candidates near the seam.
2. Admitted Ghost/remote enemies receive the usual hostile relay for damage / debuff resolution on
   their own owner.
3. This reference assumes a short melee cone, so ordinary Ghost range is sufficient. Mesh-wide or
   unusually long cones would be a different design problem, not part of this baseline sketch.

## Compiler Requirements

Designer specifies:

- cone angle
- range
- damage payload
- slow amount / duration
- whether the cone uses cast direction or current facing

Compiler emits:

- one cone-targeting query in `TargetingBlock`
- one snapshot result set filtered to hostile living entities
- one damage payload and one slow payload for every admitted target

Compiler validates:

1. `shape = cone`
2. `radius > 0`
3. `cone_angle > 0`
4. the ability stays a snapshot query rather than a persistent cone-shaped zone in this reference

## Resolved Interaction Notes

- This reference uses the cast-direction snapshot at cast commit, not an auto-targeted nearest enemy
  facing override.
- Cone admission is based on the same authoritative spatial snapshot used by other AoE queries; no
  extra line-of-sight wall blocking is implied unless the wider game layer separately authors it.
- Cone geometry is already a configurable targeting shape in the compiler docs. No new primitive or
  special engine-side geometry family is needed for this sketch.
- Persistent cone-shaped hazards would be a separate zone-authoring pattern. This sketch is only the
  instant snapshot strike.
