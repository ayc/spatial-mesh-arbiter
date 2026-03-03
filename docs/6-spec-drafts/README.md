# 6-spec-drafts — Gap Resolution Workspace

## What This Directory Is

This is a **working area** for identifying and resolving gaps in the canonical specification before implementation begins. Nothing here is authoritative. Everything here is disposable once its content has been promoted into the real docs.

## How It Differs from docs/0–5

| | docs/0–5 (Canonical Specs) | docs/6-spec-drafts (This Directory) |
|---|---|---|
| **Purpose** | Define the system | Fill holes in the definitions |
| **Authority** | Authoritative — code is implemented from these | Non-authoritative — drafts and scratch work |
| **Lifetime** | Permanent (evolves with the project) | Temporary (deleted after gaps are resolved) |
| **Audience** | Anyone building or understanding the system | The spec authors resolving open questions |
| **Content** | Locked decisions, struct definitions, protocols | Problem statements, open questions, proposed answers |

Think of docs/0–5 as the **blueprint** and this directory as the **punch list** — a structured record of what's missing from the blueprint before construction can start.

## Workflow

```
1. OPEN        Gap identified, problem statement written
2. DRAFTING    Actively working on a proposed resolution
3. REVIEW      Draft complete, ready for sign-off
4. RESOLVED    Content promoted into canonical doc, draft file archived
```

The lifecycle for each gap:

1. **Read the draft file** — understand the problem statement and open questions.
2. **Research and draft** — fill in the "Proposed Resolution" section with concrete answers (formulas, algorithms, struct definitions, pseudocode).
3. **Review** — sanity-check the draft against related specs for contradictions.
4. **Promote** — copy the resolved content into the canonical target doc listed at the top of each draft. Update cross-references if needed.
5. **Update the checklist** — mark the row in `GAPS_CHECKLIST.md` as `RESOLVED`.
6. **Archive the draft file** — move to `_archived/` (see below). Draft files preserve the reasoning chain (alternatives considered, why they were rejected) which is valuable for future contributors who may re-raise the same questions.

## Directory Structure

```
6-spec-drafts/
├── GAPS_CHECKLIST.md              # Master tracker — start here
├── README.md                      # This file
├── tier-0-foundations/            # Blocks everything (determinism, physics, dilation)
├── tier-1-combat/                # Blocks gameplay (stats, damage, contention)
├── tier-2-contracts/             # Blocks integration (wire protocol, auth, events)
├── tier-3-subsystems/            # Blocks specific features (projectiles, NPCs, LOS, etc.)
├── tier-4-testing/               # Blocks validation (conformance criteria, tooling)
└── _archived/                    # Resolved drafts — kept for decision history
```

Tiers are ordered by dependency — Tier 0 gaps should be resolved before Tier 1, because Tier 1 decisions depend on Tier 0 answers. Tiers 3 and 4 can be worked in parallel once 0–2 are stable.

## Rules

- **Never implement from a draft file.** Drafts are proposals, not specs. Code should only be written against docs/0–5.
- **Don't let drafts drift.** If a draft contradicts a canonical doc, the canonical doc wins until the draft is explicitly promoted.
- **One gap, one file.** If a gap splits into multiple sub-problems during drafting, create new draft files and link them from the checklist.
- **Archive when done.** Move resolved drafts to `_archived/`. The reasoning chain (alternatives considered, why they were rejected, audit notes) is valuable for future contributors who may re-raise the same questions. The `_archived/` directory is not authoritative — it's a historical record.
