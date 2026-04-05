# SK-06: Summon Swarm

## Designer Intent

My character summons 6 small minions around me. Each minion autonomously attacks the nearest enemy for 15 seconds, then expires. If I move, they follow me. If I die, they die.

## Primitive Composition

P-32 (Actor Spawning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (minions spawn around caster position)

## Observable Behavior

1. 6 minion entities spawn in a circle around the caster
2. Each minion acquires the nearest enemy and attacks autonomously (basic melee/ranged attack)
3. Minions follow the caster if no enemy is in range
4. Minions have their own HP and can be killed
5. After 15 seconds, surviving minions expire and despawn
6. If the caster dies, all minions immediately die
7. Each minion's attack deals damage and can trigger on-hit effects from the caster's stats

## Engine Primitives Required

Summon Swarm is now a canonical multi-spawn autonomy pattern.

The recommended lowering is:

1. one `spawn_actor` effect with:
   - `count = 6`
   - `position = caster_position`
   - `placement.offsets` containing the authored ring pattern around the caster
   - `lifetime_ticks = 900`
   - `instance_limit = { scope = owner_ability, max_live = 6, overflow = replace_oldest }`
2. one minion archetype with HP, movement speed, basic attack, and ordinary hostile targetability
3. `autonomy = {`
   `engage_filter = enemy_alive,`
   `engage_radius = ... ,`
   `attack_mode = basic_attack_only,`
   `idle_mode = follow_owner,`
   `follow_distance = ... ,`
   `on_owner_removed = die`
   `}`

This keeps the minions inside the canonical spawned-actor autonomy contract. Each minion is an
ordinary spawned actor with one deterministic FSM:

- idle near owner
- acquire nearest hostile within engage radius
- chase / basic-attack
- return to follow-owner idle behavior when no target is engaged

The minions use their own archetype stats and ability list. If the game wants caster-scaling
minions, that scaling must be baked into the archetype or authored through other canonical stat /
loadout projection surfaces rather than through implicit summon magic.

## Cross-Boundary Concerns

Summon Swarm follows the ordinary independent spawned-actor boundary model.

1. Each minion is its own authoritative spawned actor. They do not hand off as a single "swarm
   group."
2. `idle_mode = follow_owner` samples the owner's current local-or-Ghost position each tick, so if
   the owner crosses a seam the minions continue following through the same local/Ghost tracking
   path used by other follow-owner autonomy.
3. Any minion that physically crosses a boundary hands off independently through ordinary spawned-
   actor handoff. Some minions may hand off while others remain local; there is no swarm-local
   special case.
4. If a minion attacks a Ghost/remote target, the minion's current owner emits the ordinary hostile
   relay toward the target's authoritative owner.
5. The six minions are just six ordinary additional entities for density / split-threshold
   accounting. There is no special exemption for summons.

## Compiler Requirements

Designer specifies:

- minion archetype
- summon count and placement pattern
- lifetime
- hostile acquisition filter / radius
- follow-owner idle distance
- per-owner live-count policy

Compiler emits:

- one multi-spawn `spawn_actor`
- one ability-local `placement` ring
- one autonomy block using the canonical follow / acquire / chase / attack FSM
- one per-owner live-count rule to keep summon flooding bounded

Compiler validates:

1. `count <= max_spawns_per_rule`
2. `count = len(placement.offsets)`
3. `engage_radius > 0`
4. `follow_distance >= 0`
5. the summon uses canonical `spawn_actor.autonomy` rather than a bespoke NPC commander loop

## Resolved Interaction Notes

- Minions count as ordinary entities for density and split-threshold accounting while alive.
- Minions are normal targetable bodies with normal collision / pathing policy unless their archetype
  explicitly changes that.
- This reference uses a per-owner live cap of 6 with oldest-first replacement, so recasting does
  not create unbounded summon stacking.
- Owner death kills the minions immediately through `on_owner_removed = die`.
- The old ARPG "Commander Pattern" is not a separate compiler concern here; the minions are just
  spawned actors using the existing bounded autonomy FSM.
