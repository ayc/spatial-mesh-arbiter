# SK-94: Placed Potion

## Designer Intent

I throw a healing potion on the ground. The potion sits there as a glowing pickup. Any ally who walks over it picks it up and is healed. If nobody picks it up within 20 seconds, it despawns. I can have up to 5 potions on the ground at once. I'm pre-positioning healing for my team.

## Primitive Composition

P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted)

## Observable Behavior

1. Cast — potion appears at target position on the ground
2. Potion is visible to all players (allies see heal amount, enemies see the potion exists)
3. First ally to walk within pickup radius collects it → healed for X HP
4. The collector chooses WHEN to pick it up (by walking over it)
5. Potion persists for 20 seconds if not collected
6. Maximum 5 potions on the ground simultaneously (oldest despawns if 6th is placed)
7. Potions can be placed pre-fight (set up healing stations)
8. Enemies CANNOT pick up or destroy potions (in base version)
9. Visual: glowing flask on the ground, absorption effect on pickup

## Engine Primitives Required

Placed Potion is now a canonical spawned-actor interaction reference.

The recommended lowering is:

1. spawn one stationary potion actor at the target position with:
   - ordinary visible presentation
   - non-hostile, non-blocking base targetability
   - lifetime of 20 seconds
   - `interaction = {`
     `trigger_filter = allies,`
     `trigger_radius = pickup_radius,`
     `resolution_mode = collector_only,`
     `effects = [ heal(amount = X, target = collector) ],`
     `consume_on_trigger = true`
     `}`
   - `instance_limit = {`
     `scope = owner_by_ability,`
     `max_live = 5,`
     `overflow_policy = despawn_oldest`
     `}`
2. let the first allied collector resolve the heal through the ordinary heal pipeline, then remove
   the potion actor

This keeps the mechanic inside existing surfaces:

- the pickup is just one spawned actor with `interaction`
- ally-only collection is the `trigger_filter`
- heal-on-pickup is an ordinary `heal` effect on the collector
- oldest-first overflow is the canonical spawn instance-limit policy

## Cross-Boundary Concerns

Placed Potion is pickup-owner authoritative after trigger admission.

1. The potion actor's current owner runs the proximity trigger each tick using local and Ghost
   collector poses.
2. If the first admitted collector is remote/Ghost, the potion owner emits the ordinary heal effect
   to that collector's current owner and removes the potion only after the trigger commits.
3. `instance_limit` buckets live potion actors by `(owner, ability_id)` across all Arbiters, so the
   oldest-first overflow rule remains deterministic even if a healer has potions in multiple
   regions.
4. Enemies cannot pick up the potion in this reference because they never match the authored
   `trigger_filter`.

## Compiler Requirements

Designer specifies:

- ground-target position
- heal amount
- pickup radius
- lifetime
- ally-only pickup behavior
- per-owner live cap and overflow policy

Compiler emits:

- one spawned potion actor definition with canonical `interaction`
- one canonical `instance_limit` block on that spawned actor
- one ordinary `heal` effect targeting the collector

Compiler validates:

1. `trigger_radius > 0`
2. `max_live = 5` for this reference and `overflow_policy = despawn_oldest`
3. the pickup uses canonical spawned-actor interaction instead of a bespoke item entity loop

## Resolved Interaction Notes

- The caster may collect their own potion because they are included in the allied trigger filter.
- Forced movement can push allies onto a potion, and collection still happens if they enter the
  pickup radius.
- The heal is ordinary healing, so anti-heal and healing amplification modify it normally.
- The base reference gives the potion no hostile interaction surface: enemies can see it, but they
  cannot attack or collect it.
