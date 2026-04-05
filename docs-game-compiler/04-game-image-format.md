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
    flags:                  u8,         // Bitfield: bit 0 = can_counter_vulnerability_window, bit 1 = can_be_counterspelled, bit 2 = requires_concentration, bit 3 = has_channel_policy, bit 4 = has_concentration_policy, bit 5 = has_global_event_policy, bits 6-7 reserved (zero)
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
    // 1. Optional: ChannelPolicy_Wire          — if has_channel_policy flag (§3.3)
    // 2. Optional: ConcentrationPolicy_Wire    — if has_concentration_policy flag (§3.4)
    // 3. Optional: GlobalEventPolicy_Wire      — if has_global_event_policy flag (§3.5)
    // 4. ActivationMode_Wire[activation_mode_count]
    // 5. IRInstruction[instruction_count]
    // 6. IRDirective[directive_count]
    // 7. BindingSlot[binding_count]
    // 8. ParamData[param_data_size] (variable-length parameter payloads)
}
```

`ActivationModes` redirect the public/root ability entry to hidden compiler-generated variant
entries. Hidden variants are serialized as ordinary `AbilityIREntry` records and count toward the
same table/index limits as public abilities.

The fixed header stores the BASE resource pool/cost only. Any `resource_cost.escalation`
authoring lowers into `P-51` param blocks inside this entry's `ParamData`. Likewise,
`modify_resource` and shield `on_absorb_effects` lower into ordinary effect param blocks inside
`ParamData`; only status-owned `resource_stat_links` receive a dedicated counted subrecord below.
Likewise,
`vulnerability_window` lowers into a `P-65` directive payload rather than a dedicated fixed header
field. `channel`, `concentration`, and `global_event` authoring lower into the optional policy
subrecords below, with geometry/filter refs still living in `ParamData` where they share the same
compact selector encodings as other targeting payloads. `group_interaction` likewise lowers into a
`P-54` directive payload plus ordinary session/result tables in `ParamData`; this format version
does not add a dedicated fixed header for group interaction sessions.
Likewise, `link`, `damage_redirect`, `heal_mirror_ratio`, `event_clone`, `origin_override`, and
declarative `despawn_entity` lower into ordinary directive/effect param payloads inside `ParamData`;
this format version adds no dedicated fixed-header fields for those policies. `zone`
mobility / persistence / continuous-force authoring, `displacement.flight_policy`,
`inject_geometry`, `polyline_zone`, `kinematic_sweep`, `enter_container`, `exit_container`,
`fork_instance`, `split_form`, and `spawn_actor.portal_anchor` likewise lower into ordinary `P-32`
/ `P-44` / `P-14` / `P-08` / `P-57` / `P-07` / `P-58` / `P-56` / `P-30` param blocks inside
`ParamData`. The same is true for ability-local `spawn_actor.placement`, `spawn_actor.autonomy`,
`spawn_actor.interaction`, `spawn_actor.coverage`, `spawn_actor.instance_limit`,
`spawn_actor.loadout_projection`, `spawn_actor.control_projection`,
`spawn_actor.respawn_anchor`, `start_actor_transit`, and `cycle_split_form`: they
serialize as ordinary spawn/routing-behavior param payloads, not as new fixed headers on
`EntityDefinition_Wire`, because two abilities may spawn the same archetype with different
formation offsets, live limits, proximity payloads, coverage-network IDs, projected source
snapshots, split-form member bindings, owner-body return policy, or rebirth-anchor delay. Only status-owned
`zone_relation_gate` and `movement_constraint` receive dedicated status subrecords below. Static `container_profile`
metadata remains on `EntityDefinition_Wire`, because capacity, entry range, and occupant cast
policy are archetype setup rather than ability-instance payload. The same is true for
`revive_corpse`, `restore_phase`, `consume_corpse`, and `swap_identity.source = {
corpse_snapshot: ... }`: they lower into ordinary lifecycle/resource `ParamData` payloads and
runtime-state selectors rather than introducing new fixed headers on `AbilityIREntry`.
Combo-matrix rows likewise serialize ordinary effect-list blobs; contextual selectors such as
`combo_field_entity`, `combo_field_owner`, `combo_field_position`, `finisher_position`,
`projected_actor`, `projected_actor_position`, `transit_actor`, and
`transit_actor_position` are just additional compact `EntityRef` /
`PositionRef` selector values inside those blobs.

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

### 3.3 Serialized ChannelPolicy

Present when the `has_channel_policy` flag is set. Serializes
`02-schema-and-validation.md` §5.8.

```
ChannelPolicy_Wire {
    execution_mode:               u8,     // 0=complete_only, 1=tick_while_active
    movement_lock:                u8,     // 0=none, 1=root
    continuous_input:             u8,     // 0=none, 1=steer_aim, 2=steer_target_movement
    flags:                        u8,     // bit 0 = allow_other_abilities, bit 1 = break_on_displacement, bit 2 = break_on_target_invalid
    tick_interval_ticks:          u16,    // 0 when execution_mode = complete_only
    _padding:                     [u8; 2],
    interrupt_damage_threshold:   i64,    // I32F32; 0 = no damage-threshold break
    partial_cooldown_refund:      i64,    // I32F32 in [0, 1]
}
// Fixed size: 24 bytes
```

### 3.4 Serialized ConcentrationPolicy

Present when the `has_concentration_policy` flag is set. Serializes
`02-schema-and-validation.md` §5.9.

```
ConcentrationPolicy_Wire {
    check_formula:         u8,     // 0=standard_half_damage_floor_10
    flags:                 u8,     // bit 0 = allow_manual_cancel, bit 1 = replace_existing
    _padding:              [u8; 2],
    max_duration_ticks:    u32,    // 0 = unbounded
}
// Fixed size: 8 bytes
```

If `requires_concentration` is set but `has_concentration_policy` is clear, the runtime uses the
canonical defaults from `02-schema-and-validation.md` §5.9.

### 3.5 Serialized GlobalEventPolicy

Present when the `has_global_event_policy` flag is set. Serializes
`02-schema-and-validation.md` §5.10.

```
GlobalEventPolicy_Wire {
    schedule_lead_ticks:     u32,
    pulse_interval_ticks:    u32,    // 0 = one-shot
    duration_ticks:          u32,    // 0 = one-shot
    target_class:            u8,     // 0=all_entities, 1=heroes_only, 2=structures_only
    geometry_type:           u8,     // 0=whole_mesh, 1=circle, 2=ring
    flags:                   u8,     // bit 0 = cancel_if_owner_removed
    _padding:                u8,
}
// Fixed size: 16 bytes
```

`filter`, `epicenter`, `radius`, and `ring_inner` stay in ordinary `ParamData`, because they reuse
the same selector/reference encodings as other targeting and geometry payloads.

### 3.6 Serialized ActivationMode

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

### 3.7 Serialized IRInstruction

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

### 3.8 Serialized IRDirective

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

### 3.8 Bounds

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
    flags:              u16,        // Bitfield: bit 0 = has_stagger_bar, bit 1 = has_downed_state, bit 2 = has_projectile_config, bit 3 = has_block_defense, bit 4 = has_loadout_profiles, bit 5 = has_control_topology, bit 6 = has_targetability_policy, bit 7 = has_observer_presentation, bit 8 = has_container_profile, bit 9 = has_corpse_profile, bit 10 = has_ghost_phase, bits 11-15 reserved (zero)

    // Variable-length inline data:
    // 1. StatEntry_Wire[stat_count]
    // 2. ResourcePoolEntry_Wire[resource_pool_count]
    // 3. AbilityRef_Wire[ability_count]
    // 4. PassiveRef_Wire[passive_count]
    // 5. Optional: StaggerBarDef_Wire          — if has_stagger_bar flag (§4.3)
    // 6. Optional: DownedStateDef_Wire         — if has_downed_state flag (§4.4)
    // 7. Optional: ProjectileConfigDef_Wire         — if has_projectile_config flag (§4.5)
    // 8. Optional: BlockDefenseDef_Wire        — if has_block_defense flag (§4.6)
    // 9. Optional: LoadoutProfileTable_Wire    — if has_loadout_profiles flag (§4.7)
    // 10. Optional: ControlTopologyDef_Wire    — if has_control_topology flag (§4.8)
    // 11. Optional: TargetabilityPolicy_Wire   — if has_targetability_policy flag (§4.9)
    // 12. Optional: ObserverPresentation_Wire  — if has_observer_presentation flag (§4.10)
    // 13. Optional: ContainerProfileDef_Wire   — if has_container_profile flag (§4.10.1)
    // 14. Optional: CorpseProfileDef_Wire      — if has_corpse_profile flag (§4.4.1)
    // 15. Optional: GhostPhaseDef_Wire         — if has_ghost_phase flag (§4.4.2)
}
```

