# Version-Line Cutover and Rollback

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Contract Binding

Game image transitions MUST follow `docs-core/04-3-version-line-transition-contract.md`.

## 2. Required Behavior

1. Only one authoritative version line may mutate state at a time.
2. Cutover MUST occur at deterministic transition generation boundaries.
3. Rollback MUST be bounded, deterministic, and idempotent-safe.
4. Rollback MUST preserve durable single-commit equivalence.

## 3. Evidence

Transition/rollback runs MUST emit evidence compatible with `docs-core/05-1-conformance-test-matrix.md` game-boundary rows.
