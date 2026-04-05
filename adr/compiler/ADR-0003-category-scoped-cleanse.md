# ADR-0003: Category-Scoped Cleanse

## Status

Accepted

## Date

2026-04-05

## Context

Closing `SK-51 Unstoppable` exposed that polarity-based cleanse was too broad for
"strip active crowd control but not unrelated negative statuses." The project already had
`cc_immunity_categories` for future-CC blocking, but it lacked a precise way to remove currently
active CC without also purging effects like anti-heal or damage-over-time.

## Decision

Extend `cleanse` with optional `cc_categories`.

A cleanse may now:

- match by polarity and/or cleansability
- then further narrow removals to statuses whose compiled `cc_category` is in the authored set

Unstoppable-style mechanics use this path to strip active CC and then apply a matching immunity
window, rather than using a broad "remove all negatives" purge.

## Consequences

Positive:

- lets authors remove crowd control without silently purging unrelated debuffs
- reuses CC metadata the project already needs for DR and immunity
- keeps cleanse behavior compositional instead of adding a separate anti-CC subsystem

Negative:

- cleanse authoring is slightly more expressive and therefore slightly more complex

Rejected alternatives:

- broad negative-polarity purge
- manually maintained lists of every CC status ID
- leaving CC-only cleanse unsupported