Static `loadout_profiles` and `control_topology` serialize here because they are entity-setup
metadata. By contrast, authored `swap_identity` and `borrow_ability_slot` effects lower into
ability-local `P-31` param blocks inside `AbilityIREntry.ParamData`, while `control_override`
lowers into a pending Stage 1 routing mutation payload.

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

ResourceScalarEntry_Wire {
    pool_id:    u32,    // Pre-hashed pool name
    _padding:   [u8; 4],
    value:      i64,    // I32F32 scalar
}
// Fixed size: 16 bytes
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
    rally_hp_ratio:             i64,    // I32F32: fraction of base max HP restored on rally
    rally_channel_ticks:        u32,    // Ticks to channel self-rally
    finish_channel_ticks:       u32,    // Ticks to channel finish on a downed enemy
    downed_ability_count:       u16,    // Number of ability refs available while downed
    phase_flags:                u16,    // bit 0 = self_rally_on_kill
    // Inline: AbilityRef_Wire[downed_ability_count]
}
// Fixed header size: 32 bytes + variable ability refs
```

#### 4.4.1 CorpseProfileDef_Wire

Present when the `has_corpse_profile` flag is set. Serializes
`02-schema-and-validation.md` §7.2.2.

```
CorpseProfileDef_Wire {
    persist_ticks:            u32,    // Lifetime of corpse-registry entry
    corpse_flags:             u16,    // bit 0 = retain_effective_stats, bit 1 = retain_loadout_snapshot
    _padding:                 [u8; 2],
}
// Fixed size: 8 bytes
```

#### 4.4.2 GhostPhaseDef_Wire

Present when the `has_ghost_phase` flag is set. Serializes
`02-schema-and-validation.md` §7.2.1.

```
GhostPhaseDef_Wire {
    ghost_duration_ticks:       u32,
    respawn_delay_credit_ticks: u32,
    ghost_ability_count:        u16,
    phase_flags:                u16,    // bit 0 = clear_statuses_on_enter
    // Inline: AbilityRef_Wire[ghost_ability_count]
}
// Fixed header size: 12 bytes + variable ability refs
```

#### 4.5 ProjectileConfigDef_Wire

Present when the `has_projectile_config` flag is set. Serializes the projectile/trap behavior
fields from `02-schema-and-validation.md` §6.7.1-6.7.5.1.

```
ProjectileConfigDef_Wire {
    speed:                      i64,    // I32F32: velocity in units/tick
    turn_rate:                  i64,    // I32F32: max angular change per tick (0 = non-homing)
    pierce:                     u8,     // Targets passed through before stopping
    flags:                      u8,     // bit 0 = homing, bit 1 = manual_trigger_enabled, bit 2 = has_travel_scalars, bit 3 = has_return_policy, bit 4 = has_bounce_policy, bit 5 = has_attachment_policy, bit 6 = has_carry_policy
    entity_impact_behavior:     u8,     // Enum: 0=Ignore, 1=Stop, 2=Detonate, 3=DetonateAfterPierceExhausted
    world_impact_behavior:      u8,     // Enum: 0=Ignore, 1=Bounce, 2=Stop, 3=Detonate
    expiry_behavior:            u8,     // Enum: 0=Despawn, 1=Detonate
    _padding0:                  [u8; 3],
    arming_delay_ticks:         u32,    // Ticks before detonation-capable triggers arm
    proximity_trigger_radius:   i64,    // I32F32: 0 = disabled, >0 = armed proximity radius
    // Optional inline subrecords:
    // 1. ProjectileTravelScalars_Wire  — if has_travel_scalars flag
    // 2. ProjectileReturnPolicy_Wire   — if has_return_policy flag
    // 3. ProjectileBouncePolicy_Wire   — if has_bounce_policy flag
    // 4. ProjectileAttachmentPolicy_Wire — if has_attachment_policy flag
    // 5. ProjectileCarryPolicy_Wire    — if has_carry_policy flag
}
// Fixed header size: 36 bytes + optional subrecords

