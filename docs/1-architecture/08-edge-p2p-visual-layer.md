# Edge P2P Visual Layer

This document specifies the peer-to-peer communication model between Edge Nodes for visual state (animations, movement, ability casts) and the Arbiter's role as referee for authoritative consequences (damage, death, status effects).

The core principle: **P2P carries intent and animation. The Arbiter carries consequence.**

---

## 1. Motivation

In the baseline architecture, all entity state flows through the Arbiter:

```
Client A → Edge A → Arbiter → Edge B → Client B
```

This adds a full Arbiter round trip (~16ms at 60Hz + network) to every visual update. For close-range melee combat — where players need to see the axe swing connect instantly — that latency is the difference between responsive and sluggish.

The P2P visual layer adds a parallel fast path:

```
Client A → Edge A ──P2P──→ Edge B → Client B     (immediate visual)
                 └──────→ Arbiter ──→ Edge B      (authoritative consequence)
```

Edge B's client sees the attack animation immediately via P2P. The HP bar change arrives one Arbiter tick later. The animation itself takes longer than 16ms to play, so the consequence arrives before the visual impact frame — the player perceives zero delay.

---

## 2. The Two-Channel Model

Every gameplay interaction produces two kinds of information:

| Channel | Carries | Source | Latency | Authority |
|:--------|:--------|:-------|:--------|:----------|
| **P2P Visual** | Intent: "I am swinging my axe at you." Animation state, position, ability cast VFX. | Edge → Edge (direct UDP) | Edge-to-Edge (~1–5ms same region) | Optimistic. Pre-validated by the sending Edge Node but not confirmed by the Arbiter. |
| **Arbiter Authoritative** | Consequence: "You took 342 damage." HP changes, death, status effects, loot, hard state transitions. | Arbiter → Edge (existing downstream) | Edge-to-Arbiter-to-Edge (~16–33ms) | Final. The Arbiter is the sole authority for all mechanical outcomes. |

### 2.1 What P2P Visual Messages Contain

P2P messages are **visual hints**, not game state. They carry enough for the receiving client to render animations and anticipate outcomes, but never carry mechanical values that affect gameplay.

```rust
/// Sent Edge-to-Edge over direct UDP. Pre-validated by the sender.
struct PeerVisualUpdate {
    source_entity_id: EntityID,
    source_tick: u64,
    payload: PeerVisualPayload,
}

enum PeerVisualPayload {
    /// Continuous: position, velocity, facing direction.
    /// Sent every tick (or less, based on distance tier).
    Movement {
        position: NetVec2,      // Quantized to i32 for compactness
        velocity: NetVec2,
        rotation: NetCoord,
    },

    /// Discrete: an ability cast has started. Client should begin
    /// playing the cast animation and any telegraph VFX.
    AbilityCast {
        ability_id: u16,
        target_entity_id: Option<EntityID>,
        target_position: Option<NetVec2>,
    },

    /// Discrete: a melee/ranged attack is in flight toward a target.
    /// Client should play the swing/projectile animation.
    AttackIntent {
        ability_id: u16,
        target_entity_id: EntityID,
    },

    /// Discrete: entity started a channel/charge-up. Client shows
    /// the charge bar or channel animation.
    ChannelStart {
        ability_id: u16,
        duration_ticks: u32,
    },

    /// Discrete: entity interrupted its own cast/channel.
    CastInterrupted,

    /// Entity visual state change (stance, mount, stealth shimmer).
    VisualStateChange {
        visual_state: u16,     // Game-defined enum (engine treats as opaque)
    },
}
```

**What P2P messages never contain:**
- Damage values
- HP or resource changes
- Status effect application or removal
- Loot events
- Any hard state transition

These come exclusively from the Arbiter via the existing `DownstreamPayload::StateUpdate` channel.

### 2.2 Edge Node Pre-Validation

The Edge Node is a headless game client with a full copy of its player's entity state. Before sending any P2P message, it validates the action locally:

```
Client presses "Cast Fireball"
    │
    Edge A checks:
    ├── Enough mana?
    ├── Ability off cooldown?
    ├── Target in range?
    ├── Not stunned/silenced?
    │
    ├── FAIL → Reject locally. Tell client "insufficient mana."
    │          Nothing sent to P2P. Nothing sent to Arbiter.
    │
    └── PASS → Send PeerVisualUpdate::AbilityCast to nearby peers (P2P)
               Send ActionProposal to Arbiter (existing path)
```

This means P2P messages are **pre-screened**. The vast majority of invalid actions are caught at the Edge Node and never transmitted. The Arbiter only corrects race conditions and cross-player contention that the Edge Node cannot see:

- Target died on another Edge Node's proposal this tick
- Two players targeting the same contention-locked interactable
- Edge Node had stale geometry (post-split boundary mismatch)

