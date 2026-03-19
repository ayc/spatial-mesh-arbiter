# Conformance Test Matrix (Normative)

This document defines concrete verification criteria for `05-conformance-invariants.md`.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

Canonical numeric defaults referenced here are defined in `00-1-core-baseline-profile.md`.

## 1. Scope and Precedence

1. `05-conformance-invariants.md` defines what must always be true.
2. This document defines how those truths are verified and passed.
3. `05-2-core-conformance-scenario-catalog.md` defines canonical scenario IDs and required host classes.

If there is a conflict, invariants and baseline profile keys take precedence.

## 2. Conformance Gate Policy

A build is conformant only if all required tests for the target gate pass.

Gate levels:
1. `PR`: merge gate for runtime/control/adapter changes.
2. `NIGHTLY`: full matrix execution.
3. `RELEASE`: nightly matrix plus cross-host determinism and upgrade checks.

## 3. Required Evidence Artifacts

For each executed test, harnesses MUST emit:
1. test id and git revision
2. pass/fail verdict
3. key metrics used for verdict
4. failure reason classification
5. timestamp and environment metadata

## 4. Matrix

| Test ID | Invariant Group | Scenario Source | Pass Criteria | Required Gate |
| --- | --- | --- | --- | --- |
| `AUTH-01` | Authority | `SCN-AUTH-UNIQUE-WRITER` | For every `(entity_id, tick)`, exactly one authoritative writer; zero dual-writer records. | `PR`, `NIGHTLY`, `RELEASE` |
| `AUTH-02` | Authority | `SCN-AUTH-CUTOVER-TICK` | Ownership cutover happens exactly at commanded cutover tick; no pre-cutover target-owner mutation. | `PR`, `NIGHTLY`, `RELEASE` |
| `AUTH-03` | Authority | `SCN-AUTH-AMBIG-HANDOFF-FAILCLOSED` | Ambiguous handoff windows resolve fail-closed; zero dual-simulation traces. | `NIGHTLY`, `RELEASE` |
| `DET-01` | Determinism | `SCN-DET-MONOTONIC-TICK` | `current_tick` is strictly monotonic (no backward steps). | `PR`, `NIGHTLY`, `RELEASE` |
| `DET-02` | Determinism | `SCN-DET-REPLAY-DIGEST` | Deterministic replay digest for same input log matches reference digest exactly. | `PR`, `NIGHTLY`, `RELEASE` |
| `DET-03` | Determinism | `SCN-DET-CROSS-HOST-DIGEST` | Same replay digest on every required host class listed in `05-2-core-conformance-scenario-catalog.md` section 2. | `RELEASE` |
| `DET-04` | Determinism | `SCN-DET-CONTENTION-STABILITY` | Contended interaction winner/loser outcome is stable across retries/replays. | `NIGHTLY`, `RELEASE` |
| `DET-05` | Determinism | `SCN-DET-NUMERIC-CANONICALIZATION` | Equivalent numeric inputs (including float ingress variants) normalize to identical canonical fixed/integer values and replay digests. | `NIGHTLY`, `RELEASE` |
| `DET-06` | Determinism | `SCN-DET-NUMERIC-OVERFLOW-FAILCLOSED` | `NaN`, `Inf`, and overflow conversion/arithmetic cases produce deterministic reject/fault with zero mutation side effects. | `PR`, `NIGHTLY`, `RELEASE` |
| `MSG-01` | Messaging | `SCN-MSG-EXACTLY-ONE-TERMINAL` | Every non-continuous intent terminates with exactly one terminal outcome. | `PR`, `NIGHTLY`, `RELEASE` |
| `MSG-02` | Messaging | `SCN-MSG-DUPLICATE-SAFE` | Duplicate deliveries do not create duplicate mutation side effects. | `PR`, `NIGHTLY`, `RELEASE` |
| `MSG-03` | Messaging | `SCN-MSG-STALE-TIMEOUT` | Stale epoch buffering timeout never exceeds `stale_sync_timeout_ticks`; timeout path is explicit reject. | `PR`, `NIGHTLY`, `RELEASE` |
| `MSG-04` | Messaging | `SCN-MSG-SATURATION-EXPLICIT-REJECT` | Under queue pressure, non-continuous intents are never silently dropped; rejects are explicit. | `PR`, `NIGHTLY`, `RELEASE` |
| `MSG-05` | Messaging | `SCN-MSG-SCHEMA-REJECT` | Unknown `wire_schema_version` packets are rejected at ingress with no mutation side effects. | `NIGHTLY`, `RELEASE` |
| `SAF-01` | Runtime Safety | `SCN-SAF-NO-BLOCKING-IO` | Zero blocking I/O calls observed on authoritative tick thread. | `PR`, `NIGHTLY`, `RELEASE` |
| `SAF-02` | Runtime Safety | `SCN-SAF-QUEUE-BOUNDS` | Queue lengths never exceed configured caps (`external_inbox_cap`, `internal_inbox_cap`, `stale_buffer_cap`). | `PR`, `NIGHTLY`, `RELEASE` |
| `SAF-03` | Runtime Safety | `SCN-SAF-DEDUPE-OVERFLOW-FAILCLOSED` | Dedupe overflow follows fail-closed path and increments overflow metrics. | `NIGHTLY`, `RELEASE` |
| `SAF-04` | Runtime Safety | `SCN-SAF-FAIRNESS-ISOLATION` | Over `fairness_observation_window_ticks`, `unrelated_accept_rate_abuse >= unrelated_accept_rate_control * (1 - fairness_isolation_max_degradation_pct / 100)`. | `NIGHTLY`, `RELEASE` |
| `DUR-01` | Durability | `SCN-DUR-COMMIT-AFTER-DURABLE` | Consumer offset commit occurs only after durable side-effect commit. | `PR`, `NIGHTLY`, `RELEASE` |
| `DUR-02` | Durability | `SCN-DUR-TX-STATE-GRAPH` | Transaction transitions obey allowed state graph: `PENDING -> CONFIRMED` or `PENDING -> COMPENSATING -> COMPENSATED`. | `PR`, `NIGHTLY`, `RELEASE` |
| `DUR-03` | Durability | `SCN-DUR-LATE-ACK-DROP` | Ack after timeout/compensation does not reopen success path; `late_ack_dropped` signal emitted. | `NIGHTLY`, `RELEASE` |
| `DUR-04` | Durability | `SCN-DUR-DUPLICATE-COMMAND` | Same `command_id` causes at most one authoritative mutation attempt. | `PR`, `NIGHTLY`, `RELEASE` |
| `DUR-05` | Durability | `SCN-DUR-RETRY-DLQ` | After `durable_consumer_retry_max_attempts`, record is sent to DLQ with required source metadata. | `NIGHTLY`, `RELEASE` |
| `BND-01` | Game Boundary | `SCN-BND-ENGINE-GAME-IMPORT-SCAN` | Engine module set contains no game-template economy/progression/social dependency imports. | `PR`, `NIGHTLY`, `RELEASE` |
| `BND-02` | Game Boundary | `SCN-BND-ADAPTER-MUTATION-CONTAINMENT` | Adapter can mutate only through returned outcomes; direct engine-state mutation path is absent/denied. | `PR`, `NIGHTLY`, `RELEASE` |
| `BND-03` | Game Boundary | `SCN-BND-SINGLE-ADAPTER-LINE` | Runtime mesh presents exactly one adapter identity/version line. | `RELEASE` |
| `BND-04` | Game Boundary | `SCN-BND-NEGOTIATION-HANDSHAKE` | Startup admission accepts only valid compatibility intersections and emits deterministic failure codes on invalid intersections. | `PR`, `NIGHTLY`, `RELEASE` |
| `BND-05` | Game Boundary | `SCN-BND-MIXED-VERSION-REJECT` | Nodes with conflicting adapter identity/version line are rejected from authority responsibilities. | `NIGHTLY`, `RELEASE` |
| `BND-06` | Game Boundary | `SCN-BND-VERSION-TRANSITION-COMMIT` | `prepare_duration_ms <= version_transition_prepare_timeout_ms`, `drain_duration_ms <= version_transition_drain_timeout_ms`, `stabilize_duration_ticks >= version_transition_commit_stabilization_ticks`, `authoritative_version_line_count == 1` for every tick in transition generation, and observed non-continuous reject rate over `version_transition_reject_observation_window_ticks` is `<= version_transition_max_non_continuous_reject_rate_pct`. | `NIGHTLY`, `RELEASE` |
| `BND-07` | Game Boundary | `SCN-BND-VERSION-TRANSITION-ROLLBACK` | Failed transition rolls back to source version line within `version_transition_rollback_timeout_ms` with no duplicate durable outcomes. | `NIGHTLY`, `RELEASE` |
| `API-01` | Adapter API v2 | `SCN-API-STAGE-ID-CLOSED-SET` | `dispatch_stage` called with StageId values 0, 2, or 13+ MUST be rejected by the adapter with `FAULT` status. Only values in the normative StageId enum (1, 3-12) are accepted. | `PR`, `NIGHTLY`, `RELEASE` |
| `API-02` | Adapter API v2 | `SCN-API-STAGE-ORDER-MONOTONIC` | Within a single tick, `dispatch_stage` calls MUST arrive in strictly ascending StageId order. Out-of-order invocation MUST be detectable and emit a fault signal. | `PR`, `NIGHTLY`, `RELEASE` |
| `API-03` | Adapter API v2 | `SCN-API-STAGE1-ROUTING-COMMIT` | Stage 1 (`ControlAuthorityAndInputRouting`) routing decisions returned by the adapter MUST be committed by the engine before Stage 2 (`validate_intent`) executes. Intents validated in Stage 2 MUST use the routed control assignments from Stage 1. | `NIGHTLY`, `RELEASE` |
| `API-04` | Adapter API v2 | `SCN-API-STAGE9-DEFER-REQUIRED` | Combat events generated by Stage 9 (`PostDamage`) hooks MUST appear in the `deferred_events` field of `stage_outcome`, not in `emitted_events`. Events in `emitted_events` from Stage 9 MUST cause a conformance failure. | `PR`, `NIGHTLY`, `RELEASE` |
| `API-05` | Adapter API v2 | `SCN-API-STAGE11-DEFER-REQUIRED` | Timer payloads fired during Stage 11 (`StateUpdate`) MUST appear in `deferred_events`. Same enforcement as API-04. | `PR`, `NIGHTLY`, `RELEASE` |
| `API-06` | Adapter API v2 | `SCN-API-SPAWN-CONFIG-SCHEMA` | `initialize_spawn_configuration` response MUST include a `spawn_configuration` with required fields: `initial_entity_state` (valid entity snapshot), `ghost_movement_replication_cadence` (valid `GhostMovementReplicationCadence` enum, 0-3), `lifetime_ticks` (positive or null). The response MUST NOT contain `entity_id` (engine-owned, provided in the request). Missing or malformed fields MUST cause a deterministic spawn-time reject/fault and a conformance failure. | `PR`, `NIGHTLY`, `RELEASE` |
| `API-07` | Adapter API v2 | `SCN-API-DISPATCH-BATCH-DETERMINISM` | For identical `DispatchStageRequest` inputs, the adapter MUST return identical `stage_outcome` outputs. Verified by replaying the same stage context twice and comparing result digests. | `NIGHTLY`, `RELEASE` |
| `API-08` | Adapter API v2 | `SCN-API-VALIDATE-INTENT-TERMINAL` | Every non-continuous intent processed through `validate_intent` MUST terminate with exactly one `terminal_outcome` (accept or reject). Missing terminal outcome MUST cause a conformance failure. | `PR`, `NIGHTLY`, `RELEASE` |
| `SEC-01` | Security and Trust | `SCN-SEC-EXTERNAL-SIGNATURE` | Missing or invalid external signature is rejected fail closed (`AUTH_INVALID`) with zero mutation side effects. | `PR`, `NIGHTLY`, `RELEASE` |
| `SEC-02` | Security and Trust | `SCN-SEC-FRESHNESS-WINDOW` | Expired or skew-invalid envelope is rejected (`AUTH_EXPIRED`) using configured freshness bounds. | `PR`, `NIGHTLY`, `RELEASE` |
| `SEC-03` | Security and Trust | `SCN-SEC-NONCE-REPLAY` | Replayed `auth_nonce` within nonce horizon is rejected (`AUTH_REPLAYED`) with zero mutation side effects. | `NIGHTLY`, `RELEASE` |
| `SEC-04` | Security and Trust | `SCN-SEC-ROLE-AUTHZ` | Unauthorized source role/message-class combinations are rejected (`AUTH_FORBIDDEN`) with zero mutation side effects. | `PR`, `NIGHTLY`, `RELEASE` |

