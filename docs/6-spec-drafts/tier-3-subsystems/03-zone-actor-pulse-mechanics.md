# T3-03: Zone Actor Pulse Mechanics

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/02-ability-framework.md` + `03-global-events.md`

## Audit Notes

**Core pulse mechanics ARE specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| Per-pulse UUID | **Specified** — Each pulse generates a new UUID (UUID_PULSE_1, UUID_PULSE_2, etc.) | `02-ability-framework.md` lines 191-194 |
| Pulse interval/duration | **Specified** — `pulse_interval_ticks`, `duration_ticks` fields | `01-core-primitives.md` lines 239-240 |
| Pulse lifecycle | **Specified** — Duration decremented by interval each pulse, removed from queue when exhausted | `03-mesh-arbiter-state.md` lines 405-413 |
| Mobile zones | **Specified** — "Attached Aura" pattern: ZoneActor parented to entity, position syncs every tick | `02-ability-framework.md` lines 267-273 |

## Resolved Gaps

All three original gaps have been resolved in this draft:

1. **Entity Detection Per Pulse** — P-09 Shape Overlap Query per pulse tick (§1 below).
2. **Boundary Crossing Semantics** — Stateless between pulses; P-14 exception for continuous auras (§2 below).
3. **Zone Handoff** — Absolute `next_pulse_tick` serialized in handoff snapshot (§3 below).

## Proposed Resolution

### 1. Entity Detection (P-09 Shape Overlap Query)
Each pulse MUST trigger a `P-09: Shape Overlap Query` centered on the zone actor's current position.

**Algorithm:**
1.  On the tick where `current_tick == next_pulse_tick`, the engine executes a `P-09` query using the zone's `geometry` and `radius`.
2.  Results are filtered via `P-13 (Tag/Allegiance Filtering)` using the zone's `target_filters`.
3.  Ghosts ARE included in the result set, generating standard cross-boundary `MeshInternalEvent::InternalPreparedHit` relays.
4.  For each hit entity, the engine generates an `InternalPreparedHit` containing the `pulse_context` pre-rolled during the zone's creation.

### 2. Enter-Between-Pulses Behavior
Standard zone actors are **stateless** between pulse ticks.

-   An entity entering the zone's geometry between pulse ticks experiences NO effects until the next scheduled `next_pulse_tick`.
-   **Exception (P-14):** If a zone is configured with `P-14: Continuous Proximity Monitor`, the engine emits `OnEnter` events immediately upon entry. The adapter MAY use these events to apply a separate "Aura" status effect that persists as long as the entity remains in the zone. However, the periodic "Pulse" damage remains strictly tied to the `pulse_interval_ticks` schedule.

### 3. Zone Handoff Survival
Zone actors MUST be treated as **first-class entities** during spatial handoffs (splits/merges).

1.  **Serialization:** Zone actors (including `next_pulse_tick`, `remaining_duration_ticks`, and `pulse_context`) MUST be serialized into the `MergeSnapshot` or `SplitSnapshot`.
2.  **Continuity:** The receiving Arbiter MUST resume the pulse schedule using the absolute `next_pulse_tick`. This ensures that a boundary crossing does not reset or delay the pulse cadence.
3.  **Handoff Deduplication:** If a zone's geometry overlaps a boundary, only the **authoritative owner** of the zone actor triggers the pulse query. Results on the neighbor side are handled via the standard Ghost/Relay mechanism.

### 4. Implementation (Stage 11: StateUpdate)
The pulse lifecycle is managed in `Stage 11: StateUpdate`, after all combat and movement for the tick are resolved.
Because Stage 11 timer payloads MUST re-enter on the next authoritative tick, a zone pulse is queued as a `DeferredEvent`
with `event_class=deferred_spatial_event` and `target_stage=3` (`TargetResolution`).

```rust
fn tick_zone_pulses(&mut self) {
    for zone in self.zone_actors.values_mut() {
        if self.current_tick >= zone.next_pulse_tick {
            // 1. Queue the pulse as a next-tick deferred spatial event.
            self.next_tick_deferred_events.push(DeferredEvent {
                target_stage: 3, // TargetResolution
                event_class: DeferredEventClass::DeferredSpatialEvent,
                source_entity_id: zone.id.to_string(),
                ready_tick: self.current_tick + 1,
                sort_key: deterministic_zone_pulse_sort_key(zone.id, self.current_tick),
                payload: SchemaTypedPayload {
                    payload_type_id: "zone_pulse_trigger",
                    schema_version: 1,
                    body: ArpgDeferredPayload::ZonePulseTrigger {
                        zone_id: zone.id,
                        context: zone.pulse_context.clone(),
                    },
                },
            });
            
            // 2. Schedule next pulse
            zone.next_pulse_tick = self.current_tick + zone.pulse_interval_ticks;
            
            // 3. Decrement duration
            zone.remaining_duration_ticks = zone.remaining_duration_ticks
                .saturating_sub(zone.pulse_interval_ticks);
        }
        
        // 4. Cleanup expired zones
        if zone.remaining_duration_ticks == 0 {
            self.mark_for_despawn(zone.id);
        }
    }
}
```

## References

- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` — AbilityEntry (pulse_interval_ticks, duration_ticks)
- `docs-core/01-1-spatial-primitive-catalog.md` — P-09 (Shape Overlap Query), P-14 (Proximity Monitor)
- `docs-game-compiler/03-1-compiler-ir-specification.md` — Stage 11 (StateUpdate)
