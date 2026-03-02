# Action Payload Types (Ability Framework)

This document provides concrete examples of how complex ARPG/MOBA mechanics are translated into the engine's `ActionPayload` and `CombatContext` structures. It serves as a guide for Game Designers and Gameplay Engineers to map visual abilities to the networking layer.

---

## 1. Core Structures

### Combat Context (The Math Payload)
Every offensive or defensive ability relies on the `CombatContext` to pass unmitigated potential to the true owning Arbiter for final resolution.

```rust
struct CombatContext {
    base_damage: u32,
    damage_type: u8, // Mapped to a specific Element or Physical subtype (e.g., 0: Slashing, 3: Fire, 100: Healing)
    
    // Physical/Kinetic impact
    knockback_force: SimFixed,
    
    // Deep ARPG Modifiers passed over the network
    armor_penetration_pct: SimFixed,
    armor_penetration_flat: SimFixed,
    is_critical_strike: bool,

    status_effect_id: Option<u16>, // e.g., 'Poisoned', 'Stunned'

    // Proc safety metadata:
    // Direct casts start at depth 0. Reactive procs must increment depth.
    damage_origin: DamageOrigin,
    proc_depth: u8,
}
```
`DamageOrigin` is defined in `Spatial_Mesh_Interfaces.md` and is required for proc recursion safety.

---

## 2. Instant & Targeted Abilities (No Travel Time)

These abilities rely on the `TargetedAbility` payload. The Host Arbiter checks distance (plus prediction tolerance) and immediately applies the math.

### Example 2.1: "Smite" (Single Target Magic)
A Paladin clicks directly on an enemy to summon a bolt of light from the sky.

**1. The Designer's Data Definition (SpellData JSON):**
```json
{
  "spell_id": "ABILITY_SMITE",
  "archetype": "TargetedAbility",
  "mechanics": {
    "max_range": 15.0,
    "base_damage": 250,
    "damage_type": "HOLY"
  }
}
```

**2. The Edge Node Proposal (The Intent):**
*The Edge Node only sends the minimal data required to identify the player's intent.*
```rust
ActionPayload::TargetedAbility { 
    target_id: Enemy_99, 
    ability_id: ABILITY_SMITE
}
```

**3. The Arbiter Execution (The Authority):**
*The Arbiter receives the intent, looks up the data above, adds the player's stats, and applies the result.*

### Example 2.2: "Heavy Cleave" (Targeted Melee with Knockback)
A Warrior swings a massive hammer at a target, knocking them back.

**1. The Designer's Data Definition (SpellData JSON):**
```json
{
  "spell_id": "ABILITY_CLEAVE",
  "archetype": "TargetedAbility",
  "mechanics": {
    "max_range": 3.0,
    "base_damage": 100,
    "damage_type": "CRUSHING",
    "knockback_force": 50.0
  }
}
```

**2. The Edge Node Proposal (The Intent):**
```rust
ActionPayload::TargetedAbility { 
    target_id: Enemy_12, 
    ability_id: ABILITY_CLEAVE
}
```

### Example 2.3: "Flash Heal" (Targeted Friendly Support)
A Cleric instantly heals a party member.

**1. The Designer's Data Definition (SpellData JSON):**
```json
{
  "spell_id": "ABILITY_FLASH_HEAL",
  "archetype": "TargetedAbility",
  "mechanics": {
    "max_range": 25.0,
    "base_damage": 300,
    "damage_type": "HEALING"
  }
}
```

**2. The Edge Node Proposal (The Intent):**
```rust
ActionPayload::TargetedAbility { 
    target_id: Ally_42, 
    ability_id: ABILITY_FLASH_HEAL
}
```

---

## 3. Ephemeral Projectiles (Travel Time & Skillshots)

These abilities require spawning a temporary `ProjectileActor` in the mesh. The Edge Node sends the *intent* to spawn, and the Arbiter manages the flight and eventual `ImpactEvent`.

### Example 3.1: "Rocket Launcher" (Dumb-Fire AoE)
A player fires a rocket in a straight line. When it hits *any* hitbox, it explodes in a 5-meter radius.
*   **Edge Node Sends:**
    ```rust
    ActionPayload::SpawnProjectile { 
        direction: Vec2::new(1.0, 0.0), // Firing East
        spell_id: SPELL_ROCKET 
    }
    ```
