# Kinematic Dilation (KiDi)

Kinematic Dilation is a core feature of the Spatial Mesh Arbiter engine. This document is the authoritative reference for what KiDi is, how it works, and how to implement systems that interact with it correctly.

---

## 1. What KiDi Is

Kinematic Dilation is a **diegetic environmental hazard** — an intentional, in-world mechanic that physically slows entities in spatially overloaded zones.

When too many entities occupy a single Arbiter cell that cannot be further subdivided (the cell has hit `min_cell_size`), the engine does **not** degrade server performance, drop frames, or reduce tick rate. Instead, it creates a "Temporal Swamp": a zone where all entities move slower, cast slower, and recover slower — as if wading through thick temporal mud.

**KiDi is a gameplay mechanic, not a server optimization.**

### 1.1 The "Temporal Swamp" Philosophy

- **Self-Correcting Incentive.** Slow-motion combat is unpleasant. Players are incentivized to leave the overloaded zone and spread out. This naturally disperses the crowd, allowing the R-Tree to split the hotspot into multiple Arbiters.
- **Predictable Degradation.** A player shooting into a dilated zone sees their projectile smoothly decelerate at the boundary. This is a visible, understandable game mechanic — not mysterious lag.
- **Transparency.** A backend infrastructure limitation (too many entities in one cell) is expressed as an in-world phenomenon. Players experience a cinematic slow-motion battle, not dropped inputs or rubber-banding.
- **Per-Zone Isolation.** A player fighting in a 4,000-player blackhole experiences slow-motion, while another player on the *same physical Edge Node* standing in an empty forest plays at full speed. Dilation is spatial, not global.

### 1.2 When KiDi Activates

KiDi works alongside the other density defenses, not strictly after them:

1. **Soft Collision (§8.1)** pushes crowded entities outward, expanding the crowd's physical footprint so the R-Tree can split the hotspot.
2. **R-Tree splitting** subdivides overloaded cells into smaller Arbiter nodes — but only if the cell is larger than `min_cell_size`.
3. **KiDi** activates whenever `entity_count > safe_entity_threshold` (default 300), regardless of whether the cell can still subdivide. Splitting and dilation can coexist — an Arbiter at 500 entities may be dilated while the Controller is preparing a split.

At maximum density (cell at `min_cell_size`, cannot split further), KiDi is the **sole remaining defense**. But it doesn't wait for that point — it ramps in gradually as density increases, giving players a visible signal to disperse before conditions worsen.

Below `safe_entity_threshold`, `dilation_factor = 1.0` (full speed, no effect).

---

## 2. How It Works

### 2.1 The Core Invariant

> **The Arbiter always runs at full 60Hz. Every tick is a full simulation tick. The Shard Tick always increments at 60Hz. What changes is the speed of entities inside the dilated zone.**

There are no "heavy frames" or "light frames." There is no frame skipping or tick interleaving. The server does not slow down. Entities slow down.

### 2.2 The Dilation Factor

Each Arbiter calculates a local `dilation_factor` (range `[minimum_dilation_factor, 1.0]`) every tick based on current entity density:

```
density_ratio = (current_entities - safe_entity_threshold) / (critical_entity_threshold - safe_entity_threshold)
clamped_ratio = clamp(density_ratio, 0.0, 1.0)
curve_mult = clamped_ratio ^ curve_exponent
dilation_factor = 1.0 - (curve_mult * (1.0 - minimum_dilation_factor))
```

With defaults (`safe=300`, `critical=1000`, `exponent=2.0`, `min=0.2`):

| Entity Count | dilation_factor | Entity Speed |
|-------------|-----------------|-------------|
| ≤ 300 | 1.0 | Full speed |
| 400 | ≈ 0.98 | 98% speed |
| 650 | ≈ 0.80 | 80% speed |
| 850 | ≈ 0.52 | 52% speed |
| ≥ 1000 | 0.20 | 20% speed (minimum) |

The quadratic curve (`exponent=2.0`) provides a gradual ramp — barely noticeable at moderate density, steep at high density. The curve shape is live-tunable via `DilationConfig` in the `SpellData` asset dictionary (Data Epoch hot-patches).

### 2.3 The Effective Time Multiplier

An entity's effective time multiplier combines the zone-level dilation with any per-entity time scaling:

```
effective_time = dilation_factor * entity.core_stats.time_scale
```

`CoreStats.time_scale` (default 1.0) allows gameplay effects to further slow or hasten individual entities (e.g., a "Haste" buff sets `time_scale = 1.3`, a "Slow" debuff sets `time_scale = 0.5`). These stack multiplicatively with zone dilation.

