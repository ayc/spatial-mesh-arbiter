# T2-06: Surrogate Recovery and Event Spine

> **Status:** DRAFTING
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/03-mesh-controller.md` + `2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` + `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` + `5-testing-and-conformance/01-mini-mesh-conformance.md`

## Problem Statement

Current crash behavior is total-loss for Arbiter soft state and player continuity. This is simple and safe, but it creates player-visible disruption for large battles and leaves no fast-path restoration mechanism between crash and full respawn flow.

This draft defines a surrogate-oriented recovery contract with an optional event spine that can support both:
- high-availability crash continuity (`snapshot(T) + replay deltas`), and
- replay/spectator consumers in a later phase.

## Scope

### In scope

- Quarantine and surrogate takeover protocol after Arbiter crash.
- Edge-assisted recovery behavior (`EmergencyKiDi`, roll-call bundles, action gating).
- Rolling checkpoint + delta journal sidecar contract.
- Event-spine interface for durable replay/recovery streams.
- Phase sequencing (core recovery first, replay/spectator later).

### Out of scope

- Replacing the real-time combat hot path (UDP/RUDP) with Redpanda/Kafka.
- Full spectator product UX/API design.
- Cross-region replication design.

## Proposal Summary

1. **Crash detect + fence:** Mesh Controller declares Arbiter dead and issues a `RecoveryEpoch`; stale writers are fenced.
2. **Quarantine:** Failed cell is sealed temporarily (no enter/exit handoffs).
3. **Immediate edge reaction:** Affected Edge Nodes enter `EmergencyKiDi` and send continuity bundles.
4. **Hot surrogate claim:** Controller assigns a hot Arbiter as surrogate authority for the failed cell.
5. **Reconstruction:** Surrogate rebuilds to `tick T` using checkpoint + delta replay, then fills short tail gap from edge/AI roll-call.
6. **Recovery mode:** Surrogate runs in constrained mode until consistency threshold is reached.
7. **Resume:** Unseal cell and return to normal authority routing.

## Recovery Protocol (Draft)

### 1. Failure Detection and Fencing

- Controller marks Arbiter as dead.
- Controller increments `recovery_epoch`.
- Controller revokes prior lease/fencing token for dead Arbiter.
- Any message stamped with stale fencing token is rejected.

### 2. Cell Quarantine

- Failed cell enters `QUARANTINED`.
- Boundary handoffs are paused.
- Cross-boundary contested effects are deferred or deterministically dropped by policy.

### 3. Edge Surrogate Protocol

On `ExecuteSurrogateProtocol` command:

- Edge enters `EmergencyKiDi` immediately.
- Edge applies recovery action policy:
  - `ALLOW`: movement/facing, self-only defensive intents.
  - `BUFFER`: contested combat intents.
  - `BLOCK`: hard-state/economy/objective mutations.
- Edge sends `ContinuitySnapshot` for sessions mapped to failed cell.

### 4. Surrogate Rebuild

- Load latest committed `CheckpointManifest` for the failed cell.
- Replay contiguous `DeltaRecord`s up to highest verified `delta_seq`.
- Merge roll-call tail-gap data with deterministic tie-break rules.
- Start authoritative loop in `RECOVERY_MODE`.

### 5. Resume Criteria

- Coverage threshold met (sufficient edge/AI snapshot participation).
- No unresolved delta gaps in required replay horizon.
- Consistency hash checks pass for configured stability window.
- Controller transitions cell to `ACTIVE` and unseals boundaries.

## Data Contract Sketch

```rust
struct QuarantineCommand {
    cell_id: u32,
    failed_arbiter_id: u32,
    surrogate_arbiter_id: u32,
    recovery_epoch: u32,
    quarantine_start_tick: u64,
}

struct ContinuitySnapshot {
    edge_node_id: u32,
    recovery_epoch: u32,
    cell_id: u32,
    last_authoritative_tick_seen: u64,
    sessions: Vec<SessionContinuity>,
    sent_at_tick: u64,
}

struct SessionContinuity {
    character_id: UUID,
    entity_id: EntityID,
    last_input_seq: u64,
    last_ack_seq: u64,
    predicted_state: SoftStateLite,
    buffered_proposals: Vec<ActionProposalLite>,
}

struct CheckpointManifest {
    checkpoint_id: UUID,
    cell_id: u32,
    tick: u64,
    topology_epoch: u32,
    data_epoch: u32,
    recovery_epoch: u32,
    last_delta_seq: u64,
    state_hash: [u8; 32],
    committed: bool,
}