## 5. Quantitative Verdict Rules

### 5.1 Messaging and Runtime Bounds

1. Stale buffering timeout verdict uses `stale_sync_timeout_ticks`.
2. Replay horizon verdict uses `max_event_age_ticks`.
3. Queue-bound verdict uses `external_inbox_cap`, `internal_inbox_cap`, `stale_buffer_cap`.
4. Fairness verdict uses `proposal_bucket_capacity`, `proposal_bucket_refill_per_tick`, `movement_cost`, `discrete_cost`.
5. Fairness-isolation verdict uses `fairness_observation_window_ticks` and `fairness_isolation_max_degradation_pct`.

### 5.2 Adapter, Durability, and Transition Bounds

1. Adapter overrun verdict uses `adapter_tick_budget_us`, `hot_hook_timeout_us`, `spawn_hook_timeout_us`.
2. Adapter containment verdict uses `adapter_fault_window_ticks`, `adapter_fault_threshold`, `adapter_degraded_hold_ticks`.
3. Reconciliation timeout verdict uses `tx_pending_timeout_ms` and `tx_reconcile_scan_interval_ms`.
4. Dedupe-horizon verdict uses `runtime_command_dedupe_horizon_ms`.
5. Retry-to-DLQ verdict uses `durable_consumer_retry_max_attempts`, `durable_consumer_retry_backoff_initial_ms`, `durable_consumer_retry_backoff_max_ms`.
6. Transition phase bounds verdict uses `version_transition_prepare_timeout_ms`, `version_transition_drain_timeout_ms`, `version_transition_commit_stabilization_ticks`, `version_transition_rollback_timeout_ms`.
7. Transition reject-rate verdict uses `version_transition_reject_observation_window_ticks` and `version_transition_max_non_continuous_reject_rate_pct`.

