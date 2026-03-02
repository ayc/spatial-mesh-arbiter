# RPG Mechanics & State Definition

This document outlines the core RPG attribute system, combat formulas, and how offensive and defensive stats are reconciled across distributed server nodes.

Because the game engine uses a lock-free, geographically partitioned mesh (see [Core Architecture](../1-architecture-and-engine/01-core-architecture.md)), an attacking player and a defending player may exist on two completely different servers. Therefore, combat calculations are strictly divided into a **Two-Phase Pipeline**: Pre-Rolling (Offense) and Resolution (Defense).

> **Canonical Type Source:** The authoritative struct definitions for `SoftState`, `CoreStats`, `ActiveStatusEffect`, and all wire envelopes live in the [Network Interfaces](../1-architecture-and-engine/02-network-interfaces.md) document. This document provides gameplay-focused context and defines `OffensiveStats`, `DefensiveStats`, and the combat formulas that operate on them.

---

## 1. The Core Entity State (`SoftState`)

Every living entity (Player, Boss, Minion) instantiated in the Spatial Mesh possesses a `SoftState` struct. This contains the ephemeral, authoritative state required for the 60Hz physics and combat loop. The canonical definition lives in [Network Interfaces](../1-architecture-and-engine/02-network-interfaces.md); it is reproduced here for gameplay context.

```rust
// Base attributes for physics and gameplay scaling
struct CoreStats {
    move_speed: SimFixed,
    weight: SimFixed,       // Determines knockback resistance
    time_scale: SimFixed,   // Gameplay Kinematic Dilation multiplier (1.0 = normal, 0.5 = slow motion)
}

// Describes how an active buff/debuff modifies an entity's stats at evaluation time.
// Applied as a temporary layer on top of the base OffensiveStats or DefensiveStats
// during Pre-Roll (offense) or Resolution (defense). Never mutates the stored base structs.
enum StatModifier {
    // Additive: base_value + flat_value (applied first, before multiplicative)
    FlatOffense { field: OffenseField, value: SimFixed },
    FlatDefense { field: DefenseField, value: SimFixed },

    // Multiplicative: base_value * multiplier (applied after all additives)
    MultOffense { field: OffenseField, multiplier: SimFixed },
    MultDefense { field: DefenseField, multiplier: SimFixed },

    // Appends a temporary conditional to the effective OffensiveStats at Pre-Roll time
    AddConditional { conditional: OffensiveCondition },
}

// Field selectors for stat modifiers (avoids stringly-typed lookups)
enum OffenseField {
    GlobalDamageMultiplier,
    CritChance,
    CritMultiplier,
    ArmorPenetrationPct,
    ArmorPenetrationFlat,
}

enum DefenseField {
    Resistance { damage_type: u8 }, // Index into the [SimFixed; 16] array
    EvasionRating,
    BlockChance,
    ThornsDamage,
}

// Internal Engine Representation of a running Buff/Debuff
struct ActiveStatusEffect {
    effect_id: u16,
    caster_id: EntityID,       // Preserved for kill credit if a DoT kills the target
    remaining_ticks: u32,
    next_pulse_tick: u64,      // The absolute Shard Tick when this effect should trigger its payload
    data_epoch: u32,           // The balance version this buff was applied under
    pulse_context: Option<CombatContext>, // The pre-rolled damage/healing payload to apply every pulse
    modifiers: Vec<StatModifier>, // Stat modifications active while this effect is alive (see Section 1.3)
}

// Core Entity State (Authoritative)
struct SoftState {
    // 1. Vitals
    hp: i32,
    max_hp: i32,
    resource: i32,          // Mana, Energy, Fury, etc.
    max_resource: i32,

    // 2. Physics
    position: Vec2F,
    velocity: Vec2F,
    rotation: SimFixed,
    last_movement_tick: u64,

    // 3. Base Attributes (Move speed, weight, time scale)
    stats: CoreStats,

    // 4. Defensive Attributes (Used during Phase 2: Resolution)
    defense: DefensiveStats,

    // 5. Active Modifiers
    active_status_effects: Vec<ActiveStatusEffect>,
    is_invulnerable: bool,

    // 6. Lifecycle
    is_dead: bool,                          // Flags the entity for cleanup/corpse transition
    resurrect_window_ticks: Option<u32>,    // Time remaining for a healer to resurrect before hard despawn
    logout_fuse_ticks: Option<u32>,         // Used for the 60-second wilderness logout mechanic
}
```

> **Why no `OffensiveStats` inside `SoftState`?** Offensive attributes (crit, penetration, damage multipliers) are only read during Phase 1: Pre-Roll — the moment a spell is cast. They are never mutated by the 60Hz physics loop and are not needed for movement, collision, or mitigation. Keeping them out of `SoftState` reduces the serialization payload during Hitless Handoffs and WAL streaming, where `SoftState` is the primary unit of transfer. See Section 1.1 below for where they live.

### 1.1 Offensive Stats (Companion Struct — Immutable Base)

