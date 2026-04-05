# work-log/

Historical session chronology for `memory-bank/`.

Use this directory for dated milestone summaries and append-only historical notes that would make
`SESSION_HANDOFF.md` too noisy.

## Purpose

- Preserve chronological context without overloading the live handoff file
- Record significant work sessions, milestone closures, and tracker-structure changes
- Keep `SESSION_HANDOFF.md` short and current

## Naming

- Prefer one file per day: `YYYY-MM-DD.md`
- If a single day becomes too large, split by suffix:
  - `YYYY-MM-DD-a.md`
  - `YYYY-MM-DD-b.md`

## Content Guidelines

- Write from the perspective of project state changes, not terminal transcript replay
- Summarize the major changes, decisions, and resulting status
- Link to canonical trackers or ADRs when useful
- Do not duplicate full spec content

## Relationship to Other Files

- `../SESSION_HANDOFF.md` is the live checkpoint only
- `../DECISIONS.md` is the working decision index
- `../../adr/` holds durable architecture decision records once decisions are promoted
