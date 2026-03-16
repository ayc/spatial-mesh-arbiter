# Client <-> Edge Message Contract

This document is the canonical wire-level contract for traffic between physical game clients and Edge Nodes.

Canonical ownership note:
- This document is canonical for wire schema, transport, ingress validation, sequencing, and immediate edge response behavior.
- Intent taxonomy and stable `intent_id` assignments are canonical in [Intent Taxonomy](02-intent-taxonomy.md).
- NPC runtime cadence/replication behavior is canonical in [NPC Runtime and Replication Contract](../1-architecture/02-npc-architecture.md).
- NPC documentation additions in this phase do not introduce required client->edge wire schema or intent ID changes.

It defines:
- transport and connection rules,
- client->edge message schemas,
- immediate edge responses and rejection semantics,
- sequencing, idempotency, and backpressure behavior,
- auth/bootstrap and resume flow.

This contract is **normative**. Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used in RFC-style.

---

## 1. Scope and Non-Goals

### In scope
- Single multiplexed WebSocket protocol between Client and Edge.
- Message schemas for `AUTH`, `SIMULATION`, `META`, and `CONTROL` lanes.
- Optional raw-device telemetry in `CONTROL` lane for analytics/anti-cheat/debug (non-authoritative).
- Immediate edge responses (`EdgeAck`, `EdgeReject`, `AuthResult`, `EdgeControlNotice`).
- Validation, ordering, deduplication, and retry behavior.

### Out of scope
- Arbiter internal envelopes (`MeshInternalEvent`, `InternalPreparedHit`, etc.).
- Full downstream simulation replication contract (`StateUpdate`, topology streaming).
- Meta-service internal RPC/event-bus schemas.

---

## 2. Transport Contract

1. Client and Edge MUST communicate over a **single WebSocket connection**.
2. WebSocket frames MUST be **binary**.
3. Text frames MUST be rejected with `EdgeReject { reason: InvalidSchema }`.
4. Maximum decompressed payload size per frame is **64 KiB**.
5. Edge MUST send transport heartbeat (`ping`) every **5 seconds**.
6. Client MUST treat no successful ping/pong or message activity for **15 seconds** as connection loss.
7. Reconnect SHOULD use jittered exponential backoff:
   - attempt 1 delay: 0.5-1.5s random,
   - exponential growth with jitter,
   - max delay cap: 10s.
8. Client MUST reuse this same socket for all lanes (`AUTH`, `SIMULATION`, `META`, `CONTROL`).

---

## 3. Envelope Model

### 3.1 Client Envelope (Client -> Edge)

```rust
enum ClientLane {
    AUTH,
    SIMULATION,
    META,
    CONTROL,
}

struct ClientEnvelope {
    protocol_version: u16,       // REQUIRED
    kind: ClientLane,            // REQUIRED
    session_ref: Option<String>, // REQUIRED for SIMULATION/META/CONTROL after auth success
    correlation_id: Option<UUID>,// Optional tracing key, echoed by edge when possible
    sent_at_ms: Option<u64>,     // Optional client wall-clock send timestamp
    payload: ClientPayload,      // REQUIRED lane-specific payload
}

enum ClientPayload {
    Auth(ClientAuthPayload),
    Simulation(SimulationInput),
    Meta(MetaRequestEnvelope),
    Control(ClientControlPayload),
}

enum ClientControlPayload {
    // Optional app-level ping; transport ping/pong remains authoritative for liveness.
    ClientPing { ping_nonce: u64 },
    Pong { ping_nonce: u64 },
    // Optional non-authoritative device telemetry.
    DeviceTelemetry(DeviceTelemetryEnvelope),
}

struct DeviceTelemetryEnvelope {
    sample_seq: u64,                 // REQUIRED, monotonic per session
    source: TelemetrySource,         // REQUIRED input source class
    samples: Vec<DeviceTelemetrySample>, // REQUIRED non-empty, max 32
}

enum TelemetrySource {
    Mouse,
    Keyboard,
    Gamepad,
    Touch,
}

struct DeviceTelemetrySample {
    dt_ms: u16,                  // REQUIRED time since previous sample in envelope
    mouse_dx: Option<i16>,       // Optional raw mouse delta x
    mouse_dy: Option<i16>,       // Optional raw mouse delta y
    raw_buttons_down: Option<u32>, // Optional raw button edges down
    raw_buttons_up: Option<u32>,   // Optional raw button edges up
    raw_key_mask: Option<u64>,     // Optional raw keyboard mask
}
```