### 2.4 No Smoothing, No Hysteresis

`dilation_factor` is recalculated from the current entity count at the start of every tick. There is no temporal smoothing or hysteresis. The quadratic curve itself provides a gradual ramp — if 10 entities arrive in one tick, the dilation factor changes smoothly because the curve is continuous.

This is a deliberate design choice: `dilation_factor` must be reproducible from entity count alone. Any temporal state (smoothing filters, ramp timers) would need to be serialized during merges and maintained consistently across WAL replay, adding complexity for no perceptible gameplay benefit.

---

## 3. What Gets Dilated

### 3.1 Dilated Systems (Affected by `dilation_factor`)

| System | How dilation applies |
|--------|---------------------|
| **Entity movement** | `position += velocity * effective_time` every tick. Entities move slower. |
| **NPC movement** | Same as entity movement. NPC FSMs use dilated velocity. |
| **Projectile travel** | `position += velocity * step_dilation` (with cross-boundary blending near zone seams — see §5). |
| **Ability cooldowns** | Cooldown timers decrement by `effective_time` per tick instead of 1. Abilities recharge slower. |
| **Cast times** | Cast progress advances by `effective_time` per tick. Abilities cast slower. |
| **Status effect duration** | `remaining_time` decrements by `effective_time` per tick. A 10-second buff lasts 10 seconds of *entity time* — in a 0.2 swamp that's 50 wall-clock seconds, because time moves slower for the entity. |
| **Status effect pulses** | Pulse timer advances by `effective_time` per tick. Pulses fire less frequently in ticks, but the total number of pulses over the effect's duration remains the same. |
| **Knockback** | Knockback velocity is integrated with dilation via the movement system. Entities are knocked back slower. |
| **Edge Node prediction** | The Edge Node receives `dilation_factor` and applies it to its local Proxy Actor: dilated movement prediction, dilated cooldown display, dilated ability timing. |

### 3.2 Non-Dilated Systems (Run at Full Speed Every Tick)

| System | Why not dilated |
|--------|----------------|
| **Shard Tick increment** | The clock always advances at 60Hz. Dilation does not change the tick rate. |
| **Combat resolution** | Damage math, evasion, block, crit — all resolve at full speed. A hit that lands doesn't deal less damage. |
| **Inbox processing** | All proposals from the external and internal inboxes are processed every tick. Nothing is deferred or skipped. |
| **Interest management** | State broadcasts happen every tick. The *content* of those broadcasts changes less frequently (because entities move less), but the broadcast cadence is unchanged. |
| **Metronome correction** | Clock discipline runs every tick. The Arbiter's relationship to the global Metronome is never dilated. |
| **Global events** | Execute on their scheduled tick like any other tick. No special "priority interrupt" needed. |
| **Ghost integration** | Ghost position updates are processed every tick. |

### 3.3 The Key Distinction

**Timers and movement are dilated. Resolution and processing are not.**

An ability that hits doesn't deal less damage — it just takes longer to cast, and the target moves slower trying to dodge. A DoT doesn't deal less total damage — it just ticks slower, delivering the same total over a longer real-time duration. The Arbiter doesn't skip work — entities just generate less work per tick because they're doing everything slower.

---

## 4. How Load Reduction Works

KiDi reduces Arbiter load **without frame skipping** through three indirect mechanisms:

### 4.1 Edge Node Throttle

The `dilation_factor` is propagated to Edge Nodes via `TopologyUpdate`. The Edge Node applies it to the player's Proxy Actor session state:

- Movement prediction runs at dilated speed
- Ability cooldowns display at dilated rate
- The player **physically cannot move or cast as fast**

This creates a self-healing throttle: upstream `ActionProposal` volume drops proportionally to dilation. At `dilation_factor = 0.2`, incoming proposals drop by roughly 80%.

### 4.2 Reduced Event Density

Even without the Edge Node throttle, dilated entities generate fewer events per tick:
- Slower movement → fewer collision events
- Slower casting → fewer combat evaluations
- Slower projectiles → fewer boundary crossings
- Slower everything → fewer state changes to broadcast

### 4.3 Soft Collision Expansion

Per §8.1, separation steering pushes crowded entities outward. As the crowd's physical footprint expands, the R-Tree regains the ability to split the hotspot into multiple Arbiters. KiDi buys time for this expansion to occur.

---

## 5. Cross-Boundary Blending

When a projectile (or entity) crosses from one Arbiter zone to another, and the two zones have different `dilation_factor` values, the transition must be smooth — no velocity snap.

### 5.1 The Blend Equation

Given `cross_boundary_blend_width_meters` (from `DilationConfig`), the effective dilation at position `p` near a boundary is:

