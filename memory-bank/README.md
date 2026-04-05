# memory-bank/

Project-level coordination layer. Tracks meta-progress, decisions, and session context across the three workstreams (spec completion, layer extraction, engine implementation). These are **not** spec documents — they describe *where the project stands*, not *what the project is*.

Agents should use `memory-bank/` for orientation, then read the relevant authoritative spec documents before making code, design, or architecture changes.

## Files

| File | Purpose | Update Frequency |
|------|---------|-----------------|
| `SUMMARY.md` | Start here. Status across all workstreams with links to authoritative trackers. | When workstream status changes |
| `ACTIVE_WORK.md` | What's in flight, what's next, what's blocked. | Start/end of each working session |
| `ENGINE_ROADMAP.md` | 6-phase implementation plan aligned to `docs-core/` contracts. | When phases complete or scope changes |
| `DECISIONS.md` | Working decision index and ADR-promotion queue for non-obvious choices. | When a significant decision is made |
| `SESSION_HANDOFF.md` | Live checkpoint for the next LLM session; should stay short and current. | End of each significant session |
| `work-log/` | Historical session chronology and milestone summaries. | Append after significant sessions |

## Related Directories

| Path | Purpose |
|------|---------|
| `../adr/` | Durable architecture decision records. Use `../adr/compiler/` for compiler/ability-surface ADRs and `../adr/engine/` for runtime/engine ADRs. |

## Rules

- **Reference, don't duplicate.** Link to `GAPS_CHECKLIST.md`, `06-architecture-section-mapping.md`, etc. — don't copy their content here.
- **Orientation, not authority.** `memory-bank/` is a status layer, not an implementation contract. Before proposing behavior changes or writing code, read the relevant spec docs in `docs-core/`, `docs-game-compiler/`, and/or `docs/`.
- **Keep it current.** Stale tracking is worse than no tracking. If you change project state, update the relevant file.
- **Split live vs history.** Keep `SESSION_HANDOFF.md` as the live checkpoint only. Put detailed chronological history in `work-log/`.
- **Promote durable decisions.** Use `DECISIONS.md` as the working index, but promote stable long-lived decisions into `../adr/compiler/` or `../adr/engine/` instead of letting `DECISIONS.md` become the only source of rationale.
- **Keep it brief.** `ACTIVE_WORK.md` should stay under ~40 lines. `SESSION_HANDOFF.md` should stay short enough that the next agent can read it in one pass.
