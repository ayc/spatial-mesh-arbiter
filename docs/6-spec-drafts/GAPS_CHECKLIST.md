# Spec Gaps Checklist

> Master tracker for all identified specification gaps.
> Each row links to a dedicated draft file where the resolution is developed.
> Once resolved, content is promoted into the canonical doc and status updated here.

## Status Key

| Status | Meaning |
|--------|---------|
| `OPEN` | Gap identified, no draft started |
| `DRAFTING` | Active work on resolution |
| `REVIEW` | Draft complete, awaiting sign-off |
| `RESOLVED` | Promoted into canonical docs |

---

## Tier 0 — Foundations

> Blocks everything downstream. Must resolve before any simulation code.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T0-01 | **Simulation Determinism & WAL Replay Contract** — WAL self-containment, local RNG, saturating arithmetic, BTreeMap iteration | `RESOLVED` | Promoted into `01-core-concepts-and-mesh.md` determinism mandate | [archived](_archived/01-determinism-strategy.md) | `1-architecture/01-core-concepts-and-mesh.md` |
| T0-02 | **Kinematic Dilation — Spec Corrections** — 6 corrections applied. Authoritative doc at `06-kinematic-dilation.md`. | `RESOLVED` | Tick Interleaving removed, is_heavy_frame removed, KiDi doc created | [archived](_archived/02-dilation-formula.md) | `1-architecture/01-core-concepts-and-mesh.md` §8.2 + `03-mesh-arbiter-state.md` |
| T0-03 | **Collision Algorithm** — apply_kinematics, static_grid, soft collision, calculate_collisions. Resolves T3-04. | `RESOLVED` | Promoted into `03-mesh-arbiter-state.md` physics implementation notes | [archived](_archived/03-collision-algorithm.md) | `1-architecture/01-core-concepts-and-mesh.md` |

## Tier 1 — Combat Pipeline

> Blocks gameplay implementation. Depends on Tier 0 determinism decisions.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T1-01 | **Stat Compilation Formulas** — Pipeline and durability penalty ARE specified. Missing: `attribute-formulas.json` numeric coefficients, secondary attribute formulas | `OPEN` | Narrowed (pipeline exists, coefficients missing) | [draft](tier-1-combat/01-stat-compilation-formulas.md) | `3-gameplay-systems/01-rpg-mechanics.md` + `04-meta-services` |
| T1-02 | **Distance Falloff Formula** — `calculate_falloff(distance)` called in two locations, never defined | `OPEN` | Confirmed | [draft](tier-1-combat/02-distance-falloff-formula.md) | `3-gameplay-systems/01-rpg-mechanics.md` |
| T1-03 | **Combat Resolution Ordering** — Tick phase ordering exists but no intra-phase ordering for simultaneous events, no mutual-kill tie-breaking | `OPEN` | Confirmed | [draft](tier-1-combat/03-combat-resolution-ordering.md) | `3-gameplay-systems/01-rpg-mechanics.md` |
| T1-04 | **Contention Lock Algorithm** — Requirement and outcome taxonomy ARE specified. Missing: the actual algorithm | `OPEN` | Narrowed (requirement clear, mechanism missing) | [draft](tier-1-combat/04-contention-lock-algorithm.md) | `3-gameplay-systems/04-npc-and-world-interaction.md` |
| T1-05 | **Stat Caps & Overflow** — Cap values, enforcement pseudocode, resistance floor all ARE specified. Missing: intermediate overflow after buffs, non-resistance negative floors | `OPEN` | Narrowed (mostly specified) | [draft](tier-1-combat/05-stat-caps-and-overflow.md) | `3-gameplay-systems/01-rpg-mechanics.md` |
| T1-06 | **Reactive Proc & Cascade Depth** — proc_depth guard, cross-boundary relay, deferred timing all ARE specified. Missing: hard ceiling confirmation, proc types beyond thorns | `OPEN` | Narrowed (partially specified) | [draft](tier-1-combat/06-reactive-proc-cascade.md) | `3-gameplay-systems/02-ability-framework.md` |

