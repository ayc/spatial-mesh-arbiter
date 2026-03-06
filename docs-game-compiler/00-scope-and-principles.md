# Scope and Principles

## 1. Core Intent

Define a reusable, game-agnostic authoring and compilation model for game logic.

The output of this model is a deterministic game artifact loadable by runtime roles
(Edge, Arbiter, Controller-adjacent services) without embedding game-specific logic
in the core engine.

## 2. Goals

1. Designer-first authoring model with minimal required code.
2. Deterministic compile output for runtime safety and replay consistency.
3. Strict compatibility with `docs-core/` contracts.
4. Clear separation between engine runtime and game business semantics.

## 3. Non-Goals

1. Replacing `docs-core/` runtime contracts.
2. Allowing arbitrary unbounded scripting in authoritative paths.
3. Runtime hot-patching that bypasses version-line cutover policy.