### 2.3 Reconciliation: Silence Is Correction

When the Arbiter rejects an action that P2P already showed optimistically, the Arbiter does **not** send an explicit "cancel that animation" message. Instead:

- The P2P visual (attack animation) plays on the observer's client.
- The Arbiter sends `ActionFailed` to the acting player's Edge Node.
- The observer's client **never receives a damage confirmation** for that attack.
- The observer's client interprets the absence as a miss, dodge, or fizzle and can play an appropriate effect.

The Arbiter only sends explicit corrections when the **Arbiter's authoritative state diverges from what P2P would have predicted** — primarily position corrections when movement validation fails:

```rust
/// Arbiter → Edge (existing downstream channel).
/// Sent only when the Arbiter's validated state materially diverges
/// from what P2P visual updates would have shown.
DownstreamPayload::EntityCorrection {
    entity_id: EntityID,
    corrected_position: Vec2F,
    corrected_velocity: Vec2F,
    reason: CorrectionReason,
}

enum CorrectionReason {
    WallCollision,        // Entity clipped through static geometry
    SpeedViolation,       // Movement exceeded validated max speed
    PositionDesync,       // Accumulated drift exceeded threshold
    ForcedRelocation,     // Knockback, teleport, or server-initiated move
}
```

---

## 3. Proximity Manifest (Arbiter-Managed Peer Discovery)

Edge Nodes do not know who is nearby. Only the Arbiter has the spatial index. The Arbiter manages P2P connectivity by sending each Edge Node a **proximity manifest** — a list of peers and their distance tiers.

### 3.1 Distance Tiers

```rust
enum DistanceTier {
    /// 0–35m: Full P2P. Movement every tick, all discrete events.
    /// Combat can happen at this range — visual responsiveness is critical.
    Combat,

    /// 35–80m: Reduced P2P. Movement every 3rd tick, discrete events only
    /// for visually significant actions (large AoE casts, boss abilities).
    Awareness,

    /// 80–140m: Minimal P2P. Movement every 10th tick. No discrete events.
    /// Entity is a moving sprite in the distance.
    Peripheral,

    /// 140m+: No P2P connection. Entity does not exist to this observer.
    None,
}
```

### 3.2 The Manifest

The Arbiter sends manifest updates to Edge Nodes **only when peer relationships change** — when entities cross tier boundaries, enter/leave the Arbiter's cell, or connect/disconnect. This is infrequent compared to per-tick state broadcasting.

```rust
/// Arbiter → Edge Node. Sent on peer relationship changes only.
struct ProximityManifest {
    /// Peers to add or update. Edge Node opens/maintains direct UDP
    /// connections to these addresses.
    updates: Vec<PeerEntry>,

    /// Peers to remove. Edge Node closes the direct UDP connection.
    removals: Vec<EntityID>,
}

struct PeerEntry {
    entity_id: EntityID,
    edge_address: SocketAddr,    // Direct UDP address for P2P
    tier: DistanceTier,
    /// Opaque visual identity so the client can render the correct sprite
    /// without waiting for full state. Game-defined (class, armor set, etc.)
    visual_archetype: u16,
}
```

The Edge Node maintains a table of active P2P peers, keyed by `entity_id`. On each tick, it sends `PeerVisualUpdate` messages to peers according to their tier's cadence rules.

### 3.3 Cadence Rules by Tier

| Tier | Movement updates | Discrete events | Approximate bytes/tick/peer |
|:-----|:-----------------|:----------------|:---------------------------|
| **Combat** | Every tick (60Hz) | All | ~20 bytes |
| **Awareness** | Every 3rd tick (20Hz) | Visually significant only | ~7 bytes amortized |
| **Peripheral** | Every 10th tick (6Hz) | None | ~2 bytes amortized |
| **None** | — | — | 0 |

Between movement updates, the receiving client dead-reckons using the last known velocity — the same interpolation it already does for Ghost entities.

### 3.4 Cross-Boundary Peers

When an entity is near a cell boundary, the Arbiter includes peers from neighboring cells in the manifest. The Arbiter knows about these entities via the Ghost system. The manifest entry for a cross-boundary peer uses the Ghost's authoritative arbiter's Edge Node address, enabling P2P visual updates to flow directly even across cell boundaries.

If the Ghost's quality is `Degraded` (anomaly detected, frozen position), the Arbiter omits the peer from the manifest or marks it with a flag so the Edge Node falls back to Arbiter-relayed state for that entity.

---

## 4. Arbiter Broadcast Reduction

With the P2P visual layer handling movement and animation, the Arbiter's downstream broadcast responsibilities narrow significantly:

### 4.1 What the Arbiter Still Broadcasts

