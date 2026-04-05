# Meta Services Architecture

This document is the canonical architecture specification for the **Meta Services** layer — the durable, strongly-consistent backend that owns all persistent player state, economic transactions, social systems, and lifecycle orchestration.

Canonical split:
- The Spatial Mesh contracts that Meta consumes and produces (`HardEvent`, `MetaCommand`, `MetaRequest`/`MetaResponse`, `ArbiterCrashedEvent`) are defined in [Internal Mesh Types](../2-contracts-and-interfaces/internal-mesh-types/).
- The spawn handshake, logout protocol, death/respawn lifecycle, and crash recovery protocols are specified in [Core Concepts and Mesh §9](01-core-concepts-and-mesh.md).
- The Cross-Layer Transaction Ledger, Recovery Inbox, and Deferred Loot Recovery are specified in [Core Concepts and Mesh §9.8–9.10](01-core-concepts-and-mesh.md).
- The Session Manager (Redis-backed registry) is specified in [Core Concepts and Mesh §9.11](01-core-concepts-and-mesh.md) and [Core Primitives §5b](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md).
- Client-Edge wire protocol and Meta forwarding semantics are canonical in [Client-Edge Wire Protocol](../2-contracts-and-interfaces/01-client-edge-wire-protocol.md).
- Intent taxonomy for Meta-lane intents (`0300`–`0399`) is canonical in [Intent Taxonomy](../2-contracts-and-interfaces/02-intent-taxonomy.md).

This document is normative for locked contracts and service boundaries. Sections or fields explicitly marked `TBD` are draft guidance and not yet normative. Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** apply to non-`TBD` requirements.

---

## 1. Principles

1. **Durable Authority:** Meta is the sole owner of all persistent player state. The Spatial Mesh never writes to a database and never queries one during its 60Hz loop.
2. **Event-Driven Consumption:** Each Meta service subscribes to the relevant subset of `HardEvent` variants on the Event Bus. Topics are partitioned per-Arbiter (`hard_state.arbiter.{arbiter_id}`) to isolate surge traffic — see [Core Concepts §9.3](01-core-concepts-and-mesh.md). Services MUST be idempotent consumers — Redpanda/Kafka consumer groups guarantee at-least-once delivery when offsets are committed after durable processing.
3. **Per-Service Config Schemas:** Every service defines a designer-authored JSON configuration that is independently versioned and deployable. Config schemas are analogous to how `SpellData` works for abilities — designers author data, the runtime loads it.
4. **Shared Database, Schema Isolation:** All services share a single Postgres cluster but MUST use per-service schemas (e.g., `inventory.*`, `currency.*`). Cross-schema reads are permitted via explicit views; cross-schema writes are forbidden.
5. **Stateless Workers:** Every service is a horizontally-scaled, stateless worker behind the Event Bus. All mutable state lives in Postgres or Redis. No in-process caches are authoritative.
6. **Redis for Session and Caching:** The Session Manager is Redis-backed (already locked in per §9.11). Other services MAY use Redis for caching and rate limiting but MUST NOT treat Redis as durable storage for economic data.

---

## 2. Service Decomposition

Meta is decomposed into **10 services** across 4 domains:

| Domain | Service | Primary Responsibility |
|:---|:---|:---|
| **Core Platform** | Identity & Session | Auth, tokens, character CRUD, EntityID allocation, session registry, Edge Node health |
| | Spawn & Lifecycle | Spawn handshake, respawn timers, logout protocol, save zones |
| **Economy** | Inventory | Items, equipment, slots, stat compilation → pushes `OffensiveStats`/`DefensiveStats` |
| | Loot | Drop table evaluation, loot spawning, deferred loot recovery |
| | Currency & Trading | Wallets, NPC vendors, player-to-player trades, auction house |
| | Transaction & Recovery | `PendingTransaction` ledger, reconciliation, Recovery Inbox |
| **Progression** | Progression | XP, leveling, skill points / talent trees |
| | Quest & Achievement | Quest definitions, objectives, tracking, achievements, rewards |
| **Social** | Chat | Channels, message routing, moderation, rate limiting |
| | Party & Guild | Party formation/loot rules, guild creation/membership/ranks, friends lists |

### 2.1 Event Bus Subscription Matrix

Each service subscribes to only the `HardEvent` variants it needs:

| HardEvent | Identity | Spawn | Inventory | Loot | Currency | Transaction | Progression | Quest | Chat | Party |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `PlayerDied` | | X | | | | | X | X | | |
| `PlayerResurrected` | | X | | | | | | | | |
| `LootSpawned` | | | | X | | | | | | |
| `LootClaimed` | | | X | X | | | | | | |
| `ObjectiveCaptured` | | | | | | | X | X | | |
| `MonsterDied` | | | | X | | | X | X | | |
| `TransactionConfirmed` | | | | | | X | | | | |
| `ArbiterCrashedEvent` | | X | | X | | X | | | | |

---

## 3. Core Platform

### 3.1 Identity & Session Service

**Responsibility:** Owns authentication, character persistence, EntityID allocation, and the Session Manager (Redis registry tracking active sessions, Edge Node liveness, and entity-to-Arbiter mappings).

#### Locked-In Contracts

The Session Manager types are defined in [Core Primitives §5b](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md):

```rust
// Already specified — do not redefine
struct SessionMapping {
    character_id: UUID,
    entity_id: EntityID,
    arbiter_id: u32,
    edge_node_id: u32,
    status: SessionStatus,  // Active | Orphaned | Expired
    created_at: u64,
}

struct EdgeNodeRegistration {
    edge_node_id: u32,
    address: String,
    region: String,
    capacity: u32,
    current_sessions: u32,
}
```

Edge Node heartbeat contract (§9.11.1):
```
SET edge:{edge_node_id}:heartbeat ALIVE EX 6
```

The `ProxyActor` holds a `character_id: UUID` injected by Auth — the client cannot spoof identity (see [Edge Node Envelopes §2.1](../2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md)).

`EntityID` uses a generational index pattern `[32-bit Index | 32-bit Generation]` — Meta MUST increment generation before reassigning a reused slot (§2.1).

#### Designer Configuration

```json
{
  "$schema": "meta/identity-session/v1",
  "auth": {
    "token_ttl_seconds": 3600,
    "refresh_token_ttl_seconds": 604800,
    "max_sessions_per_account": 1,
    "login_rate_limit_per_minute": 10
  },
  "session_manager": {
    "edge_heartbeat_ttl_seconds": 6,
    "orphaned_session_ttl_seconds": 300,
    "session_mapping_ttl_seconds": 300
  },
  "characters": {
    "max_characters_per_account": "TBD",
    "character_name_min_length": "TBD",
    "character_name_max_length": "TBD",
    "character_name_regex": "TBD"
  },
  "entity_id_pool": {
    "generation_bits": 32,
    "index_bits": 32,
    "pre_allocation_batch_size": "TBD"
  }
}
```

#### Database Schema (TBD)

```sql
-- schema: identity

CREATE TABLE identity.accounts (
    account_id      UUID PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,          -- bcrypt/argon2
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    banned_until    TIMESTAMPTZ,
    -- TBD: OAuth provider columns, MFA state
);

CREATE TABLE identity.characters (
    character_id    UUID PRIMARY KEY,
    account_id      UUID NOT NULL REFERENCES identity.accounts,
    display_name    TEXT UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_save_zone  JSONB NOT NULL,        -- { "x": ..., "y": ... } in SimFixed coordinates
    last_login_at   TIMESTAMPTZ,
    -- TBD: class_id, appearance blob, deletion state
);

-- EntityID allocation ledger (tracks generation counters per index slot)
CREATE TABLE identity.entity_id_pool (
    index_slot      INTEGER PRIMARY KEY,
    current_generation INTEGER NOT NULL DEFAULT 0,
    assigned_to     UUID REFERENCES identity.characters,
    assigned_at     TIMESTAMPTZ
);
```

#### Open Questions
- What OAuth/SSO providers should be supported at launch?
- Should character deletion be soft-delete with a cooldown (e.g., 7-day grace period)?
- How are display names validated for profanity/impersonation?
- Should EntityID allocation be pre-batched or on-demand?

---

### 3.2 Spawn & Lifecycle Service

**Responsibility:** Orchestrates the spawn handshake, respawn timers, logout protocol, and save zone management. This service is the bridge between Meta's persistent state and the Spatial Mesh's ephemeral simulation.

#### Locked-In Contracts

**Spawn Handshake** (§9.5): The 5-step protocol is fully specified:
1. Client → Meta (auth via Edge Node)
2. Meta resolves the current lifecycle route: normally `last_save_zone` / `NEWBIE_ZONE`, but an active bounded respawn override MAY replace that destination
3. Meta queries Mesh Controller for target Arbiter at coordinates
4. Meta sends `MetaCommand::SpawnEntity` to target Arbiter via Event Bus
5. Meta replies to Edge Node with Arbiter address

The `SpawnEntity` command is defined in [Core Primitives §5](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md):
```rust
MetaCommand::SpawnEntity {
    entity_id: EntityID,
    character_id: UUID,
    compiled_state: SoftState,        // Base stats and persistent spawn defaults
    compiled_offense: OffensiveStats, // Gear-compiled offensive attributes
    respawn_context: Option<RespawnSpawnContext>,
}
```

**Logout Protocol** (§9.5):
- Safe Zone: `MetaCommand::InitiateLogout { entity_id, is_safe_zone: true }` → instant despawn
- Wilderness: `logout_fuse_ticks` = 60 seconds (set on `SoftState`)

**Death & Respawn** (§9.6):
- Meta subscribes to `HardEvent::PlayerDied` → resolves the base respawn delay from config,
  subtracts `respawn_delay_credit_ticks` (clamped at zero), and records the ordinary save-zone
  respawn schedule
- If `PlayerDied.respawn_override = Some(RespawnAnchor { ... })`, Meta also records the override
  schedule plus the anchor source/coordinates for that same death
- Meta subscribes to `HardEvent::RespawnOverrideRevoked` → clears any matching pending override. If
  the stored base respawn deadline is already in the past, Meta immediately executes the ordinary
  save-zone spawn handshake; otherwise it continues waiting on the base schedule
- Meta subscribes to `HardEvent::PlayerResurrected` → cancels timer
- On override expiry → executes Spawn Handshake at the override coordinates with
  `respawn_context = Some(RespawnSpawnContext::RespawnAnchor { anchor_entity_id })`
- The target Arbiter validates the anchor still exists, consumes it atomically, and materializes
  the player at the anchor position. If validation fails, it emits
  `HardEvent::RespawnOverrideRevoked` and does not spawn the player there
- On base timer expiry (or after any override revocation) → executes Spawn Handshake at last save
  zone

**Crash Recovery** (§9.7):
- Meta subscribes to `ArbiterCrashedEvent` → clears stale session mappings
- Next login triggers standard Spawn Handshake at last save zone

#### Designer Configuration

```json
{
  "$schema": "meta/spawn-lifecycle/v1",
  "respawn": {
    "base_respawn_timer_seconds": 15,
    "respawn_timer_scaling": "TBD: formula per level/deaths?",
    "corpse_window_seconds": 10,
    "resurrect_hp_pct": "TBD: percentage of max HP on resurrect"
  },
  "logout": {
    "wilderness_fuse_seconds": 60,
    "safe_zone_instant_logout": true
  },
  "save_zones": [
    {
      "zone_id": "TBD",
      "name": "TBD: Thornwall Keep",
      "coordinates": { "x": "TBD", "y": "TBD" },
      "is_default_newbie_zone": false,
      "required_level": "TBD"
    }
  ],
  "crash_recovery": {
    "session_stale_detection_timeout_seconds": 30
  }
}
```

#### Database Schema (TBD)

```sql
-- schema: lifecycle

-- Active respawn timers (ephemeral — cleared on spawn or server restart)
CREATE TABLE lifecycle.respawn_timers (
    character_id    UUID PRIMARY KEY,
    died_at         TIMESTAMPTZ NOT NULL,
    base_respawn_at TIMESTAMPTZ NOT NULL,
    override_respawn_at TIMESTAMPTZ,
    override_kind   TEXT,                  -- NULL for ordinary deaths, e.g. "respawn_anchor"
    override_source_entity_id BIGINT,      -- Anchor entity ID when override_kind is present
    override_x      BIGINT,                -- SimFixed as i64 bits; NULL when no override
    override_y      BIGINT,
    override_active BOOLEAN NOT NULL DEFAULT false,
    cause_event_id  UUID,                  -- Links to the HardEvent::PlayerDied
    cancelled       BOOLEAN NOT NULL DEFAULT false
);

-- Save zone definitions (designer-authored, loaded from config)
CREATE TABLE lifecycle.save_zones (
    zone_id         TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    x               BIGINT NOT NULL,       -- SimFixed as i64 bits
    y               BIGINT NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    required_level  INTEGER NOT NULL DEFAULT 0
);
```

#### Open Questions
- Should respawn timers scale with player level, number of recent deaths, or both?
- Are there penalties beyond respawn delay (XP loss, durability damage, gold drop)?
- How do instanced dungeons interact with save zones?
- Should there be a "nearest safe zone" heuristic or always use "last visited"?

---

## 4. Economy

### 4.1 Inventory Service

**Responsibility:** Owns all item storage, equipment slots, item instance creation, durability tracking, and the **stat compilation pipeline**. When a player equips, unequips, or modifies an item, this service recompiles the character's `PrimaryAttributes` into `OffensiveStats`, `DefensiveStats`, `CoreStats`, and `SecondaryAttributes`, then pushes the compiled values to the Arbiter via `UpdateEntityStats`.

The Inventory Service is the central economic actor — it creates item instances when loot is claimed, manages the full equipment lifecycle, and is the sole authority on what stats a character has.

#### Locked-In Contracts

**Stat structs** are defined in [Core Primitives §1](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md): `PrimaryAttributes`, `SecondaryAttributes`, `OffensiveStats`, `DefensiveStats`, `CoreStats`.

**The update command:**
```rust
MetaCommand::UpdateEntityStats {
    entity_id: EntityID,
    offense: Option<OffensiveStats>,
    defense: Option<DefensiveStats>,
    core_stats: Option<CoreStats>,
    secondary: Option<SecondaryAttributes>,
}
```

**Inventory wire types** are defined in [Edge Node Envelopes §2.1](../2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md): `InventorySlot`, `InventorySnapshot`, `ItemDetail`, `ResolvedAffix`, `DurabilityInfo`, `RepairResult`.

**Client requests** (via `MetaRequest`): `MoveInventoryItem`, `EquipItem`, `UnequipItem`, `InspectItem`, `RepairItem`, `RepairAllItems`.

**Client responses** (via `MetaResponse`): `InventorySync`, `ItemDetailResponse`, `RepairComplete`.

On `HardEvent::LootClaimed`, the Inventory Service creates an item instance (rolling affixes if applicable) and adds it to the player's inventory. On `HardEvent::PlayerDied`, it applies durability loss to all equipped items and triggers recompilation if any item crosses a degradation threshold.

#### The Attribute System

The full attribute system is defined in [RPG Mechanics §1](../../3-gameplay-systems/01-rpg-mechanics.md). In summary:

- **4 Major Attributes** (Body, Mind, Soul, Fate), each the sum of 3 Minors.
- **12 Minor Attributes** (Vigor, Agility, Endurance, Intellect, Perception, Willpower, Spirit, Attunement, Resolve, Fortune, Presence, Cunning).
- **5 Discoverable Secondary Attributes** (Momentum, Poise, Echo, Affinity, Synchrony) — appear on items with no in-game explanation.
- Items grant stats through **three affix tiers**: Major primary (`+3 Body`), Minor primary (`+10 Vigor`), and Direct derived (`+3% Crit Chance`).

