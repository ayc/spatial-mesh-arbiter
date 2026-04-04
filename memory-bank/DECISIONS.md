# Architecture Decision Log

> Reverse-chronological. Records the "why" behind choices that aren't self-evident from specs or code.

---

## 2026-04 — Runtime states plus hidden activation variants for stateful abilities

**Context:** The sketch audit showed a shared compiler gap across reactivation abilities,
rewinds, combo-step routing, charge systems, and "next cast / first hit" windows. The missing piece
was not primitive availability alone; it was the lack of one canonical state model connecting
authoring, IR lowering, runtime storage, and wire format.

**Decision:** Model these mechanics as bounded per-entity runtime states plus ordered
`ActivationModes` that redirect the public ability entry to hidden compiled variants. Keep
hold-release abilities on the existing discrete-cast plus continuous-button-state ingress contract.
Represent rewind recording and one-shot empower/counter windows as status-owned metadata
(`snapshot_recorder_state` and `consumption_window`) instead of bespoke sketch-local behavior.

**Alternatives:** Keep reactivation/combo/charge behavior sketch-local; add one-off special cases
per ability family; introduce new external client intent variants for hold-release abilities.

**Rationale:** This keeps the compiler surface bounded and reusable. Hidden variants let same-key
reactivation and combo routing swap targeting/effects cleanly without mutating one IR block in
place. Runtime-state tables give bookmarks, rewind buffers, sequence windows, and charge pools one
shared authoritative storage model that survives handoff. Preserving the existing intent taxonomy
avoids widening the trust boundary just to support charged abilities.

---

## 2026-04 — Canonical CC behavior profiles and status-immunity contract in compiler docs

**Context:** The full 125-sketch compatibility audit showed that the compiler had baseline `apply_cc`
coverage, but core CC mechanics were still only partially specified. Stun, root, silence, sleep,
blind, taunt, berserk, mute, and partial/full super-armor all depended on implied behavior that
was not yet a canonical compiler/runtime contract.

**Decision:** Treat supported crowd-control types as canonical behavior profiles lowered into
generated status metadata. Add explicit duration-scaling policy, status-authored category immunity,
CC expiry follow-ups, deterministic CC admission/enforcement ordering, and wire-level CC behavior /
immunity fields.

**Alternatives:** Keep CC behavior sketch-local; add one-off special cases per ability; model all
control effects as arbitrary custom status logic instead of stable compiler-supported profiles.

**Rationale:** The repeated gap was not primitive availability; it was missing canonical policy.
Making CC behavior profile-driven keeps the authoring surface compact, lets the runtime enforce
blind/taunt/berserk/mute/fear/charm deterministically without bespoke per-ability code paths, and
gives designers a stable way to express super-armor / immunity windows through ordinary status
authoring instead of undocumented engine flags.

---

## 2026-04 — Engine-first build order

**Context:** The original `02-implementation-phases.md` defined a 5-phase roadmap building the ARPG directly (shared-types → controller → arbiter → edge → swarm-tester). Meanwhile, the engine extraction into `docs-core/` produced a complete, game-agnostic contract layer.

**Decision:** Build the engine layer (`docs-core/` contracts) first, then layer the ARPG on top via the game adapter interface.

**Alternatives:** Continue with ARPG-first phases; build both in parallel.

**Rationale:** `docs-core/` is fully mature with zero TODOs — it's the most implementation-ready layer. Building engine-first validates the reusable architecture before committing to game-specific decisions. The game adapter boundary (`docs-core/04-*`) is explicitly designed to allow any game to plug in, so the ARPG becomes just one consumer. Building ARPG-first would have baked game-specific assumptions into engine code that would later need extraction — the same problem the spec already went through.

---

## 2026-04 — Explicit status polarity and cleanse contract in compiler docs

**Context:** The ability sketch set had broad primitive coverage, but `SK-15 Purify` exposed a missing canonical contract. The compiler docs had `apply_buff`, `apply_debuff`, `apply_cc`, and `StatusEffectDefinition`, but no explicit status polarity model, no first-class `cleanse` effect, and no documented way to express a temporary "block new debuffs" immunity window.

**Decision:** Add explicit `polarity` and `status_application_immunity` to `StatusEffectDefinition`, add `is_cleansable` to `apply_cc`, add a first-class `cleanse` effect schema, and introduce `P-66 Status Effect Filter Mutation` in the primitive taxonomy.

**Alternatives:** Keep cleanse semantics sketch-local; infer polarity from `apply_buff`/`apply_debuff` only; treat crowd control as a special case outside the generic status registry.

**Rationale:** Designer-recreatable ability docs require more than primitive chains. Cleanse/dispel behavior depends on canonical metadata that the compiler can validate and the runtime can evaluate deterministically. Making polarity and cleanse policy explicit removes ad hoc tag matching, lets generated CC statuses participate in the same runtime rules as ordinary debuffs, and provides a reusable contract for future dispels, buff strips, and temporary status-immunity windows.

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