*   **Projectile Actor (Later) Generates:**
    ```rust
    ActionPayload::ImpactEvent {
        impact_id: "uuid-1234",
        target_ids: vec![Enemy_1, Enemy_2, Destructible_Wall_5],
        epicenter: Vec2::new(150.0, 200.0), // Used for distance falloff calculation
        geometry: CollisionGeometry::Circle { radius: 5.0 },
        impact_tick: 5020,
        context: CombatContext {
            base_damage: 500,
            damage_type: FIRE, 
            knockback_force: 100.0,
            status_effect_id: None,
            damage_origin: DamageOrigin::DirectCast,
            proc_depth: 0
        }
    }
    ```

### Example 3.2: "Homing Missile" (Target-Locked Projectile)
A Mage casts a magic missile that physically travels toward a specific enemy, following them as they move.
*   **Edge Node Sends:**
    ```rust
    // The target_id drives the Actor's internal steering logic.
    // The direction vector provides the initial spawn trajectory.
    ActionPayload::SpawnProjectile { 
        direction: Vec2::new(0.0, 1.0), 
        target_id: Some(Enemy_8),
        spell_id: SPELL_MAGIC_MISSILE 
    }
    ```
*   **The "Dumb NPC" Steering:** The `ProjectileActor` functions as a microscopic AI. Every tick, it asks its Host Arbiter for the target's current position. 
    *   *If the target is a Real Entity:* It steers directly toward them.
    *   *If the target is a Ghost (on another server):* The Projectile seamlessly steers toward the Ghost's dead-reckoned, locally extrapolated coordinates. No cross-server network traffic is needed for the tracking math.
    *   *If the target is Lost (dies or teleports away):* The Projectile stops steering and defaults to a dumb-fire trajectory along its last known vector.

---

## 4. Complex Spatial Mechanics (The Power of the UUID)

Because the `event_idempotency_ledger` relies purely on `(Impact_UUID, Target_ID)`, the engine effortlessly supports complex multi-hit spells.

### Example 4.1: "Chain Lightning" (Bouncing Projectile)
The spell hits Target A, then creates a *new* Projectile Actor that flies to Target B, and so on.
*   **Impact 1 (Hits A):** Projectile generates `UUID_1`. Sent to Arbiter.
*   **Spawn:** Projectile Actor spawns a child Projectile Actor aimed at B.
*   **Impact 2 (Hits B):** Child generates `UUID_2`. Sent to Arbiter. 
*   *Ledger Result:* Flawless deduplication because each bounce has a unique UUID.

### Example 4.2: "Stationary Zones" (Blizzard / Healing Dome)
A player drops a static AoE field that damages or buffs anyone inside it every 1 second (60 ticks) for 5 seconds.
*   **Mechanic:** A stationary `ProjectileActor` (functioning as a `ZoneActor`) is spawned with zero velocity.
*   **The Pulse Logic:** Every 60 ticks, the Zone Actor scans all hitboxes in its radius and generates a **new unique UUID** for that specific pulse.
*   **Tick 60:** Actor generates `UUID_PULSE_1`. Sends `ImpactEvent` with `target_ids` of everyone currently inside.
*   **Tick 120:** Actor generates `UUID_PULSE_2`. Sends `ImpactEvent`.
*   **Ledger Result:** Players take damage or receive healing repeatedly, exactly as designed, because each pulse acts as a distinct, globally unique event. The `event_idempotency_ledger` prevents a single pulse from double-hitting a player on a border, but allows the player to be hit by the next pulse 60 ticks later.

---

## 5. Status Effects (Infections, DoTs, and Buffs)

Status effects (Damage Over Time, Slows, Stuns) do not require continuous network traffic. They are applied via the `status_effect_id` in the `CombatContext` and are managed internally by the owning Arbiter.

### Example 5.1: "Toxic Dart" (Application of a DoT)
A player shoots a poison dart.
*   **Projectile Generates:**
    ```rust
    ActionPayload::ImpactEvent {
        ...
        context: CombatContext {
            base_damage: 10, // Small initial hit
            damage_type: PIERCING,
            knockback_force: 0.0,
            status_effect_id: Some(EFFECT_POISON_TICK), // Applies the DoT
            damage_origin: DamageOrigin::DirectCast,
            proc_depth: 0
        }
    }
    ```