`OffensiveStats` is stored as a **companion struct alongside `SoftState`** in the Arbiter's per-entity storage. It represents the **immutable base** compiled from the player's equipment by the Meta Services layer and pushed to the Arbiter via `UpdateEntityStats` (see Section 2).

The Arbiter **never mutates** this struct during gameplay. Temporary buffs and procs that modify offensive attributes are expressed as `StatModifier` entries on `ActiveStatusEffect` and layered on top of the base at evaluation time (see Section 1.3). This ensures that Meta can push updated base stats at any time (e.g., the player equips a new weapon) without conflicting with active buff state.

```rust
struct OffensiveStats {
    global_damage_multiplier: SimFixed, // e.g., 1.2 (+20% all damage)
    crit_chance: SimFixed,              // 0.0 to 1.0
    crit_multiplier: SimFixed,          // e.g., 1.5 (150% damage)
    armor_penetration_pct: SimFixed,    // e.g., 0.3 (Ignores 30% of target armor)
    armor_penetration_flat: SimFixed,   // e.g., 10 (Ignores 10 flat armor)

    // Elemental Damage Conversions (Path of Exile style)
    // A 16-element array indexed by damage_type (matching the Damage Type Registry).
    // Each slot holds the fraction of base damage converted to that element.
    // e.g., conversion_table[3] = 0.2 means "20% of base damage is converted to Fire"
    // Zero-initialized by default; only non-zero entries affect the Pre-Roll.
    conversion_table: [SimFixed; 16],

    // Attacker-Owned Logic resolved during Phase 2 (e.g., Executioner's Axe)
    conditionals: Vec<OffensiveCondition>,
}
```

### 1.2 Defensive Stats

`DefensiveStats` lives inside `SoftState` because it is read during Phase 2: Resolution on every incoming hit — a hot-path operation that must be cache-local to the entity being damaged.

```rust
struct DefensiveStats {
    // A 16-element array mapping to the Damage Type Registry (e.g., 0=Slashing, 3=Fire).
    // Allows O(1) cache-friendly lookups during the 60Hz loop.
    resistances: [SimFixed; 16],

    evasion_rating: SimFixed, // Chance to completely dodge non-True damage
    block_chance: SimFixed,   // Chance to reduce incoming damage by 50%
    thorns_damage: i32,      // Flat True damage reflected to melee attackers
}
```

> **Resolved:** `evasion` has been removed from `CoreStats` in the Network Interfaces doc and consolidated here in `DefensiveStats` as `evasion_rating`. The mitigation path is fully self-contained within `DefensiveStats`.

### 1.3 Buff Modifier Evaluation (Base + Modifiers Pattern)

Temporary buffs and procs that alter stats (offensive or defensive) do **not** mutate the stored `OffensiveStats` or `DefensiveStats` structs. Instead, the Arbiter computes **effective stats** on-the-fly by layering `StatModifier` entries from active status effects on top of the immutable base.

#### Why not mutate the base?

Mutating `OffensiveStats` on buff apply/expire creates subtle ordering bugs:
- If Meta pushes a new equipment compilation while "Berserker Rage" is active, the push overwrites the buffed value. You'd need stack tracking to reapply the buff afterward.
- Multiple buffs modifying the same field require careful add/remove ordering. A buff expiring out-of-order can leave stale values behind.

By keeping the base immutable and computing effective stats at evaluation time, these problems disappear. Meta can push new base stats at any moment, buff expiry is trivial (the `ActiveStatusEffect` is simply removed), and the result is always deterministic.

#### The Evaluation Algorithm

When the Arbiter needs effective offensive stats (during Pre-Roll) or effective defensive stats (during Resolution), it runs the following:

```rust
fn compute_effective_offense(
    base: &OffensiveStats,
    active_effects: &[ActiveStatusEffect],
) -> OffensiveStats {
    // 1. Clone the base as the starting point
    let mut effective = base.clone();

    // 2. First pass: collect and apply all FLAT (additive) modifiers
    for effect in active_effects {
        for modifier in &effect.modifiers {
            match modifier {
                StatModifier::FlatOffense { field, value } => {
                    apply_flat_offense(&mut effective, field, *value);
                }
                StatModifier::AddConditional { conditional } => {
                    effective.conditionals.push(conditional.clone());
                }
                _ => {} // Skip defense modifiers during offense evaluation
            }
        }
    }

    // 3. Second pass: apply all MULTIPLICATIVE modifiers
    for effect in active_effects {
        for modifier in &effect.modifiers {
            match modifier {
                StatModifier::MultOffense { field, multiplier } => {
                    apply_mult_offense(&mut effective, field, *multiplier);
                }
                _ => {}
            }
        }
    }

    effective
}
```

> **Application order:** All flat (additive) modifiers are summed first, then all multiplicative modifiers are applied to the result. This matches the standard ARPG convention (e.g., Path of Exile, Diablo) and guarantees deterministic results regardless of buff application order.

The same pattern applies symmetrically for `compute_effective_defense` during Phase 2 Resolution, layering `FlatDefense` and `MultDefense` modifiers over the base `DefensiveStats`.

#### Example: "Berserker Rage" (Temporary Offensive Buff)

