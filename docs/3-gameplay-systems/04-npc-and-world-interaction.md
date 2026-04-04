# NPC and In-World Interaction Design

This document is the canonical gameplay/design specification for NPC behavior taxonomy and in-world interaction semantics.

Canonical split:
- Gameplay/design semantics are canonical here.
- Runtime cadence, replication, interest management, and client smoothing are canonical in [NPC Runtime and Replication Contract](../1-architecture/02-npc-architecture.md).
- Wire envelopes and session/auth behavior remain canonical in [Client-Edge Wire Protocol](../2-contracts-and-interfaces/01-client-edge-wire-protocol.md).

This document is normative. Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used in RFC-style.

---

## 1. Scope

### In scope
- Full NPC world set:
  - combat: lane creeps, neutral monsters, boss encounters, summoned combat entities,
  - social: vendor/quest/dialogue-capable NPCs (taxonomy-level in this phase),
  - ambient: wildlife/background entities,
  - scripted/cinematic actors.
- In-world interaction systems:
  - loot interactables,
  - objective/shrine/world-trigger interactables,
  - generic entity interaction via `world.interact_entity` (`intent_id=0114`).

### Out of scope
- New intent IDs or wire message shape changes in this phase.
- Dialogue tree schema and quest graph internals.
- Meta-service internal RPC/event schema.

---

## 2. NPC Taxonomy (Normative)

| npc_archetype | intelligence_tier | purpose | allowed_states | default_threat_model | despawn/cleanup semantics | interaction eligibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `LaneCreep` | Arbiter-Local | deterministic lane pressure and objective pacing | `Idle`, `Patrol/March`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Dead/Corpse`, `Despawned` | nearest valid hostile in lane corridor; objective-first fallback | despawn on death timer expiry or wave cleanup | interactable only in combat semantics (attack/cast), not service interaction |
| `NeutralMonster` | Arbiter-Local | PvE combat and area denial/reward loop | `Idle`, `Patrol/March`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Dead/Corpse`, `Despawned` | aggro radius + threat refresh from recent damage/heal aggro rules | corpse persists for loot visibility window, then cleanup | direct entity interaction allowed only where content explicitly marks interactable |
| `BossEncounter` | AI Node | scripted high-importance encounter behavior | `Idle`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Dead/Corpse`, `Despawned`, `ScriptedControl` | scripted phase targets + threat table tie-breakers | corpse and reward handoff MUST follow boss loot policy | entity interaction may be phase-gated (for example objective phase triggers) |
| `SummonedCombat` | Arbiter-Local | temporary combat utility entity from player/NPC action | `Idle`, `Patrol/March`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Despawned` | owner-assist first, hostile proximity second | hard despawn on owner loss/timeout/phase end | no service interaction; combat and script flags only |
| `SocialServiceNPC` | AI Node | vendor/quest/dialogue service anchor | `Idle`, `ConversationLocked`, `ServiceOpen`, `Unavailable` | non-combat by default | persistent unless world script disables | always entity-interactable when `ServiceOpen` or allowed `Idle` |
| `AmbientFauna` | Arbiter-Local | world ambience and soft activity cues | `Idle`, `Patrol/March`, `Evade/Leash`, `Despawned` | avoid-threat bias; no proactive aggro by default | despawn by streaming budget or biome policy | typically non-interactable unless explicitly tagged |
| `ScriptedActor` | AI Node / Arbiter-Local | cinematic or event-driven world actor | `ScriptedControl`, `Interactive`, `CinematicLocked`, `Despawned` | script-defined | lifecycle controlled by event script | interaction only in `Interactive` state |

---

## 3. Behavior State Models (Normative)

### 3.1 Common combat-capable states

Common finite state set for combat-capable archetypes:
- `Idle`
- `Patrol/March`
- `AcquireTarget`
- `Engaged`
- `Evade/Leash`
- `Dead/Corpse`
- `Despawned`

