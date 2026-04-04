# Game Image Format

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define the binary artifact that the Game Compiler emits and the engine runtime loads. The game image is the single distributable unit containing all compiled game content — ability IR blocks, entity definitions, status effects, formulas, and lookup tables.

---

## 1. Artifact Identity

Each emitted image MUST include:

- a fixed-size `FileHeader` containing the image format version, total size, and authenticated digest
- a `Manifest` section containing compatibility and identity metadata
- a `SectionDirectory` describing every section except the header, the directory itself, and the optional terminal `Signature`

The `Manifest` section MUST include:

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | `string` | Unique identifier for the game project |
| `game_version` | `semver` | Semantic version of the game content |
| `compiler_version` | `semver` | Version of the compiler that produced this image |
| `adapter_identity` | `string` | Game adapter identity string |
| `adapter_api_major` | `u16` | Adapter API major version for compatibility checking |
| `wire_schema_versions` | `list<u16>` | Supported wire protocol schema versions |

The authenticated image digest is stored in `FileHeader.digest`, not duplicated in the `Manifest`.

`build_timestamp` is intentionally excluded from the image. Build time MAY be recorded in compiler-side build reports or deployment metadata, but it MUST NOT appear inside the `GameImage` if byte-identical deterministic builds are required.

### 1.1 Authenticated Digest Scope

The authenticated digest stored in `FileHeader.digest` MUST be the SHA-256 hash of the entire `GameImage` envelope except:

- the 32-byte `FileHeader.digest` field itself, which MUST be treated as all zero bytes during hashing
- the optional `Signature` section (0xFF), which MUST be the final section in the file when present

This means the authenticated digest covers:

- the rest of the `FileHeader`
- the `SectionDirectory`
- the `Manifest`
- all gameplay content sections
- the optional `DebugMetadata` section, if present

Given identical source files, compiler version, build profile, and signing inputs, the emitted image bytes preceding the `Signature` section MUST be byte-identical across builds (deterministic build guarantee from `03-compiler-pipeline.md` §7).

## 2. Image Layout

A game image is a sequential binary file with the following section layout:

```
┌──────────────────────────────────────────┐
│  Section 0: File Header (fixed size)     │
├──────────────────────────────────────────┤
│  Section 1: Section Directory            │
├──────────────────────────────────────────┤
│  Section 2: Manifest                     │
├──────────────────────────────────────────┤
│  Section 3: Ability IR Table             │
├──────────────────────────────────────────┤
│  Section 4: Entity Definitions           │
├──────────────────────────────────────────┤
│  Section 5: Status Effect Definitions    │
├──────────────────────────────────────────┤
│  Section 6: Formula Registry             │
├──────────────────────────────────────────┤
│  Section 7: Static Data Tables           │
├──────────────────────────────────────────┤
│  Section 8: Lookup Indexes               │
├──────────────────────────────────────────┤
│  Section 9: Debug Metadata (optional)    │
├──────────────────────────────────────────┤
│  Section 10: Signature (optional, final) │
└──────────────────────────────────────────┘
```

### 2.1 File Header

Fixed-size header at byte offset 0. Allows fast validation without parsing the full image.

```
FileHeader {
    magic:          [u8; 4],    // "GMIM" (Game IMage)
    format_version: u16,        // Image format version
    flags:          u16,        // Bit flags (see below)
    section_count:  u16,        // Number of SectionEntry records in SectionDirectory
    _reserved:      [u8; 6],    // Zero-padded for alignment
    total_size:     u64,        // Total file size in bytes
    digest:         [u8; 32],   // SHA-256 of authenticated image envelope (§1.1)
}
// Fixed size: 56 bytes
```

`FileHeader.flags` bit assignments:

| Bit | Name | Description |
|-----|------|-------------|
| 0 | `signed` | Signature section (0xFF) is present and MUST be verified |
| 1 | `debug_present` | Debug Metadata section (0xF0) is present |
| 2-15 | Reserved | MUST be zero. Readers MUST ignore unknown flags for forward compatibility. |

