# Core Baseline Profile

This document is the single canonical source for baseline quantitative defaults used by core framework contracts.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope

This profile defines default values for:
1. runtime tick/timing bounds
2. ingress fairness and queue capacities
3. replay/idempotency horizons
4. adapter hook budgets and containment thresholds
5. durability bridge and reconciliation bounds
6. messaging trust/freshness bounds
7. version-line transition and rollback bounds
8. deterministic numeric guardrails

## 2. Usage Rules

1. Core docs MUST reference these keys instead of duplicating numeric defaults.
2. Deployments MAY tune values, but every key MUST remain finite and explicitly configured.
3. Constraint relationships in this document MUST be preserved under tuning.

## 3. Baseline Defaults

### 3.1 Runtime Timing

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `frame_budget_us` | `16_666` | microseconds | fixed 60Hz frame budget |
| `metronome_heartbeat_stale_ticks` | `180` | ticks | stale-mode threshold |
| `metronome_heartbeat_degraded_ticks` | `600` | ticks | degraded-mode threshold |

### 3.2 Ingress Fairness and Queues

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `proposal_bucket_capacity` | `24` | tokens | per-entity burst cap |
| `proposal_bucket_refill_per_tick` | `2` | tokens/tick | per-entity refill rate |
| `movement_cost` | `1` | tokens | continuous movement cost |
| `discrete_cost` | `3` | tokens | non-continuous intent cost |
| `external_inbox_cap` | `5000` | messages | bounded runtime ingress |
| `internal_inbox_cap` | `2000` | messages | bounded relay/control ingress |
| `stale_buffer_cap` | `1000` | messages | bounded epoch-sync buffer |
| `fairness_observation_window_ticks` | `600` | ticks | fairness isolation measurement window |
| `fairness_isolation_max_degradation_pct` | `10` | percent | MUST satisfy `0 <= fairness_isolation_max_degradation_pct <= 100` |

### 3.3 Replay and Idempotency

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `max_event_age_ticks` | `60` | ticks | replay horizon (1.0s at 60Hz) |
| `idempotency_bucket_capacity` | `8192` | keys/bucket | dedupe memory guardrail |
| `stale_sync_timeout_ticks` | `60` | ticks | MUST satisfy `stale_sync_timeout_ticks <= max_event_age_ticks` |

Derived planning formula:
`max_idempotency_keys ~= max_event_age_ticks * idempotency_bucket_capacity`

### 3.4 Adapter Budget and Containment

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `adapter_tick_budget_us` | `6_000` | microseconds/tick | cumulative adapter budget per authoritative tick |
| `validate_hook_budget_us` | `200` | microseconds/call | soft budget |
| `dispatch_stage_budget_us` | `1_500` | microseconds/call | soft budget per stage execution |
| `spawn_hook_budget_us` | `4_000` | microseconds/call | soft budget (off hot path) |
| `hot_hook_timeout_us` | `2_000` | microseconds/call | hard timeout for validate/dispatch hooks |
| `spawn_hook_timeout_us` | `10_000` | microseconds/call | hard timeout for spawn hook |
| `adapter_fault_window_ticks` | `300` | ticks | rolling fault window (5s at 60Hz) |
| `adapter_fault_threshold` | `32` | faults/window | containment entry threshold |
| `adapter_degraded_hold_ticks` | `600` | ticks | minimum containment hold duration |

### 3.5 Durability and Reconciliation

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `tx_pending_timeout_ms` | `30_000` | milliseconds | max wait for runtime confirmation before compensation path |
| `tx_reconcile_scan_interval_ms` | `5_000` | milliseconds | reconciliation worker cadence |
| `runtime_command_dedupe_horizon_ms` | `120_000` | milliseconds | MUST satisfy `runtime_command_dedupe_horizon_ms >= tx_pending_timeout_ms` |
| `durable_consumer_retry_max_attempts` | `8` | attempts | retries before DLQ |
| `durable_consumer_retry_backoff_initial_ms` | `100` | milliseconds | exponential backoff start |
| `durable_consumer_retry_backoff_max_ms` | `5_000` | milliseconds | exponential backoff cap |

### 3.6 Messaging Trust and Freshness

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `auth_clock_skew_tolerance_ms` | `5_000` | milliseconds | max allowed signer/verifier clock skew |
| `external_intent_ttl_ms` | `15_000` | milliseconds | max external-intent freshness window |
| `internal_event_ttl_ms` | `30_000` | milliseconds | max internal-event freshness window |
| `control_command_ttl_ms` | `30_000` | milliseconds | max control-command freshness window |
| `auth_nonce_horizon_ms` | `120_000` | milliseconds | MUST satisfy `auth_nonce_horizon_ms >= max(external_intent_ttl_ms, internal_event_ttl_ms, control_command_ttl_ms)` |

