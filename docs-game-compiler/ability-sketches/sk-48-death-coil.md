# SK-48: Death Coil

## Designer Intent

I cast a projectile at a target. If the target is an enemy, it deals damage. If the target is an ally, it heals them instead. Same ability, same cooldown, same projectile — different effect based on who I'm targeting.

## Primitive Composition

P-17 (Conditional Thresholds) → P-21 (Value Conversion)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target entity (enemy OR ally — player chooses)

## Observable Behavior

1. Cast on an enemy: projectile launches, on hit deals X damage
2. Cast on an ally: projectile launches, on hit heals for Y HP
3. Can also cast on self: heals self for Y HP (projectile is instant / zero travel time to self)
4. Same cooldown regardless of target type
5. Same resource cost regardless of target type
6. Visual: dark projectile when targeting enemy, green projectile when targeting ally

## Engine Primitives Required

Death Coil is now a canonical any-target ability using the bounded procedural fallback for
relation-conditional resolution.

The recommended lowering is:

1. author `targeting = { type = single_target, filter = all_alive, range = ... }`
2. spawn one projectile shell or use an instant self-hit path when `target = caster`
3. on resolution, branch through the canonical pure relation predicate:
   - `if target_is_hostile(caster, target)` → resolve the damage payload
   - `else` → resolve the heal payload
4. the hostile branch may continue through the ordinary damage / prepared-hit pipeline
5. the allied/self branch resolves as an ordinary heal event instead of building a CombatContext

This keeps the mechanic inside the current compiler profile:

- any-target admission is already expressible through `filter = all_alive`
- relation-dependent branching is allowed through the bounded Lua fallback surface
- the two outcome payloads still use ordinary canonical `damage` and `heal` effects

## Cross-Boundary Concerns

Death Coil uses the ordinary hostile-vs-allied split.

1. If the target is a hostile Ghost/remote entity, the caster owner takes the hostile branch and
   resolves the cast through the normal damage/prepared-hit pipeline.
2. If the target is an allied Ghost/remote entity, the caster owner takes the heal branch and emits
   the same kind of target-owner heal resolution used by other remote allied heals.
3. Relation checks happen before branch selection, so the damage path only builds hostile combat
   context when the target is actually hostile.
4. Self-target is the trivial same-owner allied branch and may skip visible projectile travel if
   the presentation wants an instant self-hit.

## Compiler Requirements

Designer specifies:

- any-target range
- damage payload for hostile targets
- heal payload for allied/self targets
- projectile presentation and self-target presentation
- shared cooldown / shared resource cost

Compiler emits:

- one any-target ability definition (`filter = all_alive`)
- one bounded relation check using `target_is_hostile`
- one hostile damage branch
- one allied/self heal branch

Compiler validates:

1. the base targeting filter admits both allies and enemies
2. the relation branch stays inside the bounded procedural fallback surface rather than inventing a
   second hidden ability identity
3. cooldown and resource cost remain shared regardless of which branch resolves

## Resolved Interaction Notes

- The damage branch is ordinary hostile damage and therefore participates in later hostile/on-hit
  consumers the same way other projectile damage does.
- The heal branch is ordinary healing and therefore participates in heal-side consumers such as
  healing mirrors when those mechanics are otherwise valid.
- Untargetable allies such as Burrowed units remain illegal targets because targetability admission
  happens before the relation branch resolves.
- Any living entity admitted by `filter = all_alive` is legal. If the design wants "heroes only,"
  that must be layered through a narrower target filter or additional predicate logic.
- Relation is evaluated at resolution time, so if a target's allegiance has changed (for example via
  a control/inversion mechanic), the branch follows the CURRENT relation rather than the relation at
  cast start.
- Presentation may vary by branch, but that is downstream/UI policy. The gameplay contract is only
  that the same public ability ID resolves as damage for hostile targets and healing for allied
  targets.