Compression is intentionally not supported in this format version. Game images are small enough (sub-256 MB bound) that the complexity of compression scope, algorithm negotiation, and offset semantics is not justified. If a future `format_version` adds compression, it will define the algorithm, scope (per-section vs whole-file), and whether section directory offsets/checksums reference compressed or decompressed bytes.

### 2.2 Section Directory

The `SectionDirectory` immediately follows the fixed-size header. It contains one `SectionEntry` for every section present in the image except the file header itself, the directory itself, and the optional terminal `Signature` section. The directory does not self-describe — its location (immediately after the header) and size (`FileHeader.section_count` entries) are determined from the header alone.

```
SectionEntry {
    section_type:   u16,        // Enum identifying the section kind
    _reserved:      u16,
    offset:         u64,        // Byte offset from file start
    size:           u64,        // Section size in bytes
    entry_count:    u32,        // Number of entries (for table sections)
    checksum:       u32,        // CRC-32 of section bytes
}
// Fixed size: 28 bytes per entry
```

The per-entry CRC-32 checksums cover the exact bytes of the referenced section and serve as fast corruption detection during loading. Because the `SectionDirectory` itself is inside the authenticated digest envelope, its offsets and checksums are tamper-evident even though CRC-32 is not cryptographic.

Section type IDs:

| Type ID | Name | In Directory? | In Digest? |
|---------|------|:------------:|:----------:|
| 0x01 | Manifest | Yes | Yes |
| 0x10 | AbilityIRTable | Yes | Yes |
| 0x11 | EntityDefinitions | Yes | Yes |
| 0x12 | StatusEffectDefinitions | Yes | Yes |
| 0x13 | FormulaRegistry | Yes | Yes |
| 0x14 | StaticDataTables | Yes | Yes |
| 0x20 | LookupIndexes | Yes | Yes |
| 0xF0 | DebugMetadata | Yes, if present | Yes, if present |
| 0xFF | Signature | No | No |

The `Signature` section, if present, MUST be the final bytes of the file and is located by the `signed` flag in `FileHeader.flags` plus the fixed `SignatureSection` size for this `format_version`.

### 2.3 Section: Manifest (0x01)

The manifest carries compatibility and identity metadata used during admission and activation checks. Unlike the previous draft, the manifest is part of the authenticated image envelope and therefore tamper-evident.

```
ManifestSection {
    adapter_api_major:            u16,
    wire_schema_version_count:    u16,
    game_id_len:                  u16,
    game_version_len:             u16,
    compiler_version_len:         u16,
    adapter_identity_len:         u16,

    // Variable-length payload, in this exact order:
    // 1. game_id[game_id_len]                     — UTF-8 bytes, no terminator
    // 2. game_version[game_version_len]           — UTF-8 semver, no terminator
    // 3. compiler_version[compiler_version_len]   — UTF-8 semver, no terminator
    // 4. adapter_identity[adapter_identity_len]   — UTF-8 bytes, no terminator
    // 5. wire_schema_versions[wire_schema_version_count] — u16 values
}
```

Manifest strings MUST be UTF-8 and SHOULD be ASCII-only for operational simplicity. The runtime MUST parse the manifest through the `SectionDirectory` entry for type 0x01 rather than by assuming any fixed byte offset after the header.

---

## 3. Section: Ability IR Table (0x10)

The primary gameplay data section. Contains all compiled `AbilityIRBlock` entries as defined in `03-1-compiler-ir-specification.md` §1.

### 3.1 Table Structure

```
AbilityIRTable {
    count:      u32,                    // Number of ability entries
    entries:    [AbilityIREntry; count], // Sequential ability blocks
}
```

### 3.2 Entry Structure

Each entry is a serialized `AbilityIRBlock`:

