# ADR

Architecture Decision Records for the Spatial Mesh Arbiter project.

These files capture durable architectural choices and their rationale after those choices are stable
enough to stand alone outside the session-by-session working log.

## Layout

- `compiler/` — authoring surface, compiler contract, IR, and ability-surface decisions
- `engine/` — runtime kernel, messaging, durability, topology, and adapter-boundary decisions

## Authority

ADRs are explanatory, not normative.

If an ADR conflicts with the layered specs:

1. `docs-core/` wins
2. then `docs-game-compiler/`
3. then `docs/`

ADRs explain why a choice was made. They do not override the implementation contracts.

## Relationship to Other Tracking Files

- `memory-bank/DECISIONS.md` is the working reverse-chronological decision index
- durable entries should be promoted from `memory-bank/DECISIONS.md` into this directory
- `memory-bank/work-log/` is chronology, not durable rationale

## Naming

- Use `ADR-####-short-kebab-title.md`
- Start at `ADR-0001`
- Numbering is global across all subdirectories, not per-folder

## Suggested Template

- `# ADR-####: Title`
- `Status`
- `Date`
- `Context`
- `Decision`
- `Consequences`
