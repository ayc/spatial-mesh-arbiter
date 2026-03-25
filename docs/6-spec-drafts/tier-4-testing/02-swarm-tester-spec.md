# T4-02: Swarm Tester Spec

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `5-testing-and-conformance/01-mini-mesh-conformance.md`

## Problem Statement

The swarm-tester crate is Phase 5 in the implementation plan. Its spec needs: bot behavior model, communication contract, combat patterns, lifecycle, and metrics.

## Resolution

### 1. Bot Behavior Model: Boids + Combat FSM

Each bot runs two systems:

**Movement (Boids flocking):**
```rust
struct BoidsConfig {
    separation_weight:  f32,    // default: 1.5
    alignment_weight:   f32,    // default: 1.0
    cohesion_weight:    f32,    // default: 1.0
    separation_radius:  f32,    // default: 3.0 units
    neighbor_radius:    f32,    // default: 10.0 units
    max_speed:          f32,    // default: 0.4 units/tick (24 units/sec)
    wander_weight:      f32,    // default: 0.5
    wander_radius:      f32,    // default: 20.0 units from spawn
}
```

Boids produce a desired velocity vector each decision tick. The bot submits this as a continuous movement intent.

**Combat (Simple FSM):**
```
Idle → [enemy in range] → Engage → [use ability] → Cooldown → Engage
                                  → [enemy dead] → Idle
                                  → [HP < 30%] → Flee → [HP > 60%] → Idle
```

### 2. Decision Loop Frequency

Bots do NOT decide every tick. Decision frequency is configurable to simulate realistic player input rates:

| Decision Type | Frequency | Notes |
|--------------|-----------|-------|
| Movement | Every 3 ticks (20Hz) | Boids calculation + movement intent |
| Ability usage | Every 6 ticks (10Hz) | Ability selection + cast intent |
| Target selection | Every 12 ticks (5Hz) | Nearest enemy scan |

### 3. Combat Action Selection

```rust
fn select_ability(bot: &Bot) -> Option<AbilityId> {
    let available: Vec<_> = bot.abilities.iter()
        .filter(|a| a.cooldown_remaining == 0 && bot.mana >= a.cost)
        .collect();

    if available.is_empty() { return None; }

    match bot.combat_profile {
        CombatProfile::Random => {
            // Uniform random from available abilities (deterministic RNG)
            Some(available[bot.rng.next_u32() as usize % available.len()].id)
        },
        CombatProfile::Priority(priority_list) => {
            // Use highest priority available ability
            for id in priority_list {
                if available.iter().any(|a| a.id == *id) {
                    return Some(*id);
                }
            }
            None
        },
        CombatProfile::Scripted(script) => {
            // Follow a fixed rotation
            script.next_ability(&available)
        },
    }
}
```

### 4. Bot Authentication

**Test tokens:** Bots use a dedicated test auth provider that issues opaque tokens without real account creation.

```rust
struct BotAuthConfig {
    auth_endpoint:      String,     // Test auth service URL
    token_prefix:       String,     // "bot_" prefix for easy identification
    auto_generate:      bool,       // Generate bot accounts on demand
}
```

The test auth provider is only available in dev/test environments. Production deployments MUST NOT include it.

### 5. Bot Lifecycle

```
1. Connect WebSocket to Edge Node
2. Send ClientHello { auth_token: bot_token }
3. Receive AuthAccepted + initial world state
4. Spawn at configured location (or random within zone)
5. Enter Boids movement + Combat FSM loop
6. Run for configured duration (or indefinitely)
7. Graceful disconnect: RequestLogout → wait for LogoutAccepted
```

### 6. Metrics Emission

Each bot emits metrics via the same telemetry channel as the conformance harness:

| Metric | Type | Description |
|--------|------|-------------|
| `bot.connected` | Gauge | Number of connected bots |
| `bot.proposal_sent` | Counter | Total proposals sent |
| `bot.proposal_accepted` | Counter | Proposals that received OK |
| `bot.proposal_rejected` | Counter | Proposals that received REJECT |
| `bot.ability_cast` | Counter | Abilities successfully cast |
| `bot.damage_dealt` | Counter | Total damage dealt |
| `bot.deaths` | Counter | Bot deaths |
| `bot.decision_latency_us` | Histogram | Time to compute decision |
| `bot.rtt_us` | Histogram | Round-trip time to Edge Node |

### 7. Configuration

```yaml
swarm:
  bot_count: 100
  spawn_zone: "test_arena"
  spawn_stagger_ms: 50           # Delay between bot connections
  combat_profile: "random"       # random | priority | scripted
  run_duration_seconds: 300      # 5 minutes (0 = indefinite)
  boids:
    separation_weight: 1.5
    alignment_weight: 1.0
    cohesion_weight: 1.0
    max_speed: 0.4
    wander_radius: 20.0
  abilities:
    - "basic_attack"
    - "fireball"
    - "heal_self"
```

## References

- `docs/0-getting-started/02-implementation-phases.md` — Phase 5
- `docs/5-testing-and-conformance/01-mini-mesh-conformance.md` — Swarm Tester references
- `docs/2-contracts-and-interfaces/01-client-edge-wire-protocol.md` — WebSocket protocol