Projectile travel mutation, return-flight, bounce counters, and attachment delay are all
archetype-owned projectile behavior. By contrast, `displacement.flight_policy` remains
ability-local and lowers into ordinary `P-02` / `P-07` param blocks inside
`AbilityIREntry.ParamData`; it does not add new fixed entity-definition headers.

```
ProjectileTravelScalars_Wire {
    radius_growth_per_unit:     i64,    // I32F32
    payload_scale_per_unit:     i64,    // I32F32
    max_scaled_radius:          i64,    // I32F32: 0 = uncapped / disabled
}
// Fixed size: 24 bytes
```

```
ProjectileReturnPolicy_Wire {
    trigger:                    u8,     // 0=max_range, 1=manual_recall, 2=world_impact
    track_mode:                 u8,     // 0=source_entity_current, 1=source_entity_last_known_on_loss
    flags:                      u8,     // bit 0 = allow_repeat_hits_on_return, bit 1 = preserve_speed
    _padding:                   u8,
    despawn_radius:             i64,    // I32F32
}
// Fixed size: 12 bytes
```

```
ProjectileBouncePolicy_Wire {
    max_bounces:                u8,
    flags:                      u8,     // bit 0 = preserve_speed
    _padding:                   [u8; 2],
}
// Fixed size: 4 bytes
```

