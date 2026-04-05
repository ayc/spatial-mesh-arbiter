# ADR-0006: Control-Projection Teardown Callbacks

## Status

Accepted

## Date

2026-04-05

## Context

`SK-81 Remote Control Summon` exposed that `control_projection` already handled routed steering and
owner-body policy, but still lacked a declarative way to distinguish:

- manual detonation
- natural expiry detonation
- controller-break detonation
- enemy destruction with no detonation

Without that distinction, the project would either need a bespoke bomb/drone subsystem or recurring
Lua fallbacks.

## Decision

Extend `control_projection` with bounded teardown callback surfaces:

- `manual_trigger_effects`
- `on_expire_effects`
- `on_controller_break_effects`

Those callbacks execute with:

- `caster = controller`
- `projected_actor`
- `projected_actor_position`

`manual_trigger_effects` also generates one temporary same-slot action for the controller while the
control session is active.

## Consequences

Positive:

- preserves the existing single-actor control model
- gives UI a bounded manual-trigger path without a new input plane
- cleanly distinguishes authored detonation from enemy destruction

Negative:

- teardown semantics are richer and must remain carefully bounded

Rejected alternatives:

- bespoke bomb/drone subsystem
- overloading `on_actor_removed` for all teardown meanings
- requiring imperative Lua for every controlled-shell detonation case