struct DeltaRecord {
    cell_id: u32,
    delta_seq: u64,
    tick: u64,
    kind: DeltaKind,
    payload: Vec<u8>,
}
```

## Exact Wire Contracts (Draft v0)

This section defines concrete envelope shapes to seed canonical promotion into:
- `ControllerCommand` (control plane),
- arbiter/edge recovery envelopes,
- sidecar recovery journal records.

### 1. Control Plane Commands

```rust
enum ControllerCommand {
    BeginRecoveryQuarantine {
        recovery_id: UUID,
        failed_arbiter_id: u32,
        surrogate_arbiter_id: u32,
        cell_id: u32,
        recovery_epoch: u32,     // Monotonic fencing epoch
        quarantine_start_tick: u64,
        quarantine_ttl_ticks: u64,
        hard_kidi_factor: SimFixed, // e.g. 0.15
    },

    EndRecoveryQuarantine {
        recovery_id: UUID,
        cell_id: u32,
        recovery_epoch: u32,
        resume_tick: u64,
    },

    AbortRecoveryQuarantine {
        recovery_id: UUID,
        cell_id: u32,
        recovery_epoch: u32,
        reason: String, // "InsufficientCoverage" | "DeltaGap" | "SurrogateUnhealthy" | ...
    },
}
```

### 2. Edge Recovery Notice and Roll-Call

```rust
enum EdgeControlNoticeType {
    ExecuteSurrogateProtocol,
    SurrogateRecoveryReady,
    SurrogateRecoveryAborted,
}

struct ExecuteSurrogateProtocolNotice {
    recovery_id: UUID,
    cell_id: u32,
    failed_arbiter_id: u32,
    surrogate_arbiter_id: u32,
    recovery_epoch: u32,
    hard_kidi_factor: SimFixed,
    quarantine_ttl_ticks: u64,
    action_policy: RecoveryActionPolicy,
}

struct ContinuitySnapshot {
    recovery_id: UUID,
    edge_node_id: u32,
    cell_id: u32,
    recovery_epoch: u32,
    last_authoritative_tick_seen: u64,
    continuity_seq: u64, // monotonic per (edge_node_id, recovery_id)
    sessions: Vec<SessionContinuity>,
    sent_at_tick: u64,
}

struct ContinuitySnapshotAck {
    recovery_id: UUID,
    edge_node_id: u32,
    continuity_seq: u64,
    accepted_session_count: u32,
}
```

### 3. Surrogate <-> Controller Recovery Status

```rust
enum RecoveryPhase {
    Quarantined,
    ReplayingJournal,
    MergingRollCall,
    Stabilizing,
    ReadyToResume,
    Aborted,
}

struct RecoveryStatus {
    recovery_id: UUID,
    cell_id: u32,
    recovery_epoch: u32,
    phase: RecoveryPhase,
    replayed_to_delta_seq: u64,
    replayed_to_tick: u64,
    expected_edge_count: u32,
    received_edge_count: u32,
    stable_tick_count: u32,
    current_state_hash: [u8; 32],
    error: Option<String>,
}
```

### 4. Sidecar Journal Records

```rust
struct RecoveryCheckpointChunk {
    checkpoint_id: UUID,
    cell_id: u32,
    chunk_index: u16,
    chunk_count: u16,
    compressed_payload: Vec<u8>,
    chunk_checksum: [u8; 32],
}

struct RecoveryCheckpointManifest {
    checkpoint_id: UUID,
    cell_id: u32,
    tick: u64,
    topology_epoch: u32,
    data_epoch: u32,
    recovery_epoch: u32,
    last_delta_seq: u64,
    state_hash: [u8; 32],
    chunk_count: u16,
    committed: bool, // true only after all chunks durably persisted
}

struct RecoveryDelta {
    cell_id: u32,
    delta_seq: u64, // strict monotonic sequence per cell
    tick: u64,
    topology_epoch: u32,
    recovery_epoch: u32,
    kind: DeltaKind,
    payload: Vec<u8>, // self-contained deterministic mutation
}
```

## Deterministic Replay and Merge Rules (Normative Draft)

### 1. Replay Rule

Authoritative rebuild order is always:
1. latest committed checkpoint `snapshot(T)`,
2. replay contiguous `delta_seq` from `T+1` forward,
3. merge roll-call tail-gap data if and only if journal has a gap or stale tail.

### 2. Delta Ordering Rule

- Sort by `delta_seq` only.
- `tick` is informational for validation/monitoring and must not override `delta_seq` order.
- Missing `delta_seq` values create a hard gap; surrogate cannot claim `ReadyToResume` until resolved or policy fallback is chosen.

### 3. Roll-Call Merge Tie-Break Rule

For conflicting per-entity edge snapshots, choose winner using:
1. highest `last_authoritative_tick_seen`,
2. highest `last_ack_seq`,
3. highest `last_input_seq`,
4. stable hash tie-break on `(edge_node_id, entity_id)` (ascending).

No non-deterministic tie-breakers are allowed.

### 4. Proposal Re-Application Rule

- Replayed/buffered proposals must preserve original `proposal_id` and `origin_tick`.
- Re-application order is deterministic by `(origin_tick, proposal_id)`.
- Idempotency ledgers remain authoritative for dedupe; never synthesize new `proposal_id` values during rebuild.

## Recovery Action Policy Matrix (Draft)

```rust
enum RecoveryActionClass {
    MovementFacing,          // movement/facing updates
    SelfDefensiveNonDurable, // shield/dodge/self-only defensive activations
    ContestedCombat,         // target-lock/projectile/offensive contested actions
    ObjectiveMutation,       // capture/interact that mutates objective state
    EconomyMutation,         // loot claim/inventory/currency mutations
}

