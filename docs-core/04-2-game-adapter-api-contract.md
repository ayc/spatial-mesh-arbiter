# Game Adapter API Contract (Normative)

This document defines strict API and startup negotiation requirements for
the engine/game adapter boundary.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope and Precedence

1. `05-conformance-invariants.md` defines global invariants.
2. `04-1-game-adapter-contract.md` defines adapter behavior constraints.
3. This document defines strict API shapes and compatibility negotiation.
4. `04-3-version-line-transition-contract.md` defines rollout/rollback behavior between valid lines.
5. `04-0-game-adapter-interface.md` is conceptual and explanatory.

If there is a conflict, higher-precedence documents win.

## 2. Canonical Hook Names

The engine-facing adapter API is fixed to these hook identifiers:
1. `validate_intent`
2. `resolve_external`
3. `resolve_internal`
4. `build_spawn`
5. `describe_compatibility`

Engine integration MUST NOT require any additional mandatory hook names.

## 3. Call Envelope Contract

### 3.1 Request Envelope

Every hook call MUST carry this request envelope:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `call_id` | string | yes | unique per invocation |
| `hook_name` | enum | yes | one of section 2 values |
| `tick` | u64 | yes | authoritative tick anchor |
| `topology_epoch` | u64 | yes | topology context |
| `data_epoch` | u64 | yes | content/config context |
| `deadline_us` | u32 | yes | hard call deadline from engine |
| `subject_entity_id` | string or null | yes | actor/entity scope when applicable |
| `payload` | object | yes | hook-specific payload |
| `wire_schema_version` | u32 | yes | payload-wire schema version |

### 3.2 Response Envelope

Every hook call MUST return this response envelope:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `call_id` | string | yes | must match request |
| `hook_name` | enum | yes | must match request |
| `status` | enum | yes | `OK`, `REJECT`, `FAULT`, `TIMEOUT` |
| `mutations` | array | yes | empty allowed |
| `emitted_events` | array | yes | empty allowed |
| `terminal_outcome` | object or null | yes | required for discrete intents in resolution hooks |
| `reject_code` | string or null | yes | required when `status=REJECT` |
| `fault_code` | string or null | yes | required when `status=FAULT` or `status=TIMEOUT` |

Response rules:
1. `status=OK` MUST NOT include `reject_code` or `fault_code`.
2. `status=REJECT` MUST include deterministic `reject_code` and MUST NOT include mutations.
3. `status=FAULT` or `status=TIMEOUT` MUST fail closed (no mutation side effects).
4. Envelope fields and ordering used for digest/replay MUST be deterministic.

### 3.3 Hook-Specific Constraints

| Hook | Required Input Payload Class | Allowed Status Values | Mutation Allowed |
| --- | --- | --- | --- |
| `validate_intent` | external intent envelope + actor snapshot | `OK`, `REJECT`, `FAULT`, `TIMEOUT` | no |
| `resolve_external` | validated external intent + authoritative view | `OK`, `REJECT`, `FAULT`, `TIMEOUT` | yes |
| `resolve_internal` | internal event envelope + authoritative view | `OK`, `REJECT`, `FAULT`, `TIMEOUT` | yes |
| `build_spawn` | spawn request + baseline state context | `OK`, `REJECT`, `FAULT`, `TIMEOUT` | yes |
| `describe_compatibility` | empty payload | `OK`, `FAULT`, `TIMEOUT` | no |

## 4. Enum and Extension Rules

1. `hook_name` and `status` are closed enums; unknown values are non-conformant.
2. `reject_code` values MAY include game-defined codes, but game-defined codes MUST use `GAME_` prefix.
3. Engine-defined boundary/fault codes MUST remain stable across adapter upgrades.
4. Unknown required fields in request or response envelopes MUST fail validation.

## 5. Startup Compatibility Negotiation

Startup admission MUST execute this deterministic handshake:
1. `ENGINE_HELLO`
2. `ADAPTER_HELLO`
3. `ADMISSION_DECISION`

### 5.1 `ENGINE_HELLO` Required Fields

1. `engine_identity`
2. `engine_version_semver`
3. `supported_adapter_api_majors` (non-empty set)
4. `supported_wire_schema_versions` (non-empty set)
5. `deployment_adapter_identity` (expected adapter identity for mesh)

### 5.2 `ADAPTER_HELLO` Required Fields

1. `adapter_identity`
2. `adapter_version_semver`
3. `adapter_api_major`
4. `supported_wire_schema_versions` (non-empty set)
5. `payload_schema_descriptors` where each descriptor contains:
   - `payload_type_id`
   - `schema_version`
   - `compatibility_mode` (`BACKWARD`, `FORWARD`, or `BIDIRECTIONAL`)

### 5.3 Admission Rules

1. `adapter_identity` MUST equal `deployment_adapter_identity`.
2. `adapter_api_major` MUST be in `supported_adapter_api_majors`.
3. `supported_wire_schema_versions` intersection MUST be non-empty.
4. Negotiated wire schema version MUST be deterministic (highest common numeric version).
5. If any required check fails, node admission MUST fail before runtime authority assignment.

### 5.4 Deterministic Negotiation Failure Codes

1. `ADAPTER_IDENTITY_MISMATCH`
2. `ADAPTER_API_MAJOR_UNSUPPORTED`
3. `WIRE_SCHEMA_NO_INTERSECTION`
4. `PAYLOAD_SCHEMA_DESCRIPTOR_INVALID`
5. `NEGOTIATION_TIMEOUT`
6. `MESH_VERSION_LINE_CONFLICT`

## 6. Mesh Version-Line Policy

1. A runtime mesh MUST contain exactly one adapter identity/version line.
2. Nodes presenting a different adapter identity or version line MUST be rejected from authority duties.
3. Mixed-version operation inside one active authority mesh is non-conformant.
4. Version-line transitions MUST follow `04-3-version-line-transition-contract.md`.
5. Upgrade strategy MUST ensure deterministic authority continuity (for example by generation cutover or drained replacement policy).

## 7. Conformance Requirements

A boundary implementation is conformant only if it passes:
1. request/response schema validation tests for all hooks
2. enum closed-set validation tests
3. success and failure startup negotiation tests
4. mixed-version-line rejection tests
5. replay/idempotency tests proving duplicate invocation does not mint duplicate mutation side effects
6. transition-admission integration tests proving only valid version lines enter authority duties