#### Item Definition Asset Files

Item definitions are loaded from **JSON asset files** at boot, versioned via the `DataEpoch` pipeline (analogous to `SpellData` for abilities). Two files:

**`data/items.json`** — Base item definitions:
```json
{
  "$schema": "data/items/v1",
  "items": [
    {
      "item_id": 1001,
      "name": "Iron Sword",
      "item_class": "weapon_1h_sword",
      "equipment_slot": "main_hand",
      "item_level": 5,
      "required_level": 3,
      "required_attributes": {},
      "base_stats": {
        "primary": { "vigor": 3 },
        "derived": { "physical_damage_multiplier": 0.05 }
      },
      "implicit_affixes": [],
      "affix_pool": { "prefix_max": 2, "suffix_max": 2 },
      "max_durability": 100,
      "max_stack_size": 1,
      "vendor_sell_price": 50,
      "flags": []
    },
    {
      "item_id": 9001,
      "name": "Excalibur",
      "item_class": "weapon_1h_sword",
      "equipment_slot": "main_hand",
      "item_level": 60,
      "required_level": 50,
      "required_attributes": { "body": 80, "soul": 40 },
      "is_unique": true,
      "quality_tier": "Legendary",
      "base_stats": {
        "primary": { "vigor": 15, "resolve": 10 },
        "derived": {
          "physical_damage_multiplier": 0.25,
          "crit_chance": 0.10,
          "crit_multiplier": 0.20
        },
        "conversion_table": { "HOLY": 0.30 },
        "core": { "move_speed": 0.05 }
      },
      "fixed_affixes": [
        { "affix_id": "holy_smite_proc", "tier": 5 },
        { "affix_id": "executioner", "tier": 3 }
      ],
      "affix_pool": { "prefix_max": 0, "suffix_max": 0 },
      "max_durability": 200,
      "max_stack_size": 1,
      "vendor_sell_price": 5000,
      "flags": ["unique", "account_bound"],
      "flavor_text": "The sword of kings, said to choose its wielder."
    }
  ]
}
```

**`data/affixes.json`** — Affix pool definitions:
```json
{
  "$schema": "data/affixes/v1",
  "affixes": [
    {
      "affix_id": "of_the_bear",
      "display_template": "of the Bear (T{tier})",
      "slot_type": "suffix",
      "tiers": [
        {
          "tier": 1,
          "required_item_level": 1,
          "weight": 1000,
          "stat_modifiers": {
            "primary": { "endurance": 3 },
            "derived": {}
          }
        },
        {
          "tier": 2,
          "required_item_level": 15,
          "weight": 500,
          "stat_modifiers": {
            "primary": { "endurance": 8 },
            "derived": {}
          }
        },
        {
          "tier": 3,
          "required_item_level": 30,
          "weight": 200,
          "stat_modifiers": {
            "primary": { "endurance": 15 },
            "derived": {}
          }
        }
      ],
      "allowed_item_classes": ["armor_*", "accessory_*"],
      "tags": ["physical_defense"]
    },
    {
      "affix_id": "executioner",
      "display_template": "Executioner's (T{tier})",
      "slot_type": "prefix",
      "tiers": [
        {
          "tier": 1,
          "required_item_level": 20,
          "weight": 200,
          "stat_modifiers": {
            "primary": { "cunning": 5 },
            "conditionals": [
              { "type": "MultiplyDamageIfTargetHpBelow", "threshold_pct": 0.30, "multiplier": 1.20 }
            ]
          }
        },
        {
          "tier": 3,
          "required_item_level": 45,
          "weight": 50,
          "stat_modifiers": {
            "primary": { "cunning": 12 },
            "conditionals": [
              { "type": "MultiplyDamageIfTargetHpBelow", "threshold_pct": 0.30, "multiplier": 1.50 }
            ]
          }
        }
      ],
      "allowed_item_classes": ["weapon_*"],
      "tags": ["offensive_conditional"]
    },
    {
      "affix_id": "of_stability",
      "display_template": "of Stability (T{tier})",
      "slot_type": "suffix",
      "tiers": [
        {
          "tier": 1,
          "required_item_level": 10,
          "weight": 300,
          "stat_modifiers": {
            "secondary": { "poise": 8 }
          }
        },
        {
          "tier": 2,
          "required_item_level": 25,
          "weight": 150,
          "stat_modifiers": {
            "secondary": { "poise": 18 }
          }
        }
      ],
      "allowed_item_classes": ["armor_*", "weapon_2h_*"],
      "tags": ["hidden_secondary"]
    },
    {
      "affix_id": "major_body",
      "display_template": "Titan's (T{tier})",
      "slot_type": "prefix",
      "tiers": [
        {
          "tier": 1,
          "required_item_level": 35,
          "weight": 30,
          "stat_modifiers": {
            "major": { "body": 2 }
          }
        },
        {
          "tier": 2,
          "required_item_level": 50,
          "weight": 10,
          "stat_modifiers": {
            "major": { "body": 4 }
          }
        }
      ],
      "allowed_item_classes": ["armor_*"],
      "allowed_quality_tiers": ["Epic", "Legendary"],
      "tags": ["major_attribute"]
    }
  ]
}
```

**Affix stat modifier categories:**
- `"primary"` — Grants Minor Attribute points (e.g., `"vigor": 5`)
- `"major"` — Grants Major Attribute points, distributed equally to all three Minors (e.g., `"body": 3` adds +3 Vigor, +3 Agility, +3 Endurance)
- `"derived"` — Grants derived combat stats directly, bypassing attribute conversion (e.g., `"crit_chance": 0.03`)
- `"secondary"` — Grants discoverable Secondary Attribute points (e.g., `"poise": 12`)
- `"conditionals"` — Grants `OffensiveCondition` entries (Executioner, Giant Slayer, etc.)
- `"conversion_table"` — Grants elemental damage conversions

#### Stat Compilation Algorithm

When a player equips, unequips, or receives an `UpdateEntityStats`-triggering event (level up, item durability threshold crossed), the Inventory Service executes the following compilation:

```
compile_stats(character_id) -> (OffensiveStats, DefensiveStats, CoreStats, SecondaryAttributes):

    // 1. Load base attributes (level allocation + class base if applicable)
    base_primaries = db.get_attribute_allocation(character_id)

    // 2. Sum all equipment contributions
    equipment_primaries = PrimaryAttributes::zero()
    equipment_secondary = SecondaryAttributes::zero()
    direct_derived = DerivedBonuses::zero()
    conditionals = []
    conversions = [SimFixed::zero(); 16]

    for slot in db.get_equipped_items(character_id):
        item_def = items_json[slot.base_item_id]
        instance = db.get_instance(slot.instance_id)

        // Skip broken items (0 durability) — they contribute nothing
        if instance.durability == Some(0):
            continue

        // Apply degradation penalty if below threshold
        let penalty = if instance.is_degraded():
            config.durability.degraded_stat_penalty_pct  // e.g., 0.50
        else:
            1.0

        // Add base item stats
        equipment_primaries += item_def.base_stats.primary * penalty
        direct_derived += item_def.base_stats.derived * penalty
        conversions += item_def.base_stats.conversion_table
        direct_derived.core += item_def.base_stats.core * penalty

        // Add affix stats (fixed affixes from uniques + rolled affixes)
        for affix in resolve_affixes(item_def, instance):
            affix_tier = affixes_json[affix.affix_id].tiers[affix.tier]
            match affix_tier.stat_modifiers:
                "primary" => equipment_primaries += mods.primary * penalty
                "major" => equipment_primaries += expand_major(mods.major) * penalty
                "derived" => direct_derived += mods.derived * penalty
                "secondary" => equipment_secondary += mods.secondary
                "conditionals" => conditionals.extend(mods.conditionals)
                "conversion_table" => conversions += mods.conversion_table

    // 3. Compute final primary attributes
    total_primaries = base_primaries + equipment_primaries

    // 4. Convert primaries → derived stats via designer-configured formulas
    //    Each minor attribute feeds derived stats at configured coefficients.
    //    See RPG Mechanics § 1.2 for the full mapping table.
    compiled_offense = convert_primaries_to_offense(total_primaries, config.attribute_formulas)
    compiled_defense = convert_primaries_to_defense(total_primaries, config.attribute_formulas)
    compiled_core = convert_primaries_to_core(total_primaries, config.attribute_formulas)

    // 5. Add direct derived bonuses (bypass attribute conversion)
    compiled_offense += direct_derived.offense
    compiled_defense += direct_derived.defense
    compiled_core += direct_derived.core
    compiled_offense.conditionals = conditionals
    compiled_offense.conversion_table = conversions

    // 6. Enforce stat caps
    compiled_offense.crit_chance = min(compiled_offense.crit_chance, config.stat_caps.crit_chance)
    compiled_offense.crit_multiplier = min(compiled_offense.crit_multiplier, config.stat_caps.crit_multiplier)
    compiled_offense.cooldown_reduction = min(compiled_offense.cooldown_reduction, config.stat_caps.cooldown_reduction)
    compiled_defense.block_chance = min(compiled_defense.block_chance, config.stat_caps.block_chance)
    compiled_defense.evasion_rating = min(compiled_defense.evasion_rating, config.stat_caps.evasion_rating)
    // resistance_max applied per-element in the resistance array

    return (compiled_offense, compiled_defense, compiled_core, equipment_secondary)
```

The compiled result is pushed via `MetaCommand::UpdateEntityStats` to the Arbiter hosting the player. The Arbiter receives flat, optimized structs — it has no knowledge of attributes, items, or affixes.

#### Durability System

Every equipment item instance tracks `current_durability` and `max_durability` (from `items.json`). Stackable items (consumables, materials) do not have durability.

**Degradation triggers:**
- `HardEvent::PlayerDied` — All equipped items lose `death_durability_loss_pct` (default: 10%) of their `max_durability`.

**Durability thresholds:**
- **Degraded** (below `degraded_threshold_pct`, default 25%): Item stats are penalized by `degraded_stat_penalty_pct` (default 50%). Triggers stat recompilation. Client shows yellow warning icon.
- **Broken** (0 durability): Item contributes **no stats** to the compilation. Client shows red broken icon. Item must be repaired before providing any benefit.

**Repair:**
- Via `MetaRequest::RepairItem { slot }` or `MetaRequest::RepairAllItems` (at NPC vendor only — validated by interaction range check).
- Cost per item: `(max_durability - current_durability) × repair_cost_per_point_base × (1 + item_level × repair_cost_level_multiplier)`.
- Deducted from the character's gold wallet via an atomic transaction with the Currency Service.
- On successful repair, durability is restored to max and stats are recompiled if a threshold was crossed.

**Durability and Endurance attribute:**
- The Endurance Minor Attribute reduces durability loss. The reduction formula is designer-configurable: `effective_loss = base_loss × (1 - endurance_durability_reduction_coefficient × endurance)`, capped at a maximum reduction percentage.

#### Designer Configuration

```json
{
  "$schema": "meta/inventory/v1",
  "slots": {
    "default_bag_capacity": 40,
    "max_bag_capacity": 120,
    "equipment_slots": [
      "head", "chest", "legs", "feet", "gloves",
      "main_hand", "off_hand",
      "ring_1", "ring_2", "amulet", "belt"
    ]
  },
  "items": {
    "max_stack_size_default": 99,
    "quality_tiers": [
      { "id": 0, "name": "Common",    "color": "#9d9d9d", "max_affixes": 1 },
      { "id": 1, "name": "Uncommon",  "color": "#1eff00", "max_affixes": 2 },
      { "id": 2, "name": "Rare",      "color": "#0070dd", "max_affixes": 4 },
      { "id": 3, "name": "Epic",      "color": "#a335ee", "max_affixes": 5 },
      { "id": 4, "name": "Legendary", "color": "#ff8000", "max_affixes": 6 }
    ],
    "definitions_file": "data/items.json",
    "affixes_file": "data/affixes.json"
  },
  "durability": {
    "death_durability_loss_pct": 0.10,
    "degraded_threshold_pct": 0.25,
    "degraded_stat_penalty_pct": 0.50,
    "repair_cost_per_point_base": 1,
    "repair_cost_level_multiplier": 0.5,
    "endurance_durability_reduction_coefficient": 0.002,
    "endurance_durability_reduction_cap": 0.50
  },
  "stat_compilation": {
    "base_stats_source": "TBD: class-based table or universal defaults (deferred pending class system design)",
    "attribute_formulas_file": "data/attribute-formulas.json",
    "stat_caps": {
      "crit_chance": 0.75,
      "crit_multiplier": 5.0,
      "cooldown_reduction": 0.50,
      "block_chance": 0.75,
      "evasion_rating": 0.60,
      "resistance_max": 85,
      "damage_reduction_pct": 0.50,
      "lifesteal_pct": 0.25,
      "spell_vamp_pct": 0.25
    }
  }
}
```

#### Database Schema

```sql
-- schema: inventory

-- Item instances: every non-stackable item in the game.
-- Created when loot is claimed, a quest reward is granted, or an item is crafted/purchased.
CREATE TABLE inventory.item_instances (
    instance_id     BIGINT PRIMARY KEY,        -- Snowflake ID or sequence
    base_item_id    SMALLINT NOT NULL,          -- References items.json
    quality_tier    SMALLINT NOT NULL DEFAULT 0, -- 0=Common, 1=Uncommon, 2=Rare, 3=Epic, 4=Legendary
    durability      SMALLINT,                   -- NULL for non-degradable items
    max_durability  SMALLINT,                   -- NULL for non-degradable items
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source          TEXT NOT NULL DEFAULT 'drop' -- 'drop', 'quest', 'crafted', 'vendor', 'gm'
);

-- Rolled affixes on item instances.
-- Uniques store their fixed_affixes here with slot_type = 'fixed'.
CREATE TABLE inventory.item_affixes (
    instance_id     BIGINT NOT NULL REFERENCES inventory.item_instances ON DELETE CASCADE,
    affix_id        TEXT NOT NULL,               -- References affixes.json
    tier            SMALLINT NOT NULL,
    slot_type       TEXT NOT NULL,                -- 'prefix', 'suffix', 'implicit', 'fixed'
    ordinal         SMALLINT NOT NULL DEFAULT 0,  -- Display ordering
    PRIMARY KEY (instance_id, affix_id)
);

-- Bag inventory: character → item mapping.
-- Stackable items (potions, materials) use base_item_id with quantity > 1 and NULL instance_id.
-- Equipment uses instance_id with quantity = 1.
CREATE TABLE inventory.bags (
    character_id    UUID NOT NULL,
    slot            SMALLINT NOT NULL,
    base_item_id    SMALLINT NOT NULL,
    instance_id     BIGINT REFERENCES inventory.item_instances, -- NULL for stackables
    quantity        INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (character_id, slot),
    CONSTRAINT valid_quantity CHECK (
        (instance_id IS NULL AND quantity >= 1) OR
        (instance_id IS NOT NULL AND quantity = 1)
    )
);

-- Equipped items (always instance-based, never stackable).
CREATE TABLE inventory.equipment (
    character_id    UUID NOT NULL,
    slot_name       TEXT NOT NULL,               -- 'head', 'chest', 'main_hand', etc.
    instance_id     BIGINT NOT NULL REFERENCES inventory.item_instances,
    PRIMARY KEY (character_id, slot_name)
);

-- Character attribute allocations (level-up point distribution).
-- Separate from equipment-derived attributes — these are the player's chosen investments.
CREATE TABLE inventory.attribute_allocations (
    character_id    UUID PRIMARY KEY,
    vigor           SMALLINT NOT NULL DEFAULT 0,
    agility         SMALLINT NOT NULL DEFAULT 0,
    endurance       SMALLINT NOT NULL DEFAULT 0,
    intellect       SMALLINT NOT NULL DEFAULT 0,
    perception      SMALLINT NOT NULL DEFAULT 0,
    willpower       SMALLINT NOT NULL DEFAULT 0,
    spirit          SMALLINT NOT NULL DEFAULT 0,
    attunement      SMALLINT NOT NULL DEFAULT 0,
    resolve         SMALLINT NOT NULL DEFAULT 0,
    fortune         SMALLINT NOT NULL DEFAULT 0,
    presence        SMALLINT NOT NULL DEFAULT 0,
    cunning         SMALLINT NOT NULL DEFAULT 0,
    unspent_points  SMALLINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_bags_character ON inventory.bags (character_id);
CREATE INDEX idx_equipment_character ON inventory.equipment (character_id);
CREATE INDEX idx_item_instances_base ON inventory.item_instances (base_item_id);
CREATE INDEX idx_item_affixes_instance ON inventory.item_affixes (instance_id);
```

