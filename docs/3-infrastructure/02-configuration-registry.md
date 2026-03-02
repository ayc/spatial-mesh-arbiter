# Engine Configuration Registry

To guarantee deterministic execution and operational flexibility, the Spatial Mesh engine eschews hardcoded "magic numbers." All tuning variables are centralized into structured configuration files.

These configurations are divided into two categories based on their lifecycle: **Boot Configuration** (infrastructure bounds set at startup) and **Live Configuration** (gameplay and performance dials that can be hot-patched via the Mesh Controller's Data Epochs).

---

## 1. Live Configuration (Hot-Patchable via Data Epoch)

These variables are packaged inside the `SpellData` dictionary. The Mesh Controller can distribute updates to these values at runtime.

### 1.1 Interest Management & Performance
| Variable | Recommended Default | Description |
| :--- | :--- | :--- |
| `combat_radius` | `45.0` meters | Radius for full 60Hz updates. Must be > `max_spell_range`. |
| `visible_radius` | `120.0` meters | Outer cull distance for ambient visual rendering. |
| `keyframe_interval_ticks` | `10` ticks | Update frequency for entities in the outer visible ring (166ms). |
| `max_spell_range` | `40.0` meters | Structural constraint for R-Tree min-cell size. |
| `ghost_anomaly_margin`| `0.75` meters | Tolerance for dead-reckoning before forcing swept-collision. |
| `ghost_degraded_ttl_ticks` | `30` ticks | How long a degraded ghost remains frozen while awaiting reliable correction. |
| `ghost_render_ttl_ticks` | `120` ticks | Hard expiry for stale ghosts if no fresh updates arrive. |

### 1.2 Kinematic Dilation (The "Temporal Swamp")
| Variable | Recommended Default | Description |
| :--- | :--- | :--- |
| `safe_entity_threshold` | `300` entities | Density below which the server runs at 1.0 scale. |
| `critical_entity_threshold`| `1000` entities | Density at which maximum physical slowdown is applied. |
| `minimum_dilation_factor` | `0.2` (1/5th speed)| Absolute floor for simulation speed. |
| `curve_exponent` | `2.0` (Quadratic) | Shape of the slowdown ramp-up. |

### 1.3 Gameplay Lifecycle
| Variable | Recommended Default | Description |
| :--- | :--- | :--- |
| `resurrect_window_ticks` | `600` ticks | 10-second window for healers before hard player despawn. |
| `logout_fuse_ticks` | `3600` ticks | 60-second vulnerability timer for wilderness logouts. |
| `handover_buffer_ticks` | `2` ticks | Lead-time for deterministic RUDP ownership flips. |

---

## 2. Boot Configuration (Static Infrastructure Limits)

These variables dictate memory allocation and security rate limits. They are loaded during Pod startup and cannot change without a restart.

### 2.1 Security & Ingress Fairness
| Variable | Recommended Default | Description |
| :--- | :--- | :--- |
| `proposal_bucket_capacity` | `24` tokens | Maximum burst size for per-entity action proposals. |
| `proposal_bucket_refill_per_tick` | `2` per tick | Actions allowed per second (120/sec). |
| `movement_cost` | `1` token | Token cost for high-frequency position updates. |
| `discrete_cost` | `3` tokens | Token cost for casts, interactions, and items. |

### 2.2 Memory Horizons & Queue Sizes
| Variable | Recommended Default | Description |
| :--- | :--- | :--- |
| `max_event_age_ticks` | `60` ticks | **Horizon for Idempotency Ledger.** Packets older than 1s are dropped. |
| `external_inbox_cap` | `5000` slots | Capacity for Edge Node proposals. |
| `internal_inbox_cap` | `2000` slots | Capacity for cross-server relays and procs. |
| `stale_buffer_cap` | `1000` slots | Capacity for proposals waiting on topology sync. |
| `auth_epoch_window` | `2` epochs | Number of previous topology epochs still accepted for auth. |

### 2.3 Controller Topology Thresholds
| Variable | Recommended Default | Description |
| :--- | :--- | :--- |
| `max_entities_per_arbiter` | `400` entities | Deterministic split trigger threshold per active Arbiter. |
| `min_cell_size_meters` | `40.0` meters | Structural floor for subdivision; below this, Arbiter dilates instead of splitting. |

---

## 3. Canonical Key Map (Compatibility)

The keys above are canonical. Legacy aliases are accepted for backward compatibility in local/dev configs:

| Legacy Key | Canonical Key |
| :--- | :--- |
| `keyframe_interval` | `keyframe_interval_ticks` |
| `safe_threshold` | `safe_entity_threshold` |
| `critical_threshold` | `critical_entity_threshold` |
| `min_dilation` | `minimum_dilation_factor` |
| `resurrect_window` | `resurrect_window_ticks` |
| `logout_fuse` | `logout_fuse_ticks` |
| `handover_buffer` | `handover_buffer_ticks` |
| `bucket_capacity` | `proposal_bucket_capacity` |
| `bucket_refill` | `proposal_bucket_refill_per_tick` |
| `max_event_age` | `max_event_age_ticks` |
