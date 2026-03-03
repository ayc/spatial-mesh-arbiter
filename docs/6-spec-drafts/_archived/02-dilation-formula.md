# T0-02: Kinematic Dilation — Spec Corrections

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/01-core-concepts-and-mesh.md` §8.2, `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md`
> **Authoritative KiDi Doc:** [`1-architecture/06-kinematic-dilation.md`](../../1-architecture/06-kinematic-dilation.md)

## Summary

The canonical spec describes KiDi using a "Tick Interleaving" / frame-skipping model that contradicts the actual design. A dedicated authoritative doc (`06-kinematic-dilation.md`) has been created with the correct model. This draft tracks the specific spec passages that must be corrected to align.

## Corrections Required

### 1. `01-core-concepts-and-mesh.md` §8.2 heading (line 488)

**Current:** "Containment via Kinematic Dilation (Tick Interleaving)"
**Action:** Remove "(Tick Interleaving)". Replace §8.2 body with a summary pointing to `06-kinematic-dilation.md` as the authoritative reference.

### 2. `01-core-concepts-and-mesh.md` line 508

**Current:** "CPU Savings (Tick Interleaving): The Arbiter continues to increment its global Shard Tick at exactly 60Hz. However, as dilation_factor drops, it safely skips heavy simulation frames. A 'Heavy Frame' is triggered if `current_tick % (1.0 / dilation_factor) == 0`. At `0.2` dilation, the heavy collision/combat loop resolves only every 5th tick."
**Action:** Replace entirely. The Arbiter does not skip frames. Load reduction comes from Edge Node throttle + reduced event density. See `06-kinematic-dilation.md` §4.

### 3. `01-core-concepts-and-mesh.md` line 509

**Current:** "Continuous Collision Detection (CCD): To prevent fast-moving objects from 'tunneling' through targets during these skipped frames..."
**Action:** Reframe. CCD is still valuable (fast projectiles need swept-volume checks), but the rationale is not "skipped frames."

### 4. `01-core-concepts-and-mesh.md` line 300

**Current:** "Priority Interrupt (Dilation Override): Global Events always override Tick Interleaving. Even if an Arbiter is currently skipping frames via Kinematic Dilation (Section 8.2), it is forced to wake up and execute a full simulation frame on the exact scheduled Shard Tick Y."
**Action:** Remove. There are no frames to skip, so there's nothing to override. Global events execute on their scheduled tick like any other tick.

### 5. `03-mesh-arbiter-state.md` lines 215-217

**Current:** Comment describes dilation_factor as "Physics resolution every 5th tick"
**Action:** Rewrite comment to reflect correct model: dilation_factor is a per-entity time multiplier, not a frame-skip interval.

### 6. `03-mesh-arbiter-state.md` lines 357-360

**Current:**
```rust
let frame_interval = (SimFixed::from_num(1) / self.dilation_factor).to_num::<u64>();
let is_heavy_frame = (self.current_tick % frame_interval == 0) || has_priority_event;
```
**Action:** Remove entirely. Replace with dilation applied to entity movement/timers per tick. See `06-kinematic-dilation.md` §3 and §10.1 for correct pseudocode.

## References

- `docs/1-architecture/06-kinematic-dilation.md` — Authoritative KiDi reference (new)
- `docs/1-architecture/01-core-concepts-and-mesh.md` §8.2 — Incorrect framing to correct
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — `is_heavy_frame` pseudocode to remove