```
signed_distance = distance from p to boundary (positive = toward destination)
alpha = clamp((signed_distance + blend_width / 2) / blend_width, 0, 1)
effective_dilation = lerp(source_dilation, destination_dilation, alpha)
position_next = position + (velocity * effective_dilation)
```

### 5.2 Normative Rules

- Both Arbiters MUST compute the blend in fixed-point (`SimFixed`) against the same `topology_epoch` boundary geometry.
- Projectile handoff (`Prepare`/`Ack`/`Commit`) transfers ownership only — it MUST NOT rewrite position or velocity to force an abrupt dilation change. Continuity comes from the shared blend equation.
- Edge prediction SHOULD apply the same blend equation from `TopologyUpdate` data to avoid client/server divergence near boundaries.

---

## 6. Dilation Propagation

The `dilation_factor` is propagated to three destinations:

| Destination | Transport | Purpose |
|------------|-----------|---------|
| **Mesh Controller** | `ArbiterHeartbeat.current_dilation` | Topology decisions, telemetry |
| **Edge Nodes** | `TopologyUpdate.my_dilation` | Client-side prediction, ability timing, movement throttle |
| **Neighboring Arbiters** | `NeighborRegion.dilation_factor` | Cross-boundary blend equation |

---

## 7. Configuration

All KiDi parameters are packaged in `DilationConfig` within the `SpellData` asset dictionary, allowing live-tuning via Data Epoch hot-patches without Arbiter restarts.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `safe_entity_threshold` | 300 | Below this, `dilation_factor = 1.0` (no effect) |
| `critical_entity_threshold` | 1000 | At/above this, `dilation_factor = minimum_dilation_factor` |
| `minimum_dilation_factor` | 0.2 | Absolute floor (1/5th speed) |
| `curve_exponent` | 2.0 | Quadratic ramp shape (higher = steeper at high density) |
| `cross_boundary_blend_width_meters` | *(see config registry)* | Interpolation band width for cross-zone transitions |

---

## 8. Client-Side Indicator

### 8.1 The KiDi Pressure Gauge

When a player enters a dilated zone (`dilation_factor < 1.0`), the client displays a **KiDi coefficient indicator** — a pressure gauge-style UI element showing the current dilation level. This is the player's primary telegraph that they are in (or approaching) a Temporal Swamp.

- **Appears** when `dilation_factor < 1.0` (any dilation active)
- **Disappears** when `dilation_factor = 1.0` (full speed, no dilation)
- **Visual range:** 1.0 (full speed, green) → 0.2 (minimum speed, red), with a gradient indicating severity
- **Updates** every time the Edge Node receives a `TopologyUpdate` with a new `my_dilation` value

The indicator serves as the diegetic warning system. Players don't need a "you are entering a danger zone" popup — they see the needle drop and can decide whether to push deeper or pull back. The gradual curve means the needle moves slowly at first (barely noticeable at 0.98) and accelerates as conditions worsen, giving players time to react.

### 8.2 No Server-Side Work Required

The Edge Node already receives `dilation_factor` via `TopologyUpdate`. The client reads this value and renders the indicator. No new server messages, no new protocol fields, no new processing. The indicator is purely a client-side interpretation of existing data.

---

## 9. The Self-Correcting Feedback Loop

KiDi's load reduction is self-correcting through a closed feedback loop:

```
More entities enter zone
    → dilation_factor decreases
        → Edge Nodes throttle player input (slower movement, slower casting)
            → fewer ActionProposals reach the Arbiter per tick
                → Arbiter load stays manageable
        → KiDi pressure gauge warns players
            → players choose to leave the zone
                → entity count drops
                    → dilation_factor increases
                        → zone returns to normal speed
```

This is why entity count is a sufficient input to the dilation formula — even though "300 entities idle" is different from "300 entities fighting," the throttle mechanism makes the distinction irrelevant. If those idle entities start fighting, the Edge Node throttle ensures their combat actions are already rate-limited by the dilation factor. The load self-corrects.

The pressure gauge adds a human feedback path on top of the mechanical one: even if the Edge Node throttle alone would stabilize the Arbiter, the pressure gauge gives players a reason to *choose* to leave, which resolves the overload faster.

---

## 10. Patterns and Anti-Patterns

### 10.1 Correct Implementation Patterns

**"Multiply by dilation"** — Any system that involves entity speed, action timing, or duration should multiply its per-tick delta by `effective_time` (which is `dilation_factor * entity.core_stats.time_scale`).

