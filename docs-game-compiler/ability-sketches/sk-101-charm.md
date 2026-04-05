# SK-101: Charm

## Designer Intent

I blow a kiss that charms an enemy. For 1.5 seconds, the charmed enemy walks directly toward me uncontrollably. They can't attack, cast, or choose their direction — they're just drawn to me. This sets up follow-up abilities by bringing the enemy into my range.

## Primitive Composition

P-03 (Trajectory Steering) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the charm source)
- Target enemy entity (hit by skillshot or targeted)

## Observable Behavior

1. Ability hits enemy — charm applied for 1.5 seconds
2. Charmed enemy walks directly toward the caster at reduced speed (normal move speed or reduced)
3. Charmed enemy cannot attack, cast, or control their movement
4. The walk direction updates based on the caster's CURRENT position (if caster moves, the charmed entity follows)
5. Duration reduced by Tenacity
6. Subject to Diminishing Returns (SK-28) — hard CC category
7. Cleansable by SK-15 Purify
8. Visual: hearts floating above the charmed enemy, dreamy walk animation

## Engine Primitives Required

Charm is now a canonical `apply_cc(cc_type = charm)` reference.

The recommended lowering is:

1. on hit, apply one generated CC status with:
   - `cc_type = charm`
   - `category = forced_movement`
   - `duration_ticks = 90`
   - `dr_category = hard_disable`
   - `duration_scaling = status_resistance`
   - `is_cleansable = true`
2. let the canonical charm profile handle the runtime behavior:
   - suppress attacks and casts
   - emit deterministic `P-03` steering toward the source each tick
   - keep the steering direction source-relative rather than snapshotted once at admission

This keeps the mechanic inside existing surfaces:

- charm is already a first-class canonical `cc_type`
- forced approach uses the same source-relative steering family as fear
- no bespoke charm-only status shape or movement override is needed

## Cross-Boundary Concerns

Charm is target-owner authoritative after admission.

1. The hit target's current owner admits the generated CC status and executes the steering there.
2. If the charm source is remote, the target owner reads the source's current local-or-Ghost pose
   each tick and steers toward that authoritative/replicated position.
3. If the charmed target hands off mid-charm, the generated status transfers with them and the new
   owner continues the same source-relative steering.
4. Remote damage or cleanse that removes the status follows the ordinary target-owner status path;
   there is no charm-specific relay family.

## Compiler Requirements

Designer specifies:

- hostile target
- charm duration
- whether the effect is cleansable
- whether standard status-resistance scaling applies

Compiler emits:

- one canonical `apply_cc` using `cc_type = charm`
- one generated forced-movement CC status with source-relative steering

Compiler validates:

1. `category = forced_movement` for charm
2. `dr_category = hard_disable` for this reference
3. the approach behavior is authored through canonical `apply_cc`, not a bespoke steering status

## Resolved Interaction Notes

- SK-15 Purify can remove the charm because the generated CC status is cleansable in this
  reference.
- Unstoppable / Super Armor style CC immunity can reject charm admission through the ordinary
  category-immunity path.
- Other movement constraints such as `SK-88 Positional Leash` still apply after charm steering,
  because those clamps run later in PostKinematic unless they explicitly opt out.
- Charm can pull the target across Arbiter boundaries; if that movement crosses a seam, the normal
  handoff path carries the generated CC state with it.
