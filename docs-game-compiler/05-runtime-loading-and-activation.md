# Runtime Loading and Activation

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define the end-to-end pipeline for loading a compiled game image into an Arbiter and activating it for authoritative use. This document consolidates content from `04-game-image-format.md` §11, the T3-07 asset loading draft, and the `PrepareDataEpoch` protocol in `docs-core/`.

---

## 1. Trigger: `PrepareDataEpoch` Command

The Mesh Controller issues `PrepareDataEpoch` to an Arbiter over TCP in three situations:

| Situation | Trigger | Source |
|-----------|---------|--------|
| Arbiter boot | Controller primes the Arbiter with the current content version as part of the readiness handshake | `docs-core/01-spatial-runtime-kernel.md` §4, `docs/1-architecture/03-mesh-controller.md` §4.1 |
| Version-line transition | Blue/green deployment rolls out new game rules | `docs-core/04-3-version-line-transition-contract.md` |
| Live hot-patch | Balance changes pushed to a running cluster without restart | `docs/1-architecture/03-mesh-controller.md` §11.3 |

```
PrepareDataEpoch {
    new_epoch:  u32,
    asset_uri:  String,       // Fully qualified HTTPS CDN URI (or file:// in dev)
    checksum:   [u8; 32],     // SHA-256 of the game image bytes
}
```

An Arbiter MUST NOT be allocated from the Warm Pool until it has an active game content version. An Arbiter without loaded content cannot process proposals through game adapter hooks.

## 2. Download

The Arbiter downloads the game image on a **background thread** — never on the authoritative tick thread.

### 2.1 Transport

- **Production:** HTTPS GET from CDN URI (e.g., `s3://game-assets/balance/v1.02.gmim`).
- **Development/Docker Compose:** `file://` scheme pointing to a mounted volume.

### 2.2 Retry Policy

```
MAX_RETRIES:          3
RETRY_BACKOFF_MS:     [500, 2000, 5000]
DOWNLOAD_TIMEOUT_MS:  30_000
```

| Attempt | Backoff | Behavior |
|---------|---------|----------|
| 1 | 0 (immediate) | Download from `asset_uri` |
| 2 | 500ms | Retry same URI |
| 3 | 2000ms | Retry same URI |
| 4 | 5000ms | Retry same URI |
| All failed | — | Report `ASSET_LOAD_FAILED` to Controller. Arbiter remains `NotReady`. |

### 2.3 No Stale Fallback

If the download fails, the Arbiter does NOT activate a previous epoch's content. It stays not-ready until the Controller retries or replaces it. This prevents version skew within a mesh.

## 3. Integrity Verification

After download completes, the background thread verifies the image before handing it to the tick thread.

### 3.1 Checksum

Compute SHA-256 over the downloaded bytes. Compare to `PrepareDataEpoch.checksum`. Mismatch → discard and retry.

### 3.2 Full Image Verification

Run the 10-step verification sequence from `04-game-image-format.md` §11.1:

1. Validate `FileHeader` magic bytes (`GMIM`).
2. Validate `format_version` is supported.
3. Verify `total_size` matches actual file size.
4. Read `SectionDirectory` and validate `section_count`.
5. Recompute SHA-256 over the authenticated image envelope (§1.1 of `04-game-image-format.md`) and compare to `FileHeader.digest`.
6. Verify per-section CRC-32 checksums.
7. If `signed` flag is set, verify Ed25519 signature against `FileHeader.digest`.
8. Parse `Manifest` via directory type 0x01 entry.
9. Validate `adapter_api_major` compatibility with the running adapter.
10. Validate `wire_schema_versions` intersection with runtime capabilities.

Any verification failure → discard and retry per §2.2. Verification failure codes are defined in `04-game-image-format.md` §11.2.

### 3.3 Parse Error Handling

If the image passes SHA-256 but fails structural parsing (malformed sections, invalid entry counts, truncated data):

1. Log the full error chain with epoch ID.
2. Treat as a download failure — retry per §2.2.
3. If all retries produce the same parse error, report `ASSET_PARSE_FAILED` to Controller.
4. The Controller MAY emit an alert and hold the epoch transition until the asset is fixed.

The Arbiter MUST NOT crash on a malformed game image. Parse errors are operational failures, not panics.

## 4. Thread-Safe Handoff

The background download thread and the 60Hz tick thread communicate via a **lock-free single-producer single-consumer (SPSC) queue**.

