# RPG Mechanics & State Definition

This document outlines the core RPG attribute system, combat formulas, and how offensive and defensive stats are reconciled across distributed server nodes.

Because the game engine uses a lock-free, geographically partitioned mesh (see `Spatial_Mesh_Arbiter_Architecture_v2.md`), an attacking player and a defending player may exist on two completely different servers. Therefore, combat calculations are strictly divided into a **Two-Phase Pipeline**: Pre-Rolling (Offense) and Resolution (Defense).

---

## 1. The Core Entity State (`SoftState`)

Every living entity (Player, Boss, Minion) instantiated in the Spatial Mesh possesses a `SoftState` struct. This contains the ephemeral, authoritative state required for the 60Hz physics and combat loop.

```rust
struct SoftState {
    // 1. Vitals
    hp: i32,
    max_hp: i32,
    resource: i32,     // Mana, Energy, Fury, etc.
    max_resource: i32,

    // 2. Base Physics
    position: Vec2F,
    velocity: Vec2F,
    weight: SimFixed,   // Determines knockback resistance
    move_speed: SimFixed,

    // 3. Offensive Attributes (Used during Phase 1: Pre-Roll)
    offense: OffensiveStats,

    // 4. Defensive Attributes (Used during Phase 2: Resolution)
    defense: DefensiveStats,

    // 5. Active Modifiers
    active_buffs: Vec<Buff>,
    is_invulnerable: bool,
}

struct OffensiveStats {
    global_damage_multiplier: SimFixed, // e.g., 1.2 (+20% all damage)
    crit_chance: SimFixed,              // 0.0 to 1.0
    crit_multiplier: SimFixed,          // e.g., 1.5 (150% damage)
    armor_penetration_pct: SimFixed,    // e.g., 0.3 (Ignores 30% of target armor)
    armor_penetration_flat: SimFixed,   // e.g., 10 (Ignores 10 flat armor)
    
    // Elemental Damage Conversions (Path of Exile style)
    // Allows items to say "20% of Physical Damage is converted to Fire"
    conversion_table: HashMap<u8, SimFixed>, 
    
    // Attacker-Owned Logic resolved during Phase 2 (e.g., Executioner's Axe)
    conditionals: Vec<OffensiveCondition>,
}

struct DefensiveStats {
    // A 16-element array mapping to the Damage Type Registry (e.g., 0=Slashing, 3=Fire).
    // Allows O(1) cache-friendly lookups during the 60Hz loop.
    resistances: [SimFixed; 16],
    
    evasion_rating: SimFixed, // Chance to completely dodge non-True damage
    block_chance: SimFixed,   // Chance to reduce incoming damage by 50%
    thorns_damage: i32,      // Flat True damage reflected to melee attackers
}
```
---

## 2. The Stat Compilation Pattern (Meta to Mesh)

The Spatial Arbiter has absolutely no concept of "Inventory," "Swords," "Rarities," or "Set Bonuses." Evaluating complex inventory graphs during a 60Hz physics loop would destroy the CPU budget. Instead, the engine uses a strictly decoupled **Compilation Pattern**:

1. **The Inventory Action (Meta Service):** The player equips the *"Executioner's Axe"* (+10% Crit, +50% Damage to low HP targets). The client sends this request directly to the stateless Inventory Service.
2. **The Compilation:** The Inventory Service queries the database, calculates the player's base stats, adds the Axe's stats, and compiles this into the flat, highly-optimized `OffensiveStats` and `DefensiveStats` structs.
3. **The Handshake:** The Meta Service pushes an async `UpdateEntityStats` command over the internal Event Bus to the Spatial Arbiter hosting the player.
4. **The 60Hz Loop:** The Arbiter atomically overwrites the player's `SoftState`. When the player attacks, the Arbiter simply reads `crit_chance = 0.15` and copies the `conditionals` over; it doesn't know *why* the crit chance is 15%, just that it is. This guarantees unhackable, blazing-fast physics execution.

---

## 3. The Cross-Boundary Combat Context

To support deep ARPG math across server boundaries without passing massive player data structures, we must upgrade the `CombatContext` payload defined in the interface blueprint.

When a player casts a spell, the originating Arbiter injects the player's offensive stats into the envelope. This ensures that a projectile retains the caster's "Armor Penetration" or "Crit Roll" even if it travels 3 servers away.

```rust
struct CombatContext {
    // The pre-calculated, final offensive potential
    base_damage: u32,
    damage_type: u8,
    
    // Physical/Kinetic impact
    knockback_force: SimFixed,
    
    // Attack properties that the *receiving* server needs to calculate defense
    armor_penetration_pct: SimFixed,
    armor_penetration_flat: SimFixed,
    is_critical_strike: bool, // Passed as a boolean so VFX/Floating Combat Text can render correctly
    
    status_effect_id: Option<u16>, 

    // Proc-safety metadata to prevent recursive reactive chains.
    damage_origin: DamageOrigin,
    proc_depth: u8,
    
    // Attacker-owned conditional logic (e.g., Executioner's Ring) to be evaluated by the target
    conditionals: Vec<OffensiveCondition>,
}
```
`DamageOrigin` is defined in `Spatial_Mesh_Interfaces.md` and shared across all combat envelopes.

