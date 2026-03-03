# T2-03: Data Epoch Distribution

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md`

## Audit Notes

**The pipeline mechanics ARE specified** in `03-mesh-controller.md` §11:
1. Controller issues `PrepareDataEpoch { new_epoch, asset_uri, checksum }` over TCP
2. Arbiters download asynchronously via background task
3. Checksum verified
4. Parsed dictionary pushed into lock-free queue, picked up at next frame boundary, atomic swap

**The epoch matching rules ARE specified** in `01-core-primitives.md` §1.1.5:
- Proposal epoch == Arbiter epoch → process normally
- Proposal stale → immediate ActionFailed
- Arbiter behind → buffer with MAX_EVENT_AGE_TICKS timeout

**Pre-rolled CombatContext carries data_epoch** (ActiveStatusEffect includes data_epoch for DoT/HoT pulses).

## Remaining Gap (Narrowed)

### 1. Trigger Mechanism
Who/what decides to issue a new `PrepareDataEpoch`? Designer CLI? Automated CD pipeline? Manual operator command?

### 2. Meta ↔ Arbiter Epoch Sync
When Meta compiles stats (e.g., during Spawn Handshake), must its data_epoch match the Arbiter's? What if Meta is on epoch N+1 but Arbiter is still on N?

### 3. Mid-Resolution Epoch Swap
Pre-rolled CombatContext uses the epoch active at cast time. If epoch swaps mid-flight (e.g., between cast and impact), the pre-rolled context is still valid because it carries its own data_epoch. But: is this explicitly the intended behavior, or an accident of the struct design?

## Questions to Resolve

- [ ] Trigger mechanism (who initiates epoch increment?)
- [ ] Meta→Arbiter sync contract (must epochs match during Spawn?)
- [ ] Confirm: pre-rolled CombatContext is epoch-pinned intentionally

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/03-mesh-controller.md` §11 — Live Data Distribution pipeline
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` §1.1.5 — Epoch matching rules
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` lines 460-468 — ActiveStatusEffect.data_epoch
