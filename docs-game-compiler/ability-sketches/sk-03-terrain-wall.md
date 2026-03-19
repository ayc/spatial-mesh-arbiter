# SK-03: Terrain Wall

## Designer Intent

My character creates a temporary wall at a target position that blocks all movement and projectiles for 5 seconds, then crumbles. I can use this to cut off escape routes, split enemy formations, or block incoming projectiles.

## Primitive Composition

P-08 (Dynamic Collision Injection) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Wall placement position (requested ground-target position)
- Wall orientation (perpendicular to caster-to-target vector, or explicit angle)

## Observable Behavior

1. Wall appears instantly at target position
2. All entity movement is blocked by the wall (pathfinding treats it as impassable)
3. All projectiles collide with the wall (raycasts hit it)
4. Wall persists for 5 seconds
5. Wall crumbles and is removed — movement and projectiles pass freely again
6. Wall has no HP (cannot be destroyed early in base version)

## Engine Primitives Required

TODO: How does the Arbiter insert/remove collision geometry at runtime? Does the static_grid support dynamic entries? What is the representation — an AABB? A line segment with thickness? How do neighboring Arbiters learn about it for cross-boundary raycasts?

## Cross-Boundary Concerns

TODO: If the wall sits on or near an Arbiter boundary, both Arbiters need to respect it for collision. Ghost entities approaching the wall from the neighbor's side need to collide with it. Projectiles crossing boundaries need to see it.

## Compiler Requirements

TODO: What does the designer write? What runtime data does the compiler produce — a collision shape definition? A timed lifecycle? How does the ability definition reference the wall's geometry?

## Open Questions

- Does the static_grid support runtime insertion/removal, or is a separate dynamic collision structure needed?
- Can entities be trapped inside the wall if it spawns on top of them? If so, what happens — push them out?
- Can the wall be placed partially inside existing static geometry?
- Should the wall have HP and be destructible as a variant?
- How does the wall interact with forced displacement abilities (SK-01 Toss landing inside a wall)?
- Performance: if many walls are active simultaneously, does the collision query degrade?
