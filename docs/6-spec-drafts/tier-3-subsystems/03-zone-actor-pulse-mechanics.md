# T3-03: Zone Actor Pulse Mechanics

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/02-ability-framework.md` + `03-global-events.md`

## Audit Notes

**Core pulse mechanics ARE specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| Per-pulse UUID | **Specified** — Each pulse generates a new UUID (UUID_PULSE_1, UUID_PULSE_2, etc.) | `02-ability-framework.md` lines 191-194 |
| Pulse interval/duration | **Specified** — `pulse_interval_ticks`, `duration_ticks` fields | `01-core-primitives.md` lines 239-240 |
| Pulse lifecycle | **Specified** — Duration decremented by interval each pulse, removed from queue when exhausted | `03-mesh-arbiter-state.md` lines 405-413 |
| Mobile zones | **Specified** — "Attached Aura" pattern: ZoneActor parented to entity, position syncs every tick | `02-ability-framework.md` lines 267-273 |

## Remaining Gap (Narrowed)

### 1. Entity Detection Per Pulse
How does the zone determine "who is inside" each pulse? Geometric overlap check via `CollisionGeometry.is_inside_with_tolerance()`? Spatial grid query? The mechanism isn't shown.

### 2. Boundary Crossing Semantics
If an entity enters the zone between pulses, do they get hit on the next pulse? (Assumed yes — each pulse is an independent check — but not explicitly stated.)

### 3. Zone Handoff
If a zone actor's owning Arbiter changes (split/merge), how does the zone's remaining pulse schedule survive?

## Questions to Resolve

- [ ] Per-pulse entity detection method
- [ ] Enter-between-pulses behavior (confirm: next pulse hits them)
- [ ] Zone survival across Arbiter handoff (split/merge)

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/02-ability-framework.md` lines 191-194 — Per-pulse UUID
- `docs/3-gameplay-systems/02-ability-framework.md` lines 267-273 — Attached Aura
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` lines 405-413 — Pulse lifecycle
