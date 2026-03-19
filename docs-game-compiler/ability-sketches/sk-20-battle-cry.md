# SK-20: Battle Cry

## Designer Intent

I shout, granting all allies within radius +20% attack speed and +15% movement speed for 8 seconds. The buff is applied at cast time — allies who enter the radius later do not receive it.

## Primitive Composition

P-09 (Shape Overlap Query) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (AoE centered on caster)

## Observable Behavior

1. Cast — spatial query for all allies within radius at this instant
2. Each ally in range receives +20% attack speed buff (8 seconds)
3. Each ally in range receives +15% movement speed buff (8 seconds)
4. Allies who move out of range keep the buff for its full duration
5. Allies who enter range after the cast do NOT receive the buff
6. The caster also receives the buff
7. Buff has independent expiry per recipient (all expire 8 seconds after application)
8. Visual: war cry animation, speed lines on buffed allies

## Engine Primitives Required

TODO: Single spatial query at cast time for "allies within radius." Apply buff to each result. Unlike SK-08 Aura (continuous) or SK-16 Holy Ground (zone with enter/leave), this is a snapshot — query once, apply, done. The buff is a stat modifier on each target's SoftState (attack speed multiplier, movement speed multiplier). How are multiplicative buffs evaluated — applied to base stats? Stacked multiplicatively with other buffs? Additive within category?

## Cross-Boundary Concerns

TODO: Allies near the Arbiter boundary who are Ghosts — can they receive the buff? The caster's Arbiter does the spatial query and finds Ghost allies. It needs to relay "apply buff" to each Ghost's owning Arbiter. Multiple relays fan out simultaneously. If 20 allies are in range and 8 are Ghosts across 3 Arbiters, that's 8 cross-boundary buff application messages.

## Compiler Requirements

TODO: Designer specifies: target filter (allies), radius, buff effects (+20% attack speed, +15% movement speed), duration (8s), snapshot (not continuous). Compiler produces: spatial query definition + buff application payload + expiry timer. The compiler needs to distinguish "snapshot AoE" from "persistent zone" (SK-08/SK-16).

## Open Questions

- Does the buff stack with itself if two supports both cast Battle Cry?
- Is there a buff cap (e.g., max +60% attack speed from all sources)?
- How are percentage-based buffs evaluated — additive with other percentage buffs, or multiplicative?
- Does the buff persist through death and revival (SK-18)?
- Can enemies dispel the buff from affected allies?
- Does Kinematic Dilation affect the buff duration (dilated = buff lasts longer in real time but same in game ticks)?
- How does the 8-second expiry interact with status effect evaluation order per tick?
- Performance: if cast in a 200-player zerg, the spatial query + 200 buff applications + N cross-boundary relays — is this bounded?
