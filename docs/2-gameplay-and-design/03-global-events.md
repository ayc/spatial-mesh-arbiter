# Global Event Types (Map-Wide Mechanics)

This document serves as a guide for Game Designers and Gameplay Engineers to create **Global Events**. 

A Global Event is triggered anytime an ability or environmental effect has a radius larger than the engine's `MAX_SPELL_RANGE` (e.g., an explosion that crosses multiple server boundaries). Instead of overloading a single Arbiter with network routing, the engine automatically escalates these to the **Mesh Controller**, which schedules a perfectly synchronized map-wide detonation.

---

## 1. The Core Pipeline

As a designer, you do not need to flag an ability as "Global." The engine handles it automatically based on the geometry radius.

`SpawnZone` content is treated as a schema alias that compiles to `SpawnProjectile` with zero velocity plus pulse/duration mechanics.

1. **The Cast:** A player, boss, or script casts a spell.
2. **The Escalation:** The Host Arbiter notices the spell geometry max-extent exceeds local resolution bounds. It stops local processing. Using its authoritative state, the Arbiter performs the **Offensive Pre-Roll** (applying the caster's Crit and Multipliers to the spell's base data) to finalize the `CombatContext`. It then sends the spell and this finalized context to the Mesh Controller.
3. **The Synchronization:** The Mesh Controller calculates exactly which server nodes (Arbiters) are in the blast zone. It sends them a command: *"Execute this exact spell, from this specific caster, at exactly Shard Tick 50,000."* The command carries deterministic execution fields (`geometry`, optional `target_filters`, optional pulse/duration metadata), not just a radius scalar.
4. **The Execution:** All affected servers independently apply the damage/status effects to their players at the exact same millisecond.

---

## 2. Example Use Cases

### Example 2.1: The "Wipe Mechanic" (Massive Combat AoE)
A World Boss finishes a 10-second cast and unleashes a massive shockwave covering the entire zone. 

Because the Mesh Controller passes down the full `CombatContext`, local server nodes will still respect player defenses. If a player in Server A is using an "Invulnerability Potion," they will survive, while a player in Server B takes full damage.

**Designer JSON:**
```json
{
  "spell_id": "BOSS_APOCALYPSE_WAVE",
  "archetype": "TargetedAbility",
  "targeting": { "target": "SELF" },
  "mechanics": {
    "geometry": { 
        "type": "Circle", 
        "radius": 500.0 // Engine auto-escalates because this is > MAX_SPELL_RANGE
    }
  },
  "combat_context": {
    "base_damage": 99999,
    "damage_type": "SHADOW", // Allows players to mitigate with Shadow Resistance
    "knockback_force": 500.0
  },
  "visuals": {
    "screen_shake": true,
    "global_vfx": "fx_massive_purple_nova"
  }
}
```

---

### Example 2.2: "Weather Shift" (Map-Wide Buffs/Debuffs)
A faction captures a mystical altar, triggering a map-wide "Blizzard" that slows all enemies. 

Instead of dealing raw damage, this relies entirely on the `status_effect_id`. The Arbiters will instantly apply the debuff to all entities within the radius, and the `ability_id` tells all Edge Nodes (clients) to start rendering snow particle effects on the players' screens.

**Designer JSON:**
```json
{
  "spell_id": "EVENT_WINTER_BLIZZARD",
  "archetype": "TargetedAbility",
  "targeting": { "target": "MAP_CENTER" },
  "mechanics": {
    "geometry": { "type": "Circle", "radius": 2000.0 }
  },
  "combat_context": {
    "base_damage": 0, // No instant damage
    "damage_type": "COLD", // Deserializes to 4
    "status_effect_id": "EFFECT_CHILLED_SLOW" // Reduces movement speed by 20%
  },
  "visuals": {
    "weather_override": "WEATHER_SNOW",
    "ambient_sound": "sfx_howling_wind"
  }
}
```

---

