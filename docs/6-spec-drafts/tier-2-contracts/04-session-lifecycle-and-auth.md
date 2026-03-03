# T2-04: Session Lifecycle & Auth

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/04-meta-services.md` + `01-client-edge-wire-protocol.md`

## Audit Notes

**Substantial auth mechanics ARE documented:**

| Aspect | Status | Source |
|--------|--------|--------|
| Wire protocol auth messages | **Specified** — ClientHello, ResumeSession, AuthRefresh with fields | `01-client-edge-wire-protocol.md` lines 146-207 |
| Token TTL | **Specified** — 3600s (1h) access, 604800s (7d) refresh | `04-meta-services.md` lines 103-116 |
| Max concurrent sessions | **Specified** — 1 per account | `04-meta-services.md` line 108 |
| Login rate limit | **Specified** — 10 per minute | `04-meta-services.md` line 109 |
| Wilderness logout fuse | **Specified** — 60s, entity remains targetable/killable | `01-core-concepts-and-mesh.md` lines 658-662 |
| Safe zone logout | **Specified** — Instant despawn via `InitiateLogout { is_safe_zone: true }` | `01-core-concepts-and-mesh.md` |
| Session orphaning | **Specified** — Heartbeat TTL (6s / 3 missed), Orphaned → Dead lifecycle | `01-core-concepts-and-mesh.md` lines 905-913 |
| Mid-session token expiry | **Specified** — Edge emits `AuthRefreshRequired` | `01-client-edge-wire-protocol.md` line 205 |

## Remaining Gap (Narrowed)

### 1. Token Format
`auth_token: String` on the wire but no spec for encoding (JWT with RS256? Opaque session ticket? OAuth2 bearer?), claim structure, or signing.

### 2. Token Validation Mechanism
How does the Edge Node validate tokens? Signature check? Introspection endpoint? Shared secret?

### 3. Refresh Rotation Strategy
When does the refresh token rotate? Are old tokens revoked? Max refresh count before re-auth?

### 4. Explicit Logout Handshake Flow
`RequestLogout` exists as a MetaRequest but the response flow (what messages does the client receive back?) is not detailed.

## Questions to Resolve

- [ ] Token format and signing algorithm
- [ ] Edge Node validation mechanism
- [ ] Refresh rotation policy (rotate on every refresh? Fixed count?)
- [ ] Logout response flow (client receives what? When is WebSocket closed?)

## Proposed Resolution

_To be drafted._

## References

- `docs/2-contracts-and-interfaces/01-client-edge-wire-protocol.md` lines 146-207 — Auth flow messages
- `docs/1-architecture/04-meta-services.md` lines 103-116 — Auth config
- `docs/1-architecture/01-core-concepts-and-mesh.md` lines 658-662 — Wilderness fuse
- `docs/1-architecture/01-core-concepts-and-mesh.md` lines 905-913 — Session Manager orphaning
