# T0-01: Simulation Determinism & WAL Replay Contract

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/01-core-concepts-and-mesh.md`

## Problem Statement

The architecture requires deterministic simulation for merge/split WAL replay, cross-boundary combat, and Metronome-synchronized global events. The spec mandates fixed-point math (`I32F32`) and "canonical iteration ordering" but does not specify:

1. **What "determinism" actually requires** — which operations must be reproducible across Arbiters, and which don't need to be?
2. **Arithmetic discipline** — rounding modes, overflow behavior for `I32F32`
3. **Iteration order** — the spec mandates it but shows `HashMap` in pseudocode
4. **WAL replay contract** — what guarantees must WAL entries provide for faithful replay?

This document establishes the determinism contract that all simulation code must follow.

## Core Principle: Determinism Through Self-Contained Messages

**The architecture does NOT require every Arbiter to be able to independently reproduce every computation from scratch.** It requires something weaker and more practical:

> **Every message and WAL entry MUST be self-contained.** Any non-deterministic value (RNG roll, external input, timestamp) used during event resolution MUST be captured in the outgoing message or WAL entry, so that any receiving node or replay process can produce byte-identical state without re-executing non-deterministic operations.

This single rule eliminates an entire class of distributed determinism problems:

### What this means in practice

**Combat rolls (RNG) are local.** An Arbiter rolls crit, evasion, block using any fast local PRNG. The roll result is baked into the outgoing message — `CombatContext.is_critical_strike`, `InternalPreparedHit.base_damage`, etc. No downstream node ever re-derives a roll. They act on the resolved value they received.

**WAL replay never re-rolls.** During merge/split, the winner replays the loser's WAL. WAL entries contain resolved outcomes with all non-deterministic values already captured. Replay is a deterministic function of the WAL contents — no RNG, no external calls, no non-deterministic operations.

**Edge Nodes receive authoritative outcomes.** `ActionApplied`, `StateUpdate`, etc. carry final results. Edge Nodes never verify or reproduce server-side computations.

### What this does NOT relax

Self-contained messages eliminate the need for synchronized RNG and reproducible external inputs. But **deterministic physics** is still required because multiple Arbiters must independently converge on the same spatial state from the same entity positions and velocities. This means:

- **Fixed-point arithmetic** must produce identical results across platforms (§2)
- **Overflow behavior** must be defined and consistent (§3)
- **Entity processing order** must be deterministic (§4)

These are specified below.

### Why RNG synchronization is unnecessary

The two-phase combat pipeline already carries resolved values:
- **Phase 1 (Pre-Roll):** Attacker's Arbiter rolls crit → packages `CombatContext { is_critical_strike: true, base_damage: 450 }` → sends to defender's Arbiter as `InternalPreparedHit`
- **Phase 2 (Resolution):** Defender's Arbiter rolls evasion/block locally → applies or rejects → emits `ActionApplied` outcome

Each roll is consumed locally and its effect propagated as data. The PRNG algorithm, seed, and state are invisible to every other node in the system.

**PRNG recommendation:** `WyRand` seeded from OS entropy at Arbiter boot. Fast (~1ns/call), small state (64-bit), good statistical properties (passes BigCrush). But any PRNG works — the choice is an implementation detail, not an architectural constraint.

## Fixed-Point Arithmetic Rules

### Rounding: Truncation Toward Zero (Fixed Crate Default)

**Rule:** All fixed-point arithmetic uses the `fixed` crate's default operators, which truncate toward zero for integer conversions (`to_num::<T>()` discards fractional bits) and truncate for division.

**Rationale:** The `fixed` crate's `I32F32` (`FixedI64<U32>`) performs all arithmetic using integer operations internally. Division truncates the fractional result. `to_num::<u64>()` discards fractional bits (truncation toward zero). This is deterministic, platform-independent, and consistent with the spec's existing pseudocode (which uses `as i32` for HP damage).

**No banker's rounding.** Mandating truncation everywhere avoids mixed-mode confusion.

**Spec rule:**
> All `SimFixed` arithmetic MUST use the `fixed` crate's default operators. Explicit rounding (e.g., `round_to_zero()`, `ceil()`) is only permitted when the spec calls for it by name. Division and `to_num` truncate toward zero. No implicit rounding mode changes.

### Cross-Platform Determinism: Guaranteed by Construction

`I32F32` is `FixedI64<U32>` — a 64-bit signed integer with an implicit binary point. All operations are integer add/sub/mul/shift. No floating-point hardware is involved.

- x86_64, aarch64, and wasm32 produce identical results by construction.
- The `fixed` crate does not use SIMD or platform-specific intrinsics for basic arithmetic.
- Rust's integer arithmetic is defined as two's complement and platform-independent.

**Verification:** Pin the `fixed` crate version in `Cargo.lock`. Add a CI determinism test: run the same 1000-tick simulation on x86_64 and aarch64, assert byte-identical final state.

## Overflow: Saturating Arithmetic in Simulation

**Rule:** All `SimFixed` arithmetic in the simulation loop MUST use saturating variants:

```rust
// CORRECT — saturating
let result = a.saturating_mul(b);
let result = a.saturating_add(b);
let result = a.saturating_div(b);

