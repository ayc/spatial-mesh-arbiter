# Compiler Pipeline

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT  
**Purpose:** Define the architectural stages of the Game Compiler. This document describes the deterministic pipeline that ingests designer-authored code (Lua/YAML), validates it against engine constraints, and lowers it into the canonical `AbilityIRBlock` representation defined in `03-1-compiler-ir-specification.md` (`IRInstruction`, `IRDirective`, metadata, and binding table).

---

## 1. Pipeline Overview

The compiler is a deterministic, stateless transformation pipeline. It takes a set of source files and produces a signed `GameImage`.

The pipeline executes in strictly ordered phases:
1. **Ingestion & Parsing** (AST Generation)
2. **Semantic Analysis** (Type checking and Symbol resolution)
3. **Lowering & Guard Extraction** (Converting AST to IR primitives)
4. **Binding Allocation** (Memory layout for the IR)
5. **Safety & Bounds Validation** (Enforcing engine constraints)
6. **Emission** (Generating the Game Image)

If any phase encounters an error, the compilation MUST fail closed and emit deterministic diagnostic codes.

---

## 2. Phase 1: Ingestion & Parsing

**Input:** Raw `.lua`, `.yaml`, or `.json` files.
**Output:** Abstract Syntax Tree (AST).

1. **Format Canonicalization:** The compiler parses YAML/JSON data structures and the restricted Lua-subset profile (`01-1-lua-subset-profile.md`).
2. **AST Construction:** All inputs are converted into a unified, language-agnostic AST. 
3. **Rejection:** Any forbidden Lua syntax (e.g., `while` loops, `goto`, `math.random`) MUST be rejected during this phase with a `LUA_PROFILE_UNSUPPORTED_FEATURE` diagnostic.

---

## 3. Phase 2: Semantic Analysis

**Input:** Unified AST.
**Output:** Typed AST with resolved symbols.

1. **Symbol Resolution:** Every function call in the AST is checked against the Whitelisted API (`01-2-lua-whitelisted-api.md`). Unknown symbols trigger `LUA_API_UNKNOWN_SYMBOL`.
2. **Type Checking:** Arguments passed to API functions MUST match the expected domains (e.g., passing a `SimFixed` where an `EntityID` is expected fails).
3. **Context Validation:** The compiler verifies that the rule is executing in the correct environment (`edge`, `arbiter`, or `meta`). For example, calling `spend_resource` in an `edge` validation script triggers `LUA_API_CONTEXT_FORBIDDEN`.

---

## 4. Phase 3: Lowering & Guard Extraction

**Input:** Typed AST.
**Output:** Partially resolved `AbilityIRBlock` template (`IRInstruction` entries, `IRDirective` entries, metadata, symbolic binding names).

This is the core translation phase where game logic becomes engine primitives.

1. **Primitive Mapping:** Allowed API calls are mapped to either a corresponding `PrimitiveId` (P-01 through P-66), an ability-metadata field, or a cross-cutting `IRDirective`.
2. **Metadata Population:** Ability-scoped properties such as cooldown, resource cost, cast time, targeting type, counter flags, concentration flags, and finisher classifications are extracted into the `AbilityIRBlock` metadata.
3. **Guard Extraction and P-17 Lowering:** 
    * The compiler walks the AST looking for `if/elseif` control-flow blocks.
    * These blocks are extracted and converted into the engine's `GuardExpr` enum (for example, `if target.hp < 25 then ...` becomes `GuardExpr::HpBelow`).
    * P-17 (Conditional Thresholds) is therefore lowered as a guard expression, not as a standalone `IRInstruction`.
    * No Lua bytecode is emitted for control flow.
4. **Cross-Cutting Directive Emission:** Primitives that the IR spec classifies as cross-cutting (`P-26`, `P-27`, `P-28`, `P-32`, `P-33`, `P-34`, `P-47`, `P-56`) are emitted as `IRDirective` entries or metadata fields rather than stage-specific `IRInstruction` entries.
5. **Stage Assignment:** For stage-specific primitives, the compiler automatically assigns the required `PipelineStage` using the IR-spec mapping plus data-dependency context. For example, a spatial query driven only by intent-time inputs lowers to `TargetResolution`, while a spatial query centered on a binding emitted by `KinematicResolution` lowers to `PostKinematic`.
6. **Lowering Failure Contract:** If a semantically valid construct cannot be mapped into a legal IR form, the compiler MUST fail with deterministic lowering diagnostics rather than emitting partial runtime logic.

---

## 5. Phase 4: Binding Allocation

**Input:** Partially resolved `AbilityIRBlock` template with symbolic binding names.
**Output:** IR with fully resolved `BindingTable` and canonical `BindingRef` assignments.

