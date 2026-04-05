# ADR-0002: Shield Absorb to Resource to Offense Loop

## Status

Accepted

## Date

2026-04-05

## Context

Closing `SK-70 Energy Shield` exposed that the compiler already supported ordinary shields,
resource pools, and stat layering, but still lacked a canonical way to say:

- each authoritative absorbed amount on a shield grants resource
- that current resource continuously changes present offense

The project needed to decide whether to keep the mechanic blocked, create a bespoke shield-owned
Energy subsystem, or solve it compositionally on the existing shield/resource/stat surfaces.

## Decision

Extend the canonical compiler surface with:

- `apply_shield.bind_absorbed_value_as`
- `apply_shield.on_absorb_effects`
- `modify_resource`
- status-owned `resource_stat_links`

This makes the mechanic an ordinary composition:

1. shield absorbs damage
2. absorbed amount is bound into callback context
3. callback mutates a normal resource pool
4. a status reads the current pool and applies live stat scaling

## Consequences

Positive:

- keeps the mechanic on existing target-owner mutation paths
- works for self-shield and ally-shield credit with one shared contract
- avoids inventing a bespoke Energy subsystem

Negative:

- shield behavior now has a richer callback surface
- resource-to-offense loops need careful validation to remain bounded and legible

Rejected alternatives:

- a bespoke shield-owned Energy state type
- a break-only payoff model with no live absorb-to-offense loop
- leaving the mechanic partially unsupported
