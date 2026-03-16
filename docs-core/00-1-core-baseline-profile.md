# Core Baseline Profile

This document is the single canonical source for baseline quantitative defaults used by core framework contracts.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope

This profile defines default values for:
1. runtime tick/timing bounds
2. ingress fairness and queue capacities
3. replay/idempotency horizons
4. adapter hook budgets and containment thresholds
5. durability bridge and reconciliation bounds
6. messaging trust/freshness bounds
7. version-line transition and rollback bounds
8. deterministic numeric guardrails

## 2. Usage Rules

1. Core docs MUST reference these keys instead of duplicating numeric defaults.
2. Deployments MAY tune values, but every key MUST remain finite and explicitly configured.
3. Constraint relationships in this document MUST be preserved under tuning.

## 3. Baseline Defaults

### 3.1 Runtime Timing

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `frame_budget_us` | `16_666` | microseconds | fixed 60Hz frame budget |
| `metronome_heartbeat_stale_ticks` | `180` | ticks | stale-mode threshold |
| `metronome_heartbeat_degraded_ticks` | `600` | ticks | degraded-mode threshold |

### 3.2 Ingress Fairness and Queues

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `proposal_bucket_capacity` | `24` | tokens | per-entity burst cap |
| `proposal_bucket_refill_per_tick` | `2` | tokens/tick | per-entity refill rate |
| `movement_cost` | `1` | tokens | continuous movement cost |
| `discrete_cost` | `3` | tokens | non-continuous intent cost |
| `external_inbox_cap` | `5000` | messages | bounded runtime ingress |
| `internal_inbox_cap` | `2000` | messages | bounded relay/control ingress |
| `stale_buffer_cap` | `1000` | messages | bounded epoch-sync buffer |
| `fairness_observation_window_ticks` | `600` | ticks | fairness isolation measurement window |
| `fairness_isolation_max_degradation_pct` | `10` | percent | MUST satisfy `0 <= fairness_isolation_max_degradation_pct <= 100` |

### 3.3 Replay and Idempotency

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `max_event_age_ticks` | `60` | ticks | replay horizon (1.0s at 60Hz) |
| `idempotency_bucket_capacity` | `8192` | keys/bucket | dedupe memory guardrail |
| `stale_sync_timeout_ticks` | `60` | ticks | MUST satisfy `stale_sync_timeout_ticks <= max_event_age_ticks` |

Derived planning formula:
`max_idempotency_keys ~= max_event_age_ticks * idempotency_bucket_capacity`

### 3.4 Adapter Budget and Containment

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `adapter_tick_budget_us` | `6_000` | microseconds/tick | cumulative adapter budget per authoritative tick |
| `validate_hook_budget_us` | `200` | microseconds/call | soft budget |
| `resolve_external_hook_budget_us` | `1_000` | microseconds/call | soft budget |
| `resolve_internal_hook_budget_us` | `1_000` | microseconds/call | soft budget |
| `spawn_hook_budget_us` | `4_000` | microseconds/call | soft budget (off hot path) |
| `hot_hook_timeout_us` | `2_000` | microseconds/call | hard timeout for validate/external/internal hooks |
| `spawn_hook_timeout_us` | `10_000` | microseconds/call | hard timeout for spawn hook |
| `adapter_fault_window_ticks` | `300` | ticks | rolling fault window (5s at 60Hz) |
| `adapter_fault_threshold` | `32` | faults/window | containment entry threshold |
| `adapter_degraded_hold_ticks` | `600` | ticks | minimum containment hold duration |

### 3.5 Durability and Reconciliation

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `tx_pending_timeout_ms` | `30_000` | milliseconds | max wait for runtime confirmation before compensation path |
| `tx_reconcile_scan_interval_ms` | `5_000` | milliseconds | reconciliation worker cadence |
| `runtime_command_dedupe_horizon_ms` | `120_000` | milliseconds | MUST satisfy `runtime_command_dedupe_horizon_ms >= tx_pending_timeout_ms` |
| `durable_consumer_retry_max_attempts` | `8` | attempts | retries before DLQ |
| `durable_consumer_retry_backoff_initial_ms` | `100` | milliseconds | exponential backoff start |
| `durable_consumer_retry_backoff_max_ms` | `5_000` | milliseconds | exponential backoff cap |

### 3.6 Messaging Trust and Freshness

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `auth_clock_skew_tolerance_ms` | `5_000` | milliseconds | max allowed signer/verifier clock skew |
| `external_intent_ttl_ms` | `15_000` | milliseconds | max external-intent freshness window |
| `internal_event_ttl_ms` | `30_000` | milliseconds | max internal-event freshness window |
| `control_command_ttl_ms` | `30_000` | milliseconds | max control-command freshness window |
| `auth_nonce_horizon_ms` | `120_000` | milliseconds | MUST satisfy `auth_nonce_horizon_ms >= max(external_intent_ttl_ms, internal_event_ttl_ms, control_command_ttl_ms)` |

### 3.7 Version-Line Transition and Rollback

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `version_transition_prepare_timeout_ms` | `30_000` | milliseconds | max `PREPARE` phase duration |
| `version_transition_drain_timeout_ms` | `120_000` | milliseconds | max `DRAIN` phase duration |
| `version_transition_commit_stabilization_ticks` | `300` | ticks | minimum `STABILIZE` duration before commit |
| `version_transition_rollback_timeout_ms` | `60_000` | milliseconds | max rollback completion time |
| `version_transition_reject_observation_window_ticks` | `600` | ticks | reject-rate evaluation window |
| `version_transition_max_non_continuous_reject_rate_pct` | `5` | percent | MUST satisfy `0 <= version_transition_max_non_continuous_reject_rate_pct <= 100` |

### 3.8 Deterministic Numeric Guardrails

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `position_fixed_scale` | `1000` | units/meter | MUST be positive integer scale |
| `velocity_fixed_scale` | `1000` | units/(meter/second) | MUST be positive integer scale |
| `max_abs_position_units` | `2_000_000_000` | fixed units | absolute position conversion guardrail |
| `max_abs_velocity_units_per_tick` | `200_000` | fixed units/tick | absolute per-tick velocity guardrail |
| `max_abs_acceleration_units_per_tick2` | `50_000` | fixed units/tick^2 | absolute per-tick acceleration guardrail |

## 4. Cross-Document References

This profile is consumed by:
1. `01-spatial-runtime-kernel.md`
2. `02-spatial-messaging-plane.md`
3. `04-1-game-adapter-contract.md`
4. `03-durability-bridge.md`
5. `05-1-conformance-test-matrix.md`
6. `04-3-version-line-transition-contract.md`
