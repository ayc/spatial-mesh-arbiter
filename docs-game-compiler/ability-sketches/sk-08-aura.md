# SK-08: Aura

## Designer Intent

Passive ability: enemies within a radius around my character take X damage per second and have their movement speed reduced by 20%. The effect applies as long as they are within range and ends when they leave. No activation required — always on while the ability is equipped/toggled.

## Primitive Composition

P-06 (Attached Kinematics) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (passive — no explicit activation)
- No target required (affects all enemies in radius)

## Observable Behavior

1. Enemies entering the aura radius receive a debuff: damage per second + 20% movement slow
2. Enemies leaving the aura radius lose the debuff immediately
3. Damage ticks once per second on each affected enemy
4. The aura moves with the caster
5. No cast time, no cooldown, no resource cost (passive)
6. The aura can be visually indicated (ground effect around caster)

## Engine Primitives Required

TODO: This is a continuous spatial query — every tick (or at some cadence), the Arbiter queries "which enemy entities are within radius R of the caster?" and applies/removes the debuff. Is this a ZoneActor attached to the caster (mobile zone)? Or is it processed differently — a per-entity check during the tick? How does enter/leave detection work — tracking a set of "currently affected" entities and diffing each tick?

## Cross-Boundary Concerns

TODO: Near an Arbiter boundary, some enemies in the aura radius will be Ghosts. The aura damage needs to relay to their owning Arbiter. If the caster moves along a boundary, entities constantly enter/leave Ghost status while inside the aura. How frequently do Ghost-targeted aura damage relays fire? This could generate significant cross-boundary traffic under density.

## Compiler Requirements

TODO: How does the designer express "passive, always-on, radius R, apply debuff to enemies in range"? What runtime structure does this compile into — a ZoneActor definition attached to the caster? A special tick-phase entry? How does the compiler validate the performance bounds of a continuous spatial query?

## Open Questions

- What is the tick cadence for the spatial query — every frame (60Hz) or once per second (matching the damage tick)?
- Does the aura affect stealthed/invisible enemies?
- Can the aura be temporarily disabled (e.g., silenced)?
- Is there a maximum number of entities the aura can affect simultaneously (bounded for performance)?
- How does this interact with Kinematic Dilation — if the zone is dilated, does the damage tick slower?
- Does the slow stack with other movement speed debuffs, and is there a movement speed floor?
- Performance: in a Blackhole scenario with 200+ enemies in range, what is the cost per tick of the spatial query + debuff application + cross-boundary relays?