```
ProjectileAttachmentPolicy_Wire {
    delay_ticks:                u32,
    on_carrier_loss:            u8,     // 0=last_known_position, 1=fizzle
    flags:                      u8,     // bit 0 = follow_attached_entity, bit 1 = preserve_original_payload
    _padding:                   [u8; 2],
}
// Fixed size: 8 bytes
```

```
ProjectileCarryPolicy_Wire {
    max_carried_targets:        u8,
    _padding0:                  [u8; 7],
    carry_offset_distance:      i64,    // I32F32
    lateral_spacing:            i64,    // I32F32
}
// Fixed size: 24 bytes
```
```

#### 4.6 BlockDefenseDef_Wire

Present when the `has_block_defense` flag is set. Serializes
`02-schema-and-validation.md` §7.3.

```
BlockDefenseDef_Wire {
    chance_stat_id:          u16,    // Pre-hashed stat name
    applies_to:              u8,     // 0=direct_hits, 1=weapon_hits_only, 2=all_damage_events
    flags:                   u8,     // bit 0 = negates_non_damage_effects
    dr_penalty_per_block:    i64,    // I32F32
    dr_decay_interval_ticks: u32,
    max_dr_stacks:           u16,    // 0 = uncapped
    _padding:                [u8; 2],
}
// Fixed size: 20 bytes
```

#### 4.6.1 ContainerProfileDef_Wire

Present when the `has_container_profile` flag is set. Serializes
`02-schema-and-validation.md` §7.3.1.

```
ContainerProfileDef_Wire {
    max_capacity:            u16,
    occupant_cast_policy:    u8,    // 0=none, 1=basic_attacks_only, 2=all
    occupant_storage_mode:   u8,    // 0=attached_visible, 1=off_world_stored
    flags:                   u8,    // bit 0 = occupant_can_be_targeted, bit 1 = allow_manual_exit, bit 2 = eject_on_removed
    _padding:                [u8; 3],
    allowed_filter_id:       u32,   // Pre-hashed filter identifier
    entry_range:             i64,   // I32F32
}
// Fixed size: 20 bytes
```

#### 4.7 LoadoutProfileTable_Wire

Present when the `has_loadout_profiles` flag is set. Serializes
`02-schema-and-validation.md` §7.4.

```
LoadoutProfileTable_Wire {
    profile_count:    u16,
    _padding:         [u8; 2],
    // Inline: LoadoutProfileDef_Wire[profile_count]
}
// Fixed header size: 4 bytes + variable profile data

