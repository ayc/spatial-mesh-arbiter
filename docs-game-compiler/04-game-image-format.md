# Game Image Format

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define the binary artifact that the Game Compiler emits and the engine runtime loads. The game image is the single distributable unit containing all compiled game content — ability IR blocks, entity definitions, status effects, formulas, and lookup tables.

---

## 1. Artifact Identity

Each emitted image MUST include:

- a fixed-size `FileHeader` containing the image format version, total size, and authenticated digest
- a `Manifest` section containing compatibility and identity metadata
- a `SectionDirectory` describing every non-header section except the optional terminal `Signature`

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
    flags:          u16,        // Bit flags (signed, debug-present, compressed)
    section_count:  u16,        // Number of SectionEntry records in SectionDirectory
    _reserved:      [u8; 6],    // Zero-padded for alignment
    total_size:     u64,        // Total file size in bytes
    digest:         [u8; 32],   // SHA-256 of authenticated image envelope (§1.1)
}
// Fixed size: 56 bytes
```

### 2.2 Section Directory

The `SectionDirectory` immediately follows the fixed-size header. It contains one `SectionEntry` for every non-header section present in the image except the optional terminal `Signature` section. This lets the runtime parse the image deterministically from the header alone.

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
    resource_cost:          i64,        // I32F32 encoded
    cast_time_ticks:        u32,
    targeting_type:         u8,         // TargetingType enum
    cast_immunity:          u8,         // CcImmunityTier enum (0 = none)
    flags:                  u8,         // Bitfield: is_counter, is_counterable, requires_concentration
    combo_finisher:         u8,         // ComboFinisherType enum (0 = none)
    _padding:               [u8; 4],    // Alignment padding

    // Variable-length sections (offsets relative to entry start)
    // Note: stagger_damage is NOT a block-level field. It is a parameter on
    // individual damage instructions within the ability's instruction list,
    // consistent with 03-1-compiler-ir-specification.md and 02-schema-and-validation.md §5.1.
    instruction_count:      u16,
    directive_count:        u16,
    binding_count:          u16,
    param_data_size:        u16,        // Total bytes for all param blocks

    // Inline arrays follow in order:
    // 1. IRInstruction[instruction_count]
    // 2. IRDirective[directive_count]
    // 3. BindingSlot[binding_count]
    // 4. ParamData[param_data_size] (variable-length parameter payloads)
}
```

### 3.3 Serialized IRInstruction

```
IRInstruction_Wire {
    primitive_id:   u8,         // P-01 through P-65
    stage:          u8,         // PipelineStage enum
    guard_offset:   u16,        // Offset into ParamData (0xFFFF = no guard)
    param_offset:   u16,        // Offset into ParamData
    param_size:     u16,        // Size of param block in bytes
    output_binding: u16,        // Binding slot index (0xFFFF = no output)
}
// Fixed size: 10 bytes
```

### 3.4 Serialized IRDirective

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

### 3.5 Bounds

| Constraint | Limit | Source |
|-----------|-------|--------|
| Instructions per ability | `<= MAX_INSTRUCTIONS_PER_ABILITY` (default: 32) | `03-1-compiler-ir-specification.md` §7 |
| Directives per ability | `<= 16` | Cross-cutting primitive count |
| Bindings per ability | `<= MAX_BINDINGS_PER_ABILITY` (default: 16) | `03-1-compiler-ir-specification.md` §7 |
| Param data per ability | `<= 4096 bytes` | Prevents unbounded ability payloads |
| Total abilities per image | `<= 65536` | u16 index space |

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
    ability_count:      u16,        // Number of ability ID references
    passive_count:      u16,        // Number of passive status effect references
    flags:              u16,        // Bitfield: has_stagger_bar, has_downed_state

    // Variable-length inline data:
    // 1. StatEntry[stat_count]         — { stat_id: u16, value: i64 }
    // 2. AbilityRef[ability_count]     — { ability_id: u32 }
    // 3. PassiveRef[passive_count]     — { status_id: u32 }
    // 4. Optional: StaggerBarDef       — if has_stagger_bar flag
    // 5. Optional: DownedStateDef      — if has_downed_state flag
}
```

---

## 5. Section: Status Effect Definitions (0x12)

Serialized buff/debuff/CC definitions from `02-schema-and-validation.md` §9.

### 5.1 Entry Structure

```
StatusEffectDef_Wire {
    status_id:          u32,        // Numeric status ID
    max_stacks:         u8,
    flags:              u8,         // Bitfield: is_passive, is_cleansable
    cc_category:        u8,         // CcCategory enum (0 = none)
    _reserved:          u8,
    duration_ticks:     u32,
    modifier_count:     u16,        // Stat modifiers
    capability_flags:   u16,        // P-26 capability mask (if CC)

    // Variable-length inline data:
    // 1. StatModifier[modifier_count]  — { stat_id: u16, op: u8, value: i64 }
    // 2. Optional: PeriodicBlock       — if has periodic effects
    // 3. Optional: OnExpireEffects     — effect list for expiry
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

### 11.2 Activation Protocol

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
