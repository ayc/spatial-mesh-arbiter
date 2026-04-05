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
9. Duration reduced by Tenacity / status resistance
10. Treated as a soft-disable movement debuff for ordinary cleanse / immunity handling
11. Cleansable by SK-15 Purify
12. Visual: metal post + chain, chain pulls taut when target reaches the edge

## Engine Primitives Required

Positional Leash is now a canonical status-owned `movement_constraint` reference.

The recommended lowering is:

1. on hit, write the target's current position into one runtime bookmark such as `leash_anchor`
2. apply one negative leash status to the target with:
   - `movement_constraint = {`
     `anchor_state = leash_anchor,`
     `max_distance = 3.0,`
     `on_violation = clamp,`
     `apply_to_forced_movement = true,`
     `apply_to_teleports = true`
     `}`
   - `cc_category = soft_disable`
   - `duration_scaling = status_resistance`
   - `is_cleansable = true`
3. let the runtime enforce the clamp in PostKinematic using the stored bookmark instead of creating
   a bespoke leash primitive

This keeps the mechanic inside the canonical compiler surface:

- the anchor is just a stored bookmark, not a second required entity
- the leash radius is the authored `max_distance`
- voluntary movement, forced displacement, sweeps, and teleports are all constrained because the
  reference keeps both movement-class flags enabled
- the clamp happens after committed movement for the tick, matching the canonical `P-04` contract

## Cross-Boundary Concerns

Positional Leash is target-owner authoritative.

1. The hit owner's current Arbiter snapshots the target's committed world position into the leash
   bookmark and admits the negative status there.
2. If the leashed entity later hands off, the status and bookmark transfer as ordinary SoftState.
   The new owner continues enforcing the same clamp locally; there is no shared leash object.
3. The bookmark stores an absolute world position, so topology changes and split/merge events do
   not change the leash center.
4. Because the clamp is evaluated only on the authoritative owner in PostKinematic, Ghosts never
   enforce or guess the final leash result locally.

## Compiler Requirements

Designer specifies:

- melee-range hostile target
- leash radius
- duration
- whether the anchor is the target's current position
- cleanse / status-resistance behavior

Compiler emits:

- one bookmark write capturing the target's current position
- one negative status carrying the canonical `movement_constraint`
- ordinary runtime status metadata for cleanse / status-resistance handling

Compiler validates:

1. the authored anchor state references a bookmark of kind `position`
2. `max_distance > 0`
3. the reference uses canonical `movement_constraint`, not a bespoke leash primitive or a second
   movement-resolution pass

## Resolved Interaction Notes

- This reference clamps blinks, dashes, pulls, fears, teleports, and other displacement the same
  way it clamps voluntary movement because both movement-class flags remain enabled.
- SK-15 Purify can remove the leash because it is an ordinary cleansable negative status.
- Unstoppable / Super Armor style CC immunity can block leash admission when they reject
  `soft_disable` effects through the canonical status-immunity path.
- The base reference uses a stored anchor position only. A destroyable leash post is a later
  variant, not part of this baseline sketch.
