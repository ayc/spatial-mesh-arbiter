# T2-07: Redpanda Event Bus Adoption ADR

> **Status:** DRAFTING  
> **Date:** 2026-03-04  
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)  
> **Canonical Target:** `1-architecture/01-core-concepts-and-mesh.md` + `1-architecture/04-meta-services.md` + `0-getting-started/02-implementation-phases.md`

## Decision

Adopt **Redpanda (Kafka API)** as the primary Event Bus transport from initial implementation (day 1) for:
- hard-state events (`hard_state.arbiter.{arbiter_id}`),
- inbound arbiter commands (`arbiter.{arbiter_id}.commands`),
- controller crash/control events (`controller.mesh.events`).

Redis remains in scope for Session Manager registry/caching and is not used as the primary event stream transport.

## Context

This codebase is not yet productionized and has no live Redis Streams traffic to migrate.  
A runtime dual-write cutover plan is unnecessary at this stage and would add complexity without benefit.

## Why

1. Avoids building and validating two broker paths before first release.
2. Aligns implementation directly with replay/spectator/event-spine direction.
3. Keeps contracts stable early (`topic`, partition, offset, consumer group semantics).

## Non-Goals

- No change to 60Hz simulation hot path (UDP/RUDP).
- No replacement of Session Manager Redis key-value contracts.
- No requirement to maintain Redis Streams compatibility in production.

## Implementation Plan (Normative Draft)

### Phase A: Broker and Topic Bootstrap

1. Provision Redpanda cluster and topic set from [Core Concepts §9.3](../../1-architecture/01-core-concepts-and-mesh.md).
2. Disable broker auto-topic-creation in all environments.
3. Create DLQ topics with explicit retention and ACLs.

### Phase B: Producer Integration

1. Implement `EventBus` producer on Redpanda/Kafka client (`acks=all`, idempotent producer).
2. Wire Arbiter hard-state publisher to `hard_state.arbiter.{arbiter_id}`.
3. Wire Meta/Session command publishers to `arbiter.{arbiter_id}.commands`.
4. Wire Controller crash/control events to `controller.mesh.events`.

### Phase C: Consumer Integration

1. Implement consumer groups with offset commit after durable side effects.
2. Enforce idempotency by `event_id` for all consumers.
3. Implement retry budget and DLQ publish contract.

### Phase D: Conformance and Failure Drills

1. Add test scenarios for:
   - rebalance during load,
   - crash before commit (at-least-once replay validation),
   - poison event path to DLQ,
   - lag alert thresholds and recovery.
2. Validate no Arbiter 60Hz regression under broker slowdown (publisher backpressure path).

### Phase E: Release Readiness

1. Freeze topic naming/versioning.
2. Publish runbooks and alerts for lag, produce error rate, and DLQ rate.
3. Remove any temporary Redis Streams placeholders from code/docs before first release.

## Rollback and Contingency

Because there is no production cutover, rollback is release gating rather than runtime transport switch:

1. If broker conformance fails, block release and fix Redpanda path.
2. If severe unresolved broker risk remains, defer launch scope of dependent features (e.g., spectator) but keep hard-state path contract intact.
3. Do not introduce an unplanned Redis dual-stack fallback unless explicitly approved as a new ADR.

## Acceptance Criteria

1. All Event Bus producers/consumers run against Redpanda in conformance environments.
2. At-least-once + idempotency behavior is proven in failure drills.
3. DLQ contract is implemented and observable.
4. Topic provisioning, ACLs, and retention are automated in infrastructure code.
5. No Redis Streams dependency remains in implementation mandates for production path.

## Open Questions

1. Exact initial partition count policy for `controller.mesh.events` (fixed vs adaptive)?
2. Per-service retry budget defaults before DLQ publish?
3. Required non-prod footprint (single-broker dev mode vs 3-broker staging)?
4. Do we keep a Redis transport adapter only for local developer experimentation?

## References

- [Core Concepts and Mesh §9.3](../../1-architecture/01-core-concepts-and-mesh.md)
- [Meta Services Architecture §1, §7](../../1-architecture/04-meta-services.md)
- [Implementation Phases & Mandates](../../0-getting-started/02-implementation-phases.md)
- [Hard-State Events](../../2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md)
