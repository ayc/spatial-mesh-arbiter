# SK-09: Chain Lightning

## Designer Intent

On hit, my attack has a 30% chance to arc lightning to the nearest enemy within range. Each arc
deals reduced damage (70% of the previous arc) and can chain to another nearby enemy. Maximum 5
bounces. An enemy can only be hit once per chain.

## Primitive Composition

P-32 (Actor Spawning) → P-11 (N-Nearest Neighbor) → P-35 (On-Hit Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Triggering hit event
- Initial struck target
- Caster's offensive stats

## Observable Behavior

1. A normal hit lands on the initial target.
2. There is a 30% proc chance to begin a lightning chain.
3. The chain jumps to the nearest eligible enemy within the authored arc range.
4. Each jump deals 70% of the previous jump's damage.
5. The chain continues up to 5 bounces or until no eligible next target exists.
6. A given enemy can be hit at most once per chain.
7. Visual presentation may render one lightning segment per jump.

## Engine Primitives Required

Chain Lightning is the canonical `on_hit + propagation(mode = bounce_nearest)` reference.

The recommended lowering is:

- one passive/on-hit trigger with:
  - `hook = on_hit`
  - `effects = [lightning damage payload]`
  - `propagation = {`
    `mode = bounce_nearest,`
    `base_chance = 0.30,`
    `max_generations = 5,`
    `effect_multiplier_per_generation = 0.70,`
    `query_radius = ... ,`
    `max_targets_per_generation = 1,`
    `filter = enemy_alive,`
    `dedup_scope = entity_once_per_chain`
    `}`

This keeps the mechanic inside the canonical propagation surface:

- the root hit is ordinary damage
- propagation carries the stable `chain_id`, current generation, and visited-target set
- nearest-target selection is handled by the compiled `bounce_nearest` query rule
- damage falloff is the canonical `effect_multiplier_per_generation`, not a sketch-local formula

## Cross-Boundary Concerns

Chain Lightning follows the canonical propagation relay contract.

1. The root `on_hit` trigger fires on the owner of the target that just took the original hit.
2. That owner runs the nearest-target query locally, including Ghost candidates.
3. If the selected next target is remote, the child arc is relayed with the same `chain_id`,
   incremented generation, and visited-set metadata to that target's owner.
4. The next owner resolves the child damage locally and, if the generation limit has not been
   reached, repeats the same nearest-target query for the following jump.
5. Because the visited set is part of the relayed propagation metadata, the chain cannot bounce
   back onto a target it already hit just because authority changed.

## Compiler Requirements

Designer specifies:

- proc chance
- arc range
- max bounces
- base lightning damage payload
- per-generation damage falloff

Compiler emits:

- one `on_hit` trigger
- one `PropagationBlock(mode = bounce_nearest)`
- one visited-target dedup set with `entity_once_per_chain`
- one ordinary lightning damage payload as the child effect

Compiler validates:

1. `max_generations > 0`
2. `query_radius > 0`
3. `max_targets_per_generation = 1` for `bounce_nearest`
4. `effect_multiplier_per_generation > 0`
5. the chain is bounded through canonical propagation metadata rather than an ad hoc proc-depth
   counter

## Resolved Interaction Notes

- Tie ordering for "nearest enemy" is deterministic: candidates are sorted by `(distance, entity_id)`.
- Each jump is ordinary damage and therefore resolves against the struck target's own defenses,
  shields, evasion rules, and other later hooks.
- The chain stops immediately when no eligible next target exists or when `generation >= max_generations`.
- This reference uses the propagation chain itself as the recursive mechanic. Child lightning hits do
  not start fresh root Chain Lightning trees outside that same bounded `chain_id`.
- Unrelated downstream hooks may still see the child damage if those mechanics are otherwise legal;
  only Chain Lightning's own repeat behavior is governed by this propagation chain.
