# SK-42: Withering Fire

## Designer Intent

I have 5 charges of a rapid-fire arrow attack. Each press fires one arrow at the nearest enemy hero (auto-targeted). Charges recharge independently — one charge every 8 seconds. I can dump all 5 rapidly for burst damage, then wait for them to recharge.

## Primitive Composition

P-42 (Stacking Counters w/ Decay) → P-11 (N-Nearest Neighbor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (auto-targets nearest enemy hero within range)

## Observable Behavior

1. Press ability — one arrow fires at the nearest enemy hero within range
2. Arrow is instant (hitscan or very fast projectile — no meaningful travel time)
3. Arrow deals X damage to the target
4. One charge is consumed (5 max charges)
5. Can be pressed rapidly — fire all 5 in quick succession (no cooldown between charges, just a minimum interval like 0.15s)
6. Charges recharge independently: one charge every 8 seconds
7. Charge recharge timer starts when a charge is consumed, not when all charges are spent
8. If no enemy hero is in range: ability fails / fires at nearest non-hero enemy
9. Visual: rapid arrow shots, charge counter UI element

## Engine Primitives Required

### Charge-Based Cost System
All existing abilities use one of:
- **Cooldown:** cast → wait N seconds → cast again
- **Resource:** cast costs X mana/energy → regenerate resource over time

Charges are a third model:
```
struct ChargeState {
    current_charges: u8,
    max_charges: u8,
    recharge_interval_ticks: u64,      // Ticks per charge recharge
    recharge_timers: Vec<u64>,         // Independent timer per depleted charge
    min_use_interval_ticks: u64,       // Minimum ticks between successive uses
    last_use_tick: u64,
}
```

Each time a charge is consumed, a recharge timer starts. Multiple timers can run simultaneously (if 3 charges are used, 3 timers tick independently). When a timer completes, one charge is restored.

This is fundamentally different from cooldowns because:
- You can use the ability N times before waiting
- Recharging is per-charge, not per-ability
- Using one charge doesn't reset other recharge timers

Where does ChargeState live — on the entity's SoftState as an ability-specific field? As a status effect? As part of the ability definition at runtime?

### Auto-Targeting
The caster doesn't specify a target — the engine selects one. Selection logic:
1. Query all enemy heroes within range
2. Select the nearest one (by distance to caster)
3. If no heroes: optionally fall back to nearest non-hero enemy
4. If no enemies at all: ability fails (charge NOT consumed)

The auto-target selection must be deterministic — if two enemies are equidistant, the tie-break must produce the same result on every Arbiter (e.g., lowest EntityID wins).

### Rapid-Fire Rate Limiting
The minimum interval between uses (0.15s = 9 ticks) prevents the player from dumping all 5 in a single tick. The Arbiter must enforce this interval even if the client sends 5 proposals simultaneously. This interacts with the per-entity token bucket — does each charge use consume a token?

## Cross-Boundary Concerns

TODO: The auto-targeting spatial query considers enemies within range of the caster. Enemies near the boundary are Ghosts. If the nearest enemy is a Ghost, the arrow targets the Ghost and damage is relayed to the Ghost's owning Arbiter. Since this ability can fire 5 times rapidly, it could generate 5 cross-boundary damage relays in quick succession.

Also: the auto-target selection on the caster's Arbiter uses Ghost positions, which may be slightly stale (dead-reckoned). The "nearest" enemy might not actually be nearest if Ghost position data is lagging. Is this acceptable, or does it cause noticeable mis-targeting?

## Compiler Requirements

TODO: Designer specifies: max charges (5), recharge time per charge (8s), minimum use interval (0.15s), damage per shot, auto-target (nearest enemy hero, fallback to non-hero), range. Compiler produces:
- Ability definition with charge cost model (not cooldown, not resource)
- Auto-target selection function (nearest hero, deterministic tie-break)
- Rapid-fire interval enforcement
- ChargeState as part of the entity's runtime ability state

The compiler needs to support a third cost model alongside cooldown and resource. The ability definition format must express: `cost_type: Charges { max: 5, recharge: 8s, min_interval: 0.15s }`.

## Open Questions

- Do charges recharge while dead?
- Does the recharge timer pause during CC (stun/silence)?
- Can SK-12 Spell Echo trigger on a charge-based ability (echo doesn't consume a charge — is that valid)?
- Does each arrow independently roll crit, or do all 5 share a crit determination?
- Can each arrow trigger on-hit procs (SK-09 Chain Lightning per arrow)?
- If the auto-targeted enemy dies between the ability press and the arrow arriving, does the arrow retarget?
- Does the minimum use interval interact with attack speed buffs (SK-20 Battle Cry)?
- How does the charge counter display synchronize between Edge Node prediction and Arbiter authority?
- Can charges be partially refunded (e.g., caster is silenced after using 2 charges — do the remaining 3 stay)?
- Performance: 5 rapid spatial queries (one per shot for auto-targeting) in 0.75 seconds — bounded?
