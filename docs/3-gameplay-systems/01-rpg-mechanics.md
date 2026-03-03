# RPG Mechanics & State Definition

This document outlines the core RPG attribute system, combat formulas, and how offensive and defensive stats are reconciled across distributed server nodes.

Because the game engine uses a lock-free, geographically partitioned mesh (see [Core Architecture](../1-architecture/01-core-concepts-and-mesh.md)), an attacking player and a defending player may exist on two completely different servers. Therefore, combat calculations are strictly divided into a **Two-Phase Pipeline**: Pre-Rolling (Offense) and Resolution (Defense).

> **Canonical Type Source:** The authoritative struct definitions for `SoftState`, `CoreStats`, `ActiveStatusEffect`, and all wire envelopes live in the [Network Interfaces](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md) document. This document provides gameplay-focused context and defines `OffensiveStats`, `DefensiveStats`, and the combat formulas that operate on them.

---

## 1. The Attribute System

Every player character is defined by a hierarchical attribute system that feeds into the combat stats used by the Spatial Mesh. The Arbiter never sees these attributes directly — they are compiled into flat `OffensiveStats`, `DefensiveStats`, and `CoreStats` structs by the Meta Inventory Service (see Section 2). This section defines the attributes themselves and the conversion framework.

### 1.1 Major and Minor Attributes

Attributes are organized into **4 Major Attributes**, each composed of **3 Minor Attributes** (12 total). A Major Attribute's value is the sum of its three Minors. Major totals are used for equipment requirements, content gating, and broad archetype identification. Minor values drive the actual derived stat formulas.

```
PrimaryAttributes {
    // --- Body (Physical Domain) ---
    vigor: u16,         // Raw power and force
    agility: u16,       // Speed, reflexes, coordination
    endurance: u16,     // Toughness and stamina

    // --- Mind (Mental Domain) ---
    intellect: u16,     // Cognitive power and knowledge
    perception: u16,    // Awareness and precision
    willpower: u16,     // Discipline and concentration

    // --- Soul (Spiritual Domain) ---
    spirit: u16,        // Inner energy and healing
    attunement: u16,    // Connection to the world's magical fabric
    resolve: u16,       // Spiritual conviction and fortitude

    // --- Fate (Metaphysical Domain) ---
    fortune: u16,       // Luck and probability
    presence: u16,      // Force of personality
    cunning: u16,       // Resourcefulness and exploitation
}

// Derived Major totals (not stored — computed on read)
Body = vigor + agility + endurance
Mind = intellect + perception + willpower
Soul = spirit + attunement + resolve
Fate = fortune + presence + cunning
```

A character's Minor Attribute values come from three additive sources:
1. **Base allocation** — Level-up points distributed by the player (or a base stat source, e.g., class tables — deferred).
2. **Equipment** — Items grant Minor Attribute points via affixes (see Section 1.4).
3. **Buffs** — Temporary status effects can grant or reduce attribute points. These are layered at evaluation time (see Section 1.3 for the existing base + modifier pattern).

#### Body — Physical Domain

*How the character exists as a physical being in the world.*

| Minor | Combat | World |
|:---|:---|:---|
| **Vigor** | Physical/melee damage scaling, knockback force, block effectiveness | Carry capacity, mining yield, break barriers, salvage returns, intimidation dialogue |
| **Agility** | Attack/cast speed, evasion rating, movement speed | Lockpicking, trap disarming, acrobatics, stealth, crafting dexterity, fishing |
| **Endurance** | Max HP, HP regen, physical resistances (Slashing, Piercing, Crushing) | Sprint duration, swim speed, environmental hazard survival, durability loss reduction, potion effectiveness |

#### Mind — Mental Domain

*How the character processes, analyzes, and exerts cognitive force.*

| Minor | Combat | World |
|:---|:---|:---|
| **Intellect** | Spell damage scaling, max resource pool, cooldown reduction | Enchanting potency, recipe discovery, puzzle interactions, item identification, lore decryption |
| **Perception** | Crit chance, armor penetration, AoE targeting precision | Detect hidden (doors, chests, stealthed players), tracking, trap detection, appraise item value, rare node detection |
| **Willpower** | CC resistance (reduced duration), your CCs last longer, resource cost reduction, resist interrupts | Corruption resistance, crafting focus (fewer failures), resist fear/charm, maintain enchantments |

#### Soul — Spiritual Domain

*The character's inner essence and connection to forces beyond the physical.*

