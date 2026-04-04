# Active Work

> Last Updated: 2026-04-04

## In Progress

- **[Spec] 12 gap drafts awaiting review/promotion** — Tier 1-4 drafts need final review and promotion into canonical `docs/` sections. (`docs/6-spec-drafts/GAPS_CHECKLIST.md`)
- **[Implementation] Complete Phase 1 foundation** — `shared-types` still needs SimFixed wrappers, baseline profile constants, and fixed-point `CollisionGeometry` primitives. (`memory-bank/ENGINE_ROADMAP.md`)
- **[Docs] Resolve compiler gaps identified by the full compatibility audit** — All 125 ability sketches are now classified in `COMPILER_COMPATIBILITY_CHECKLIST.md`; `CG-03` and `CG-07` are resolved, and the grouped unresolved compiler backlog now centers on `CG-16`, `CG-11`, `CG-02`, plus the 7-sketch families `CG-05`, `CG-06`, `CG-10`, `CG-12`, `CG-13`, and `CG-14`. (`docs-game-compiler/ability-sketches/COMPILER_COMPATIBILITY_CHECKLIST.md`)
- **[Docs] Sketch-closure Batch 1 underway** — `SK-15 Purify` is closed; `SK-24 Stun`, `SK-29 Blizzard`, `SK-35 Blink Strike`, and `SK-108 Mana Burn` remain in the first batch. (`docs-game-compiler/ability-sketches/COMPLETION_CHECKLIST.md`)

## Up Next

- **Promote Tier 1 review items** — T1-01 (Stat Compilation), T1-02 (Distance Falloff), T1-05 (Stat Caps) are the most implementation-relevant of the 12 pending reviews.
- **Add baseline profile constants** — Encode tick rate, ingress budgets, and replay horizons from `docs-core/00-1-core-baseline-profile.md` into `shared-types`.
- **Close the highest-leverage compiler gaps from the audit** — Continue with `CG-16` (special non-HP resolution rules), `CG-11` (control topology/loadout authoring), `CG-02` (channel/maintained-cast lifecycle), then the tied 7-sketch families `CG-05`, `CG-06`, `CG-10`, `CG-12`, `CG-13`, and `CG-14`. (`docs-game-compiler/ability-sketches/COMPILER_GAP_REGISTER.md`)
- **Continue sketch-closure Batch 1** — Close `SK-24 Stun`, `SK-29 Blizzard`, `SK-35 Blink Strike`, and `SK-108 Mana Burn` so the compiler docs have a reliable baseline set of designer-recreatable references.
- **Decide extraction kickoff timing** — `docs-core/06-architecture-section-mapping.md` is complete, but extraction execution is still deferred until it becomes the critical path for the game adapter boundary.

## Blocked

- **Layer extraction** — Mapped in `docs-core/06-architecture-section-mapping.md` but execution hasn't started. Not blocking implementation yet (docs-core contracts are self-standing), but will matter once game adapter work begins.

## Recently Completed

- Set up `memory-bank/` tracking files and populated the initial dashboard, roadmap, and decision log
- Drafted `ENGINE_ROADMAP.md` with the 6-phase engine-first build order
- Reconciled memory-bank drift against the current repository state
- Added `docs-game-compiler/ability-sketches/COMPLETION_CHECKLIST.md` to define sketch-completion criteria and a prioritized closure queue
- Added `COMPILER_COMPATIBILITY_CHECKLIST.md` and `COMPILER_GAP_REGISTER.md` to audit all 125 sketches against the current compiler surface
- Closed `SK-15 Purify` by adding canonical compiler/docs support for cleanse filtering, status polarity, and status-application immunity
- Resolved `CG-03` canonically by adding CC behavior profiles, duration scaling, status-based CC immunity, and deterministic admission/enforcement ordering
- Resolved `CG-07` canonically by adding runtime-state definitions, activation-mode hidden variants, hold-release input-mode contracts, and status-owned consumption windows
- Moved scratch files (`chunk_*`, `aggregated_text.txt`, `*.py` scripts) into `_scratch/`
- Updated `CLAUDE.md` to reflect accurate docs-game-compiler maturity
- Added status/scope notes to `02-implementation-phases.md` and `GAPS_CHECKLIST.md`
- Deep analysis of `docs-game-compiler/` completeness (identified 06/07 as the only skeletal files)
