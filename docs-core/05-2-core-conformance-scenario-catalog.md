# Core Conformance Scenario Catalog (Normative)

This document defines canonical scenario identifiers used by
`05-1-conformance-test-matrix.md`.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope and Precedence

1. `05-conformance-invariants.md` defines required truths.
2. `05-1-conformance-test-matrix.md` defines required pass/fail outcomes.
3. This document defines canonical scenario IDs and execution anchors.

If a harness implementation changes, scenario IDs and assertions in this
document remain the compatibility contract.

## 2. Required Release Host Classes

`DET-03` cross-host determinism checks MUST execute on all required host
classes:

| Host Class ID | Required | Notes |
| --- | --- | --- |
| `HC-LINUX-X86_64` | yes | Linux x86_64 server build target |
| `HC-LINUX-ARM64` | yes | Linux arm64 server build target |

Deployments MAY add host classes, but release conformance MUST include all
required classes above.

## 3. Scenario IDs

### 3.1 Authority

| Scenario ID | Required Assertion |
| --- | --- |
| `SCN-AUTH-UNIQUE-WRITER` | exactly one authoritative writer per `(entity_id, tick)` |
| `SCN-AUTH-CUTOVER-TICK` | ownership cutover occurs exactly at configured cutover tick |
| `SCN-AUTH-AMBIG-HANDOFF-FAILCLOSED` | ambiguous ownership windows fail closed with zero dual simulation |

### 3.2 Determinism

| Scenario ID | Required Assertion |
| --- | --- |
| `SCN-DET-MONOTONIC-TICK` | `current_tick` is strictly monotonic |
| `SCN-DET-REPLAY-DIGEST` | replay digest matches reference digest for same input log |
| `SCN-DET-CROSS-HOST-DIGEST` | replay digest matches across all required host classes |
| `SCN-DET-CONTENTION-STABILITY` | deterministic winner/loser ordering under retry/replay |
| `SCN-DET-NUMERIC-CANONICALIZATION` | equivalent numeric inputs normalize to one canonical authoritative representation |
| `SCN-DET-NUMERIC-OVERFLOW-FAILCLOSED` | NaN/Inf/overflow numeric paths reject fail closed with no mutation |

### 3.3 Messaging

| Scenario ID | Required Assertion |
| --- | --- |
| `SCN-MSG-EXACTLY-ONE-TERMINAL` | one terminal outcome per non-continuous intent |
| `SCN-MSG-DUPLICATE-SAFE` | duplicate envelope delivery causes no duplicate mutation |
| `SCN-MSG-STALE-TIMEOUT` | stale epoch buffering obeys bounded timeout and explicit reject |
| `SCN-MSG-SATURATION-EXPLICIT-REJECT` | saturation never silently drops non-continuous intents |
| `SCN-MSG-SCHEMA-REJECT` | unknown wire schema is rejected before mutation |

### 3.4 Runtime Safety

| Scenario ID | Required Assertion |
| --- | --- |
| `SCN-SAF-NO-BLOCKING-IO` | zero blocking I/O calls on authoritative tick path |
| `SCN-SAF-QUEUE-BOUNDS` | queue lengths remain within configured caps |
| `SCN-SAF-DEDUPE-OVERFLOW-FAILCLOSED` | dedupe overflow rejects fail closed and emit metrics |
| `SCN-SAF-FAIRNESS-ISOLATION` | abusive sender does not exceed configured unrelated-acceptance degradation bound |

### 3.5 Durability

| Scenario ID | Required Assertion |
| --- | --- |
| `SCN-DUR-COMMIT-AFTER-DURABLE` | consumer offset commit only after durable side-effect commit |
| `SCN-DUR-TX-STATE-GRAPH` | only allowed transaction transitions are used |
| `SCN-DUR-LATE-ACK-DROP` | late ack cannot reopen compensated/closing path |
| `SCN-DUR-DUPLICATE-COMMAND` | at most one authoritative mutation attempt per `command_id` |
| `SCN-DUR-RETRY-DLQ` | exhausted retries transition deterministically to DLQ |

### 3.6 Game Boundary

| Scenario ID | Required Assertion |
| --- | --- |
| `SCN-BND-ENGINE-GAME-IMPORT-SCAN` | engine code has no forbidden game-specific dependencies |
| `SCN-BND-ADAPTER-MUTATION-CONTAINMENT` | adapter cannot directly mutate engine-owned state |
| `SCN-BND-SINGLE-ADAPTER-LINE` | deployed mesh exposes exactly one adapter identity/version line |
| `SCN-BND-NEGOTIATION-HANDSHAKE` | startup negotiation success/failure follows contract and deterministic failure codes |
| `SCN-BND-MIXED-VERSION-REJECT` | mixed adapter version lines are rejected from authority |
| `SCN-BND-VERSION-TRANSITION-COMMIT` | valid transition generation commits with bounded phase durations and bounded non-continuous reject-rate impact |
| `SCN-BND-VERSION-TRANSITION-ROLLBACK` | failed transition rolls back to source line within configured rollback timeout |

### 3.7 Security and Trust

| Scenario ID | Required Assertion |
| --- | --- |
| `SCN-SEC-EXTERNAL-SIGNATURE` | invalid/missing external signature is rejected fail closed |
| `SCN-SEC-FRESHNESS-WINDOW` | expired or skew-invalid messages are rejected deterministically |
| `SCN-SEC-NONCE-REPLAY` | replayed nonce within horizon is rejected deterministically |
| `SCN-SEC-ROLE-AUTHZ` | unauthorized source role for message class is rejected fail closed |

## 4. Legacy Mapping (Informative)

Current repository implementations MAY map these core IDs to existing
mini-mesh drills from `docs/5-testing-and-conformance/01-mini-mesh-conformance.md`.
That mapping is operational guidance only and does not replace this contract.