| Minor | Combat | World |
|:---|:---|:---|
| **Spirit** | Resource regen, healing power (given and received), buff/debuff duration | Creature taming, alchemy potency, meditation speed, commune with ghost NPCs, shrine duration |
| **Attunement** | Elemental damage bonus (all), elemental resistances (all non-physical), summon bond strength, thorns/reflect | Detect magical anomalies, ley line bonuses, ritual crafting, enchantment stability, weather sense |
| **Resolve** | Curse/corruption resistance, death penalty reduction, cleanse effectiveness, buff duration on self | Protection in corrupted zones, divine faction standing, persist through debuff zones, holy site access |

#### Fate — Metaphysical Domain

*The intangible forces that shape destiny — fortune, influence, and cunning. These are not personal capabilities but how the universe responds to the character.*

Fate as a Major Attribute gates content that rewards "soft power" builds. Certain quests, legendary items, NPC factions, and world events require minimum Fate thresholds, making the merchant prince and treasure hunter first-class archetypes rather than afterthoughts.

| Minor | Combat | World |
|:---|:---|:---|
| **Fortune** | Crit multiplier, proc chance on item effects, secondary "lucky dodge" | Loot rarity/quantity, gold find, rare crafting outcomes, gambling NPC results, random world event triggers, treasure map quality |
| **Presence** | Party aura radius and strength, summon/pet effectiveness, threat/aggro generation | Vendor prices, reputation gain speed, NPC dialogue branches, hire mercenaries, guild leadership bonuses, quest reward bonuses |
| **Cunning** | Bonus damage to debuffed/CC'd targets, ambush/first-strike damage, counter-attack chance, trap damage | Barter override, disguise, smuggling routes, sabotage, reverse-engineer items, exploit quest shortcuts |

### 1.2 Primary → Derived Stat Conversion

During stat compilation (Section 2), each Minor Attribute feeds one or more **derived combat stats** via designer-configurable conversion formulas. The conversion rates are defined in the designer configuration (`meta/attribute-formulas/v1`) and can be rebalanced without code changes.

The conversion framework follows this pattern:

```
derived_stat = Σ (minor_attribute_value × coefficient) + direct_item_bonuses
```

Multiple Minor Attributes can feed the same derived stat with different weights. This creates cross-stat synergies — there is always more than one way to increase a given combat stat, but through different tradeoffs.

#### Derived Stat Mapping

The following table defines WHICH Minor Attributes contribute to WHICH derived stats. The specific coefficients are designer-tuned values in the configuration file, not hardcoded.

**Offensive Derived Stats:**

| Derived Stat | Fed By | Notes |
|:---|:---|:---|
| Physical damage multiplier | Vigor (primary) | Scales physical-origin damage |
| Spell damage multiplier | Intellect (primary) | Scales spell-origin damage |
| Elemental damage multiplier | Attunement (primary) | Scales all elemental damage types |
| Global damage multiplier | (direct affixes only) | Multiplicative with type-specific multipliers |
| Crit chance | Perception (primary), Agility (minor) | Capped (see stat caps config) |
| Crit multiplier | Fortune (primary) | Base 1.5 (150%), scales with Fortune |
| Armor penetration (%) | Perception (primary) | |
| Armor penetration (flat) | Perception (minor) | |
| Attack/cast speed | Agility (primary) | Multiplier on ability cast/recovery times |
| Cooldown reduction | Intellect (minor) | Capped (see stat caps config) |
| Lifesteal % | (direct affixes only) | % of physical damage returned as HP |
| Spell vamp % | (direct affixes only) | % of spell damage returned as HP |
| Status effect duration | Spirit (primary), Willpower (minor) | +% duration on effects you apply |
| AoE radius multiplier | Perception (minor) | +% radius on area abilities |
| Projectile speed multiplier | Agility (minor) | +% velocity on projectile abilities |
| Proc chance multiplier | Fortune (primary) | +% chance for item/ability proc effects |
| Debuff bonus damage | Cunning (primary) | +% damage to debuffed/CC'd targets |
| Ambush damage multiplier | Cunning (primary) | +% damage on first strike from stealth/surprise |
| Counter-attack chance | Cunning (minor) | Chance to auto-retaliate on melee hit received |
| Conversion table | (direct affixes only) | Elemental damage conversions (existing) |
| Conditionals | (item affixes only) | Executioner, Giant Slayer, etc. (existing) |

**Defensive Derived Stats:**