LoadoutProfileDef_Wire {
    profile_id:                 u32,    // Pre-hashed profile name
    ability_count:              u16,
    passive_count:              u16,
    resource_multiplier_count:  u16,
    stat_multiplier_count:      u16,
    stat_override_count:        u16,
    flags:                      u16,    // bit 0 = has_max_hp_multiplier, bit 1 = has_movement_speed_multiplier, bit 2 = has_appearance_id, bit 3 = inherit_abilities, bit 4 = inherit_passives
    // Variable-length inline data:
    // 1. Optional: max_hp_multiplier(i64)           — if has_max_hp_multiplier
    // 2. Optional: movement_speed_multiplier(i64)   — if has_movement_speed_multiplier
    // 3. Optional: appearance_id(u32)               — if has_appearance_id
    // 4. AbilityRef_Wire[ability_count]             — omitted if inherit_abilities
    // 5. PassiveRef_Wire[passive_count]             — omitted if inherit_passives
    // 6. ResourceScalarEntry_Wire[resource_multiplier_count]
    // 7. StatEntry_Wire[stat_multiplier_count]
    // 8. StatEntry_Wire[stat_override_count]
}
```

If `inherit_abilities` or `inherit_passives` is set, the corresponding count MUST be zero and the
parent `EntityDefinition_Wire` arrays remain in force for that profile. If the inherit flag is
clear, a zero count means the profile deliberately exposes none of that category.

#### 4.8 ControlTopologyDef_Wire

Present when the `has_control_topology` flag is set. Serializes
`02-schema-and-validation.md` §7.5-§7.6.

```
ControlTopologyDef_Wire {
    mode:               u8,     // 0=one_to_many, 1=many_to_one
    input_policy:       u8,     // 0=mirror, 1=role_split, 2=adapter_routed
    selection_mode:     u8,     // 0=single, 1=multiple, 2=all
    elimination_policy: u8,     // 0=all_members_removed, 1=primary_removed, 2=shared_entity_removed
    member_count:       u16,
    _padding:           [u8; 2],
    // Inline: ControlMemberDef_Wire[member_count]
}
// Fixed header size: 8 bytes + variable member data

