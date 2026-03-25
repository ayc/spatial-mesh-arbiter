# T4-03: Debug Canvas Spec

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `5-testing-and-conformance/01-mini-mesh-conformance.md`

## Problem Statement

A "2D Debug Canvas" for real-time R-Tree visualization is referenced but not specified: framework, data source, visualization layers, interaction model.

## Resolution

### 1. Architecture: Standalone Web Application

**Framework:** HTML5 Canvas + WebSocket client. No native dependencies — runs in any browser.

**Rationale:** A web-based canvas is the lowest-friction option for developers. No build step, no framework installation, no GPU requirements. The Canvas 2D API handles 4,000+ entity dots at 60fps. If performance becomes an issue at higher entity counts, WebGL can be added as an optimization pass.

### 2. Data Source: Controller Telemetry Stream

The debug canvas connects to the **Mesh Controller's debug endpoint** (WebSocket), which aggregates topology and entity state from all Arbiters.

```
Controller maintains:
  - R-Tree partition boundaries (from topology state)
  - Per-Arbiter entity counts
  - Per-Arbiter dilation factors
  - Global entity position snapshots (sampled, not every tick)

Controller → Debug Canvas (WebSocket, 10Hz):
  DebugFrame {
      tick: u64,
      partitions: Vec<PartitionView>,    // Cell boundaries + metadata
      entities: Vec<EntityDot>,           // Position + team + type
      ghosts: Vec<GhostDot>,             // Ghost positions + quality
  }
```

**Sampling:** The Controller sends debug frames at 10Hz (every 6 ticks), not 60Hz. This keeps bandwidth manageable. Entity positions are sampled snapshots, not authoritative — the canvas is a visualization tool, not a replay viewer.

### 3. Visualization Layers

| Layer | Content | Default On? | Color Scheme |
|-------|---------|:-----------:|-------------|
| **Topology** | R-Tree partition boundaries, Arbiter IDs | Yes | White cell borders, Arbiter ID labels |
| **Entities** | Player dots, NPC dots, projectile dots | Yes | Team-colored dots (blue/red/green/yellow) |
| **Ghosts** | Ghost entity positions | No | Semi-transparent dots, red = Degraded |
| **Interest Rings** | Per-entity visibility/combat rings | No | Dashed circles at `visible_radius` and `combat_radius` |
| **Dilation Zones** | Per-partition dilation factor heatmap | No | Green (1.0) → Yellow (0.5) → Red (0.2) |
| **Handoff Arrows** | Active entity handoffs between Arbiters | No | Animated arrows showing handoff direction |
| **Dynamic Geometry** | P-08 injected collision geometry | No | Orange rectangles/circles |
| **Spawn Points** | NPC spawn locations | No | Star markers |

### 4. Interaction

| Action | Behavior |
|--------|----------|
| Pan | Click-drag to scroll the viewport |
| Zoom | Mouse wheel or pinch to zoom |
| Click entity | Show entity details panel (ID, HP, position, team, dilation, Arbiter) |
| Click partition | Show Arbiter details (entity count, dilation factor, tick rate, queue depth) |
| Layer toggles | Checkbox panel to enable/disable each layer |
| Pause | Freeze the display at the current frame (data continues buffering) |
| Time scrub | Scrub backward through buffered frames (last 60 seconds at 10Hz = 600 frames) |

### 5. Controller Debug Endpoint

```
GET /debug/canvas → Upgrade to WebSocket

Messages (Controller → Canvas):
  DebugFrame (10Hz)

Messages (Canvas → Controller):
  SetSampleRate { hz: u8 }       // Override sample rate (1-30Hz)
  RequestEntityDetail { id }      // Request full entity state snapshot
  RequestPartitionDetail { id }   // Request full Arbiter metrics
```

**Security:** The debug endpoint MUST only be available in dev/staging environments. Production deployments MUST disable it or require auth.

### 6. Deployment

| Environment | Availability | Notes |
|-------------|:----------:|-------|
| Local dev (Docker Compose) | Always on | `http://localhost:9090/debug` |
| Staging | Enabled with auth | Requires dev team credentials |
| Production | Disabled | Endpoint not compiled/deployed |

The canvas HTML/JS is served as a static asset by the Controller process. No separate deployment needed.

### 7. Performance Budget

| Constraint | Target |
|-----------|--------|
| Canvas render budget | < 16ms per frame (60fps) |
| Max entity dots before degradation | 5,000 (at 10Hz update) |
| WebSocket bandwidth | < 500 KB/s at 10Hz with 4,000 entities |
| Frame buffer (time scrub) | 600 frames (60 seconds at 10Hz) |

If entity count exceeds the render budget, the canvas automatically enables spatial LOD: entities beyond a distance threshold are rendered as single-pixel dots instead of labeled circles.

## References

- `docs/5-testing-and-conformance/01-mini-mesh-conformance.md` — Debug Canvas mention
- `docs/1-architecture/03-mesh-controller.md` — Controller state and topology management
