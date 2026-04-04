# Ability Sketch Completion Checklist

This tracker defines what it means for an ability sketch to be "designer-recreatable with the compiler" rather than merely "decomposed into primitives."

It exists because the current sketch set already has broad primitive coverage, but many sketches still leave cross-boundary behavior and compiler output details as TODOs. Those gaps are the remaining blocker for using the sketches as reliable designer-facing references.

This file is the **closure tracker**. It is distinct from:

- `COMPILER_COMPATIBILITY_CHECKLIST.md` — per-sketch audit of whether the current compiler docs already support each sketch
- `COMPILER_GAP_REGISTER.md` — grouped backlog of missing canonical compiler contracts revealed by that audit

## Goal

For a sketch to count as complete, a game designer should be able to:

1. Understand the intended gameplay behavior.
2. See the canonical primitive chain that expresses it.
3. Know the cross-boundary/runtime contract required for the ability.
4. Know what authoring inputs the compiler accepts.
5. Know what compiler output / IR / validation shape the compiler must produce.

## Completion Criteria

Every sketch is complete only when all of the following are true:

1. `Primitive Composition` matches the canonical primitive taxonomy in `../ability-primitives/`.
2. `Observable Behavior` is concrete enough to define player-visible semantics without relying on TODO notes.
3. `Cross-Boundary Concerns` contains resolved behavior, not open TODOs.
4. `Compiler Requirements` states:
   - what the designer specifies
   - what the compiler emits
   - what the compiler validates or rejects
5. Any reusable rule discovered while closing the sketch is promoted into canonical compiler or contract docs instead of being left as sketch-local prose.
6. Open questions are either resolved or converted into explicit backlog items elsewhere. A completed sketch should not hide unresolved contract questions behind TODO markers.

## Working Statuses

Use these statuses when reviewing or updating sketches:

| Status | Meaning |
|---|---|
| `Primitive-Covered` | Sketch has a primitive chain, but still contains unresolved TODOs. |
| `Closure-In-Progress` | Cross-boundary and compiler sections are actively being resolved. |
| `Sketch-Complete` | Sketch satisfies the completion criteria above and has no remaining TODOs. |
| `Canonicalized` | Reusable outcomes from the sketch have been folded into the relevant compiler/core/docs contracts. |

Current baseline: all sketches are at least `Primitive-Covered`; many are not yet `Sketch-Complete`.

## Resolution Workflow

Apply this sequence to each sketch:

1. Read the sketch and verify the primitive chain against `../ability-primitives/README.md`.
2. Resolve `Cross-Boundary Concerns` using authoritative engine contracts in `docs-core/`.
3. Resolve `Compiler Requirements` into:
   - designer-facing fields
   - emitted semantic IR / runtime artifacts
   - validation rules and compile-time errors
4. If the sketch exposes a recurring pattern, promote that rule into the canonical compiler docs (`01-*`, `02-*`, `03-*`, `04-*`, `05-*`) or the primitive catalog.
5. Remove TODOs from the sketch once the canonical destination exists.

## Prioritization Rule

Prioritize sketches using this order:

1. Common designer building blocks that many other abilities depend on.
2. Mechanics that force compiler-surface decisions not yet made canonically.
3. Mechanics that stress cross-boundary authority and therefore expose engine/compiler contract gaps.
4. Exotic or mode-specific mechanics after the baseline authoring surface is stable.

TODO count alone is not a sufficient priority signal. Reusable leverage matters more.

## Priority Queue

### Priority A — Core authoring baseline

These sketches should be closed first because they define common mechanics a designer will reach for immediately, and they force canonical answers the compiler needs anyway.

| Sketch | Why it is high leverage |
|---|---|
| `SK-15 Purify` | Forces canonical status-effect classification, cleanse filters, and immunity interception rules. |
| `SK-24 Stun` | Establishes the baseline hard-CC authoring model and DR/capability interactions. |
| `SK-29 Blizzard` | Canonical hostile stationary zone pattern: pulse timer + AoE query + periodic effect. |
| `SK-34 Charge` | Resolves complex multi-phase movement, entity pinning, and conditional movement outcomes. |
| `SK-35 Blink Strike` | Establishes instant teleport semantics and instant cross-boundary handoff rules. |
| `SK-108 Mana Burn` | Forces compiler support for resource-targeting combat, not just HP-targeting effects. |
| `SK-117 Stagger Bar` | Defines secondary combat bars and non-HP depletion states for bosses. |
| `SK-122 Counterspell` | Clarifies cast interception and mid-cast cancellation in the authoring and IR model. |

### Priority B — High-value boundary and systems closure

These sketches should follow once the baseline is stable because they define important but more specialized runtime/compiler patterns.

| Sketch | Why it is next |
|---|---|
| `SK-30 Trail of Fire` | Canonical moving-deposit geometry and movement-driven effect authoring. |
| `SK-31 Vortex` | Resolves continuous forced movement and moving-zone authority interactions. |
| `SK-32 Minefield` | Forces stealth/visibility, dormant actors, and long-lived proximity actors. |
| `SK-33 Shifting Sands` | Resolves self-propelled zones and zone boundary handoff behavior. |
| `SK-66 Symbiote` | High-value remote-origin ability pattern for cross-entity casting. |
| `SK-69 Portal Pair` | Canonical linked-structure teleport pattern. |
| `SK-82 Projectile Deflect` | Clarifies projectile ownership hijacking and projectile return semantics. |
| `SK-120 Combo Field Matrix` | Defines systemic cross-player interactions and compiler-side combo tagging. |

### Priority C — Systemic, group, or mode-specific mechanics

These should be tackled after the baseline designer surface is stable.

| Sketch | Why it is later |
|---|---|
| `SK-68 Multi-Entity Control` | Game-mode level ownership model, not baseline ability authoring. |
| `SK-77 Two-Player Entity` | Specialized multi-session control topology. |
| `SK-105 Pocket Arena` | Separate simulation-space extraction, high complexity, niche usage. |
| `SK-121 Downed State` | Important game-system mechanic, but larger lifecycle/system design than baseline ability authoring. |
| `SK-124 Group Sequential Combo` | Group-state machine mechanic, valuable but not foundational. |
| `SK-125 Group Simultaneous Input` | Group coordination mechanic, valuable but not foundational. |

## Immediate Batch Recommendation

Current Batch 1 status:

- `SK-15 Purify` — complete on 2026-04-04

If work continues now, the remaining first closure batch should be:

1. `SK-24 Stun`
2. `SK-29 Blizzard`
3. `SK-35 Blink Strike`
4. `SK-108 Mana Burn`

This remaining batch is small enough to complete in a few focused sessions while still forcing answers for:

- status effect classification
- capability / CC semantics
- stationary zones
- teleport semantics
- resource-targeting combat

Those answers will unblock many later sketches.
