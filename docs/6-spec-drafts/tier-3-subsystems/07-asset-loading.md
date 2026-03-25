# T3-07: Asset Loading & CDN Fallback

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/03-mesh-controller.md`

## Problem Statement

`PrepareDataEpoch` includes `asset_uri` and `checksum` but the asset loading pipeline details are unspecified: checksum algorithm, download failure handling, parse error behavior, and thread-safe handoff.

## Resolution

### 1. Asset Hosting

Assets are hosted on a CDN (e.g., S3, CloudFront). The `asset_uri` in `PrepareDataEpoch` is a fully qualified HTTPS URI. The Arbiter downloads via HTTPS GET.

No local filesystem fallback in production. In development/Docker Compose, `asset_uri` MAY use a `file://` scheme pointing to a mounted volume.

### 2. Checksum Algorithm

**SHA-256.** This matches the game image format (`04-game-image-format.md` §1.1) which uses SHA-256 for the authenticated digest. Using the same algorithm across the pipeline avoids algorithm proliferation.

```rust
struct PrepareDataEpoch {
    new_epoch:  u32,
    asset_uri:  String,       // HTTPS CDN URI
    checksum:   [u8; 32],     // SHA-256 of the game image bytes
}
```

The Arbiter computes SHA-256 over the downloaded bytes and compares to `checksum`. Mismatch → download is discarded and retried.

### 3. Retry and Fallback Policy

```rust
const ASSET_DOWNLOAD_MAX_RETRIES: u32 = 3;
const ASSET_DOWNLOAD_RETRY_BACKOFF_MS: [u64; 3] = [500, 2000, 5000];
const ASSET_DOWNLOAD_TIMEOUT_MS: u64 = 30_000;
```

| Attempt | Backoff | Behavior |
|---------|---------|----------|
| 1 | 0 (immediate) | Download from `asset_uri` |
| 2 | 500ms | Retry same URI |
| 3 | 2000ms | Retry same URI |
| 4 | 5000ms | Retry same URI |
| All failed | — | Report `ASSET_LOAD_FAILED` to Controller. Arbiter remains in `NotReady` state and is NOT promoted to the Warm Pool. |

**No fallback to previous epoch.** If the download fails, the Arbiter does not activate a stale version. It stays not-ready until the Controller retries or replaces it. This prevents version skew within a mesh.

### 4. Thread-Safe Handoff

```
Background thread                         60Hz tick loop
─────────────────                         ─────────────
1. Download bytes from CDN
2. Compute SHA-256, compare to checksum
3. Parse game image (verify header, sections, indexes)
4. Push parsed GameImage into lock-free SPSC queue ──→  5. At frame boundary, poll queue
                                                         6. If new image present: atomic swap
                                                         7. Send PrepareDataEpochAck to Controller
```

The lock-free single-producer single-consumer (SPSC) queue ensures zero blocking on the tick thread. The tick thread polls at every frame boundary (beginning of tick, before Stage 1). If an image is available, it swaps atomically. If not, the tick proceeds with the current epoch.

### 5. Parse Error Handling

If the downloaded bytes pass the SHA-256 check but fail to parse as a valid game image:

1. The parse error is logged with the full error chain and epoch ID.
2. The download is treated as failed (same as checksum mismatch).
3. The retry policy applies — the Arbiter retries the download.
4. If all retries produce the same parse error, the Arbiter reports `ASSET_PARSE_FAILED` to the Controller.
5. The Controller MAY emit an alert and hold the epoch transition until the asset is fixed and redistributed.

**The Arbiter MUST NOT crash on a malformed game image.** Parse errors are operational failures, not panics.

### 6. Hot-Patch Behavior (Already Active Arbiter)

When a `PrepareDataEpoch` arrives for an Arbiter that already has an active epoch:

1. The same download/verify/parse pipeline runs on the background thread.
2. On success, the new image is pushed to the SPSC queue.
3. At the next frame boundary, the tick thread atomically swaps to the new epoch.
4. In-flight effects from the previous epoch resolve under their creation-time epoch (epoch pinning — see `docs-core/04-0-game-adapter-interface.md` §6).
5. The old image is released after all epoch-pinned effects have expired.

## References

- `docs/1-architecture/03-mesh-controller.md` §11 — Game Content Distribution
- `docs-game-compiler/04-game-image-format.md` — Game image binary format and integrity verification
- `docs-core/04-0-game-adapter-interface.md` §6 — Data contract and epoch activation
