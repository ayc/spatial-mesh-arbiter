# Spatial Messaging Plane

This document is normative for messaging behavior across edge, runtime, and control-plane boundaries.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

Canonical numeric defaults referenced in this document are defined in `00-1-core-baseline-profile.md`.

## 1. Purpose

The messaging plane transports intents, internal events, control directives, and authoritative outcomes while preserving:
1. single-writer authority semantics
2. deterministic ordering behavior
3. idempotent replay safety
4. bounded failure behavior under load

## 2. Message Classes

1. **External Intent**: actor-originated requests entering authoritative runtime.
2. **Internal Event**: runtime-to-runtime relay for cross-boundary interactions.
3. **Control Command**: controller/runtime lifecycle, topology, and synchronization directives.
4. **Authoritative Outcome**: terminal accept/reject and authoritative state notifications.

## 3. Envelope Contract

### 3.1 Common Required Fields

All mutation-capable envelopes MUST include:
1. `wire_schema_version` (unknown versions are rejected at ingress).
2. Unique envelope idempotency identity (`proposal_id`, `event_id`, or command id).
3. Source identity.
4. Ordering anchor (`origin_tick` or equivalent monotonic anchor).
5. `topology_epoch` where topology-sensitive routing applies.
6. `data_epoch` where balance/config-sensitive resolution applies.
7. Payload type identifier.
8. `auth_subject`.
9. `auth_issued_at_ms`.
10. `auth_expires_at_ms`.
11. `auth_nonce`.
12. `auth_signature` and `auth_key_id`.

### 3.2 Class-Specific Correlation Keys

1. External Intent: correlated by `proposal_id`.
2. Internal Event: correlated by `event_id`; effect-level dedupe MAY require domain keys (for example `(impact_id, target_id)`).
3. Control Command: correlated by deterministic command/event id for retry-safe execution.
4. Authoritative Outcome: correlated to originating intent/event key (for example `proposal_id` or adapter-level `action_id`).

## 4. Routing and Propagation Rules

1. External intents MUST route to one authoritative host for the actor at evaluation time.
2. Internal relay rebroadcast MUST be bounded by explicit protocol (default one-hop `TTL=1` behavior for overlap relay).
3. Relayed peers MUST NOT emit terminal client outcomes for the original external intent.
4. Only the actor-owner runtime node MAY emit terminal intent outcomes.
5. Cross-boundary target-locked interactions MUST use actor-owner pre-roll plus target-owner mutation to prevent split-brain outcomes.

## 5. Ordering and Epoch Handshake

### 5.1 Topology Epoch Rules

1. `proposal.topology_epoch == local.topology_epoch`: process normally.
2. `proposal.topology_epoch < local.topology_epoch`: forward surrogate-style to current owner.
3. `proposal.topology_epoch > local.topology_epoch`: buffer until topology update arrives, under bounded timeout.

### 5.2 Data Epoch Rules

1. `proposal.data_epoch == local.data_epoch`: process normally.
2. `proposal.data_epoch < local.data_epoch`: reject non-continuous proposal deterministically (`Data Epoch Mismatch` class).
3. `proposal.data_epoch > local.data_epoch`: attempt activation; if unavailable, buffer with bounded timeout, then fail deterministically (`Data Epoch Sync Timeout` class).

### 5.3 Bounded Timeout Rule

The bounded wait horizon for stale topology/data synchronization MUST be finite and deterministic.

Baseline profile default:
1. `max_event_age_ticks` (see baseline profile).
2. On timeout, non-continuous intents MUST receive explicit terminal reject.

### 5.4 Saturation Rule

If stale-buffer capacity is exhausted:
1. non-continuous intents MUST be explicitly rejected (`Queue Saturated` class)
2. continuous movement intents MAY be coalesced/dropped and reconciled by snapshots
3. silent drop of non-continuous intents is non-compliant

## 6. Outcome Semantics

1. Every non-continuous external intent MUST terminate with exactly one terminal outcome (`accept` or `reject`).
2. Terminal outcomes MUST be idempotent by intent key.
3. Continuous movement intents MAY omit per-intent terminal outcomes and reconcile via authoritative snapshots.
4. For border-targeted intents, terminal `accept` means accepted/forwarded under local authority, not guaranteed remote damage commit.
5. Outcome error payloads SHOULD expose a stable machine code set even if human-readable strings vary by adapter/runtime.

Recommended baseline reject-code classes:
1. `RATE_LIMITED`
2. `QUEUE_SATURATED`
3. `OUT_OF_RANGE`
4. `INVALID_TARGET`
5. `DATA_EPOCH_MISMATCH`
6. `DATA_EPOCH_SYNC_TIMEOUT`
7. `TOPOLOGY_SYNC_TIMEOUT`
8. `INVALID_PAYLOAD_TYPE`
9. `AUTH_INVALID`
10. `AUTH_EXPIRED`
11. `AUTH_REPLAYED`
12. `AUTH_FORBIDDEN`

