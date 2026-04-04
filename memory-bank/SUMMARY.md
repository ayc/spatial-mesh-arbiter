# Project Status Summary

> Last Updated: 2026-04-04

---

## Workstream 1: ARPG Spec Completion

17 of 30 tracked gaps are resolved. 12 are in REVIEW status awaiting promotion into canonical `docs/` sections. 1 deferred to phase 2 (T2-06: Surrogate Recovery). No gaps are OPEN or DRAFTING — all design work is done, the remaining effort is editorial promotion.

**Tracker:** [`docs/6-spec-drafts/GAPS_CHECKLIST.md`](../docs/6-spec-drafts/GAPS_CHECKLIST.md)

---

## Workstream 2: Layer Extraction

The section-by-section mapping of `docs/1-architecture/` into `docs-core/` dispositions (`retain-core`, `split`, `move-template`) is complete. No extraction moves have been executed yet. The recommended order is: (1) move `04-meta-services.md` game domains out, (2) split `01-core-concepts-and-mesh.md`, (3) normalize protocol docs, (4) keep `03-mesh-controller.md` and `07-framework-boundary.md` as core baselines.

**Tracker:** [`docs-core/06-architecture-section-mapping.md`](../docs-core/06-architecture-section-mapping.md)

---

## Workstream 3: Engine Implementation

Early Phase 1. `crates/shared-types` exists with stage ID enums, deferred event types, and `EntityId` — all `#![no_std]`, 8 passing tests as of 2026-04-04. No other crates exist. SimFixed wrappers, baseline profile constants, and CollisionGeometry math are the remaining Phase 1 items. The full 6-phase build sequence is defined in the engine roadmap.

**Tracker:** [`memory-bank/ENGINE_ROADMAP.md`](ENGINE_ROADMAP.md)

---

## Key Blockers

- **12 REVIEW items need promotion** — These are complete drafts sitting in `docs/6-spec-drafts/` that need to be folded into their canonical target docs. Not blocking implementation directly, but blocks closing out the spec workstream.
- **Layer extraction not started** — Not blocking engine implementation yet (`docs-core/` contracts are self-standing), but will matter when Phase 5 (game adapter interface) needs a clean engine/game boundary.
