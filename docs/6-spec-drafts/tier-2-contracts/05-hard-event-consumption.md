# T2-05: HardEvent Consumption Contract

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md`

## Audit Notes

**The consumption framework IS substantially specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| XACK requirement | **Specified** — Consumers must explicitly ack via XACK | `01-core-concepts-and-mesh.md` line 548 |
| At-least-once delivery | **Specified** — Guaranteed by Redis Streams consumer groups | `01-core-concepts-and-mesh.md` line 547 |
| Idempotency mandate | **Specified** — Events carry unique `event_id` (UUID) for dedup | `01-core-concepts-and-mesh.md` line 549 |
| Consumer groups | **Specified** — Per-service groups (e.g., `group:progression`, `group:loot`) | `01-core-concepts-and-mesh.md` lines 604-610 |
| Ordering | **Specified** — Per-stream, not global | `01-core-concepts-and-mesh.md` line 550 |
| Scaling thresholds | **Specified** — Lag >1000 → scale up, >5000 → critical alert, p99 >500ms → investigate | `01-core-concepts-and-mesh.md` lines 612-617 |
| Stream retention | **Specified** — Trimmed by age/MAXLEN | `01-core-concepts-and-mesh.md` line 551 |
| EventBus trait | **Specified** — publish/subscribe/ack abstraction | `01-core-concepts-and-mesh.md` lines 554-571 |
| Loot source of truth | **Specified** — `loot.drops` Postgres row, atomic UPDATE | `04-meta-services.md` line 1071 |

## Remaining Gap (Narrowed)

### 1. Ack Timing
When should XACK occur relative to Postgres commit? If consumer crashes between persist and ack, the event is redelivered — consumer must handle this idempotently. But is "ack after persist" the mandated pattern?

### 2. Retry / Dead Letter Policy
"Unacknowledged events are redelivered after a configurable visibility timeout" — but what is the timeout value? Max retries before dead letter? Backoff strategy?

### 3. Per-Service Idempotency Mechanism
The requirement (dedup by event_id) is stated but implementation pattern is not. Postgres upsert? In-memory LRU cache? Both?

### 4. Poison Pill Handling
If an event causes a consumer to crash repeatedly, no mechanism to quarantine it.

## Questions to Resolve

- [ ] Mandated ack pattern: ack-after-persist or ack-after-process?
- [ ] Visibility timeout value
- [ ] Max retry count before dead letter
- [ ] Per-service idempotency pattern (Postgres upsert recommended?)
- [ ] Poison pill / dead letter queue strategy

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/01-core-concepts-and-mesh.md` §9.3 — Durability Contract, EventBus trait
- `docs/2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md` — HardEvent enum, publisher
- `docs/1-architecture/04-meta-services.md` — Event Bus Subscription Matrix, loot source of truth
