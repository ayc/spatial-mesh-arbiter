# Project Status Summary

> Last Updated: 2026-04-05

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

## Workstream 4: Compiler Compatibility Audit

The full 125-sketch compatibility audit is now recorded under `docs-game-compiler/ability-sketches/`. Current snapshot: all 125 sketches are `Complete`; there are no remaining `Supported`, `Partial`, or `Blocked` entries. `CG-03` (advanced CC lifecycle and target-control policy), `CG-07` (reactivation / temporal-state / charge-state authoring), `CG-16` (special non-HP resolution rules), `CG-11` (control topology / identity swap / multi-owner loadout authoring), `CG-02` (channel / maintained-cast / concentration lifecycle), `CG-01` (cross-boundary snap / target-side authority matrix), `CG-04` (persistent linkage / redirection / event cloning authoring), `CG-05` (zone actor lifecycle variants), `CG-06` (dynamic geometry / sweep-volume authoring), `CG-08` (recursive / bounded reactive propagation), `CG-09` (spawned actor lifecycle and split-form control projection), `CG-10` (visibility / targetability / suspension authoring), `CG-12` (containment / instance topology), `CG-13` (post-terminal respawn-route override), `CG-14` (advanced projectile lifecycle mutation), `CG-15` (group aggregator / cooperative-input authoring), `CG-17` (controller-escalated global-event execution), `CG-18` (combo-field replacement context), `CG-19` (controlled-shell teardown callbacks), `CG-20` (late-bound spawned-actor directed transit), `CG-21` (projectile-side multi-target carry), and `CG-22` (shield absorb callbacks plus live resource-backed offense scaling) all remain resolved canonically. The compiler-gap register is fully closed, and the sketch-closure tracker is now fully exhausted; remaining docs work has shifted back to spec promotion, extraction, and compiler-doc polish outside the sketch corpus.

**Tracker:** [`docs-game-compiler/ability-sketches/COMPILER_COMPATIBILITY_CHECKLIST.md`](../docs-game-compiler/ability-sketches/COMPILER_COMPATIBILITY_CHECKLIST.md), [`docs-game-compiler/ability-sketches/COMPILER_GAP_REGISTER.md`](../docs-game-compiler/ability-sketches/COMPILER_GAP_REGISTER.md)

---

## Key Blockers

- **12 REVIEW items need promotion** — These are complete drafts sitting in `docs/6-spec-drafts/` that need to be folded into their canonical target docs. Not blocking implementation directly, but blocks closing out the spec workstream.
- **Layer extraction not started** — Not blocking engine implementation yet (`docs-core/` contracts are self-standing), but will matter when Phase 5 (game adapter interface) needs a clean engine/game boundary.
- **No open compiler-gap families remain** — The sketch/compiler compatibility backlog is fully
  canonicalized. Remaining docs work is closure/editorial, not missing compiler-contract discovery.