Authoritative boundary rules for `ClientControlPayload::DeviceTelemetry`:
1. Telemetry MUST NOT trigger authoritative gameplay actions by itself.
2. Edge MUST treat telemetry as best-effort and MAY drop telemetry under load.
3. Edge MUST NOT reject or roll back valid `SIMULATION` intents because telemetry was dropped.

### 3.2 Edge Envelope (Edge -> Client)

```rust
enum EdgeLane {
    AUTH,
    SIMULATION,
    META,
    CONTROL,
}

struct EdgeEnvelope {
    protocol_version: u16,        // REQUIRED selected/active version
    kind: EdgeLane,               // REQUIRED
    correlation_id: Option<UUID>, // Echoed from request where available
    edge_node_id: u32,            // REQUIRED
    payload: EdgePayload,         // REQUIRED
}

enum EdgePayload {
    AuthResult(AuthResult),
    Ack(EdgeAck),
    Reject(EdgeReject),
    ControlNotice(EdgeControlNotice),
}
```

---

## 4. Authentication and Session Bootstrap

### 4.1 Messages

```rust
enum ClientAuthPayload {
    ClientHello(ClientHello),
    ResumeSession(ResumeSession),
    AuthRefresh(AuthRefresh),
}

struct ClientHello {
    auth_token: String,                // REQUIRED bearer token
    client_build: String,              // REQUIRED semantic build id
    platform: String,                  // REQUIRED (e.g. "windows", "mac", "ios")
    supported_protocol_versions: Vec<u16>, // REQUIRED non-empty
    client_nonce: u64,                 // REQUIRED anti-replay nonce
}

struct ResumeSession {
    session_ref: String,       // REQUIRED prior edge-issued session ref
    resume_token: String,      // REQUIRED resume credential
    last_input_seq: u64,       // REQUIRED highest sequence client believes was sent
    client_nonce: u64,         // REQUIRED anti-replay nonce
}

struct AuthRefresh {
    session_ref: String,       // REQUIRED
    refresh_token: String,     // REQUIRED
    client_nonce: u64,         // REQUIRED anti-replay nonce
}
```

### 4.2 Edge Auth Result

```rust
enum AuthStatus {
    Accepted,
    Rejected,
    RefreshRequired,
    ResumeRejected,
}

struct AuthResult {
    status: AuthStatus,            // REQUIRED
    session_ref: Option<String>,   // REQUIRED when Accepted
    character_id: Option<UUID>,    // REQUIRED when Accepted
    entity_id: Option<u64>,        // REQUIRED when Accepted and entity already mapped
    selected_protocol_version: u16,// REQUIRED
    reason: Option<RejectReason>,  // REQUIRED for Rejected/ResumeRejected/RefreshRequired
    message: Option<String>,       // Optional user-facing detail
}
```

### 4.3 Auth Invariants

1. Client MUST send `ClientHello` before non-auth lanes unless resuming with `ResumeSession`.
2. Edge MUST reject any non-auth message without established session as `Unauthenticated`.
3. Edge MUST bind session identity to validated token claims, never client-provided identity fields.
4. If token expires mid-session, Edge MUST emit `AuthResult { status: RefreshRequired }` or `EdgeControlNotice::AuthRefreshRequired`.
5. Replay-protection nonces MUST be monotonic per `(session_ref, lane=AUTH)`.