```
AbilityIREntry {
    // Metadata (fixed-size header)
    ability_id:             u32,        // Numeric ability ID (from compiler symbol table)
    cooldown_ticks:         u32,
    resource_pool_id:       u32,        // Pre-hashed pool name (mana, energy, rage, etc.)
    resource_cost:          i64,        // I32F32 encoded amount to debit
    cast_time_ticks:        u32,
    targeting_type:         u8,         // TargetingType enum
    self_cc_immunity_during_cast: u8,   // CcImmunityTier enum (0 = none)
    flags:                  u8,         // Bitfield: bit 0 = can_counter_vulnerability_window, bit 1 = can_be_counterspelled, bit 2 = requires_concentration, bits 3-7 reserved (zero)
    combo_finisher:         u8,         // ComboFinisherType enum (0 = none)
    _padding:               [u8; 3],    // Alignment padding
    input_mode:             InputMode_Wire, // Inline fixed-size subrecord

    // Variable-length sections (offsets relative to entry start)
    // Note: stagger_damage is NOT a block-level field. It is a parameter on
    // individual damage instructions within the ability's instruction list,
    // consistent with 03-1-compiler-ir-specification.md and 02-schema-and-validation.md §5.1.
    activation_mode_count:  u16,
    instruction_count:      u16,
    directive_count:        u16,
    binding_count:          u16,
    param_data_size:        u16,        // Total bytes for all param blocks

    // Inline arrays follow in order:
    // 1. ActivationMode_Wire[activation_mode_count]
    // 2. IRInstruction[instruction_count]
    // 3. IRDirective[directive_count]
    // 4. BindingSlot[binding_count]
    // 5. ParamData[param_data_size] (variable-length parameter payloads)
}
```

`ActivationModes` redirect the public/root ability entry to hidden compiler-generated variant
entries. Hidden variants are serialized as ordinary `AbilityIREntry` records and count toward the
same table/index limits as public abilities.

```
InputMode_Wire {
    mode_type:       u8,         // 0 = instant, 1 = hold_release
    flags:           u8,         // bit 0 = blocks_other_abilities, bit 1 = retains_max_charge_until_release
    _reserved:       [u8; 2],
    min_charge_ticks: u32,
    max_charge_ticks: u32,
    move_speed_multiplier_while_holding: i64, // I32F32; 1.0 for instant abilities
}
// Fixed size: 20 bytes
```

### 3.3 Serialized ActivationMode

```
ActivationMode_Wire {
    predicate_kind:   u8,        // 0=state_present, 1=state_absent, 2=sequence_step, 3=charge_count
    predicate_op:     u8,        // 0=none, 1=eq, 2=gte, 3=lte
    compare_value:    u16,       // sequence step or charge-count threshold; 0 when unused
    runtime_state_id: u32,       // Pre-hashed RuntimeStateDefinition.state_id
    variant_ability_id: u32,     // Hidden AbilityIREntry selected when predicate matches
}
// Fixed size: 12 bytes
```

### 3.4 Serialized IRInstruction

```
IRInstruction_Wire {
    op_kind:        u8,         // 0 = primitive, 1 = runtime_state
    op_id:          u8,         // PrimitiveId or RuntimeStateOp enum
    stage:          u8,         // PipelineStage enum
    _reserved:      u8,
    guard_offset:   u16,        // Offset into ParamData (0xFFFF = no guard)
    param_offset:   u16,        // Offset into ParamData
    param_size:     u16,        // Size of param block in bytes
    output_binding: u16,        // Binding slot index (0xFFFF = no output)
}
// Fixed size: 12 bytes
```

`runtime_state` op IDs are:

- `0 = WriteState`
- `1 = ClearState`
- `2 = AdvanceSequence`
- `3 = ModifyChargePool`

Runtime-state references and state-backed payload selectors inside `ParamData` serialize as
pre-hashed `u32` `state_id` values plus compact selector enums, matching the `RuntimeStateTable`
defined in §7.4.

### 3.5 Serialized IRDirective

```
IRDirective_Wire {
    primitive_id:   u8,         // Only cross-cutting primitive IDs allowed
    _reserved:      u8,
    guard_offset:   u16,        // Offset into ParamData (0xFFFF = no guard)
    param_offset:   u16,        // Offset into ParamData
    param_size:     u16,        // Size of param block in bytes
}
// Fixed size: 8 bytes
```

### 3.6 Bounds

