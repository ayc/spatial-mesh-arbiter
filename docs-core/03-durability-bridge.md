# Durability Bridge

This document is normative for bridging ephemeral runtime effects and durable platform state.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

Canonical numeric defaults are defined in `00-1-core-baseline-profile.md`.

## 1. Purpose

The durability bridge connects authoritative in-memory simulation with durable persistence without blocking the authoritative tick loop.

## 2. Hard vs Soft State Contract

Hard state:
1. loss can create exploit, economic inconsistency, or irrecoverable progression divergence
2. MUST be persisted via durable asynchronous workflows

Soft state:
1. high-frequency simulation state
2. authoritative in-memory while runtime node is alive
3. recoverable through lifecycle/reconciliation flows rather than strict replay

## 3. Event Bus Contract

### 3.1 Delivery and Ordering

1. Delivery model MUST be at-least-once.
2. Ordering guarantees are per partition only; consumers MUST NOT assume global ordering.
3. Producer keys SHOULD preserve per-entity/per-transaction ordering locality where required.

### 3.2 Producer Rules

1. Every published event MUST include a stable unique identity (`event_id`).
2. Producer retries MUST be idempotent-safe.
3. Publishing failures MUST be observable and retried via bounded retry policy.

### 3.3 Consumer Rules

1. Consumers MUST commit offsets only after durable side effects commit.
2. Consumers MUST be idempotent by event identity.
3. Retry policy MUST be bounded by these baseline keys:
`durable_consumer_retry_max_attempts`, `durable_consumer_retry_backoff_initial_ms`, `durable_consumer_retry_backoff_max_ms`.
4. After retry budget exhaustion, record MUST be moved to DLQ with source metadata for deterministic replay.

## 4. Command Ingress Contract

### 4.1 Runtime Command Envelope Requirements

Every durable-to-runtime command that can mutate authoritative state MUST carry:
1. `command_id` (unique idempotency identity)
2. source identity
3. topology/data epoch context when relevant
4. causal reference to durable business action (`tx_id` or equivalent)

### 4.2 Queueing and Admission

1. Runtime command workers MUST bridge into authoritative loop through bounded non-blocking queues.
2. Queue overflow MUST be explicit and observable (never silent successful acceptance).
3. Runtime MUST deduplicate commands by `command_id`.
4. Dedup retention horizon MUST satisfy:
`runtime_command_dedupe_horizon_ms >= tx_pending_timeout_ms`

### 4.3 Duplicate Command Race Rule

If the same `command_id` is observed concurrently/repeatedly (retry, rebalance, replay):
1. at most one authoritative mutation attempt is permitted
2. subsequent duplicates MUST resolve as idempotent no-op
3. duplicate observations SHOULD still produce deterministic acknowledgment or audit records

## 5. Reconciliation State Machine

Bridge operations that consume durable value and require runtime confirmation MUST use explicit transaction states.

### 5.1 Required States

1. `PENDING`: durable side effect committed; waiting for runtime confirmation.
2. `CONFIRMED`: runtime confirmation accepted; transaction closed success.
3. `COMPENSATING`: timeout/failure path started; compensation in progress.
4. `COMPENSATED`: compensation committed; transaction closed compensated.

### 5.2 Required Timers

1. `tx_pending_timeout_ms`: max wait before entering compensation path.
2. `tx_reconcile_scan_interval_ms`: cadence for timeout/reconcile scanning.

### 5.3 Transition Rules

1. `PENDING -> CONFIRMED` on valid confirmation before timeout cutoff.
2. `PENDING -> COMPENSATING` when timeout cutoff is reached.
3. `COMPENSATING -> COMPENSATED` after compensation durable commit.
4. `CONFIRMED` and `COMPENSATED` are terminal states.

## 6. Edge Case Semantics

### 6.1 Late Acknowledgment Rule

Late confirmation received after timeout cutoff MUST NOT reopen success path.

Required behavior:
1. if transaction is `CONFIRMED`: idempotent no-op
2. if transaction is `COMPENSATING` or `COMPENSATED`: ignore confirmation for mutation, emit `late_ack_dropped` audit signal

This deterministic rule prevents success/compensation flip-flops from delivery jitter.

### 6.2 Duplicate Confirmation Race

Duplicate confirmations for the same `tx_id` MUST be idempotent:
1. first valid confirmation may transition `PENDING -> CONFIRMED`
2. all subsequent confirmations are no-op/audit only

### 6.3 Rollback/Compensation Window Rule

1. Compensation path begins no later than `tx_pending_timeout_ms` after pending creation.
2. Compensation attempts MUST be idempotent.
3. Compensation completion/failure MUST be durably auditable.
4. Recovery MUST never mint duplicate durable outcomes.

## 7. Observability Requirements

Implementations MUST emit at least:
1. `pending_count`
2. `pending_age_ms` distribution
3. `confirmed_count`
4. `compensating_count`
5. `compensated_count`
6. `late_ack_dropped_count`
7. `duplicate_command_count`
8. `duplicate_confirmation_count`
9. `dlq_publish_count`
10. retry-attempt histograms and final-attempt failures

## 8. Conformance Checks

A durability-bridge implementation is conformant only if it passes:
1. at-least-once duplicate delivery idempotency tests
2. offset-commit-after-durable-commit tests
3. duplicate command race tests (single mutation)
4. late-ack-after-timeout tests (no reopen from compensated path)
5. compensation idempotency and auditability tests
6. retry-budget-to-DLQ transition tests
