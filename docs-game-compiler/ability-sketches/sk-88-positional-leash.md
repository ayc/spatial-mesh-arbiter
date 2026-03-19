# SK-88: Positional Leash

## Designer Intent

I slam a post into the ground next to an enemy hero, chaining them to it. For 3 seconds, the enemy can move freely within the chain's radius — but if they try to move beyond the radius, they're yanked back to the edge. They can fight, cast, and act normally within the area. They just can't leave.

## Primitive Composition

P-04 (Positional Clamping) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in melee range)

## Observable Behavior

1. Cast on enemy at melee range — a post is placed at the target's current position
2. Chain connects the target to the post
3. The target CAN move freely within the chain's radius (e.g., 3 meters)
4. The target CAN attack, cast abilities, and use items normally
5. If the target attempts to move beyond the chain radius: movement is clamped to the edge
6. The target CANNOT dash, blink, or teleport beyond the radius (forced movement is also constrained)
7. The chain persists for 3 seconds
8. The post has no HP and cannot be destroyed (in base version)
9. Duration reduced by Tenacity
10. Subject to Diminishing Returns (SK-28) — soft CC category
11. Cleansable by SK-15 Purify
12. Visual: metal post + chain, chain pulls taut when target reaches the edge

## Engine Primitives Required

### Bounded Movement Constraint

This is a fundamentally new movement constraint — not a disable (root), not a reduction (slow), but a **spatial boundary**:

```
status_effect: PositionalLeash {
    anchor_position: Vec2F,     // Where the post was placed
    max_radius: SimFixed,       // Chain length
    expires_at_tick: u64,
}
```

Each tick during `apply_kinematics` for the leashed entity:
1. Calculate the entity's new position after movement input
2. Check: is the new position within `max_radius` of `anchor_position`?
3. If yes: allow the movement normally
4. If no: clamp the position to the nearest point on the radius boundary

```
fn apply_leash_constraint(entity_pos: &mut Vec2F, anchor: Vec2F, max_radius: SimFixed) {
    let delta = *entity_pos - anchor;
    let distance = delta.magnitude();
    if distance > max_radius {
        *entity_pos = anchor + delta.normalize() * max_radius;
    }
}
```

### Constraining All Movement Types

The leash must constrain ALL forms of movement:
- Voluntary movement (WASD/click-to-move): clamped at boundary
- Dashes (SK-34 Charge): dash stops at the boundary
- Blinks (SK-35 Blink Strike): teleport destination clamped to within radius
- Forced movement (SK-78 Fear flee): flee clamped at boundary
- SK-31 Vortex pull: can pull within the leash area but not beyond it

The constraint is applied AFTER all movement calculations, as a final position clamp. It overrides the result of any movement, regardless of source.

### Interaction With Displacement

What about abilities that forcibly move the leashed entity beyond the boundary?
- SK-01 Toss: the toss destination is beyond the leash → clamped? Or does toss override the leash?
- SK-43 Drag: dragged beyond leash radius → clamped? Or drag pulls them free?
- SK-84 Temporal Trap: forced teleport to a stored position → clamped or override?

Design choice: does the leash constrain ALL movement absolutely (nothing can move you beyond it), or can certain "override" abilities break through?

If the leash is absolute: it's a spatial invariant that the kinematics system enforces.
If certain abilities override: the leash must have a priority system (can be broken by ultimate abilities?).

### Anchor Entity

The post/anchor is a placed object at a fixed position. It could be:
- A simple position stored in the status effect (no physical entity)
- A placed entity with position but no HP/interaction (just a visual marker)
- A placed entity with HP that can be destroyed to free the leashed entity (variant)

The simplest implementation: the anchor is just a Vec2F in the status effect. No entity needed.

## Cross-Boundary Concerns

TODO: The leashed entity is constrained to a radius around the anchor position. If the anchor is near an Arbiter boundary:

1. **Entity tries to cross boundary:** The leash clamps movement at the radius edge, which is before the boundary. The entity CAN'T cross the boundary (they're chained to a point on this side). No handoff occurs.

2. **Anchor ON the boundary:** The leash radius extends into both Arbiters' regions. The entity can move within the radius, potentially crossing the boundary. The leash constraint must work on both Arbiters — if the entity crosses, the new Arbiter must enforce the same leash.

3. **Topology change during leash:** If the anchor position's owning Arbiter changes (split/merge), the leash anchor position stays absolute. The entity's Arbiter enforces the clamp using the stored anchor coordinates.

## Compiler Requirements

TODO: Designer specifies: melee range target, anchor at target's position, chain radius (3m), duration (3s), target can act normally within radius, movement clamped at boundary, affects all movement types, Tenacity-reducible, DR category, cleansable. Compiler produces:
- PositionalLeash status effect with anchor_position + max_radius
- Kinematics post-processing: clamp position within radius after all movement
- Applies to all movement types (voluntary, forced, dash, blink, teleport)
- Anchor as stored position (no separate entity needed)

The compiler adds Leash to the CC/movement-constraint type system alongside Root, Slow, and displacement.

## Open Questions

- Can the leashed entity use SK-35 Blink Strike to teleport to a target outside the radius? (Destination clamped?)
- Does SK-51 Unstoppable prevent the leash (it's a movement constraint — a form of CC)?
- Can the leashed entity be displaced BY ALLIES (SK-01 Toss by ally to save them) — does the leash prevent it?
- If the leash anchor is on one Arbiter and the entity crosses to another, who enforces the clamp?
- Can the post be destroyed (variant with HP)?
- Does the leash affect vertical displacement (SK-01 Toss airborne arc)?
- Can multiple leashes be applied simultaneously? If so, the entity is constrained to the INTERSECTION of both radii.
- Does the leash prevent SK-69 Portal Pair teleportation?
- How does the leash interact with SK-40 Mind Control (forced to walk away → clamped at edge)?
- Does Kinematic Dilation affect the leash duration?
