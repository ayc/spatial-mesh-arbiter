# SK-85: Ring Geometry

## Designer Intent

I cast a ring of frost at a target position. After a brief delay, the ring activates — enemies standing ON THE RING (the circumference) are damaged and rooted. Enemies standing INSIDE the ring (at the center) are completely safe. The ring is a donut shape — only the edge matters.

## Primitive Composition

P-09 (Shape Overlap Query) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Cast at target position — ring indicator appears (brief delay before activation)
2. After 0.5 second delay: ring activates
3. Enemies ON the ring (within the band between inner and outer radius) are hit: damage + root
4. Enemies INSIDE the ring (within inner radius) are NOT hit — safe zone
5. Enemies OUTSIDE the ring (beyond outer radius) are NOT hit
6. One-time activation (not a persistent zone — single check on activation)
7. Visual: frost ring on the ground, enemies caught on the edge are frozen

## Engine Primitives Required

Ring Geometry is now a canonical ring-shaped delayed AoE reference.

The recommended lowering is:

1. author the ability with:
   - `targeting = { type = area, shape = ring, range = ..., radius = outer_radius, ring_inner = inner_radius, filter = enemy_alive }`
   - `cast_time = 0.5`
2. on completion, resolve one ring-shaped query with:
   - ordinary damage
   - ordinary root application to the same matched targets

This keeps the mechanic inside existing canonical surfaces:

- ring/donut is already a supported targeting geometry
- the center-safe behavior is just `ring_inner`
- the brief warning window is the ordinary cast / delay window, not a bespoke geometry scheduler

## Cross-Boundary Concerns

Ring Geometry follows the ordinary AoE query pattern.

1. The ring query is centered and evaluated on the caster's current owner.
2. Local targets are resolved directly; admitted remote/Ghost targets receive the ordinary hostile
   relay for damage and root admission.
3. A ring that straddles a seam is still one local query plus Ghost-backed remote admissions, just
   like other large AoE shapes.

## Compiler Requirements

Designer specifies:

- outer radius
- inner radius
- warning / cast delay
- damage
- root duration

Compiler emits:

- one ring-shaped area query
- one ordinary damage payload
- one ordinary root payload

Compiler validates:

1. `0 <= ring_inner < radius`
2. the delayed activation is expressed through the ordinary cast window, not a bespoke ring-only
   timer system
3. root uses the ordinary canonical `apply_cc(cc_type = root)` path

## Resolved Interaction Notes

- Thin and thick rings are both legal because `ring_inner` and `radius` are independently authored
  within the canonical validation bounds.
- The center remains completely safe in this reference because only the ring band is queried.
- Ring geometry is just another targeting shape and may be reused for hostile or beneficial effects
  in later designs without adding a new geometry primitive.
- Later movement or displacement that puts an entity into the band before cast completion makes that
  entity eligible for the one-time hit exactly like other delayed AoE casts.
