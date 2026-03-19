# SK-16: Holy Ground

## Designer Intent

I place a healing zone on the ground. All allies standing inside it are healed every second for 8 seconds. The zone is stationary — allies must stay inside to receive healing. Enemies are not affected.

## Primitive Composition

P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer) → P-15 (Value Modification)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Healing zone appears at target position (circular, fixed radius)
2. Every 1 second: all allies inside the zone are healed for X HP
3. Allies entering the zone mid-duration begin receiving heals on the next pulse
4. Allies leaving the zone stop receiving heals immediately
5. Zone persists for 8 seconds then fades
6. Multiple healing zones can overlap — healing stacks
7. Visual: glowing circle on the ground, pulse effect on each heal tick

## Engine Primitives Required

TODO: This is a ZoneActor (similar to SK-08 Aura) but targeting allies and applying healing instead of damage. The zone needs to perform a spatial query each pulse for "allied entities within radius." How does the Arbiter distinguish ally from enemy? Is this a faction/team field on the entity? How does heal resolution differ from damage resolution — does it go through the same combat pipeline (Phase 1/Phase 2) or is there a separate heal path?

## Cross-Boundary Concerns

TODO: Allies near an Arbiter boundary who are Ghosts — can they receive healing? Ghost entities are read-only projections (position, velocity, radius). If an ally Ghost is standing in the healing zone, the zone's Arbiter needs to relay a heal event to the Ghost's owning Arbiter. This mirrors the damage relay path but for healing. Is the relay structure the same (MeshInternalEvent with a heal payload)?

## Compiler Requirements

TODO: Designer specifies: zone radius, pulse interval (1s), duration (8s), heal amount per pulse, target filter (allies only). Compiler produces: ZoneActor definition with pulse behavior, targeting filter, heal payload. How does the compiler express "allies only" as a targeting filter? Is it an enum (ALLIES, ENEMIES, ALL) or something more complex (faction-based)?

## Open Questions

- Does the healing zone heal the caster if they stand in it?
- Can enemies destroy or dispel the zone?
- Does healing interact with SK-17 Sacrifice Shield — does healing restore shield HP or only real HP?
- How does overhealing work — is it wasted, or does it convert to a temporary shield?
- Does the zone pulse on placement (tick 0) or only after the first interval (tick 60)?
- How does Kinematic Dilation affect the pulse interval — does it heal slower in dilated zones?
- Performance: in a large group fight with multiple overlapping healing zones, how many spatial queries per tick?
