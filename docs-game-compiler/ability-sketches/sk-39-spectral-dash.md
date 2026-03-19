# SK-39: Spectral Dash

## Designer Intent

I send a wave of banshees forward in a line. The wave travels as a projectile. At any point while the wave is in flight, I can reactivate to instantly teleport to the wave's current position. If I don't reactivate, the wave dissipates at max range and nothing happens.

## Primitive Composition

P-07 (Entity-as-Kinematic-Volume) → P-27 (Targetability Overrides)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (from requested aim direction)
- Reactivation input (same ability key, while wave is in flight)

## Observable Behavior

1. Cast — wave launches from caster in the specified direction
2. Wave travels forward at a constant speed (like a projectile, but passes through enemies without hitting)
3. While the wave is in flight: ability icon changes to "Teleport" — pressing it teleports the caster to the wave's current position
4. If reactivated: caster disappears and appears at the wave's position instantly. Wave dissipates.
5. If not reactivated: wave reaches max range and dissipates. Ability goes on cooldown.
6. The wave does not deal damage or interact with entities — it's purely a mobility tool
7. Visual: ghostly banshee wave traveling forward, caster dissolves and reforms at the wave on reactivation

## Engine Primitives Required

### Moving Bookmark (Projectile as Destination)
Unlike SK-36 Shadow Step (static bookmark at cast position), the bookmark here is a **live projectile** whose position changes every tick. The caster needs a reference to the projectile actor to query its current position on reactivation.

```
status_effect: SpectralDashLink {
    wave_projectile_id: EntityID,  // Reference to the live projectile
    can_reactivate: bool,
}
```

The projectile is a `ProjectileActor` with special properties:
- No collision with entities (passes through everything)
- No damage payload
- Optional collision with static geometry (does the wave stop at walls?)
- Provides its position to the caster's reactivation logic

### Reactivation Targeting a Moving Entity
When the caster reactivates, the engine must:
1. Look up the wave projectile by `wave_projectile_id`
2. Read its CURRENT position (which has changed since cast)
3. Snap the caster to that position (instant teleport, same as SK-35/SK-36)
4. Despawn the wave projectile

This is a new interaction: an ability that targets one of the caster's own active projectiles, not an enemy entity or a ground position.

## Cross-Boundary Concerns

TODO: The wave projectile might have crossed an Arbiter boundary while in flight (standard projectile handoff). If the caster reactivates after the wave crossed a boundary:
1. The caster is on Arbiter A
2. The wave is now on Arbiter B (after handoff)
3. Reactivation requires: reading the wave's position from Arbiter B, then teleporting the caster from A to B

This is an **indirect cross-boundary teleport** — the caster doesn't directly choose to go cross-boundary, they follow their projectile which happened to cross. The caster's Arbiter needs to know where the projectile currently is, even though the projectile might have been handed off. Does the caster's Arbiter maintain a reference to the handed-off projectile's current Arbiter?

## Compiler Requirements

TODO: Designer specifies: wave speed, wave max range, wave collision rules (pass through entities, stop at walls?), reactivation (teleport to wave position), no damage. Compiler produces:
- ProjectileActor definition with no damage payload and no entity collision
- Status effect on caster linking to the projectile
- Multi-phase ability: Phase 1 (launch wave), Phase 2 (teleport to wave)
- Projectile despawn on reactivation or max range

The compiler needs to express "this projectile is a mobility tool, not a weapon" — no CombatContext, no offensive stats baked in.

## Open Questions

- Does the wave pass through SK-03 Terrain Walls, or does it stop (and the caster can teleport to the wall)?
- Can the caster be CC'd (stun/root) and still reactivate? Root blocks movement — is teleporting "movement"?
- If the wave is in flight and the caster dies, does the wave persist (allowing a revived caster to teleport)?
- Does the teleport trigger SK-32 Minefield at the destination?
- Can enemies see the wave (revealing the potential teleport destination)?
- If the wave crosses a boundary and gets handed off, how does the caster's Arbiter track the wave's current position for reactivation?
- What happens if the wave is mid-handoff (in the 3-phase protocol) when the caster reactivates?
- Can the caster cast other abilities while the wave is in flight (wave doesn't lock the caster)?
- Does the wave have a collision radius, or is it a point? If the caster teleports to it, do they appear at the wave's center or its front edge?