*   **Arbiter Resolution:** The Arbiter applies the 10 damage, then adds `EFFECT_POISON_TICK` to the victim's internal `SoftState.active_buffs` array.
*   **The Engine Loop:** During `simulate_physics_step()`, the Arbiter automatically deducts HP every second based on the active poison buff. Zero network traffic is required to sustain the DoT.

### Example 5.2: "Infection" (Spreading Status Effect)
A plague that spreads from player to player.
*   **Mechanic:** Managed entirely within the Arbiter's `simulate_physics_step()`. 
*   If Player A has `EFFECT_PLAGUE` active, the Arbiter runs a fast distance check against nearby entities every 60 ticks.
*   If Player B is within 2 meters, the Arbiter simply adds `EFFECT_PLAGUE` to Player B's `SoftState`.
*   If Player B is a Ghost (owned by another server), the Arbiter uses the Arbiter Relay Protocol to send an internal authoritative payload (typically `ActionPayload::InternalPreparedHit`) to apply the debuff across the border.

---

## 6. Cascading & Triggered Abilities (Procs)

Complex ARPGs often feature abilities that spawn *other* abilities upon impact (e.g., "Corpse Explosions" or "On-Hit" procs). The architecture handles this by allowing the Spatial Arbiter to recursively push new events into its own internal queue.

### Example 6.1: "Plague Carrier" (On-Hit Secondary Spawn)
A player fires a dart. When it hits an enemy, it explodes into a lingering, stationary poison cloud.
*   **The Impact:** The dart `ProjectileActor` hits the enemy and generates:
    ```rust
    ActionPayload::ImpactEvent {
        impact_id: "uuid-dart-1",
        target_ids: vec![Enemy_A],
        context: CombatContext {
            base_damage: 50,
            damage_type: POISON,
            knockback_force: 0.0,
            status_effect_id: Some(TRIGGER_PLAGUE_BURST), // The Cascade Trigger
            damage_origin: DamageOrigin::DirectCast,
            proc_depth: 0
        }
    }
    ```
*   **The Cascade (Inside the Arbiter):** During `apply_combat_math()`, the Arbiter processes the damage and detects `TRIGGER_PLAGUE_BURST`. It immediately constructs a new internal event to spawn the secondary cloud, and pushes it to its own `internal_inbox`:
    ```rust
    self.internal_inbox.push(MeshInternalEvent {
        event_id: generate_uuid(),
        source_arbiter_id: self.arbiter_id,
        actor_id: Some(original_attacker_id),
        origin_tick: current_shard_tick(), // Inherit current temporal context
        data_epoch: current_data_epoch(), // Pin this cascade to the current dictionary version
        payload: ActionPayload::SpawnProjectile { 
            direction: Vec2F::ZERO, // Stationary
            spell_id: SPELL_PLAGUE_CLOUD // Inherits its position from Enemy A's current location
        }
    });
    ```
*   **The Result:** On the very next tick, a new `ProjectileActor` (acting as a stationary 5-second cloud) is instantiated perfectly within the lock-free loop, subject to all standard Ghost Relay rules.

### Example 6.2: "Chilling Aura" (Attached Zone Actor)
A Paladin activates an aura that slows and damages all nearby enemies. The aura physically moves with the Paladin.
*   **Mechanic:** The ability spawns a specialized `ProjectileActor` (or `ZoneActor`) that is **parented** to the Paladin's EntityID.
*   **The Movement Loop:** Every tick, the Aura Actor updates its coordinates to match the Paladin's authoritative position.
*   **The Pulse:** Every 60 ticks, the Aura Actor performs a radial collision check against all hitboxes. If the Paladin is standing on a border, the check includes both real players and **Ghost entities**.
*   **The Impact:** The Aura Actor generates an `ImpactEvent` with a unique UUID for that specific pulse and hands it to the Arbiter.
*   **The Relay:** If Ghost entities were caught in the blast, the Host Arbiter relays the `ImpactEvent` to the neighboring Arbiters via the standard Arbiter Relay Protocol (Section 2.4). Enemy players on the other side of the border receive the slow debuff seamlessly.

