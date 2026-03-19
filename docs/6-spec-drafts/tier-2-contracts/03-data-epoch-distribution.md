# T2-03: Data Epoch Distribution

> **Status:** RESOLVED
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md`

## Audit Notes

**The pipeline mechanics ARE specified** in `03-mesh-controller.md` §11:
1. Controller issues `PrepareDataEpoch { new_epoch, asset_uri, checksum }` over TCP
2. Arbiters download asynchronously via background task
3. Checksum verified
4. Parsed dictionary pushed into lock-free queue, picked up at next frame boundary, atomic swap

**The epoch matching rules ARE specified** in `01-core-primitives.md` §1.1.5:
- Proposal epoch == Arbiter epoch → process normally
- Proposal stale → immediate ActionFailed
- Arbiter behind → buffer with MAX_EVENT_AGE_TICKS timeout

**Pre-rolled CombatContext carries data_epoch** (ActiveStatusEffect includes data_epoch for DoT/HoT pulses).

## Resolution

### Key Reframing

The original §11 of `03-mesh-controller.md` was titled "Live Data Distribution (Hot-Patching)" and framed `PrepareDataEpoch` as a hot-patching feature. This undersold the mechanism. **`PrepareDataEpoch` is the fundamental mechanism for loading game content into the engine.** An Arbiter without loaded content is an empty runtime that cannot process any game-specific proposal.

The section has been reframed as "Game Content Distribution" with the primary purpose being Arbiter readiness, and hot-patching as a secondary capability of the same pipeline.

### Answers to gap questions

#### 1. Trigger Mechanism

- [x] Who initiates epoch increment?

**The Mesh Controller**, in three situations:

| Situation | Trigger |
| :--- | :--- |
| Arbiter boot / Warm Pool registration | Controller primes the Arbiter with the current content version as part of the readiness handshake (§4.1). This is the primary use case. |
| Version line transition | Blue/green deployment rolls out new game rules via the `docs-core/04-3` transition state machine. |
| Live hot-patch (optional) | Balance changes pushed to a running cluster without restart. Same pipeline, Arbiter swaps atomically at next frame boundary. |

What sits *upstream* of the Controller (designer CLI, CI/CD pipeline, game compiler output) is an operational/tooling concern, not an engine contract concern. It belongs in `docs/4-infrastructure/` or `docs-game-compiler/`.

#### 2. Meta ↔ Arbiter Epoch Sync

- [x] Must epochs match during Spawn?

**Meta SHOULD use the same data epoch as the target Arbiter when compiling stats, but brief mismatch during activation windows is tolerated.**

Rationale: Meta compiles `OffensiveStats`/`DefensiveStats` as immutable snapshots and sends them to the Arbiter. The Arbiter uses them as received — it never re-derives stats from the balance data. SpellData is used by Arbiters for ability resolution (damage coefficients, ranges, cooldowns), which is a separate concern from stat compilation.

During the brief window where Meta and an Arbiter are on different epochs (e.g., during a hot-patch rollout), the worst case is a few seconds of slightly mismatched balance tuning. The inconsistency is harmless and self-resolving once the Arbiter activates the new epoch.

Meta can learn the mesh's current epoch from the Controller, which tracks `Current Data Epoch` in its state (§14) and is already queried by Meta during spawn topology lookup (§12).

#### 3. Epoch Pinning

- [x] Is pre-rolled CombatContext epoch-pinned intentionally?

**Yes, intentionally.** The pattern is consistent across the entire codebase:

- `ActiveStatusEffect` carries `data_epoch` — DoT/HoT pulses resolve under the epoch they were applied in
- `ScheduledAbilityExecution` carries `data_epoch` pinned at scheduling time
- `Projectile` carries `data_epoch`
- Global event fan-out commands carry `data_epoch` — Arbiters validate it before detonation

The normative rule: **effects are epoch-pinned at creation time and resolve under their pinned epoch, not the current one.** The Arbiter's `try_activate_data_epoch()` handles the case where it needs to resolve under an older epoch.

### Changes applied

1. **`docs-core/01-spatial-runtime-kernel.md` §5** — Added runtime safety constraint: a node MUST NOT accept entity authority until it has loaded and activated a valid game content version.
2. **`docs-core/04-0-game-adapter-interface.md` §3** — Added versioned game content distribution as an engine-provided capability.
3. **`docs/1-architecture/03-mesh-controller.md` §4.1** — Added `PrepareDataEpoch` as a required step in the registration/readiness handshake. Arbiters are not marked Ready until content is activated.
4. **`docs/1-architecture/03-mesh-controller.md` §11** — Reframed from "Live Data Distribution (Hot-Patching)" to "Game Content Distribution." Primary purpose is Arbiter readiness; hot-patching is a secondary capability. Added trigger situation table.

## References

- `docs/1-architecture/03-mesh-controller.md` §4.1 — Registration and readiness handshake
- `docs/1-architecture/03-mesh-controller.md` §11 — Game Content Distribution
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` §1.1.5 — Epoch matching rules
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` lines 460-468 — ActiveStatusEffect.data_epoch
- `docs-core/01-spatial-runtime-kernel.md` §5 — Runtime Safety Constraints
- `docs-core/04-0-game-adapter-interface.md` §3 — Minimum Adapter Surface
- `docs-core/04-3-version-line-transition-contract.md` — Version line rollout/rollback
