# ADR-0001: Bounded Projectile Carry Roster

## Status

Accepted

## Date

2026-04-05

## Context

Closing `SK-55 Growing Projectile` showed that the compiler already covered projectile growth,
payload scaling, wall impact, and single-target sweep capture, but it still lacked one bounded way
for a projectile itself to transport multiple struck entities forward across ordinary projectile
handoff.

The project needed to decide whether to:

- reject that mechanic family outright
- narrow it back to ordinary growth-only projectile damage
- force it into entity-local sweep capture
- or allow projectile actors to own a bounded carried-target set

## Decision

Allow projectile actors to own a bounded ordered carried-target roster through canonical
`ProjectileCarryBlock`.

The roster is projectile-local runtime state capped by `max_carried_targets`.

Carried targets:

- remain ordinary authoritative entities
- suppress independent action while carried
- release at the projectile's committed current position on world impact, expiry, or removal
- transfer across projectile handoff by moving only the ordered target IDs, not serialized entity
  state

`P-06` remains entity-to-entity only.

## Consequences

Positive:

- closes the snowball / rolling multi-carry mechanic family cleanly
- keeps the state bounded and handoff-stable
- avoids widening `P-06` or reusing `P-58` containers for a fundamentally projectile-local problem

Negative:

- projectile actors now own a slightly richer runtime-state shape
- projectile removal/handoff must preserve and release the bounded roster correctly

Rejected alternatives:

- narrowing `SK-55` to growth-only damage with no rolling capture
- forcing the mechanic into entity-local `kinematic_sweep.capture_first`
- modeling the projectile as a container-like transport shell
