# T2-05: HardEvent Consumption Contract

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md`

## Audit Notes

The consumption framework is substantially specified: offset commit requirement, at-least-once delivery, idempotency mandate, consumer groups, ordering, scaling thresholds, topic retention, and EventBus trait. Missing: commit timing, retry policy, dead letter handling, and idempotency implementation pattern.

## Resolution

### 1. Commit Timing: Commit-After-Persist

**Rule:** A consumer MUST NOT commit its offset until ALL side effects of the event are durably persisted.

```
1. Receive event from topic
2. Process event (compute side effects)
3. Persist side effects to durable store (Postgres INSERT/UPDATE)
4. Only after Postgres commit succeeds: commit consumer offset to Redpanda
```

If the consumer crashes between step 3 and step 4, the event will be redelivered. The idempotency mechanism (§3) prevents duplicate side effects.

**Anti-pattern:** Committing offset before Postgres persist. This loses events on crash.

### 2. Retry and Dead Letter Policy

```rust
const HARDEVENT_MAX_PROCESSING_ATTEMPTS: u32 = 5;
const HARDEVENT_RETRY_BACKOFF: [Duration; 5] = [
    Duration::from_millis(100),
    Duration::from_millis(500),
    Duration::from_secs(2),
    Duration::from_secs(10),
    Duration::from_secs(30),
];
```

| Attempt | Backoff | Behavior |
|---------|---------|----------|
| 1 | 0 (immediate) | Process event |
| 2 | 100ms | Retry same event |
| 3 | 500ms | Retry |
| 4 | 2s | Retry |
| 5 | 10s | Retry |
| 6 | — | Send to dead-letter topic + commit offset |

### Dead-Letter Topic Naming

```
deadletter.<consumer_group>.<source_topic>
```

Example: `deadletter.group.progression.hard_events.kills`

Dead-letter messages carry:
```json
{
    "original_event": { /* full HardEvent payload */ },
    "failure_reason": "string",
    "attempt_count": 5,
    "first_failure_at": "ISO8601",
    "last_failure_at": "ISO8601",
    "consumer_group": "group.progression",
    "source_topic": "hard_events.kills",
    "source_partition": 3,
    "source_offset": 12847
}
```

Dead-letter topics have extended retention (30 days). Ops tooling can replay dead-letter events after the root cause is fixed.

### 3. Per-Service Idempotency: Postgres Upsert

**Recommended pattern:** Each consumer service maintains an `event_dedup` table:

```sql
CREATE TABLE event_dedup (
    event_id    UUID PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    consumer_group TEXT NOT NULL
);

-- TTL: rows older than 7 days are pruned by a scheduled job
```

On each event:
```sql
INSERT INTO event_dedup (event_id, consumer_group)
VALUES ($1, $2)
ON CONFLICT (event_id) DO NOTHING
RETURNING event_id;
```

If the INSERT returns no rows (conflict), the event was already processed → skip. If it returns a row, proceed with processing. This is atomic with the side-effect transaction.

**Alternative for high-throughput consumers:** In-memory LRU cache (bounded, e.g., 100K entries) as a fast-path check before the Postgres upsert. Cache miss falls through to Postgres.

### 4. Poison Pill Handling

A poison pill is an event that causes repeated consumer crashes. The retry mechanism (§2) handles this:

1. After `HARDEVENT_MAX_PROCESSING_ATTEMPTS` failures, the event is sent to the dead-letter topic.
2. The consumer commits the offset and moves on to the next event.
3. The dead-letter event is logged with full failure context for investigation.
4. An operational alert (`HARDEVENT_DEAD_LETTERED`) is emitted.

**Critical:** The consumer MUST NOT block the partition indefinitely on a single failing event. The dead-letter mechanism ensures forward progress.

### 5. Baseline Profile Keys

```
hardevent_max_processing_attempts:  5
hardevent_deadletter_retention_days: 30
hardevent_dedup_ttl_days: 7
hardevent_lag_warn_threshold: 1000
hardevent_lag_critical_threshold: 5000
hardevent_p99_latency_warn_ms: 500
```

## References

- `docs/1-architecture/01-core-concepts-and-mesh.md` §9.3 — Durability Contract, EventBus trait
- `docs/2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md` — HardEvent enum
- `docs/6-spec-drafts/tier-2-contracts/07-redpanda-adoption-adr.md` — Redpanda as event bus