### 5.3 Trust and Security Bounds

1. Signature freshness/skew verdict uses `auth_clock_skew_tolerance_ms`.
2. External intent freshness verdict uses `external_intent_ttl_ms`.
3. Internal event freshness verdict uses `internal_event_ttl_ms`.
4. Control command freshness verdict uses `control_command_ttl_ms`.
5. Nonce replay verdict uses `auth_nonce_horizon_ms`.

### 5.4 Numeric Determinism Bounds

1. Conversion-scale verdict uses `position_fixed_scale` and `velocity_fixed_scale`.
2. Numeric-range guardrail verdict uses `max_abs_position_units`, `max_abs_velocity_units_per_tick`, `max_abs_acceleration_units_per_tick2`.

## 6. Failure Classification

Every failing test MUST classify one of:
1. `INVARIANT_VIOLATION`
2. `TIMEOUT_BUDGET_EXCEEDED`
3. `UNBOUNDED_RESOURCE_BEHAVIOR`
4. `NON_DETERMINISTIC_RESULT`
5. `IDEMPOTENCY_FAILURE`
6. `BOUNDARY_BREACH`
7. `HARNESS_INVALID`
8. `AUTH_TRUST_VIOLATION`
9. `API_CONTRACT_VIOLATION`

## 7. Matrix Maintenance

1. New invariant statements require a corresponding matrix row before release.
2. New baseline profile keys that impact verdict logic require explicit matrix references.
3. Scenario references MAY evolve, but pass criteria and gate requirements MUST remain explicit and machine-checkable.
