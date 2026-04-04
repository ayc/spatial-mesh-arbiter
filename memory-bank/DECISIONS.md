# Architecture Decision Log

> Reverse-chronological. Records the "why" behind choices that aren't self-evident from specs or code.

---

## 2026-04 — Engine-first build order

**Context:** The original `02-implementation-phases.md` defined a 5-phase roadmap building the ARPG directly (shared-types → controller → arbiter → edge → swarm-tester). Meanwhile, the engine extraction into `docs-core/` produced a complete, game-agnostic contract layer.

**Decision:** Build the engine layer (`docs-core/` contracts) first, then layer the ARPG on top via the game adapter interface.

**Alternatives:** Continue with ARPG-first phases; build both in parallel.

**Rationale:** `docs-core/` is fully mature with zero TODOs — it's the most implementation-ready layer. Building engine-first validates the reusable architecture before committing to game-specific decisions. The game adapter boundary (`docs-core/04-*`) is explicitly designed to allow any game to plug in, so the ARPG becomes just one consumer. Building ARPG-first would have baked game-specific assumptions into engine code that would later need extraction — the same problem the spec already went through.

---

## 2026-03 — Redpanda over Redis Streams for event bus

**Context:** The spec originally referenced Redis Streams for the Meta Services event bus. No production traffic existed yet.

**Decision:** Adopt Redpanda (Kafka API) as the day-1 event bus. Redis retained only for Session Manager registry/caching.

**Alternatives:** Redis Streams; dual-write with cutover plan.

**Rationale:** Redpanda provides durability (`acks=all`, idempotent producers), at-least-once delivery with consumer-side idempotency, strict FIFO ordering per partition, and DLQ support — all required by the durability bridge contract. Since there's no live traffic, a dual-write cutover was unnecessary complexity. Redpanda's topic/partition/offset semantics also align directly with the replay/spectator/event-spine architecture planned for phase 2. See `docs/6-spec-drafts/tier-2-contracts/07-redpanda-adoption-adr.md` for the full ADR.

---

## 2026-03 — `no_std` for shared-types crate

**Context:** `shared-types` defines the foundational type vocabulary (stage IDs, deferred events, entity IDs) shared across all engine crates.

**Decision:** Build `shared-types` as `#![no_std]` with `#[cfg(test)] extern crate std`.

**Alternatives:** Standard `std` crate; `no_std` with alloc.

**Rationale:** The Arbiter's 60Hz loop is the most constrained execution context in the system. Keeping the shared type crate `no_std` ensures these types never accidentally pull in allocating or blocking operations. It also keeps the door open for embedded or WASM targets if the engine is ever ported. Test code uses `std` for convenience (Vec in assertions, etc.) without contaminating the library.

---

## 2026-03 — Single-threaded Tokio for Arbiter

**Context:** The Arbiter runs a deterministic 60Hz simulation loop with strict no-shared-mutable-state invariants.

**Decision:** Use single-threaded Tokio runtime for the Arbiter process. Multi-threaded Tokio for Controller and Edge nodes.

**Alternatives:** Multi-threaded Tokio everywhere; custom event loop without Tokio.

**Rationale:** The Arbiter's lock-free invariant means no mutexes or RwLocks inside the tick loop. A multi-threaded runtime would require synchronization primitives that violate this constraint. Single-threaded Tokio gives async I/O (for network ingress/egress between ticks) without introducing shared-state concurrency. Controller and Edge have no determinism requirement, so multi-threaded runtime is fine there. Mandated in `docs/0-getting-started/02-implementation-phases.md` §1.2.

---

## 2026-02 — Layer extraction from monolithic spec

**Context:** `docs/` started as a single ARPG server specification. During development it became clear that a reusable distributed game engine was embedded inside the ARPG-specific design.

**Decision:** Extract the engine contracts into `docs-core/` and the compiler/tooling layer into `docs-game-compiler/`, leaving `docs/` as the ARPG reference implementation.

**Alternatives:** Keep everything in `docs/` with section tags; create a separate repo for the engine.

**Rationale:** The monolithic spec mixed engine invariants (spatial authority, 60Hz tick, determinism) with game-specific design (loot tables, talent trees, quest systems). This made it impossible to reason about which rules were universal vs. ARPG-specific. Extraction into layers with a strict precedence hierarchy (`docs-core/` wins on conflicts) cleanly separates concerns. A separate repo was rejected because the layers are tightly co-evolving during the design phase — the extraction mapping (`docs-core/06-architecture-section-mapping.md`) requires reading both simultaneously.
