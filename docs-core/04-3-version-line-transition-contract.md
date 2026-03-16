# Version-Line Transition Contract (Normative)

This document defines deterministic rollout and rollback behavior for adapter
version-line changes in an authoritative runtime mesh.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope and Precedence

1. `05-conformance-invariants.md` defines non-negotiable invariants.
2. `04-2-game-adapter-api-contract.md` defines strict adapter API and startup negotiation.
3. This document defines operational transition/rollback behavior between valid version lines.
4. `04-1-game-adapter-contract.md` defines adapter behavior constraints.

If there is a conflict, higher-precedence documents win.

## 2. Definitions

1. **Version line**: `(adapter_identity, adapter_version_line)` admitted for authority duties.
2. **Source line**: currently active authoritative version line before transition.
3. **Target line**: candidate version line to become active.
4. **Transition generation**: unique id for one transition attempt.
5. **Transition window**: bounded interval from transition start to commit or rollback completion.

## 3. Global Transition Invariants

1. Exactly one version line may own authoritative mutation rights at any instant.
2. Mixed source/target authority mutation for the same transition generation is non-conformant.
3. Transition decisions (commit/rollback) MUST be deterministic from observed gate conditions.
4. Transition and rollback paths MUST preserve replay/idempotency guarantees.
5. Rollback MUST NOT mint duplicate durable outcomes.

## 4. State Machine

The transition controller MUST enforce this state machine:
1. `PREPARE`
2. `DRAIN`
3. `CUTOVER`
4. `STABILIZE`
5. terminal `COMMITTED` or `ROLLED_BACK`

No other terminal states are allowed.

## 5. Phase Requirements

### 5.1 `PREPARE`

1. Validate target compatibility via `04-2-game-adapter-api-contract.md`.
2. Ensure target-line nodes are bootstrapped and ready but not authoritative.
3. Complete within `version_transition_prepare_timeout_ms` or fail to `ROLLED_BACK`.

### 5.2 `DRAIN`

1. Source line continues authority but stops admitting new source-line scale-out.
2. Non-essential topology churn SHOULD be suppressed for transition stability.
3. Source authoritative workload is drained toward target eligibility criteria.
4. Drain phase MUST complete within `version_transition_drain_timeout_ms` or fail to `ROLLED_BACK`.

### 5.3 `CUTOVER`

1. Cutover point MUST be a deterministic control event identified by transition generation.
2. Authority admission switches from source line to target line at cutover commit.
3. Source line MUST stop accepting new authoritative ownership after cutover commit.
4. If cutover cannot be applied atomically, transition MUST fail to `ROLLED_BACK`.

### 5.4 `STABILIZE`

1. Target line runs authority exclusively for `version_transition_commit_stabilization_ticks`.
2. During stabilization, rollback is still permitted when rollback triggers fire.
3. If stabilization passes without rollback trigger, transition commits (`COMMITTED`).

## 6. Rollback Contract

### 6.1 Rollback Triggers

A transition MUST rollback when any required gate fails, including:
1. authority invariant breach
2. determinism/replay digest mismatch
3. bounded safety-profile violation
4. adapter negotiation boundary breach
5. non-continuous reject-rate breach beyond configured transition bound

### 6.2 Rollback Behavior

1. Rollback MUST restore source line as sole authoritative line.
2. Rollback completion MUST be bounded by `version_transition_rollback_timeout_ms`.
3. Target line writes observed during failed transition MUST be reconciled idempotently.
4. Discrete intents accepted during failed target window MUST resolve deterministically (success preserved or compensated), never duplicated.

### 6.3 Rollback Safety Outcomes

1. Durable business outcomes MUST remain single-commit equivalent per transaction identity.
2. Compensation side effects MUST be auditable and idempotent.
3. Replay of transition window logs MUST converge to the same committed/rolled-back final state.

## 7. Quantitative Bounds

Canonical defaults are defined in `00-1-core-baseline-profile.md`:
1. `version_transition_prepare_timeout_ms`
2. `version_transition_drain_timeout_ms`
3. `version_transition_commit_stabilization_ticks`
4. `version_transition_rollback_timeout_ms`
5. `version_transition_reject_observation_window_ticks`
6. `version_transition_max_non_continuous_reject_rate_pct`

## 8. Observability Requirements

Implementations MUST emit:
1. `transition_generation`
2. `source_version_line`, `target_version_line`
3. phase transitions with timestamps
4. rollback trigger classification
5. per-phase duration metrics
6. non-continuous reject-rate during transition window
7. reconciliation/compensation counters during rollback

## 9. Conformance Requirements

A version-line transition implementation is conformant only if it passes:
1. successful transition commit tests (`PREPARE -> DRAIN -> CUTOVER -> STABILIZE -> COMMITTED`)
2. rollback-on-gate-failure tests with bounded rollback completion
3. single-authority-line tests during all phases
4. replay equivalence tests across transition generations
5. no-duplicate-durable-outcome tests across rollback paths
