# T3-04: Line of Sight Calculation

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/04-npc-and-world-interaction.md`

## Problem Statement

Interaction validation gate 2 requires "Range and LOS" check. NPC threat acquisition also implies LOS. But the LOS algorithm is never specified:

1. Is LOS a simple range check (no obstacles)?
2. Or does it involve raycasting against static geometry?
3. What about entities behind other entities (no body-blocking LOS implied)?
4. Does the 2D top-down perspective simplify this to a 2D raycast?

## Questions to Resolve

- [ ] LOS algorithm: range-only, or raycast against static geometry?
- [ ] If raycast: against what geometry? (same `static_grid` as collision?)
- [ ] Body-blocking: do other entities block LOS?
- [ ] Height/elevation: is this purely 2D or are there elevation layers?
- [ ] Performance budget: LOS checks per tick?

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/04-npc-and-world-interaction.md` — Validation gate 2
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — `static_grid` reference
