# SK-76: Build Zone

## Designer Intent

I place pylons that generate a power field around them. My turret structures can ONLY be placed within a pylon's power field. If a pylon is destroyed, any turrets in its field that are no longer covered by another pylon also shut down. The pylon network defines where I can build.

## Primitive Composition

P-08 (Dynamic Collision Injection) → P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Pylon placement: caster entity + target position (ground-targeted)
- Turret placement: caster entity + target position (must be within a pylon's power field)

## Observable Behavior

1. Place Pylon — creates a power field (visible circle on the ground)
2. Pylon has HP, can be destroyed by enemies
3. Place Turret — can ONLY be placed within a pylon's power field radius
4. If turret placement target is outside all power fields: placement fails (error message)
5. Turret auto-attacks nearby enemies while in a powered field
6. If the pylon powering a turret is destroyed AND no other pylon's field covers the turret: turret deactivates (stops attacking, loses shield, but doesn't die immediately — can be re-powered by placing a new pylon)
7. Multiple pylons' fields can overlap — turrets in overlap zones are safe if any one pylon survives
8. Visual: blue power field circles, turrets glow when powered, dim when depowered

## Engine Primitives Required

Build Zone is now a canonical `spawn_actor.coverage` provider/consumer reference.

The recommended lowering is:

1. pylon placement spawns one stationary provider actor that authors:
   - `coverage = { mode = provider, network_id = pylon_power, radius = ..., member_filter = ... }`
2. turret placement spawns one stationary consumer actor that authors:
   - `coverage = { mode = consumer, network_id = pylon_power, require_for_spawn = true, unpowered_mode = dormant }`
   - ordinary stationary summon AI / auto-attack behavior while powered
3. the coverage registry handles:
   - placement denial when no provider covers the requested spawn point
   - repowering when a new provider appears
   - depowering when the last covering provider disappears

This keeps the mechanic inside the canonical spawned-actor and coverage-network surfaces:

- pylons are just spawned provider actors
- turrets are just spawned consumer actors
- overlap safety is the ordinary "at least one admitted provider covers this consumer" rule
- depowered behavior reuses canonical dormancy / suspension rather than a bespoke build graph

## Cross-Boundary Concerns

Coverage is already defined as a single-authority cross-boundary registry.

1. Provider actors publish their coverage disc from their current position.
2. Consumer owners evaluate powered state from local providers plus Ghost-backed provider poses with
   the same `network_id`.
3. A pylon near a seam may therefore still power a turret across the boundary without introducing a
   shared mutable field object.
4. On provider spawn, removal, handoff, or position change, consumer owners recompute powered state
   through the canonical coverage contract.

## Compiler Requirements

Designer specifies:

- pylon HP and coverage radius
- turret HP and stationary attack behavior
- whether turret spawn requires live coverage
- whether unpowered turrets become `dormant` or `suspended`

Compiler emits:

- one provider spawn profile for pylons
- one consumer spawn profile for turrets
- ordinary stationary summon AI for the powered turret
- optional live-count caps if the design wants bounded pylon/turret counts per owner

Compiler validates:

1. provider `radius > 0`
2. provider `member_filter` is present
3. turret placement uses `require_for_spawn = true` in this reference
4. the powered/depowered rule is expressed through canonical coverage + dormancy/suspension, not a
   bespoke dependency-graph subsystem

## Resolved Interaction Notes

- Overlapping pylons work automatically because any one covering provider keeps the turret powered.
- Destroying one pylon only depowers a turret if no other provider in the same network still covers
  it.
- Re-power is automatic when a new pylon enters coverage; the turret does not need a second spawn
  or rebuild step.
- This reference uses `unpowered_mode = dormant`, so a depowered turret stops acting and its
  powered passives/shields pause through the existing suspension contract.
- Pylons and turrets remain ordinary spawned actors and therefore count toward the same spawned-actor
  limits and entity-load considerations as other placed structures.
