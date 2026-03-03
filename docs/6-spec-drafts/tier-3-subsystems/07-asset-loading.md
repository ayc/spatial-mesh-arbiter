# T3-07: Asset Loading & CDN Fallback

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/03-mesh-controller.md`

## Problem Statement

`PrepareDataEpoch` includes `asset_uri` and `checksum` but the asset loading pipeline is unspecified:

1. Where are assets hosted? (S3? Local filesystem? CDN?)
2. Checksum algorithm (SHA256? CRC32? Blake3?)
3. Download failure handling (retry count, backoff, fallback to previous epoch?)
4. Thread-safe handoff from background download thread to Arbiter tick loop
5. Parse error handling (malformed SpellData JSON/bincode)

## Questions to Resolve

- [ ] Asset hosting strategy
- [ ] Checksum algorithm
- [ ] Retry and fallback policy
- [ ] Thread-safe queue mechanism for download → tick loop handoff
- [ ] Parse error behavior (reject epoch? Crash? Use previous?)

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/03-mesh-controller.md` §10 — Live Data Distribution
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — PrepareDataEpoch handling
