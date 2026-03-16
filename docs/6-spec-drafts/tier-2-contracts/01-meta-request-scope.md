# T2-01: MetaRequest Scope

> **Status:** RESOLVED
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `2-contracts-and-interfaces/01-client-edge-wire-protocol.md` + `02-edge-node-envelopes.md`

## Audit Notes

The discrepancy is larger than originally claimed:
- Wire protocol: **4 variants** (SendChatMessage, MoveInventoryItem, InviteToParty, RequestLogout)
- Edge Node Envelopes: **41 variants** (chat, inventory, loot, party, guild, friends, LFG, moderation, session)

The Edge Node Envelopes doc preamble states (line 7): "The types below are runtime-focused interface excerpts." But this is ambiguous — it doesn't clarify whether:
- The wire protocol is intentionally a minimal subset and the Edge Node expands internally
- The wire protocol is incomplete and needs to grow
- The 41-variant enum is an internal dispatcher that the 4 wire variants map into

## Resolution

**The wire protocol's 4-variant `MetaRequest` was a placeholder that was never expanded.** The Edge Node Envelopes' 41-variant enum is the canonical definition.

Evidence:
1. The wire protocol's 4 variants are one example per domain (chat, inventory, social, session) — a sketch, not a contract.
2. The Edge Node `ProxyActor::on_client_message` directly matches on `ClientMessage::Meta(request)` and forwards it to Meta with no translation step. The client sends the same `MetaRequest` the Edge receives.
3. A client cannot equip items, join guilds, vote on loot, or perform meaningful meta interactions with only 4 variants.

### Changes applied

1. **`01-client-edge-wire-protocol.md` §9.1:** Removed the inline 4-variant `MetaRequest` enum. The section now references the canonical definition in `02-edge-node-envelopes.md` §2.1 and clarifies that the client sends the same enum with no translation or fan-out.

2. **`02-edge-node-envelopes.md`:** Added a canonical ownership comment above the `MetaRequest` enum confirming it is the single source of truth, referenced by the wire protocol.

### Answers to gap questions

- [x] Is the 4-variant wire protocol intentional? **No.** It was a placeholder.
- [x] Or does the wire protocol need to enumerate all 41 request types? **The wire protocol now references the canonical enum in edge node envelopes rather than duplicating it.**
- [x] If fan-out: what is the mapping from wire intent to internal MetaRequest? **There is no fan-out. The client sends the full `MetaRequest` enum directly.**
- [x] Evolution path: how are new MetaRequest types added without breaking existing clients? **New variants are added to the canonical `MetaRequest` enum in `02-edge-node-envelopes.md`. The wire protocol inherits them automatically. Older clients that never send new variants are unaffected; the Edge validates schema on receipt.**

## References

- `docs/2-contracts-and-interfaces/01-client-edge-wire-protocol.md` §9.1 — now references canonical enum
- `docs/2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md` §2.1 — canonical `MetaRequest` definition (41 variants)