### Example 6.3: "Thorns Armor" (Reactive Procs)
A player activates a buff that reflects 15 True damage back to anyone who hits them with a melee attack. 
*   **The Application:** The designer assigns `EFFECT_THORNS_AURA` to a buff spell. The Arbiter adds this to the player's `SoftState.active_buffs`.
*   **The Engine Trigger:** When an enemy hits the player, the Arbiter executes `apply_combat_math`. It calculates the damage to the victim, then sees the Thorns buff. 
*   **The Resolution:** The Arbiter does *not* instantly damage the attacker (this avoids memory access violations/Borrow Checker errors). Instead, the Arbiter automatically pushes a new `MeshInternalEvent` with `ActionPayload::InternalPreparedHit` targeting the attacker into its own queue. The attacker takes the 15 True damage on the very next simulation tick.
*   **The Proc Guard:** The reflected hit is stamped as `damage_origin = ReactiveProc` and `proc_depth = 1`, so it cannot recursively trigger another Thorns reflect. This prevents infinite Thorns-vs-Thorns event loops.

---

## 7. Game Designer Workflow (Data-Driven Abilities)

To ensure rapid iteration, Game Designers do **not** write Rust code to create new abilities. The `Spatial_Mesh` engine is built as a pure data-driven runner.

Designers create abilities by defining standard JSON, YAML, or proprietary Editor structures, which the server loads into memory as the `SpellData` dictionary. 

*(Note: While the Engine's `CombatContext` uses a fast `u8` integer for `damage_type`, designers use human-readable strings like `"SLASHING"` or `"FIRE"`. The server's Asset Loader automatically serializes these strings into the correct `u8` integers during boot.)*

### The Designer's Process:
1.  **Define the Base Archetype:** The designer selects whether the ability is `TargetedAbility` (Instant-Targeted), `GroundTargetedAbility` (Ground AoE), or `SpawnProjectile` (Travel time).
    -   `SpawnZone` is supported as a **content-layer alias** that compiles to `SpawnProjectile` with zero velocity plus pulse/duration mechanics.
2.  **Define the Physics:** (Range, Velocity, Bounding Box Radius).
3.  **Define the `CombatContext`:** (Base Damage, Damage Type, Knockback Weight).
4.  **Define the FX / Logic Hooks:** Attach particle effect IDs for the client, and Status Effect IDs (like `TRIGGER_PLAGUE_BURST`) for the server.

### Concrete Example: Creating a "WoW Rogue" Kit

#### 1. "Kidney Shot" (Targeted Stun)
```json
{
  "spell_id": "ROGUE_KIDNEY_SHOT",
  "archetype": "TargetedAbility",
  "targeting": { "max_range": 2.5 },
  "combat_context": {
    "base_damage": 45,
    "damage_type": "PIERCING",
    "status_effect_id": "EFFECT_STUN_3_SEC"
  }
}
```

#### 2. "Shadowstep" (Teleport Physics Override)
```json
{
  "spell_id": "ROGUE_SHADOWSTEP",
  "archetype": "TargetedAbility",
  "targeting": { "max_range": 25.0 },
  "physics_override": {
    "teleport_caster": true,
    "teleport_destination": "TARGET_REAR",
    "teleport_offset_distance": 1.0
  }
}
```

#### 3. "Vanish" (Stealth / Interest Management Override)
```json
{
  "spell_id": "ROGUE_VANISH",
  "archetype": "TargetedAbility",
  "targeting": { "target": "SELF" },
  "combat_context": {
    "status_effect_id": "EFFECT_IMPROVED_STEALTH"
  }
}
```

#### 4. "Wrecking Ball" (Ballistic Target Displacement)
```json
{
  "spell_id": "GARROSH_WRECKING_BALL",
  "archetype": "TargetedAbility",
  "targeting": { "max_range": 3.0 },
  "physics_override": {
    "target_displacement": true,
    "displacement_type": "BALLISTIC_ARC",
    "destination_logic": "CURSOR_LOCATION",
    "duration_ticks": 60
  },
  "combat_context": {
    "base_damage": 80,
    "damage_type": "CRUSHING",
    "status_effect_id": "EFFECT_AIRBORNE_STUN"
  }
}
```

#### 5. "Earthquake" (GroundTargeted-AoE)
A Shaman clicks a location on the ground. Everyone in a 10-meter radius is instantly damaged and slowed.
```json
{
  "spell_id": "SHAMAN_EARTHQUAKE",
  "archetype": "GroundTargetedAbility",
  "targeting": { "max_range": 30.0 },
  "mechanics": {
    "geometry": { "type": "Circle", "radius": 10.0 }
  },
  "combat_context": {
    "base_damage": 120,
    "damage_type": "CRUSHING",
    "status_effect_id": "EFFECT_SLOW_50"
  }
}
```

