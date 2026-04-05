# ADR-0004: Late-Bound Actor Transit

## Status

Accepted

## Date

2026-04-05

## Context

Re-auditing `SK-98 Mobile Transport` showed that containment was already canonical through `P-58`,
but the compiler still lacked a clean way to say "this already-spawned shell now flies to the
chosen point at speed X and does landing effects on arrival." The alternative was to turn this into
a spawn-local vehicle phase or a bespoke vehicle subsystem.

## Decision

Add `start_actor_transit` as a narrow late-bound transit effect.

It:

- targets one existing live actor
- snapshots one authored destination position
- drives fixed-speed straight-line travel across ordinary handoff boundaries
- exposes `transit_actor` / `transit_actor_position` only to arrival callbacks

Transit is separate from spawn and separate from ordinary `displacement`.

## Consequences

Positive:

- preserves late-launch timing for transport shells
- reuses existing actor, containment, lifecycle, and handoff rules
- avoids inventing a general vehicle-state subsystem too early

Negative:

- adds a distinct movement contract that must stay narrowly scoped

Rejected alternatives:

- `spawn_actor.transit` with destination fixed at spawn time
- overloading `displacement` for long-lived shell transit
- a bespoke vehicle phase/state framework