```rust
// CORRECT: movement
entity.position += entity.velocity.saturating_mul(effective_time);

// CORRECT: cooldown recovery
ability.cooldown_remaining -= effective_time;

// CORRECT: status effect pulse timer
effect.pulse_timer -= effective_time;
if effect.pulse_timer <= SimFixed::ZERO {
    apply_pulse(effect);
    effect.pulse_timer += effect.pulse_interval; // Reset, preserving remainder
}

// CORRECT: status effect duration
effect.remaining_time -= effective_time;
if effect.remaining_time <= SimFixed::ZERO {
    expire_effect(effect);
}
```

**"Resolution is instant"** — Combat math (damage calculation, evasion check, block check) happens at full speed. When an ability's cast time completes (dilated), the resulting damage is applied immediately (not dilated). Dilation affects *when* things happen, not *how much* they do.

**"Propagate to Edge"** — Always include `dilation_factor` in downstream `TopologyUpdate` so Edge Nodes can match their local prediction to the server's entity timing.

### 10.2 Anti-Patterns (Do NOT Do These)

**"Frame skipping / tick interleaving"** — Do NOT implement dilation by skipping simulation frames. Every tick runs the full simulation loop. The Arbiter does not slow down; entities do. Frame skipping creates a cascade of edge cases: What happens to proposals arriving on skipped frames? Do timers tick on skipped frames? Do pulses fire? None of these questions exist when every tick is a full tick.

**"Server-side CPU optimization"** — Do NOT think of KiDi as a way to reduce server CPU usage. KiDi reduces load *indirectly* through the Edge Node throttle and reduced event density, not by making the Arbiter do less work per tick. If you need to optimize Arbiter CPU, profile and optimize the simulation loop — don't skip frames.

**"Tick rate reduction"** — Do NOT reduce the Arbiter's tick rate under load. The Shard Tick is always 60Hz. The Metronome is always 60Hz. Reducing tick rate would break cross-boundary synchronization, Metronome discipline, and the global event scheduling contract.

**"Dilated damage"** — Do NOT reduce damage or healing values based on dilation. A Fireball in the Temporal Swamp deals the same damage as a Fireball outside it. The difference is that the Fireball takes longer to cast, travels slower, and the target moves slower trying to dodge it.

**"Cheating entity time"** — Do NOT decrement buff/effect timers at wall-clock rate to "prevent exploits." Timers decrement by `effective_time` per tick, which means a 10-second buff at `dilation_factor = 0.2` takes 50 wall-clock seconds to expire. This is intentional — the entity experiences 10 seconds of subjective time. The swamp stretches time for everything: movement, casting, cooldowns, *and* buff durations. Decrementing at wall-clock rate would break the diegetic model (buffs would expire faster relative to the entity's actions, making the swamp punish buff-reliant playstyles disproportionately).

**Time in this engine is entity time.** When the spec says a buff lasts "10 seconds," that means 10 seconds of entity time. In a Temporal Swamp at 0.2 dilation, that's 50 wall-clock seconds — but the entity only performs 10 seconds worth of actions during that period. Everything is proportionally slower: the buff, the movement, the casting, the combat. No system gets an unfair advantage or disadvantage from dilation.

---

## 11. Relationship to Other Systems

| System | Interaction |
|--------|-------------|
| **R-Tree / Mesh Controller** | KiDi activates when the R-Tree cannot subdivide further. The Controller monitors `current_dilation` via heartbeats. |
| **Soft Collision (§8.1)** | First line of defense. Pushes entities apart so the R-Tree can split. KiDi is the fallback when soft collision alone isn't enough. |
| **Edge Node / Proxy Actor** | Receives `dilation_factor`, applies to local prediction and throttle. Creates the self-healing load reduction loop. |
| **Cross-Boundary Combat** | `InternalPreparedHit` carries pre-rolled damage (not dilated). Defender resolves at full speed. |
| **Projectile Handoff** | Blend equation ensures smooth velocity transition across zone boundaries. Handoff protocol doesn't modify position/velocity. |
| **Global Events** | Execute on their scheduled tick. No special handling needed — every tick is a full tick. |
| **Status Effects** | Pulse timers and durations advance at dilated rate. Total effect (damage, healing) is preserved; delivery is stretched. |
| **NPC AI** | NPC FSMs and AI Nodes operate at dilated speed. Decision frequency is unchanged, but movement/casting is slower. |
| **Client UI** | Receives `dilation_factor` from Edge Node. Displays KiDi pressure gauge when `dilation_factor < 1.0`. Purely client-side rendering of existing data. |
| **Mini-Mesh Conformance** | Scenario C ("Blackhole") tests KiDi: 30 bots at `[0,0]` should trigger dilation, bots visibly slow down. |
