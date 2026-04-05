# ADR-0007: Target-Side Status Consumption for Mass Detonation

## Status

Accepted

## Date

2026-04-05

## Context

Closing `SK-95 Mass Effect Detonation` exposed that the declarative compiler surface could already
represent the burst payloads and mesh-wide timing, but the naive mental model was still a
source-side "caster effect registry." That would have required live cross-Arbiter membership
tracking for every target carrying one of the caster's primer statuses.

## Decision

Keep detonation target-side authoritative.

The detonate ability:

1. schedules one mesh-wide `global_event` execute tick
2. each target owner resolves one exact-match
   `consume_status(target, status_id, source_entity)` against its own active status registry
3. if a matching status from the caster exists, the target owner removes it atomically and emits
   the authored burst payload in that same target context

## Consequences

Positive:

- survives handoffs naturally because the active status registry already lives on the target owner
- avoids stale source-side membership tracking
- composes cleanly with the existing controller-escalated `global_event` path

Negative:

- authors must reason in terms of target-side consumption rather than source-side bookkeeping

Rejected alternatives:

- caster-owned effect registry
- special-case primer/detonator behavior through another subsystem
- bespoke controller broadcast that explicitly names every target