#### Entity Lookup

When the Inventory Service needs to push `UpdateEntityStats` to the Arbiter, it queries the Session Manager (Redis) for the character's current `entity_id` and `arbiter_id`:
```
GET session:{character_id} → SessionMapping { entity_id, arbiter_id, ... }
```
If the character is not online (no active session), the compilation result is persisted to the database and will be loaded during the next Spawn Handshake.

#### Open Questions (Resolved)

| Original Question | Resolution |
|:---|:---|
| Item definitions: Postgres or JSON? | **JSON asset files** (`data/items.json`, `data/affixes.json`), versioned via DataEpoch. Consistent with SpellData pattern. |
| Random affixes / procedural items? | **Affix pool system.** Items have a base type + rolled modifier slots from weighted affix pools. Stored as `(instance_id, [affix_id, tier])` in `inventory.item_affixes`. |
| Stat compilation algorithm? | **Attribute aggregation → formula conversion → direct bonus addition → cap enforcement.** See compilation pseudocode above. |
| Item durability / degradation? | **Yes.** Degrade on death, repair at NPC vendors for gold. Degraded items provide reduced stats; broken items provide none. |
| How does Inventory Service find the entity? | **Queries Session Manager** (Redis) for `entity_id` and `arbiter_id` from the character's `SessionMapping`. |

#### Remaining Open Questions
- How are attribute respec costs handled? (Gold, premium currency, or a consumable item?)
- Should there be a "salvage" system to break items into crafting materials?
- How do set bonuses work, if at all? (Track equipped set pieces and grant bonus stats at thresholds?)
- Should affixes have a value range within a tier (e.g., T2 Endurance rolls between +6 and +10) or fixed values per tier?

---

### 4.2 Loot Service

**Responsibility:** Evaluates drop tables when monsters die, rolls item quality and affixes, creates item instances, issues loot spawn commands to the Arbiter, manages party loot distribution, tracks loot claim state, maintains bad luck protection counters, and manages deferred loot recovery after crashes.

The Loot Service is the bridge between the combat system (which produces `MonsterDied` events) and the Inventory Service (which stores claimed items). It is the sole authority on what drops, at what quality, and who is eligible to claim it.

#### Locked-In Contracts

The Loot Service consumes `HardEvent::MonsterDied`:
```rust
HardEvent::MonsterDied {
    killer: Option<EntityID>,
    monster_id: EntityID,
    monster_type_id: u16,
    participating_entities: Vec<EntityID>,
}
```

It produces `HardEvent::LootSpawned` (via a spawn command to the Arbiter):
```rust
HardEvent::LootSpawned {
    drop_id: UUID,
    instance_id: u64,            // The created item instance (from inventory.item_instances)
    base_item_id: u16,           // For client icon/name rendering
    quality_tier: u8,            // For client color rendering
    location: Vec2F,
    source_monster_id: Option<EntityID>,
    eligible_entity_ids: Vec<EntityID>, // Who can interact with this drop
    despawn_tick: u64,            // Absolute tick when loot disappears
}
```

It consumes `HardEvent::LootClaimed`:
```rust
HardEvent::LootClaimed {
    drop_id: UUID,
    character_id: UUID,
    instance_id: u64,            // The item instance being claimed
}
```

**Deferred Loot Recovery** state machine (§9.10):
1. `ROLLED` — Meta records loot at `MonsterDied` consume time
2. `SPAWNED` — Meta issues spawn command to Arbiter
3. `CLAIMED` — Meta receives `LootClaimed` and finalizes
4. `DEFERRED` — Arbiter crashed while `SPAWNED` and no `LootClaimed` exists
5. `EXPIRED` — Deferred claim window ended

V1 recovery rules: 24-hour claim window, surfaced via Loot Reclamation NPC, restricted to original `participating_entities`, reuses party loot policy.

On `ArbiterCrashedEvent`, the Loot Service transitions all `SPAWNED` drops on the crashed Arbiter to `DEFERRED`.

#### Drop Table Definition

Drop tables are loaded from a **JSON asset file** (`data/drop-tables.json`), versioned via the `DataEpoch` pipeline alongside `items.json` and `affixes.json`.

```json
{
  "$schema": "data/drop-tables/v1",
  "tables": [
    {
      "table_id": "wolf_common",
      "monster_type_ids": [1001, 1002, 1003],
      "roll_count": { "min": 1, "max": 2 },
      "bonus_roll_chance": 0.15,
      "entries": [
        {
          "item_id": 2001,
          "weight": 1000,
          "min_quantity": 1,
          "max_quantity": 3,
          "conditions": []
        },
        {
          "item_id": 1001,
          "weight": 200,
          "min_quantity": 1,
          "max_quantity": 1,
          "conditions": [{ "type": "min_player_level", "value": 5 }]
        },
        {
          "item_id": 3001,
          "weight": 50,
          "min_quantity": 1,
          "max_quantity": 1,
          "conditions": [{ "type": "min_player_level", "value": 10 }]
        }
      ],
      "guaranteed_drops": [
        { "item_id": 9100, "quantity": 1 }
      ],
      "quality_curve": "standard",
      "unique_table": [
        {
          "item_id": 9500,
          "base_weight": 5,
          "pity_eligible": true,
          "conditions": [{ "type": "min_player_level", "value": 15 }]
        }
      ]
    },
    {
      "table_id": "world_boss_dragon",
      "monster_type_ids": [5001],
      "loot_mode": "personal_per_participant",
      "roll_count": { "min": 2, "max": 4 },
      "bonus_roll_chance": 0.30,
      "entries": [
        { "item_id": 4001, "weight": 500, "min_quantity": 1, "max_quantity": 1, "conditions": [] },
        { "item_id": 4002, "weight": 300, "min_quantity": 1, "max_quantity": 1, "conditions": [] },
        { "item_id": 4003, "weight": 100, "min_quantity": 1, "max_quantity": 1, "conditions": [] }
      ],
      "guaranteed_drops": [
        { "item_id": 9200, "quantity": 5 }
      ],
      "quality_curve": "boss_elevated",
      "unique_table": [
        { "item_id": 9001, "base_weight": 2, "pity_eligible": true, "conditions": [] }
      ]
    }
  ]
}
```

#### Drop Evaluation Pipeline

When `HardEvent::MonsterDied` is consumed, the Loot Service executes the following pipeline. For standard monsters, this runs once and produces shared drops. For world bosses (`loot_mode: "personal_per_participant"`), this runs independently **per participating entity**, each with their own Fortune modifier and pity state.

```
evaluate_drops(monster_type_id, participating_entities, killer, location, arbiter_id):

    table = drop_tables_json[monster_type_id]

    // For world bosses, run the pipeline per-participant
    if table.loot_mode == "personal_per_participant":
        for entity in participating_entities:
            fortune = get_fortune_attribute(entity)
            evaluate_single(table, entity, fortune, location, arbiter_id)
        return

    // For standard monsters, run once with the killer's Fortune
    fortune = get_fortune_attribute(killer) or 0
    evaluate_single(table, participating_entities, fortune, location, arbiter_id)

evaluate_single(table, eligible, fortune, location, arbiter_id):

    // --- Step 1: Guaranteed Drops ---
    for guaranteed in table.guaranteed_drops:
        create_drop(guaranteed.item_id, guaranteed.quantity, eligible, ...)

    // --- Step 2: Roll Count ---
    roll_count = random(table.roll_count.min, table.roll_count.max)
    if random() < table.bonus_roll_chance:
        roll_count += 1

    // --- Step 3: Per-Roll Item Selection + Quality + Affix Rolling ---
    for i in 0..roll_count:

        // 3a. Filter entries by conditions (player level, etc.)
        valid_entries = table.entries.filter(|e| e.conditions_met(eligible))

        // 3b. Apply pity weight adjustments to unique table entries
        combined = valid_entries + apply_pity_weights(table.unique_table, eligible)

        // 3c. Weighted random selection
        selected = weighted_random(combined)
        quantity = random(selected.min_quantity, selected.max_quantity)

        // 3d. Determine quality tier (for non-unique, non-stackable items)
        item_def = items_json[selected.item_id]
        if item_def.is_unique:
            quality_tier = item_def.quality_tier
        else if item_def.max_stack_size > 1:
            quality_tier = 0  // Stackables are always Common
        else:
            quality_tier = roll_quality_tier(table.quality_curve, fortune)

        // 3e. Roll affixes and create item instance
        instance = create_item_instance(selected.item_id, quality_tier, fortune)

        // 3f. Record the drop
        create_drop(instance, quantity, eligible, location, arbiter_id)

        // 3g. Update pity counters
        if selected was from unique_table:
            reset_pity_counter(eligible, table.table_id, selected.item_id)
        else:
            increment_pity_counters(eligible, table.table_id)
```

#### Quality Tier Determination

Quality tier is rolled against a **quality curve** defined in the designer config. The Fortune attribute shifts the roll result upward, making rare quality tiers more likely for high-Fortune characters.

```
roll_quality_tier(curve_name, fortune):
    curve = config.quality_curves[curve_name]
    // Fortune shifts the roll: each point of Fortune adds a small bonus to the percentile roll
    roll = random(0.0, 1.0) + (fortune * config.fortune_quality_coefficient)
    roll = clamp(roll, 0.0, 1.0)

    // Walk the curve thresholds
    if roll < curve.common_threshold:     return Common      // 0
    if roll < curve.uncommon_threshold:   return Uncommon    // 1
    if roll < curve.rare_threshold:       return Rare        // 2
    if roll < curve.epic_threshold:       return Epic        // 3
    return Legendary                                         // 4
```

Quality tier determines the number of affix slots available on the item (per the `quality_tiers` config in the Inventory Service):
| Quality | Max Affixes |
|:---|:---|
| Common | 1 |
| Uncommon | 2 |
| Rare | 4 |
| Epic | 5 |
| Legendary | 6 |

#### Affix Rolling

When creating an item instance, affixes are rolled from the weighted affix pool defined in `affixes.json`. The number of affixes rolled is `random(1, max_affixes_for_quality_tier)`, distributed between prefix and suffix slots up to the item's `affix_pool.prefix_max` and `affix_pool.suffix_max`.

```
roll_affixes(item_def, quality_tier, fortune):
    max_affixes = quality_tiers[quality_tier].max_affixes
    num_affixes = random(1, min(max_affixes, item_def.prefix_max + item_def.suffix_max))

    rolled = []
    for i in 0..num_affixes:
        // Determine if this slot is prefix or suffix (respect caps)
        slot_type = pick_slot_type(rolled, item_def.affix_pool)

        // Filter eligible affixes by: item_class, item_level, slot_type, not already rolled
        pool = affixes_json.filter(|a|
            a.slot_type == slot_type
            && a.allowed_item_classes.matches(item_def.item_class)
            && a.has_tier_for_item_level(item_def.item_level)
            && a.affix_id not in rolled
            && a.allowed_quality_tiers is empty or includes quality_tier
        )

        // Weighted random selection from eligible pool
        selected_affix = weighted_random(pool)

        // Select the highest tier eligible for this item level
        tier = selected_affix.highest_tier_for(item_def.item_level)

        rolled.push({ affix_id: selected_affix.affix_id, tier, slot_type })

    return rolled
```

