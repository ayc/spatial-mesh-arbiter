# Active Work

> Last Updated: 2026-04-04

## In Progress

- **[Spec] 12 gap drafts awaiting review/promotion** — Tier 1-4 drafts need final review and promotion into canonical `docs/` sections. (`docs/6-spec-drafts/GAPS_CHECKLIST.md`)
- **[Implementation] Complete Phase 1 foundation** — `shared-types` still needs SimFixed wrappers, baseline profile constants, and fixed-point `CollisionGeometry` primitives. (`memory-bank/ENGINE_ROADMAP.md`)

## Up Next

- **Promote Tier 1 review items** — T1-01 (Stat Compilation), T1-02 (Distance Falloff), T1-05 (Stat Caps) are the most implementation-relevant of the 12 pending reviews.
- **Add baseline profile constants** — Encode tick rate, ingress budgets, and replay horizons from `docs-core/00-1-core-baseline-profile.md` into `shared-types`.
- **Decide extraction kickoff timing** — `docs-core/06-architecture-section-mapping.md` is complete, but extraction execution is still deferred until it becomes the critical path for the game adapter boundary.

## Blocked

- **Layer extraction** — Mapped in `docs-core/06-architecture-section-mapping.md` but execution hasn't started. Not blocking implementation yet (docs-core contracts are self-standing), but will matter once game adapter work begins.

## Recently Completed

- Set up `memory-bank/` tracking files and populated the initial dashboard, roadmap, and decision log
- Drafted `ENGINE_ROADMAP.md` with the 6-phase engine-first build order
- Reconciled memory-bank drift against the current repository state
- Moved scratch files (`chunk_*`, `aggregated_text.txt`, `*.py` scripts) into `_scratch/`
- Updated `CLAUDE.md` to reflect accurate docs-game-compiler maturity
- Added status/scope notes to `02-implementation-phases.md` and `GAPS_CHECKLIST.md`
- Deep analysis of `docs-game-compiler/` completeness (identified 06/07 as the only skeletal files)
