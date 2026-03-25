# T1-04: Contention Lock Algorithm

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/04-npc-and-world-interaction.md`

## Audit Notes

The requirement (deterministic single-winner) and outcome taxonomy are fully specified. Missing: the algorithm itself.

## Resolution

### 1. Algorithm: Deterministic First-Arrive with EntityID Tie-Break

```rust
fn resolve_contention(lock: &mut ContentionLock, attempts: &[ContentionAttempt], tick: u64) -> EntityID {
    if let Some(winner) = lock.locked_by {
        return winner; // Already locked — all new attempts rejected
    }

    // Sort: earliest arrival tick first, then lowest EntityID for same-tick ties
    let mut sorted = attempts.to_vec();
    sorted.sort_by_key(|a| (a.arrival_tick, a.entity_id));

    let winner = sorted[0].entity_id;
    lock.locked_by = Some(winner);
    lock.locked_at_tick = tick;
    winner
}
```

**Tie-breaking:** Same-tick ties broken by lowest `EntityID` (generational IDs have a stable total order). Deterministic across replay.

### 2. Scope: Per-Arbiter Only

Contention is local to the Arbiter owning the contested entity. Cross-boundary interaction proposals relay to the target's Arbiter and are resolved locally. No distributed locking.

### 3. Lock Duration by Interaction Type

| Interaction | Lock Duration | Notes |
|------------|--------------|-------|
| Loot pickup | 1 tick | Instant claim |
| NPC interaction (vendor, quest) | 0 (no lock) | Concurrent access allowed |
| Objective capture | Channel duration (e.g., 180 ticks) | Broken if interrupted |
| Resource node | Gather duration (e.g., 120 ticks) | Broken if interrupted |

Lock auto-releases at `locked_at_tick + lock_duration_ticks`. Interrupted interactions (CC, death, movement) emit a lock-release mutation.

### 4. Party Loot Mode Interaction

| Mode | Uses Contention Lock? | Resolution |
|------|:---:|---|
| FreeForAll | Yes | First player wins lock → claims item |
| NeedGreed | No | Party-locked entity. Meta runs vote → winner via Recovery Inbox |
| MasterLoot | No | Leader assigns via Meta → recipient via Recovery Inbox |

### 5. Rejected Contenders

```rust
TerminalOutcome::Reject {
    reject_code: "CONTENTION_LOST",
    detail: "Another player claimed this first.",
}
```

Client MAY retry with jittered backoff (client-side).

## References

- `docs/3-gameplay-systems/04-npc-and-world-interaction.md` — Validation gates, determinism mandate
- `docs/1-architecture/02-npc-architecture.md` §8.3 — Single-winner event contract
- `docs/1-architecture/04-meta-services.md` §4.2 — Party loot distribution modes
