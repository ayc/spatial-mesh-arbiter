# SK-114: Piercing Execute

## Designer Intent

I swing my axe at an enemy. If they're below an HP threshold (e.g., 400 HP), they are INSTANTLY KILLED. Not "take 99999 damage" — KILLED. This kill bypasses EVERYTHING: invulnerability, shields, death immunity, death prevention, hit-count shields. Nothing saves them. If they're below the threshold, they die.

## Primitive Composition

P-17 (Conditional Thresholds) → P-24 (Resolution Bypass)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in melee range)

## Observable Behavior

1. Check target's current HP
2. If HP is above threshold: deal normal damage (ability functions as a regular attack)
3. If HP is at or below threshold: TARGET IS INSTANTLY KILLED
4. The kill bypasses: invulnerability (SK-44), death immunity (SK-73), death prevention (SK-93), shields (SK-17, SK-113), deferred resolution (SK-112), all other protective mechanics
5. The kill triggers: on-kill effects (SK-11 On-Kill Cascade), kill credit, HardEvent
6. If the kill succeeds: ability's cooldown is reset (can be used again immediately)
7. Visual: massive executioner axe animation, distinct kill effect (no damage number — just DEAD)

## Engine Primitives Required

Piercing Execute is now a canonical `execute` reference.

The recommended lowering is:

1. emit one hostile `execute` effect with:
   - `target = ...`
   - `hp_threshold = 400`
   - `normal_damage = ...` for the non-execute fallback
   - `reset_cooldown_on_execute = true`
   - `bypass_prevention = true`
2. let the target owner perform the threshold check against the target's ACTUAL current HP
3. if the threshold succeeds, let the runtime emit the canonical `P-24` bypass-marked kill
4. if the threshold fails, let the authored `normal_damage` resolve through the ordinary damage
   pipeline instead

This keeps the mechanic entirely inside the canonical execute surface:

- there is no bespoke "force kill" instruction outside `execute`
- bypass behavior is the authored `bypass_prevention = true` flag
- cooldown reset is part of the same canonical `execute` definition
- the fallback path is ordinary damage, not a second ad hoc branch

## Cross-Boundary Concerns

Piercing Execute follows the canonical target-owner threshold contract.

1. The origin owner may target a Ghost as normal, but it does not decide execute success from
   guessed Ghost HP.
2. The target's current owner performs the authoritative threshold check against the target's actual
   current HP.
3. If the threshold succeeds there, the target owner emits the bypass-marked kill and the execute
   path succeeds.
4. If the threshold fails there, the same target owner resolves the authored fallback
   `normal_damage` instead.
5. Because the decision happens only on target authority, Ghost staleness can never incorrectly
   force an execute kill; at worst, the origin owner proposes an execute attempt that resolves as
   ordinary damage on the target owner.

## Compiler Requirements

Designer specifies:

- melee/targeting admission
- HP threshold
- fallback normal damage
- whether the cooldown resets on execute success
- whether the execute bypasses prevention

Compiler emits:

- one canonical `execute`
- one target-owner threshold check against actual HP
- the bypass-marked kill path when the threshold succeeds
- the fallback damage path when the threshold fails

Compiler validates:

1. the mechanic uses canonical `execute`, not a bespoke death-pipeline hook
2. `hp_threshold >= 0`
3. `reset_cooldown_on_execute` only applies to the execute-success branch
4. `bypass_prevention` is available only through authorized compiled ability definitions

## Resolved Interaction Notes

- The threshold uses actual current HP, not effective HP including shields and not prospective net
  HP after deferred ledger release.
- Untargetable / non-admitted targets such as Burrow or Stasis still cannot be executed because the
  cast must first pass ordinary target admission.
- With `bypass_prevention = true`, the execute bypasses shields, instance barriers, deferred
  ledger, HP floors, death prevention, and other prevention/intermediate-phase protections covered
  by the canonical `P-24` bypass path.
- The execute path still produces real kill credit and normal terminal-death consequences because it
  commits an actual terminal kill, not fake damage.
- If the threshold fails, the ability is just a normal damage ability and does not reset cooldown.