## 7. Idempotency and Replay

1. Duplicate delivery MUST be safe for all mutation-capable messages.
2. Replay older than retention horizon MUST be dropped deterministically.
3. Dedup memory MUST be bounded by explicit capacity, not unbounded hash growth.
4. Overflow of dedupe capacity MUST fail closed for mutation safety and increment observable counters.

Baseline profile defaults:
1. `max_event_age_ticks`
2. `idempotency_bucket_capacity`
3. Effective key budget approximation:
`max_idempotency_keys ~= max_event_age_ticks * idempotency_bucket_capacity`

## 8. Ingress Fairness and Queue Bounds

Runtime ingress MUST enforce per-entity fairness before shared queue admission.

Baseline profile defaults:
1. `proposal_bucket_capacity`
2. `proposal_bucket_refill_per_tick`
3. `movement_cost`
4. `discrete_cost`
5. `external_inbox_cap`
6. `internal_inbox_cap`
7. `stale_buffer_cap`

Behavior requirements:
1. Over-budget non-continuous intents MUST reject explicitly.
2. Over-budget movement intents MAY drop/coalesce.
3. One abusive entity/session MUST NOT be able to starve global queue capacity.

## 9. Control-Plane Messaging Requirements

1. Control commit commands MUST be retry-safe and idempotent.
2. Runtime behavior under temporary controller outage MUST remain deterministic (frozen topology, continued simulation).
3. Controller-unavailable escalations for controller-routed effects MUST fail closed with explicit reject/refund behavior.
4. Control synchronization heartbeats MAY be low-frequency and best-effort, but correction behavior MUST remain bounded and monotonic.

## 10. Observability Requirements

Implementations MUST emit metrics/events for at least:
1. terminal outcomes by class and reject code
2. stale-buffer depth and saturation rejects
3. token-bucket rejects
4. epoch mismatch/timeouts
5. dedupe insert results (`inserted`, `duplicate`, `overflow`)
6. replay drops beyond horizon
7. wire-schema rejects
8. surrogate forwards due to stale topology
9. auth signature validation failures
10. auth freshness/expiry rejects
11. auth nonce replay rejects

## 11. Conformance Checks

A messaging-plane implementation is conformant only if it passes:
1. exactly-one terminal outcome checks for non-continuous intents
2. duplicate delivery idempotency tests
3. stale epoch buffering/timeout behavior checks
4. queue saturation explicit-reject checks
5. replay horizon drop checks
6. dedupe overflow fail-closed checks
7. per-entity fairness isolation checks
8. signature/integrity validation checks at trust boundaries
9. freshness-window expiry/skew checks
10. nonce replay rejection checks
11. numeric payload normalization checks for mutation-capable envelopes

## 12. Trust and Security Boundary Contract

### 12.1 Trust Tiers

1. External clients are untrusted and MUST NOT directly mutate authoritative runtime state.
2. Edge-to-runtime and runtime-to-runtime links are privileged mesh boundaries and MUST use mutual authentication.
3. Control-plane senders are privileged but MUST still satisfy message integrity and freshness checks.

### 12.2 Integrity and Source Validation

1. Ingress MUST verify `auth_signature` using `auth_key_id` before mutation admission.
2. Failed signature validation MUST fail closed and return deterministic reject (`AUTH_INVALID`).
3. Source role authorization MUST be explicit per message class (external intent, internal event, control command, outcome).
4. Unauthorized class/source combinations MUST fail closed (`AUTH_FORBIDDEN`).

### 12.3 Freshness and Replay Protection

Canonical bounds are defined in `00-1-core-baseline-profile.md`:
1. `auth_clock_skew_tolerance_ms`
2. `external_intent_ttl_ms`
3. `internal_event_ttl_ms`
4. `control_command_ttl_ms`
5. `auth_nonce_horizon_ms`

Required behavior:
1. `auth_issued_at_ms` and `auth_expires_at_ms` MUST be validated against local time with bounded skew tolerance.
2. Expired envelopes MUST fail closed (`AUTH_EXPIRED`).
3. `auth_nonce` replay within the configured nonce horizon MUST fail closed (`AUTH_REPLAYED`).
4. Nonce replay tracking MUST be bounded and observable.

## 13. Numeric Payload Normalization

1. Numeric payload fields that influence authoritative mutation MUST declare explicit scale semantics in schema.
2. If ingress accepts floating-point numeric fields, ingress normalization MUST apply the kernel canonical conversion rule from `01-spatial-runtime-kernel.md`.
3. `NaN`, `Inf`, and out-of-guardrail converted values MUST be rejected deterministically before mutation admission.
4. Equivalent numeric inputs MUST normalize to one canonical integer/fixed representation for replay equivalence.