---

## 5. Simulation Lane Contract

The client sends **intent-only** simulation messages. The client MUST NOT send authoritative outcomes or mutate-only server payloads.

For runtime interface alignment with [Core Primitives](internal-mesh-types/01-core-primitives.md):

```rust
// Canonical wire alias used by edge ingress in runtime-facing docs/code.
type RawInput = SimulationInput;
```

### 5.1 Simulation Input Schema

```rust
struct SimulationInput {
    input_seq: u64,                    // REQUIRED, strictly increasing per session
    client_tick: u64,                  // REQUIRED, client simulation tick
    sent_at_ms: Option<u64>,           // Optional wall-clock timestamp
    movement: MovementIntent,          // REQUIRED (can be zero vector)
    aim: AimIntent,                    // REQUIRED
    buttons: ButtonIntent,             // REQUIRED edge/held states
    discrete_events: Option<Vec<SimulationDiscreteEvent>>, // Optional batched discrete intents
}

struct MovementIntent {
    // Normalized stick/keyboard intent in signed fixed range.
    // -32767..32767 per axis.
    axis_x: i16,
    axis_y: i16,
}

enum AimIntent {
    CursorWorld { x: i32, y: i32 }, // NetCoord-space world cursor
    Facing { yaw_millirad: i32 },   // Optional alternate for controller schemes
}

struct ButtonIntent {
    // Bitmasks: one bit per logical control.
    pressed_edges: u32, // transitions: up->down this frame
    released_edges: u32,// transitions: down->up this frame
    held_mask: u32,     // current held state mask
}
```

### 5.2 Discrete Event Schema

```rust
struct SimulationDiscreteEvent {
    client_event_id: UUID, // REQUIRED idempotency key, unique per event
    event: DiscreteIntent,
}

enum DiscreteIntent {
    TargetedAbility { target_id: u64, ability_id: u16 },
    GroundTargetedAbility { destination_x: i32, destination_y: i32, ability_id: u16 },
    SpawnProjectile { direction_x: i32, direction_y: i32, target_id: Option<u64>, spell_id: u16 },
    UseConsumable { item_id: u16 },
    Interact { target_entity: u64 },
}
```

### 5.3 Forbidden Client Payloads

Client simulation messages MUST NOT include any of:
- authoritative HP/resource/buff mutation claims,
- direct `ImpactEvent`,
- internal-only prepared-hit/proc payloads,
- arbiter-routing override fields.

Violations MUST be rejected with `InvalidIntent`.

### 5.4 Intent Catalog (Authoritative Gameplay)

The authoritative client contract is expressed as intent, not raw device streams:

| Intent category | Message shape | Authoritative for gameplay |
| :--- | :--- | :--- |
| Continuous control | `SimulationInput { movement, aim, buttons }` | Yes |
| Discrete action | `SimulationDiscreteEvent` | Yes |
| Meta action | `MetaRequestEnvelope` | Yes (for meta workflows) |
| Raw-device telemetry | `ClientControlPayload::DeviceTelemetry` | No |

For gameplay design language, statements like "I cast fireball" map to a discrete intent variant:
- `TargetedAbility` for lock-on cast,
- `GroundTargetedAbility` for AoE placement,
- `SpawnProjectile` for directional skillshots.

---

## 6. Sequencing, Deduplication, and Ordering

1. Edge MUST track `last_input_seq` per active session.
2. `input_seq` MUST be strictly increasing:
   - if `input_seq <= last_input_seq`, Edge MUST drop and emit `EdgeReject { reason: StaleSequence, retry: do-not-retry }`.
3. Sequence gaps (`input_seq > last_input_seq + 1`) MUST NOT force disconnect:
   - Edge MAY continue processing newest input.