| Constraint | Limit | Source |
|-----------|-------|--------|
| Instructions per ability | `<= MAX_INSTRUCTIONS_PER_ABILITY` (default: 32) | `03-1-compiler-ir-specification.md` §7 |
| Directives per ability | `<= 16` | Cross-cutting primitive count |
| Bindings per ability | `<= MAX_BINDINGS_PER_ABILITY` (default: 16) | `03-1-compiler-ir-specification.md` §7 |
| Activation modes per public ability | `<= 8` | Ordered hidden-variant redirect cap |
| Param data per ability | `<= 4096 bytes` | Prevents unbounded ability payloads |
| Total abilities per image | `<= 65536` | u16 index space, including hidden variants |

---

## 4. Section: Entity Definitions (0x11)

Serialized entity archetypes from `02-schema-and-validation.md` §7.

### 4.1 Entry Structure

```
EntityDefinition_Wire {
    entity_type_id:     u32,        // Numeric type ID
    max_hp:             i64,        // I32F32
    movement_speed:     i64,        // I32F32
    stat_count:         u16,        // Number of base stat entries
    resource_pool_count: u16,       // Number of resource pool entries
    ability_count:      u16,        // Number of ability ID references
    passive_count:      u16,        // Number of passive status effect references
    combo_field_type:   u8,         // P-64 combo field tag (0 = none)
    _padding:           u8,         // Alignment
    flags:              u16,        // Bitfield: bit 0 = has_stagger_bar, bit 1 = has_downed_state, bit 2 = has_projectile_config, bits 3-15 reserved (zero)

    // Variable-length inline data:
    // 1. StatEntry_Wire[stat_count]
    // 2. ResourcePoolEntry_Wire[resource_pool_count]
    // 3. AbilityRef_Wire[ability_count]
    // 4. PassiveRef_Wire[passive_count]
    // 5. Optional: StaggerBarDef_Wire          — if has_stagger_bar flag (§4.3)
    // 6. Optional: DownedStateDef_Wire         — if has_downed_state flag (§4.4)
    // 7. Optional: ProjectileConfigDef_Wire         — if has_projectile_config flag (§4.5)
}
```

#### 4.2 Entity Subrecord Wire Types

Tiny fixed-size records referenced by `EntityDefinition_Wire` variable-length arrays:

```
StatEntry_Wire {
    stat_id:    u16,    // Pre-hashed stat name
    _padding:   [u8; 6], // Alignment
    value:      i64,    // I32F32
}
// Fixed size: 16 bytes

ResourcePoolEntry_Wire {
    pool_id:    u32,    // Pre-hashed pool name (mana, energy, rage, etc.)
    _padding:   [u8; 4], // Alignment
    max_value:  i64,    // I32F32: maximum pool capacity
}
// Fixed size: 16 bytes

AbilityRef_Wire {
    ability_id: u32,    // References AbilityIRTable entry
}
// Fixed size: 4 bytes

PassiveRef_Wire {
    status_id:  u32,    // References StatusEffectDefinitions entry
}
// Fixed size: 4 bytes
```

#### 4.3 StaggerBarDef_Wire

Present when the `has_stagger_bar` flag is set. Serializes `02-schema-and-validation.md` §7.1.

```
StaggerBarDef_Wire {
    max_stagger:            i64,    // I32F32
    regen_rate_per_tick:    i64,    // I32F32
    regen_delay_ticks:      u32,    // Ticks before regen starts after last stagger damage
    stagger_duration_ticks: u32,    // Duration of the stagger state when bar depletes
    vulnerability_bonus:    i64,    // I32F32: damage multiplier during stagger
}
// Fixed size: 32 bytes
```

#### 4.4 DownedStateDef_Wire

Present when the `has_downed_state` flag is set. Serializes `02-schema-and-validation.md` §7.2.

```
DownedStateDef_Wire {
    downed_hp_ratio:            i64,    // I32F32: fraction of max HP for downed pool
    downed_movement_speed_ratio: i64,   // I32F32: fraction of base movement speed while downed
    rally_channel_ticks:        u32,    // Ticks to channel self-rally
    finish_channel_ticks:       u32,    // Ticks to channel finish on a downed enemy
    downed_ability_count:       u16,    // Number of ability refs available while downed
    _padding:                   [u8; 2],
    // Inline: AbilityRef_Wire[downed_ability_count]
}
// Fixed header size: 28 bytes + variable ability refs
```