## Tier 2 — Contract Contradictions

> Blocks integration between layers. Must reconcile before Edge/Meta/Arbiter can talk correctly.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T2-01 | **MetaRequest Scope** — Wire protocol defines 4 variants; Edge Node Envelopes define 41. Relationship unclear (internal dispatch? aspirational? subset?) | `OPEN` | Confirmed (genuine ambiguity) | [draft](tier-2-contracts/01-meta-request-scope.md) | `2-contracts-and-interfaces/01-client-edge-wire-protocol.md` + `02-edge-node-envelopes.md` |
| T2-02 | ~~OffensiveStats Mutability~~ | `RESOLVED` | **Not a gap.** Spec is explicit: base immutable during gameplay, Meta replaces via UpdateEntityStats on equip/level/durability, buffs layer at eval time. | [draft](tier-2-contracts/02-offensive-stats-mutability.md) | `2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` |
| T2-03 | **Data Epoch Distribution** — Pipeline mechanics specified (download, verify, swap). Missing: who triggers epoch increment, Meta↔Arbiter epoch sync, mid-resolution semantics | `OPEN` | Narrowed (pipeline exists, triggers/sync missing) | [draft](tier-2-contracts/03-data-epoch-distribution.md) | `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md` |
| T2-04 | **Session Lifecycle & Auth** — Token TTL, max sessions, wilderness fuse, session orphaning ARE specified. Missing: token format (JWT vs opaque), refresh rotation, explicit logout handshake flow | `OPEN` | Narrowed (substantial auth exists, format/rotation missing) | [draft](tier-2-contracts/04-session-lifecycle-and-auth.md) | `1-architecture/04-meta-services.md` + `01-client-edge-wire-protocol.md` |
| T2-05 | **HardEvent Consumption Contract** — XACK requirement, at-least-once delivery, idempotency mandate, consumer groups, scaling thresholds ARE specified. Missing: ack timing (vs Postgres persist), retry policy, visibility timeout, dead letter handling | `OPEN` | Narrowed (framework exists, failure-mode details missing) | [draft](tier-2-contracts/05-hard-event-consumption.md) | `2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md` |

## Tier 3 — Subsystem Gaps

