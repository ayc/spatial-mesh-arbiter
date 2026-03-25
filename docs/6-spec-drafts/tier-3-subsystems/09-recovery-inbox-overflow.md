# T3-09: Recovery Inbox Overflow

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/04-meta-services.md`

## Problem Statement

The Recovery Inbox holds items for crash refund, deferred loot, auction purchases, GM comp, and event rewards. What happens when the player claims an entry but their inventory is full? What's the inbox capacity? What about long-term expiry?

## Resolution

### 1. Claim-When-Full Behavior

**Rule:** If the player's inventory cannot accommodate the claimed item(s), the claim is **rejected and the entry stays in the inbox**. The item is NOT lost, NOT force-added, NOT mailed.

```rust
fn claim_inbox_entry(player: &mut Player, entry: &InboxEntry) -> ClaimResult {
    if !player.inventory.can_fit(entry.items) {
        return ClaimResult::Rejected {
            reason: "INVENTORY_FULL",
            hint: "Free inventory space and try again.",
        };
    }
    // Atomic: remove from inbox + add to inventory in one transaction
    let txn = begin_transaction();
    txn.remove_inbox_entry(entry.id);
    txn.add_items_to_inventory(player.id, entry.items);
    txn.commit()?;
    ClaimResult::Success
}
```

**Rationale:** "Item stays in inbox" is the only safe option. Force-adding creates inventory overflow bugs. Mailing requires a mail system. Losing items is unacceptable for crash refunds and paid purchases.

### 2. Inbox Capacity

**Bounded:** `max_inbox_entries_per_player = 100` (configurable).

If an incoming delivery would exceed the cap:
1. The delivery is held in the Meta service's pending queue (not the player's inbox).
2. When the player claims entries and frees inbox slots, pending deliveries are promoted in FIFO order.
3. If the pending queue also fills (`max_pending_deliveries_per_player = 50`), the **oldest non-critical** pending delivery is dropped and a `DELIVERY_DROPPED` alert is emitted.
4. **Critical deliveries** (crash refunds, paid purchases) are NEVER dropped — they overflow into a separate uncapped recovery log that persists until claimed or manually resolved by support.

| Category | Droppable? | Rationale |
|----------|-----------|-----------|
| Crash refund | No | Player lost items due to server fault |
| Paid purchase | No | Real-money transaction |
| Auction purchase | No | Player spent currency |
| GM compensation | No | Support-issued |
| Event reward | Yes (after 30 days) | Time-limited by design |
| Deferred loot | Yes (after 30 days) | Standard loot expiry |

### 3. Entry Expiry

| Entry Type | Expiry | Behavior on Expiry |
|-----------|--------|-------------------|
| Crash refund | 90 days | Escalated to support queue (not deleted) |
| Paid purchase | Never | Persists until claimed |
| Auction purchase | 90 days | Currency refunded, item returned to seller |
| GM compensation | 90 days | Escalated to support queue |
| Event reward | 30 days | Deleted with `REWARD_EXPIRED` log |
| Deferred loot | 30 days | Deleted with `LOOT_EXPIRED` log |

**Expiry is wall-clock based** (not game-time or dilated-time). The Meta service runs a scheduled sweep job.

### 4. Notification

When the inbox has claimable entries:
1. The Meta service sets a `has_inbox_items: bool` flag on the player's session state.
2. The Edge Node receives this flag in session metadata and displays a UI indicator.
3. On login, the client queries inbox summary (entry count, categories) via `MetaRequest::GetInboxSummary`.
4. Individual entry details are fetched on demand via `MetaRequest::GetInboxEntries { page, page_size }`.

No push notification for inbox deliveries — the flag is polled at login and periodically (every 60 seconds) during play.

### 5. Configuration

```json
"recovery_inbox": {
    "max_inbox_entries_per_player": 100,
    "max_pending_deliveries_per_player": 50,
    "default_expiry_days_loot": 30,
    "default_expiry_days_critical": 90,
    "inbox_poll_interval_seconds": 60,
    "never_drop_categories": ["crash_refund", "paid_purchase", "auction_purchase", "gm_compensation"]
}
```

## References

- `docs/1-architecture/04-meta-services.md` §6.2 — Recovery Inbox
- `docs-core/03-durability-bridge.md` — Transaction state machine for atomic claim operations