#### 4.5 ProjectileConfigDef_Wire

Present when the `has_projectile_config` flag is set. Serializes the projectile/trap behavior fields from `02-schema-and-validation.md` §6.7.1-6.7.2.

```
ProjectileConfigDef_Wire {
    speed:                      i64,    // I32F32: velocity in units/tick
    turn_rate:                  i64,    // I32F32: max angular change per tick (0 = non-homing)
    pierce:                     u8,     // Targets passed through before stopping
    homing:                     u8,     // 0 = false, 1 = true
    arming_delay_ticks:         u32,    // Ticks before detonation-capable triggers arm
    // DetonationPolicy (inline)
    manual_trigger_enabled:     u8,     // 0 = false, 1 = true
    proximity_trigger_radius:   i64,    // I32F32: 0 = disabled, >0 = armed proximity radius
    entity_impact_behavior:     u8,     // Enum: 0=Ignore, 1=Stop, 2=Detonate, 3=DetonateAfterPierceExhausted
    world_impact_behavior:      u8,     // Enum: 0=Ignore, 1=Bounce, 2=Stop, 3=Detonate
    expiry_behavior:            u8,     // Enum: 0=Despawn, 1=Detonate
    _padding:                   [u8; 2], // Alignment to 4-byte boundary
}
// Fixed size: 36 bytes
```

---

## 5. Section: Status Effect Definitions (0x12)

Serialized buff/debuff/CC definitions from `02-schema-and-validation.md` §9.

### 5.1 Entry Structure

```
StatusEffectDef_Wire {
    status_id:          u32,        // Numeric status ID
    max_stacks:         u8,
    flags:              u8,         // Bitfield: bit 0 = is_passive, bit 1 = is_cleansable, bit 2 = has_periodic_effects, bit 3 = has_on_expire_effects, bit 4 = has_consumption_window, bits 5-7 reserved (zero)
    polarity:           u8,         // StatusPolarity enum: 0=neutral, 1=positive, 2=negative
    status_application_immunity: u8, // StatusApplicationImmunity enum: 0=none, 1=negative, 2=positive, 3=all
    cc_category:        u8,         // CcCategory enum: 0=none, 1=displacement, 2=hard_disable, 3=soft_disable, 4=forced_movement, 5=target_override, 6=mute
    duration_scaling:   u8,         // StatusDurationScaling enum: 0=fixed, 1=status_resistance
    cc_behavior_profile: u8,        // CcBehaviorProfile enum: 0=none, 1=stun, 2=root, 3=silence, 4=sleep, 5=disarm, 6=blind, 7=fear, 8=charm, 9=taunt, 10=berserk, 11=mute
    cc_immunity_mask:   u8,         // Bitmask over CcCategory values; 0 = none
    duration_ticks:     u32,
    modifier_count:     u16,        // Stat modifiers
    capability_flags:   u16,        // P-26 capability bitmask: bit 0=CAN_MOVE, bit 1=CAN_CAST, bit 2=CAN_ATTACK, bit 3=CAN_USE_ITEMS, bit 4=PASSIVES_ACTIVE, bits 5-15 reserved
    snapshot_recorder_state_id: u32, // 0 = none; references RuntimeStateTable entry of kind snapshot_buffer

    // Variable-length inline data:
    // 1. StatModifier[modifier_count]  — { stat_id: u16, op: u8, value: i64 }
    // 2. Optional: PeriodicBlock_Wire          — if has_periodic_effects flag
    // 3. Optional: ConsumptionWindowBlock_Wire — if has_consumption_window flag
    // 4. Optional: OnExpireEffects             — if has_on_expire_effects flag
}
```

Compiler-generated `apply_cc` statuses serialize using the same wire format. They MUST carry
`polarity = negative`, inherit their authored `is_cleansable` value, serialize their selected
`duration_scaling`, and set a non-zero `cc_behavior_profile` matching the canonical `cc_type`
table. Ordinary authored buffs/debuffs SHOULD use `cc_behavior_profile = none`, but they MAY still
set `cc_category` and `cc_immunity_mask` for CC-admission and immunity-window purposes.

