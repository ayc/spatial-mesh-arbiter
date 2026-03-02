# NPC Runtime and Replication Contract

This document is the canonical architecture/runtime contract for NPC simulation cadence, replication, interest management, reliability classes, and client smoothing behavior.

Canonical split:
- NPC gameplay taxonomy and interaction semantics are canonical in [05. NPC and In-World Interaction Design](../2-gameplay-and-design/05-npc-and-world-interaction-design.md).
- Wire envelope/auth/session contracts remain canonical in [03. Client <-> Edge Message Contract](03-client-edge-message-contract.md).

This document is normative. Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used in RFC-style.

---

## 1. Scope

### In scope
- Runtime NPC simulation cadence by tier.
- Replication contract from Arbiter -> Edge/Client.
- Interest rings, per-client update budgets, and prioritization.
- Reliability class by NPC event/delta type.
- Client interpolation/extrapolation and correction behavior.

### Out of scope
- New client->edge intent IDs or envelope shape changes.
- Full dialogue tree data model and quest graph schema.
- Meta-service internal RPC/event schema.

---

## 2. Core Timing Model (Normative)

1. The authoritative world clock MUST remain on the existing fixed mesh tick.
2. NPC AI and movement MAY execute at sub-rates through tier scheduling.
3. Combat outcomes (hit/death/state mutation) MUST remain authoritative on the core world tick path even when decision cadence is lower.

### 2.1 Default NPC runtime tiers

| Tier | Archetype default | Decision tick | Movement integration | Replication cadence |
| :--- | :--- | :--- | :--- | :--- |
| `T0 CombatCritical` | boss phases, high-threat combat NPCs | `15 Hz` | `30 Hz` | near/mid/far = `15/8/2 Hz` |
| `T1 LaneCreep` | lane creeps and simple combat waves | `10 Hz` engaged, `5 Hz` march | `20 Hz` | near/mid/far = `10/5/1 Hz` |
| `T2 Ambient` | fauna/background world actors | `2 Hz` | `10 Hz` | near/far = `5 Hz` / event-only |
| `T3 SocialStatic` | vendors/quest hubs/service NPCs | `1 Hz` | `0 Hz` (static) | event-only + optional `1 Hz` visible keepalive |

### 2.2 Tier assignment defaults

| NPC archetype | Default tier |
| :--- | :--- |
| `LaneCreep` | `T1 LaneCreep` |
| `NeutralMonster` | `T0 CombatCritical` while engaged, else `T1 LaneCreep` |
| `BossEncounter` | `T0 CombatCritical` |
| `SummonedCombat` | `T0 CombatCritical` while active |
| `SocialServiceNPC` | `T3 SocialStatic` |
| `AmbientFauna` | `T2 Ambient` |
| `ScriptedActor` | `T3 SocialStatic` unless script marks combat-critical window |

---

## 3. Interest Management Contract (Normative)

### 3.1 Per-client rings

Each subscribed client view MUST classify visible NPCs into rings:
- `Near`: full combat relevance.
- `Mid`: reduced cadence relevance.
- `Far`: low-rate or event-only relevance.

Default ring thresholds:
- `Near`: `0-35m`
- `Mid`: `35-80m`
- `Far`: `80-140m`
- beyond `140m`: not replicated unless explicit script override.

### 3.2 Hysteresis

Ring promotion/demotion MUST use hysteresis to prevent flapping:
- promote only after crossing inward threshold for `>= 250 ms`,
- demote only after crossing outward threshold for `>= 500 ms`.

### 3.3 Per-client budget and priority

Hard per-client NPC replication budget defaults:
- `32 KiB/s` payload budget for NPC deltas/events.
- `max 64` NPC delta records per replication batch.

If budget pressure occurs, scheduler MUST degrade in this order:
1. preserve lifecycle-critical events,
2. preserve combat-critical deltas,
3. preserve interaction state transitions,
4. degrade/drop ambient/background deltas first.

---

## 4. Replication Interfaces (Documentation-Level Types)

No client->edge wire envelope changes are required in this phase. These types define downstream/runtime replication contract semantics.

```rust
enum NpcRuntimeTier {
    T0CombatCritical,
    T1LaneCreep,
    T2Ambient,
    T3SocialStatic,
}

enum NpcState {
    Idle,
    PatrolMarch,
    AcquireTarget,
    Engaged,
    EvadeLeash,
    DeadCorpse,
    Despawned,
    ConversationLocked,
    ServiceOpen,
    Unavailable,
    ScriptedControl,
    Interactive,
    CinematicLocked,
}

struct NpcStateDelta {
    npc_id: u64,
    npc_type_id: u16,
    state: NpcState,
    pos_q: (i32, i32),   // quantized NetCoord
    vel_q: (i16, i16),   // quantized velocity
    facing_q: i16,       // quantized orientation
    anim_state: u16,
    server_tick: u64,
}

enum NpcLifecycleKind {
    Spawned,
    Despawned,
    Died,
    Respawned,
    StateReset,
}

struct NpcLifecycleEvent {
    npc_id: u64,
    kind: NpcLifecycleKind,
    server_tick: u64,
}

enum NpcInteractionKind {
    InteractionOpened,
    InteractionResolved,
    ObjectiveProgressed,
    LootClaimed,
}

struct NpcInteractionEvent {
    npc_id: u64,
    kind: NpcInteractionKind,
    initiator_entity_id: Option<u64>,
    server_tick: u64,
}

struct NpcReplicationBatch {
    batch_tick: u64,
    priority_tier: NpcRuntimeTier,
    deltas: Vec<NpcStateDelta>,
    lifecycle_events: Vec<NpcLifecycleEvent>,
    interaction_events: Vec<NpcInteractionEvent>,
}
```