Required transition triggers:
1. `Idle -> Patrol/March` when schedule/wave route exists.
2. `Patrol/March -> AcquireTarget` when valid hostile enters aggro/visibility policy.
3. `AcquireTarget -> Engaged` when path/range resolution succeeds.
4. `Engaged -> Evade/Leash` when target invalidates or leash boundary breaks.
5. `Evade/Leash -> Patrol/March` or `Idle` on leash completion.
6. `Engaged -> Dead/Corpse` on zero-health terminal event.
7. `Dead/Corpse -> Despawned` on cleanup timer or script directive.

### 3.2 Social variants

Social finite states:
- `Idle`
- `ConversationLocked`
- `ServiceOpen`
- `Unavailable`

Required triggers:
1. `Idle -> ConversationLocked` when a client acquires an interaction lock.
2. `ConversationLocked -> ServiceOpen` when preconditions pass.
3. `ServiceOpen -> Idle` on completion, timeout, or explicit close.
4. Any state -> `Unavailable` when world script disables service.

### 3.3 Scripted variants

Scripted finite states:
- `ScriptedControl`
- `Interactive`
- `CinematicLocked`

Required triggers:
1. `ScriptedControl -> Interactive` only on script checkpoint release.
2. `Interactive -> CinematicLocked` when scripted cinematic ownership begins.
3. `CinematicLocked -> Interactive` only after cinematic completion event.

### 3.4 Threat, Aggro, and Leash Mechanics

Combat-capable NPCs that use threat tables MUST apply the following deterministic model.

#### Threat generation

Threat generated by an action is:

```
threat_generated = (value × threat_multiplier) + flat_threat
```

| Source | `threat_multiplier` | `flat_threat` | Notes |
| :--- | :---: | :---: | :--- |
| Direct damage | `1.0` | `0` | Base rule: one threat per one damage dealt |
| Healing on an ally already in combat | `0.5` | `0` | Split across enemies currently in combat with the healed ally |
| Taunt ability | `0.0` | `current_top_threat × 1.1` | Forces a swap by setting the taunter above the current leader |
| AoE damage | `1.0` per target | `0` | Full threat against each valid target hit |
| Crowd-control application | `0.0` | `100` | Flat threat for applying CC |
| Buff on ally in combat | `0.25` | `0` | Low threat, split across enemies currently in combat |
| Resurrection | `0.0` | `500` | High flat threat for reviving in combat |

Game-authored modifiers MAY scale `threat_multiplier` per source (for example tank stance,
stealth threat reduction, or boss-specific rules).

#### Threat decay and swap thresholds

| Mode | Rule |
| :--- | :--- |
| In combat | No passive decay while any threat-table source remains within aggro range |
| Out of combat | Full threat reset when all sources leave aggro range or die |
| Death | Dead entities are removed from the threat table immediately |
| Out-of-range bleed | Alive targets beyond aggro range lose `5%` threat per tick until they re-enter or drop to zero |

NPCs MUST NOT swap targets on every tiny threat lead. Challenger evaluation uses:

```
swap_required = current_target_threat × (1.0 + swap_threshold_pct)
```

| NPC type | `swap_threshold_pct` |
| :--- | :---: |
| Standard monster | `10%` |
| Boss / elite | `20%` |
| Add / minion | `0%` |

If `challenger_threat > swap_required`, the NPC swaps. Otherwise it stays on its current target.
The comparison happens at the NPC's normal decision cadence, not continuously between decision
ticks.

#### Leash behavior

Leash anchor is the NPC's spawn point or current patrol waypoint. Default leash parameters are:

- `max_range = 40.0`
- `return_speed_multiplier = 2.0`
- `arrival_tolerance = 1.0`

When an NPC exceeds `max_range` from its leash anchor:

1. It enters `Evade/Leash`.
2. It becomes untargetable and immune to further combat processing.
3. It moves back toward the anchor at `move_speed × return_speed_multiplier`.
4. Its threat table is cleared immediately.
5. On reaching the anchor within `arrival_tolerance`, it returns to `Idle`, resets HP to max,
   and removes active status effects.

Kinematic dilation scales the NPC's return speed but does not alter the leash distance check
itself.

---

## 4. In-World Interaction Semantics (Normative)

