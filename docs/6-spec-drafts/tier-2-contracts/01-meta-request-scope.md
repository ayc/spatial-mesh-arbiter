# T2-01: MetaRequest Scope

> **Status:** OPEN
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

## Remaining Gap

- [ ] Is the 4-variant wire protocol intentional? If so, how does a client trigger `EquipItem` or `GuildBankDeposit`?
- [ ] Or does the wire protocol need to enumerate all 41 request types?
- [ ] If fan-out: what is the mapping from wire intent to internal MetaRequest?
- [ ] Evolution path: how are new MetaRequest types added without breaking existing clients?

## Proposed Resolution

_To be drafted._

## References

- `docs/2-contracts-and-interfaces/01-client-edge-wire-protocol.md` lines 359-364 — 4 MetaRequest variants
- `docs/2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md` lines 53-109 — 41 MetaRequest variants
