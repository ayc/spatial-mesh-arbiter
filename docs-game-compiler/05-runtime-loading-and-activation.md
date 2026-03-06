# Runtime Loading and Activation

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Load Sequence

1. verify image integrity
2. validate compatibility against runtime and adapter contracts
3. stage image in non-authoritative state
4. activate at deterministic cutover point

## 2. Compatibility Binding

Startup admission MUST align with `docs-core/04-2-game-adapter-api-contract.md`.

Runtime MUST reject images that fail adapter identity/version or wire schema compatibility checks.

## 3. Operational Guarantees

1. Load/activation MUST NOT bypass engine authority invariants.
2. Activation failure MUST fail closed with explicit reason codes.
3. Activation events MUST be observable and auditable.
