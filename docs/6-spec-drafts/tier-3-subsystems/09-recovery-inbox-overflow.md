# T3-09: Recovery Inbox Overflow

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/04-meta-services.md`

## Problem Statement

The Recovery Inbox holds items for crash refund, deferred loot, auction purchases, GM comp, and event rewards. But what happens when the player tries to claim an inbox entry and their inventory is full?

Options:
- Item stays in inbox (try again later)
- Item is force-added to overflow slot
- Item is mailed (but there's no mail system specced)
- Item is lost (unacceptable)

## Questions to Resolve

- [ ] Claim-when-full behavior
- [ ] Inbox capacity limit (or unbounded?)
- [ ] Inbox entry expiry (30 days mentioned — what about items that can't be claimed due to full inventory for 30 days?)
- [ ] Notification mechanism when inbox has claimable items

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/04-meta-services.md` §6.2 — Recovery Inbox