```
Background thread                         60Hz tick loop
─────────────────                         ─────────────
1. Download bytes from CDN
2. Compute SHA-256, compare to checksum
3. Run full image verification (§3.2)
4. Deserialize lookup indexes
5. Push verified GameImage into SPSC queue ──→  6. At frame boundary, poll queue
                                                 7. If new image present: atomic swap
                                                 8. Send PrepareDataEpochAck to Controller
```

The tick thread polls the SPSC queue at the **beginning of every tick** (before Stage 1). If an image is available, it swaps atomically. If not, the tick proceeds with the current epoch.

Zero blocking I/O occurs on the tick thread. The SPSC queue push/poll is O(1) and wait-free.

## 5. Activation

### 5.1 Atomic Frame-Boundary Swap

When the tick thread dequeues a verified `GameImage`:

1. The new image's lookup indexes (ability, entity, status effect, formula) replace the current indexes.
2. The `current_data_epoch` is updated to `new_epoch`.
3. The swap takes effect at the start of the tick — all stages within that tick use the new content.

### 5.2 Epoch Pinning

In-flight effects (active status effects, projectiles, zone actors) that were created under the previous epoch MUST resolve under their **creation-time epoch** data, not the new epoch. This prevents mid-flight behavior changes:

- A projectile spawned under epoch 5 with `base_damage = 100` continues dealing 100 damage even if epoch 6 changes it to 50.
- Epoch pinning is tracked per-effect via the `data_epoch` field on `ProjectileActor`, `StatusEffect`, and `ZoneActor`.

The old image is retained in memory until all epoch-pinned effects from that epoch have expired or been despawned. Then it is released.

### 5.3 Controller Acknowledgment

After successful activation:

1. The Arbiter sends `PrepareDataEpochAck { epoch: new_epoch, status: OK }` to the Controller over TCP.
2. The Controller marks the Arbiter as content-ready for that epoch.
3. For boot-time loading: the Controller promotes the Arbiter from `Idle` to `Ready` in the Warm Pool.
4. For hot-patches: the Controller tracks epoch convergence across the mesh (all Arbiters on the new epoch).

If activation fails (verification or compatibility rejection):

1. The Arbiter sends `PrepareDataEpochAck { epoch: new_epoch, status: FAILED, reason: ... }` to the Controller.
2. The Arbiter retains its current epoch (no change).
3. The Controller decides whether to retry, roll back the epoch, or replace the Arbiter.

## 6. Hot-Patch Behavior (Already Active Arbiter)

When a `PrepareDataEpoch` arrives for an Arbiter that already has an active epoch:

1. The same download → verify → parse → SPSC queue pipeline runs.
2. The new image is pushed to the SPSC queue.
3. At the next frame boundary, the tick thread atomically swaps to the new epoch (§5.1).
4. Epoch pinning preserves in-flight effects from the previous epoch (§5.2).
5. The old image is released after all epoch-pinned effects expire.

The Arbiter does NOT pause, drain, or skip ticks during a hot-patch. The swap is instantaneous at the frame boundary.

## 7. Failure Modes Summary

| Failure | Arbiter Response | Controller Response |
|---------|-----------------|-------------------|
| Download timeout/error (all retries) | Stays `NotReady` or retains current epoch | May retry, replace Arbiter, or abort transition |
| Checksum mismatch | Retry (counted against retry budget) | N/A until all retries exhausted |
| Parse error | Retry, then report `ASSET_PARSE_FAILED` | Alert, hold transition |
| Compatibility rejection | Report `FAILED` with reason code | Roll back or fix asset |
| Signature verification failure | Report `FAILED` with `IMAGE_SIGNATURE_INVALID` | Alert, investigate signing pipeline |

## 8. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `04-game-image-format.md` | Defines the binary format, verification sequence (§11.1), failure codes (§11.2), and activation protocol (§11.3). |
| `docs-core/01-spatial-runtime-kernel.md` | §4: Topology epochs and Arbiter readiness. §5: No blocking I/O on tick thread. |
| `docs-core/04-0-game-adapter-interface.md` | §6: Data contract and epoch activation. |
| `docs-core/04-3-version-line-transition-contract.md` | Rollout/rollback behavior for version-line transitions. |
| `docs/1-architecture/03-mesh-controller.md` | §4.1: Warm Pool readiness handshake. §11: Game Content Distribution. |
| `docs/6-spec-drafts/tier-3-subsystems/07-asset-loading.md` | Original draft specifying download, retry, and thread handoff. |
