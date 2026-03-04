# T2-05: HardEvent Consumption Contract

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md`

## Audit Notes

**The consumption framework IS substantially specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| Offset commit requirement | **Specified** — Consumers must commit offsets after durable processing | `01-core-concepts-and-mesh.md` §9.3 Durability Contract |
| At-least-once delivery | **Specified** — Guaranteed by consumer group replay of uncommitted offsets | `01-core-concepts-and-mesh.md` §9.3 Durability Contract |
| Idempotency mandate | **Specified** — Events carry unique `event_id` (UUID) for dedup | `01-core-concepts-and-mesh.md` §9.3 Durability Contract |
| Consumer groups | **Specified** — Per-service groups (e.g., `group.progression`, `group.loot`) | `01-core-concepts-and-mesh.md` §9.3 |
| Ordering | **Specified** — Per topic partition, not global | `01-core-concepts-and-mesh.md` §9.3 Durability Contract |
| Scaling thresholds | **Specified** — Lag >1000 → scale up, >5000 → critical alert, p99 >500ms → investigate | `01-core-concepts-and-mesh.md` §9.3 |
| Topic retention | **Specified** — Broker-managed by time/size | `01-core-concepts-and-mesh.md` §9.3 Durability Contract |
| EventBus trait | **Specified** — publish/subscribe/ack abstraction | `01-core-concepts-and-mesh.md` lines 554-571 |
| Loot source of truth | **Specified** — `loot.drops` Postgres row, atomic UPDATE | `04-meta-services.md` line 1071 |

## Remaining Gap (Narrowed)

### 1. Commit Timing
Offset commit order vs Postgres commit needs explicit per-service rules (recommended: commit only after DB commit and side effects are durable).

### 2. Retry / Dead Letter Policy
Redelivery and retries are implicit in offset replay, but policy is still missing:
- max processing retry attempts before quarantine,
- dead-letter topic naming and retention,
- backoff and poison-pill handling.

### 3. Per-Service Idempotency Mechanism
The requirement (dedup by event_id) is stated but implementation pattern is not. Postgres upsert? In-memory LRU cache? Both?

### 4. Poison Pill Handling
If an event causes a consumer to crash repeatedly, no mechanism to quarantine it.

## Questions to Resolve

- [ ] Mandated commit pattern: commit-after-persist only?
- [ ] Max retry count before dead letter
- [ ] Dead-letter topic contract (`deadletter.<service>.<source_topic>`)?
- [ ] Per-service idempotency pattern (Postgres upsert recommended?)
- [ ] Poison pill / dead letter queue strategy

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/01-core-concepts-and-mesh.md` §9.3 — Durability Contract, EventBus trait
- `docs/2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md` — HardEvent enum, publisher
- `docs/1-architecture/04-meta-services.md` — Event Bus Subscription Matrix, loot source of truth
