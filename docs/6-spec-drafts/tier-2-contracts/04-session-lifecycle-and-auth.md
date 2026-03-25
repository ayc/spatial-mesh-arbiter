# T2-04: Session Lifecycle & Auth

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/04-meta-services.md` + `01-client-edge-wire-protocol.md`

## Audit Notes

Substantial auth mechanics are documented: wire protocol auth messages, token TTL (1h access / 7d refresh), max sessions (1), login rate limit (10/min), wilderness fuse (60s), safe zone instant logout, session orphaning (6s heartbeat TTL). Missing: token format, validation mechanism, refresh rotation, and explicit logout handshake.

## Resolution

### 1. Token Format: Opaque Session Ticket

**Decision: Opaque bearer tokens, NOT JWTs.**

```
access_token:  base64url(random_bytes(32))   // 256-bit, 43 chars
refresh_token: base64url(random_bytes(32))   // 256-bit, 43 chars
```

**Rationale:** JWTs require signature verification at the Edge Node, which means distributing signing keys to every Edge Node. Opaque tokens require a validation call to the Identity Service, but:
- The Edge Node already maintains a session cache for heartbeat tracking
- Token validation happens once on `ClientHello` and once per `AuthRefresh`, not per-packet
- Opaque tokens are revocable immediately (delete from Identity Service store); JWTs are valid until expiry

### 2. Token Validation Mechanism

**Edge Node validates via Identity Service lookup:**

```
1. Client sends ClientHello { access_token }
2. Edge Node calls Identity Service: ValidateToken(access_token)
3. Identity Service:
   - Looks up token in session store (Redis/memory)
   - Checks: token exists, not expired, not revoked, account not banned
   - Returns: { valid: true, account_id, session_id, expires_at }
4. Edge Node caches session locally for the connection lifetime
5. Subsequent packets use the cached session — no per-packet validation
```

On `AuthRefresh`:
```
1. Client sends AuthRefresh { refresh_token }
2. Edge Node calls Identity Service: RefreshToken(refresh_token)
3. Identity Service issues new access_token + optionally rotated refresh_token
4. Edge Node sends new tokens to client via AuthTokenUpdate
```

### 3. Refresh Rotation Policy

| Policy | Value | Notes |
|--------|-------|-------|
| Refresh on every use | Yes | Each `AuthRefresh` call rotates the refresh token |
| Old refresh token grace period | 30 seconds | Covers network race conditions (old token valid briefly after rotation) |
| Max refresh count before re-auth | 168 (7 days ÷ 1h access TTL) | After 7 days of continuous refresh, force full re-authentication |
| Revocation on suspicious activity | Immediate | Account ban, password change, or concurrent session detection revokes all tokens |

### 4. Explicit Logout Handshake Flow

```
Client → Edge:   RequestLogout
Edge → Arbiter:  InitiateLogout { entity_id, is_safe_zone }

If safe zone:
  Arbiter:        Despawn entity immediately
  Arbiter → Edge: LogoutComplete { immediate: true }
  Edge → Client:  LogoutAccepted
  Edge:           Close WebSocket

If wilderness:
  Arbiter:        Start wilderness fuse timer (60s)
  Arbiter → Edge: LogoutPending { fuse_remaining_ticks: 3600 }
  Edge → Client:  LogoutPending { countdown_seconds: 60 }

  After 60s (or entity killed):
  Arbiter:        Despawn entity
  Arbiter → Edge: LogoutComplete { immediate: false }
  Edge → Client:  LogoutAccepted
  Edge:           Close WebSocket

Edge → Identity Service: EndSession(session_id)
Identity Service: Revoke access_token + refresh_token
```

If the client disconnects during the wilderness fuse (ALT+F4), the session orphaning mechanism takes over (heartbeat TTL → Orphaned → Dead after 6 seconds).

### 5. Configuration

```json
"auth": {
    "access_token_ttl_seconds": 3600,
    "refresh_token_ttl_seconds": 604800,
    "refresh_rotation_grace_seconds": 30,
    "max_refresh_count_before_reauth": 168,
    "max_concurrent_sessions_per_account": 1,
    "login_rate_limit_per_minute": 10,
    "token_bytes": 32
}
```

## References

- `docs/2-contracts-and-interfaces/01-client-edge-wire-protocol.md` — Auth flow messages
- `docs/1-architecture/04-meta-services.md` — Auth config
- `docs/1-architecture/01-core-concepts-and-mesh.md` — Wilderness fuse, session orphaning
