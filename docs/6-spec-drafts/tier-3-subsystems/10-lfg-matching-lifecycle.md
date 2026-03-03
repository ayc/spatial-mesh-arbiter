# T3-10: LFG Matching Lifecycle

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/04-meta-services.md`

## Problem Statement

LFG has Enqueue/Dequeue/MatchFound but the full lifecycle is missing:

1. After MatchFound, do players accept/decline? Or is it auto-formed?
2. If one player declines, does the group dissolve? Or does the declined slot get re-queued?
3. What's the acceptance timeout?
4. How is the formed group bound (auto-create party? Teleport to instance?)
5. What happens if a player disconnects during acceptance window?

## Questions to Resolve

- [ ] Accept/decline flow after match
- [ ] Acceptance timeout
- [ ] Partial decline handling (re-queue or dissolve?)
- [ ] Group binding mechanism (party creation, instance teleport)
- [ ] Disconnect during acceptance

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/04-meta-services.md` §8 — Party & Guild Service, LFG
- `docs/2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md` — LfgEnqueue, LfgMatchFound
