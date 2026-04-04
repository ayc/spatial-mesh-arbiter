# Spatial Mesh Arbiter — Agent Orientation

This is the specification and implementation repository for the Spatial Mesh Arbiter — a lock-free, deterministic, 60Hz distributed game engine for massive-scale multiplayer (4,000+ players). The engine is being built in Rust.

Accuracy and strict adherence to the specs are non-negotiable.

## Documentation Layers and Precedence

There are three documentation directories with a strict precedence hierarchy:

1. **`docs-core/`** (highest authority) — The game-agnostic engine contract. Reusable runtime rules for time, space, topology, transport, and conformance. This layer is fully mature with zero TODOs or placeholders.

2. **`docs-game-compiler/`** — Designer-facing game definition model and compiler toolchain. Targets `docs-core/` contracts. The Lua authoring specs (01-x files) and ability-primitives catalog are production-quality. The compilation pipeline specs (02-05) are substantial drafts near production. Only `06-version-line-cutover-and-rollback.md` and `07-tooling-workflow.md` are skeletal. The 125 ability sketches systematically lack Cross-Boundary Concerns and Compiler Requirements sections (~290 TODOs).

3. **`docs/`** (reference implementation) — An ARPG (Diablo-style MMO) built on the framework. The original monolithic spec from which the other two layers are being extracted. 17/30 tracked gaps resolved, 12 in review, 1 deferred (see `docs/6-spec-drafts/GAPS_CHECKLIST.md`).

**If any layer conflicts with `docs-core/`, `docs-core/` wins.**

## Origin Story

`docs/` was written first as a single game server specification. The realization that a reusable engine was embedded inside it led to the creation of `docs-core/` (extracted engine contracts) and `docs-game-compiler/` (tooling layer between engine and game content). The extraction is ongoing — `docs-core/06-architecture-section-mapping.md` is the active roadmap, mapping every section of `docs/1-architecture/` to a disposition: `retain-core`, `split`, or `move-template`.

## Core Architecture

The engine operates on a strict Spatial Actor Model:

- **Client (Zero-Trust):** A "dumb terminal" that sends structured Client Intents (e.g., `DiscreteIntent::TargetedAbility`), never raw WASD streams or authoritative outcomes.
- **Edge Node / Proxy Actor (Gateway):** Trusted headless client at the network edge. Performs anti-cheat validation, translates intents into `ActionProposals`, provides client-side prediction (`EdgeAck`). Does not perform combat mitigation math.
- **Mesh Arbiter / Spatial Actor (Authority):** Lock-free, single-threaded deterministic physics loop at 60Hz. Owns a 2D spatial region (R-Tree node) and exclusively mutates `SoftState` of entities within that region.
- **Mesh Controller (Control Plane):** Highly consistent (Raft) cluster that dictates R-Tree topology (splits/merges), synchronizes the global tick ("The Metronome"), and routes high-radius Global Events.
- **Meta Services:** Eventual-consistency services (Inventory, Social, Persistence). The Arbiter communicates with Meta asynchronously via a Redpanda event bus (Kafka API), emitting `HardEvents` like `PlayerDied` or `LootSpawned`.

### Two-Phase Combat Pipeline

Attacker and defender may exist on different physical Arbiters, so combat is asynchronous:

1. Client sends `DiscreteIntent` to Edge.
2. Edge validates and sends `ActionProposal` to attacker's Host Arbiter.
3. **Phase 1 (Offense):** Attacker's Arbiter evaluates against `OffensiveStats`, generates `CombatContext` (crits, base damage, armor pen).
4. **The Relay:** If target is a Ghost (owned by neighbor), wraps `CombatContext` in `MeshInternalEvent::InternalPreparedHit` and sends over RUDP.
5. **Phase 2 (Defense):** Target's Arbiter evaluates `CombatContext` against `DefensiveStats` (resistances, block, evasion) and mutates `SoftState`.

### Key Engine Mechanics

- **Ghost Entities:** Read-only 2D projections of entities near Arbiter borders. Synchronized via UDP dead-reckoning. Used for local raycasting and collision, not direct damage (they trigger the `ImpactEvent` relay).
- **Ephemeral Actors (Projectiles):** Independent `ProjectileActor` structs with their own `tick()` loop. Cross-boundary handoff uses a 3-phase protocol (`Prepare` → `Ack` → `Commit`) over RUDP.
- **Kinematic Dilation (KiDi):** Defense against density events (4,000 players in one cell). Arbiter calculates a `dilation_factor` — entities move/cast/recover slower while the server still ticks at 60Hz.

## Strict Engineering Rules

- **No floating-point math** in the simulation loop. Use `I32F32` (SimFixed) from the `fixed` crate with saturating arithmetic (`saturating_mul`, `saturating_add`).
- **60Hz tick rate is non-negotiable.** Load adaptation happens via kinematic dilation, never by dropping frames.
- **Lock-free mutability.** Actors share no memory. Concurrency is achieved through spatial jurisdiction, not mutexes.
- **Token-bucket ingress.** Every `ActionProposal` is gated by a per-entity token bucket.
- **Verify with structs.** The source of truth for types lives in `docs/2-contracts-and-interfaces/internal-mesh-types/`. Read those before proposing changes or explaining architecture.
- **Cite sources.** Reference specific struct names and file paths when discussing architecture.
- **Single spatial authority.** Each entity has exactly one authoritative Arbiter per tick. No shared mutable state between actors.
- **Read whole files.** If a file read truncates, paginate through the rest before drawing conclusions.

## Project Tracking

**`memory-bank/`** contains project-level coordination files — progress status, architecture decisions, implementation roadmap, and session handoff context. Start with `memory-bank/SUMMARY.md` for a quick orientation on where the project stands. See `memory-bank/README.md` for file descriptions and update guidelines.

**Keep `memory-bank/` current.** At the end of each turn, if your work changed project state (resolved a gap, wrote code, made a decision, shifted priorities), update the relevant `memory-bank/` file. At minimum: `ACTIVE_WORK.md` for progress changes, `DECISIONS.md` for architectural choices, `SESSION_HANDOFF.md` at the end of significant sessions.

## Branches

- `docs` — main branch
- `engine_docs` — active working branch for documentation extraction and refinement