4. Edge MUST deduplicate `SimulationDiscreteEvent` by `(session_ref, client_event_id)` for at least **10 seconds**.
5. Duplicate discrete events MUST NOT dispatch duplicate upstream proposals.
6. Under pressure, Edge MAY coalesce movement to latest-per-session while preserving discrete event ordering.
7. Movement has no per-input terminal simulation ack requirement from Arbiter; reconciliation occurs via downstream state updates.

---

## 7. Send Cadence and Backpressure

### 7.1 Recommended Client Cadence

| Lane | Cadence | Requirement |
| :--- | :--- | :--- |
| `SIMULATION` movement/aim/buttons | Adaptive 20-60Hz | Client SHOULD adapt based on motion/combat intensity and edge notices |
| `SIMULATION` discrete events | Immediate | Client MUST send immediately; MUST NOT wait for next cadence tick |
| `META` | On demand | Client sends per action, not heartbeat paced |
| `CONTROL` keepalive | 5s ping/pong | Client MUST respond to edge pings |
| `CONTROL` telemetry | 5-20Hz batched | Client SHOULD batch raw-device samples; Edge MAY drop without gameplay impact |

### 7.2 Backpressure Behavior

When edge is saturated:
- Edge MAY emit `EdgeControlNotice::Backpressure { suggested_hz }`.
- Client SHOULD reduce simulation cadence to `suggested_hz` (min floor 20Hz unless disconnected).
- Edge MAY coalesce movement inputs but MUST preserve discrete-event idempotency semantics.

---

## 8. Translation Map (Intent -> Mesh Proposal)

| Client Intent | Edge Translation | Upstream Payload |
| :--- | :--- | :--- |
| `MovementIntent + AimIntent` | Integrate and validate | `ActionPayload::Engine(EngineAction::Movement)` |
| `DiscreteIntent::TargetedAbility` | Validate range/cooldown rules, stamp epochs | `ActionPayload::Game(ArpgAction::TargetedAbility)` |
| `DiscreteIntent::GroundTargetedAbility` | Validate cast destination rules | `ActionPayload::Game(ArpgAction::GroundTargetedAbility)` |
| `DiscreteIntent::SpawnProjectile` | Validate spell profile | `ActionPayload::Game(ArpgAction::SpawnProjectile)` |
| `DiscreteIntent::UseConsumable` | Validate local/use constraints then meta/mesh path | `ActionPayload::Game(ArpgAction::UseConsumable)` |
| `DiscreteIntent::Interact` | Validate interactable target | `ActionPayload::Game(ArpgAction::Interact)` |

Internal-only payloads (e.g., prepared-hit/proc/impact relay) MUST NEVER be accepted from client ingress.

---

## 9. Meta Lane Contract

### 9.1 Meta Request Schema

```rust
struct MetaRequestEnvelope {
    request_id: UUID, // REQUIRED client-generated correlation/idempotency id
    request: MetaRequest,
}
```

