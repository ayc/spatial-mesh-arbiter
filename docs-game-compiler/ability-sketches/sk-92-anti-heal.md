# SK-92: Anti-Heal

## Designer Intent

I throw a grenade at a target area. Enemies hit receive a debuff that reduces all healing they receive by 100% for 2 seconds. Allies hit receive a buff that increases healing received by 25% for 2 seconds. The grenade itself deals damage to enemies and heals allies.

## Primitive Composition

P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted)

## Observable Behavior

1. Grenade lands at target position — AoE affects all entities in radius
2. Enemies: take damage + receive "Healing Blocked" debuff (100% healing reduction, 2 seconds)
3. Allies: receive heal + receive "Healing Amplified" buff (25% bonus healing, 2 seconds)
4. While Healing Blocked: any heal on the target is reduced to 0 (DoT heals, direct heals, passive heals — all blocked)
5. While Healing Amplified: any heal on the target is increased by 25%
6. Both effects are cleansable by SK-15 Purify
7. Visual: purple anti-heal indicator on enemies, green amplification glow on allies

## Engine Primitives Required

Anti-Heal is now a canonical stat-layering reference.

The recommended lowering is:

1. resolve one ground-targeted AoE using the same relation-branching pattern as `SK-48`
2. on hostile hits:
   - deal ordinary AoE damage
   - apply one negative `healing_blocked` status with:
     - `stat_modifiers = [{ stat = healing_received_multiplier, op = mul, value = 0.0 }]`
     - `duration_ticks = 120`
     - `is_cleansable = true`
3. on allied hits:
   - resolve one ordinary AoE heal
   - apply one positive `healing_amplified` status with:
     - `stat_modifiers = [{ stat = healing_received_multiplier, op = mul, value = 1.25 }]`
     - `duration_ticks = 120`
     - `is_cleansable = true`

This keeps the mechanic inside existing surfaces:

- incoming-heal modification is ordinary `P-16` stat layering on the canonical incoming-heal
  effectiveness stat
- the grenade's mixed ally/enemy behavior is just relation-branching AoE resolution
- no bespoke heal-hook system is needed because ordinary heal resolution already reads the target's
  current compiled stats

## Cross-Boundary Concerns

Anti-Heal is target-owner authoritative after admission.

1. The grenade owner runs the AoE query using local and Ghost poses, then relays admitted remote
   targets through the ordinary target-owner path.
2. Each target owner applies the local damage / heal payload and admits the matching anti-heal or
   amplification status there.
3. Every later incoming heal on that target is already local to the target owner, so the
   `healing_received_multiplier` check is completely local after the status has been admitted.
4. HP overwrites or other non-heal rewrites are unaffected because they do not use the ordinary heal
   pipeline.

## Compiler Requirements

Designer specifies:

- target position
- AoE radius
- hostile damage amount
- hostile healing reduction amount and duration
- allied heal amount
- allied healing amplification amount and duration
- whether the statuses are cleansable

Compiler emits:

- one relation-branching area effect
- one negative anti-heal status definition using `stat_modifiers`
- one positive healing-amplification status definition using `stat_modifiers`

Compiler validates:

1. the anti-heal multiplier is clamped into the ordinary non-negative heal-resolution range
2. incoming-heal modification is expressed through canonical stat modifiers, not a bespoke
   "on_heal" callback path
3. the hostile and allied branches remain deterministic relation filters on the same AoE event

## Resolved Interaction Notes

- Lifesteal, drain, HoTs, direct heals, and pickup heals are all affected because they use the
  ordinary heal pipeline.
- `restore_from_state` and other HP overwrite mechanics are not heals and therefore are unaffected.
- `death_prevention` bypasses anti-heal by default unless that status explicitly opts out of the
  bypass.
- This reference assumes one non-stacking anti-heal and one non-stacking amplification status per
  source application. Designers who want stacking author it explicitly through ordinary status rules.
