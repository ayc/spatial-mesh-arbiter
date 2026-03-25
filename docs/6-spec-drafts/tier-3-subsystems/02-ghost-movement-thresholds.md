# T3-02: Ghost Movement Thresholds

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md`

## Problem Statement

Ghost anomaly detection uses `GhostMovementClass` (Normal, HighSpeed, Teleport) to determine expected displacement per tick via `max_allowed_displacement(movement_class, dt)`. But the classification thresholds and the function itself are missing.

## Resolution

### Classification Thresholds

Thresholds are defined in `LiveConfig` and are live-tunable via Data Epoch:

```rust
struct GhostMovementConfig {
    // Velocity thresholds (units per tick at 60Hz)
    normal_max_velocity:    SimFixed,  // default: 0.5  (30 units/sec — walking/running)
    high_speed_max_velocity: SimFixed, // default: 2.0  (120 units/sec — dashes/leaps)
    // Above high_speed_max_velocity → classified as Teleport
}
```

| Class | Velocity Range (units/tick) | Velocity Range (units/sec) | Examples |
|-------|---------------------------|---------------------------|----------|
| `Normal` | 0 to 0.5 | 0 to 30 | Walking, running, kiting |
| `HighSpeed` | 0.5 to 2.0 | 30 to 120 | Charge (SK-34), Spectral Dash (SK-39), Fear flee |
| `Teleport` | > 2.0 | > 120 | Blink (SK-35), Portal (SK-69), Time Rewind (SK-37) |

### `max_allowed_displacement` Definition

```rust
fn max_allowed_displacement(class: GhostMovementClass, dt: u64, config: &GhostMovementConfig) -> SimFixed {
    let dt_fixed = SimFixed::from_num(dt);
    match class {
        GhostMovementClass::Normal => {
            config.normal_max_velocity * dt_fixed
        },
        GhostMovementClass::HighSpeed => {
            config.high_speed_max_velocity * dt_fixed
        },
        GhostMovementClass::Teleport => {
            // Teleport has no distance limit — it's expected to be large
            SimFixed::MAX
        },
    }
}
```

### Classification at Source

The **authoritative Arbiter** (not the Ghost-holding neighbor) classifies movement when sending Ghost updates:

```rust
fn classify_movement(displacement: SimFixed, dt: u64, config: &GhostMovementConfig) -> GhostMovementClass {
    if dt == 0 { return GhostMovementClass::Teleport; }
    let velocity = displacement / SimFixed::from_num(dt);
    if velocity > config.high_speed_max_velocity {
        GhostMovementClass::Teleport
    } else if velocity > config.normal_max_velocity {
        GhostMovementClass::HighSpeed
    } else {
        GhostMovementClass::Normal
    }
}
```

The classification is included in the `GhostUpdate` payload so the receiving Arbiter knows what displacement to expect.

### Lag Spike vs Legitimate Teleport

A stale Ghost update (large `dt`) with large displacement looks identical to a teleport. The distinction:

1. **Legitimate teleport:** The source Arbiter classifies it as `Teleport` in the Ghost update. The receiver trusts the classification.
2. **Lag spike:** No Ghost update arrives for many ticks, then a `Normal` or `HighSpeed` classified update arrives with a large `dt`. `max_allowed_displacement` scales with `dt`, so a Normal update with `dt=60` (1 second gap) allows `0.5 * 60 = 30 units` of displacement. If the observed displacement exceeds this (entity teleported due to lag), the anomaly path triggers and the Ghost degrades until a correction arrives.

This means: lag spikes that produce small displacements are tolerated (the formula scales). Lag spikes that produce large displacements are caught and degraded. Legitimate teleports are pre-classified and accepted.

### Interaction with `GhostMovementReplicationCadence`

The `GhostMovementReplicationCadence` enum (from `docs-core/04-2-game-adapter-api-contract.md`) controls how OFTEN updates are sent. `GhostMovementClass` classifies the CONTENT of each update. They are orthogonal:

| Cadence | Class | Example |
|---------|-------|---------|
| `Standard` | `Normal` | Player walking around |
| `Standard` | `HighSpeed` | Player using a dash ability |
| `High` | `Normal` | Projectile traveling at moderate speed |
| `High` | `Teleport` | Projectile that blinks to a new position |
| `None` | N/A | Static zone — no updates sent |

### Baseline Profile Keys

```
ghost_normal_max_velocity:      0.5    // units/tick
ghost_high_speed_max_velocity:  2.0    // units/tick
```

These SHOULD be defined in `LiveConfig` (hot-tunable via Data Epoch) rather than in the core baseline profile, since they are game-dependent tuning values.

## References

- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — Ghost anomaly detection
- `docs-core/04-2-game-adapter-api-contract.md` §3.6.2 — `GhostMovementReplicationCadence`
- `docs/1-architecture/06-kinematic-dilation.md` — Movement velocity scaling under dilation