The canonical `MetaRequest` enum (all variants, associated types, and supporting enums) is defined in [Edge Node Envelopes — §2.1](internal-mesh-types/02-edge-node-envelopes.md#21-interface). The client sends the same `MetaRequest` enum that the Edge Node receives — there is no translation or fan-out step. The Edge Node wraps the request in a `MetaRequestEnvelope` with the client-generated `request_id` and injects the trusted `character_id` before forwarding to Meta services.

### 9.2 Meta Lane Behavior

1. Edge MUST inject trusted identity (`character_id`) before forwarding to Meta services.
2. Edge MUST emit immediate `EdgeAck` for accepted forwarding or `EdgeReject` for local validation failure.
3. Simulation-lane rate limiting MUST NOT block valid meta-lane requests.
4. Invalid meta schema MUST reject with `InvalidSchema`.

---

## 10. Immediate Edge Response Types

### 10.1 EdgeAck

```rust
enum AckKind {
    AuthAccepted,
    SimulationAccepted,
    MetaAccepted,
}

struct EdgeAck {
    ack_kind: AckKind,             // REQUIRED
    session_ref: Option<String>,   // REQUIRED after auth
    input_seq: Option<u64>,        // Present for simulation acceptance
    request_id: Option<UUID>,      // Present for meta acceptance
}
```

`EdgeAck` means the envelope was accepted into the Edge ingress/forwarding pipeline. `EdgeAck` MUST NOT be interpreted as authoritative gameplay success (hit, damage application, cooldown commit, or state mutation completion).

### 10.2 EdgeReject

```rust
enum RetryPolicy {
    RetryNow,
    RetryLater,
    DoNotRetry,
}

enum RejectReason {
    Unauthenticated,
    SessionExpired,
    InvalidSchema,
    UnsupportedVersion,
    StaleSequence,
    RateLimited,
    PayloadTooLarge,
    InvalidIntent,
    ServerBusy,
}

struct EdgeReject {
    reason: RejectReason,         // REQUIRED
    retry: RetryPolicy,           // REQUIRED
    input_seq: Option<u64>,       // Present when reject is for simulation input
    request_id: Option<UUID>,     // Present when reject is for meta request
    message: Option<String>,      // Optional developer/user-facing detail
}
```

### 10.3 EdgeControlNotice

```rust
enum ControlNoticeType {
    Backpressure,
    AuthRefreshRequired,
    ReconnectAdvice,
    RateLimitWarning,
}

struct EdgeControlNotice {
    notice_type: ControlNoticeType, // REQUIRED
    suggested_hz: Option<u8>,       // For Backpressure
    reconnect_after_ms: Option<u32>,// For ReconnectAdvice
    scope: Option<String>,          // e.g. "simulation", "meta"
    message: Option<String>,
}
```

---

## 11. Error Model and Retry Semantics

| RejectReason | Meaning | Client behavior |
| :--- | :--- | :--- |
| `Unauthenticated` | No valid session context | Re-authenticate immediately (`RetryNow`) |
| `SessionExpired` | Session invalidated or timed out | Re-bootstrap (`RetryNow`) |
| `InvalidSchema` | Missing/invalid required fields or wrong types | Fix payload before retry (`DoNotRetry`) |
| `UnsupportedVersion` | No protocol version overlap | Upgrade/downgrade client (`DoNotRetry`) |
| `StaleSequence` | Duplicate or out-of-order old `input_seq` | Advance sequence and continue (`DoNotRetry`) |
| `RateLimited` | Per-session fairness gate exceeded | Back off and retry (`RetryLater`) |
| `PayloadTooLarge` | Envelope exceeds max size | Split/reduce payload (`DoNotRetry`) |
| `InvalidIntent` | Forbidden or impossible intent content | Correct payload (`DoNotRetry`) |
| `ServerBusy` | Temporary edge saturation | Retry with backoff (`RetryLater`) |

---

## 12. Security and Abuse Controls

Edge ingress validation order MUST be:
1. auth/session check,
2. schema/version check,
3. sequencing and dedup check,
4. lane-specific validation,
5. anti-cheat precheck,
6. dispatch.

Additional requirements:
- Per-session token bucket limits MUST be enforced on simulation ingress.
- Per-session rate limits SHOULD be applied to telemetry ingress separately from simulation fairness buckets.
- Session-bound identity MUST be server-derived; client identity claims are ignored.
- All rejects MUST be explicit for discrete actions; no silent dropping of discrete intents.
- Telemetry processing MUST NOT block simulation ingress processing.

---

## 13. Observability Contract

Edge MUST emit structured logs/traces for each accepted/rejected envelope with:
- `edge_node_id`,
- `session_id` (if established),
- `character_id` (if established),
- `protocol_version`,
- `kind`/lane,
- `correlation_id` (if present),
- `input_seq` (simulation),
- `client_event_id` (discrete event),
- `request_id` (meta),
- `sample_seq` (telemetry),
- `reject_reason` (if rejected).

---

## 14. Compatibility and Versioning

1. Client negotiates version via `ClientHello.supported_protocol_versions`.
2. Edge selects one version and returns `AuthResult.selected_protocol_version`.
3. If no overlap, Edge MUST reject with `UnsupportedVersion`.
4. Unknown optional fields SHOULD be ignored for forward compatibility.
5. Unknown required fields or malformed required fields MUST trigger `InvalidSchema`.
6. Version mismatch after session establishment MUST fail fast with `UnsupportedVersion`.

---

## 15. Worked Examples

Examples below are illustrative JSON-style payloads carried in binary frames.

### 15.1 Auth lane

Valid `ClientHello`:

```json
{
  "protocol_version": 3,
  "kind": "AUTH",
  "session_ref": null,
  "correlation_id": "f8a97a3f-4bd9-4d81-a22f-23be43b670c1",
  "payload": {
    "Auth": {
      "ClientHello": {
        "auth_token": "eyJhbGciOi...",
        "client_build": "1.2.7",
        "platform": "windows",
        "supported_protocol_versions": [2, 3],
        "client_nonce": 991771
      }
    }
  }
}
```

Invalid auth (unsupported version only):

```json
{
  "protocol_version": 99,
  "kind": "AUTH",
  "payload": {
    "Auth": {
      "ClientHello": {
        "auth_token": "eyJhbGciOi...",
        "client_build": "1.2.7",
        "platform": "windows",
        "supported_protocol_versions": [99],
        "client_nonce": 991772
      }
    }
  }
}
```

### 15.2 Simulation movement lane

Valid `SimulationInput`:

```json
{
  "protocol_version": 3,
  "kind": "SIMULATION",
  "session_ref": "sess_abc123",
  "payload": {
    "Simulation": {
      "input_seq": 1042,
      "client_tick": 550120,
      "movement": { "axis_x": 12000, "axis_y": -8000 },
      "aim": { "CursorWorld": { "x": 125400, "y": -9920 } },
      "buttons": { "pressed_edges": 1, "released_edges": 0, "held_mask": 1 }
    }
  }
}
```

Invalid movement (authoritative fields illegally included):

```json
{
  "protocol_version": 3,
  "kind": "SIMULATION",
  "session_ref": "sess_abc123",
  "payload": {
    "Simulation": {
      "input_seq": 1043,
      "client_tick": 550121,
      "movement": { "axis_x": 0, "axis_y": 0 },
      "aim": { "CursorWorld": { "x": 0, "y": 0 } },
      "buttons": { "pressed_edges": 0, "released_edges": 0, "held_mask": 0 },
      "hp": 999999
    }
  }
}
```

### 15.3 Simulation discrete action lane

Valid discrete cast:

```json
{
  "protocol_version": 3,
  "kind": "SIMULATION",
  "session_ref": "sess_abc123",
  "payload": {
    "Simulation": {
      "input_seq": 1044,
      "client_tick": 550122,
      "movement": { "axis_x": 0, "axis_y": 0 },
      "aim": { "CursorWorld": { "x": 126000, "y": -9400 } },
      "buttons": { "pressed_edges": 0, "released_edges": 0, "held_mask": 0 },
      "discrete_events": [
        {
          "client_event_id": "3f4810f2-45a4-47f2-b60d-57fbc5f58be4",
          "event": {
            "TargetedAbility": { "target_id": 88442211, "ability_id": 203 }
          }
        }
      ]
    }
  }
}
```

Invalid discrete action (internal-only intent):

```json
{
  "protocol_version": 3,
  "kind": "SIMULATION",
  "session_ref": "sess_abc123",
  "payload": {
    "Simulation": {
      "input_seq": 1045,
      "client_tick": 550123,
      "movement": { "axis_x": 0, "axis_y": 0 },
      "aim": { "CursorWorld": { "x": 0, "y": 0 } },
      "buttons": { "pressed_edges": 0, "released_edges": 0, "held_mask": 0 },
      "discrete_events": [
        {
          "client_event_id": "df579539-0d7a-4796-b333-31ec6dc85fc8",
          "event": {
            "InternalPreparedHit": { "target_id": 1, "context": {} }
          }
        }
      ]
    }
  }
}
```

### 15.4 Meta lane

Valid meta request:

```json
{
  "protocol_version": 3,
  "kind": "META",
  "session_ref": "sess_abc123",
  "payload": {
    "Meta": {
      "request_id": "9207c868-b4ab-4ca6-a6ef-48af4d7aa995",
      "request": {
        "SendChatMessage": { "channel": "party", "text": "stack on me" }
      }
    }
  }
}
```

Invalid meta request (missing required `request_id`):

```json
{
  "protocol_version": 3,
  "kind": "META",
  "session_ref": "sess_abc123",
  "payload": {
    "Meta": {
      "request": {
        "MoveInventoryItem": { "from_slot": 2, "to_slot": 18 }
      }
    }
  }
}
```

### 15.5 Edge reject example

```json
{
  "protocol_version": 3,
  "kind": "SIMULATION",
  "edge_node_id": 17,
  "correlation_id": "f8a97a3f-4bd9-4d81-a22f-23be43b670c1",
  "payload": {
    "Reject": {
      "reason": "StaleSequence",
      "retry": "DoNotRetry",
      "input_seq": 1042,
      "message": "input_seq already processed"
    }
  }
}
```

### 15.6 Control telemetry lane

Valid telemetry batch (non-authoritative):

```json
{
  "protocol_version": 3,
  "kind": "CONTROL",
  "session_ref": "sess_abc123",
  "payload": {
    "Control": {
      "DeviceTelemetry": {
        "sample_seq": 7001,
        "source": "Mouse",
        "samples": [
          { "dt_ms": 8, "mouse_dx": 2, "mouse_dy": -1, "raw_buttons_down": 1, "raw_buttons_up": 0 },
          { "dt_ms": 8, "mouse_dx": 1, "mouse_dy": 0, "raw_buttons_down": 0, "raw_buttons_up": 0 }
        ]
      }
    }
  }
}
```

Invalid telemetry batch (empty `samples`):

```json
{
  "protocol_version": 3,
  "kind": "CONTROL",
  "session_ref": "sess_abc123",
  "payload": {
    "Control": {
      "DeviceTelemetry": {
        "sample_seq": 7002,
        "source": "Mouse",
        "samples": []
      }
    }
  }
}
```

---

## 16. Protocol Conformance Checklist

1. Duplicate `input_seq` arrives -> edge drops and emits deterministic stale-sequence reject.
2. Out-of-order old sequence after newer acceptance -> deterministic stale handling.
3. Burst traffic over limits -> movement coalesced, discrete rejected with explicit reason.
4. Invalid simulation payload attempts internal-only semantics -> rejected with `InvalidIntent`.
5. Expired token mid-session -> refresh-required flow and retry behavior is deterministic.
6. Resume with stale/invalid session -> deterministic resume rejection and full bootstrap fallback.
7. Valid meta request while simulation lane is rate-limited -> meta lane remains available.
8. Protocol version mismatch -> fail-fast `UnsupportedVersion`.
9. Telemetry dropped under pressure -> simulation and discrete intents continue unaffected.

---

## 17. Cross-References

- Runtime edge/arbiter interfaces: [Core Primitives](internal-mesh-types/01-core-primitives.md)
- Architecture and trust boundaries: [Core Concepts and Mesh](../1-architecture/01-core-concepts-and-mesh.md)
- Ability/action semantics referenced by translation map: [Ability Framework](../3-gameplay-systems/02-ability-framework.md)
