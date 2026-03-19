# SK-25: Root

## Designer Intent

I snare an enemy's feet to the ground. They cannot move for 3 seconds, but they can still attack and cast abilities. They can be freed early by SK-15 Purify or by certain mobility abilities.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Ability lands on target — root is applied for 3 seconds
2. Target cannot move (movement input ignored, velocity forced to zero)
3. Target CAN attack (auto-attack functional if enemies are in range)
4. Target CAN cast abilities (all non-movement abilities functional)
5. Active movement abilities (dashes, blinks) are blocked while rooted
6. Root does NOT interrupt channels
7. Duration reduced by tenacity
8. Diminishing returns apply (same system as SK-24 but may be in a separate DR category)
9. Cleansable by SK-15 Purify
10. Visual: vines/ice/chains around the target's feet

## Engine Primitives Required

TODO: Root suppresses movement capability only — `can_move = false` but `can_attack = true`, `can_cast = true`. The Arbiter needs to distinguish "movement ability" from "non-movement ability" for casting suppression. A rooted entity that tries to cast a dash/blink should be rejected, but a rooted entity casting a fireball should succeed. How is "movement ability" classified — a tag on the ability definition? Does the compiler flag it?

## Interaction With Other CC

- **Stun (SK-24)** applied while rooted: stun takes over (fully disabled). When stun expires, does the remaining root duration continue, or is it consumed?
- **Silence (SK-26)** applied while rooted: both apply simultaneously — can't move AND can't cast, but can still auto-attack. Effectively a stun but composed of two separate effects.
- **Displacement (SK-01 Toss)** while rooted: does the root prevent displacement? Design choice — root could ground the entity (displacement blocked) or displacement could break the root.

## Cross-Boundary Concerns

TODO: Same relay pattern as SK-24. If the target is a Ghost, the root is relayed to the owning Arbiter. The rooted entity's movement is halted — Ghost updates will show velocity zero. Abilities cast by the rooted entity still go through the normal proposal path (they're not suppressed).

## Compiler Requirements

TODO: Designer specifies: CC type (root — movement disable), duration (3s), capability suppression (move only), does NOT interrupt channels, DR category (soft CC? or shared with stun?), tenacity-reducible, cleansable. Compiler also needs to flag movement abilities as "blocked by root" in their ability definitions. This is a cross-cutting concern — every dash/blink ability needs to check for root status.

## Open Questions

- Are roots and stuns in the same DR category or separate categories?
- Does root prevent ALL movement (including knockback from SK-01 Toss) or only voluntary movement?
- Can a rooted entity use a ground-targeted ability at their own feet (SK-03 Terrain Wall)?
- Does root affect summoned minions (SK-06) — are they rooted too, or only the caster?
- How does root interact with SK-04 Tether distance check — if one partner is rooted and the other walks away, does the tether snap?
- If a rooted entity is inside SK-08 Aura, does the root prevent them from leaving (they're stuck in the damage zone)?
- Does root affect vertical displacement (SK-01 Toss airborne arc) or only horizontal movement?
