# T1-03: Combat Resolution Ordering

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md`

## Problem Statement

When multiple combat events arrive in the same tick, resolution order matters (e.g., simultaneous kills, damage vs heal race). The spec states "deterministic convergence for contested interactions" but doesn't specify the ordering mechanism.

## Questions to Resolve

- [ ] Within a single tick, what order are combat events processed? (sorted by proposal_id? origin_tick? entity_id?)
- [ ] If two entities kill each other simultaneously, do both die? Or does one win?
- [ ] Does damage apply before or after healing in the same tick?
- [ ] For cross-boundary combat (InternalPreparedHit), does arrival order matter or is there a canonical sort?
- [ ] Are status effects applied before or after damage in the same tick?

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/01-rpg-mechanics.md` — Two-phase pipeline
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — drain order in tick loop