enum RecoveryActionPolicy {
    Allow,
    Buffer,
    Block,
}
```

Default matrix in `QUARANTINED` + `RECOVERY_MODE`:
- `MovementFacing` -> `Allow`
- `SelfDefensiveNonDurable` -> `Allow`
- `ContestedCombat` -> `Buffer`
- `ObjectiveMutation` -> `Block`
- `EconomyMutation` -> `Block`

## Fallback and Abort Semantics (Normative Draft)

### 1. Quarantine TTL Expiry

If `quarantine_ttl_ticks` elapses before `ReadyToResume`:
- Controller sends `AbortRecoveryQuarantine`.
- Surrogate stops accepting buffered contested actions for that recovery window.
- Affected sessions fall back to standard spawn/reconnection flow.

### 2. Coverage Failure

If `received_edge_count / expected_edge_count` remains below threshold (configurable) after grace window:
- recovery is aborted with reason `InsufficientCoverage`.
- surrogate may perform partial safe-state despawn policy for unresolved entities.

### 3. Delta Gap Failure

If journal replay has unresolved hard gap and roll-call cannot deterministically fill:
- recovery is aborted with reason `DeltaGap`.
- no contested buffered actions are committed.

### 4. Split-Brain Guard

At any point, if surrogate observes writes with stale fencing token or duplicate active lease holder:
- transition to `Aborted`,
- freeze contested actions,
- emit critical control-plane alert.

## Rolling Checkpoint Requirements (Draft)

- Checkpoint cadence target: every `100-250ms` (adaptive by load).
- Delta journal: ordered, monotonic `delta_seq`, self-contained deterministic payloads.
- Required snapshot domains:
  - authoritative entities,
  - NPC FSM/runtime state,
  - projectile/zone actor state,
  - idempotency and proposal dedupe windows,
  - pending deterministic schedulers.
- Sidecar write path must be non-blocking to 60Hz loop.
- Checkpoints must be replicated off-host to survive node loss.

## Event Spine (Draft Direction)

Event spine is an asynchronous durable backbone for replay/recovery consumers.

### Phase 1 target

- Keep gameplay hot path as-is (UDP/RUDP + controller TCP).
- Use sidecar checkpoint+delta stream for surrogate recovery only.

### Phase 2 target

- Add durable event-spine broker for replay and downstream consumers.
- Candidate implementation: Redpanda topics keyed by `cell_id` (strict per-cell ordering).
- Spectator/replay consumers must be isolated from recovery-critical consumers.

## Phasing

### Phase 1 (core crash continuity)

- Fencing + `RecoveryEpoch`.
- Quarantine + surrogate assignment.
- Edge `EmergencyKiDi` + continuity roll-call.
- Sidecar checkpoint+delta replay path.

### Phase 1.5 (hardening)

- Recovery chaos drills.
- Hash drift alarms.
- SLO guardrails and auto-abort behavior.

### Phase 2 (platform expansion)

- Event spine productization.
- Replay consumers.
- Live spectator mode.

## Acceptance Criteria (Draft)

- Crash-to-surrogate authority handoff p99 <= `1500ms` for hot surrogate path.
- No stale fenced writer accepted after `RecoveryEpoch` transition.
- Deterministic replay from `checkpoint + deltas` reconstructs cell to expected state hash in conformance suite.
- Quarantine action-gating policy is enforced and observable.
- Recovery tests exist for:
  - missing edge snapshots,
  - stale/duplicate continuity bundles,
  - delta gap handling,
  - split-brain prevention via fencing.

## Open Questions

- What is the exact quarantine TTL before hard fallback?
- Which contested action classes are buffered vs blocked?
- What is the minimum coverage threshold for resume?
- Should AI Node snapshots be mandatory for resume?
- What is the required off-host replication durability policy for checkpoints/deltas?
- If Redpanda is selected in Phase 2, what are the exact topic boundaries and retention windows?

## References

- `docs/1-architecture/01-core-concepts-and-mesh.md` §6, §7, §9.7
- `docs/1-architecture/03-mesh-controller.md` §5, §6, §9, §13
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md`
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md`
- `docs/5-testing-and-conformance/01-mini-mesh-conformance.md`
