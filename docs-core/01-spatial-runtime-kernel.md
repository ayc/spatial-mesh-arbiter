# Spatial Runtime Kernel

## 1. Responsibilities

The kernel owns:
- spatial partitioning and authority assignment
- topology mutation (split/merge/slide)
- authoritative tick scheduling
- movement integration and collision primitives
- cross-boundary visibility proxies
- load adaptation mechanisms

## 2. Authority Contract

1. At any tick, one and only one runtime node may mutate an entity's authoritative state.
2. Ownership transitions must occur at deterministic cutover ticks.
3. Transition windows must be fail-closed if ownership is ambiguous.

## 3. Tick Contract

1. Authoritative loop cadence is fixed.
2. Tick values are monotonic and never move backward.
3. Tick loop ordering is stable and explicitly defined.
4. Runtime load policies may scale entity progression speed, but must not violate loop determinism.

## 4. Topology Contract

1. Topology changes are versioned by monotonic epochs.
2. All participants validate epoch compatibility for ingress and handoff traffic.
3. Stale traffic is rejected or short-buffered under bounded timeout rules.

## 5. Runtime Safety Constraints

1. No blocking disk/network/database calls in authoritative tick path.
2. No unbounded queues in runtime mutation path.
3. No non-deterministic iteration order for authoritative mutation collections.
4. Runtime arithmetic and conversion rules must be consistent across hosts.
5. A runtime node MUST NOT accept entity authority until it has loaded and activated a valid game content version. Content loading is asynchronous and MUST NOT block the tick path; activation occurs atomically at a frame boundary.

## 6. Quantitative Safety Profile (Baseline)

The following baseline bounds make section 5 operationally testable.
Deployments MAY tune values, but every bound MUST remain finite and explicitly configured.

Canonical defaults are defined in `00-1-core-baseline-profile.md`.

### 6.1 Tick and Timing Bounds

1. `frame_budget_us`.
2. `metronome_heartbeat_stale_ticks`.
3. `metronome_heartbeat_degraded_ticks`.

### 6.2 Ingress Fairness Bounds

1. `proposal_bucket_capacity`.
2. `proposal_bucket_refill_per_tick`.
3. `movement_cost`.
4. `discrete_cost`.

### 6.3 Queue Capacity Bounds

1. `external_inbox_cap`.
2. `internal_inbox_cap`.
3. `stale_buffer_cap`.

### 6.4 Replay and Idempotency Bounds

1. `max_event_age_ticks`.
2. `idempotency_bucket_capacity`.
3. Effective key ceiling approximation:
`max_idempotency_keys ~= max_event_age_ticks * idempotency_bucket_capacity`.
4. Dedupe overflow behavior MUST fail closed and emit overflow metrics.

### 6.5 Stale Handshake Timeout Bounds

1. Topology/data stale buffering timeout MUST be bounded.
2. Baseline timeout bound: `stale_sync_timeout_ticks <= max_event_age_ticks`.
3. On timeout, non-continuous intents MUST be explicitly rejected (never silently dropped).

### 6.6 Deterministic Numeric Guardrails

1. `position_fixed_scale`.
2. `velocity_fixed_scale`.
3. `max_abs_position_units`.
4. `max_abs_velocity_units_per_tick`.
5. `max_abs_acceleration_units_per_tick2`.

## 7. Deterministic Numeric Semantics

### 7.1 Canonical Authoritative Numeric Model

1. Authoritative spatial simulation MUST use integer/fixed-point arithmetic for mutation decisions.
2. Floating-point values MAY be accepted at ingress only, and MUST be normalized before entering authoritative mutation logic.
3. After normalization, authoritative state and replay logs MUST carry canonical fixed-point/integer values only.

### 7.2 Conversion and Rounding Rules

1. Canonical conversion rule:
`fixed = round_half_away_from_zero(input_value * configured_scale)`.
2. Canonical scales are `position_fixed_scale` and `velocity_fixed_scale` from the baseline profile.
3. Input values producing absolute converted magnitude above configured guardrails MUST be rejected fail closed.
4. `NaN` or `Inf` numeric inputs MUST be rejected deterministically before mutation admission.

### 7.3 Arithmetic and Overflow Rules

1. Fixed-point multiply/divide operations MUST use widened intermediates sufficient to detect overflow before narrowing.
2. Overflow on authoritative numeric operations MUST fail closed (reject/fault, no mutation side effects).
3. Silent wraparound overflow is non-conformant.
4. Deterministic integer division in authoritative paths MUST truncate toward zero.

### 7.4 Wire and Replay Numeric Consistency

1. Numeric payload fields that affect authoritative mutation MUST be schema-defined with explicit scale metadata.
2. Equivalent numeric values MUST serialize to one canonical replay/wire representation.
3. Host-specific floating-point modes MUST NOT affect authoritative outcomes.