| Data | To whom | Cadence |
|:-----|:--------|:--------|
| **Full SoftState + SoftExt** | Owning Edge Node only | Every tick |
| **Authoritative combat outcomes** (damage, healing, death, status effects) | Affected Edge Nodes | On event |
| **Entity corrections** | Affected Edge Node | On divergence detection |
| **Proximity manifest updates** | All Edge Nodes | On peer relationship change |
| **Topology updates, global events, data epoch** | All Edge Nodes | On event |

### 4.2 What the Arbiter No Longer Broadcasts

| Data | Previously | Now handled by |
|:-----|:-----------|:---------------|
| Other entities' positions (near ring) | Arbiter → all nearby Edge Nodes, every tick | P2P between Edge Nodes |
| Other entities' positions (mid/far ring) | Arbiter → all Edge Nodes, reduced cadence | P2P between Edge Nodes, tier-gated |
| Ability cast animations | Arbiter → nearby Edge Nodes | P2P visual events |
| Visual state changes | Arbiter → nearby Edge Nodes | P2P visual events |

The Arbiter's downstream bandwidth drops from **O(entities × observers)** per tick to **O(events)** — only combat outcomes and corrections, which are sparse compared to continuous position/animation updates.

---

## 5. Security Model

### 5.1 Trust Boundaries

Edge Nodes are **server-side trusted infrastructure**, not client processes. They run in the same datacenter as the Arbiter. A compromised Edge Node is a server breach, not a client cheat.