`snapshot_recorder_state_id`, when non-zero, requests the engine's canonical `P-05 Historical
State Buffer` behavior for the referenced runtime-state slot. This is a status-owned recorder flag,
not a separate timer callback.

```
ConsumptionWindowBlock_Wire {
    consume_on:              u8,    // 0=cast_ability, 1=damage_received, 2=on_hit
    flags:                   u8,    // bit 0 = consume_only_on_success
    max_consumptions:        u8,
    override_count:          u8,
    allowed_ability_count:   u16,
    on_consume_effect_count: u16,
    // Inline variable data:
    // 1. allowed_ability_ids[u32; allowed_ability_count]
    // 2. AbilityOverride_Wire[override_count]
    // 3. Effect_Wire[on_consume_effect_count]
}
```

```
AbilityOverride_Wire {
    ability_id:             u32,
    flags:                  u8,     // bit 0 = has_damage_multiplier, bit 1 = has_radius_multiplier, bit 2 = has_add_effects, bit 3 = has_replace_effects
    add_effect_count:       u8,
    replace_effect_count:   u8,
    _reserved:              u8,
    damage_multiplier:      i64,    // I32F32; ignored unless corresponding flag is set
    radius_multiplier:      i64,    // I32F32; ignored unless corresponding flag is set
    // Inline variable data:
    // 1. add_effects[add_effect_count]
    // 2. replace_effects[replace_effect_count]
}
```

---

## 6. Section: Formula Registry (0x13)

Deterministic numeric formulas referenced by ability scaling expressions and `formula_eval()` Lua calls.

```
FormulaEntry {
    formula_id:     u32,        // Numeric formula ID
    op_count:       u16,        // Number of operations in the formula
    input_count:    u16,        // Number of input variables
    // Inline: FormulaOp[op_count] — stack-based evaluation bytecode
    // Inline: InputDecl[input_count] — { name_hash: u32, type: u8 }
}
```

Formulas are stack-based bytecode (RPN) with a bounded operation count (`max_formula_ops_per_eval`). This ensures deterministic, bounded evaluation at runtime.

---

## 7. Section: Static Data Tables (0x14)

Game-defined lookup tables that don't fit into the typed sections above:

### 7.1 Combo Matrix

Serialized from `02-schema-and-validation.md` §10:

```
ComboMatrixTable {
    entry_count:    u16,
    entries:        [ComboMatrixEntry; entry_count],
}

ComboMatrixEntry {
    field_type:     u8,         // ComboFieldType enum
    finisher_type:  u8,         // ComboFinisherType enum
    effect_offset:  u16,        // Offset into inline effect data
    effect_size:    u16,        // Size of the serialized effect
}
```

### 7.2 Spawn Tables

Entity spawn configuration (archetype references, weight tables, conditions):

```
SpawnTableEntry {
    table_id:       u32,
    entry_count:    u16,
    entries:        [SpawnEntry; entry_count],
}

SpawnEntry {
    archetype_id:   u32,
    weight:         u16,        // Relative spawn weight
    condition:      u16,        // Guard expression offset (0xFFFF = unconditional)
}
```

### 7.3 Game Constants

Key-value pairs for game-wide tuning parameters:

```
GameConstantsTable {
    count:          u16,
    entries:        [ConstantEntry; count],
}

ConstantEntry {
    key_hash:       u32,        // FNV-1a hash of the constant name
    value:          i64,        // I32F32 encoded
}
```

### 7.4 Runtime State Table

Serialized from `02-schema-and-validation.md` §10. These are the bounded per-entity state-slot
definitions used by activation modes, bookmark/rewind mechanics, combo windows, and charge pools.

```
RuntimeStateTable {
    entry_count:    u16,
    entries:        [RuntimeStateEntry_Wire; entry_count],
}

