# T3-10: LFG Matching Lifecycle

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/04-meta-services.md`

## Problem Statement

LFG has Enqueue/Dequeue/MatchFound but the post-match lifecycle is missing: accept/decline, timeouts, partial decline handling, group binding, and disconnect during acceptance.

## Resolution

### 1. Post-Match Accept/Decline Flow

```
Meta Service finds a valid match (role composition satisfied)
  ↓
Meta → each matched player's Edge Node: LfgMatchProposed {
    match_id, role_assignments, dungeon_id, accept_deadline_tick
}
  ↓
Each player: Accept or Decline (or timeout)
  ↓
Meta collects responses
```

### 2. Acceptance Timeout

| Parameter | Value | Notes |
|-----------|-------|-------|
| `lfg_accept_timeout_seconds` | 30 | Configurable. Starts when `LfgMatchProposed` is sent. |
| `lfg_accept_grace_ticks` | 60 | 1-second grace for network latency |

If a player does not respond within the timeout, they are treated as a decline.

### 3. Response Handling

```
All accepted → Group is formed (§4)
One or more declined/timed out → Partial decline handling (§3.1)
```

#### 3.1 Partial Decline Handling

**Rule:** On any decline or timeout, the match is dissolved. Players who accepted are re-queued automatically with priority (they go to the front of the queue, not the back).

```
Player A: Accept
Player B: Accept
Player C: Decline
Player D: Accept

Result:
  - Match dissolved
  - Players A, B, D re-queued with priority flag
  - Player C removed from queue (voluntary decline)
  - Player C receives a short re-queue cooldown (60 seconds)
```

| Scenario | Declining Player | Accepting Players |
|----------|-----------------|-------------------|
| Voluntary decline | Removed from queue + 60s cooldown | Re-queued with priority |
| Timeout (no response) | Removed from queue + 60s cooldown | Re-queued with priority |
| Disconnect during acceptance | Treated as timeout | Re-queued with priority |

**Repeated declines:** After 3 declines within 30 minutes, the player receives a longer cooldown (15 minutes). This prevents queue trolling.

### 4. Group Binding

On all-accept:

1. **Party creation:** Meta Service auto-creates a party with the matched players. If any player is already in a party, they are removed from their current party first (with notification).
2. **Instance reservation:** Meta Service reserves a dungeon instance (Spatial Instance Forking, P-56, or a dedicated Arbiter depending on the content).
3. **Teleport offer:** Each player receives `LfgTeleportReady { instance_id, entry_position }`. They can accept the teleport or travel manually.
4. **Teleport timeout:** If a player doesn't teleport within `lfg_teleport_timeout_seconds` (default: 120s / 2 minutes), they remain in the overworld. The dungeon proceeds with whoever teleported in.

### 5. Disconnect During Acceptance

If a player disconnects (WebSocket close) during the acceptance window:

1. The session orphaning mechanism (6s heartbeat TTL) takes effect.
2. If the player reconnects before `lfg_accept_timeout_seconds`: they can still accept/decline.
3. If they don't reconnect in time: treated as timeout (§3.1).

### 6. MetaRequest Additions

The following MetaRequest variants are needed (currently missing from the enum):

| Variant | Direction | Payload |
|---------|-----------|---------|
| `LfgAcceptMatch` | Client → Meta | `{ match_id }` |
| `LfgDeclineMatch` | Client → Meta | `{ match_id }` |
| `LfgTeleportAccept` | Client → Meta | `{ instance_id }` |

These should be added to the MetaRequest enum in `02-edge-node-envelopes.md`.

### 7. Configuration

```json
"lfg": {
    "accept_timeout_seconds": 30,
    "teleport_timeout_seconds": 120,
    "decline_cooldown_seconds": 60,
    "repeated_decline_threshold": 3,
    "repeated_decline_window_minutes": 30,
    "repeated_decline_long_cooldown_minutes": 15,
    "auto_requeue_on_partial_decline": true
}
```

## References

- `docs/1-architecture/04-meta-services.md` §8 — Party & Guild Service, LFG
- `docs/2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md` — LfgEnqueue, LfgMatchFound
- `docs-core/01-4-dynamic-topology-contract.md` §3 — Spatial Instance Forking for dungeon instances
