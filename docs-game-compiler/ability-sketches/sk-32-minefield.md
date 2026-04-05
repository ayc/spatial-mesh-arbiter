# SK-32: Minefield

## Designer Intent

I place 5 invisible mines in a pattern around a target position. Each mine arms after 1 second. When an enemy walks over an armed mine, it detonates dealing AoE damage to all enemies within blast radius. Mines last 60 seconds if not triggered.

## Primitive Composition

P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-52 (Asymmetric Team-Rendering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (ground-targeted, center of mine pattern)

## Observable Behavior

1. 5 mines are placed in one deterministic authored pattern around the target point
2. Mines are invisible to enemies (unless they have detection/true sight)
3. Each mine arms after 1 second (cannot detonate during arming)
4. When any enemy entity enters an armed mine's trigger radius: mine detonates
5. Detonation deals AoE damage to all enemies within blast radius (larger than trigger radius)
6. Each mine detonates independently — one detonation does not chain to others unless enemies are pushed into them
7. Undetonated mines persist for 60 seconds then despawn
8. Mines are visible to the caster and allies
9. Visual: subtle shimmer for allies, invisible to enemies, explosion on detonation

## Engine Primitives Required

Minefield is now a canonical `spawn_actor` trap pattern.

The compiler lowers it to one `spawn_actor` effect with:

1. `count = 5`
2. `placement.offsets` containing the authored deterministic mine pattern around the target point
3. a static mine archetype
4. `lifetime_ticks = 3600`
5. `interaction = { arming_delay_ticks = 60, trigger_filter = enemy_alive, trigger_radius = ...,
   resolution_mode = radius_query, effect_radius = ..., effect_filter = enemy_alive, effects = [...],
   consume_on_trigger = true }`

Each mine is an ordinary spawned actor with one bounded arming/proximity state machine supplied by
`SpawnInteractionBlock`. The mine arms after one second, then runs the canonical `P-14` overlap
check each tick. On the first admitted trigger, it resolves the authored AoE payload from the mine's
current position and consumes itself.

The placement pattern is not random. It is one explicit ordered offset list authored relative to the
requested ground-target anchor, so designers can express a pentagon, line, cross, or any other
bounded fixed layout without bespoke runtime logic.

## Stealth/Visibility

Mines reuse the canonical visibility and targetability surfaces instead of inventing a trap-specific
stealth system.

The mine archetype authors:

1. `observer_presentation` so allies see the mine normally while enemies do not
2. `targetability_policy` if the design wants detected mines to become attackable or interactable
3. optional suspension/dormancy metadata only if the mine should be excluded from specific query
   classes beyond ordinary visibility filtering

So "invisible to enemies unless revealed" is downstream observer filtering plus targetability
policy, not a separate hidden-entity mechanic.

## Cross-Boundary Concerns

Each mine is an ordinary spawned actor with its own authoritative owner.

1. The authored placement offsets expand the target point into five deterministic spawn positions.
2. The mine owner runs the trigger-radius overlap check locally from the mine's current position.
3. If the first admitted trigger entity or any AoE targets are Ghosts, the mine owner emits the
   ordinary target-owner relay payload rather than mutating Ghost state locally.
4. Long-lived mines survive ordinary topology changes through the same spawned-actor handoff rules
   as other `P-32` entities, including preserved owner linkage and expiry tick.

So boundary handling is not bespoke to traps. The mine is just another spawned actor whose trigger
and blast payloads already obey the standard authority model.

## Compiler Requirements

Designer specifies:

- target anchor position
- mine count
- explicit placement offsets relative to that anchor
- mine lifetime
- arming delay
- trigger radius
- blast radius
- hostile filter
- detonation payload
- observer-presentation / targetability policy for mine visibility and reveal behavior

Compiler emits:

- one `spawn_actor` trap effect with `count = 5`
- one ability-local `placement` block carrying the authored offset list
- one ability-local `interaction` block carrying arming, trigger, and detonation policy
- one mine entity archetype with the authored observer/targetability metadata

Compiler validates:

1. `count <= max_spawns_per_rule`
2. `count = len(placement.offsets)`
3. `arming_delay_ticks >= 0`
4. `trigger_radius > 0`
5. `effect_radius > 0` for `radius_query`
6. the mine payload uses ordinary spawned-actor / visibility surfaces rather than sketch-local
   hidden-trap flags

## Resolved Interaction Notes

- Mine placement is deterministic. Designers author explicit offsets; the compiler does not inject
  randomness into the pattern.
- Friendly fire is controlled by the authored trigger/effect filters. This sketch uses enemy-only
  admission.
- Detection/reveal behavior is observer/targetability authoring. If the game wants revealed mines
  to be destroyable, the mine archetype can simply expose enemy targetability once revealed.
- Mine detonation is a normal authored AoE payload. Crit, on-hit hooks, and other combat-side
  behavior follow the same combat contracts as any other hostile effect.
- Mines count as ordinary spawned actors for entity-count and live-limit purposes while they exist.