#### 6. "Time Bubble" (Gameplay Kinematic Dilation)
A Time Wizard drops a stationary zone that heavily dilates local time for enemies inside it.
*Note: Because this modifies the `time_scale` in the `CoreStats`, it automatically slows down the enemy's physical movement speed AND their ability cooldown recovery rates, perfectly mimicking the server's infrastructure-level "Temporal Swamp" but strictly scoped to the victims inside the bubble.*
```json
{
  "spell_id": "WIZARD_TIME_BUBBLE",
  "archetype": "SpawnZone",
  "targeting": { "max_range": 20.0 },
  "mechanics": {
    "geometry": { "type": "Circle", "radius": 8.0 },
    "duration_ticks": 600, // Lasts 10 seconds
    "pulse_interval_ticks": 10 // Rapid checks to apply/refresh the aura
  },
  "combat_context": {
    "base_damage": 0,
    "damage_type": "TRUE",
    "status_effect_id": "EFFECT_CHRONO_SLOW" // This buff overrides target time_scale to 0.3
  }
}
```

Because the Networking layer (`ActionPayload`) and the Engine Math (`apply_combat_math`) use these generic, polymorphic envelopes, a designer can create 1,000 unique spells without requiring the networking engineers to alter a single line of server routing code.

---

## 8. Rule-Bending Archetypes (Physics & Hard CC)

The engine effortlessly supports abilities that manipulate spatial reality or sever player control by leveraging the strict separation between the Edge Node (Proxy) and the Spatial Arbiter.