### Example 2.3: "Bridge Collapse" (Environmental Targeting)
During a siege, a Nuke is dropped to destroy the bridges leading to a fortress. 

Because Global Events carry the `ability_id`, the Arbiter can be programmed to look for specific tags during the `resolve_action` loop. This spell deals massive damage, but *only* to entities tagged as `Structure`. Players standing next to the bridge take zero damage, but the bridge hitbox is destroyed.

**Designer JSON:**
```json
{
  "spell_id": "SIEGE_DESTROY_BRIDGE",
  "archetype": "SpawnProjectile",
  "mechanics": {
    "fuse_timer_ticks": 180, // 3-second fall time
    "geometry": { "type": "Box", "width": 50.0, "length": 50.0, "rotation": 0.0 },
    "target_filters": ["TAG_STRUCTURE"] // The Arbiter will ignore player entities
  },
  "combat_context": {
    "base_damage": 50000,
    "damage_type": "TRUE" // Ignores structure armor
  },
  "visuals": {
    "telegraph_type": "BOX_FILL",
    "telegraph_color": "RED",
    "impact_particle": "fx_stone_explosion"
  }
}
```

---

### Example 2.4: "The Gas" (Zone Denial / Battle Royale Ring)
A massive zone of poison descends on a sector of the map, damaging players inside it every second.

To avoid flooding the Mesh Controller with requests every second, the Controller schedules a single Global Event that spawns a **Stationary Zone Actor** in every affected Arbiter. The Arbiters then manage the local ticking damage independently without further Controller involvement.

**Designer JSON:**
```json
{
  "spell_id": "ARENA_POISON_GAS",
  "archetype": "SpawnZone", // content alias -> SpawnProjectile + pulse/duration mechanics
  "targeting": { "target": "COORDINATE" },
  "mechanics": {
    "geometry": { "type": "Circle", "radius": 800.0 },
    "pulse_interval_ticks": 60, // Pulses every 1 second
    "duration_ticks": 3600 // Lasts for 60 seconds
  },
  "combat_context": {
    "base_damage": 50,
    "damage_type": "TRUE", // Armor doesn't protect against gas
    "status_effect_id": "EFFECT_HEALING_REDUCED"
  },
  "visuals": {
    "environmental_tint": "GREEN_HAZE"
  }
}
```

---

## 3. The Underlying Engine Interface (For Engineers)

When the engine executes the JSON files above, the Mesh Controller sends the following strictly-typed command down to the Arbiters to guarantee deterministic, synchronized execution.

```rust
ControllerCommand::ExecuteGlobalEvent {
    event_id: "uuid-9999",              // Prevents duplicate explosions
    caster_id: Entity_42,               // Used for Kill Credit and PvP faction checks
    ability_id: SPELL_BOSS_APOCALYPSE,  // Matches the JSON spell_id
    data_epoch: 1,                      // The balance version this event was pre-rolled under
    context: CombatContext {            // Fully pre-rolled by the Originating Arbiter
        base_damage: 99999,
        damage_type: 8,                 // SHADOW
        knockback_force: SimFixed::from_num(500),
        armor_penetration_pct: SimFixed::from_num(0.5), // 50% Penetration from the Boss stats
        armor_penetration_flat: SimFixed::from_num(50),
        is_critical_strike: true,       // The Boss rolled a Crit!
        status_effect_id: None,
        damage_origin: DamageOrigin::DirectCast,
        proc_depth: 0
    },
    epicenter: Vec2F { x: SimFixed::from_num(1000), y: SimFixed::from_num(1000) },
    geometry: CollisionGeometry::Circle { radius: SimFixed::from_num(500) },
    target_filters: None,             // Optional: Some(vec![TAG_STRUCTURE]) for structure-only events
    pulse_interval_ticks: None,       // Optional: Some(60) for zone pulses
    duration_ticks: None,             // Optional: Some(3600) for long-lived zones
    execute_at_tick: 50000              // The exact Shard Tick for detonation
}
```