RuntimeStateEntry_Wire {
    state_id:       u32,        // Pre-hashed RuntimeStateDefinition.state_id
    kind:           u8,         // 0=bookmark, 1=snapshot_buffer, 2=sequence_window, 3=charge_pool
    flags:          u8,         // Kind-specific flags (defined below)
    charge_type_count: u16,     // Only used by charge_pool entries
    arg0:           u32,        // Kind-specific scalar
    arg1:           u32,        // Kind-specific scalar
    arg2:           u32,        // Kind-specific scalar
    // Optional inline data:
    // 1. Optional min_use_interval_ticks[u32; 1] — only for charge_pool when flags bit 4 is set
    // 2. charge_type_ids[u32; charge_type_count] — only for typed charge_pool entries
}
```

`RuntimeStateEntry_Wire` interpretation by `kind`:

- `bookmark`
  - `arg0 = expires_after_ticks`
  - `arg1 = payload_kind` (`0 = position`, `1 = entity_ref`)
  - `flags bit 0 = capture_topology_epoch`
  - `flags bit 1 = clear_on_owner_death`
- `snapshot_buffer`
  - `arg0 = window_ticks`
  - `arg1 = sample_interval_ticks`
  - `flags bit 0 = clear_on_read`
  - `flags bit 4 = record_position`
  - `flags bit 5 = record_hp`
- `sequence_window`
  - `arg0 = max_step`
  - `arg1 = window_ticks`
  - `arg2 = reset_to_step`
- `charge_pool`
  - `arg0 = capacity`
  - `arg1 = recharge_interval_ticks`
  - `arg2 = decay_ticks`
  - `flags bits 0-1 = recharge_mode` (`0 = none`, `1 = independent`, `2 = all_at_once`)
  - `flags bits 2-3 = decay_mode` (`0 = none`, `1 = all_at_once`, `2 = oldest_first`)
  - `flags bit 4 = has_min_use_interval`
  - if `flags bit 4` is set, one inline `u32 min_use_interval_ticks` follows the header before any
    `charge_type_ids`

All runtime-state references embedded elsewhere in the image use the same pre-hashed `state_id`
space and resolve through this table plus the lookup index in §8.5.

---

## 8. Section: Lookup Indexes (0x20)

O(1) access indexes built by the compiler for runtime content lookup. The engine uses these to locate content by ID without scanning.

### 8.1 Ability Index

Maps `ability_id` → byte offset within the Ability IR Table section.

```
AbilityIndex {
    count:      u32,
    entries:    [IndexEntry; count],   // Sorted by ability_id for binary search
}

