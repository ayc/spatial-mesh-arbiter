# Game Adapter Contract (Normative)

This document is the normative companion to `04-0-game-adapter-interface.md`.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope and Precedence

This contract defines required behavior at the engine/game adapter boundary.

Precedence rules:
1. `05-conformance-invariants.md` defines non-negotiable global invariants.
2. This document defines adapter-specific requirements.
3. `04-2-game-adapter-api-contract.md` defines strict request/response and startup negotiation shape.
4. `04-3-version-line-transition-contract.md` defines rollout/rollback behavior between version lines.
5. `04-0-game-adapter-interface.md` is conceptual and explanatory.

If there is a conflict, higher-precedence documents win.

## 2. Required Adapter Surface

Every game adapter MUST implement these hooks:
1. Intent validation hook.
2. External action resolution hook.
3. Internal event resolution hook.
4. Spawn/initial-state construction hook.
5. Serialization compatibility declarations for game-owned payloads.

The adapter MAY add internal helper hooks, but engine integration MUST only depend on the required surface above.

Canonical request/response envelope fields, required enums, and deterministic call semantics are defined in `04-2-game-adapter-api-contract.md`.

## 3. Tick Boundary and Call Order Contract

The engine MUST invoke adapter hooks in a stable, deterministic order.

Within each authoritative tick:
1. Global-event resolution hooks execute before internal relay-event hooks.
2. Internal relay-event hooks execute before external action-resolution hooks.
3. For a given class of work, entity iteration order MUST be deterministic.
4. Adapter outcomes are applied only through the engine mutation pipeline.

The adapter MUST NOT assume out-of-band callbacks or direct engine state mutation.

## 4. Ownership and Mutation Contract

Engine-owned domains (adapter MUST NOT mutate directly):
1. Authoritative tick progression and pacing.
2. Spatial topology, ownership, and handoff mechanics.
3. Transport/routing envelopes and replay/idempotency machinery.
4. Engine-core entity fields and runtime safety structures.

Game-owned domains (adapter MAY define and mutate via returned outcomes):
1. Action semantics and game-level validation rules.
2. Game extension state and interpretation.
3. Game-level event meaning and hard-event payload meaning.
4. Content schemas and balancing assets.

The adapter MUST express all intended state changes as returned outcomes, not imperative side effects against engine internals.

## 5. Determinism Requirements

Adapter execution in authoritative paths MUST satisfy:
1. No wall-clock reads for simulation decisions.
2. No OS/system randomness in simulation decisions.
3. No blocking I/O (network, disk, database) in hook execution.
4. No non-deterministic collection iteration affecting mutation order.
5. Numeric behavior consistent with engine determinism rules.

Random decisions MUST use engine-provided deterministic RNG only.

## 6. Outcome and Error Semantics

For discrete external intents:
1. Each intent key MUST terminate with exactly one terminal outcome (`accept` or `reject`).
2. Terminal outcomes MUST be idempotent by intent key.
3. Duplicate delivery MUST NOT produce duplicate mutations.

For continuous intents:
1. Per-intent terminal outcomes MAY be omitted.
2. Reconciliation MUST occur via authoritative snapshots.

Failure handling:
1. Validation failures MUST return deterministic reject outcomes.
2. Resolution-time adapter faults MUST fail closed (reject/no mutation) and emit observable fault signals.

## 7. Serialization and Compatibility Contract

Game-owned payloads crossing engine boundaries MUST be:
1. Explicitly versioned.
2. Backward/forward compatibility-scoped by declared strategy.
3. Deterministically serializable/deserializable.

Compatibility requirements:
1. Engine and adapter MUST negotiate compatible versions at startup.
2. A deployed runtime mesh MUST host one adapter identity/version line at a time.
3. Breaking payload/schema changes MUST require explicit version increment and rollout policy.
4. Startup admission MUST follow the handshake state machine and failure codes defined in `04-2-game-adapter-api-contract.md`.
5. Version-line upgrade and rollback behavior MUST follow `04-3-version-line-transition-contract.md`.

## 8. Failure and Degraded-Mode Contract

The engine MUST enforce bounded adapter impact under failure:
1. Hook execution budgets MUST be bounded by configuration.
2. Hook timeout/exception handling MUST be deterministic and observable.
3. Repeated adapter faults MUST trigger deterministic containment policy (for example: entity-level reject-only mode or process-level failover policy).

The adapter MUST be safe under replay/retry; recovery paths MUST NOT mint duplicate durable outcomes.

### 8.1 Baseline Quantitative Bounds

Canonical defaults are defined in `00-1-core-baseline-profile.md`.

Required profile keys:
1. `frame_budget_us`
2. `adapter_tick_budget_us`
3. `validate_hook_budget_us`
4. `resolve_external_hook_budget_us`
5. `resolve_internal_hook_budget_us`
6. `spawn_hook_budget_us`
7. `hot_hook_timeout_us`
8. `spawn_hook_timeout_us`
9. `adapter_fault_window_ticks`
10. `adapter_fault_threshold`
11. `adapter_degraded_hold_ticks`

### 8.2 Timeout and Overrun Semantics

1. A hook call exceeding its hard timeout threshold MUST be treated as `ADAPTER_HOOK_TIMEOUT`.
2. Timeout handling MUST fail closed for the triggering operation (no mutation applied).
3. If cumulative adapter time exceeds `adapter_tick_budget_us`, the runtime MUST stop admitting additional non-continuous external intents for that tick and return deterministic rejects.
4. Continuous movement intents MAY still be coalesced/dropped and reconciled by snapshots.

### 8.3 Repeated-Fault Containment

1. If `adapter_fault_threshold` is reached within `adapter_fault_window_ticks`, runtime MUST enter deterministic containment mode.
2. In containment mode, game-specific non-continuous external intents MUST return deterministic reject (`ADAPTER_DEGRADED` class) for at least `adapter_degraded_hold_ticks`.
3. Containment transitions (enter/exit) MUST be observable via structured events/metrics.
4. Recovery from containment MUST NOT bypass replay/idempotency guarantees.

## 9. Conformance Requirements

An adapter implementation MUST pass, at minimum:
1. Deterministic replay equivalence tests.
2. Intent idempotency and duplicate-delivery tests.
3. Handoff/replay boundary tests for game-owned payloads.
4. Compatibility negotiation tests for supported version pairs.
5. Fault-containment tests (timeout, exception, malformed payload).
6. Strict API-envelope and enum conformance tests against `04-2-game-adapter-api-contract.md`.

Adapter certification is incomplete until all required conformance groups pass.
