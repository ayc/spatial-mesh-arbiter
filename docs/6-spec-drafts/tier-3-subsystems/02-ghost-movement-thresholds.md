# T3-02: Ghost Movement Thresholds

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md`

## Problem Statement

Ghost anomaly detection uses `GhostMovementClass` (Normal, HighSpeed, Teleport) to determine expected displacement per tick. But the classification thresholds are missing:

- What velocity marks the boundary between Normal and HighSpeed?
- What displacement marks a Teleport vs a HighSpeed movement?
- How is a Teleport distinguished from a lag spike (no updates for N ticks then a large jump)?

## Questions to Resolve

- [ ] Velocity threshold for HighSpeed classification
- [ ] Displacement threshold for Teleport classification
- [ ] Lag spike detection vs legitimate Teleport
- [ ] Are thresholds configurable or hardcoded?
- [ ] Per-entity or global thresholds? (e.g., does a mount increase the threshold?)

## Proposed Resolution

_To be drafted._

## References

- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — Ghost anomaly detection
- `docs/4-infrastructure/02-configuration-registry.md` — `ghost_anomaly_margin`
