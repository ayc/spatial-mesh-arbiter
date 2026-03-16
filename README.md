# Spatial Mesh Arbiter

A lock-free, deterministic, 60Hz distributed game engine designed for massive-scale (4,000+ player) multiplayer environments. It solves the "Blackhole" density problem — extreme player concentration in a single area — using spatial partitioning, kinematic dilation, and a strict single-authority actor model, without generic distributed locks or time-travel buffers.

## Project Structure

The project is organized into three documentation layers with a clear precedence hierarchy:

### 1. [`docs-core/`](docs-core/README.md) — Engine Framework (Authoritative)

The game-agnostic engine contract. Defines the reusable runtime rules for time, space, topology, and transport that remain constant regardless of the game built on top. Covers:

- Spatial runtime kernel (authority, ticks, R-Tree topology)
- Messaging plane (wire envelopes, routing, idempotency)
- Durability bridge (hard vs. soft state, persistence reconciliation)
- Game adapter interface (trait-based boundary for plugging in game logic)
- Conformance invariants and test matrix

**This layer is authoritative.** If any other layer conflicts with `docs-core/`, `docs-core/` wins.

### 2. [`docs-game-compiler/`](docs-game-compiler/README.md) — Game Compiler Framework

The designer-facing game definition model and compiler toolchain that targets the engine contracts in `docs-core/`. Allows non-engineers to author game behavior in a constrained Lua subset and YAML/JSON, which gets compiled into deterministic runtime artifacts the engine can load.

Covers the designer language spec, Lua subset profile, whitelisted API surface, schema validation, compiler pipeline, game image format, and runtime loading.

### 3. [`docs/`](docs/README.md) — ARPG Reference Implementation

The first concrete game built on the framework — a Diablo-style MMO-ARPG. Serves as both a production spec and a reference template demonstrating how to implement the `docs-core/` engine contracts. Covers architecture, wire protocols, RPG mechanics, ability systems, NPC architecture, infrastructure, and conformance scenarios.

## How These Layers Relate

`docs/` was written first as a monolithic game server specification. The project then recognized that a reusable, game-agnostic engine was embedded inside it. `docs-core/` is the result of extracting and distilling that engine contract — every section was deliberately chosen, refined, and stripped of game-specific semantics.

`docs-game-compiler/` is the newest layer, defining the tooling that sits between the engine and game content. It specifies how designers author game logic that compiles down to artifacts the engine can load via its adapter interface.

The extraction from `docs/` into `docs-core/` is ongoing. [`docs-core/06-architecture-section-mapping.md`](docs-core/06-architecture-section-mapping.md) is the active roadmap for this decomposition — it maps every section of `docs/1-architecture/` to a disposition (`retain-core`, `split`, or `move-template`) indicating where that content belongs in the final structure.

## Key Engineering Constraints

- **No floating-point math** in the simulation loop — fixed-point (`I32F32`) only, for cross-CPU determinism
- **60Hz tick rate is sacred** — the Arbiter never drops frames; load adaptation happens via kinematic dilation
- **Lock-free mutability** — actors share no memory; concurrency through spatial jurisdiction, not mutexes
- **Strict single authority** — each entity has exactly one authoritative owner per tick
