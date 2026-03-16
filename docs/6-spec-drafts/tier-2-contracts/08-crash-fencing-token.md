# T2-08: Crash Fencing Token Formalization

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Extracted From:** [T2-06: Surrogate Recovery and Event Spine](06-surrogate-recovery-and-event-spine.md) (deferred to phase 2)
> **Canonical Target:** `1-architecture/03-mesh-controller.md` + `1-architecture/01-core-concepts-and-mesh.md`

## Problem Statement

When an Arbiter crashes, the Mesh Controller declares it dead and neighbors absorb its region. However, the mechanism for **rejecting stale messages** from the dead Arbiter (or from Edge/AI Nodes still addressing it) is not formally specified.

The current crash protocol (§9.7 of `01-core-concepts-and-mesh.md`) describes the topology repair and entity destruction flow but does not define:

1. How neighbors and the Controller distinguish "messages from a dead Arbiter that arrived late" from "messages from the live replacement."
2. What token or epoch is used to fence the dead Arbiter's writes.
3. How Edge Nodes that were mid-flight to the dead Arbiter learn their proposals are no longer valid.

The topology epoch increment on crash covers the case where an Edge Node sends a proposal with a stale `topology_epoch` — `docs-core/02-spatial-messaging-plane.md` §5.1 handles this via forwarding. But there is no explicit **per-Arbiter authority token** that is revoked on crash and checked on receipt.

### Relationship to topology epoch

The topology epoch already handles most stale message scenarios: when the Controller issues `UpdateTopology` to absorb the dead cell, the epoch increments and stale-epoch messages are forwarded or rejected per the messaging plane contract. This gap is about whether the topology epoch is **sufficient** as the sole fencing mechanism, or whether an additional per-Arbiter lease/token is needed to cover edge cases like:

- Messages in flight between the crash and the topology epoch propagation (the window between heartbeat failure detection and `UpdateTopology` delivery to all neighbors).
- Internal mesh messages (Arbiter-to-Arbiter RUDP) that arrive after the sender is declared dead but before the receiver has processed the new topology epoch.

## Scope

### In scope

- Formalize whether `topology_epoch` alone is sufficient for crash fencing, or whether an additional per-Arbiter lease token is required.
- Define the acceptance rule for internal mesh messages (RUDP) arriving from a dead Arbiter during the detection-to-topology-update window.
- Define the Edge Node behavior when proposals are in flight to a dead Arbiter.
- Ensure the split/merge WAL format is designed to be extensible for future checkpoint+delta crash recovery (T2-06 phase 2).

### Out of scope

- Surrogate recovery, quarantine protocol, or checkpoint+delta replay (T2-06, phase 2).
- RecoveryEpoch as a new epoch type (T2-06, phase 2).
- Edge degraded mode / EmergencyKiDi (T2-06, phase 2).

## Analysis Direction

### Option A: Topology epoch is sufficient

The simplest resolution. The crash detection window (~3 seconds) is bounded, and the messaging plane already handles stale-epoch messages. Late-arriving RUDP messages from the dead Arbiter are harmless because:

- Ghost updates from a dead source are garbage-collected when neighbors process `UpdateTopology`.
- `ImpactEvent` relays stamped with a stale topology epoch are rejected or forwarded per §5.1.
- Edge proposals to the dead Arbiter's UDP endpoint fail at the transport layer (dead socket) and the Edge reconnection flow (§9.4) handles re-routing.

If this option holds, the gap is resolved by adding an explicit normative statement to the crash recovery section confirming that `topology_epoch` is the fencing mechanism and documenting the bounded window behavior.

### Option B: Per-Arbiter lease token

If the topology epoch alone leaves gaps (e.g., RUDP messages that bypass epoch checks, or internal messages that are processed before the topology update arrives), introduce a lightweight per-Arbiter `authority_lease` that is:

- Issued by the Controller on Arbiter registration.
- Included in internal mesh message headers.
- Revoked on crash declaration.
- Checked by receivers alongside `topology_epoch`.

This adds wire format overhead (one u64 per internal message) but closes any window between crash detection and topology propagation.

## WAL Extensibility Constraint

Independent of the fencing resolution: the WAL format used for split/merge topology operations MUST be designed so that it can be reused as the delta journal format for checkpoint-based crash recovery in a future phase. Specifically:

- WAL entries MUST remain self-contained (no external state required for replay).
- WAL entry format MUST support versioning so new entry kinds can be added without breaking existing replay consumers.
- WAL serialization MUST be deterministic (byte-identical output for identical logical content).

These constraints are already implied by the determinism mandate (T0-01) but should be explicitly stated as a forward-compatibility requirement in the WAL contract.

## Open Questions

- Does any internal mesh message bypass topology epoch validation today? If not, Option A likely holds.
- What is the maximum in-flight message count during the ~3 second detection window, and are those messages all harmless if processed against stale state?
- Should the WAL extensibility constraint be promoted into `docs-core/01-spatial-runtime-kernel.md` or kept in the ARPG layer?

## References

- `docs/1-architecture/01-core-concepts-and-mesh.md` §9.7 (Arbiter Crash Recovery)
- `docs/1-architecture/03-mesh-controller.md` §9.2 (Heartbeat/Crash Detection)
- `docs-core/02-spatial-messaging-plane.md` §5.1 (Topology Epoch Rules)
- `docs-core/02-spatial-messaging-plane.md` §5.3 (Bounded Timeout Rule)
- `docs-core/05-2-core-conformance-scenario-catalog.md` SCN-MSG-STALE-TIMEOUT
- `docs/6-spec-drafts/tier-2-contracts/06-surrogate-recovery-and-event-spine.md` (phase 2 surrogate recovery design)