The engine cannot allocate memory dynamically in the 60Hz tick loop. The compiler MUST pre-calculate all intermediate variable storage.

1. **Data Flow Analysis:** The compiler traces symbolic values that are produced by one instruction/directive and consumed by another (for example, saving the result of a `Shape Overlap Query` to use in `Value Modification`).
2. **Slot Assignment:** Each distinct intermediate value is assigned a `BindingSlot` in the ability's binding table.
3. **Canonical Slot Ordering:** Binding slots MUST be assigned in a deterministic order based on first definition and first use, not on incidental source variable names. Equivalent source forms MUST yield identical binding layouts.
4. **Instruction/Directive Patching:** `IRInstruction` and `IRDirective` parameter blocks are updated to reference the assigned `BindingRef` index instead of AST-local names.

---

## 6. Phase 5: Safety & Bounds Validation

**Input:** Resolved IR sequence and Binding Table.
**Output:** Validated `AbilityIRBlock`.

Before emission, the compiler MUST prove the ability will not crash or stall the engine.

1. **Instruction Bound Check:** The length of the instruction vector MUST NOT exceed `MAX_INSTRUCTIONS_PER_ABILITY` (default: 32).
2. **Binding Bound Check:** The size of the binding table MUST NOT exceed `MAX_BINDINGS_PER_ABILITY` (default: 16).
3. **Structural IR Validation:** The compiler verifies that every `BindingRef` resolves, cross-cutting primitives appear only as `IRDirective`/metadata entries, and the lowered data-flow graph is acyclic.
4. **Cascade and Re-entrancy Validation:** The compiler verifies that reactive hooks, timer payloads, and other deferred effects are emitted in forms that re-enter only at the next tick where required by the IR spec. Any lowering that would require same-tick PostDamage or StateUpdate re-entry MUST be rejected.
5. **Canonicalization and Numeric Normalization:** All numeric literals are converted to their canonical `I32F32` (`SimFixed`) representation, IR fields are ordered canonically, and incidental source-order differences (temporary names, declaration ordering) are erased from the normalized IR shape.

---

## 7. Phase 6: Emission

**Input:** Validated `AbilityIRBlock` set.
**Output:** Signed `GameImage` artifact.

1. **Serialization:** The IR blocks, alongside static data (Entity Definitions, Spawn Tables, Formula Registries), are serialized into the binary format defined in `04-game-image-format.md`.
2. **Manifest and Digest Generation:** The compiler generates manifest metadata and deterministic content digests/checksums required by `04-game-image-format.md`.
3. **Signature Sealing:** If the build profile requires signed artifacts, the compiler signs the emitted `GameImage` deterministically after serialization and digest generation.
4. **Deterministic Build Guarantee:** Given the exact same source files, compiler version, build profile, and signing inputs, this phase MUST emit a byte-for-byte identical output file across multiple runs (`01-3-lua-conformance-test-matrix.md` requirement).

---

## 8. Diagnostic Contract

The pipeline stages map to deterministic classes of errors. The compiler MAY emit secondary diagnostics, but the primary diagnostic code for a given root failure MUST be stable across runs.

*   **Phase 1 (Parsing):** `LUA_PROFILE_PARSE_ERROR`, `LUA_PROFILE_UNSUPPORTED_FEATURE`, `LUA_PROFILE_FORBIDDEN_API`
*   **Phase 2 (Semantic):** `LUA_API_UNKNOWN_SYMBOL`, `LUA_API_ARITY_MISMATCH`, `LUA_API_ARG_TYPE_MISMATCH`, `LUA_API_ARG_DOMAIN_VIOLATION`, `LUA_API_CONTEXT_FORBIDDEN`, `LUA_API_UNBOUNDED_SELECTOR`, `LUA_API_MUTATION_BUDGET_EXCEEDED`
*   **Phase 3 (Lowering):** `IR_LOWERING_UNMAPPABLE_CONSTRUCT`, `IR_GUARD_UNSUPPORTED_PATTERN`, `IR_CROSS_CUTTING_DIRECTIVE_REQUIRED`
*   **Phase 4 (Binding):** `BINDING_UNRESOLVED_REFERENCE`, `BINDING_TYPE_CONFLICT`, `BINDING_TABLE_OVERFLOW`
*   **Phase 5 (Safety/Bounds):** `IR_INSTRUCTION_LIMIT_EXCEEDED`, `IR_REACTIVE_CASCADE_UNBOUNDED`, `IR_NEXT_TICK_DEFER_REQUIRED`, `IR_CANONICALIZATION_FAILURE`
*   **Phase 6 (Emission):** `GAME_IMAGE_SERIALIZATION_FAILURE`, `GAME_IMAGE_SIGNATURE_FAILURE`
