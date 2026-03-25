# T3-08: Dilation + Global Event Interaction

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md`

## Audit Notes

**The priority wakeup IS specified.** Dilated Arbiters DO wake early for global events — `has_priority_event` forces evaluation. Also confirmed: global events are listed under "Non-Dilated Systems" in `06-kinematic-dilation.md` §3.2.

**The dilation scope IS comprehensively specified.** `06-kinematic-dilation.md` §3 provides a complete system-by-system breakdown of dilated vs non-dilated systems, including status effect timers, cooldowns, cast times, and pulse intervals.

## Resolution

### 1. Sustained Dilation Intervention

**Rule:** If an Arbiter's `dilation_factor` remains at `minimum_dilation_factor` for longer than `sustained_dilation_intervention_ticks`, the Controller MUST trigger a forced topology split attempt, even if the cell is already at `min_cell_size`.

```rust
struct DilationConfig {
    // ... existing fields ...
    sustained_dilation_intervention_ticks: u64,  // default: 1800 (30 seconds at 60Hz)
}
```

**Intervention cascade:**

| Condition | Action |
|-----------|--------|
| Cell is above `min_cell_size` | Controller initiates standard split (existing behavior) |
| Cell is AT `min_cell_size` | Controller emits a `DILATION_FLOOR_SUSTAINED` operational alert. No split is possible. The alert triggers infrastructure-level response (manual intervention, capacity scaling, or player communication). |
| Dilation recovers before threshold | Timer resets. No intervention. |

**Rationale:** 30 seconds at minimum dilation (20% speed) is a severely degraded experience. Automated intervention ensures the system doesn't silently sit in a bad state. If the cell can't split (already at minimum size), human operators are notified.

### 2. Timer Scope Under Dilation (Already Resolved)

The remaining question ("which timers are affected?") is fully answered by `06-kinematic-dilation.md` §3:

| Timer Type | Dilated? | Mechanism |
|-----------|----------|-----------|
| Ability cooldowns | Yes | Decrement by `effective_time` per tick |
| Cast times | Yes | Progress by `effective_time` per tick |
| Status effect duration | Yes | Remaining time decrements by `effective_time` |
| Status effect pulse interval | Yes | Pulse timer advances by `effective_time` |
| NPC respawn timers | **No** | Respawn is a Meta service operation, not a simulation timer. Respawn commands arrive via `MeshInternalEvent` at the scheduled tick regardless of dilation. |
| Loot despawn timers | **No** | Loot entities are spawned with `lifetime_ticks` in absolute ticks (from `01-2-entity-lifecycle-contract.md` §5.4). The engine expires them at the scheduled tick regardless of dilation. |
| Recovery inbox expiry | **No** | Meta service operation, wall-clock based. |

**Key principle:** Dilation affects **entity-local simulation timers** (things that use `effective_time`). It does NOT affect **infrastructure timers** (things that run on absolute ticks or wall-clock time).

### 3. Player-Facing Communication

When dilation is active, the Edge Node receives `dilation_factor` in downstream payloads and displays:
- Dilated cooldown timers (abilities appear to recharge slower)
- Dilated cast bars (casts appear slower)
- Optional "High Density Zone" indicator (game-adapter-defined UI — not engine-specified)

The specific UI treatment is game-owned (adapter/client decision), not engine-contracted.

## References

- `docs/1-architecture/06-kinematic-dilation.md` §3 — Complete dilated/non-dilated system table
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — Priority event wakeup
- `docs-core/01-2-entity-lifecycle-contract.md` §5.4 — Lifetime enforcement (absolute ticks)