---

## 4. The Two-Phase Combat Pipeline

To guarantee deterministic outcomes when combat crosses boundaries, the calculation is split into two distinct phases. 

### Phase 1: The Pre-Roll (Originating Server)
When a player clicks "Fire", the Arbiter that owns that player looks at their `OffensiveStats` and constructs the `CombatContext`. 

1. **Calculate Base:** Start with the Spell's base damage (e.g., 100).
2. **Apply Multipliers:** Multiply by `global_damage_multiplier` (e.g., 100 * 1.2 = 120).
3. **Roll for Crit:** The server rolls a random number against `crit_chance`. If successful, it multiplies the damage by `crit_multiplier` and sets `is_critical_strike = true`.
4. **Package Penetration & Logic:** It copies the player's `armor_penetration` values and `conditionals` array directly into the envelope.
5. **Stamp Proc Metadata:** Direct player/boss casts stamp `damage_origin = DirectCast` and `proc_depth = 0`.
6. **The Launch:** The projectile is spawned or the TargetedAbility is sent over the network. 

*Crucial Rule:* The `CombatContext` damage value is completely finalized from an offensive perspective before it ever leaves the origin server.

### Phase 2: The Mitigation Resolution (Receiving Server)
When the attack actually connects with the victim, the Arbiter that owns the victim executes `apply_combat_math`. It does **not** roll for crits or offensive multipliers. It only calculates Mitigation and Target-Based logic.

#### The Math Formula (`apply_combat_math`)

```rust
// 1. Evasion Check
if roll_dice() < victim.defense.evasion_rating {
    return; // "DODGED!"
}

// 2. Distance Falloff
let falloff_mult = calculate_falloff(distance);
let mut incoming_damage = context.base_damage as SimFixed * falloff_mult;

// 3. Unroll Attacker's Phase 2 Directives (Conditionals)
// This resolves complex item logic (e.g., "+50% damage if target HP < 30%") 
// exactly where the target's HP is authoritatively known.
let victim_hp_pct = victim.hp as SimFixed / victim.max_hp as SimFixed;
for condition in &context.conditionals {
    match condition {
        OffensiveCondition::MultiplyDamageIfTargetHpBelow { threshold_pct, multiplier } => {
            if victim_hp_pct < *threshold_pct {
                incoming_damage *= *multiplier;
            }
        },
        OffensiveCondition::AddDamageTargetMaxHpPct { pct_as_damage, .. } => {
            incoming_damage += (victim.max_hp as SimFixed * *pct_as_damage);
        }
        // ...
    }
}

// 4. Block Check
let mut is_blocked = false;
if roll_dice() < victim.defense.block_chance {
    incoming_damage *= SimFixed::from_num(0.5); // Reduce damage by 50%
    is_blocked = true;                         // Trigger "BLOCKED!" VFX
}

// 5. Resistance & Penetration Math
// Determinism Rule: All literal numbers must be converted to SimFixed. Standard f32 math is forbidden.
if context.damage_type != 99 && context.damage_type != 100 { // Ignore True/Healing
    // Get the victim's raw resistance to this specific element (e.g., FIRE)
    let mut effective_resistance = victim.defense.resistances[context.damage_type as usize];
    
    // Apply Attacker's Penetration
    effective_resistance *= (SimFixed::from_num(1) - context.armor_penetration_pct);
    effective_resistance -= context.armor_penetration_flat;
    
    // Clamp resistance between -100 (Taking double damage) and 85 (Taking 15% damage)
    effective_resistance = effective_resistance.clamp(SimFixed::from_num(-100), SimFixed::from_num(85));
    
    // Calculate Final Mitigation
    let one_hundred = SimFixed::from_num(100);
    if effective_resistance > SimFixed::from_num(0) {
        incoming_damage *= (SimFixed::from_num(1) - (effective_resistance / one_hundred));
    } else {
        // Negative resistance amplifies damage
        incoming_damage *= (SimFixed::from_num(1) + (effective_resistance.abs() / one_hundred));
    }
}

// 6. Final Application
victim.hp -= incoming_damage as i32;

// 7. Reactive Procs (Non-Recursive Guard)
if victim.defense.thorns_damage > 0
    && matches!(context.damage_origin, DamageOrigin::DirectCast)
    && context.proc_depth == 0
{
    trigger_thorns_mesh_event(
        attacker_id,
        victim.defense.thorns_damage,
        DamageOrigin::ReactiveProc,
        context.proc_depth + 1
    );
}
```

---

## 5. Itemization Strategy & Engine Constraints

By splitting the math this way, Game Designers gain massive flexibility for itemization:

*   **Weapons / Rings:** Provide `OffensiveStats` (Crit, Penetration, Conversions). These modify the projectile at launch.
*   **Armor / Shields:** Provide `DefensiveStats` (Resistances, Block, Evasion). These mitigate the incoming projectile upon impact.

Because the `CombatContext` envelope carries the bridge data (`penetration`, `is_crit`), the engine supports incredibly deep ARPG math without ever requiring two servers to synchronously query each other's databases during a 60Hz loop.
