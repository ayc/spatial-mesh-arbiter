# Session Handoff

> Context for the next LLM session to pick up without re-deriving state.

---

## 2026-04-04 — CG-07 temporal/reactivation state canonically resolved

### What was accomplished
- Added canonical compiler support for hold-release abilities, ordered same-key reactivation, bookmarks, rewind buffers, combo windows, shared charge pools, and next-cast / first-hit consumption windows.
- Extended `docs-game-compiler/02-schema-and-validation.md` with `InputModeBlock`, `ActivationModes`, `RuntimeStateDefinition`, runtime-state effects/refs, and status-owned `snapshot_recorder_state` / `consumption_window` metadata.
- Extended `docs-game-compiler/03-1-compiler-ir-specification.md` so activation modes redirect to hidden compiled variants, runtime-state ops live in the IR scheduler, and hold-release stays on the existing discrete-cast plus continuous-button-state ingress contract.
- Extended `docs-game-compiler/04-game-image-format.md` with `InputMode_Wire`, `ActivationMode_Wire`, runtime-state op encoding, `ConsumptionWindowBlock_Wire`, and a canonical runtime-state table/index under `StaticDataTables`.
- Updated `docs-game-compiler/01-2-lua-whitelisted-api.md` so the procedural fallback surface now mirrors the new runtime-state predicates and mutation effects.
- Updated the compatibility audit to mark `CG-07` resolved, re-score the affected sketches, and reclassify `SK-12 Spell Echo` onto `CG-08` because its remaining gap is bounded recursive repeat policy rather than temporal state.
- Updated `memory-bank/SUMMARY.md`, `ACTIVE_WORK.md`, and `DECISIONS.md` to reflect the new compiler-contract state.

### What was left incomplete
- This resolved the canonical compiler contract, not the sketch-local closure pass. Batch 1 sketch closure is still open for `SK-24`, `SK-29`, `SK-35`, and `SK-108`.
- The next highest-leverage unresolved compiler gaps are now `CG-16`, `CG-11`, `CG-02`, and the tied 7-sketch families `CG-05`, `CG-06`, `CG-10`, `CG-12`, `CG-13`, and `CG-14`.

### Key discoveries
- The real stateful-ability gap was one shared runtime-state model, not a dozen bespoke mechanics.
- Hold-release could be closed without widening the external intent taxonomy; the existing discrete-cast plus continuous-button-state contract was enough.
- `SK-12 Spell Echo` was mis-bucketed under `CG-07`; after the state-model work landed, its real remaining blocker is recursive repeat/termination policy (`CG-08`).
- The audit snapshot is now: 1 `Complete`, 43 `Supported`, 32 `Partial`, 49 `Blocked`.

---

## 2026-04-04 — CG-03 advanced CC lifecycle canonically resolved

### What was accomplished
- Added canonical CC behavior profiles to `docs-game-compiler/02-schema-and-validation.md` for `stun`, `root`, `silence`, `sleep`, `disarm`, `blind`, `fear`, `charm`, `taunt`, `berserk`, and `mute`.
- Added explicit `duration_scaling`, `apply_cc.on_expire_effects`, and `StatusEffectDefinition.cc_immunity_categories` so tenacity-like duration reduction, post-CC immunity windows, and super-armor style buffs are represented in the canonical compiler surface.
- Added deterministic CC admission/enforcement ordering to `docs-game-compiler/03-1-compiler-ir-specification.md`, including blind miss timing, taunt/berserk target override, sleep break-on-damage, mute passive suspension, and categorical immunity checks.
- Extended `docs-game-compiler/04-game-image-format.md` with wire-level `duration_scaling`, `cc_behavior_profile`, and `cc_immunity_mask`.
- Updated the compatibility audit to mark `CG-03` resolved and promoted 14 sketches from `Partial`/`Blocked` to `Supported`.
- Updated `memory-bank/SUMMARY.md`, `ACTIVE_WORK.md`, and `DECISIONS.md` to reflect the new compiler-contract state.

### What was left incomplete
- This resolved the canonical compiler contract, not the sketch-local cleanup pass. Batch 1 sketch closure is still open for `SK-24`, `SK-29`, `SK-35`, and `SK-108`.
- The next highest-leverage unresolved compiler gaps are now `CG-07`, `CG-16`, `CG-11`, and `CG-02`.

