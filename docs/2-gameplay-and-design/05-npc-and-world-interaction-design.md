# NPC and In-World Interaction Design

This document is the canonical gameplay/design specification for NPC behavior taxonomy and in-world interaction semantics.

Canonical split:
- Gameplay/design semantics are canonical here.
- Runtime cadence, replication, interest management, and client smoothing are canonical in [04. NPC Runtime and Replication Contract](../1-architecture-and-engine/04-npc-runtime-and-replication-contract.md).
- Wire envelopes and session/auth behavior remain canonical in [03. Client <-> Edge Message Contract](../1-architecture-and-engine/03-client-edge-message-contract.md).

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

| npc_archetype | purpose | allowed_states | default_threat_model | despawn/cleanup semantics | interaction eligibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `LaneCreep` | deterministic lane pressure and objective pacing | `Idle`, `Patrol/March`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Dead/Corpse`, `Despawned` | nearest valid hostile in lane corridor; objective-first fallback | despawn on death timer expiry or wave cleanup | interactable only in combat semantics (attack/cast), not service interaction |
| `NeutralMonster` | PvE combat and area denial/reward loop | `Idle`, `Patrol/March`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Dead/Corpse`, `Despawned` | aggro radius + threat refresh from recent damage/heal aggro rules | corpse persists for loot visibility window, then cleanup | direct entity interaction allowed only where content explicitly marks interactable |
| `BossEncounter` | scripted high-importance encounter behavior | `Idle`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Dead/Corpse`, `Despawned`, `ScriptedControl` | scripted phase targets + threat table tie-breakers | corpse and reward handoff MUST follow boss loot policy | entity interaction may be phase-gated (for example objective phase triggers) |
| `SummonedCombat` | temporary combat utility entity from player/NPC action | `Idle`, `Patrol/March`, `AcquireTarget`, `Engaged`, `Evade/Leash`, `Despawned` | owner-assist first, hostile proximity second | hard despawn on owner loss/timeout/phase end | no service interaction; combat and script flags only |
| `SocialServiceNPC` | vendor/quest/dialogue service anchor | `Idle`, `ConversationLocked`, `ServiceOpen`, `Unavailable` | non-combat by default | persistent unless world script disables | always entity-interactable when `ServiceOpen` or allowed `Idle` |
| `AmbientFauna` | world ambience and soft activity cues | `Idle`, `Patrol/March`, `Evade/Leash`, `Despawned` | avoid-threat bias; no proactive aggro by default | despawn by streaming budget or biome policy | typically non-interactable unless explicitly tagged |
| `ScriptedActor` | cinematic or event-driven world actor | `ScriptedControl`, `Interactive`, `CinematicLocked`, `Despawned` | script-defined | lifecycle controlled by event script | interaction only in `Interactive` state |

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

- Intent taxonomy and `intent_id=0114`: [04. Intent Taxonomy & ID Registry](04-intent-taxonomy-and-registry.md)
- Runtime cadence/replication contract: [04. NPC Runtime and Replication Contract](../1-architecture-and-engine/04-npc-runtime-and-replication-contract.md)
- Wire ingress envelope/auth semantics: [03. Client <-> Edge Message Contract](../1-architecture-and-engine/03-client-edge-message-contract.md)