### 8.1 Physics Overrides (Teleports and Displacement)
Abilities like "Shadowstep" or "Blink" don't just apply damage; they forcibly mutate an entity's `[x, y]` coordinates.
*   **The Proposal:** The Edge Node sends a standard `TargetedAbility` payload.
*   **The Resolution:** The Arbiter looks up the spell in the `SpellData` dictionary and finds the `physics_override` rules. It validates the destination (ensuring the player isn't blinking into a wall), and then **atomically updates** the entity's `SoftState.position`.
*   **The Broadcast:** The Arbiter emits a `StateUpdate` with the new coordinates. The Edge Node receives this and "snaps" its local prediction to match the server's new reality.

### 8.2 Hard Crowd Control (Stuns, Polymorphs, and Banishes)
When a player is Stunned, they lose the ability to propose movement or actions.
*   **The Application:** A "Kidney Shot" applies `EFFECT_STUN`. The Arbiter adds this to the victim's `SoftState.active_buffs`.
*   **The Enforcement:** In the next tick, if the victim's Edge Node sends a `Movement` proposal, the Arbiter's `resolve_action` check sees the `STUN` flag and **silently discards the packet**. 
*   **The Result:** The player's inputs are ignored by the authoritative mesh until the stun duration expires. The Edge Node (Proxy) also sees the `STUN` flag in the downstream update and locally disables the player's UI/input to prevent prediction jitter.

### 8.3 "The Nuke" (Area of Effect Escalation)
If an ability's radius is larger than the Arbiter's `MAX_SPELL_RANGE` (e.g., a map-wide explosion), the Arbiter cannot resolve it locally.
*   **The Escalation:** The Arbiter forwards the `ActionProposal` to the **Mesh Controller**.
*   **The Scheduling:** The Mesh Controller calculates all affected Arbiters and issues an `ExecuteGlobalEvent` command (Section 5.3) scheduled for a future `Shard Tick`. 
*   **The Detonation:** Every Arbiter in the blast zone independently applies the damage at the exact same millisecond, ensuring perfectly synchronized map-wide destruction without a centralized simulation bottleneck.

---

## 9. Boss Mechanics & Telegraphed AoEs

In ARPGs and MMOs (like *Lost Ark* or *Final Fantasy XIV*), boss encounters rely heavily on "Telegraphs"—red warning zones that appear on the ground before a massive attack lands. 

The architecture handles these complex delays with zero continuous bandwidth cost by utilizing the `fuse_timer` of a `ProjectileActor`.

### The Telegraph Flow (Bandwidth Optimization)
1.  **The Broadcast:** When the Boss casts a Telegraphed AoE, the Arbiter spawns a stationary `ProjectileActor` with a long fuse (e.g., 2.0 seconds). The Arbiter sends **exactly one** downstream `StateUpdate` to the Proxy Nodes containing the actor's Telegraph visual data.
2.  **The Client Render:** The client receives this single packet and locally interpolates the red warning circle filling up over the 2.0 seconds. 
3.  **The Execution:** Exactly 120 ticks later, the `ProjectileActor` detonates, dealing damage to any hitboxes currently in the zone. If a player was stunned during the cast time and the actor was deleted, the client simply removes the warning circle.

### Example 9.1: "Falling Meteor" (Telegraphed Circle)

```json
{
  "spell_id": "BOSS_FALLING_METEOR",
  "archetype": "SpawnProjectile",
  "targeting": {
    "direction": [0.0, 0.0],
    "velocity": 0.0
  },
  "mechanics": {
    "fuse_timer_ticks": 120, 
    "geometry": { "type": "Circle", "radius": 15.0 }
  },
  "combat_context": {
    "base_damage": 5000,
    "damage_type": "FIRE", // Deserializes to 3
    "knockback_force": 200.0
  },
  "visuals": {
    "telegraph_type": "RADIAL_FILL",
    "telegraph_color": "RED",
    "telegraph_duration_sec": 2.0,
    "impact_particle": "fx_massive_crater"
  }
}
```

### Example 9.2: "Dragon's Breath" (Telegraphed Cone)
If a boss breathes fire in a 90-degree cone, the engine doesn't need new networking logic. The designer simply changes the `geometry` in the JSON. The `ProjectileActor` uses vector angle math to determine victims at the moment the fuse blows, rather than standard radius math.

```json
{
  "spell_id": "BOSS_DRAGON_BREATH",
  "archetype": "SpawnProjectile",
  "targeting": {
    "direction": [1.0, 0.0],
    "velocity": 0.0
  },
  "mechanics": {
    "fuse_timer_ticks": 60,
    "geometry": { 
        "type": "Cone", 
        "radius": 20.0, 
        "angle_degrees": 90.0,
        "direction": [1.0, 0.0]
    }
  },
  "combat_context": {
    "base_damage": 1200,
    "damage_type": "FIRE" // Deserializes to 3
  },
  "visuals": {
    "telegraph_type": "CONE_FILL",
    "telegraph_color": "ORANGE",
    "telegraph_duration_sec": 1.0
  }
}
```

### Example 9.3: "The Tether" (Linked Mechanics)
A Boss connects Player A and Player B with a laser beam. If they walk more than 15 meters apart, the beam snaps, dealing massive damage to both.
*   **The Mechanic:** The Boss spawns a `TetherActor` that holds references to both `EntityIDs`.
*   **The Loop:** Every tick, the `TetherActor` queries the Arbiter for the positions of Player A and Player B.
*   **The Snap:** If `distance > 15m`, the `TetherActor` generates an `ImpactEvent` targeting both players, deals the damage, and deletes itself. Because it is a standard Actor, it triggers Hitless Handoffs if the players move across Arbiters while tethered.

---

## Appendix: Damage Type Registry (The Asset Pipeline)

Designers use the following human-readable strings in JSON. The Asset Loader automatically serializes these into `u8` integers. This allows the engine's 60Hz loop to perform blazing-fast `O(1)` array lookups for mitigation stats, while giving designers rich, D&D-style itemization.

### Physical Sub-Types (The Weapon Triangle)
*   `"SLASHING"` (0): Swords, Axes. (e.g., Weak vs Plate, Strong vs Cloth).
*   `"PIERCING"` (1): Arrows, Spears, Daggers. (e.g., High crit multipliers).
*   `"CRUSHING"` (2): Maces, Hammers, Boulders. (e.g., Strong vs Golems/Plate).

### Elemental Sub-Types (The Magic Spectrum)
*   `"FIRE"` (3): Applies burning DoTs. (Blocked by Fire Resist).
*   `"COLD"` (4): Applies slows/chills. (Blocked by Cold Resist).
*   `"LIGHTNING"` (5): Arcs between targets. (Blocked by Lightning Resist).
*   `"POISON"` (6): Long-duration debuffs. (Blocked by Poison Resist).
*   `"HOLY"` (7): Paladin/Cleric offensive magic. (Blocked by Holy Resist).
*   `"SHADOW"` (8): Necromancer magic, lifesteal. (Blocked by Shadow Resist).

### System Types
*   `"TRUE"` (99): Unmitigable damage (bypasses all armor/resistances).
*   `"HEALING"` (100): Mathematically adds to HP instead of subtracting.
