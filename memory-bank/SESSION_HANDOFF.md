# Session Handoff

> Live checkpoint only.
> For chronological history and milestone summaries, see `memory-bank/work-log/`.

---

## 2026-04-05 — Current Checkpoint

- `docs-core/` remains the top authority. `memory-bank/` is orientation-only; agents must still
  read the relevant spec docs before proposing behavior or writing code.
- The `docs-game-compiler` sketch workstream is fully closed:
  - `COMPILER_COMPATIBILITY_CHECKLIST.md` is `125 Complete / 0 Supported / 0 Partial / 0 Blocked`
  - `COMPLETION_CHECKLIST.md` and `COMPILER_GAP_REGISTER.md` are now historical closed artifacts
- The active project queues are now:
  - promote the 12 `REVIEW` drafts in `docs/6-spec-drafts/`
  - complete Phase 1 `shared-types` work: SimFixed wrappers, baseline profile constants, and
    fixed-point `CollisionGeometry`
  - keep layer extraction deferred until the game-adapter boundary becomes the critical path
- Current engine status:
  - only `crates/shared-types` exists
  - `cargo test -p shared-types` passes with 8 tests
- Tracking layout is now:
  - `SESSION_HANDOFF.md` = live checkpoint
  - `memory-bank/work-log/` = historical session chronology
  - `memory-bank/DECISIONS.md` = working decision index
  - `adr/compiler/` and `adr/engine/` = durable architecture decision records
- First ADR promotion pass completed:
  - `ADR-0001` through `ADR-0007` now hold the most durable cross-cutting compiler decisions
  - `DECISIONS.md` remains the working index for decisions that have not yet been promoted
- Worktree note:
  - the branch is docs-heavy and very dirty
  - `.obsidian/workspace.json` is also modified and appears unrelated to engine/compiler docs

## Next Recommended Work

1. Promote Tier 1 review items in `docs/6-spec-drafts/`: Stat Compilation, Distance Falloff, Stat Caps.
2. Add baseline profile constants to `crates/shared-types` from `docs-core/00-1-core-baseline-profile.md`.
3. Decide when to start the extraction moves defined in `docs-core/06-architecture-section-mapping.md`.