A Warrior activates Berserker Rage, gaining +50% Crit Chance and +30% Damage for 10 seconds.

**1. The Designer's Data Definition:**
```json
{
  "spell_id": "WARRIOR_BERSERKER_RAGE",
  "archetype": "TargetedAbility",
  "targeting": { "target": "SELF" },
  "combat_context": {
    "status_effect_id": "EFFECT_BERSERKER_RAGE"
  }
}
```

**2. The Status Effect Definition:**
```json
{
  "effect_id": "EFFECT_BERSERKER_RAGE",
  "duration_ticks": 600,
  "modifiers": [
    { "type": "FlatOffense", "field": "CritChance", "value": 0.5 },
    { "type": "MultOffense", "field": "GlobalDamageMultiplier", "multiplier": 1.3 }
  ]
}
```

**3. The Runtime Flow:**

| Step | What happens |
|:---|:---|
| **Tick 1000** | Warrior casts Berserker Rage. Arbiter adds `ActiveStatusEffect { effect_id: EFFECT_BERSERKER_RAGE, remaining_ticks: 600, modifiers: [FlatOffense(CritChance, +0.5), MultOffense(GlobalDamageMultiplier, 1.3)], .. }` to the entity's `active_status_effects`. |
| **Tick 1042** | Warrior casts Fireball. Arbiter runs Pre-Roll. Base `OffensiveStats` from gear: `crit_chance = 0.15`, `global_damage_multiplier = 1.2`. Effective after buff: `crit_chance = 0.15 + 0.5 = 0.65`, `global_damage_multiplier = 1.2 * 1.3 = 1.56`. These effective values are used to build the `CombatContext`. |
| **Tick 1200** | Meta pushes `UpdateEntityStats` (player equipped a new ring: base `crit_chance` changes to `0.20`). Arbiter overwrites the base `OffensiveStats`. Buff is still active. |
| **Tick 1210** | Warrior casts again. Effective: `crit_chance = 0.20 + 0.5 = 0.70`. New ring and buff coexist correctly — no stale state. |
| **Tick 1600** | Berserker Rage expires. Arbiter removes the `ActiveStatusEffect`. No stat reversal logic needed. |
| **Tick 1610** | Warrior casts again. Effective: `crit_chance = 0.20` (pure base from ring). |

> **Performance note:** `compute_effective_offense` is only called at cast time (Pre-Roll), not every tick. A typical entity has 0–5 active status effects with 1–3 modifiers each — the iteration cost is negligible compared to the spell lookup and `CombatContext` construction.

---

## 2. The Stat Compilation Pattern (Meta to Mesh)

The Spatial Arbiter has absolutely no concept of "Inventory," "Swords," "Rarities," or "Set Bonuses." Evaluating complex inventory graphs during a 60Hz physics loop would destroy the CPU budget. Instead, the engine uses a strictly decoupled **Compilation Pattern**:

1. **The Inventory Action (Meta Service):** The player equips the *"Executioner's Axe"* (+10% Crit, +50% Damage to low HP targets). The client sends this request directly to the stateless Inventory Service.
2. **The Compilation:** The Inventory Service queries the database, calculates the player's base stats, adds the Axe's stats, and compiles this into the flat, highly-optimized `OffensiveStats` and `DefensiveStats` structs.
3. **The Handshake:** The Meta Service pushes an async `UpdateEntityStats` command over the internal Event Bus to the Spatial Arbiter hosting the player.
4. **The 60Hz Loop:** The Arbiter atomically overwrites the entity's `OffensiveStats` companion struct and the `DefensiveStats` within `SoftState`. When the player attacks, the Arbiter reads `crit_chance = 0.15` from the companion `OffensiveStats` and copies the `conditionals` into the `CombatContext` envelope; it doesn't know *why* the crit chance is 15%, just that it is. This guarantees unhackable, blazing-fast physics execution.

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
When a player clicks "Fire", the Arbiter that owns that player reads the entity's companion `OffensiveStats` (Section 1.1), layers active buff modifiers on top (Section 1.3), and constructs the `CombatContext`.

1. **Compute Effective Offense:** Call `compute_effective_offense(base_offense, active_status_effects)` to produce the effective `OffensiveStats` with all active buff modifiers applied. This is a read-only computation — the stored base is never touched.
2. **Calculate Base:** Start with the Spell's base damage (e.g., 100).
3. **Apply Multipliers:** Multiply by the effective `global_damage_multiplier` (e.g., 100 * 1.56 = 156 with Berserker Rage active).
4. **Roll for Crit:** The server rolls a random number against the effective `crit_chance`. If successful, it multiplies the damage by the effective `crit_multiplier` and sets `is_critical_strike = true`.
5. **Package Penetration & Logic:** It copies the effective `armor_penetration` values and `conditionals` array (including any buff-injected conditionals) directly into the envelope.
6. **Stamp Proc Metadata:** Direct player/boss casts stamp `damage_origin = DirectCast` and `proc_depth = 0`.
7. **The Launch:** The projectile is spawned or the TargetedAbility is sent over the network.

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
