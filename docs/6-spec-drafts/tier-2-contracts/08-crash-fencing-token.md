# T2-08: Crash Fencing Token Formalization

> **Status:** RESOLVED
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Extracted From:** [T2-06: Surrogate Recovery and Event Spine](06-surrogate-recovery-and-event-spine.md) (deferred to phase 2)
> **Canonical Target:** `1-architecture/03-mesh-controller.md` + `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md`

## Problem Statement

When an Arbiter crashes, the Mesh Controller declares it dead and neighbors absorb its region. However, the mechanism for **rejecting stale messages** from the dead Arbiter was not formally specified.

The topology epoch handles stale *external* proposals (Edge Node → Arbiter), but most *internal* mesh messages (`MeshInternalEvent`, `GhostUpdate`) do not carry `topology_epoch` and bypass epoch validation entirely. Only `ProjectileHandoff` validates topology epoch.

## Analysis

Three options were considered:

### Option A: Topology epoch is sufficient
**Does not hold.** `MeshInternalEvent` and `GhostUpdate` do not carry `topology_epoch`, so there is nothing to validate against. The assumption that "stale-epoch messages are rejected per §5.1" is incorrect for these message types.

### Option B: Per-Arbiter lease token
Adds a new `authority_lease` field to all internal message headers. Closes the gap but adds wire overhead to every internal message and introduces a new engine-level concept that would need to be reflected in `docs-core/`.

### Option C: Reject by `source_arbiter_id` after crash (selected)
When the Controller declares an Arbiter dead, it already sends `AbortPendingHandoffs { crashed_arbiter_id }` to neighbors. Neighbors add the `crashed_arbiter_id` to a `fenced_arbiter_ids` set and silently drop any subsequent `MeshInternalEvent` or `GhostUpdate` from that source.

**Why this is sufficient:**
- The dead Arbiter stops sending immediately (the process is dead). The only concern is messages already in flight.
- In-flight messages drain within milliseconds (bounded by network latency, not the 3-second detection window).
- Ghost updates from a dead source are harmless (read-only projections, garbage-collected on topology update) but rejecting them early is cleaner.
- ImpactEvents from a dead source contain legitimately pre-rolled CombatContext, but accepting damage from a crashed attacker creates ambiguous gameplay state. Dropping them is safer — the attacker's entity is destroyed anyway.
- The `fenced_arbiter_ids` set is cleared when the Arbiter processes the subsequent `UpdateTopology` that removes the dead Arbiter from its neighbor set.
- No wire format changes. No new engine-level concepts. Uses data already available.

**Why not Option B:**
Adding `topology_epoch` to all internal messages would also cause legitimate ghost updates and relays to be rejected during *normal* topology transitions (splits, slides) when the sending Arbiter hasn't yet processed the new epoch. That creates ghost state gaps during routine operations — a worse problem than the one being solved.

## Changes Applied

**`03-mesh-arbiter-state.md`:**
1. Added `fenced_arbiter_ids: HashSet<u32>` field to `SpatialActor` struct.
2. `on_internal_event_rudp`: added `fenced_arbiter_ids` check before queueing.
3. `on_ghost_update_unreliable`: added `fenced_arbiter_ids` check before processing.
4. `AbortPendingHandoffs` handler: populates `fenced_arbiter_ids` with `crashed_arbiter_id` before aborting projectile handoffs.

## WAL Extensibility Constraint

Independent of the fencing resolution: the WAL format used for split/merge topology operations MUST be designed so that it can be reused as the delta journal format for checkpoint-based crash recovery in a future phase (T2-06). Specifically:

- WAL entries MUST remain self-contained (no external state required for replay).
- WAL entry format MUST support versioning so new entry kinds can be added without breaking existing replay consumers.
- WAL serialization MUST be deterministic (byte-identical output for identical logical content).

These constraints are already implied by the determinism mandate (T0-01) but should be explicitly stated as a forward-compatibility requirement when the WAL format is implemented.

## docs-core/ Impact

None for the fencing change. The `fenced_arbiter_ids` mechanism is an implementation detail of the crash cleanup path in the ARPG layer. The engine-level messaging plane contract (`docs-core/02`) does not need changes because the fencing operates on `source_arbiter_id` (already present in internal messages), not on a new epoch or token type.

The WAL extensibility constraint may warrant a note in `docs-core/01-spatial-runtime-kernel.md` when the WAL format is formally specified, but is not blocking.

## References

- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — fenced_arbiter_ids, on_internal_event_rudp, on_ghost_update_unreliable, AbortPendingHandoffs
- `docs/1-architecture/03-mesh-controller.md` §9.2 — Crash Declaration and cleanup
- `docs-core/02-spatial-messaging-plane.md` §5.1 — Topology Epoch Rules (applies to external proposals only)
- `docs/6-spec-drafts/tier-2-contracts/06-surrogate-recovery-and-event-spine.md` — phase 2 surrogate recovery design