ControlMemberDef_Wire {
    role_id:            u32,    // Pre-hashed role name
    entity_type_id:     u32,    // 0 when this member addresses the shared entity in many-to-one mode
    loadout_profile_id: u32,    // 0 = none
    control_scope:      u8,     // 0=full, 1=movement_only, 2=abilities_only, 3=observer_only
    flags:              u8,     // bit 0 = is_primary
    _padding:           [u8; 2],
}
// Fixed size: 16 bytes
```

`member_count` MUST respect the core `max_multiplex_group_size` bound. `many_to_one` entries
serialize the shared entity once in the parent `EntityDefinition_Wire`; member rows describe role
inputs and optional `loadout_profile_id` restrictions rather than distinct spawned archetypes.

#### 4.9 TargetabilityPolicy_Wire

Present when the `has_targetability_policy` flag is set. Serializes
`02-schema-and-validation.md` §9.11.

```
TargetabilityPolicy_Wire {
    flags:   u8,   // bit 0 = hostile_effects, bit 1 = allied_beneficial_effects, bit 2 = allied_harmful_effects, bit 3 = self_effects, bit 4 = affected_by_area_effects, bit 5 = collidable_for_skillshots, bit 6 = collidable_for_pathing
    _padding:[u8; 3],
}
// Fixed size: 4 bytes
```

#### 4.10 ObserverPresentation_Wire

Present when the `has_observer_presentation` flag is set. Serializes
`02-schema-and-validation.md` §9.12.

```
ObserverPresentation_Wire {
    visibility_flags:      u8,    // bit 0 = visible_to_enemies, bit 1 = visible_to_allies, bit 2 = visible_to_self
    appearance_source:     u8,    // 0=self, 1=mirror_entity
    enemy_hp_presentation: u8,    // 0=authoritative, 1=full, 2=mirror_source_percent
    ally_marker:           u8,    // 0=none, 1=decoy_indicator
    source_entity_ref:     u32,   // 0 when appearance_source = self
}
// Fixed size: 8 bytes
```

---

## 5. Section: Status Effect Definitions (0x12)

Serialized buff/debuff/CC definitions from `02-schema-and-validation.md` §9.

### 5.1 Entry Structure

```
StatusEffectDef_Wire {
    status_id:          u32,        // Numeric status ID
    max_stacks:         u8,
    _reserved0:         u8,
    flags:              u16,        // Bitfield: bit 0 = is_passive, bit 1 = is_cleansable, bit 2 = has_periodic_effects, bit 3 = has_on_expire_effects, bit 4 = has_consumption_window, bit 5 = has_damage_accumulator, bit 6 = has_deferred_ledger, bit 7 = has_hp_floor, bit 8 = has_death_prevention, bit 9 = has_movement_damage, bit 10 = has_targetability_policy, bit 11 = has_observer_presentation, bit 12 = has_suspension, bit 13 = has_projectile_intercept, bit 14 = has_zone_relation_gate, bit 15 = has_movement_constraint
    polarity:           u8,         // StatusPolarity enum: 0=neutral, 1=positive, 2=negative
    status_application_immunity: u8, // StatusApplicationImmunity enum: 0=none, 1=negative, 2=positive, 3=all
    cc_category:        u8,         // CcCategory enum: 0=none, 1=displacement, 2=hard_disable, 3=soft_disable, 4=forced_movement, 5=target_override, 6=mute
    duration_scaling:   u8,         // StatusDurationScaling enum: 0=fixed, 1=status_resistance
    cc_behavior_profile: u8,        // CcBehaviorProfile enum: 0=none, 1=stun, 2=root, 3=silence, 4=sleep, 5=disarm, 6=blind, 7=fear, 8=charm, 9=taunt, 10=berserk, 11=mute
    cc_immunity_mask:   u8,         // Bitmask over CcCategory values; 0 = none
    duration_ticks:     u32,
    modifier_count:     u16,        // Stat modifiers
    resource_stat_link_count: u16,  // Status-owned resource-to-stat overlays
    capability_flags:   u16,        // P-26 capability bitmask: bit 0=CAN_MOVE, bit 1=CAN_CAST, bit 2=CAN_ATTACK, bit 3=CAN_USE_ITEMS, bit 4=PASSIVES_ACTIVE, bits 5-15 reserved
    snapshot_recorder_state_id: u32, // 0 = none; references RuntimeStateTable entry of kind snapshot_buffer

    // Variable-length inline data:
    // 1. StatModifier[modifier_count]  — { stat_id: u16, op: u8, value: i64 }
    // 2. ResourceStatLink_Wire[resource_stat_link_count]
    // 3. Optional: PeriodicBlock_Wire          — if has_periodic_effects flag
    // 4. Optional: ConsumptionWindowBlock_Wire — if has_consumption_window flag
    // 5. Optional: DamageAccumulatorDef_Wire   — if has_damage_accumulator flag
    // 6. Optional: DeferredLedgerDef_Wire      — if has_deferred_ledger flag
    // 7. Optional: HpFloorDef_Wire             — if has_hp_floor flag
    // 8. Optional: DeathPreventionDef_Wire     — if has_death_prevention flag
    // 9. Optional: MovementDamageDef_Wire      — if has_movement_damage flag
    // 10. Optional: TargetabilityPolicy_Wire    — if has_targetability_policy flag
    // 11. Optional: ObserverPresentation_Wire  — if has_observer_presentation flag
    // 12. Optional: SuspensionDef_Wire         — if has_suspension flag
    // 13. Optional: ProjectileInterceptDef_Wire — if has_projectile_intercept flag
    // 14. Optional: ZoneRelationGateDef_Wire   — if has_zone_relation_gate flag
    // 15. Optional: MovementConstraintDef_Wire — if has_movement_constraint flag
    // 16. Optional: OnExpireEffects            — if has_on_expire_effects flag
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

`damage_accumulator.bind_total_as` is a compiler-local binding name only, so it is NOT serialized
here. The wire format carries only the runtime behavior flags for the accumulator policy.

`resource_stat_links` serialize as a counted inline array rather than consuming another flag bit,
because the 16-bit status `flags` field is already fully allocated. A zero
`resource_stat_link_count` means the status has no live resource-backed stat overlays.

```
ResourceStatLink_Wire {
    pool_id:      u32,    // Pre-hashed pool name
    stat_id:      u16,    // Pre-hashed stat name
    operation:    u8,     // 0=add_flat, 1=add_percent, 2=multiply
    _padding:     u8,
    coefficient:  i64,    // I32F32
}
// Fixed size: 16 bytes
```

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
DamageAccumulatorDef_Wire {
    flags:        u8,    // bit 0 = include_absorbed_damage
    _padding:     [u8; 3],
}
// Fixed size: 4 bytes
```

```
DeferredLedgerDef_Wire {
    flags:        u8,    // bit 0 = freeze_observer_hp
    remove_policy:u8,    // 0=resolve_immediately, 1=discard
    _padding:     [u8; 2],
}
// Fixed size: 4 bytes
```

```
HpFloorDef_Wire {
    min_hp:       i64,   // I32F32
}
// Fixed size: 8 bytes
```

```
DeathPreventionDef_Wire {
    restore_hp_ratio: i64, // I32F32
    flags:            u8,  // bit 0 = consume_on_trigger, bit 1 = bypass_anti_heal
    _padding:         [u8; 7],
}
// Fixed size: 16 bytes
```

```
MovementDamageDef_Wire {
    damage_per_unit:   i64, // I32F32
    max_damage_per_tick: i64, // I32F32; ignored unless flags bit 0 is set
    damage_type:       u8,  // Game-defined damage-type enum
    flags:             u8,  // bit 0 = has_damage_cap
    _padding:          [u8; 6],
}
// Fixed size: 24 bytes
```

```
SuspensionDef_Wire {
    mode:              u8,   // 0=suspended, 1=dormant, 2=stasis
    flags:             u8,   // bit 0 = invulnerable, bit 1 = pause_status_timers, bit 2 = pause_ability_cooldowns, bit 3 = interrupt_active_casts, bit 4 = interrupt_active_channels, bit 5 = exclude_from_payloads
    _padding:          [u8; 2],
}
// Fixed size: 4 bytes
```

```
ProjectileInterceptDef_Wire {
    mode:                     u8,   // 0=reflect_to_source
    max_redirect_generations: u8,
    fallback_target:          u8,   // 0=last_known_source_position, 1=despawn
    flags:                    u8,   // bit 0 = preserve_original_payload
}
// Fixed size: 4 bytes
```

```
ZoneRelationGateDef_Wire {
    zone_state_id:             u32,   // References RuntimeStateTable entry of kind bookmark
    flags:                     u8,    // bit 0 = require_target_inside, bit 1 = require_hostile_source_inside, bit 2 = reject_damage, bit 3 = reject_hostile_effects
    _padding:                  [u8; 3],
}
// Fixed size: 8 bytes
```

```
MovementConstraintDef_Wire {
    anchor_state_id:           u32,   // References RuntimeStateTable entry of kind bookmark
    max_distance:              i64,   // I32F32
    damage_per_unit:           i64,   // I32F32; 0 unless mode = damage
    mode:                      u8,    // 0=clamp, 1=reverse, 2=damage
    flags:                     u8,    // bit 0 = apply_to_forced_movement, bit 1 = apply_to_teleports
    _padding:                  [u8; 2],
}
// Fixed size: 24 bytes
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
    effects_offset: u16,        // Offset into inline serialized EffectList data
    effects_size:   u16,        // Size of the serialized EffectList blob
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