| Derived Stat | Fed By | Notes |
|:---|:---|:---|
| Resistances (physical) | Endurance (primary) | Slashing, Piercing, Crushing |
| Resistances (elemental) | Attunement (primary) | Fire, Cold, Lightning, Poison, Holy, Shadow |
| Evasion rating | Agility (primary) | Chance to dodge |
| Block chance | (direct affixes only) | From shield/off-hand equipment |
| Block effectiveness | Vigor (minor) | How much block reduces damage (default 50%) |
| Thorns damage | Attunement (minor) | Flat damage reflected to melee attackers |
| Damage reduction % | (direct affixes only) | Flat % DR after all mitigation |
| Healing received multiplier | Spirit (minor) | +% effectiveness of incoming heals |
| Status effect resistance | Willpower (primary), Resolve (minor) | -% duration on debuffs applied to you |
| Curse resistance | Resolve (primary) | Separate from general status effect resistance |
| Poise | Endurance (minor), Vigor (minor) | Hidden stagger resistance (see Section 1.5) |

**Vital Derived Stats:**

| Derived Stat | Fed By | Notes |
|:---|:---|:---|
| Max HP bonus | Endurance (primary), Vigor (minor) | Added to base max HP |
| Max resource bonus | Intellect (primary), Spirit (minor) | Added to base max resource |
| HP regen per second | Endurance (minor), Spirit (minor) | Flat regen rate |
| Resource regen per second | Spirit (primary), Intellect (minor) | Flat regen rate |

**Utility Derived Stats:**

| Derived Stat | Fed By | Notes |
|:---|:---|:---|
| Movement speed | Agility (minor) | Multiplier on base movement |
| Weight (knockback resist) | Vigor (minor), Endurance (minor) | Higher = harder to displace |
| Loot rarity bonus | Fortune (primary) | % increase on loot quality rolls |
| Gold find | Fortune (minor) | % increase on gold drops |
| Vendor price modifier | Presence (primary) | Buy cheaper, sell higher |
| Reputation gain | Presence (minor) | +% reputation earned |
| XP bonus | (direct affixes only) | % increase on XP gains |

> **Design note — "(primary)" vs. "(minor)" contribution:** Where a Minor Attribute is listed as the "primary" contributor, it has a higher coefficient in the conversion formula. Where listed as "minor," it contributes at a lower rate. This distinction is purely about the designer-configured weights — the compilation algorithm treats all contributions identically (sum of `value × coefficient`).

### 1.3 Discoverable Secondary Attributes

In addition to the 12 Minor Attributes, there exist **Secondary Attributes** that appear on certain items and equipment. These are displayed as raw numeric values on item tooltips — `+22 Poise`, `+6 Momentum` — but the game provides **no explanation of what they do**. Players must discover their mechanics through experimentation and community research.

Secondary Attributes are compiled and pushed to the Arbiter alongside primary-derived stats, but their effects involve hidden thresholds and interaction rules that are not surfaced in any UI.

```
SecondaryAttributes {
    momentum: u16,
    poise: u16,
    echo: u16,
    affinity: u16,
    synchrony: u16,
}
```

#### Momentum

Builds as an entity lands consecutive hits without a gap exceeding a hidden tick threshold. At hidden breakpoints, attack speed and damage receive escalating bonuses. Resets to zero after the gap threshold is exceeded. Items with `+Momentum` lower the breakpoint thresholds and increase the ramp rate.

#### Poise

Hidden stagger and interrupt resistance. When an entity receives a hit, the game compares the entity's current Poise against the attack's hidden **impact force** value. If Poise exceeds the impact force, the entity is not staggered and cast animations are not interrupted. If Poise is lower, the entity suffers a stagger proportional to the deficit. Armor and heavy weapons carry hidden Poise values. The specific thresholds are intentionally undocumented.

#### Echo

Grows as a player repeatedly defeats the same monster type. At hidden thresholds, the player deals incrementally more damage to that monster type, takes less damage from them, and receives improved drop rates. Decays slowly over time when the player stops hunting that type. Functions as a hidden bestiary mastery system that rewards specialization. Items with `+Echo` increase the accumulation rate and slow the decay.

#### Affinity

Tracks cumulative usage of specific damage types and elements. A character who primarily deals Fire damage gradually develops a hidden Fire affinity that provides subtle bonuses to Fire damage and Fire resistance. Spreading damage across many elements prevents any single affinity from reaching its thresholds. Items with `+Affinity` lower the activation thresholds, making it easier to develop and maintain an elemental identity.

#### Synchrony