> Blocks specific features. Can be resolved in parallel once Tier 0-2 are stable.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T3-01 | **Projectile Simulation** — Euler integration, homing steering, pierce field, fuse decrement, collision call ARE specified. Missing: turn rate limiting, explosion trigger logic, pierce decrement details | `OPEN` | Narrowed (core mechanics exist, refinements missing) | [draft](tier-3-subsystems/01-projectile-simulation.md) | `3-gameplay-systems/02-ability-framework.md` |
| T3-02 | **Ghost Movement Thresholds** — Enum and function calls exist but numeric thresholds and classification logic are entirely missing | `OPEN` | Confirmed | [draft](tier-3-subsystems/02-ghost-movement-thresholds.md) | `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` |
| T3-03 | **Zone Actor Pulse Mechanics** — Per-pulse UUID generation, pulse lifecycle, mobile zone (attached aura) ARE specified. Missing: entity detection algorithm per pulse, boundary crossing semantics | `OPEN` | Narrowed (core pulse model exists, detection algorithm missing) | [draft](tier-3-subsystems/03-zone-actor-pulse-mechanics.md) | `3-gameplay-systems/02-ability-framework.md` + `03-global-events.md` |
| T3-04 | **Line of Sight Calculation** — Resolved by T0-03: `static_grid.query_segment_aabb()` provides raycast against static geometry. If segment from A to B intersects any AABB, LOS is blocked. | `RESOLVED` | Resolved via T0-03 static_grid | [draft](tier-3-subsystems/04-line-of-sight.md) | `3-gameplay-systems/04-npc-and-world-interaction.md` |
| T3-05 | **Threat Table & Leash Mechanics** — High-level concepts mentioned but no formulas. Aggro, decay, leash all genuinely unspecified | `OPEN` | Confirmed | [draft](tier-3-subsystems/05-threat-and-leash.md) | `3-gameplay-systems/04-npc-and-world-interaction.md` |
| T3-06 | **NPC Data Asset Format** — Tier assignment and archetype binding ARE specified. Missing: JSON schema/format, spawn rules, compilation pipeline | `OPEN` | Narrowed (classification exists, format missing) | [draft](tier-3-subsystems/06-npc-data-asset-format.md) | `1-architecture/02-npc-architecture.md` |
| T3-07 | **Asset Loading & CDN Fallback** — High-level flow specified (background download, lock-free queue, atomic swap). Missing: checksum algorithm, retry logic, parse error handling | `OPEN` | Narrowed (flow exists, details missing) | [draft](tier-3-subsystems/07-asset-loading.md) | `1-architecture/03-mesh-controller.md` |
| T3-08 | **Dilation + Global Event Interaction** — Priority event wakeup IS specified (`has_priority_event` overrides dilation). Missing: sustained dilation behavior, player experience during prolonged dilation | `OPEN` | Narrowed (wakeup specified, sustained behavior missing) | [draft](tier-3-subsystems/08-dilation-global-event-interaction.md) | `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md` |
| T3-09 | **Recovery Inbox Overflow** — Explicitly flagged as open question in the spec itself (`max_unclaimed_entries: "TBD"`) | `OPEN` | Confirmed (spec acknowledges the gap) | [draft](tier-3-subsystems/09-recovery-inbox-overflow.md) | `1-architecture/04-meta-services.md` |
| T3-10 | **LFG Matching Lifecycle** — Matching algorithm and party formation ARE specified. Missing: accept/decline protocol, timeout, partial-decline handling (no `LfgAcceptMatch` in MetaRequest enum) | `OPEN` | Narrowed (matching exists, post-match lifecycle missing) | [draft](tier-3-subsystems/10-lfg-matching-lifecycle.md) | `1-architecture/04-meta-services.md` |

## Tier 4 — Testing & Tooling

> Blocks validation. Can proceed in parallel with Tier 3.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T4-01 | **Conformance Pass/Fail Criteria** — Scenarios have documented "Observation" expectations. Missing: formalized automated assertions, metric thresholds, timing tolerances, CI integration | `OPEN` | Narrowed (observations exist, automation criteria missing) | [draft](tier-4-testing/01-conformance-pass-fail-criteria.md) | `5-testing-and-conformance/01-mini-mesh-conformance.md` |
| T4-02 | **Swarm Tester Spec** — Usage context specified (WebSocket frames per client-edge protocol). Missing: Boids parameters, bot auth, combat action selection, decision loop frequency, metrics | `OPEN` | Confirmed (substantial) | [draft](tier-4-testing/02-swarm-tester-spec.md) | `5-testing-and-conformance/01-mini-mesh-conformance.md` |
| T4-03 | **Debug Canvas Spec** — Conceptual requirements specified (what to visualize). Missing: framework, data transport, API, interaction model | `OPEN` | Confirmed | [draft](tier-4-testing/03-debug-canvas-spec.md) | `5-testing-and-conformance/01-mini-mesh-conformance.md` |

---

## Progress Summary

| Tier | Total | Open | Drafting | Review | Resolved |
|------|-------|------|----------|--------|----------|
| 0 — Foundations | 3 | 0 | 0 | 0 | 3 |
| 1 — Combat | 6 | 6 | 0 | 0 | 0 |
| 2 — Contracts | 5 | 4 | 0 | 0 | 1 |
| 3 — Subsystems | 10 | 9 | 0 | 0 | 1 |
| 4 — Testing | 3 | 3 | 0 | 0 | 0 |
| **Total** | **27** | **22** | **0** | **0** | **5** |
