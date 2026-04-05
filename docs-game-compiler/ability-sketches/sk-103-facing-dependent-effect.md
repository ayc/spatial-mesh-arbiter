# SK-103: Facing-Dependent Effect

## Designer Intent

I unleash a petrifying gaze in a cone in front of me. Enemies FACING me are turned to stone (stunned for 2 seconds). Enemies facing AWAY from me are only slowed (40% for 2 seconds). The effect depends on which direction the target is looking at the moment the ability hits.

## Primitive Composition

P-12 (Facing/Dot-Product Check) → P-17 (Conditional Thresholds)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (cone in front of caster)

## Observable Behavior

1. Cast — cone AoE in front of the caster (like SK-49 Cone Strike)
2. For each enemy hit, check: is the enemy's facing direction toward the caster or away?
3. If facing TOWARD caster (within ~90° of looking at caster): stunned for 2 seconds
4. If facing AWAY from caster (looking away): slowed 40% for 2 seconds
5. The check is instantaneous — based on facing at the moment of impact
6. Duration reduced by Tenacity
7. Subject to Diminishing Returns (SK-28)
8. Visual: enemies facing caster turn to stone, enemies facing away get frost effect

## Engine Primitives Required

Facing-Dependent Effect is now a canonical cone-targeting plus guarded per-target branching
reference.

The recommended lowering is:

1. author one cone snapshot query exactly like `SK-49` for the affected target set
2. apply two mutually exclusive conditional follow-up effects to each admitted target:
   - `condition: { facing_toward: { entity: target, other: caster } }`
     -> `apply_cc(cc_type = stun, category = hard_disable, duration_ticks = 120, ...)`
   - `condition: { not: { facing_toward: { entity: target, other: caster } } }`
     -> one negative slow status using canonical stat layering / soft-disable metadata

This keeps the mechanic inside existing surfaces:

- the cone query is the same canonical targeting shape as `SK-49`
- the per-target branch is a normal conditional effect using `GuardExpr`
- facing checks are already a supported geometric guard, not a new primitive

## Cross-Boundary Concerns

Facing-Dependent Effect is origin-owner admission, target-owner branch resolution.

1. The caster owner performs the cone query against local and Ghost-visible candidates just like
   other short-range AoEs.
2. Remote/Ghost targets are relayed to their authoritative owners with the already-admitted payload.
3. Each remote target owner then evaluates the `facing_toward(target, caster)` guard
   authoritatively when deciding whether that target receives stun or slow.
4. This avoids any need for the origin owner to guess remote facing from Ghost data.

## Compiler Requirements

Designer specifies:

- cone angle / range
- stun duration
- slow amount / duration
- the instantaneous facing condition that selects the branch

Compiler emits:

- one cone-targeting snapshot query
- one guarded stun effect for targets facing the caster
- one guarded slow effect for targets not facing the caster

Compiler validates:

1. the branch conditions are mutually exclusive and cover the admitted target set
2. the stun branch uses canonical `apply_cc`
3. the slow branch uses canonical negative status layering rather than a bespoke slow primitive

## Resolved Interaction Notes

- Different targets in the same cone may receive different branches based on their own facing at
  impact time.
- Unstoppable / Super Armor can block the stun branch through ordinary CC immunity, but the slow
  branch is still a normal debuff unless some other immunity rejects it.
- The facing check is instantaneous at effect resolution; late turning before impact can change the
  outcome.
- This sketch does not require a `docs-core/` expansion. The compiler already treats facing guards
  as a supported conditional-effect input.