### 3.7 Version-Line Transition and Rollback

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `version_transition_prepare_timeout_ms` | `30_000` | milliseconds | max `PREPARE` phase duration |
| `version_transition_drain_timeout_ms` | `120_000` | milliseconds | max `DRAIN` phase duration |
| `version_transition_commit_stabilization_ticks` | `300` | ticks | minimum `STABILIZE` duration before commit |
| `version_transition_rollback_timeout_ms` | `60_000` | milliseconds | max rollback completion time |
| `version_transition_reject_observation_window_ticks` | `600` | ticks | reject-rate evaluation window |
| `version_transition_max_non_continuous_reject_rate_pct` | `5` | percent | MUST satisfy `0 <= version_transition_max_non_continuous_reject_rate_pct <= 100` |

### 3.8 Deterministic Numeric Guardrails

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `position_fixed_scale` | `1000` | units/meter | MUST be positive integer scale |
| `velocity_fixed_scale` | `1000` | units/(meter/second) | MUST be positive integer scale |
| `max_abs_position_units` | `2_000_000_000` | fixed units | absolute position conversion guardrail |
| `max_abs_velocity_units_per_tick` | `200_000` | fixed units/tick | absolute per-tick velocity guardrail |
| `max_abs_acceleration_units_per_tick2` | `50_000` | fixed units/tick^2 | absolute per-tick acceleration guardrail |

### 3.9 Spatial Primitives (Amendment A)

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `selector_max_targets` | `32` | entities | maximum entities returned by any spatial query (P-09, P-11) |
| `max_query_radius` | `100` | fixed units | maximum radius for shape overlap (P-09) and nearest-neighbor (P-11) queries |
| `max_raycast_length` | `200` | fixed units | maximum ray length for swept-segment raycast (P-10) |
| `shape_overlap_tolerance` | `10` | fixed sub-units (0.01 meters at default scale) | tolerance for shape boundary intersection (P-09) |
| `max_history_buffer_ticks` | `240` | ticks | maximum rewind buffer depth per entity (P-05); 4 seconds at 60Hz |
| `max_dynamic_geometry_per_arbiter` | `64` | objects | maximum injected geometry objects (P-08) |
| `max_dynamic_geometry_area` | `50_000` | fixed area units | maximum total area of injected geometry (P-08) |
| `max_monitored_zones_per_arbiter` | `128` | zones | maximum active proximity monitors (P-14) |

### 3.10 Entity Lifecycle (Amendment C)

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `max_lifecycle_phases_per_entity` | `3` | phases | maximum game-defined life phases per entity type (P-25). Phase IDs 0 (Active) and 255 (Removed) are engine-reserved. |
| `max_entities_per_arbiter` | `2000` | entities | total entities (owned + spawned) on one Arbiter |
| `max_spawned_actors_per_owner` | `8` | entities | maximum actors spawned by a single owner entity (P-32) |
| `max_dormant_entities_per_arbiter` | `256` | entities | maximum simultaneously dormant entities (P-33) |
| `max_suspension_duration_ticks` | `1800` | ticks | maximum entity suspension duration before auto-unsuspend (P-53); 30 seconds at 60Hz |

### 3.11 Entity Relationships (Amendment D)

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `max_bindings_per_entity` | `8` | bindings | maximum active P-34 bindings on a single entity |
| `max_cross_boundary_bindings_per_arbiter` | `256` | bindings | maximum cross-boundary bindings tracked per Arbiter |
| `max_multiplex_group_size` | `4` | entities | maximum entities in an input multiplex group (P-30) |

### 3.12 Dynamic Topology (Amendment E)

| Key | Default | Unit | Constraint |
| --- | --- | --- | --- |
| `max_team_count` | `16` | teams | maximum team IDs for P-52 visibility bitmask. MUST be <= 64. |
| `max_instances_per_arbiter` | `4` | instances | maximum concurrent spatial instances (P-56) |
| `max_entities_per_instance` | `16` | entities | maximum entities in a single spatial instance (P-56) |
| `max_instance_duration_ticks` | `3600` | ticks | maximum instance lifetime (P-56); 60 seconds at 60Hz |
| `max_polyline_geometries_per_arbiter` | `32` | polylines | maximum active polyline generators (P-57) |
| `max_polyline_segments` | `64` | segments | maximum segments per polyline (P-57) |
| `max_container_capacity` | `8` | entities | maximum entities per container (P-58) |
| `max_containers_per_arbiter` | `16` | containers | maximum active containers (P-58) |
| `max_portal_anchors_per_arbiter` | `8` | anchors | maximum portal anchors on one Arbiter (P-59) |
| `max_portal_anchors_per_network` | `8` | anchors | maximum anchors in one portal network (P-59) |
| `max_portal_networks` | `16` | networks | maximum active portal networks across the mesh (P-59) |

## 4. Cross-Document References

This profile is consumed by:
1. `01-spatial-runtime-kernel.md`
2. `01-1-spatial-primitive-catalog.md`
3. `01-2-entity-lifecycle-contract.md`
4. `01-3-entity-relationship-contract.md`
5. `01-4-dynamic-topology-contract.md`
6. `02-spatial-messaging-plane.md`
7. `03-durability-bridge.md`
8. `04-1-game-adapter-contract.md`
9. `04-3-version-line-transition-contract.md`
10. `05-1-conformance-test-matrix.md`
