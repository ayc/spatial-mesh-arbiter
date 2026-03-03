# T3-08: Dilation + Global Event Interaction

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/03-mesh-controller.md` + `03-mesh-arbiter-state.md`

## Audit Notes

**The priority wakeup IS specified** in `03-mesh-arbiter-state.md` lines 349-360:

```rust
let mut has_priority_event = false;
for cmd in self.pending_global_events.values() {
    if let ControllerCommand::ExecuteGlobalEvent { execute_at_tick, .. } = cmd {
        if self.current_tick >= *execute_at_tick { has_priority_event = true; }
    }
}
let is_heavy_frame = (self.current_tick % frame_interval == 0) || has_priority_event;
```

**Answer: Yes, dilated Arbiters DO wake early for global events.** `has_priority_event` forces `is_heavy_frame = true`, bypassing the dilation skip.

Also confirmed in `01-core-concepts-and-mesh.md`: "Global Events always override Tick Interleaving. Even if an Arbiter is currently skipping frames via Kinematic Dilation, it is forced to wake up and execute a full simulation frame on the exact scheduled Shard Tick."

## Remaining Gap (Narrow)

The wakeup mechanism is clear. What's missing:

### 1. Sustained Dilation Behavior
No documentation on:
- How long dilation can persist before intervention
- Whether there's a quality-of-life floor (e.g., "if dilated below X for >Y seconds, trigger forced split even at min_cell_size")
- Player-facing communication during prolonged dilation

### 2. Dilation Effect Scope
Which game systems are affected by dilation?
- Movement: clearly affected (velocity * dilation)
- Status effect timers: tick on light frames?
- NPC respawn timers: affected?
- Loot despawn timers: affected?

## Questions to Resolve

- [ ] Sustained dilation intervention threshold (if any)
- [ ] Which timers are affected by dilation vs running at wall-clock rate

## Proposed Resolution

_To be drafted._

## References

- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` lines 349-360 — Priority event wakeup
- `docs/1-architecture/01-core-concepts-and-mesh.md` — "Priority Interrupt (Dilation Override)" quote