### Key discoveries
- The core CC gap was mostly a policy gap, not a primitive gap.
- `apply_cc` needed a runtime behavior-profile concept more than it needed dozens of bespoke authoring fields.
- Slow-style control effects are best treated as ordinary negative statuses with `cc_category` plus `duration_scaling`, not as a separate `apply_cc` profile.

---

## 2026-04-04 — Full sketch/compiler compatibility audit added

### What was accomplished
- Added `docs-game-compiler/ability-sketches/COMPILER_COMPATIBILITY_CHECKLIST.md` as a full-pass audit over all 125 sketches.
- Added `docs-game-compiler/ability-sketches/COMPILER_GAP_REGISTER.md` to group repeated missing compiler contracts instead of repeating them per sketch.
- Linked the new audit artifacts from `docs-game-compiler/ability-sketches/README.md` and clarified in `COMPLETION_CHECKLIST.md` that closure-tracking and compatibility-auditing are separate layers.
- Updated `memory-bank/SUMMARY.md` and `memory-bank/ACTIVE_WORK.md` so the repo-level status now reflects the compiler audit result.

### What was left incomplete
- The audit is diagnostic only. No new canonical compiler contracts were added in this session.
- Sketch-closure Batch 1 is still open for `SK-24`, `SK-29`, `SK-35`, and `SK-108`.

### Key discoveries
- The primitive taxonomy is stronger than the sketch TODO count alone suggests: 19 sketches are already `Supported` by the current canonical compiler docs, plus `SK-15` is `Complete`.
- The real blockers are concentrated in a smaller set of repeated gap families: advanced CC lifecycle (`CG-03`), temporal/reactivation state (`CG-07`), special non-HP resolution rules (`CG-16`), and control-topology/loadout authoring (`CG-11`).
- The full audit snapshot is now: 1 `Complete`, 19 `Supported`, 47 `Partial`, 58 `Blocked`.

---

## 2026-04-04 — SK-15 Purify closed

### What was accomplished
- Closed `docs-game-compiler/ability-sketches/sk-15-purify.md` by removing its TODO sections and replacing them with resolved cross-boundary and compiler requirements.
- Added canonical compiler/docs support for Purify's required semantics:
  - `cleanse` effect type in `02-schema-and-validation.md`
  - explicit `StatusEffectDefinition.polarity`
  - explicit `status_application_immunity`
  - `apply_cc.is_cleansable`
  - `P-66 Status Effect Filter Mutation`
- Updated `04-game-image-format.md` and `03-1-compiler-ir-specification.md` so the schema, wire format, and stage model agree on status filtering and immunity behavior.
- Updated `memory-bank/ACTIVE_WORK.md` and `memory-bank/DECISIONS.md` to reflect the new docs-side contract and progress.

### What was left incomplete
- Sketch-closure Batch 1 is still in progress. Remaining first-batch sketches: `SK-24`, `SK-29`, `SK-35`, `SK-108`.
- No attempt was made to propagate `P-66` into other existing sketch compositions yet; only `SK-15` was closed in this session.

### Key discoveries
- Purify could not be closed cleanly without elevating cleanse semantics into the canonical compiler docs.
- The main missing contract was not "how to remove debuffs" but "how the compiler classifies statuses and how the runtime blocks new status admissions during immunity windows."

---

## 2026-04-04 — Ability sketch closure queue added

### What was accomplished
- Added `docs-game-compiler/ability-sketches/COMPLETION_CHECKLIST.md` to define what "designer-recreatable with the compiler" means for a sketch.
- Added an explicit priority queue for sketch closure, with Priority A/B/C buckets and an immediate first batch.
- Linked the new checklist from `docs-game-compiler/ability-sketches/README.md`.
- Updated `memory-bank/ACTIVE_WORK.md` so the sketch-closure batch is visible as upcoming docs work.

### What was left incomplete
- No individual sketch was closed in this session; the work here was tracker/process setup only.
- The 125 sketch files still contain the same TODO backlog; this change only makes the closure order explicit.

### Key discoveries
- The sketch set already has primitive-chain coverage, but that is not the same thing as compiler-ready closure.
- The highest-leverage first batch is `SK-15`, `SK-24`, `SK-29`, `SK-35`, and `SK-108` because those five force answers for status classification, CC semantics, zone authoring, teleport semantics, and resource-targeting combat.

---

## 2026-04-04 — Tracking guidance clarified

### What was accomplished
- Updated `memory-bank/README.md` to explicitly state that `memory-bank/` is an orientation/status layer, not implementation authority.
- Updated `AGENTS.md` to require agents to read the relevant spec docs before proposing architecture, explaining contracts, or writing code.

