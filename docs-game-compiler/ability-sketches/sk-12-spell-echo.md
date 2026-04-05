# SK-12: Spell Echo

## Designer Intent

25% chance when I cast an ability to automatically repeat the same ability immediately at no
resource cost. The echo targets the same target or ground position. The echo can itself echo again
with halved probability (25% -> 12.5% -> 6.25% ...) under a finite deterministic bound.

## Primitive Composition

P-40 (On-Cast Intercept)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- triggering cast event (`on_cast`)
- the public ability that was just admitted
- original target or position snapshot

## Observable Behavior

1. I cast an ability normally.
2. There is a 25% chance to replay that same ability immediately against the same target snapshot
   or cursor-position snapshot.
3. The replay pays no extra resource cost and does not consume a second cooldown.
4. The replay is a full second cast: it may spawn projectiles, apply statuses, or heal/damage just
   like the root cast.
5. Each replayed child has a halved chance to produce the next replay generation.
6. The chain is finite because the compiler requires an explicit max-generation cap even when the
   gameplay copy reads as "theoretically infinite."
7. Visual presentation may render ghostly or mirrored repeat-cast effects.

## Engine Primitives Required

Spell Echo is the canonical `on_cast + propagation(mode = repeat_same_cast)` reference.

The recommended lowering is:

- one passive `on_cast` trigger with:
  - `hook = on_cast`
  - `effects = []`
  - `propagation = {`
    `mode = repeat_same_cast,`
    `base_chance = 0.25,`
    `chance_multiplier_per_generation = 0.5,`
    `max_generations = 8,`
    `replay_targeting = same_snapshot,`
    `repeat_resource_policy = free,`
    `repeat_cooldown_policy = ignore`
    `}`

This keeps the mechanic inside the canonical replay surface:

- the root cast is an ordinary admitted cast
- replayed children re-enter as full casts of the same public `ability_id`
- target entity or ground-position targeting uses the root snapshot, not fresh cursor input
- cost/cooldown bypass is compiler-authored replay policy, not a bespoke refund path

## Cross-Boundary Concerns

Spell Echo follows the canonical replayed-cast authority rules.

1. The echo child is a same-tick Stage 2 replay, not a next-tick PostDamage proc.
2. If the original target is local, the replay follows the ordinary local cast path.
3. If the original target is remote/Ghost, the replay follows the same target-owner relay path as
   the root cast using the stored target snapshot.
4. Ground-targeted casts reuse the original `cursor_position` snapshot exactly; they do not ask the
   Edge Node for a new target point.
5. Later projectile travel, handoff, and hit resolution are ordinary consequences of the replayed
   cast itself. Spell Echo does not need a special projectile lane.

## Compiler Requirements

Designer specifies:

- base echo chance
- per-generation chance decay
- explicit max-generation cap
- whether replayed casts are free and/or ignore cooldown

Compiler emits:

- one passive `on_cast` trigger
- one `PropagationBlock(mode = repeat_same_cast)`
- one replay snapshot containing the root public `ability_id` plus target/cursor envelope

Compiler validates:

1. `max_generations > 0`
2. `effects = []` on the root trigger because the replayed cast itself is the child payload
3. replay bypass is limited to the authored resource/cooldown policy; other legality checks still
   re-run on the replay
4. the mechanic is modeled through canonical replay metadata rather than a bespoke "cast twice"
   ability variant

## Resolved Interaction Notes

- Spell Echo replays on the same tick in Stage 2, not as a later reactive event.
- Replayed casts are full ordinary casts and may therefore create ordinary downstream hit/crit
  effects if those later mechanics are otherwise legal.
- If the replayed cast's target preconditions are no longer valid when the child resolves
  (for example, the target became untargetable or a corpse input was consumed), that replay fails
  cleanly rather than inventing a second fallback rule.
- Echo does not consume a second Edge-ingress token-bucket admission because it is a compiler-owned
  replay of an already admitted cast, not a second player intent.
- The "infinite" geometric tail is intentionally normalized to a finite authored cap in the
  canonical profile.
