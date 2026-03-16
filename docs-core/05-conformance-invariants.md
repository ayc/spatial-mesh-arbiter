# Conformance Invariants

This document defines non-negotiable invariants for engine conformance.

Normative verification criteria for these invariants are defined in
`05-1-conformance-test-matrix.md`.

Canonical scenario identifiers used by that matrix are defined in
`05-2-core-conformance-scenario-catalog.md`.

If a matrix row conflicts with an invariant statement, this document takes
precedence.

## 1. Authority Invariants

1. Single-writer authority per entity per tick.
2. Ownership transfer only at deterministic cutover points.
3. No dual-simulation side effects during transition windows.

## 2. Determinism Invariants

1. Tick progression is monotonic.
2. Authoritative mutation ordering is deterministic.
3. Numeric and conversion behavior is host-consistent.
4. Replay of deterministic logs/messages converges to equivalent state.
5. Numeric normalization, rounding, and overflow handling are explicit and deterministic.

## 3. Messaging Invariants

1. Mutation-capable messages carry idempotency identity.
2. Duplicate delivery cannot produce duplicate mutation.
3. Non-continuous intents terminate with one terminal outcome.
4. Stale epoch handling is explicit (reject or bounded buffer).

## 4. Runtime Safety Invariants

1. No blocking I/O in authoritative loop.
2. All hot-path queues and ledgers are bounded.
3. Overflow behavior is deterministic and observable.

## 5. Durability Invariants

1. Hard-state transitions are emitted to durable async path.
2. Durable consumers ack only after durable commit.
3. Recovery/reconciliation is idempotent and auditable.

## 6. Game Boundary Invariants

1. Engine never embeds game-specific economic/progression semantics.
2. Game adapter never bypasses engine authority/time/topology rules.
3. Engine contracts remain reusable across game implementations.
4. Adapter compatibility negotiation and startup admission are deterministic and explicit.
5. Version-line transition and rollback behavior is deterministic, bounded, and single-authority safe.

## 7. Security and Trust Invariants

1. Untrusted external traffic cannot mutate authoritative state without valid authenticated mediation.
2. Mutation-capable messages enforce integrity and source authentication at ingress.
3. Freshness and replay protection are explicit, bounded, and fail closed.
4. Authorization by message class and source role is explicit and deterministic.
