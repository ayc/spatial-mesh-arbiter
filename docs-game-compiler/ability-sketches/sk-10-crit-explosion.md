# SK-10: Crit Explosion

## Designer Intent

When I land a critical hit, an explosion erupts at the target's position dealing AoE damage to all
enemies within radius. The explosion damage can itself critically strike, triggering another
explosion at each crit target's position. Damage diminishes with each generation.

## Primitive Composition

P-37 (On-Crit Hook) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Triggering crit event
- Target position where the crit landed
- Caster's offensive stats

## Observable Behavior

1. A critical hit lands on the original target.
2. An explosion is centered on that target's position and damages enemies within radius.
3. Each explosion hit rolls its own crit chance through the ordinary damage pipeline.
4. Any explosion hit that crits becomes the center of a child explosion.
5. Each generation deals less damage than the previous generation.
6. The cascade is bounded to a finite maximum generation count.
7. Visual presentation may render simultaneous branching explosions through dense groups.

## Engine Primitives Required

Crit Explosion is the canonical `on_crit + propagation(mode = fanout_query)` reference.

The recommended lowering is:

- one passive/on-crit trigger with:
  - `hook = on_crit`
  - `effects = [aoe_damage(center = target_position, shape = circle, radius = ..., ...)]`
  - `propagation = {`
    `mode = fanout_query,`
    `base_chance = 1.0,`
    `max_generations = ...,`
    `effect_multiplier_per_generation = 0.50,`
    `query_radius = ... ,`
    `max_targets_per_generation = ... ,`
    `filter = enemy_alive,`
    `dedup_scope = entity_once_per_chain`
    `}`

This keeps the mechanic inside the canonical propagation surface:

- the root crit is ordinary damage
- the explosion itself is ordinary `aoe_damage` centered on `target_position`
- recursive child explosions are bounded by propagation `chain_id` / generation metadata
- generation-based damage decay uses `effect_multiplier_per_generation`

## Cross-Boundary Concerns

Crit Explosion follows the canonical propagation fan-out contract.

1. The root `on_crit` trigger fires on the authoritative owner of the critted target.
2. That owner resolves the first explosion locally from the target's committed position.
3. If any child explosion centers belong to remote/Ghost endpoints, the corresponding child
   generation is relayed with the same `chain_id` and incremented generation metadata to the
   relevant owners.
4. Each owner runs its own local AoE query and resolves child explosion damage only against its own
   authoritative entities.
5. A cascade near a seam can therefore fan out across multiple Arbiters, but every local explosion
   still follows the single-authority rule.

## Compiler Requirements

Designer specifies:

- explosion radius
- base explosion damage payload
- max generations
- per-generation damage falloff
- target cap / filter for each child fan-out step

Compiler emits:

- one `on_crit` trigger
- one `PropagationBlock(mode = fanout_query)`
- one ordinary explosion `aoe_damage` payload centered on `target_position`
- one bounded propagation chain with generation scaling and per-chain dedup

Compiler validates:

1. `max_generations > 0`
2. `query_radius > 0`
3. `max_targets_per_generation > 0`
4. `effect_multiplier_per_generation > 0`
5. the recursion bound is expressed through canonical propagation metadata rather than an unbounded
   proc tree

## Resolved Interaction Notes

- Each explosion hit is ordinary damage and therefore rolls crit and resolves defenses normally on
  the struck target.
- Multiple crits from the same explosion may spawn child generations in parallel; they still share
  the same bounded `chain_id`.
- This reference uses `entity_once_per_chain` to stop one cascade from repeatedly revisiting the
  same enemy.
- The explosion is centered on `target_position` exactly as resolved by the engine plane, not on a
  snapped grid cell.
- Child explosion hits may still participate in unrelated downstream hooks if those mechanics are
  otherwise legal; Crit Explosion's own recursion remains bounded by its propagation metadata.