Accumulates while a player remains in the same party with the same members. At hidden thresholds, the entire party receives subtle bonuses: slightly improved healing received, marginally wider aura radius, and a small XP bonus. Resets when party composition changes. Items with `+Synchrony` accelerate the accumulation rate. This mechanic rewards stable group play over constant matchmaking cycling — but the game never tells players it exists.

### 1.4 The Three-Tier Affix Model

Items can grant stats through three distinct affix tiers, creating layered optimization choices:

**Tier 1 — Major Primary Affixes** (rare, high-tier items only):

Grant points to an entire Major Attribute. `+3 Body` adds +3 to Vigor, Agility, AND Endurance simultaneously. Effectively triple value per point, making these the most sought-after affix rolls. Restricted to Epic and Legendary quality tiers.

**Tier 2 — Minor Primary Affixes** (standard):

Grant points to a single Minor Attribute. `+10 Vigor` feeds all of Vigor's derived stats through the conversion formulas. Broad value — a single affix improves multiple combat and world stats.

**Tier 3 — Direct Derived Affixes** (surgical):

Grant a specific derived stat directly, bypassing the attribute conversion. `+3% Crit Chance` adds exactly 3% crit and nothing else. Less total value than an equivalent Minor Attribute investment, but allows precise targeting of breakpoints.

#### The Optimization Tradeoff

Consider a player who needs more crit chance:
- `+3 Mind` (Major) → grants Intellect, Perception, and Willpower → improves crit (via Perception) but also spell damage, CDR, CC resistance, and more. Maximum breadth.
- `+15 Perception` (Minor) → improves crit, armor pen, AoE radius, detection. Focused but multi-faceted.
- `+4% Crit Chance` (Direct) → exactly 4% crit. Surgical. Nothing else.

Each tier is optimal in different build contexts. A character near multiple breakpoints benefits from the broad investment. A character that just needs 2% more crit to reach a cap benefits from the surgical affix.

### 1.5 Hidden Stats

The following systems affect gameplay but are **never surfaced in any UI, tooltip, character sheet, or game documentation**. They exist purely as discoverable mechanics — emergent patterns that the player community must identify and map through observation and data collection.

#### Karma

Tracks cumulative player behavior: sparing enemies vs. executing them, donating gold vs. hoarding, helping NPCs vs. ignoring them. Subtly shifts NPC reactions, available quest branches, and which world events trigger in the player's vicinity. Two characters with identical attributes and gear may experience different content based on their Karma divergence. The game never acknowledges Karma exists.

#### Soul Weight

A function of the player's total accumulated power — level, equipped gear score, and wealth. Subtly influences the difficulty and reward profile of the ambient world around the player. Higher Soul Weight attracts tougher ambient spawns but shifts loot tables upward. Lower Soul Weight encounters a gentler world. This creates a hidden dynamic difficulty system that players gradually notice when comparing experiences.

#### Rhythm

Certain ability sequences trigger hidden combo bonuses when cast in specific orders. These are not documented anywhere in the ability framework. Players who accidentally discover a sequence — and notice the anomalous damage spike — must systematically test to map the valid chains. Rhythm combos are defined in the designer configuration alongside ability data.

#### Adaptive Resistance

When an entity takes repeated damage of the same type within a time window, a hidden resistance to that type gradually builds, decaying over time once the damage source stops. The game's version of "what doesn't kill you makes you stronger." Players who notice the pattern may develop strategies around intentional resistance training or exploit it defensively against sustained elemental damage.

---

## 2. The Core Entity State (`SoftState`)

Every living entity (Player, Boss, Minion) instantiated in the Spatial Mesh possesses a `SoftState` struct. This contains the ephemeral, authoritative state required for the 60Hz physics and combat loop. The canonical definition lives in [Network Interfaces](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md); it is reproduced here for gameplay context.

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
    modifiers: Vec<StatModifier>, // Stat modifications active while this effect is alive (see Section 2.3)
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

> **Why no `OffensiveStats` inside `SoftState`?** Offensive attributes (crit, penetration, damage multipliers) are only read during Phase 1: Pre-Roll — the moment a spell is cast. They are never mutated by the 60Hz physics loop and are not needed for movement, collision, or mitigation. Keeping them out of `SoftState` reduces the serialization payload during Hitless Handoffs and WAL streaming, where `SoftState` is the primary unit of transfer. See Section 2.1 below for where they live.

### 2.1 Offensive Stats (Companion Struct — Immutable Base)

