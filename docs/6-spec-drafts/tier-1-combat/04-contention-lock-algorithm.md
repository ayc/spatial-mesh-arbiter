# T1-04: Contention Lock Algorithm

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/04-npc-and-world-interaction.md`

## Audit Notes

**The requirement IS clearly specified:**

- NPC Interaction Design §4.2: "contention lock (single-winner where applicable)"
- NPC Interaction Design §5: "Contention outcomes MUST be deterministic and single-winner where required (loot/objective claim points)."
- NPC Architecture §8.3: "Single-winner interactions MUST produce exactly one `InteractionResolved` winner event. Losers MUST receive deterministic reject/result outcome."
- `RejectedContended` is a standard outcome with client retry guidance: "retry-later with short jittered backoff"

**What's missing is the algorithm**, not the requirement.

## Remaining Gap

The spec mandates deterministic single-winner but doesn't specify how:

- [ ] Algorithm: first-arrive-first-win? Deterministic hash of (entity_id, target_id, tick)? Ticket lottery?
- [ ] Scope: per-Arbiter only? Or can cross-boundary contention occur? (e.g., loot entity near a boundary)
- [ ] Lock duration: one tick? Until interaction animation completes?
- [ ] Interaction with party loot modes: does NeedGreed/MasterLoot bypass the contention lock entirely (Meta handles distribution)?

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/04-npc-and-world-interaction.md` — Validation gates (§4.2), determinism mandate (§5), outcome taxonomy (§4.3-4.4)
- `docs/1-architecture/02-npc-architecture.md` §8.3 — Single-winner event contract
- `docs/1-architecture/04-meta-services.md` §4.2 — Party loot distribution modes