### 4.1 Sample payload: combat-critical batch

```json
{
  "batch_tick": 812340,
  "priority_tier": "T0CombatCritical",
  "deltas": [
    {
      "npc_id": 99120044,
      "npc_type_id": 41,
      "state": "Engaged",
      "pos_q": [129440, -23360],
      "vel_q": [122, -18],
      "facing_q": 602,
      "anim_state": 7,
      "server_tick": 812340
    }
  ],
  "lifecycle_events": [],
  "interaction_events": []
}
```

### 4.2 Sample payload: interaction resolution

```json
{
  "batch_tick": 812361,
  "priority_tier": "T1LaneCreep",
  "deltas": [],
  "lifecycle_events": [],
  "interaction_events": [
    {
      "npc_id": 4401,
      "kind": "LootClaimed",
      "initiator_entity_id": 7000021,
      "server_tick": 812361
    }
  ]
}
```

---

## 5. Reliability Matrix

| Signal class | Reliability class | Rule |
| :--- | :--- | :--- |
| `NpcLifecycleEvent::Spawned/Despawned/Died/Respawned/StateReset` | Reliable | MUST be delivered/replayed deterministically before dependent deltas |
| `NpcInteractionEvent::InteractionResolved/ObjectiveProgressed/LootClaimed` | Reliable | MUST be delivered/replayed deterministically |
| `NpcStateDelta` continuous movement/animation | Best-effort | MAY drop under pressure; later authoritative deltas reconcile |
| Ring transitions and tier reclassification notices | Reliable | MUST preserve ordering with lifecycle changes |

Deterministic recovery rule:
- If best-effort deltas are missed, subsequent authoritative deltas MUST converge client state without requiring client->edge protocol changes.

---

## 6. Client Smoothing Contract

1. Client MUST interpolate `NpcStateDelta` by default.
2. Client MAY extrapolate for short gaps up to `120 ms`.
3. Snap correction MUST occur when either condition is true:
   - position error exceeds `2.0m`, or
   - no authoritative delta for `> 500 ms` while entity remains relevant.
4. Lifecycle events MUST be ordered before movement deltas at the same or newer `server_tick`.
5. `Died` or `Despawned` lifecycle events MUST immediately invalidate future interpolation on prior trajectories.

---

## 7. Failure Modes and Edge Cases

### 7.1 Arbiter handoff while NPC engaged
- Handoff boundary transition MUST preserve `npc_id`, state continuity, and monotonic `server_tick`.
- Duplicate deltas around handoff window MAY occur; client MUST keep newest-by-tick.

### 7.2 Bursty combat and budget saturation
- Scheduler MUST preserve reliable events and degrade low-priority ambient deltas first.
- Combat-critical tiers MUST retain minimum replication cadence of `8 Hz` in `Near`.

### 7.3 Interaction contention
- Single-winner interactions (loot/objective claim points) MUST produce exactly one `InteractionResolved` winner event.
- Losers MUST receive deterministic reject/result outcome through existing interaction resolution path.

### 7.4 Edge-node reconnection bootstrap
- Reconnected clients MUST receive an authoritative NPC bootstrap snapshot for `Near` ring before resumptive deltas.
- Bootstrap MAY downsample `Mid/Far` initial rings and backfill progressively.

---

## 8. Conformance Checklist

1. Every NPC archetype has exactly one default tier mapping.
2. Tier cadence table defines decision, movement, and replication rates without gaps.
3. Reliable vs best-effort classification is explicit for all replication signal classes.
4. `world.interact_entity` semantics map to interaction outcomes without new intent IDs.
5. No section introduces required new fields for existing client->edge envelopes.
6. Sample payloads validate against documented fields and ordering constraints.

---

## 9. Cross-References

- NPC gameplay taxonomy and semantics: [05. NPC and In-World Interaction Design](../2-gameplay-and-design/05-npc-and-world-interaction-design.md)
- Edge wire and ingress contract: [03. Client <-> Edge Message Contract](03-client-edge-message-contract.md)
- Runtime interfaces companion: [02. Network Interfaces](02-network-interfaces.md)
