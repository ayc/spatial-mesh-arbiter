# SK-100: Ally-Untargetable

## Designer Intent

My character is a massive dragon that is PERMANENTLY immune to all crowd control. However, as a tradeoff, my allies CANNOT target me with any beneficial effects — no heals, no shields, no buffs, no cleanses. I'm on my own. I must self-sustain through my own abilities. Enemies can target and damage me normally.

## Primitive Composition

P-27 (Targetability Overrides) → P-62 (Categorized CC Immunity)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- No input (permanent passive trait)

## Observable Behavior

1. Permanent: always immune to all CC (stuns, roots, silences, slows, fear, taunt, displacement, sleep — everything)
2. Permanent: allies cannot target me with beneficial effects (heals, shields, buffs, cleanses all fail)
3. Enemies CAN target and damage me normally (I'm not invulnerable)
4. I CAN target allies with my own abilities (if I have ally-targeted abilities)
5. I have my own self-sustain abilities to compensate for lack of ally healing
6. This is my identity — it's always on, cannot be toggled off
7. Visual: massive model, no healing indicators from allies, self-sufficient aesthetic

## Engine Primitives Required

Ally-Untargetable is now a canonical entity-definition `targetability_policy` plus passive CC
immunity reference.

The recommended lowering is:

1. author permanent base targeting on the entity definition:
   - `targetability_policy = {`
     `hostile_effects = true,`
     `allied_beneficial_effects = false,`
     `allied_harmful_effects = true,`
     `self_effects = true`
     `}`
2. add one permanent passive status to the entity with
   `cc_immunity_categories = [displacement, hard_disable, soft_disable, forced_movement, target_override, mute]`

This keeps the mechanic inside existing surfaces:

- ally-beneficial rejection is the canonical relation-scoped targetability policy
- enemies can still target and damage the entity normally because `hostile_effects` remains true
- self-targeted abilities still work because `self_effects` remains true
- permanent CC immunity is just a passive status using the same category-based immunity surface as
  temporary Unstoppable-style effects

## Cross-Boundary Concerns

Ally-Untargetable uses the ordinary target-owner admission path.

1. The entity's permanent `targetability_policy` lives on the authoritative owner and transfers with
   the entity like any other base definition data.
2. Cross-boundary ally heals, buffs, shields, and cleanses deterministically fail at target
   admission when they reach that owner, because `allied_beneficial_effects = false`.
3. If local Ghost-side metadata already exposes the same base targetability profile, origin owners
   may prune some attempts earlier, but correctness does not depend on that optimization.
4. Hostile effects continue to resolve normally across boundaries because the hostile channel stays
   enabled.

## Compiler Requirements

Designer specifies:

- permanent ally-beneficial lockout
- whether hostile effects remain legal
- whether self-effects remain legal
- the permanent CC-immunity category set

Compiler emits:

- one entity-definition `targetability_policy`
- one permanent passive status granting the authored `cc_immunity_categories`

Compiler validates:

1. `allied_beneficial_effects = false` while `hostile_effects = true` and `self_effects = true`
   for this reference
2. the CC immunity is expressed through passive status metadata, not a bespoke hardcoded
   "always unstoppable" switch
3. the mechanic stays relation-scoped; it does not imply general invulnerability or general ally
   invisibility

## Resolved Interaction Notes

- The entity can still target itself because `self_effects = true`.
- Team-agnostic or hostile non-CC effects still work normally if they do not use the allied
  beneficial channel.
- `SK-91 Team-Agnostic Stasis` is not exempted by this trait because stasis is a harmful suspension,
  not an allied beneficial effect and not one of the canonical CC categories.
- Passive auras or outbound support from this entity to allies are unaffected. The lockout applies
  to incoming allied beneficial admission on this entity.