// FORBIDDEN in simulation — panics in debug, wraps in release
let result = a * b;
let result = a + b;
```

**Rationale:** The default `*` operator on `I32F32` panics in debug mode and wraps in release mode on overflow. Wrapping produces silently wrong results (e.g., massive damage becomes negative). Panicking crashes the Arbiter. Neither is acceptable for a live game server. Saturating clamps to `I32F32::MAX` / `I32F32::MIN` — a safe degradation.

**Implementation:** Create a `SimMath` wrapper module that exposes only saturating operations. Lint or `clippy::deny` against bare arithmetic operators on `SimFixed` in the `spatial-arbiter` crate. This applies to simulation code only — Meta Services and Edge Node code can use normal arithmetic since they don't need cross-Arbiter determinism.

**Exception:** `wrapping_mul` / `wrapping_add` are permitted for non-simulation purposes (hash mixing, ID generation, etc.).

## Iteration Order: Sorted by EntityID Ascending

**Rule:** All iteration over entity collections in the simulation loop MUST process entities in ascending `EntityID` order.

**Implementation:** Replace `HashMap<EntityID, SoftState>` with `BTreeMap<EntityID, SoftState>` for the `entities` map in `SpatialActor`. `BTreeMap` iteration is sorted by key, which satisfies the determinism requirement without a collect-and-sort step each tick.

**Rationale:** The spec already mandates "canonical iteration ordering (e.g., processing entities by ID)" in §6.2 of Core Concepts. `BTreeMap` is the natural choice:
- Iteration is always sorted — no per-tick sort overhead.
- Insertion/removal is O(log n) vs HashMap's O(1), but n ≤ 1000 (max entities per Arbiter), so the difference is negligible.
- `hashbrown` (mandated for other maps) remains appropriate for non-determinism-sensitive maps where iteration order doesn't affect simulation output.

**Scope:**
- `entities: BTreeMap<EntityID, SoftState>` — **must be sorted** (affects combat resolution order)
- `offense_by_entity: BTreeMap<EntityID, OffensiveStats>` — **must be sorted** (looked up in entity order)
- `ghost_entities: HashMap<EntityID, GhostState2D>` — **can stay HashMap** (ghosts are read-only; iteration order doesn't affect authoritative state)
- `projectiles: BTreeMap<ProjectileID, ProjectileActor>` — **must be sorted** (affects collision resolution order)

## Summary of Decisions

| Area | Decision | Why |
|------|----------|-----|
| **Core principle** | Messages and WAL entries are self-contained — non-deterministic values captured at source | Eliminates need for synchronized RNG, reproducible external calls, or re-execution during replay |
| **RNG** | Local `WyRand`, OS entropy seed. Results carried in messages/WAL. | Roll outcomes are data, not recomputed. PRNG choice is an implementation detail. |
| **Rounding** | Truncation toward zero (`fixed` crate default) | Platform-independent, matches existing pseudocode |
| **Overflow** | Saturating arithmetic in simulation (lint-enforced via `SimMath`) | Prevents panic (debug) and silent wrap (release) |
| **Iteration** | `BTreeMap` for entities/projectiles, ascending EntityID | Spec already mandates canonical ordering; `BTreeMap` provides it by construction |
| **Cross-platform** | Guaranteed by `I32F32` (integer arithmetic only) | No floating-point hardware involved |

## Closed Questions

- **`ghost_entities` stays `HashMap`.** Ghosts need fast keyed lookup (O(1) for position updates from neighbors) and insert/remove (O(1) for TTL expiry). Iteration order doesn't affect authoritative state — ghost hits produce `InternalPreparedHit` messages resolved independently on the ghost's home Arbiter. BTreeMap would add O(log n) overhead for no correctness benefit.
- **`SimFixed::saturating_pow()` — provide as utility, not strictly required.** The dilation formula raises a `[0, 1]` value to a positive exponent, which cannot overflow. But a saturating wrapper is cheap insurance for future uses and prevents developers from reaching for `f64`.

## References

- `docs/0-getting-started/02-implementation-phases.md` — `fixed` crate mandate, `hashbrown` mandate
- `docs/2-contracts-and-interfaces/internal-mesh-types/05-architecture-summary.md` — "Deterministic Time" rule
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — tick loop processing order
- `docs/1-architecture/01-core-concepts-and-mesh.md` §6.2 — "enforce canonical iteration ordering"