IndexEntry {
    id:         u32,
    offset:     u32,        // Byte offset within AbilityIRTable section
}
```

### 8.2 Entity Index

Maps `entity_type_id` → byte offset within Entity Definitions section. Same structure as ability index.

### 8.3 Status Effect Index

Maps `status_id` → byte offset within Status Effect Definitions section. Same structure.

### 8.4 Formula Index

Maps `formula_id` → byte offset within Formula Registry section. Same structure.

### 8.5 Runtime State Index

Maps `state_id` → byte offset within the Runtime State Table subsection of `StaticDataTables`.
Same structure as the other indexes.

---

## 9. Section: Debug Metadata (0xF0, optional)

Present only when the compiler is invoked with debug flags. If present, this section is part of the authenticated image envelope and therefore changes the image digest. Debug and release builds are intentionally distinct artifacts.

Contains:
1. **Source maps** — mapping IR instructions back to source file/line for diagnostics
2. **Ability name table** — human-readable ability names (not present in release builds)
3. **Compiler diagnostics** — warnings emitted during compilation (informational only)

The engine MUST NOT depend on debug metadata for correctness. Release builds SHOULD omit this section entirely.

---

## 10. Section: Signature (0xFF)

Cryptographic signature over `FileHeader.digest` for tamper detection and artifact authenticity.

```
SignatureSection {
    algorithm:      u8,         // 0x01 = Ed25519
    _reserved:      [u8; 3],
    public_key:     [u8; 32],   // Signing public key
    signature:      [u8; 64],   // Signature over FileHeader.digest
}
```

If the `signed` flag is set in the file header, the `Signature` section MUST be present as the terminal section of the file. The runtime MUST verify the signature before activating the image. Verification failure MUST prevent activation and emit an observable fault event.

Unsigned images (development builds) MUST have the `signed` flag cleared and this section omitted.

---

## 11. Integrity and Verification

### 11.1 Load-Time Verification

Before activating a game image, the runtime MUST:

1. Validate the file header magic bytes (`GMIM`).
2. Validate `format_version` is supported.
3. Verify `total_size` matches actual file size.
4. Read the `SectionDirectory` immediately after the header and validate that `section_count` matches the number of directory entries.
5. Recompute SHA-256 over the authenticated image envelope defined in §1.1 and compare it to `FileHeader.digest`.
6. Verify per-section CRC-32 checksums for every section listed in the directory against the exact bytes of that section.
7. If `signed` flag is set, verify the cryptographic signature against `FileHeader.digest`.
8. Parse the `Manifest` section via its type 0x01 directory entry.
9. Validate `adapter_api_major` compatibility with the running adapter.
10. Validate `wire_schema_versions` intersection with runtime capabilities.

Any verification failure MUST prevent activation. The verification chain is non-circular: authenticated image envelope → digest → signature.

### 11.2 Verification Failure Codes

Runtime image verification and activation MUST map failures to stable primary codes. At minimum, implementations MUST use:

- `IMAGE_HEADER_INVALID` — unsupported `format_version`, invalid magic bytes, or malformed fixed header fields
- `IMAGE_SIZE_MISMATCH` — `total_size` does not match the actual file size
- `IMAGE_DIGEST_MISMATCH` — recomputed authenticated digest does not equal `FileHeader.digest`
- `IMAGE_SIGNATURE_INVALID` — signature bytes are present but fail cryptographic verification
- `IMAGE_SIGNATURE_MISSING` — `signed` flag is set but the terminal `Signature` section is absent or truncated
- `IMAGE_ADAPTER_INCOMPATIBLE` — manifest `adapter_api_major` is incompatible with the running adapter
- `IMAGE_WIRE_INCOMPATIBLE` — manifest `wire_schema_versions` has no intersection with runtime-supported wire schema versions

Implementations MAY emit secondary diagnostics, but the primary code for a given root failure MUST be stable across runs.

### 11.3 Activation Protocol

Activation follows `docs-core/04-0-game-adapter-interface.md` §3.5 and `docs-core/04-3-version-line-transition-contract.md`:

1. Image is loaded and verified (§11.1).
2. Lookup indexes are memory-mapped or deserialized into runtime lookup structures.
3. The adapter signals readiness to the engine.
4. The engine atomically activates the new content at a frame boundary.
5. New ability resolutions use the updated IR blocks; in-flight effects from the previous version resolve under their creation-time epoch (epoch pinning).

---

## 12. Size and Performance Constraints

| Constraint | Bound | Rationale |
|-----------|-------|-----------|
| Max image size | 256 MB | Bounded by distribution and loading time |
| Max abilities | 65,536 | u16 index space |
| Max entity types | 65,536 | u16 index space |
| Max status effects | 65,536 | u16 index space |
| Max formulas | 65,536 | u16 index space |
| Section alignment | 8 bytes | Ensures safe memory-mapped access on all platforms |
| String encoding | No raw strings in content sections | All strings are pre-hashed to u32 (FNV-1a) at compile time. Human-readable names live only in debug metadata. |

The "no raw strings" constraint is critical for determinism — string comparison in the 60Hz loop would be non-deterministic in cost. All runtime lookups use numeric IDs or pre-computed hashes.

---

## 13. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `03-compiler-pipeline.md` | Phase 6 (Emission) produces this artifact format. |
| `03-1-compiler-ir-specification.md` | §3 Ability IR Table serializes `AbilityIRBlock` entries from the IR spec. |
| `02-schema-and-validation.md` | Defines the source schemas that compile into sections 3-7. |
| `docs-core/04-0-game-adapter-interface.md` | §3.5: Engine distributes and activates game content via data-epoch mechanisms. |
| `docs-core/04-3-version-line-transition-contract.md` | Defines rollout/rollback behavior for version line transitions. |
| `docs-core/03-durability-bridge.md` | Data epoch distribution for content updates. |
