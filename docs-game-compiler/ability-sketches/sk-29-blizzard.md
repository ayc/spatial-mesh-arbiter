# SK-29: Blizzard

## Designer Intent

I cast a snowstorm at a target position. The storm persists for 8 seconds. Every second, enemies inside take cold damage and are slowed by 30%. The storm is stationary — I can walk away and it keeps going.

## Primitive Composition

P-32 (Actor Spawning) → P-09 (Shape Overlap Query) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Storm zone appears at target position (circular, fixed radius)
2. Every 1 second: all enemies inside take X cold damage
3. Every 1 second: all enemies inside receive 30% movement slow (refreshed each pulse, effectively permanent while inside)
4. Enemies entering mid-duration begin taking damage/slow on the next pulse
5. Enemies leaving the zone lose the slow after it expires (1-2 seconds)
6. Caster is free to move and act after casting — zone is independent
7. Zone persists for 8 seconds then dissipates
8. Visual: swirling snow/ice effect within the zone boundary

## Engine Primitives Required

TODO: This is the canonical ZoneActor — a stationary, independent actor that runs its own tick loop. Each pulse: spatial query for "enemies within radius," apply damage + apply slow debuff to each. The ZoneActor has its own lifecycle (spawn tick, expiry tick), its own CombatContext (caster's offensive stats baked in at cast time), and its own pulse timer. How does the ZoneActor relate to the caster — does it retain a reference to the caster's EntityID for kill credit? What if the caster dies — does the zone persist?

## Enter/Leave Detection

TODO: The zone needs to track who is currently inside for two reasons:
1. Only pulse entities that are inside (not re-apply to entities who already left)
2. The slow debuff needs cleanup when an entity leaves

Is this a set of EntityIDs maintained per-zone that is diffed each pulse? Or does each pulse do a fresh spatial query and apply effects without tracking membership? If fresh query: the slow from the previous pulse might still be active when the entity leaves, giving a trailing slow. If tracked: the zone maintains state and explicitly removes the slow on leave.

## Cross-Boundary Concerns

TODO: The zone is placed at a position that might be near an Arbiter boundary. Enemies in the zone might be Ghosts owned by a different Arbiter. Each pulse that hits a Ghost generates a damage relay to the Ghost's owning Arbiter. With 8 pulses over 8 seconds and potentially many Ghosts, this is a steady stream of cross-boundary traffic. What if the zone straddles a boundary — part of the radius is in one Arbiter's region, part in another? Can a zone exist in two Arbiters simultaneously, or must it be owned by one?

## Compiler Requirements

TODO: Designer specifies: zone shape (circle), radius, pulse interval (1s), duration (8s), damage per pulse, damage type (cold), debuff per pulse (30% slow, 1-2s duration), targeting filter (enemies). Compiler produces: ZoneActor definition with pulse behavior, targeting filter, damage payload, debuff payload, lifecycle timer. This should be a common pattern — many abilities are variations of "place zone, pulse effects."

## Open Questions

- Does the zone damage the caster's allies if they stand in it (friendly fire)?
- Does the zone interact with SK-03 Terrain Wall — can you wall enemies inside a blizzard?
- If the caster dies, does the zone persist for its full duration?
- Does each pulse roll crit independently, or is crit determined at cast time?
- Can enemies block (SK-21) or evade individual pulses?
- Does the slow from each pulse stack with itself (30% + 30% = 60%) or refresh (always 30%)?
- How does Kinematic Dilation affect pulse interval — do pulses happen slower in dilated zones?
- Can the zone be dispelled or destroyed by enemies?
- Does the zone count as an entity for Arbiter entity_count / split trigger purposes?
