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

1. 5 mines are placed in a predefined pattern (pentagon? line? random within radius?)
2. Mines are invisible to enemies (unless they have detection/true sight)
3. Each mine arms after 1 second (cannot detonate during arming)
4. When any enemy entity enters an armed mine's trigger radius: mine detonates
5. Detonation deals AoE damage to all enemies within blast radius (larger than trigger radius)
6. Each mine detonates independently — one detonation does not chain to others unless enemies are pushed into them
7. Undetonated mines persist for 60 seconds then despawn
8. Mines are visible to the caster and allies
9. Visual: subtle shimmer for allies, invisible to enemies, explosion on detonation

## Engine Primitives Required

TODO: Each mine is a **dormant actor** with a proximity trigger. The Arbiter needs to:
1. Spawn 5 entity-like actors at calculated positions
2. Each has a state machine: `ARMING (1s) → ARMED → DETONATED / EXPIRED`
3. While ARMED: check each tick if any enemy entity is within trigger radius
4. On trigger: perform AoE spatial query within blast radius, apply damage to all results, transition to DETONATED, despawn

The proximity check is the performance concern — 5 mines × 60Hz × up to 60 seconds = checking proximity against all nearby enemies continuously. Is this a spatial index query or brute force? Does the Arbiter batch mine proximity checks?

## Stealth/Visibility

TODO: Mines are invisible to enemies. The engine needs a **visibility system** — entities can have a stealth flag that makes them invisible to the opposing team. Detection abilities (true sight) can reveal stealthed entities. How is visibility implemented:
- Arbiter-level: mines are present in the entity map but filtered from downstream payloads to enemy Edge Nodes?
- Client-level: mines are sent to all clients but the client hides them based on visibility rules?
- Server authoritative visibility is safer (anti-cheat) but means the Arbiter must track per-team visibility.

## Cross-Boundary Concerns

TODO: If mines are placed near an Arbiter boundary, enemy entities approaching from the neighbor's side are Ghosts. The mine's Arbiter needs Ghost positions to check proximity. If the Ghost triggers a mine, the detonation damage relays to the Ghost's owning Arbiter. Long-lived mines (60 seconds) might outlast topology changes — if the Arbiter splits, do mines transfer to the child that inherits their position?

## Compiler Requirements

TODO: Designer specifies: mine count (5), placement pattern, arming delay (1s), trigger radius, blast radius, damage, mine lifetime (60s), visibility (invisible to enemies), detonation behavior (one-shot). Compiler produces: mine actor definitions with state machine + proximity trigger + AoE detonation + stealth flag + lifetime timer. The compiler needs to validate that the mine count is bounded and the proximity check is feasible.

## Open Questions

- Is the mine placement pattern deterministic (fixed pentagon) or has randomness (random within radius)?
- Can mines be placed on top of each other?
- Can allies trigger mines accidentally (friendly fire)?
- Can enemies destroy mines if they have detection (attack the mine)?
- Do mines have HP, or are they invulnerable until triggered/expired?
- Does mine detonation trigger on-hit procs for the caster (SK-09 Chain Lightning)?
- Can mine damage crit?
- How do mines interact with SK-31 Vortex — can enemies be pulled onto mines?
- Do mines count toward entity_count for split trigger purposes?
- How does the 60-second lifetime interact with entity handoff during topology changes?
- Performance: many casters placing mines = many dormant actors doing proximity checks every tick
