# Scope and Principles

## 1. Core Intent

The framework is a deterministic, spatially aware runtime for large-scale multiplayer simulation on a shared world map.

It is not a game ruleset.

## 2. Layer Model

1. Spatial Runtime Kernel
2. Spatial Messaging Plane
3. Durability Bridge
4. Game Adapter Layer

The first three layers are engine-owned. The fourth is game-owned.

## 3. Core Principles

1. Single Spatial Authority: each entity has exactly one authoritative owner per tick.
2. Deterministic Execution: same inputs and same tick order produce same outputs.
3. Non-Blocking Simulation: no blocking I/O in the authoritative simulation loop.
4. Bounded Memory Under Load: queues, ledgers, and buffers must be capacity-limited.
5. Idempotent Cross-Boundary Semantics: duplicate network delivery must not cause duplicate state mutation.
6. Explicit Hard vs Soft State: only exploit-critical state is durably persisted.
7. Engine/Game Separation: engine owns time, space, transport, and safety invariants; game owns semantics.

## 4. Non-Goals

This abstract does not define:
- Combat math formulas
- Itemization/economy design
- Narrative/social progression rules
- Game content taxonomy

