# SK-115: Corpse Economy

## Designer Intent

When enemies die, they leave corpses on the ground. My class has multiple abilities that CONSUME corpses for different effects. Corpse Explosion detonates a corpse for AoE damage. Raise Skeleton consumes a corpse to summon a minion. Corpse Lance fires projectiles from corpse positions. Each ability eats one corpse. Corpses are a spatial resource — where they are matters, and managing them is core to my gameplay.

## Primitive Composition

P-39 (On-Death Hook) → P-47 (Spatial Corpse Registry) → P-11 (N-Nearest Neighbor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Dead enemy entities leave corpse objects at their death position
- Caster chooses which ability to use on/near a corpse
- Each ability consumes one or more corpses

## Observable Behavior

1. Enemy dies → corpse object appears at death position
2. Corpse persists for 30 seconds (or until consumed)
3. **Corpse Explosion**: target a corpse → it explodes dealing AoE damage scaled by the dead enemy's max HP
4. **Raise Skeleton**: target a corpse → it's consumed, a skeleton minion spawns at the corpse position
5. **Corpse Lance**: target an enemy → the nearest N corpses each launch a projectile at the target, each corpse consumed
6. Each corpse can only be consumed ONCE (first ability to use it claims it)
7. Multiple corpses from a big fight = more resources to spend
8. Visual: corpse objects on ground (bone piles, bodies), consumed with appropriate effect (explosion, skeleton rising, projectile launching)

## Engine Primitives Required

Corpse Economy is now a canonical corpse-profile plus `consume_corpse` reference.

The canonical contract is:

1. qualifying entity types define a `corpse_profile` so terminal death creates corpse-registry
   entries with retained death position and any needed stat snapshots
2. corpse-consuming abilities use `consume_corpse` to:
   - choose a corpse explicitly (`selection = target`)
   - choose the nearest corpses to the caster/target/position
   - optionally bind corpse position and retained corpse stats into downstream effects
3. child effects then consume those bindings to produce different outcomes:
   - Corpse Explosion: damage/aoe centered on `bind_position_as`
   - Raise Skeleton: `spawn_actor` at `bind_position_as`, scaling from `bind_stats`
   - Corpse Lance: select `count = N` corpses and emit one projectile/effect chain per corpse

This keeps the entire mechanic inside existing corpse surfaces:

- corpses are not a bespoke second resource type outside the corpse registry
- multiple different abilities can consume the same corpse class through their own authored
  `consume_corpse` blocks
- corpse-derived position and stat snapshots are canonical bindings, not ad hoc effect-local data
- atomic first-claim-wins contention is already part of `consume_corpse`

## Cross-Boundary Concerns

Corpse Economy follows the current canonical corpse rule: corpse access is local to the death
Arbiter.

1. `consume_corpse` query modes read only the CURRENT Arbiter's authoritative corpse registry.
2. Remote/Ghost corpse access fails cleanly rather than relaying a corpse claim across Arbiters.
3. Atomic corpse claim happens before child effects execute, so a corpse can feed at most one
   successful consuming branch even under local contention.
4. Once a corpse is successfully selected and claimed, corpse-derived bindings such as death
   position and retained stats are immutable snapshots for that effect execution.

## Compiler Requirements

Designer specifies:

- which entity types produce corpse records
- corpse persistence duration and retained snapshot fields
- per-ability corpse selection mode, range, count, and filter
- which corpse stats/position bindings each consuming ability needs
- whether each ability actually consumes the corpse or only reads it

Compiler emits:

- corpse-bearing entity definitions through `corpse_profile`
- per-ability `consume_corpse` blocks with deterministic query/claim semantics
- downstream effect chains that read corpse position/stat bindings for explosion, summon, or
  projectile outcomes

Compiler validates:

1. corpse-consuming queries use canonical dead/corpse filters
2. query modes supply required `range` / `center` / `count` fields
3. requested corpse stat bindings are unique within one `consume_corpse` block
4. remote/Ghost corpse consumption is not authored under the current canonical profile

## Resolved Interaction Notes

- Only entity types with a qualifying `corpse_profile` create usable corpse records. This sketch
  does not imply "all deaths always leave corpses."
- `SK-107 Corpse Possession` competes for the same local corpse registry. The first successful
  consumer claim wins; later contenders fail cleanly.
- Corpse-derived stat scaling uses the retained corpse snapshot chosen by the entity's corpse
  profile, not a live pointer into the dead entity.
- Corpse Lance and other multi-corpse consumers use deterministic `(distance, corpse_id)` ordering
  when selecting more than one corpse.
- Corpse lifetime is ordinary corpse-profile persistence in simulation ticks, so Kinematic Dilation
  does not create a separate corpse-expiry time base.
