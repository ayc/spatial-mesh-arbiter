# Project Context

This is the specification repository for the Spatial Mesh Arbiter — a lock-free, deterministic, 60Hz distributed game engine for massive-scale multiplayer (4,000+ players).

## Documentation Layers and Precedence

There are three documentation directories with a strict precedence hierarchy:

1. **`docs-core/`** (highest authority) — The game-agnostic engine contract. Reusable runtime rules for time, space, topology, transport, and conformance. This layer is fully mature with zero TODOs or placeholders.

2. **`docs-game-compiler/`** — Designer-facing game definition model and compiler toolchain. Targets `docs-core/` contracts. The Lua authoring specs (01-x files) are production-quality; the compilation pipeline (02-07) is still skeletal.

3. **`docs/`** (reference implementation) — An ARPG (Diablo-style MMO) built on the framework. The original monolithic spec from which the other two layers are being extracted. Architecture and wire protocol docs are strong; combat math and testing specs have significant gaps (24/29 tracked gaps still open in `docs/6-spec-drafts/GAPS_CHECKLIST.md`).

**If any layer conflicts with `docs-core/`, `docs-core/` wins.**

## Origin Story

`docs/` was written first as a single game server specification. The realization that a reusable engine was embedded inside it led to the creation of `docs-core/` (extracted engine contracts) and `docs-game-compiler/` (tooling layer between engine and game content). The extraction is ongoing — `docs-core/06-architecture-section-mapping.md` is the active roadmap, mapping every section of `docs/1-architecture/` to a disposition: `retain-core`, `split`, or `move-template`.

## Key Rules

- **No floating-point math** in the simulation loop. Use `I32F32` (SimFixed) from the `fixed` crate with saturating arithmetic.
- **60Hz tick rate is non-negotiable.** Load adaptation happens via kinematic dilation, never by dropping frames.
- **Verify with structs.** The source of truth for types lives in `docs/2-contracts-and-interfaces/internal-mesh-types/`. Read those before proposing changes.
- **Cite sources.** Reference specific struct names and file paths when discussing architecture.
- **Single spatial authority.** Each entity has exactly one authoritative Arbiter per tick. No shared mutable state between actors.

## Branches

- `docs` — main branch
- `engine_docs` — active working branch for documentation extraction and refinement
