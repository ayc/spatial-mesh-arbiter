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
| `DEFERRED` | Validated design, intentionally postponed to a later phase |

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
| T1-01 | **Stat Compilation Formulas** — Linear formula with per-level scaling. Full `attribute-formulas.json` schema with starting coefficients. Secondary attributes (Momentum, Poise, Echo, Affinity, Synchrony) defined. | `REVIEW` | All sub-gaps resolved: formula shape, schema, coefficients, secondary attributes | [draft](tier-1-combat/01-stat-compilation-formulas.md) | `3-gameplay-systems/01-rpg-mechanics.md` + `04-meta-services` |
| T1-02 | **Distance Falloff Formula** — Per-ability configurable: `None`, `Linear` (with floor), or `Step` (discrete tiers). Default AoE: linear 100%→25% from center to edge. | `REVIEW` | Resolved with three falloff modes and designer-configurable floor | [draft](tier-1-combat/02-distance-falloff-formula.md) | `3-gameplay-systems/01-rpg-mechanics.md` |
| T1-03 | **Combat Modifier Pipeline & Proc Order** — Defined by the 12 Canonical Pipeline Stages in the Game Compiler IR Spec. | `REVIEW` | Awaiting adoption of `docs-game-compiler/03-1-compiler-ir-specification.md` into engine contracts. | [draft](tier-1-combat/03-combat-resolution-ordering.md) | `3-gameplay-systems/01-rpg-mechanics.md` |
| T1-04 | **Contention Lock Algorithm** — First-arrive with EntityID tie-break. Per-Arbiter scope. Per-interaction-type lock duration. Party loot modes bypass contention. | `REVIEW` | Algorithm specified with tie-breaking, scope, duration, and loot mode interaction | [draft](tier-1-combat/04-contention-lock-algorithm.md) | `3-gameplay-systems/04-npc-and-world-interaction.md` |
| T1-05 | **Stat Caps & Overflow** — Caps re-enforced at evaluation time (buffs bank above cap, absorb debuffs). Per-stat negative floors defined (move_speed min 10%, dmg_red floor -50%, crit floor 0%). | `REVIEW` | Both sub-gaps resolved with evaluation-time clamping and explicit floor table | [draft](tier-1-combat/05-stat-caps-and-overflow.md) | `3-gameplay-systems/01-rpg-mechanics.md` |
| T1-06 | **Reactive Proc & Cascade Depth** — Resolved by the "Deferred Execution Rule" and "Reactive Depth Bound" in the IR Spec. | `REVIEW` | Awaiting adoption of `docs-game-compiler/03-1-compiler-ir-specification.md` §6. | [draft](tier-1-combat/06-reactive-proc-cascade.md) | `3-gameplay-systems/02-ability-framework.md` |

## Tier 2 — Contract Contradictions

