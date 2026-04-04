# memory-bank/

Project-level coordination layer. Tracks meta-progress, decisions, and session context across the three workstreams (spec completion, layer extraction, engine implementation). These are **not** spec documents — they describe *where the project stands*, not *what the project is*.

## Files

| File | Purpose | Update Frequency |
|------|---------|-----------------|
| `SUMMARY.md` | Start here. Status across all workstreams with links to authoritative trackers. | When workstream status changes |
| `ACTIVE_WORK.md` | What's in flight, what's next, what's blocked. | Start/end of each working session |
| `ENGINE_ROADMAP.md` | 6-phase implementation plan aligned to `docs-core/` contracts. | When phases complete or scope changes |
| `DECISIONS.md` | Architecture decisions and their rationale — the "why" behind non-obvious choices. | When a significant decision is made |
| `SESSION_HANDOFF.md` | Context for the next LLM session to pick up without re-deriving state. | End of each significant session |

## Rules

- **Reference, don't duplicate.** Link to `GAPS_CHECKLIST.md`, `06-architecture-section-mapping.md`, etc. — don't copy their content here.
- **Keep it current.** Stale tracking is worse than no tracking. If you change project state, update the relevant file.
- **Keep it brief.** `ACTIVE_WORK.md` should stay under ~40 lines. `SESSION_HANDOFF.md` entries should be pruned once their context is reflected in `SUMMARY.md` or `DECISIONS.md`.