`OffensiveStats` is stored as a **companion struct alongside `SoftState`** in the Arbiter's per-entity storage. It represents the **immutable base** compiled from the player's attributes and equipment by the Meta Inventory Service and pushed to the Arbiter via `UpdateEntityStats` (see Section 3).

The Arbiter **never mutates** this struct during gameplay. Temporary buffs and procs that modify offensive attributes are expressed as `StatModifier` entries on `ActiveStatusEffect` and layered on top of the base at evaluation time (see Section 2.3). This ensures that Meta can push updated base stats at any time (e.g., the player equips a new weapon) without conflicting with active buff state.

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
    // ArrayVec keeps the struct stack-allocated to prevent heap allocations in the 60Hz loop.
    conditionals: ArrayVec<OffensiveCondition, 4>,
}
```

### 2.2 Defensive Stats

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

### 2.3 Buff Modifier Evaluation (Base + Modifiers Pattern)

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

## 3. The Stat Compilation Pattern (Meta to Mesh)

The Spatial Arbiter has absolutely no concept of "Inventory," "Swords," "Rarities," "Attributes," or "Set Bonuses." Evaluating complex inventory and attribute graphs during a 60Hz physics loop would destroy the CPU budget. Instead, the engine uses a strictly decoupled **Compilation Pattern**:

1. **The Inventory Action (Meta Service):** The player equips the *"Executioner's Axe"* (+10 Perception, +5 Cunning, +50% Damage to low HP targets). The client sends this request directly to the stateless Inventory Service.
2. **The Attribute Aggregation:** The Inventory Service sums all Minor Attribute points from base allocation + all equipped items + all item affixes to produce the character's total `PrimaryAttributes`.
3. **The Stat Compilation:** Each Minor Attribute is converted to derived combat stats via the designer-configurable conversion formulas (Section 1.2). Direct derived affixes (e.g., `+3% Crit Chance`) are added on top. Stat caps are enforced. The result is flat, highly-optimized `OffensiveStats`, `DefensiveStats`, and `CoreStats` structs.
4. **The Push:** The Meta Service pushes an async `UpdateEntityStats` command over the internal Event Bus to the Spatial Arbiter hosting the player.
5. **The 60Hz Loop:** The Arbiter atomically overwrites the entity's `OffensiveStats` companion struct, `DefensiveStats`, and `CoreStats` within `SoftState`. When the player attacks, the Arbiter reads `crit_chance = 0.15` from the companion `OffensiveStats` and copies the `conditionals` into the `CombatContext` envelope; it doesn't know *why* the crit chance is 15% (whether it came from Perception, a direct affix, or both), just that it is. This guarantees unhackable, blazing-fast physics execution.

---

## 4. The Cross-Boundary Combat Context

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
    conditionals: ArrayVec<OffensiveCondition, 4>,
}
```
`DamageOrigin` is defined in [Network Interfaces](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md) and shared across all combat envelopes.

---

## 5. The Two-Phase Combat Pipeline

To guarantee deterministic outcomes when combat crosses boundaries, the calculation is split into two distinct phases. 

### Phase 1: The Pre-Roll (Originating Server)
When a player clicks "Fire", the Arbiter that owns that player reads the entity's companion `OffensiveStats` (Section 2.1), layers active buff modifiers on top (Section 2.3), and constructs the `CombatContext`.

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

## 6. Itemization Strategy & Engine Constraints

By splitting the math this way, Game Designers gain massive flexibility for itemization:

*   **Weapons / Rings:** Primarily grant offensive Minor Attributes (Vigor, Perception, Cunning) and direct offensive affixes (Crit, Penetration, Conversions). These shape the projectile at launch.
*   **Armor / Shields:** Primarily grant defensive Minor Attributes (Endurance, Willpower, Resolve) and direct defensive affixes (Resistances, Block, Evasion). These mitigate the incoming projectile upon impact.
*   **Accessories (Amulets, Belts):** Can grant any attribute domain, enabling hybrid builds. A Fate-heavy amulet (+Fortune, +Presence) creates a fundamentally different character than a Body-heavy one (+Vigor, +Endurance).

The three-tier affix model (Section 1.4) means a single item can carry Major Attributes (+3 Body), Minor Attributes (+10 Perception), and Direct Derived stats (+2% Crit Chance) simultaneously. The compilation pipeline (Section 3) flattens all of this into the optimized structs the Arbiter consumes.

Because the `CombatContext` envelope carries the bridge data (`penetration`, `is_crit`), the engine supports incredibly deep ARPG math without ever requiring two servers to synchronously query each other's databases during a 60Hz loop.