> Blocks integration between layers. Must reconcile before Edge/Meta/Arbiter can talk correctly.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T2-01 | ~~MetaRequest Scope~~ | `RESOLVED` | **Not a gap.** Wire protocol §9.1 had a placeholder 4-variant `MetaRequest` that was never expanded. The canonical 41-variant enum in Edge Node Envelopes §2.1 is the single source of truth. Wire protocol now references it directly; no translation or fan-out exists. | [draft](tier-2-contracts/01-meta-request-scope.md) | `2-contracts-and-interfaces/01-client-edge-wire-protocol.md` + `02-edge-node-envelopes.md` |
| T2-02 | ~~OffensiveStats Mutability~~ | `RESOLVED` | **Not a gap.** Spec is explicit: base immutable during gameplay, Meta replaces via UpdateEntityStats on equip/level/durability, buffs layer at eval time. | [draft](tier-2-contracts/02-offensive-stats-mutability.md) | `2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` |
| T2-03 | ~~Data Epoch Distribution~~ | `RESOLVED` | **Reframed.** `PrepareDataEpoch` is primarily the Arbiter readiness mechanism (loading game content), not just a hot-patching feature. Trigger: Controller at boot (§4.1), version line transitions, and optionally live hot-patch. Meta sync: tolerated brief mismatch, Controller tracks current epoch. Epoch pinning: intentional, effects resolve under creation-time epoch. Updated `docs-core/01` (runtime safety constraint), `docs-core/04-0` (engine-provided capability), and `03-mesh-controller.md` (§4.1 readiness handshake, §11 reframed). | [draft](tier-2-contracts/03-data-epoch-distribution.md) | `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md` |
| T2-04 | **Session Lifecycle & Auth** — Opaque bearer tokens (not JWT). Edge validates via Identity Service lookup. Refresh rotation on every use with 30s grace. Full logout handshake (safe zone instant, wilderness 60s fuse). | `REVIEW` | All sub-gaps resolved: token format, validation, rotation, logout flow | [draft](tier-2-contracts/04-session-lifecycle-and-auth.md) | `1-architecture/04-meta-services.md` + `01-client-edge-wire-protocol.md` |
| T2-05 | **HardEvent Consumption Contract** — Commit-after-persist mandate. 5-retry exponential backoff. Dead-letter topic naming convention. Postgres upsert idempotency pattern. Poison pill quarantine via DLQ. | `REVIEW` | All sub-gaps resolved: commit timing, retry, DLQ, idempotency, poison pill | [draft](tier-2-contracts/05-hard-event-consumption.md) | `2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md` |
| T2-06 | **Surrogate Recovery + Event Spine Contract** — Define quarantine/surrogate takeover, edge roll-call continuity snapshots, rolling checkpoint+delta replay, and phase boundary between crash continuity and spectator/replay services. **Deferred to phase 2:** total-loss model is sufficient for phase 1; resolving now would force premature `docs-core/` changes before the engine is validated. Phase 1 carries extracted to T2-08. | `DEFERRED` | New architecture proposal from 2026-03-04 brainstorming | [draft](tier-2-contracts/06-surrogate-recovery-and-event-spine.md) | `1-architecture/03-mesh-controller.md` + `01-core-primitives.md` + `03-mesh-arbiter-state.md` + `5-testing-and-conformance/01-mini-mesh-conformance.md` |
| T2-07 | **Redpanda Event Bus Adoption ADR** — Define day-1 Redpanda implementation plan, conformance gates, and release contingency (no Redis Streams cutover required pre-launch) | `REVIEW` | Added after transport decision update on 2026-03-04 | [draft](tier-2-contracts/07-redpanda-adoption-adr.md) | `1-architecture/01-core-concepts-and-mesh.md` + `04-meta-services.md` + `0-getting-started/02-implementation-phases.md` |
| T2-08 | ~~Crash Fencing Token Formalization~~ | `RESOLVED` | **Resolved via `fenced_arbiter_ids` reject list.** Internal mesh messages (`MeshInternalEvent`, `GhostUpdate`) don't carry `topology_epoch`, so epoch-based fencing doesn't apply to them. Instead, neighbors add `crashed_arbiter_id` to a `fenced_arbiter_ids` set on `AbortPendingHandoffs` and drop subsequent internal messages from that source. No wire format changes, no `docs-core/` impact. WAL extensibility noted as a forward-compatibility constraint for T2-06 phase 2. | [draft](tier-2-contracts/08-crash-fencing-token.md) | `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` |

## Tier 3 — Subsystem Gaps