### 4.1 Interaction classes

- `LootInteractable`: claimable drop or reward token in world space.
- `ObjectiveInteractable`: shrine/objective/world trigger that advances encounter state.
- `EntityInteractable`: generic service/entity interaction through `world.interact_entity`.

`world.interact_entity` (`intent_id=0114`) MUST be the canonical ingress intent for these interaction classes in this phase.

### 4.2 Validation gates (strict order)

Interaction validation MUST execute in this order:
1. session/auth validity,
2. range and LOS (if the class requires LOS),
3. target state is currently interactable,
4. ownership/party/quest constraints,
5. contention lock (single-winner where applicable),
6. cooldown/rate-limit gates.

If a gate fails, downstream gates MUST NOT execute for that request.

### 4.3 Outcomes

Standard outcomes:
- `Accepted`
- `RejectedOutOfRange`
- `RejectedInvalidState`
- `RejectedContended`
- `RejectedUnauthorized`
- `RejectedRateLimited`
- `RejectedServerBusy`

### 4.4 Client retry guidance

| Outcome | Client behavior |
| :--- | :--- |
| `Accepted` | proceed with optimistic UI transition and await authoritative world/result updates |
| `RejectedOutOfRange` | do-not-retry until position/LOS changes |
| `RejectedInvalidState` | do-not-retry until target state changes |
| `RejectedContended` | retry-later with short jittered backoff |
| `RejectedUnauthorized` | do-not-retry unless account/party/quest state changes |
| `RejectedRateLimited` | retry-later using backoff policy |
| `RejectedServerBusy` | retry-later with backoff and priority downgrade |

### 4.5 Deterministic Contention Lock Algorithm

Single-winner interactions such as loot claims, objective captures, and gather nodes MUST resolve
through a per-Arbiter contention lock. There is no distributed lock across Arbiters; cross-boundary
interaction proposals relay to the owning Arbiter and are resolved there.

The winner rule is:

1. Earliest admitted attempt wins.
2. Same-tick ties break by lowest `EntityID`.
3. Once a lock is held, later contenders receive `RejectedContended` until the lock expires or is
   explicitly released.

This yields a deterministic total order because generational `EntityID`s have a stable ordering
within one replay.

#### Lock duration by interaction class

| Interaction | Lock duration | Notes |
| :--- | :--- | :--- |
| Loot pickup | `1 tick` | Instant claim path |
| NPC interaction (vendor, quest, service) | no contention lock | Concurrent access allowed unless content adds a separate conversation lock |
| Objective capture | channel duration | Released on interruption, death, or completion |
| Resource node / gather | gather duration | Released on interruption, death, or completion |

#### Party loot interaction

| Mode | Uses contention lock? | Resolution |
| :--- | :---: | :--- |
| `FreeForAll` | Yes | First admitted claimant wins |
| `NeedGreed` | No | Party-locked entity; Meta resolves roll/vote and grants through recovery/loot flow |
| `MasterLoot` | No | Party leader or designated master resolves recipient through Meta |

---

## 5. Design Rules

1. NPC responsiveness MUST match archetype class:
   - `BossEncounter` and `NeutralMonster` in combat SHOULD feel responsive within combat-grade cadence.
   - `LaneCreep` SHOULD feel steady and deterministic rather than twitch-reactive.
   - `AmbientFauna` MAY be visibly lower-frequency without fairness impact.
2. Contention outcomes MUST be deterministic and single-winner where required (loot/objective claim points).
3. Internal-only server actions MUST NEVER appear as player-visible interaction options.
4. Interaction affordances SHOULD clearly communicate availability, lock status, and failure reason class.

---

## 6. Cross-References

- Intent taxonomy and `intent_id=0114`: [Intent Taxonomy](../2-contracts-and-interfaces/02-intent-taxonomy.md)
- Runtime cadence/replication contract: [NPC Runtime and Replication Contract](../1-architecture/02-npc-architecture.md)
- Wire ingress envelope/auth semantics: [Client-Edge Wire Protocol](../2-contracts-and-interfaces/01-client-edge-wire-protocol.md)