P2P messages between Edge Nodes travel over the internal datacenter network. They are:
- **Not encrypted** (same trust boundary as Arbiter ↔ Edge traffic today).
- **Not signed** (Edge Nodes are trusted peers, not untrusted clients).
- **Validated by the sending Edge Node** (pre-screened against local entity state).
- **Never authoritative** (the Arbiter's consequence channel overrides any P2P claim).

### 5.2 Cheat Scenarios

| Cheat | P2P impact | Arbiter response |
|:------|:-----------|:-----------------|
| Speed hack (client claims impossible position) | Edge A sends inflated position to peers. Other clients briefly see the entity moving too fast. | Arbiter detects speed violation in movement validation. Sends `EntityCorrection` to all Edge Nodes. Visual snaps back within one tick. |
| Phantom ability (client claims cast with no mana) | Edge A rejects locally. Nothing sent to P2P or Arbiter. | N/A — never reaches the network. |
| Compromised Edge Node sends fake P2P | Peers show fake animation briefly. | Arbiter never confirms the action. No mechanical effect. Visual glitch resolves in one tick. |

The worst case for P2P visual cheating is a **one-tick visual glitch** — an animation plays for 16ms that shouldn't have. No gameplay consequence.

---

## 6. Edge Node Implementation Changes

### 6.1 New Responsibilities

The Edge Node (`ProxyActor`) gains:

```rust
struct ProxyActor {
    // ... existing fields ...

    /// Active P2P peers from the Arbiter's proximity manifest.
    /// Keyed by entity_id for fast lookup and removal.
    p2p_peers: HashMap<EntityID, PeerConnection>,
}

struct PeerConnection {
    entity_id: EntityID,
    edge_address: SocketAddr,
    tier: DistanceTier,
    visual_archetype: u16,
    ticks_since_last_movement_send: u8,   // For cadence gating
}
```

### 6.2 Tick Loop Additions

The Edge Node's existing 60Hz tick loop (see [Edge Node Envelopes §2.1](../2-contracts-and-interfaces/internal-mesh-types/02-edge-node-envelopes.md)) gains two steps:

```
Existing tick loop:
  1. Aggregate client inputs
  2. Run local physics prediction
  3. Send predicted state to client
  4. Build and send ActionProposal to Arbiter
  5. Timeout stale pending proposals

New additions:
  6. Broadcast PeerVisualUpdate to P2P peers (tier-gated cadence)
  7. Receive and apply PeerVisualUpdates from other Edge Nodes
```

**Step 6 — P2P Outbound:** For each peer in `p2p_peers`, check if this tick satisfies the tier's cadence rule. If so, send a `PeerVisualUpdate::Movement` with the entity's current predicted position and velocity. Discrete events (casts, attacks) are sent immediately to all Combat-tier peers regardless of cadence.

**Step 7 — P2P Inbound:** Receive `PeerVisualUpdate` messages from peers. Update the local visual representation of the peer entity. Dead-reckon between updates using the last known velocity. These updates are **never reconciled against Arbiter state** — they are a visual-only layer. When the Arbiter sends an `EntityCorrection` or `StateUpdate` for the same entity, the authoritative data takes precedence.

### 6.3 Manifest Handling

When the Edge Node receives a `ProximityManifest` from the Arbiter:

1. For each entry in `updates`: insert or update the peer in `p2p_peers`. If this is a new peer, open a UDP socket to `edge_address`.
2. For each entry in `removals`: close the UDP connection and remove from `p2p_peers`. Notify the client to fade out the entity (it has left visual range).

Manifest updates are infrequent — they only fire when entities cross tier boundaries or enter/leave the cell. The Edge Node does not poll for them.

---

## 7. Relationship to Existing Systems

### 7.1 Ghost Entities

The Ghost system handles **cross-boundary** entity visibility at the Arbiter level. P2P handles **same-cell** visual updates at the Edge Node level. They serve different purposes:

| System | Scope | Authority | Purpose |
|:-------|:------|:----------|:--------|
| Ghost entities | Cross-boundary (Arbiter ↔ Arbiter) | Arbiter dead-reckoning with anomaly detection | Arbiter needs approximate positions of entities in neighboring cells for combat validation near borders |
| P2P visual layer | Same-cell (Edge ↔ Edge) | Edge Node pre-validated, optimistic | Players need immediate visual feedback for nearby entities |

For cross-boundary entities that appear in the proximity manifest (§3.4), the Edge Node receives P2P updates from the foreign entity's Edge Node directly. The Ghost system continues to operate at the Arbiter level for validation purposes.

### 7.2 Interest Management

The proximity manifest replaces the Arbiter's per-tick entity broadcast for non-owning observers. The tiered distance model (Combat/Awareness/Peripheral/None) is the interest management system — it just operates at the Edge Node level via P2P rather than at the Arbiter level via downstream broadcast.

The Arbiter retains interest management responsibility for:
- **Owner state**: full `EntityCore` + `SoftExt` to the owning Edge Node every tick
- **Combat outcomes**: damage, healing, death, status effects to affected Edge Nodes
- **Corrections**: position/state corrections when validation diverges from P2P

### 7.3 Kinematic Dilation

Dilation affects P2P visual updates the same way it affects all entity movement. The Edge Node applies the dilation factor (received from the Arbiter via `TopologyUpdate`) when computing predicted positions for P2P broadcast. Observers see dilated movement in P2P — consistent with what the Arbiter validates.

### 7.4 Framework Boundary

In the framework boundary model (see [Framework Boundary §3](07-framework-boundary.md)):

- `PeerVisualPayload` is **partially game-defined**. `Movement` is engine-owned. Discrete events (`AbilityCast`, `AttackIntent`, `ChannelStart`, `VisualStateChange`) are game-defined via an associated type on the `GameActions` trait.
- `DistanceTier` thresholds are **engine configuration** (set in the config registry, tunable per deployment).
- The decision of which discrete events are "visually significant" enough for Awareness tier is **game-defined** (the game tags abilities with a visibility tier in its data assets).

---

## 8. Bandwidth Analysis

### 8.1 Outbound from a Single Edge Node (Combat Tier)

Assume 50 entities in Combat tier (0–35m):
- Movement: 50 peers × 20 bytes × 60Hz = **60 KB/s**
- Discrete events (average 2 casts/sec): 50 peers × 12 bytes × 2 = **1.2 KB/s**
- **Total: ~61 KB/s outbound**

This is well within datacenter UDP capacity and comparable to the Arbiter's current per-Edge broadcast cost — just distributed across Edge Nodes instead of concentrated on the Arbiter.

### 8.2 Arbiter Downstream Savings

| Scenario | Before (Arbiter broadcasts everything) | After (P2P visual layer) |
|:---------|:---------------------------------------|:-------------------------|
| 400 entities, 200 Edge Nodes | ~200 KB/tick downstream from Arbiter | ~5 KB/tick (combat outcomes + corrections only) |
| Arbiter CPU on broadcast | O(entities × observers) serialization | O(events) serialization |
| Arbiter tick budget freed | — | ~2–4ms reclaimed per tick for validation/resolution |

The Arbiter's downstream I/O drops by roughly an order of magnitude. Its tick budget shifts from "serialize and fan out state" to "validate and resolve."

---

## 9. Open Questions

1. **P2P transport.** Should P2P use raw UDP (minimal overhead, no reliability) or the existing `renet` RUDP channels with a dedicated unreliable channel? Raw UDP is simpler for visual-only data that tolerates loss. `renet` provides the connection abstraction that the Edge Node already uses for Arbiter communication.

2. **NAT traversal.** Edge Nodes are server-side infrastructure in the same datacenter, so NAT is not a concern for same-region deployments. For geographically distributed Edge Nodes (edge datacenters), P2P may need to route through a relay or fall back to Arbiter broadcast for cross-region peers.

3. **Peer connection limits.** In extreme density (400+ entities in Combat range during a world boss), each Edge Node would maintain ~400 P2P connections. Should there be a hard cap with fallback to Arbiter broadcast for excess peers? The proximity manifest could enforce a `max_combat_peers` budget.