> Blocks specific features. Can be resolved in parallel once Tier 0-2 are stable.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T3-01 | **Projectile Simulation** — Core mechanics exist. Needs reconciliation with `P-07` and `P-61` primitives for dynamic properties and bouncing. | `REVIEW` | Supported by Game Compiler taxonomy. | [draft](tier-3-subsystems/01-projectile-simulation.md) | `3-gameplay-systems/02-ability-framework.md` |
| T3-02 | **Ghost Movement Thresholds** — `max_allowed_displacement` defined. Normal ≤0.5 u/tick, HighSpeed ≤2.0 u/tick, Teleport = unlimited. Source Arbiter classifies; lag spike vs teleport distinguished by classification + dt scaling. | `REVIEW` | Thresholds defined, classification algorithm specified, lag spike handling resolved | [draft](tier-3-subsystems/02-ghost-movement-thresholds.md) | `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` |
| T3-03 | **Zone Actor Pulse Mechanics** — Core pulse model exists. Needs reconciliation with `P-14 Continuous Proximity Monitor` for edge-triggered events. | `REVIEW` | Supported by Game Compiler taxonomy. | [draft](tier-3-subsystems/03-zone-actor-pulse-mechanics.md) | `3-gameplay-systems/02-ability-framework.md` + `03-global-events.md` |
| T3-04 | **Line of Sight Calculation** — Resolved by T0-03: `static_grid.query_segment_aabb()` provides raycast against static geometry. If segment from A to B intersects any AABB, LOS is blocked. | `RESOLVED` | Resolved via T0-03 static_grid | [draft](tier-3-subsystems/04-line-of-sight.md) | `3-gameplay-systems/04-npc-and-world-interaction.md` |
| T3-05 | **Threat Table & Leash Mechanics** — Threat formula (damage×multiplier+flat), per-source multipliers, swap threshold (10% standard/20% boss), leash mechanics (range, return speed, HP reset, evade state). | `REVIEW` | All sub-gaps resolved: threat formula, decay, swap threshold, leash protocol | [draft](tier-3-subsystems/05-threat-and-leash.md) | `3-gameplay-systems/04-npc-and-world-interaction.md` |
| T3-06 | **NPC Data Asset Format** — YAML schema for NPC definitions (stats, abilities, threat config, loot). Spawn rules schema (location, population, conditions, patrol paths). Compilation pipeline to game image EntityDefinitions. | `REVIEW` | All sub-gaps resolved: asset schema, spawn rules, patrol format, compilation | [draft](tier-3-subsystems/06-npc-data-asset-format.md) | `1-architecture/02-npc-architecture.md` |
| T3-07 | **Asset Loading & CDN Fallback** — SHA-256 checksum, 3-retry with exponential backoff, no stale-version fallback, SPSC lock-free handoff to tick thread, parse errors treated as download failures. | `REVIEW` | All sub-gaps resolved | [draft](tier-3-subsystems/07-asset-loading.md) | `1-architecture/03-mesh-controller.md` |
| T3-08 | **Dilation + Global Event Interaction** — Sustained dilation intervention after 30s at floor triggers forced split or ops alert. Timer scope fully resolved per `06-kinematic-dilation.md` §3 (simulation timers dilated, infrastructure timers not). | `REVIEW` | Both sub-gaps resolved | [draft](tier-3-subsystems/08-dilation-global-event-interaction.md) | `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md` |
| T3-09 | **Recovery Inbox Overflow** — 100-entry inbox cap, claim-when-full rejected (item stays), pending queue for overflow, critical items never dropped, per-category expiry (30-90 days), notification via session flag. | `REVIEW` | All sub-gaps resolved | [draft](tier-3-subsystems/09-recovery-inbox-overflow.md) | `1-architecture/04-meta-services.md` |
| T3-10 | **LFG Matching Lifecycle** — Accept/decline flow (30s timeout). Partial decline: dissolved, acceptors re-queued with priority, decliners get cooldown. Group binding (auto-party, instance reservation, teleport offer). Disconnect handling. 3 new MetaRequest variants. | `REVIEW` | All sub-gaps resolved: accept/decline, partial handling, binding, disconnect | [draft](tier-3-subsystems/10-lfg-matching-lifecycle.md) | `1-architecture/04-meta-services.md` |

## Tier 4 — Testing & Tooling

> Blocks validation. Can proceed in parallel with Tier 3.
> **Audited against source docs 2026-03-03.**

| # | Gap | Status | Audit | Draft | Canonical Target |
|---|-----|--------|-------|-------|-----------------|
| T4-01 | **Conformance Pass/Fail Criteria** — Machine-checkable assertion framework (predicate + timing window + severity). Structured telemetry channel (UDP + Protobuf). Per-category timing tolerances. CI pipeline with Docker Compose + `conformance-runner` binary. | `REVIEW` | All sub-gaps resolved: assertion framework, metrics, tolerances, CI integration | [draft](tier-4-testing/01-conformance-pass-fail-criteria.md) | `5-testing-and-conformance/01-mini-mesh-conformance.md` |
| T4-02 | **Swarm Tester Spec** — Boids flocking + Combat FSM dual model. Decision frequencies (movement 20Hz, abilities 10Hz, targeting 5Hz). Three combat profiles (random, priority, scripted). Test token auth. Full lifecycle. Per-bot metrics. | `REVIEW` | All sub-gaps resolved: behavior model, auth, combat, lifecycle, metrics | [draft](tier-4-testing/02-swarm-tester-spec.md) | `5-testing-and-conformance/01-mini-mesh-conformance.md` |
| T4-03 | **Debug Canvas Spec** — HTML5 Canvas web app. Controller telemetry WebSocket at 10Hz. 8 visualization layers (topology, entities, ghosts, interest rings, dilation, handoffs, geometry, spawns). Pan/zoom/click/pause/scrub. Performance budget for 5K entities. | `REVIEW` | All sub-gaps resolved: framework, data source, layers, interaction, performance | [draft](tier-4-testing/03-debug-canvas-spec.md) | `5-testing-and-conformance/01-mini-mesh-conformance.md` |

---

## Progress Summary

| Tier | Total | Open | Drafting | Review | Resolved | Deferred |
|------|-------|------|----------|--------|----------|----------|
| 0 — Foundations | 3 | 0 | 0 | 0 | 3 | 0 |
| 1 — Combat | 6 | 0 | 0 | 6 | 0 | 0 |
| 2 — Contracts | 8 | 0 | 0 | 3 | 4 | 1 |
| 3 — Subsystems | 10 | 0 | 0 | 9 | 1 | 0 |
| 4 — Testing | 3 | 0 | 0 | 3 | 0 | 0 |
| **Total** | **30** | **0** | **0** | **21** | **8** | **1** |