### What was left incomplete
- The underlying implementation/spec status is unchanged; this session only clarified process guidance.

### Key discoveries
- The repo already implied this rule, but it was not explicit enough in either `memory-bank/README.md` or `AGENTS.md`.

---

## 2026-04-04 — Memory-bank reconciliation

### What was accomplished
- Audited `memory-bank/` against the actual repository state and corrected stale status claims.
- Updated `SUMMARY.md` to reflect the current `shared-types` test count (8 passing tests) and the remaining Phase 1 scope.
- Updated `ACTIVE_WORK.md` to remove already-completed setup/roadmap tasks and replace them with the actual in-flight implementation priorities.
- Added this handoff entry so the latest session state is immediately visible at the top of the file.

### What was left incomplete
- The 12 REVIEW-status gap drafts in `docs/6-spec-drafts/GAPS_CHECKLIST.md` still need promotion into canonical docs.
- Layer extraction (per `docs-core/06-architecture-section-mapping.md`) still has not started.
- Phase 1 implementation is still incomplete: `shared-types` needs SimFixed wrappers, baseline profile constants, and fixed-point collision geometry.
- ~~`docs/0-getting-started/02-implementation-phases.md` still says the replacement engine roadmap is pending; that drift remains outside `memory-bank/`.~~ Fixed: now points to `memory-bank/ENGINE_ROADMAP.md`.

### Key discoveries
- `cargo test -p shared-types` currently passes 8 tests, not 7.
- The Rust workspace still contains exactly one crate: `crates/shared-types`.
- The authoritative engine build sequence now lives in `memory-bank/ENGINE_ROADMAP.md`; any tracker claiming it is still pending is stale.

---

## 2026-04-04 — Project orientation, cleanup, and memory-bank creation

### What was accomplished
- Reviewed full project status across all three workstreams (spec, extraction, implementation).
- Cleaned up project root: moved `chunk_aa`/`ab`/`ac`, `aggregated_text.txt`, `parse_sketches.py`, and 10 one-shot refactoring `.py` scripts into `_scratch/`.
- Deep analysis of `docs-game-compiler/`: confirmed 01-x files and ability-primitives are production-quality, 02-05 are substantial drafts (not skeletal as CLAUDE.md claimed), only 06 (18 lines) and 07 (23 lines) are genuinely skeletal. 125 ability sketches have ~290 systematic TODOs in Cross-Boundary Concerns and Compiler Requirements sections.
- Updated `CLAUDE.md` to reflect accurate maturity of each layer.
- Added status notes to `docs/0-getting-started/02-implementation-phases.md` (marked §2 as superseded, §1 and §3 still valid) and `docs/6-spec-drafts/GAPS_CHECKLIST.md` (scoped to ARPG layer only).
- Created `memory-bank/` directory with tracking files.
- Created root `.gitignore` (was entirely missing).

### What was left incomplete
- At the end of that session, `memory-bank/ENGINE_ROADMAP.md` had not yet been populated with engine-first build phases mapped to `docs-core/` contracts. This was completed later the same day.
- At the end of that session, `memory-bank/DECISIONS.md` had not yet been seeded with the initial architecture decisions. This was completed later the same day.
- At the end of that session, `memory-bank/SUMMARY.md` had not yet been written as the entry-point dashboard. This was completed later the same day.
- The 12 REVIEW-status gap drafts in `GAPS_CHECKLIST.md` still need promotion into canonical docs.
- Layer extraction (per `06-architecture-section-mapping.md`) hasn't started.

### Key discoveries
- `crates/shared-types` is the only implementation code. Contains `PipelineStageId` (12-stage enum), `DispatchStageId` (11-stage subset excluding IntentValidation), `DeferredTargetStageId` (Stage 3 and 7 only), and `DeferredEvent<TPayload>`. It was at 7 passing tests at the end of that session; the current count is 8.
- The chunk files were output from `parse_sketches.py` which scraped ability sketch Observable Behavior sections. The Rust pseudocode in `chunk_aa`/`ab` was a narrative sketch, not compilable code, and has no relationship to `crates/shared-types`.
- `GEMINI.md` still references "Redis Streams Event Bus" — this was superseded by the Redpanda decision (T2-07). May need updating.
- `docs/0-getting-started/02-implementation-phases.md` defines valid crate mandates (§1) and constraints (§3) but its build phases (§2) target the ARPG, not the engine.
