# SK-59: Oil Ignite

## Designer Intent

I drop an oil spill on the ground that slows enemies who walk through it. I can reactivate the ability to ignite the oil — transforming the zone from a slow field into a fire zone that deals heavy damage. The fire burns for a duration then the zone disappears.

## Primitive Composition

P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-64 (Combo Field × Finisher Matrix)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)
- Reactivation input (same ability key, while oil zone is active)

## Observable Behavior

1. Cast — oil zone appears at target position (circular, fixed radius)
2. **Oil phase:** Enemies inside are slowed by 40%. No damage. Oil persists until ignited or expired (8 seconds).
3. Reactivate — oil ignites, transforming into fire
4. **Fire phase:** Enemies inside take X fire damage per second. Slow is removed (fire doesn't slow). Fire lasts 4 seconds.
5. If not reactivated: oil evaporates after 8 seconds with no fire phase
6. Oil can also be ignited by any fire ability passing through it (SK-30 Trail of Fire, fire projectiles)
7. Visual: dark oil pool → reactivation → blazing fire

## Engine Primitives Required

### Zone State Machine

This is the first zone with **multiple behavioral states**. The ZoneActor has a state machine:

```
enum OilZoneState {
    Oil { slow_pct: SimFixed, expires_at_tick: u64 },
    Fire { dps: SimFixed, expires_at_tick: u64 },
    Expired,
}
```

State transitions:
- `Oil → Fire`: on caster reactivation or on contact with a fire-typed ability
- `Oil → Expired`: on oil timer expiry (8s without ignition)
- `Fire → Expired`: on fire timer expiry (4s after ignition)

Each state has different per-pulse behavior:
- Oil: apply slow to enemies inside (no damage)
- Fire: apply damage to enemies inside (no slow)

### External Ignition Trigger

The oil zone can be ignited by OTHER abilities — not just the caster's reactivation. Any fire-typed ability that intersects the oil zone triggers the transition. This means:
- Projectiles (fire arrows) passing through the oil
- SK-30 Trail of Fire deposited on the oil
- Other fire AoE zones overlapping

The Arbiter needs to detect "a fire-typed effect intersected this oil zone" and trigger the state transition. This is **inter-ability interaction** — one ability's effect modifies another ability's zone state.

### Reactivation Targeting a Zone

Like SK-36 Shadow Step (reactivate to return) and SK-41 Detonation Arrow (reactivate to detonate), the caster needs a reference to the active zone for reactivation:

```
status_effect: OilIgniteLink {
    zone_id: EntityID,
    can_ignite: bool,
}
```

## Cross-Boundary Concerns

TODO: The oil zone is a stationary entity on the Arbiter where it was placed. Standard zone cross-boundary patterns apply (Ghosts in the zone receive effect relays). The external ignition trigger adds complexity: if a fire projectile from a neighboring Arbiter crosses the boundary and enters the oil zone, the oil's Arbiter needs to detect the intersection and trigger ignition. Does the fire projectile's handoff include "I'm fire-typed" metadata that the receiving Arbiter checks against active oil zones?

## Compiler Requirements

TODO: Designer specifies: zone with two phases (oil: slow 40%, 8s duration; fire: X DPS, 4s duration), caster reactivation triggers phase change, external fire ignition triggers phase change, targeting filter (enemies). Compiler produces:
- ZoneActor with state machine (Oil → Fire → Expired)
- Per-state pulse behavior (slow vs damage)
- Reactivation link on caster
- External trigger: fire-typed ability intersection
- Ability type tags ("fire") that the compiler can reference for interaction rules

The compiler needs to support **ability type tags** (fire, ice, poison, etc.) and **inter-ability interactions** ("fire abilities ignite oil zones").

## Open Questions

- Can multiple oil zones exist simultaneously from the same caster?
- Can an ally's fire ability ignite the oil (friendly ignition)?
- Does the fire phase benefit from the caster's spell power / offensive stats?
- Can enemies ignite the oil with their own fire abilities (turning your zone against you)?
- Does the zone block projectiles in either phase?
- Can the fire phase trigger SK-02 Poison Shot's DoT refresh (fire damage counts as "damage from caster")?
- Does the oil phase slow flying/displaced entities (SK-01 Toss passing through oil)?
- How does the zone interact with SK-03 Terrain Wall — can you wall enemies inside burning oil?
- Performance: checking every fire-typed effect against every active oil zone per tick — is this bounded?
