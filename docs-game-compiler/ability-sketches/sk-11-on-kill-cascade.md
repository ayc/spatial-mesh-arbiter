# SK-11: On-Kill Cascade

## Designer Intent

When I kill an enemy, an explosion of dark energy erupts from the corpse dealing AoE damage to
nearby enemies. I also gain a 10% damage buff for 5 seconds. If the explosion kills another enemy,
it triggers again, creating a bounded chain reaction through tightly packed groups.

## Primitive Composition

P-39 (On-Death Hook) -> P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- terminal death event with attributed `killer_entity`
- `death_position` of the killed entity
- killer's current offensive stats

## Observable Behavior

1. An enemy dies with kill credit attributed to me.
2. A corpse burst damages nearby enemies around that corpse's death position.
3. I gain a 10% damage buff for 5 seconds; later qualifying kills refresh that same window.
4. If the corpse burst kills another enemy, that later death emits its own corpse burst.
5. Later generations continue until no more qualifying kills occur or the authored generation cap
   is reached.
6. Each child burst still resolves as ordinary hostile damage on the struck target.
7. Visual presentation may render a ripple of explosions through a dense pack.

## Engine Primitives Required

On-Kill Cascade is the canonical killer-attributed `on_death` plus bounded corpse-burst reference.

The recommended lowering is:

1. one killer-owned passive death trigger that matches only deaths whose `killer_entity` resolves
   to the passive owner and applies one refresh-style `kill_cascade_buff` to `killer_entity`
2. one sibling killer-owned passive death trigger on the same attribution rule with:
   - `hook = on_death`
   - `propagation = {`
     `mode = fanout_query,`
     `max_generations = ... ,`
     `query_radius = ... ,`
     `max_targets_per_generation = ... ,`
     `filter = enemy_alive,`
     `dedup_scope = entity_once_per_chain`
     `}`
   - child damage payloads emitted from `death_position`
3. author `kill_cascade_buff` as one positive status with:
   - `max_stacks = 1`
   - `duration_ticks = 300`
   - one offensive stat modifier worth +10% damage

This keeps the mechanic inside existing surfaces:

- kill attribution comes from the canonical `killer_entity` binding on terminal death
- the buff is an ordinary refresh-style positive status on the killer
- the corpse burst is just bounded propagation from `death_position`
- recursion is carried by canonical `chain_id` / generation metadata rather than a bespoke corpse
  loop

## Cross-Boundary Concerns

On-Kill Cascade follows the canonical death-owner plus propagation relay story.

1. The dying entity's current owner is authoritative for terminal death, `death_position`, and
   `killer_entity`.
2. If the killer is remote, the killer buff is relayed to the killer's owner as an ordinary
   targeted status application.
3. The corpse-burst query runs from `death_position` on the dead entity's owner.
4. Local results are resolved locally; remote/Ghost results are relayed with the same `chain_id`,
   generation, and visited-set metadata.
5. Later generations use whatever killer buff state is committed by the time their child events
   re-enter. Already emitted child branches do not retroactively resnapshot after a later kill.

## Compiler Requirements

Designer specifies:

- whether the passive listens to all attributed kills or some narrower filter
- corpse-burst radius and damage payload
- maximum propagation generations and per-generation target cap
- buff magnitude, duration, and refresh behavior
- whether one chain may hit one entity more than once

Compiler emits:

- one killer-attributed `on_death` buff trigger
- one killer-attributed `on_death` burst trigger
- one `PropagationBlock(mode = fanout_query)` for the burst chain
- one refresh-style positive killer buff status

Compiler validates:

1. the mechanic keys off canonical `killer_entity` attribution rather than a bespoke kill detector
2. `query_radius > 0`
3. `max_generations > 0`
4. the buff is modeled as an ordinary positive status, not inline mutation of the killer's offense
5. the recursion bound is expressed through propagation metadata rather than an unbounded proc tree

## Resolved Interaction Notes

- This reference uses a refresh-style buff (`max_stacks = 1`), not unbounded per-kill stacking.
- Only deaths with actual kill attribution to the passive owner count. Environmental or unattributed
  deaths do not trigger it.
- Multi-kill same-tick bursts may refresh the killer buff multiple times, but they do not
  retroactively rescale already emitted sibling branches.
- Each child burst hit is ordinary damage and therefore still respects the struck target's shields,
  mitigation, death prevention, and later DeathCheck behavior.
- The burst chain keeps the original killer credit unless some later independent source lands the
  terminal blow first.