The Loot Service creates the item instance and its affixes by writing to `inventory.item_instances` and `inventory.item_affixes`. It holds cross-schema write access to the inventory schema for item creation only (not modification of existing player inventory — that is the Inventory Service's responsibility via `LootClaimed`).

#### Bad Luck Protection (Pity System)

A per-character, per-drop-table pity counter tracks how many rolls have occurred since the last rare/unique drop from that table. Each failed roll increments the counter, which applies an increasing weight bonus to rare entries in subsequent rolls.

```
apply_pity_weights(unique_table, eligible_entities):
    adjusted = []
    for entry in unique_table:
        if not entry.pity_eligible:
            adjusted.push(entry)
            continue

        // Use the highest pity counter among eligible entities (for party fairness)
        max_pity = max(get_pity_counter(entity, table_id, entry.item_id) for entity in eligible)

        // Weight grows linearly with pity count; guaranteed at hard pity threshold
        bonus = max_pity * config.pity_weight_per_kill
        if max_pity >= config.pity_hard_threshold:
            adjusted_weight = 999999  // Guaranteed
        else:
            adjusted_weight = entry.base_weight + bonus

        adjusted.push(entry with weight = adjusted_weight)

    return adjusted
```

The Fortune attribute accelerates pity accumulation: `effective_pity_increment = 1 + (fortune * config.fortune_pity_coefficient)`. High-Fortune characters reach the hard pity threshold faster.

Pity counters are stored in Postgres and reset to zero when the tracked rare/unique item drops.

#### Party Loot Distribution

When a drop is created, the Loot Service checks the party membership and loot mode for the eligible entities (via a cross-schema read of `social.parties` / `social.party_members`).

**FreeForAll:** First entity to interact with the drop claims it. No restriction beyond the `eligible_entities` list.

**RoundRobin:** The Loot Service maintains a rotating index per party. Each drop is assigned to the next participant in rotation. Only the assigned entity can claim it. If the assigned entity doesn't claim within `round_robin_claim_timeout_seconds`, the drop opens to all eligible entities.

**NeedGreed:** On drop, the Loot Service creates a vote session in Redis:
```
SET loot:vote:{drop_id} { votes: {}, timeout_at: now + vote_timeout } EX vote_timeout_seconds
```
Each eligible entity can cast `Need`, `Greed`, or `Pass` via `MetaRequest::LootVote { drop_id, vote }`. When all votes are in (or timeout expires):
- All `Need` voters: random winner among them.
- If no `Need`: all `Greed` voters: random winner.
- If no `Need` or `Greed`: drop opens to all or despawns.

**MasterLoot:** The party leader assigns the drop to a specific party member via `MetaRequest::AssignLoot { drop_id, target_character_id }`. Unassigned drops open to all after `master_loot_assign_timeout_seconds`.

#### Party Loot and Crash Recovery

When an Arbiter crashes, `SPAWNED` drops transition to `DEFERRED`. The critical invariant for dupe prevention:

1. The `loot.drops` row in Postgres is the **single source of truth**. The `status` column can only transition to `CLAIMED` once, enforced by an atomic `UPDATE ... WHERE status = 'SPAWNED' OR status = 'DEFERRED'` with a row lock.
2. For **NeedGreed** votes in progress at crash time: the Redis vote session expires naturally. On deferred recovery, the drop is resurfaced via the Loot Reclamation NPC with the party loot mode that was recorded at creation time. A new vote session is started if the mode requires it.
3. For **RoundRobin**: the assigned entity is recorded on the drop row (`assigned_to`). Deferred recovery preserves this assignment.
4. For **MasterLoot**: if the leader hasn't assigned the drop, it falls back to FreeForAll among eligible entities during deferred recovery.
5. **Anti-dupe guarantee:** The Arbiter's in-world loot entity is ephemeral. The Postgres row is authoritative. Even if a crash causes the Arbiter to "lose" a loot entity, the row in `loot.drops` tracks whether it was claimed. The Loot Reclamation NPC queries Postgres directly — there is no second path to claim the same drop.

#### World Boss Loot

Monsters with `loot_mode: "personal_per_participant"` in their drop table use **personal loot rolls**:

- Each entity in `participating_entities` gets an independent evaluation of the full drop table.
- Each entity's **own Fortune attribute** modifies their quality curves and pity counters.
- Drops are created with `eligible_entities = [single_entity]` — only that player can see and claim their personal loot.
- Personal loot drops are never subject to party loot mode votes — they bypass NeedGreed/RoundRobin/MasterLoot entirely.
- Personal loot is still subject to deferred recovery if the Arbiter crashes.

This prevents world boss loot drama and ensures every participant is rewarded proportionally to their Fortune investment.

#### Runtime Loot Event Multipliers

Drop rates and quality curves are globally tunable at runtime via the configuration registry (see [Configuration Registry](../4-infrastructure/02-configuration-registry.md)):

```json
{
  "global_loot_modifiers": {
    "drop_quantity_multiplier": 1.0,
    "drop_quality_bonus": 0.0,
    "bonus_roll_chance_additive": 0.0,
    "pity_accumulation_multiplier": 1.0,
    "unique_weight_multiplier": 1.0
  }
}
```

A "2x Loot Weekend" event sets `drop_quantity_multiplier: 2.0` and `drop_quality_bonus: 0.10`. These are applied in the drop evaluation pipeline before Fortune modifiers. Changes take effect on the next config reload signal (no restart required).

#### Anti-Exploit Protections

**Crash farming prevention:** The deferred recovery system is designed to make crash exploitation unprofitable:
- Deferred drops enter a 24-hour claim window but do NOT re-roll. The item instance was created at `MonsterDied` time — crashing the Arbiter doesn't give a second chance at better loot.
- Deferred drops are only claimable at a Loot Reclamation NPC, requiring the player to travel there. No automated collection.
- An abuse detection heuristic tracks the ratio of `DEFERRED` to `CLAIMED` drops per character. If a character has an abnormally high deferral rate (suggesting intentional crash exploitation), an alert is raised for GM review.

**Loot lockout window:** After a world boss is killed, participating entities are flagged with a lockout (`loot.boss_lockouts`) preventing them from being eligible for the same boss's drop table within the cooldown period. This prevents kill-cycling.

**Eligible entity validation:** The `participating_entities` list is authored by the Arbiter at `MonsterDied` emit time based on actual damage/healing contribution. The Loot Service trusts this list and does not re-evaluate eligibility. An entity that wasn't in the fight cannot claim the drop.

#### Designer Configuration

```json
{
  "$schema": "meta/loot/v1",
  "drop_tables_file": "data/drop-tables.json",
  "quality_curves": {
    "standard": {
      "common_threshold": 0.60,
      "uncommon_threshold": 0.85,
      "rare_threshold": 0.96,
      "epic_threshold": 0.995
    },
    "boss_elevated": {
      "common_threshold": 0.20,
      "uncommon_threshold": 0.55,
      "rare_threshold": 0.85,
      "epic_threshold": 0.97
    }
  },
  "fortune_quality_coefficient": 0.001,
  "fortune_pity_coefficient": 0.005,
  "pity": {
    "pity_weight_per_kill": 2,
    "pity_hard_threshold": 200
  },
  "loot_rules": {
    "party_loot_modes": ["FreeForAll", "RoundRobin", "NeedGreed", "MasterLoot"],
    "default_party_loot_mode": "FreeForAll",
    "loot_despawn_timer_seconds": 300,
    "round_robin_claim_timeout_seconds": 60,
    "need_greed_vote_timeout_seconds": 30,
    "master_loot_assign_timeout_seconds": 120
  },
  "world_boss": {
    "lockout_cooldown_hours": 24,
    "min_contribution_threshold_pct": 0.02
  },
  "deferred_recovery": {
    "claim_window_hours": 24,
    "reclamation_npc_type_id": 8001,
    "abuse_alert_deferral_ratio_threshold": 0.50,
    "abuse_alert_min_sample_size": 20
  },
  "global_loot_modifiers": {
    "drop_quantity_multiplier": 1.0,
    "drop_quality_bonus": 0.0,
    "bonus_roll_chance_additive": 0.0,
    "pity_accumulation_multiplier": 1.0,
    "unique_weight_multiplier": 1.0
  }
}
```

#### Database Schema

```sql
-- schema: loot

-- Runtime loot tracking (state machine).
-- Each row represents a single dropped item in the world or in deferred recovery.
CREATE TABLE loot.drops (
    drop_id             UUID PRIMARY KEY,
    table_id            TEXT NOT NULL,           -- Which drop table produced this
    monster_type_id     SMALLINT NOT NULL,
    instance_id         BIGINT NOT NULL,         -- References inventory.item_instances
    base_item_id        SMALLINT NOT NULL,       -- Denormalized for quick queries
    quality_tier        SMALLINT NOT NULL,
    quantity            INTEGER NOT NULL DEFAULT 1,
    location_x          BIGINT NOT NULL,         -- Vec2F.x as i64 bits
    location_y          BIGINT NOT NULL,
    arbiter_id          INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'ROLLED',
    -- ROLLED → SPAWNED → CLAIMED (normal)
    -- ROLLED → SPAWNED → DEFERRED → CLAIMED (crash recovery)
    -- ROLLED → SPAWNED → DEFERRED → EXPIRED (unclaimed)
    eligible_entities   JSONB NOT NULL,          -- participating_entities from MonsterDied
    party_loot_mode     TEXT,                    -- Loot mode at time of drop (for deferred recovery)
    assigned_to         UUID,                    -- character_id for RoundRobin/MasterLoot assignment
    claimed_by          UUID,                    -- character_id on claim
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    despawn_at          TIMESTAMPTZ NOT NULL,
    deferred_at         TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ              -- Set when transitioning to DEFERRED
);

-- Bad luck protection counters (per character, per drop table, per unique item).
CREATE TABLE loot.pity_counters (
    character_id        UUID NOT NULL,
    table_id            TEXT NOT NULL,
    item_id             SMALLINT NOT NULL,       -- The unique/rare item being tracked
    kill_count          INTEGER NOT NULL DEFAULT 0,
    last_drop_at        TIMESTAMPTZ,             -- When the item last dropped (NULL = never)
    PRIMARY KEY (character_id, table_id, item_id)
);

-- World boss lockouts (prevents kill-cycling for loot).
CREATE TABLE loot.boss_lockouts (
    character_id        UUID NOT NULL,
    monster_type_id     SMALLINT NOT NULL,
    locked_until        TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (character_id, monster_type_id)
);

CREATE INDEX idx_drops_status ON loot.drops (status) WHERE status IN ('SPAWNED', 'DEFERRED');
CREATE INDEX idx_drops_arbiter ON loot.drops (arbiter_id, status);
CREATE INDEX idx_drops_eligible ON loot.drops USING gin (eligible_entities);
CREATE INDEX idx_pity_character ON loot.pity_counters (character_id);
CREATE INDEX idx_lockouts_character ON loot.boss_lockouts (character_id);
```

#### Open Questions (Resolved)

| Original Question | Resolution |
|:---|:---|
| Drop table weighting algorithm? | **Weighted random selection** from filtered entry pool. Unique/rare entries use a **pity system** with per-character counters that increase weight over time. Fortune attribute accelerates pity. |
| Runtime loot rate tuning? | **Yes.** Global loot modifiers (quantity, quality, pity, unique weight) are hot-reloadable via the configuration registry. |
| Party loot + crash recovery? | **NeedGreed vote state is ephemeral (Redis)**. On crash, vote expires and deferred recovery restarts the vote at the Loot Reclamation NPC. The Postgres `loot.drops` row is the single source of truth — dupe-free by atomic status transition. |
| World boss loot? | **Per-participant personal rolls.** Each entity gets independent table evaluation with their own Fortune modifier. No shared loot pile. |
| Anti-exploit protections? | **Three layers:** (1) Deferred drops don't re-roll. (2) Abuse heuristic on deferral ratio. (3) World boss lockout cooldowns. |

#### Remaining Open Questions
- Should drop tables support "loot tiers" (e.g., tier 1 monsters share a common pool, tier 2 share a different one) to reduce config duplication?
- Should there be a "bonus loot" system for first kill of the day / week?
- How does Fortune interact with guaranteed drops? (It shouldn't — guaranteed drops are always granted regardless of Fortune.)
- Should crafting materials have their own separate drop table or be embedded in the monster's main table?

---

### 4.3 Currency & Trading Service

**Responsibility:** Manages all currency wallets (gold, premium currency, PvP tokens, etc.), NPC vendor transactions, player-to-player trading, and the auction house.

#### Locked-In Contracts

From §9.8.2, the following are atomic database transactions within Meta (no cross-layer ledger needed):
- Player-to-player trade — atomic database transaction
- Sell item to NPC vendor — item removed, gold added, same transaction

From §9.9 (`InboxReason`):
```rust
InboxReason::AuctionPurchase  // Bought an item while offline
```

#### Designer Configuration

```json
{
  "$schema": "meta/currency-trading/v1",
  "currencies": [
    {
      "currency_id": "gold",
      "display_name": "Gold",
      "max_wallet_balance": "TBD",
      "decimal_places": 0
    },
    {
      "currency_id": "premium_gems",
      "display_name": "Gems",
      "max_wallet_balance": "TBD",
      "decimal_places": 0
    }
  ],
  "vendors": {
    "npc_vendor_definitions": "TBD: reference to vendor data file",
    "buy_price_multiplier": 1.0,
    "sell_price_multiplier": 0.25
  },
  "trading": {
    "player_trade_enabled": true,
    "max_items_per_trade": "TBD",
    "trade_distance_limit": "TBD: max distance between players in simulation units",
    "trade_cooldown_seconds": "TBD"
  },
  "auction_house": {
    "enabled": "TBD",
    "listing_fee_pct": "TBD",
    "sale_tax_pct": "TBD",
    "max_listing_duration_hours": "TBD",
    "max_active_listings_per_character": "TBD"
  }
}
```

#### Database Schema (TBD)

```sql
-- schema: currency

CREATE TABLE currency.wallets (
    character_id    UUID NOT NULL,
    currency_id     TEXT NOT NULL,
    balance         BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, currency_id),
    CONSTRAINT positive_balance CHECK (balance >= 0)
);

-- TBD: currency.transaction_log for audit trail

CREATE TABLE currency.auction_listings (
    listing_id      UUID PRIMARY KEY,
    seller_id       UUID NOT NULL,
    item_id         SMALLINT NOT NULL,
    quantity        INTEGER NOT NULL,
    buyout_price    BIGINT NOT NULL,
    currency_id     TEXT NOT NULL DEFAULT 'gold',
    listed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'ACTIVE'  -- ACTIVE|SOLD|EXPIRED|CANCELLED
);

-- TBD: currency.trade_sessions for in-progress player-to-player trades
-- TBD: currency.vendor_definitions (or loaded from JSON config)
```

#### Open Questions
- Is there a real-money / premium currency? If so, how does it interact with the in-game economy?
- Should the auction house be regional (per-shard) or global?
- What anti-gold-farming protections are needed? (Trade limits, velocity checks?)
- How do NPC vendor inventories work? (Static stock, rotating stock, player-influenced?)
- Should there be a gold sink (repair costs, teleportation fees, etc.)?

---

### 4.4 Transaction & Recovery Service

**Responsibility:** Manages the `PendingTransaction` ledger for cross-layer operations (item consumed → ephemeral effect delivered), performs login-time reconciliation, and manages the Recovery Inbox.

#### Locked-In Contracts

**PendingTransaction Ledger** (§9.8):
```
PendingTransaction {
    tx_id: UUID,
    character_id,
    tx_type: ConsumeItem,
    item_id,
    arbiter_id,
    created_at: now,
    status: PENDING
}
```
- `PENDING` → `CONFIRMED` on `HardEvent::TransactionConfirmed { tx_id }`
- `PENDING` → `REFUNDED` on login-time reconciliation (timeout: 30 seconds)

**Recovery Inbox** (§9.9):
```rust
struct InboxEntry {
    entry_id: UUID,
    character_id: UUID,
    item_id: u16,
    quantity: u32,
    reason: InboxReason,
    source_tx_id: Option<UUID>,
    created_at: Timestamp,
    claimed: bool,
}

enum InboxReason {
    CrashRefund,
    DeferredLoot,
    AuctionPurchase,
    GmCompensation,
    EventReward,
}
```

Reconciliation runs during the Spawn Handshake (§9.5/§9.8.3):
1. Query `PENDING` transactions older than `TRANSACTION_TIMEOUT`
2. Mark as `REFUNDED`
3. Restore items to Recovery Inbox

On `ArbiterCrashedEvent`, this service MAY proactively mark affected transactions as `REFUNDED` (or wait for login-time reconciliation).

#### Designer Configuration

```json
{
  "$schema": "meta/transaction-recovery/v1",
  "transaction_ledger": {
    "pending_timeout_seconds": 30,
    "max_pending_per_character": "TBD"
  },
  "recovery_inbox": {
    "retention_days": 30,
    "max_unclaimed_entries": "TBD",
    "ui_display_reasons": {
      "CrashRefund": "Server disruption — your {item_name} has been returned.",
      "DeferredLoot": "Unclaimed reward from {source_name}.",
      "AuctionPurchase": "Your auction purchase has arrived.",
      "GmCompensation": "Compensation from the game team.",
      "EventReward": "Seasonal event reward."
    }
  }
}
```

#### Database Schema (TBD)

```sql
-- schema: transactions

CREATE TABLE transactions.pending (
    tx_id           UUID PRIMARY KEY,
    character_id    UUID NOT NULL,
    tx_type         TEXT NOT NULL,          -- e.g., 'ConsumeItem'
    item_id         SMALLINT,
    quantity        INTEGER NOT NULL DEFAULT 1,
    arbiter_id      INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING|CONFIRMED|REFUNDED
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);

CREATE TABLE transactions.recovery_inbox (
    entry_id        UUID PRIMARY KEY,
    character_id    UUID NOT NULL,
    item_id         SMALLINT NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1,
    reason          TEXT NOT NULL,          -- Maps to InboxReason enum
    source_tx_id    UUID,                  -- Links back to pending transaction
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed         BOOLEAN NOT NULL DEFAULT false,
    claimed_at      TIMESTAMPTZ
);

CREATE INDEX idx_pending_character ON transactions.pending (character_id, status);
CREATE INDEX idx_inbox_character ON transactions.recovery_inbox (character_id, claimed);
```

#### Open Questions
- Should reconciliation be proactive (on `ArbiterCrashedEvent`) or lazy (on next login), or both?
- What happens if the player's inventory is full when they try to claim an inbox entry?
- Should there be an admin tool for manually creating Recovery Inbox entries (GM compensation)?
- Is there a cap on the number of pending transactions per character?

---

## 5. Progression

### 5.1 Progression Service

**Responsibility:** Manages XP accumulation, level-ups, attribute point allocation, talent point allocation, and skill slot unlocks. Consumes kill and objective events from the Event Bus and updates persistent character progression. On level-up, notifies the Inventory Service to trigger stat recompilation.

#### Locked-In Contracts

From §9.7.4: *"Level, XP, quest progress — Updated by Meta when it consumes `HardEvent` from the Event Bus."*

Events consumed:
- `HardEvent::PlayerDied { killer, victim, respawn_delay_credit_ticks, respawn_override }` — PvP kill credit XP for the killer
- `HardEvent::MonsterDied { killer, monster_type_id, participating_entities }` — PvE XP for participants
- `HardEvent::ObjectiveCaptured { team, zone }` — objective XP for team members

The Progression Service does NOT directly push to the Arbiter. When a level-up grants new attribute points and the player allocates them, the Inventory Service recompiles `PrimaryAttributes` → derived stats and pushes `UpdateEntityStats`.

#### XP Curve

XP required per level follows an exponential curve:

```
xp_required(level) = base_xp × level^exponent
```

This creates a smooth curve where early levels are fast and later levels slow down progressively. The specific `base_xp` and `exponent` values are designer-configurable. Example at `base_xp = 100, exponent = 1.8`:

| Level | XP Required | Cumulative |
|:---|:---|:---|
| 2 | 348 | 348 |
| 10 | 6,310 | ~25,000 |
| 25 | 31,623 | ~350,000 |
| 50 | 110,000 | ~2,500,000 |

#### XP Sources

**Monster Kill XP:**
Each monster type has a `base_xp` value defined in the monster data file. XP is scaled by the level difference between the killer and the monster:

```
effective_xp = monster_base_xp × level_difference_multiplier(killer_level, monster_level)

level_difference_multiplier(killer, monster):
    diff = killer - monster
    if diff > max_overlevel_penalty:   return 0.0    // Too easy, no XP
    if diff > 0:                       return 1.0 - (diff × overlevel_penalty_per_level)
    if diff < -max_underlevel_bonus:   return max_underlevel_multiplier
    if diff < 0:                       return 1.0 + (abs(diff) × underlevel_bonus_per_level)
    return 1.0
```

**PvP Kill XP:**
```
pvp_xp = player_kill_base_xp × (victim_level / killer_level) × level_diff_scaling
```
- Capped at `max_pvp_xp_per_kill` to prevent boosting.
- A **diminishing returns tracker** per (killer, victim) pair decays the XP reward for repeatedly killing the same player. Resets after `pvp_diminishing_reset_hours`.

**Objective Capture XP:** Flat XP per objective definition, awarded to all team members present at the capture.

**Quest Completion XP:** Defined per quest in the quest data file. Awarded on quest turn-in.

#### Party XP Sharing (Contribution-Weighted)

When a monster dies with multiple `participating_entities`, XP is distributed proportionally to each entity's contribution:

```
distribute_party_xp(total_xp, participating_entities, contributions):
    // contributions = { entity_id: { damage_dealt, healing_done } }

    // 1. Calculate weighted contribution per entity
    //    Healing counts at a boosted rate to protect support roles
    for entity in participating_entities:
        weighted = contributions[entity].damage_dealt
                 + contributions[entity].healing_done × healing_contribution_multiplier
        entity.weighted_contribution = weighted

    // 2. Compute each entity's share
    total_weighted = sum(entity.weighted_contribution for entity in participating_entities)
    for entity in participating_entities:
        share_pct = entity.weighted_contribution / total_weighted

        // 3. Minimum contribution threshold (anti-AFK leeching)
        if share_pct < min_contribution_threshold_pct:
            continue  // No XP for negligible contribution

        // 4. Apply party bonus (grouping is rewarded)
        party_bonus = 1.0 + (party_size - 1) × party_bonus_per_member
        entity_xp = total_xp × share_pct × party_bonus

        grant_xp(entity, entity_xp)
```

- `healing_contribution_multiplier`: Configurable boost so healers aren't penalized (default: 1.5).
- `party_bonus_per_member`: Small bonus per additional party member (default: 0.10 → a 5-person party gets +40% total XP). This ensures grouping is always net-positive.
- `min_contribution_threshold_pct`: Below this threshold, no XP is awarded (default: 0.02 → must contribute at least 2%).
- Proximity requirement: Only entities within `max_party_xp_share_distance` of the kill are eligible. Distance is checked against the monster's death location, not the killer's position.

#### Leveling Rewards

Each level grants three types of rewards:

**1. Attribute Points** — the primary reward. Distributed freely across the 12 Minor Attributes by the player via `MetaRequest::AllocateAttributePoints`.

```
attribute_points_per_level = base_attribute_points + floor(level / attribute_points_bonus_interval)
```
Early levels grant fewer points; later levels grant slightly more to maintain progression feel.

**2. Talent Points** — one point per level, invested in the talent tree system (see below).

**3. Skill Slot Unlocks** — at milestone levels, new ability slots or passive tiers are unlocked. Defined in the designer config as a level → unlock mapping:

```json
{
  "milestone_unlocks": [
    { "level": 1,  "unlock": "ability_slot_1" },
    { "level": 3,  "unlock": "ability_slot_2" },
    { "level": 5,  "unlock": "passive_slot_1" },
    { "level": 8,  "unlock": "ability_slot_3" },
    { "level": 12, "unlock": "passive_slot_2" },
    { "level": 18, "unlock": "ability_slot_4" },
    { "level": 25, "unlock": "passive_slot_3" },
    { "level": 35, "unlock": "ability_slot_5" },
    { "level": 50, "unlock": "passive_slot_4" }
  ]
}
```

#### Talent Tree System

Four talent trees aligned with the four Major Attributes: **Body**, **Mind**, **Soul**, and **Fate**. Any character can invest in any tree — build identity comes from which trees you go deep in, not from a class selection.

Talent definitions are loaded from a **JSON asset file** (`data/talent-trees.json`), versioned via the `DataEpoch` pipeline.

```json
{
  "$schema": "data/talent-trees/v1",
  "trees": [
    {
      "tree_id": "body",
      "display_name": "Body",
      "description": "Physical combat, survivability, and material mastery.",
      "tiers": [
        {
          "tier": 1,
          "required_points_in_tree": 0,
          "nodes": [
            {
              "node_id": "body_t1_vigor_boost",
              "display_name": "Ironblood",
              "description": "+3% Physical Damage per rank",
              "max_rank": 5,
              "effect_per_rank": {
                "derived_bonus": { "physical_damage_multiplier": 0.03 }
              }
            },
            {
              "node_id": "body_t1_endurance_boost",
              "display_name": "Thick Skin",
              "description": "+2% Max HP per rank",
              "max_rank": 5,
              "effect_per_rank": {
                "derived_bonus": { "max_hp_pct": 0.02 }
              }
            }
          ]
        },
        {
          "tier": 2,
          "required_points_in_tree": 5,
          "nodes": [
            {
              "node_id": "body_t2_block_reflect",
              "display_name": "Retribution",
              "description": "Blocking an attack reflects 10% of blocked damage per rank",
              "max_rank": 3,
              "effect_per_rank": {
                "unique_modifier": "block_reflect_pct",
                "value": 0.10
              }
            }
          ]
        },
        {
          "tier": 5,
          "required_points_in_tree": 25,
          "is_keystone": true,
          "nodes": [
            {
              "node_id": "body_t5_unstoppable",
              "display_name": "Unstoppable Force",
              "description": "KEYSTONE: While above 80% HP, you are immune to stagger and movement-impairing effects. +25% Poise.",
              "max_rank": 1,
              "effect_per_rank": {
                "keystone": "unstoppable_force"
              },
              "exclusive_with": ["body_t5_immovable"]
            },
            {
              "node_id": "body_t5_immovable",
              "display_name": "Immovable Object",
              "description": "KEYSTONE: Block chance applies to spells. Block effectiveness increased to 75%. -20% Movement Speed.",
              "max_rank": 1,
              "effect_per_rank": {
                "keystone": "immovable_object"
              },
              "exclusive_with": ["body_t5_unstoppable"]
            }
          ]
        }
      ]
    },
    {
      "tree_id": "fate",
      "display_name": "Fate",
      "description": "Fortune manipulation, social influence, and exploiting opportunity.",
      "tiers": [
        {
          "tier": 1,
          "required_points_in_tree": 0,
          "nodes": [
            {
              "node_id": "fate_t1_fortune_boost",
              "display_name": "Lucky Star",
              "description": "+2% Proc Chance per rank",
              "max_rank": 5,
              "effect_per_rank": {
                "derived_bonus": { "proc_chance_multiplier": 0.02 }
              }
            },
            {
              "node_id": "fate_t1_cunning_boost",
              "display_name": "Opportunist",
              "description": "+3% Damage to debuffed targets per rank",
              "max_rank": 5,
              "effect_per_rank": {
                "derived_bonus": { "debuff_bonus_damage": 0.03 }
              }
            }
          ]
        },
        {
          "tier": 5,
          "required_points_in_tree": 25,
          "is_keystone": true,
          "nodes": [
            {
              "node_id": "fate_t5_loaded_dice",
              "display_name": "Loaded Dice",
              "description": "KEYSTONE: Critical strikes have a 25% chance to not consume the crit roll (can chain-crit). +50% Loot Rarity.",
              "max_rank": 1,
              "effect_per_rank": {
                "keystone": "loaded_dice"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

**Talent node types:**
- **Passive stat bonus**: Grants a flat or percentage derived stat bonus per rank. Applied during stat compilation.
- **Unique modifier**: Grants a gameplay mechanic that doesn't map to a standard derived stat (e.g., "block reflects damage"). Implemented as a flag or parameter on the entity that the Arbiter checks during specific game logic.
- **Keystone**: Powerful, build-defining passive. Max 1 rank. Found at the deepest tiers. Keystones within the same tier may be `exclusive_with` each other — choosing one locks out the other.

Talent bonuses from `derived_bonus` entries are included in the stat compilation pipeline alongside equipment contributions. The Inventory Service queries `progression.talent_allocations` during compilation and adds their bonuses during the "direct derived bonus" phase.

#### Respec System

**Attribute respec** and **talent respec** are separate operations:
- **Attribute respec**: Refunds all allocated attribute points. Cost: `base_respec_cost × level` in gold. Cooldown: configurable (default 24 hours). Triggers stat recompilation.
- **Talent respec**: Refunds all allocated talent points. Same cost formula. Same cooldown. Triggers stat recompilation.
- Both operations are atomic — all points are refunded, not individual nodes. This prevents min-maxing by partially respeccing.
- Respec is available at any NPC with a `respec_service` interaction type.

#### Designer Configuration

```json
{
  "$schema": "meta/progression/v1",
  "leveling": {
    "max_level": 60,
    "xp_curve": {
      "base_xp": 100,
      "exponent": 1.8
    },
    "xp_rewards": {
      "monster_xp_file": "data/monster-xp.json",
      "player_kill_base_xp": 50,
      "max_pvp_xp_per_kill": 500,
      "pvp_diminishing_reset_hours": 24,
      "objective_capture_xp_file": "data/objective-xp.json"
    },
    "level_scaling": {
      "overlevel_penalty_per_level": 0.10,
      "max_overlevel_penalty": 8,
      "underlevel_bonus_per_level": 0.05,
      "max_underlevel_multiplier": 1.5
    },
    "xp_sharing": {
      "party_xp_split_mode": "contribution_weighted",
      "healing_contribution_multiplier": 1.5,
      "party_bonus_per_member": 0.10,
      "min_contribution_threshold_pct": 0.02,
      "max_party_xp_share_distance": 5000
    }
  },
  "rewards": {
    "base_attribute_points_per_level": 5,
    "attribute_points_bonus_interval": 10,
    "talent_points_per_level": 1,
    "milestone_unlocks_file": "data/milestone-unlocks.json"
  },
  "talents": {
    "talent_trees_file": "data/talent-trees.json"
  },
  "respec": {
    "base_respec_cost_gold": 100,
    "respec_cost_level_multiplier": 1.0,
    "respec_cooldown_hours": 24
  },
  "paragon": {
    "enabled": false,
    "paragon_xp_curve": "TBD: deferred pending endgame design"
  },
  "global_xp_modifiers": {
    "xp_multiplier": 1.0,
    "party_bonus_multiplier": 1.0
  }
}
```

#### Database Schema

```sql
-- schema: progression

CREATE TABLE progression.character_level (
    character_id        UUID PRIMARY KEY,
    level               INTEGER NOT NULL DEFAULT 1,
    current_xp          BIGINT NOT NULL DEFAULT 0,
    total_xp_earned     BIGINT NOT NULL DEFAULT 0,
    attribute_points    INTEGER NOT NULL DEFAULT 0,  -- Total granted (level-based)
    talent_points       INTEGER NOT NULL DEFAULT 0,  -- Total granted (1 per level)
    unspent_attribute   INTEGER NOT NULL DEFAULT 0,
    unspent_talent      INTEGER NOT NULL DEFAULT 0,
    last_respec_at      TIMESTAMPTZ                  -- NULL if never respecced
);

-- Talent tree allocations (character → node → rank)
CREATE TABLE progression.talent_allocations (
    character_id        UUID NOT NULL,
    tree_id             TEXT NOT NULL,           -- 'body', 'mind', 'soul', 'fate'
    node_id             TEXT NOT NULL,           -- References talent-trees.json
    current_rank        INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (character_id, node_id)
);

-- Skill slot unlocks (tracks which milestone unlocks a character has earned)
CREATE TABLE progression.skill_unlocks (
    character_id        UUID NOT NULL,
    unlock_id           TEXT NOT NULL,           -- e.g., 'ability_slot_3', 'passive_slot_2'
    unlocked_at_level   INTEGER NOT NULL,
    PRIMARY KEY (character_id, unlock_id)
);

-- PvP diminishing returns tracker (prevents kill-trading for XP)
CREATE TABLE progression.pvp_diminishing (
    killer_id           UUID NOT NULL,
    victim_id           UUID NOT NULL,
    kill_count          INTEGER NOT NULL DEFAULT 1,
    first_kill_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_kill_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (killer_id, victim_id)
);

-- Paragon levels (schema reserved, not yet active)
CREATE TABLE progression.paragon (
    character_id        UUID PRIMARY KEY,
    paragon_level       INTEGER NOT NULL DEFAULT 0,
    paragon_xp          BIGINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_talent_character ON progression.talent_allocations (character_id);
CREATE INDEX idx_pvp_dim_reset ON progression.pvp_diminishing (last_kill_at);
```

#### Open Questions (Resolved)

| Original Question | Resolution |
|:---|:---|
| XP curve? | **Exponential:** `base_xp × level^exponent`. Designer-configurable base and exponent. |
| Party XP sharing? | **Contribution-weighted** with healing boost multiplier, party bonus per member, and minimum contribution threshold. |
| PvP XP boosting? | **Diminishing returns** per (killer, victim) pair. Resets after configurable hours. Max PvP XP per kill capped. |
| Talent trees class-specific? | **No.** Four universal trees aligned with Major Attributes (Body, Mind, Soul, Fate). Any character can invest in any tree. |
| Respec? | **Yes.** Full refund of all attribute or talent points. Gold cost scales with level. 24-hour cooldown. |
| Prestige/paragon? | **Deferred.** Schema reserved (`progression.paragon`), config placeholder exists, not yet active. |

#### Remaining Open Questions
- Should talent keystones have additional requirements beyond points invested (e.g., minimum Major Attribute threshold)?
- How do talent "unique modifiers" and "keystones" interact with the Arbiter? (Flags on the entity record? Special status effects?)
- Should there be seasonal XP events with different multiplier stacking rules?

---

### 5.2 Quest & Achievement Service

**Responsibility:** Manages quest definitions, objective tracking, quest state machines, quest chain/branching logic, daily/weekly reset timers, achievements, and reward dispatching. Consumes relevant events from the Event Bus to advance quest objectives automatically.

#### Locked-In Contracts

Events consumed for quest/achievement progress:
- `HardEvent::MonsterDied` — "Kill 10 wolves" type objectives
- `HardEvent::PlayerDied` — PvP kill objectives
- `HardEvent::ObjectiveCaptured` — territory control objectives
- `HardEvent::LootClaimed` — collection objectives

Quest rewards are dispatched to the appropriate services:
- XP → Progression Service
- Gold → Currency Service
- Items → Inventory Service (creates item instances)
- Attribute points → Progression Service
- Unlocks → Quest Service (unlocks next quest in chain, zone access flags)

Quest progress is **crash-safe by design** — all progress is stored in Meta's Postgres database. An Arbiter crash cannot lose quest progress because the Event Bus guarantees at-least-once delivery and the Quest Service is an idempotent consumer.

#### Quest Definition Asset File

Quest definitions are loaded from a **JSON asset file** (`data/quests.json`), versioned via the `DataEpoch` pipeline.

```json
{
  "$schema": "data/quests/v1",
  "quests": [
    {
      "quest_id": "main_001_wolf_problem",
      "display_name": "A Wolf Problem",
      "description": "The village elder needs someone to thin the wolf population threatening the farmlands.",
      "category": "main_story",
      "required_level": 3,
      "required_attributes": {},
      "prerequisites": [],
      "objectives": [
        {
          "objective_id": "kill_wolves",
          "type": "KillMonster",
          "target_id": 1001,
          "required_count": 10,
          "description": "Slay wolves in the Thornwall Farmlands"
        },
        {
          "objective_id": "collect_pelts",
          "type": "CollectItem",
          "target_id": 2050,
          "required_count": 5,
          "description": "Collect wolf pelts"
        }
      ],
      "objective_mode": "all",
      "rewards": {
        "xp": 500,
        "gold": 100,
        "items": [{ "item_id": 1010, "quantity": 1, "quality_tier": 1 }],
        "attribute_points": 0,
        "unlocks": ["main_002_alpha_hunt"]
      },
      "turn_in_npc_type_id": 7001,
      "repeatable": false,
      "group_quest": false
    },
    {
      "quest_id": "daily_bounty_wolves",
      "display_name": "Daily Bounty: Wolves",
      "description": "The bounty board offers a standing reward for wolf control.",
      "category": "daily",
      "required_level": 5,
      "prerequisites": ["main_001_wolf_problem"],
      "objectives": [
        {
          "objective_id": "kill_wolves_daily",
          "type": "KillMonster",
          "target_id": 1001,
          "required_count": 5,
          "description": "Slay wolves (daily)"
        }
      ],
      "objective_mode": "all",
      "rewards": {
        "xp": 200,
        "gold": 50,
        "items": [],
        "attribute_points": 0,
        "unlocks": []
      },
      "repeatable": true,
      "reset_schedule": { "type": "daily", "reset_hour_utc": 6 },
      "group_quest": false
    },
    {
      "quest_id": "branch_mercy_or_justice",
      "display_name": "The Bandit's Plea",
      "description": "A captured bandit begs for mercy. The guard captain demands justice.",
      "category": "side",
      "required_level": 15,
      "prerequisites": ["side_010_bandit_camp"],
      "objectives": [
        {
          "objective_id": "spare_bandit",
          "type": "TalkToNPC",
          "target_id": 7050,
          "required_count": 1,
          "description": "Speak to the bandit and grant mercy"
        },
        {
          "objective_id": "execute_bandit",
          "type": "TalkToNPC",
          "target_id": 7051,
          "required_count": 1,
          "description": "Report to the guard captain for execution"
        }
      ],
      "objective_mode": "any",
      "rewards": {
        "xp": 800,
        "gold": 200,
        "items": [],
        "attribute_points": 1,
        "unlocks": []
      },
      "branching_rewards": {
        "spare_bandit": {
          "unlocks": ["branch_bandit_ally"],
          "reputation": { "outlaws": 100, "guard": -50 }
        },
        "execute_bandit": {
          "unlocks": ["branch_guard_favor"],
          "reputation": { "guard": 100, "outlaws": -100 }
        }
      },
      "repeatable": false,
      "group_quest": false
    },
    {
      "quest_id": "group_dragon_siege",
      "display_name": "The Dragon Siege",
      "description": "Rally your party and defeat the dragon threatening Thornwall.",
      "category": "group",
      "required_level": 40,
      "prerequisites": ["main_030_dragon_awakening"],
      "objectives": [
        {
          "objective_id": "slay_dragon",
          "type": "KillMonster",
          "target_id": 5001,
          "required_count": 1,
          "description": "Defeat the Elder Dragon"
        }
      ],
      "objective_mode": "all",
      "rewards": {
        "xp": 5000,
        "gold": 1000,
        "items": [{ "item_id": 4010, "quantity": 1, "quality_tier": 3 }],
        "attribute_points": 2,
        "unlocks": ["main_031_aftermath"]
      },
      "repeatable": false,
      "reset_schedule": { "type": "weekly", "reset_day_utc": "monday", "reset_hour_utc": 6 },
      "group_quest": true
    }
  ]
}
```

**Objective types:**

| Type | `target_id` | Trigger Event |
|:---|:---|:---|
| `KillMonster` | `monster_type_id` | `HardEvent::MonsterDied` |
| `KillPlayer` | (none — any player) | `HardEvent::PlayerDied` |
| `CollectItem` | `base_item_id` | `HardEvent::LootClaimed` |
| `CaptureObjective` | `region_id` | `HardEvent::ObjectiveCaptured` |
| `TalkToNPC` | `npc_type_id` | `MetaRequest::InteractNPC` (via interaction system) |
| `ReachLocation` | `zone_id` | Position check on zone entry (Arbiter emits event) |
| `UseAbility` | `ability_id` | `HardEvent::AbilityUsed` (if added) or tracked by Arbiter |

**Objective modes:**
- `"all"` — All objectives must be completed (standard quest).
- `"any"` — Completing any single objective completes the quest (branching choice).

**Quest chains and branching:**
- `prerequisites` lists quest IDs that must be completed before this quest is available.
- `"unlocks"` in rewards lists quest IDs that become available on completion.
- `objective_mode: "any"` + `branching_rewards` enables branching: completing different objectives leads to different reward paths and unlocks different follow-up quests. This creates branching storylines without complex state machines — the quest graph is a DAG defined by prerequisite and unlock relationships.

**Group quests:**
When `group_quest: true`, objective progress is **shared among all party members**. If any party member kills the quest target, all party members with the quest active get credit. This is tracked by cross-referencing the `participating_entities` from `MonsterDied` against the `social.party_members` table.

**Daily/weekly resets:**
Quests with a `reset_schedule` can be repeated after the reset timer. On reset, the quest's status is set back to `AVAILABLE` and objective progress is cleared. The reset is processed by a scheduled job that runs at the configured UTC hour.

#### Achievement System

Achievements are loaded from `data/achievements.json`:

```json
{
  "$schema": "data/achievements/v1",
  "achievements": [
    {
      "achievement_id": "ach_wolf_slayer_100",
      "display_name": "Wolf Slayer",
      "description": "Slay 100 wolves.",
      "category": "combat",
      "criteria": {
        "type": "KillMonster",
        "target_id": 1001,
        "required_count": 100
      },
      "reward": {
        "title": "Wolf Slayer",
        "attribute_bonus": { "vigor": 2 },
        "cosmetic_id": null
      },
      "hidden": false
    },
    {
      "achievement_id": "ach_discover_hidden_shrine",
      "display_name": "???",
      "description": "???",
      "category": "exploration",
      "criteria": {
        "type": "ReachLocation",
        "target_id": "hidden_shrine_01",
        "required_count": 1
      },
      "reward": {
        "title": "Shrine Seeker",
        "attribute_bonus": { "resolve": 3 },
        "cosmetic_id": "aura_shimmer_01"
      },
      "hidden": true
    }
  ]
}
```

**Achievement rewards:**
- **Titles**: Display name prefix/suffix shown to other players.
- **Attribute bonuses**: Small permanent Minor Attribute bonuses. These are included in the stat compilation pipeline — the Inventory Service queries `quests.character_achievements` and sums all earned attribute bonuses during compilation. This means achievements are a meaningful (but small) progression vector.
- **Cosmetics**: Visual effects, auras, or transmog unlocks (tracked by ID, implementation deferred to client rendering).
- **Hidden achievements**: Name and description show as "???" until unlocked. Discovery is part of the fun.

Achievement progress is tracked via aggregate counters in `quests.achievement_progress`, updated incrementally as events flow through the Event Bus. Unlike quest objectives which reset, achievement counters are permanent.

#### Designer Configuration

```json
{
  "$schema": "meta/quests/v1",
  "quest_definitions_file": "data/quests.json",
  "achievement_definitions_file": "data/achievements.json",
  "quest_log": {
    "max_active_quests": 25,
    "max_tracked_quests": 5
  },
  "daily_reset_hour_utc": 6,
  "weekly_reset_day_utc": "monday",
  "group_quest_share_distance": 5000,
  "turn_in_interaction_range": 500
}
```

#### Database Schema

```sql
-- schema: quests

-- Character quest state (active, completed, or abandoned quests)
CREATE TABLE quests.character_quests (
    character_id    UUID NOT NULL,
    quest_id        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    -- IN_PROGRESS | COMPLETED | FAILED | ABANDONED | AVAILABLE (for repeatables after reset)
    accepted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    completion_count INTEGER NOT NULL DEFAULT 0,     -- For repeatable quests
    last_reset_at   TIMESTAMPTZ,                     -- For daily/weekly tracking
    branch_chosen   TEXT,                            -- Which objective was completed (for branching quests)
    PRIMARY KEY (character_id, quest_id)
);

-- Per-objective progress counters
CREATE TABLE quests.objective_progress (
    character_id    UUID NOT NULL,
    quest_id        TEXT NOT NULL,
    objective_id    TEXT NOT NULL,
    current_count   INTEGER NOT NULL DEFAULT 0,
    required_count  INTEGER NOT NULL,
    completed       BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (character_id, quest_id, objective_id)
);

-- Unlocked achievements
CREATE TABLE quests.character_achievements (
    character_id    UUID NOT NULL,
    achievement_id  TEXT NOT NULL,
    unlocked_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (character_id, achievement_id)
);

-- Achievement progress counters (permanent, never reset)
CREATE TABLE quests.achievement_progress (
    character_id    UUID NOT NULL,
    achievement_id  TEXT NOT NULL,
    current_count   INTEGER NOT NULL DEFAULT 0,
    required_count  INTEGER NOT NULL,
    PRIMARY KEY (character_id, achievement_id)
);

-- Reputation with factions (affected by quest choices and achievements)
CREATE TABLE quests.character_reputation (
    character_id    UUID NOT NULL,
    faction_id      TEXT NOT NULL,
    reputation      INTEGER NOT NULL DEFAULT 0,       -- Can be negative
    PRIMARY KEY (character_id, faction_id)
);

CREATE INDEX idx_quests_character ON quests.character_quests (character_id, status);
CREATE INDEX idx_quests_reset ON quests.character_quests (last_reset_at) WHERE status = 'AVAILABLE';
CREATE INDEX idx_ach_progress ON quests.achievement_progress (character_id);
CREATE INDEX idx_reputation ON quests.character_reputation (character_id);
```

#### Open Questions (Resolved)

| Original Question | Resolution |
|:---|:---|
| Quest chains / branching? | **DAG-based.** Prerequisites + unlocks define chains. `objective_mode: "any"` + `branching_rewards` enables branching storylines. |
| Daily/weekly quests? | **Yes.** `reset_schedule` with configurable UTC hour/day. Scheduled job resets status and clears progress. |
| Group quests? | **Shared progress.** Party members get credit when any member completes an objective, within range. |
| Quest progress survives crashes? | **Yes.** All progress in Meta's Postgres. Event Bus guarantees at-least-once delivery. Idempotent consumers. |
| Achievement rewards? | **Titles + small permanent attribute bonuses + cosmetics.** Attribute bonuses feed into stat compilation. Hidden achievements show "???" until unlocked. |

#### Remaining Open Questions
- Should there be a "quest journal" or "lore codex" system that records story fragments as quests are completed?
- How do escort / timed objectives work? (Requires Arbiter coordination for NPC escort state.)
- Should reputation unlock vendor inventories, ability variants, or zone access at thresholds?
- Can achievements grant unique talent tree nodes (e.g., a secret node unlocked by completing a hidden achievement)?

---

## 6. Social

### 6.1 Chat Service

**Responsibility:** Manages chat channels, message routing, content moderation, rate limiting, and player reporting. Operates entirely outside the Spatial Mesh — chat messages never touch an Arbiter.

#### Locked-In Contracts

From [Edge Node Envelopes §2.1](../2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md):
```rust
MetaRequest::SendChatMessage { channel: String, text: String }
MetaRequest::JoinChannel { channel: String }
MetaRequest::LeaveChannel { channel: String }
MetaRequest::BlockPlayer { target_character_name: String }
MetaRequest::UnblockPlayer { target_character_id: UUID }
MetaRequest::ReportPlayer { target_character_name: String, reason: ReportReason, details: String }

MetaResponse::ChatReceived { channel: String, sender: String, text: String }
MetaResponse::ChatError { reason: String }
MetaResponse::ChannelJoined { channel: String }
MetaResponse::ChannelLeft { channel: String }
MetaResponse::PlayerMuted { until: u64, reason: String }
MetaResponse::ReportAcknowledged { report_id: UUID }
```

The Edge Node routes `ClientMessage::Meta(MetaRequest)` directly to Meta Services, injecting the trusted `character_id`. The client cannot spoof the sender identity.

#### Channel Architecture

Chat channels are organized into three scoping tiers:

| Channel Type | Scope | Subscription Model | Examples |
|:---|:---|:---|:---|
| **System** | All connected players, server-wide | Auto-subscribed on login, cannot leave | `global`, `trade` |
| **Membership** | Scoped to social group roster | Auto-subscribed on group join, auto-removed on leave | `party:{party_id}`, `guild:{guild_id}` |
| **Direct** | 1:1 between two characters | Created on first whisper, ephemeral | `whisper:{character_id_a}:{character_id_b}` |
| **Custom** | Player-created, opt-in | Joined via `JoinChannel`, persisted across sessions | `custom:trade-rare-items`, `custom:pvp-lfg` |

**Channel ID conventions:**
- System channels use bare names: `global`, `trade`
- Membership channels are prefixed with the group type and ID: `party:550e8400-...`, `guild:6ba7b810-...`
- Whisper channels use a deterministic composite key: the two `character_id` UUIDs sorted lexicographically and joined by `:`, prefixed with `whisper:`
- Custom channels are prefixed with `custom:` and a slugified player-chosen name

**Routing implementation:** The Chat Service maintains an in-memory (Redis) pub/sub subscription map. Each online player's Edge Node subscribes to a per-session Redis channel (`chat:session:{session_id}`). When a chat message is accepted, the Chat Service resolves all recipients from the channel subscription map and publishes to each recipient's session channel. The Edge Node forwards the `ChatReceived` response to the physical client.

For **membership channels**, the Chat Service reads the current party/guild roster from the Party & Guild Service (direct Postgres read of `social.party_members` / `social.guild_members`) at message send time. There is no cached subscription list to go stale — membership is always authoritative.

**Whisper routing:** Whispers resolve the target by character name via the Session Manager. If the target is offline, the message is dropped with a `ChatError { reason: "Player is offline" }`. Whispers are not queued for offline delivery.

#### Rate Limiting

Rate limits are enforced per-character using Redis sliding window counters (`chat:rate:{character_id}:{channel_type}`).

| Limit | Threshold | Window | Consequence |
|:---|:---|:---|:---|
| Global/Trade messages | 8 messages | 60 seconds | `ChatError`, message dropped |
| Party/Guild messages | 20 messages | 60 seconds | `ChatError`, message dropped |
| Whisper messages | 15 messages | 60 seconds | `ChatError`, message dropped |
| Duplicate message | Identical text | 5 seconds | `ChatError`, message silently dropped |
| Burst | 4 messages | 3 seconds | 10-second send cooldown on that channel |

If a player hits the rate limit 3 times within 10 minutes, a 5-minute automatic soft mute is applied (system channels only; party/guild/whisper unaffected).

#### Spam Detection

Beyond rate limiting, a lightweight spam detection pipeline runs on every message before delivery:

1. **Profanity filter** — Server-side regex match against a word list (`meta/chat/profanity_wordlist.txt`). Matched words are replaced with `***` but the message is still delivered. Repeated profanity (5+ filtered messages in 10 minutes) escalates to auto-mute.
2. **Repetition detector** — If a player sends the same message (or >80% Levenshtein similarity) 3 times within 30 seconds, subsequent duplicates are silently dropped.
3. **Link/URL filter** — Messages containing URLs in `global` or `trade` channels are held for a 2-second delay and checked against a block list. Allowed domains (e.g., the game's own site) pass through immediately.
4. **Character flood** — Messages with >70% of the same character or >10 consecutive repeated characters are silently dropped.

All spam detection operates as a stateless pipeline. No ML models or external services are required. The word list and URL block list are loaded from the config asset file and hot-reloadable via `DataEpoch`.

#### Moderation System

**Mute escalation ladder:**

| Offense Count | Mute Duration | Source |
|:---|:---|:---|
| 1st | 10 minutes | Auto (spam detection) or GM |
| 2nd | 1 hour | Auto or GM |
| 3rd | 24 hours | Auto or GM |
| 4th+ | 7 days | GM only |
| Permanent | Indefinite | GM only (manual review required) |

Offense count tracks total mutes within a rolling 30-day window. Mute state is stored in `chat.mutes` with an expiration timestamp. The Chat Service checks mute status on every `SendChatMessage` before any other processing — muted players receive `ChatError { reason: "You are muted until ..." }`.

**Player blocking:** When a player blocks another via `BlockPlayer`, the block is stored in `chat.blocked_players`. Blocked players' messages are filtered at the recipient's Edge Node (the Chat Service still routes the message to all subscribers, but marks it with a `blocked: true` flag so the Edge Node can drop it before forwarding to the client). This ensures the blocker sees no messages from the blocked player in any channel, including party and guild.

**Player reporting:** `ReportPlayer` creates a row in `chat.reports`. Reports are batched and surfaced to GMs via an admin dashboard (out of scope for this document). When a player accumulates a configurable threshold of unique reporters (default: 5 unique reporters in 24 hours), the system auto-mutes the player for the current escalation tier and flags the account for GM review.

**GM commands:** GMs interact with the moderation system via an admin RPC interface (not the game client). Available actions:
- Mute/unmute a player (with reason)
- Ban a player (suspends the account; handled by Identity & Session Service)
- View chat history for a player or channel (reads `chat.messages`)
- Clear a player's offense counter
- Add/remove entries from the profanity word list

#### Message Persistence

Chat messages are persisted to `chat.messages` for **moderation audit and GM review**. Messages are NOT persisted for client-side chat history — the client maintains its own local scrollback buffer. The server-side message log is retained for a configurable duration (default: 30 days) and then purged by a scheduled job. Whisper messages are also logged for harassment investigation.

#### Designer Configuration

```json
{
  "$schema": "meta/chat/v1",
  "channels": {
    "predefined": [
      { "channel_id": "global", "display_name": "Global", "type": "system", "max_message_length": 500, "color": "#FFFFFF" },
      { "channel_id": "trade", "display_name": "Trade", "type": "system", "max_message_length": 500, "color": "#FFAA00" },
      { "channel_id": "party", "display_name": "Party", "type": "membership", "max_message_length": 500, "color": "#5599FF" },
      { "channel_id": "guild", "display_name": "Guild", "type": "membership", "max_message_length": 500, "color": "#33CC33" },
      { "channel_id": "whisper", "display_name": "Whisper", "type": "direct", "max_message_length": 500, "color": "#FF66CC" }
    ],
    "custom_channels_enabled": true,
    "max_custom_channel_name_length": 32,
    "max_custom_channels_per_player": 5
  },
  "rate_limiting": {
    "global_messages_per_minute": 8,
    "party_guild_messages_per_minute": 20,
    "whisper_messages_per_minute": 15,
    "duplicate_message_cooldown_seconds": 5,
    "burst_threshold": 4,
    "burst_window_seconds": 3,
    "burst_cooldown_seconds": 10,
    "soft_mute_trigger_count": 3,
    "soft_mute_trigger_window_minutes": 10,
    "soft_mute_duration_minutes": 5
  },
  "moderation": {
    "profanity_filter_enabled": true,
    "profanity_word_list": "meta/chat/profanity_wordlist.txt",
    "url_block_list": "meta/chat/url_blocklist.txt",
    "url_allowed_domains": ["example-game.com"],
    "mute_escalation_minutes": [10, 60, 1440, 10080],
    "mute_escalation_window_days": 30,
    "auto_mute_report_threshold": 5,
    "auto_mute_report_window_hours": 24,
    "profanity_auto_mute_threshold": 5,
    "profanity_auto_mute_window_minutes": 10,
    "message_retention_days": 30
  }
}
```

#### Database Schema

```sql
-- schema: chat

-- Persistent message log for moderation audit. NOT used for real-time delivery.
-- Retained for `message_retention_days`, then purged by scheduled job.
CREATE TABLE chat.messages (
    message_id      UUID PRIMARY KEY,
    channel_id      TEXT NOT NULL,
    sender_id       UUID NOT NULL,         -- character_id
    sender_name     TEXT NOT NULL,          -- Denormalized for fast GM search
    content         TEXT NOT NULL,          -- Original text (pre-profanity-filter)
    filtered        BOOLEAN NOT NULL DEFAULT false, -- True if profanity filter modified the message
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_messages_sender ON chat.messages (sender_id, sent_at DESC);
CREATE INDEX idx_chat_messages_channel ON chat.messages (channel_id, sent_at DESC);

-- Active mutes. Expired rows are cleaned up lazily (checked at send time) and by scheduled job.
CREATE TABLE chat.mutes (
    character_id    UUID PRIMARY KEY,
    muted_until     TIMESTAMPTZ NOT NULL,  -- Use 'infinity' for permanent mutes
    reason          TEXT NOT NULL,
    issued_by       UUID,                  -- character_id of GM, NULL for auto-mutes
    offense_count   INT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Mute history for escalation tracking. Never deleted (audit trail).
CREATE TABLE chat.mute_history (
    mute_id         UUID PRIMARY KEY,
    character_id    UUID NOT NULL,
    muted_until     TIMESTAMPTZ NOT NULL,
    reason          TEXT NOT NULL,
    issued_by       UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_mute_history_char ON chat.mute_history (character_id, created_at DESC);

-- Player block list. Bidirectional: blocking A→B also hides A's messages from B's perspective.
CREATE TABLE chat.blocked_players (
    character_id         UUID NOT NULL,
    blocked_character_id UUID NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (character_id, blocked_character_id)
);

-- Player reports for GM review queue.
CREATE TABLE chat.reports (
    report_id       UUID PRIMARY KEY,
    reporter_id     UUID NOT NULL,         -- character_id of reporter
    reported_id     UUID NOT NULL,         -- character_id of reported player
    reason          TEXT NOT NULL,          -- ReportReason enum value
    details         TEXT,                   -- Free-text explanation from reporter
    message_id      UUID,                  -- Optional: the specific message being reported
    status          TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'reviewed', 'actioned', 'dismissed'
    reviewed_by     UUID,                  -- GM character_id
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at     TIMESTAMPTZ
);
CREATE INDEX idx_chat_reports_reported ON chat.reports (reported_id, created_at DESC);
CREATE INDEX idx_chat_reports_status ON chat.reports (status) WHERE status = 'pending';

-- Custom channel subscriptions. Membership channels (party/guild) are resolved at send time
-- from social.party_members / social.guild_members and do not appear here.
CREATE TABLE chat.channel_subscriptions (
    character_id    UUID NOT NULL,
    channel_id      TEXT NOT NULL,          -- Only custom:* channels
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (character_id, channel_id)
);
```

---

### 6.2 Party & Guild Service

**Responsibility:** Manages party formation, party loot rules, guild creation/membership/ranks/permissions, guild bank, friends lists, player blocking, and LFG matchmaking. Publishes party membership to the Loot Service (for loot distribution) and the Progression Service (for XP sharing).

#### Locked-In Contracts

From [Edge Node Envelopes §2.1](../2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md):
```rust
// Party
MetaRequest::InviteToParty { target_character_name: String }
MetaRequest::RespondToPartyInvite { from_character_id: UUID, accepted: bool }
MetaRequest::LeaveParty
MetaRequest::KickFromParty { target_character_id: UUID }
MetaRequest::PromotePartyLeader { target_character_id: UUID }
MetaRequest::SetPartyLootMode { mode: PartyLootMode }
MetaRequest::SetPartyRole { target_character_id: UUID, role: PartyRole }

// Guild
MetaRequest::CreateGuild { guild_name: String }
MetaRequest::InviteToGuild { target_character_name: String }
MetaRequest::RespondToGuildInvite { guild_id: UUID, accepted: bool }
MetaRequest::LeaveGuild
MetaRequest::KickFromGuild { target_character_id: UUID }
MetaRequest::SetGuildRank { target_character_id: UUID, rank: String }
MetaRequest::SetGuildRankPermissions { rank: String, permissions: Vec<GuildPermission> }
MetaRequest::GuildBankDeposit { bag_slot: u8 }
MetaRequest::GuildBankWithdraw { bank_tab: u8, bank_slot: u8 }
MetaRequest::SetGuildMotd { text: String }
MetaRequest::DisbandGuild

// Friends
MetaRequest::SendFriendRequest { target_character_name: String }
MetaRequest::RespondToFriendRequest { from_character_id: UUID, accepted: bool }
MetaRequest::RemoveFriend { target_character_id: UUID }

// LFG
MetaRequest::LfgEnqueue { activity: LfgActivity, role: PartyRole }
MetaRequest::LfgDequeue

// Responses
MetaResponse::PartyInviteReceived { from_name: String, from_character_id: UUID }
MetaResponse::PartySync(PartySnapshot)
MetaResponse::PartyDisbanded
MetaResponse::GuildInviteReceived { guild_name: String, from_name: String, guild_id: UUID }
MetaResponse::GuildSync(GuildSnapshot)
MetaResponse::GuildMotdUpdated { text: String }
MetaResponse::GuildDisbanded
MetaResponse::FriendRequestReceived { from_name: String, from_character_id: UUID }
MetaResponse::FriendsSync(FriendsSnapshot)
MetaResponse::LfgMatchFound { activity: LfgActivity, party_id: UUID }
MetaResponse::LfgQueueUpdate { position: u32, estimated_wait_seconds: u32 }
```

From §9.10 (Deferred Loot Recovery): *"Distribution rules must reuse the same party loot policy as live drops (Need/Greed/DKP/leader assignment)."*

From §9.9 (`InboxReason`): Guild bank withdrawals that fail to deliver (full bag, player offline mid-transaction) are routed through the Recovery Inbox.

The Party & Guild Service is a data dependency for:
- **Loot Service** — reads party membership and loot mode for drop distribution
- **Progression Service** — reads party membership for XP sharing
- **Chat Service** — resolves membership channels at message send time

All cross-service reads use direct Postgres queries against the `social.*` schema (per Principle 4: shared database, schema isolation). No internal RPC is required for party/guild membership lookups.

#### 6.2.1 Party System

**Party lifecycle:**
1. **Creation** — When a player sends `InviteToParty`, the service checks if the inviter is already in a party. If not, a new party is created with the inviter as leader. If the inviter is already in a party and is the leader, the invite proceeds. Non-leaders cannot invite (unless the guild has a future "Party Invite" permission — deferred).
2. **Invite delivery** — The target is resolved by character name via the Session Manager. If online, `PartyInviteReceived` is pushed to their Edge Node. If offline, the invite is dropped.
3. **Accept/Decline** — `RespondToPartyInvite` either adds the player to the party (inserting into `social.party_members` and broadcasting `PartySync` to all members) or silently discards the invite.
4. **Leave** — `LeaveParty` removes the player. If the leader leaves, leadership auto-transfers to the longest-tenured remaining member. If the last member leaves, the party row is deleted.
5. **Kick** — Leader-only. Removes the target and broadcasts `PartySync`. The kicked player receives `PartyDisbanded`.
6. **Disband** — Implicit when the last member leaves or the leader kicks everyone. No explicit disband command.

**Invite timeout:** Pending invites expire after a configurable timeout (default: 60 seconds). Expired invites are not stored — the in-memory Redis key (`party:invite:{target_character_id}`) simply TTLs out.

**Party roles:** Roles (`Tank`, `Healer`, `Damage`, `Flex`) are cosmetic tags displayed on party frames. They have no gameplay effect and exist to coordinate expectations. The leader can assign roles via `SetPartyRole`, and roles are included in `PartySnapshot`.

**Party frames data:** The `PartyMember` struct includes `current_hp_pct` and `current_resource_pct` for party frame rendering. These values are pushed from the Arbiter to Meta via a lightweight periodic update (every ~500ms, not on the 60Hz loop). The Chat Service piggybacks this data on the existing `PartySync` broadcast. When a party member crosses Arbiter boundaries, the new Arbiter continues the updates seamlessly because the Session Manager tracks the current hosting Arbiter.

**Party loot mode:** The leader can change loot mode at any time via `SetPartyLootMode`. The new mode takes effect immediately for subsequent drops. In-flight loot (e.g., an active NeedGreed vote) completes under the mode it started with.

#### 6.2.2 Guild System

**Guild lifecycle:**
1. **Creation** — `CreateGuild` validates the guild name (unique, 3–24 characters, alphanumeric + spaces, no profanity), deducts the creation cost from the player's gold wallet (via Currency & Trading Service), and creates the guild with the player as Guild Master (rank ordinal 0).
2. **Default ranks** — On creation, 4 default ranks are inserted: Guild Master (ordinal 0), Officer (1), Member (2), Initiate (3). The Guild Master rank cannot be renamed, deleted, or have its permissions modified. All other ranks are fully customizable.
3. **Invite** — Players with the `Invite` permission on their rank can invite others. The target must not already be in a guild (single-guild-per-character constraint).
4. **Leave** — Any member except the Guild Master can leave. The Guild Master must transfer leadership first or disband.
5. **Kick** — Players with the `Kick` permission can kick members of strictly lower rank (higher ordinal number).
6. **Disband** — Guild Master only. Removes all members, deletes guild bank contents (items are mailed to the Guild Master via Recovery Inbox), and marks the guild as disbanded. The guild name is released for reuse after 30 days.

**Guild permission matrix:**

Each rank has a set of `GuildPermission` flags. The Guild Master rank implicitly has all permissions and cannot be modified. For all other ranks, permissions are stored in `social.guild_ranks.permissions` as a JSONB array.

| Permission | Description | Default: Officer | Default: Member | Default: Initiate |
|:---|:---|:---:|:---:|:---:|
| `Invite` | Invite new members | Yes | No | No |
| `Kick` | Kick members of lower rank | Yes | No | No |
| `Promote` | Promote up to one rank below own | Yes | No | No |
| `Demote` | Demote members of lower rank | Yes | No | No |
| `BankDeposit` | Deposit items to guild bank | Yes | Yes | Yes |
| `BankWithdraw` | Withdraw items from guild bank | Yes | No | No |
| `BankManageTabs` | Purchase/rename guild bank tabs | Yes | No | No |
| `EditMotd` | Change the message of the day | Yes | No | No |
| `EditRanks` | Rename ranks & modify permissions below own rank | No | No | No |
| `StartGuildEvent` | Create guild calendar events | Yes | Yes | No |
| `UseGuildRepair` | Use guild funds for personal repair costs | Yes | Yes | No |

**Rank promotion/demotion rules:**
- A player can only promote another player to one rank below their own rank (Officers can promote to Member, not to Officer).
- A player can only demote members who are strictly lower rank than themselves.
- The Guild Master can promote anyone to any rank, including Officer.
- Leadership transfer is a separate action: the Guild Master uses `SetGuildRank` with rank `"Guild Master"`, which atomically demotes the old GM to Officer and promotes the target to GM.

**Inactive Guild Master succession:**

If the Guild Master has not logged in for a configurable period (default: 30 days), the system triggers an automatic succession:
1. The highest-ranked online officer (by rank ordinal, then by `joined_at` seniority) is promoted to Guild Master.
2. If no officers exist, the longest-tenured member is promoted.
3. The old Guild Master is demoted to Member (not kicked) so they retain membership if they return.
4. A `SystemAlert` is broadcast to all online guild members: `"Guild leadership has been transferred to {new_leader_name} due to inactivity."`

This is checked by a scheduled job running daily. The threshold is configurable in the designer config.

#### 6.2.3 Guild Bank

The guild bank is a shared item storage facility accessible by guild members with the appropriate permissions.

**Structure:**
- The bank is organized into tabs (default: 1 tab on guild creation).
- Each tab has a configurable number of slots (default: 50).
- Additional tabs can be purchased by members with `BankManageTabs` permission, at escalating gold costs.

**Deposit flow:**
1. Player sends `GuildBankDeposit { bag_slot }`.
2. Service verifies the player has `BankDeposit` permission.
3. The item is atomically moved from `inventory.bags` to `social.guild_bank_items` within a single transaction. The Inventory Service is called via internal RPC to remove the item from the player's bag.
4. A `guild_bank_log` entry is created for audit.
5. `GuildSync` is broadcast to online members with updated bank state.

**Withdraw flow:**
1. Player sends `GuildBankWithdraw { bank_tab, bank_slot }`.
2. Service verifies the player has `BankWithdraw` permission.
3. The item is atomically moved from `social.guild_bank_items` to the player's bag via Inventory Service RPC. If the player's bag is full, the withdraw fails with a `SystemAlert`.
4. A `guild_bank_log` entry is created.
5. `GuildSync` is broadcast.

**Withdraw rate limiting:** To prevent bank raids, each rank has a configurable daily withdraw limit (default: Officers = 20, Members = 0, Initiate = 0). The Guild Master has no limit. Withdraw counts reset at the daily server reset time.

#### 6.2.4 Friends System

**Friend lifecycle:**
1. `SendFriendRequest` — Resolved by character name. If the target is online, `FriendRequestReceived` is pushed. If offline, the request is persisted in `social.friend_requests` and delivered on next login.
2. `RespondToFriendRequest` — Accept inserts bidirectional rows into `social.friends` (A→B and B→A) and broadcasts `FriendsSync` to both players. Decline deletes the request row.
3. `RemoveFriend` — Deletes both bidirectional rows and broadcasts `FriendsSync`.

**Online status:** When a player logs in, the Session Manager publishes a presence event. The Friends Service reads the player's friends list and pushes `FriendsSync` (with updated `is_online` and `current_zone`) to all online friends. The same happens on logout. Zone changes are updated on Arbiter transfer (topology update).

**Block interaction with friends:** Blocking a player who is currently on the friends list automatically removes the friendship (both directions) before applying the block.

**Friends list capacity:** Default 100 friends. Configurable in designer config.

#### 6.2.5 LFG / Matchmaking

The LFG (Looking For Group) system provides automated party formation for structured content.

**Queue model:**
- Players enqueue with `LfgEnqueue { activity, role }`. A player can only be in one LFG queue at a time.
- The queue is stored entirely in Redis (`lfg:queue:{activity_type}:{activity_id}`) as a sorted set keyed by enqueue timestamp.
- Players already in a full party cannot enqueue.
- Players in a partial party enqueue as a unit — the service reserves N slots (current party size) when matching.

**Matching algorithm:**

A background worker runs every 5 seconds per activity type:

```
fn try_match(activity, queue):
    required_roles = activity.required_composition  // e.g., {Tank: 1, Healer: 1, Damage: 3}
    candidates = queue.entries_sorted_by_enqueue_time()

    // Greedy role-fill: iterate candidates in FIFO order
    slots = copy(required_roles)
    matched = []

    for candidate in candidates:
        if candidate.role == Flex:
            // Flex fills the first unfilled role, prioritizing Tank > Healer > Damage
            for role in [Tank, Healer, Damage]:
                if slots[role] > 0:
                    slots[role] -= 1
                    matched.push((candidate, role))
                    break
        else if slots[candidate.role] > 0:
            slots[candidate.role] -= 1
            matched.push((candidate, candidate.role))

        if all slots filled:
            // Match found! Form the party.
            form_party(matched, activity)
            remove_all(matched, from: queue)
            return

    // No complete match this cycle. Update queue positions for waiting players.
    for (i, candidate) in queue.entries().enumerate():
        push_to_edge(candidate.session, LfgQueueUpdate { position: i+1, estimated_wait: ... })
```

**Party formation on match:**
1. A new party is created with loot mode defaulting to `NeedGreed` for dungeons, `FreeForAll` for open world.
2. All matched players receive `LfgMatchFound` with the `party_id`.
3. `PartySync` is broadcast to all matched players.
4. The party leader is assigned to the player who queued first (longest wait).

**Activity definitions:**

| Activity Type | Required Composition | Match Size |
|:---|:---|:---|
| Dungeon | 1 Tank, 1 Healer, 3 Damage | 5 |
| World Boss | No role requirement | 5 (forms multiple parties) |
| PvP Arena | No role requirement | Matched by team size (2v2, 3v3) |
| PvP Battleground | No role requirement | 10v10 (configurable per BG) |
| Open World | No role requirement | 2–5 (first 2 matched, others join) |

**Estimated wait time:** Calculated as a rolling average of the last 20 successful match times for that activity/role combination. Stored in Redis. Returned in `LfgQueueUpdate`.

#### Designer Configuration

```json
{
  "$schema": "meta/social/v1",
  "party": {
    "max_party_size": 5,
    "loot_modes": ["FreeForAll", "RoundRobin", "NeedGreed", "MasterLoot"],
    "default_loot_mode": "FreeForAll",
    "invite_timeout_seconds": 60,
    "roles": ["Tank", "Healer", "Damage", "Flex"]
  },
  "guild": {
    "max_guild_size": 200,
    "creation_cost_gold": 10000,
    "min_name_length": 3,
    "max_name_length": 24,
    "max_ranks": 10,
    "default_ranks": [
      { "name": "Guild Master", "ordinal": 0, "permissions": ["*"] },
      { "name": "Officer", "ordinal": 1, "permissions": ["Invite", "Kick", "Promote", "Demote", "BankDeposit", "BankWithdraw", "BankManageTabs", "EditMotd", "StartGuildEvent", "UseGuildRepair"] },
      { "name": "Member", "ordinal": 2, "permissions": ["BankDeposit", "StartGuildEvent", "UseGuildRepair"] },
      { "name": "Initiate", "ordinal": 3, "permissions": ["BankDeposit"] }
    ],
    "inactive_leader_succession_days": 30,
    "disband_name_release_days": 30,
    "guild_bank": {
      "initial_tabs": 1,
      "max_tabs": 8,
      "slots_per_tab": 50,
      "tab_costs_gold": [0, 5000, 10000, 25000, 50000, 100000, 250000, 500000],
      "daily_withdraw_limits": {
        "Guild Master": -1,
        "Officer": 20,
        "Member": 0,
        "Initiate": 0
      }
    },
    "guild_repair": {
      "enabled": true,
      "daily_gold_limit_per_member": 500,
      "funded_from": "guild_bank_gold"
    }
  },
  "friends": {
    "max_friends_list_size": 100,
    "max_blocked_list_size": 50,
    "friend_request_timeout_hours": 72
  },
  "lfg": {
    "match_interval_seconds": 5,
    "activities": {
      "dungeon": { "composition": { "Tank": 1, "Healer": 1, "Damage": 3 }, "default_loot_mode": "NeedGreed" },
      "world_boss": { "composition": {}, "group_size": 5, "default_loot_mode": "FreeForAll" },
      "pvp_arena_2v2": { "composition": {}, "group_size": 2 },
      "pvp_arena_3v3": { "composition": {}, "group_size": 3 },
      "pvp_battleground": { "composition": {}, "group_size": 10 },
      "open_world": { "composition": {}, "group_size": 5, "min_group_size": 2 }
    }
  }
}
```

#### Database Schema

```sql
-- schema: social

-- ========================
-- PARTY
-- ========================

CREATE TABLE social.parties (
    party_id        UUID PRIMARY KEY,
    leader_id       UUID NOT NULL,
    loot_mode       TEXT NOT NULL DEFAULT 'FreeForAll',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE social.party_members (
    party_id        UUID NOT NULL REFERENCES social.parties ON DELETE CASCADE,
    character_id    UUID NOT NULL UNIQUE,   -- A character can only be in one party
    role            TEXT NOT NULL DEFAULT 'Flex',
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (party_id, character_id)
);

-- ========================
-- GUILD
-- ========================

CREATE TABLE social.guilds (
    guild_id        UUID PRIMARY KEY,
    guild_name      TEXT UNIQUE NOT NULL,
    leader_id       UUID NOT NULL,
    motd            TEXT NOT NULL DEFAULT '',
    bank_gold       BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    disbanded_at    TIMESTAMPTZ           -- Non-null = disbanded; name released after configured period
);

CREATE TABLE social.guild_ranks (
    guild_id        UUID NOT NULL REFERENCES social.guilds ON DELETE CASCADE,
    rank_name       TEXT NOT NULL,
    ordinal         SMALLINT NOT NULL,     -- 0 = Guild Master (immutable)
    permissions     JSONB NOT NULL DEFAULT '[]',
    PRIMARY KEY (guild_id, rank_name)
);
CREATE UNIQUE INDEX idx_guild_ranks_ordinal ON social.guild_ranks (guild_id, ordinal);

CREATE TABLE social.guild_members (
    guild_id        UUID NOT NULL REFERENCES social.guilds ON DELETE CASCADE,
    character_id    UUID NOT NULL UNIQUE,   -- Single-guild constraint
    rank_name       TEXT NOT NULL DEFAULT 'Initiate',
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login      TIMESTAMPTZ NOT NULL DEFAULT now(), -- Updated on session create; used for succession check
    PRIMARY KEY (guild_id, character_id),
    FOREIGN KEY (guild_id, rank_name) REFERENCES social.guild_ranks (guild_id, rank_name)
);

-- ========================
-- GUILD BANK
-- ========================

CREATE TABLE social.guild_bank_tabs (
    guild_id        UUID NOT NULL REFERENCES social.guilds ON DELETE CASCADE,
    tab_index       SMALLINT NOT NULL,
    tab_name        TEXT NOT NULL DEFAULT 'Tab',
    PRIMARY KEY (guild_id, tab_index)
);

CREATE TABLE social.guild_bank_items (
    guild_id        UUID NOT NULL,
    tab_index       SMALLINT NOT NULL,
    slot_index      SMALLINT NOT NULL,
    base_item_id    SMALLINT NOT NULL,     -- items.json reference
    quantity        INT NOT NULL DEFAULT 1,
    instance_id     BIGINT,                -- Non-null for equipment with affixes
    PRIMARY KEY (guild_id, tab_index, slot_index),
    FOREIGN KEY (guild_id, tab_index) REFERENCES social.guild_bank_tabs (guild_id, tab_index)
);

-- Audit trail for all guild bank deposits and withdrawals.
CREATE TABLE social.guild_bank_log (
    log_id          UUID PRIMARY KEY,
    guild_id        UUID NOT NULL,
    character_id    UUID NOT NULL,
    action          TEXT NOT NULL,          -- 'deposit', 'withdraw'
    base_item_id    SMALLINT NOT NULL,
    quantity        INT NOT NULL,
    instance_id     BIGINT,
    tab_index       SMALLINT NOT NULL,
    slot_index      SMALLINT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_guild_bank_log ON social.guild_bank_log (guild_id, created_at DESC);

-- Daily withdraw tracking. Reset by scheduled job at server reset time.
CREATE TABLE social.guild_bank_withdraw_counts (
    guild_id        UUID NOT NULL,
    character_id    UUID NOT NULL,
    withdraw_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    count           INT NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, character_id, withdraw_date)
);

-- ========================
-- FRIENDS
-- ========================

CREATE TABLE social.friends (
    character_id    UUID NOT NULL,
    friend_id       UUID NOT NULL,
    added_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (character_id, friend_id)
);
-- Bidirectional: adding A→B also inserts B→A in the same transaction.

CREATE TABLE social.friend_requests (
    from_id         UUID NOT NULL,
    to_id           UUID NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,  -- from_created_at + friend_request_timeout_hours
    PRIMARY KEY (from_id, to_id)
);

-- ========================
-- GUILD INVITES (pending, not yet accepted)
-- ========================

CREATE TABLE social.guild_invites (
    guild_id        UUID NOT NULL REFERENCES social.guilds,
    invited_id      UUID NOT NULL,         -- Target character_id
    invited_by      UUID NOT NULL,         -- character_id of inviter
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (guild_id, invited_id)
);
```

---

## 7. Cross-Cutting Concerns

### 7.1 Service Communication

Meta services communicate internally via:
- **Direct Postgres queries** — for synchronous reads of cross-service data (e.g., Loot Service reads Party membership)
- **Event Bus (Redpanda)** — for asynchronous event propagation from the Spatial Mesh
- **Internal RPC** — for synchronous cross-service calls where needed (e.g., Spawn Service calls Inventory Service to compile stats)

The Edge Node connects to Meta via `meta_rpc_client: RpcClient` (gRPC or equivalent), as defined on `ProxyActor`.

### 7.2 Observability

Each service SHOULD emit structured metrics for:
- Event Bus consumer lag (per consumer group)
- Database query latency (per table/operation)
- Cross-service RPC latency
- Business metrics (logins/hour, items spawned, trades completed, etc.)

### 7.3 Configuration Versioning

Config schemas use semantic versioning (e.g., `meta/inventory/v1`). A config deployment:
1. New config version is uploaded and validated against the JSON schema
2. Services reload config on signal (no restart required)
3. Old config is retained for rollback

This mirrors the `PrepareDataEpoch` / `ActivateDataEpoch` pattern used for `SpellData` in the Spatial Mesh.

---

## 8. References

- [Core Concepts and Mesh](01-core-concepts-and-mesh.md) — §9 covers all Meta-adjacent protocols
- [Core Primitives](../2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md) — `HardEvent`, `MetaCommand`, `SoftState`, `OffensiveStats`, `DefensiveStats`, `SessionMapping`
- [Edge Node Envelopes](../2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md) — `MetaRequest`, `MetaResponse`, `InventorySnapshot`, `ProxyActor`
- [Hard-State Events](../2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md) — `HardEvent` enum, `ArbiterCrashedEvent`, `HardStatePublisher`
- [Intent Taxonomy](../2-contracts-and-interfaces/02-intent-taxonomy.md) — Meta-lane intent IDs `0300`–`0399`
- [Configuration Registry](../4-infrastructure/02-configuration-registry.md) — Runtime config patterns
