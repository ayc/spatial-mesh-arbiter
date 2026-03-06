# SDK Surface Draft (Designer Domains)

This document drafts the designer-facing SDK shape for the game compiler
ecosystem.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative where
used.

## 1. Purpose

1. Define a practical SDK surface that designers can use directly in Lua profile
   authoring.
2. Cover nearly complete MMO RPG, RTS, and MOBA gameplay/business domains
   without exposing engine internals.
3. Keep strict alignment with `docs-core/` determinism, boundedness, and
   durability rules.

## 2. SDK Packaging Model

SDK is organized into namespaced packs:

1. `sdk.shared.*`: pure helpers safe across contexts.
2. `sdk.edge.*`: low-latency validation and admission helpers.
3. `sdk.sim.*`: authoritative simulation helpers (`arbiter` only).
4. `sdk.meta.*`: durable business workflow helpers (`meta` only).
5. `sdk.obs.*`: observability and conformance helpers.

Compiler policy:

1. Every symbol MUST declare allowed contexts.
2. Every symbol MUST declare determinism class (`PURE`, `MUT`, `EMIT`,
   `DURABLE`, `OBS`).
3. Every symbol that can fan out work MUST declare boundedness caps.
4. All calls MUST lower to canonical IR operations prior to emission.

Compatibility note:

1. `01-2-lua-whitelisted-api.md` currently defines the normative v0 callable
   surface using flat symbols (for example `spend_resource`).
2. This document defines the target v1 ergonomic surface using namespaced
   symbols (for example `sdk.sim.resource.spend`).
3. During migration, compiler MAY support both forms as aliases if they lower to
   identical IR and pass the same policy checks.

## 3. Genre-Complete Domain Coverage

This SDK target is near-complete coverage for:

1. MMO RPG
2. RTS
3. MOBA

### 3.1 Cross-Genre Core Domains

| Domain | Primary SDK Packs | Dominant Contexts | MMO RPG | RTS | MOBA |
|---|---|---|---|---|---|
| Intent and admission policy | `sdk.edge.intent`, `sdk.shared.policy` | `edge`, `arbiter` | required | required | required |
| Combat and ability execution | `sdk.sim.combat`, `sdk.sim.ability` | `arbiter` | required | required | required |
| Stats and formula evaluation | `sdk.sim.stats`, `sdk.sim.formula` | `arbiter`, `edge`, `meta` | required | required | required |
| Spells, skills, and talent progression | `sdk.sim.spell`, `sdk.sim.skill`, `sdk.meta.talent` | `arbiter`, `edge`, `meta` | required | required | required |
| Status/effect pipelines | `sdk.sim.status` | `arbiter` | required | required | required |
| Spatial queries and targeting | `sdk.sim.spatial`, `sdk.sim.targeting` | `arbiter`, `edge` | required | required | required |
| AI and deterministic behavior | `sdk.sim.ai`, `sdk.sim.behavior` | `arbiter` | required | required | required |
| NPC/monster/named-unit runtime | `sdk.sim.npc`, `sdk.sim.monster`, `sdk.sim.named_unit` | `arbiter`, `meta` | required | required | required |
| Interactable objects and world props | `sdk.sim.interactable`, `sdk.sim.object_state` | `arbiter`, `edge` | required | required | required |
| Terrain and region semantics | `sdk.sim.terrain`, `sdk.sim.region`, `sdk.sim.nav_policy` | `arbiter`, `edge`, `meta` | required | required | required |
| Crafting and recipe pipelines | `sdk.meta.crafting`, `sdk.meta.recipe`, `sdk.sim.crafting_station` | `meta`, `edge`, `arbiter` | required | required | optional |
| Spawn and lifecycle | `sdk.sim.spawn`, `sdk.meta.lifecycle` | `arbiter`, `meta` | required | required | required |
| Team/party constructs | `sdk.meta.party`, `sdk.sim.party` | `meta`, `arbiter` | required | required | required |
| Raid and large-group orchestration | `sdk.meta.raid`, `sdk.meta.instance`, `sdk.sim.encounter` | `meta`, `edge`, `arbiter` | required | optional | optional |
| PvP matchmaking and rating governance | `sdk.meta.pvp`, `sdk.meta.matchmaking`, `sdk.meta.rank` | `meta`, `edge` | required | required | required |
| Housing and player property | `sdk.meta.housing`, `sdk.sim.housing_instance` | `meta`, `arbiter` | required | optional | optional |
| Session and presence management | `sdk.edge.session`, `sdk.meta.session` | `edge`, `meta` | required | required | required |
| Persistence and savepoint flows | `sdk.meta.persistence`, `sdk.meta.snapshot` | `meta` | required | required | required |
| Administration and operations controls | `sdk.meta.admin`, `sdk.meta.ops` | `meta`, `edge` | required | required | required |
| Ranked/seasons/competitive state | `sdk.meta.rank`, `sdk.meta.season` | `meta` | optional | required | required |
| LiveOps/store/events | `sdk.meta.liveops`, `sdk.meta.store` | `meta` | required | optional | required |
| Messaging/notifications/mailbox | `sdk.meta.notify`, `sdk.meta.message`, `sdk.meta.mailbox` | `meta`, `edge` | required | required | required |
| Moderation/policy enforcement | `sdk.meta.moderation` | `meta` | required | required | required |
| Telemetry/conformance/audit | `sdk.obs.metrics`, `sdk.obs.audit` | all | required | required | required |

### 3.2 MMO RPG Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Character archetypes, classes, talent trees | `sdk.meta.class`, `sdk.meta.talent`, `sdk.sim.loadout` | `meta`, `arbiter` |
| Spellbooks, skills, and loadout specialization | `sdk.sim.spell`, `sdk.sim.skill`, `sdk.meta.talent`, `sdk.meta.loadout` | `arbiter`, `meta` |
| Quests, narrative chapters, objective chains | `sdk.meta.quest`, `sdk.meta.story` | `meta` |
| Open-world zones, dungeons, raid instances | `sdk.meta.instance`, `sdk.sim.encounter` | `meta`, `arbiter` |
| Inventory, equipment, progression gating | `sdk.meta.inventory`, `sdk.sim.equipment`, `sdk.meta.progression` | `meta`, `arbiter` |
| Crafting, gathering, refinement | `sdk.meta.crafting`, `sdk.meta.gathering` | `meta` |
| Player trade, mail, auction house | `sdk.meta.trade`, `sdk.meta.mail`, `sdk.meta.auction` | `meta` |
| Guilds, factions, reputation systems | `sdk.meta.guild`, `sdk.meta.faction`, `sdk.meta.reputation` | `meta` |
| Party finder, role queues, and raid roster governance | `sdk.meta.party`, `sdk.meta.raid`, `sdk.meta.lfg` | `meta`, `edge` |
| NPC factions, monster families, named encounter units | `sdk.sim.npc`, `sdk.sim.monster`, `sdk.sim.named_unit`, `sdk.sim.encounter` | `arbiter`, `meta` |
| Interactable dungeons/world objects | `sdk.sim.interactable`, `sdk.sim.object_state`, `sdk.sim.trigger` | `arbiter` |
| Terrain hazards and zone modifiers | `sdk.sim.terrain`, `sdk.sim.region` | `arbiter`, `meta` |
| Player housing, plot ownership, decoration | `sdk.meta.housing`, `sdk.sim.housing_instance` | `meta`, `arbiter` |
| Mounts, pets, companions | `sdk.meta.mount`, `sdk.meta.pet`, `sdk.sim.companion` | `meta`, `arbiter` |
| World bosses and timed world events | `sdk.meta.world_event`, `sdk.sim.encounter` | `meta`, `arbiter` |
| PvP arenas, battlegrounds, and faction war rules | `sdk.meta.pvp`, `sdk.meta.matchmaking`, `sdk.sim.objective` | `meta`, `arbiter` |

### 3.3 RTS Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Unit templates, squads, role tags | `sdk.sim.unit`, `sdk.sim.squad` | `arbiter` |
| Order queues and command resolution | `sdk.sim.command`, `sdk.sim.queue` | `arbiter` |
| Worker economy, harvesting, logistics | `sdk.sim.harvest`, `sdk.sim.logistics` | `arbiter` |
| Building construction and production queues | `sdk.sim.build`, `sdk.sim.production` | `arbiter` |
| Tech tree and upgrade research | `sdk.sim.tech`, `sdk.meta.tech_unlock` | `arbiter`, `meta` |
| Supply/population and upkeep constraints | `sdk.sim.supply` | `arbiter` |
| Neutral monsters and named map objectives | `sdk.sim.monster`, `sdk.sim.named_unit`, `sdk.sim.objective` | `arbiter` |
| Interactable control points and map props | `sdk.sim.interactable`, `sdk.sim.object_state` | `arbiter` |
| Terrain chokepoints and movement modifiers | `sdk.sim.terrain`, `sdk.sim.nav_policy` | `arbiter` |
| Production recipe chains and queue policy | `sdk.sim.production`, `sdk.meta.recipe`, `sdk.meta.crafting` | `arbiter`, `meta` |
| Fog of war and vision control | `sdk.sim.vision` | `arbiter` |
| Control groups, formations, pathing policy | `sdk.sim.control_group`, `sdk.sim.formation`, `sdk.sim.pathing` | `arbiter` |
| Party lobby handoff and ready-state gating | `sdk.meta.party`, `sdk.meta.matchmaking` | `meta`, `edge` |
| Match win conditions and objective scoring | `sdk.sim.objective`, `sdk.meta.match` | `arbiter`, `meta` |
| Ranked PvP ladder and deserter policy | `sdk.meta.pvp`, `sdk.meta.rank`, `sdk.meta.match_policy` | `meta` |
| Replay, observer, tournament admin | `sdk.meta.replay`, `sdk.meta.tournament` | `meta` |

### 3.4 MOBA Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Hero roster, kits, role constraints | `sdk.meta.hero`, `sdk.sim.hero_kit` | `meta`, `arbiter` |
| Ability skill-order and talent path rules | `sdk.sim.spell`, `sdk.sim.skill`, `sdk.meta.talent` | `arbiter`, `meta` |
| Draft/ban and pre-match lobby rules | `sdk.meta.draft`, `sdk.meta.match` | `meta` |
| Lane state, wave spawning, push logic | `sdk.sim.lane`, `sdk.sim.wave` | `arbiter` |
| Jungle camps and neutral objective control | `sdk.sim.jungle`, `sdk.sim.objective` | `arbiter` |
| Named epic monsters and boss objective rules | `sdk.sim.monster`, `sdk.sim.named_unit`, `sdk.sim.objective` | `arbiter` |
| Interactable map plants/gates/vision props | `sdk.sim.interactable`, `sdk.sim.object_state` | `arbiter` |
| Terrain elevation/brush and path policy | `sdk.sim.terrain`, `sdk.sim.nav_policy` | `arbiter` |
| Tower/inhibitor/base objective lifecycle | `sdk.sim.structure`, `sdk.sim.objective` | `arbiter` |
| Item shop, build paths, consumables | `sdk.meta.shop`, `sdk.sim.item_runtime` | `meta`, `arbiter` |
| Gold/xp, assists, bounty and comeback rules | `sdk.sim.reward`, `sdk.sim.comeback` | `arbiter` |
| Death timers, respawn waves, homeguard gates | `sdk.sim.respawn` | `arbiter` |
| Party queue integrity and role-lock governance | `sdk.meta.party`, `sdk.meta.matchmaking` | `meta`, `edge` |
| AFK/remake/surrender governance | `sdk.meta.match_policy` | `meta` |
| Ranked tiers, splits, seasonal resets | `sdk.meta.rank`, `sdk.meta.season` | `meta` |

### 3.5 Platform and Service Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Session lifecycle and reconnect policy | `sdk.edge.session`, `sdk.meta.session` | `edge`, `meta` |
| Durable profile/world persistence | `sdk.meta.persistence`, `sdk.meta.snapshot` | `meta` |
| Recovery, reconciliation, rollback windows | `sdk.meta.recovery`, `sdk.meta.migration` | `meta` |
| GM tooling and account administration | `sdk.meta.admin`, `sdk.meta.gm` | `meta` |
| Maintenance mode and feature gates | `sdk.meta.ops`, `sdk.meta.feature_gate` | `meta`, `edge` |
| Compliance-grade audit trails | `sdk.meta.audit`, `sdk.obs.audit` | `meta`, all |

### 3.6 Messaging and Communication Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Direct notifications and template messages | `sdk.meta.notify`, `sdk.meta.message` | `meta` |
| System broadcast and channel messaging | `sdk.meta.message`, `sdk.meta.channel` | `meta` |
| Durable mailbox lifecycle and attachments | `sdk.meta.mailbox`, `sdk.meta.mail_attachment` | `meta` |
| Unread/expiry and delivery policy | `sdk.meta.mail_policy`, `sdk.meta.notify` | `meta`, `edge` |

### 3.7 NPC and AI Agent Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| NPC archetypes and spawn-table binding | `sdk.sim.npc`, `sdk.sim.spawn` | `arbiter`, `meta` |
| Monster aggro/threat and leash policies | `sdk.sim.monster`, `sdk.sim.threat`, `sdk.sim.leash` | `arbiter` |
| Named unit identity and scripted phases | `sdk.sim.named_unit`, `sdk.sim.encounter` | `arbiter`, `meta` |
| Deterministic AI utility/state transitions | `sdk.sim.ai`, `sdk.sim.behavior` | `arbiter` |
| Anti-exploit and anti-kite behavior limits | `sdk.sim.leash`, `sdk.sim.policy` | `arbiter` |

### 3.8 World Interaction and Housing Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Interactable object predicates and activation | `sdk.sim.interactable`, `sdk.sim.object_state` | `arbiter`, `edge` |
| Trigger chains and scripted world props | `sdk.sim.trigger`, `sdk.sim.object_state` | `arbiter` |
| Terrain tags, hazards, and movement policy | `sdk.sim.terrain`, `sdk.sim.nav_policy`, `sdk.sim.region` | `arbiter`, `edge`, `meta` |
| Housing ownership and permission model | `sdk.meta.housing`, `sdk.meta.housing_policy` | `meta` |
| Housing placement, budgets, and persistence | `sdk.meta.housing`, `sdk.meta.persistence`, `sdk.sim.housing_instance` | `meta`, `arbiter` |

### 3.9 Crafting and Production Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Recipe registry and requirement checks | `sdk.meta.recipe`, `sdk.meta.crafting` | `meta`, `edge` |
| Craft queue start/cancel/complete lifecycle | `sdk.meta.crafting`, `sdk.meta.queue` | `meta` |
| Station interaction and admission policy | `sdk.sim.crafting_station`, `sdk.edge.intent` | `arbiter`, `edge` |
| Deterministic consume/grant semantics | `sdk.meta.crafting`, `sdk.meta.inventory` | `meta` |
| Batch crafting and anti-duplication controls | `sdk.meta.crafting`, `sdk.meta.txn` | `meta` |

### 3.10 Spell, Skill, and Talent Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Spell cast eligibility and target policy | `sdk.sim.spell`, `sdk.edge.intent` | `arbiter`, `edge` |
| Skill activation and runtime gating | `sdk.sim.skill`, `sdk.sim.resource` | `arbiter` |
| Talent allocation, refund, and respec | `sdk.meta.talent`, `sdk.meta.progression` | `meta` |
| Skill progression and xp grants | `sdk.meta.skill_progression`, `sdk.meta.talent` | `meta` |
| Loadout slots and specialization constraints | `sdk.meta.loadout`, `sdk.sim.skill` | `meta`, `arbiter` |

### 3.11 Party, Raid, and PvP Domains

| Domain | Primary SDK Packs | Dominant Contexts |
|---|---|---|
| Party lifecycle (create/invite/join/leave/disband) | `sdk.meta.party`, `sdk.meta.lfg` | `meta`, `edge` |
| Party role and ready-state policy | `sdk.meta.party`, `sdk.edge.intent` | `meta`, `edge` |
| Raid roster and subgroup assignment | `sdk.meta.raid`, `sdk.meta.instance` | `meta` |
| Raid lockout and checkpoint governance | `sdk.meta.raid`, `sdk.meta.progression`, `sdk.meta.instance` | `meta` |
| PvP queue/join/leave and team assembly | `sdk.meta.pvp`, `sdk.meta.matchmaking` | `meta`, `edge` |
| PvP result reporting, rating updates, and penalties | `sdk.meta.pvp`, `sdk.meta.rank`, `sdk.meta.match_policy` | `meta` |

### 3.12 Domain Boundary Rules

1. Simulation-critical loops MUST remain in `sdk.sim.*` and execute in
   `arbiter`.
2. Economic ownership transfer and long-lived business workflows MUST remain in
   `sdk.meta.*`.
3. `sdk.edge.*` MUST stay pre-authoritative and MUST NOT commit durable state.
4. Cross-domain behavior MUST communicate through intents/events and canonical
   IR, not direct side effects.
5. Each domain pack SHOULD include conformance fixtures for boundedness,
   determinism, and idempotency.
6. world-object state transitions MUST be authoritative in `arbiter`.
7. housing ownership and placement mutations MUST execute in `meta` with
   idempotent durable semantics.
8. crafting consume/grant operations MUST execute atomically in `meta` with
   idempotency keys.
9. talent allocation and skill progression writes MUST execute in `meta` with
   idempotent durable semantics.
10. party membership, leadership, and role assignments MUST execute in `meta`
    with idempotent durable semantics.
11. raid roster/lockout/checkpoint mutations MUST execute in `meta`; arbiter
    MAY only consume versioned snapshots for encounter policy.
12. pvp queue state, match result, and rating mutations MUST execute in `meta`
    and MUST NOT be committed directly from `arbiter` rules.

## 4. Core Pack Sketch

## 4.1 `sdk.shared`

Representative concepts:

1. canonical numeric helpers (`fixed`, clamp, deterministic rounding)
2. deterministic collection helpers (bounded list/map transforms)
3. stable code and policy enums (reject codes, reason codes)

Example calls:

```lua
local mana_cost = sdk.shared.num.fixed("30.0")
local capped = sdk.shared.num.clamp_fixed(mana_cost, sdk.shared.num.fixed("0.0"), sdk.shared.num.fixed("1000.0"))
```

## 4.2 `sdk.edge`

Representative concepts:

1. input schema checks
2. rate/fairness prechecks
3. cheap target validity predicates

Example calls:

```lua
sdk.edge.intent.require_payload_shape(ctx, "ability.cast_targeted.v1")
sdk.edge.intent.require_not_rate_limited(ctx.actor_id, "ability.cast")
```

## 4.3 `sdk.sim`

Representative concepts:

1. combat, status, resource, cooldown, targeting
2. deterministic combat-stat and formula evaluation
3. deterministic spell and skill runtime helpers
4. deterministic NPC/state-machine helpers
5. interactable object and terrain policy helpers
6. spawn/despawn with explicit caps
7. party/raid/pvp policy reads for deterministic combat governance

Example calls:

```lua
sdk.sim.resource.spend(ctx.caster, "mana", sdk.shared.num.fixed("30.0"))
sdk.sim.spawn.entity("projectile.fireball_basic", ctx.caster, ctx.target)
local dmg = sdk.sim.formula.eval("formula.fireball_damage.v1", {
  power = sdk.sim.stats.effective(ctx.caster, "spell_power"),
  resistance = sdk.sim.stats.effective(ctx.target, "fire_resist"),
  coeff = sdk.shared.num.fixed("1.25")
})
sdk.sim.combat.apply_damage(ctx.caster, ctx.target, dmg, "fire")
sdk.sim.spell.cast(ctx.caster, "spell.fireball.v2", ctx.target, "default")
sdk.sim.skill.activate(ctx.caster, "skill.blink.v1", ctx.target)
sdk.sim.ai.set_state(ctx.npc_id, "combat.engage")
sdk.sim.ai.set_target(ctx.npc_id, ctx.target)
sdk.sim.interactable.activate(ctx.actor_id, ctx.object_id, "use")
```

### 4.3.1 Combat, Stat, and Formula Contract

1. formulas MUST be declared in a deterministic formula registry (no dynamic eval).
2. formula evaluation MUST be pure and bounded (no hidden loops or recursion).
3. final combat values MUST apply canonical rounding/clamp policy before mutation.
4. derived stats MUST be reproducible from base stats plus ordered modifier sets.
5. formula ids SHOULD be versioned (`formula.<name>.vN`) for safe rollout.

### 4.3.2 NPC, Monster, and Named Unit AI Contract

1. AI transitions MUST be deterministic for identical inputs and tick order.
2. AI decision surfaces MUST be bounded by explicit per-tick transition caps.
3. named-unit behavior phases SHOULD be explicit state machines with stable ids.
4. aggro/leash behavior MUST be policy-driven and replay-stable.
5. AI helpers MUST NOT perform blocking I/O or external calls.

### 4.3.3 Interactable Object and Terrain Contract

1. interactable activations MUST be permission-checked and deterministic.
2. object state transitions MUST be explicit and replay-safe (`LOCKED -> OPEN`).
3. terrain policy queries MUST be bounded per rule evaluation.
4. terrain modifiers that influence combat/movement MUST normalize numeric
   effects via canonical fixed-point rules.
5. trigger-chain fan-out MUST be bounded by profile limits.

### 4.3.4 Spell, Skill, and Talent Runtime Contract

1. spell cast admission MUST be deterministic and policy-checked.
2. spell and skill effect fan-out MUST respect explicit per-cast budgets.
3. skill activation MUST obey cooldown/resource and target legality policy.
4. runtime talent effects MUST be sourced from explicit versioned talent state.
5. spell/skill helpers MUST NOT perform durable progression writes directly.

### 4.3.5 Party, Raid, and PvP Runtime Contract

1. arbiter reads of party, raid, and team state MUST use tick-stable snapshots.
2. raid-size or subgroup-based encounter scaling MUST be deterministic and
   bounded.
3. pvp hostility/friendly-fire policies MUST be deterministic for identical
   inputs.
4. runtime helpers MAY validate readiness/eligibility but MUST NOT commit party,
   raid, or rating mutations.
5. arbiter-side match progression events SHOULD emit durable intents for `meta`
   settlement.

## 4.4 `sdk.meta`

Representative concepts:

1. durable transactions and idempotent emits
2. inventory/economy/progression workflows
3. social/liveops/business systems
4. session/persistence/admin operations
5. housing ownership and placement workflows
6. crafting and recipe workflows
7. spell/skill/talent progression workflows
8. party/raid/pvp social and competitive workflows

Example calls:

```lua
local tx = sdk.meta.txn.begin("reward_grant", ctx.command_id)
sdk.meta.inventory.grant_item(ctx.player_id, "item.health_potion", 3)
sdk.meta.txn.confirm(tx)
sdk.meta.session.renew(ctx.player_id, ctx.session_id)
sdk.meta.persistence.enqueue_profile_save(ctx.player_id, ctx.session_id)
sdk.meta.housing.place_item(ctx.player_id, ctx.plot_id, ctx.item_id, ctx.transform, ctx.command_id)
sdk.meta.crafting.execute(ctx.player_id, "recipe.iron_sword.v1", 1, ctx.station_id, ctx.command_id)
sdk.meta.talent.allocate(ctx.player_id, "talent.pyromancy.rank_2", ctx.command_id)
sdk.meta.party.invite(ctx.party_id, ctx.leader_id, ctx.target_id, ctx.command_id)
sdk.meta.raid.assign_subgroup(ctx.raid_id, ctx.member_id, 2, ctx.command_id)
sdk.meta.pvp.queue_join(ctx.player_id, "arena_3v3", ctx.command_id)
```

### 4.4.1 Messaging, Notifications, and Mailbox

1. all mailbox mutation calls MUST be `meta` only.
2. notification and mailbox sends SHOULD use idempotency keys.
3. mailbox attachments MUST be bounded by explicit profile caps.
4. expiry and unread behavior SHOULD be explicit and policy-driven.

Example calls:

```lua
sdk.meta.notify.send(ctx.player_id, "quest.complete", { quest_id = ctx.quest_id }, ctx.command_id)
sdk.meta.mailbox.send({
  to_player_id = ctx.player_id,
  subject_key = "reward.title",
  body_key = "reward.body",
  attachments = ctx.attachments,
  expires_at_ms = ctx.expires_at_ms,
  idempotency_key = ctx.command_id
})
```

### 4.4.2 Housing Contract

1. housing ownership/permission writes MUST be `meta` only.
2. placement/removal operations MUST enforce explicit per-plot budgets.
3. placement operations MUST include idempotency keys for retry safety.
4. housing persistence snapshots MUST be versioned and migration-safe.
5. arbiter-side housing interactions MAY read instance state but MUST NOT commit
   ownership transfers.

### 4.4.3 Crafting Contract

1. crafting consume/grant operations MUST be atomic and idempotent.
2. recipe definitions MUST be deterministic and versioned (`recipe.<name>.vN`).
3. ingredient and output entry counts MUST obey explicit profile caps.
4. queue operations MUST be bounded per rule evaluation.
5. arbiter MAY validate station interaction but MUST NOT directly commit durable
   inventory ownership changes.

### 4.4.4 Spell, Skill, and Talent Progression Contract

1. talent allocation/refund operations MUST be idempotent and version-safe.
2. skill xp and level progression writes MUST execute in `meta` only.
3. respec workflows MUST be explicit transactions with compensation semantics.
4. loadout constraint violations MUST fail closed with stable reject codes.
5. arbiter spell/skill activation MAY read progression state but MUST NOT commit
   progression mutations directly.

### 4.4.5 Party, Raid, and PvP Contract

1. party invite/join/leave/kick/disband operations MUST be idempotent and
   version-safe.
2. raid roster, subgroup, and lockout mutations MUST execute in `meta` with
   explicit transaction boundaries.
3. pvp queue admission and team assembly MUST enforce deterministic policy with
   stable reject codes.
4. pvp result settlement and rating updates MUST be idempotent and
   duplicate-safe.
5. deserter penalties and cooldown application MUST be durable `meta`
   operations; arbiter MAY only emit supporting events.

## 4.5 `sdk.obs`

Representative concepts:

1. structured reject and outcome records
2. boundedness budget events
3. conformance evidence markers

Example calls:

```lua
sdk.obs.metrics.count("intent.reject.OUT_OF_RANGE", 1)
sdk.obs.audit.emit_policy_event("auction.listing_settlement", "confirmed")
```

## 5. Auction House Domain (First-Class)

Auction house is in scope and SHOULD be a first-class `sdk.meta.auction` pack.

Required subdomains:

1. listing lifecycle:
   1. create
   2. update price (if allowed)
   3. cancel
   4. expire
2. bid and buyout:
   1. submit bid
   2. submit buyout
   3. conflict resolution rules
3. escrow and reservation:
   1. reserve seller item
   2. reserve buyer currency
   3. release reservations on cancel/fail
4. settlement:
   1. transfer ownership
   2. apply marketplace fee and taxes
   3. deliver proceeds and receipts
5. abuse controls:
   1. duplicate command protection
   2. idempotent retries
   3. anti-self-trade and policy checks

Representative API shape:

```lua
local listing_id = sdk.meta.auction.create_listing({
  seller_id = ctx.player_id,
  item_ref = ctx.item_ref,
  stack_qty = 1,
  currency_id = "gold",
  start_price = 1200,
  buyout_price = 2200,
  duration_sec = 86400,
  idempotency_key = ctx.command_id
})

sdk.meta.auction.submit_buyout({
  buyer_id = ctx.buyer_id,
  listing_id = listing_id,
  idempotency_key = ctx.command_id
})
```

Safety requirements:

1. auction settlement MUST be `meta` only.
2. auction APIs MUST require idempotency keys on every mutation-capable call.
3. arbiter rules MAY only emit auction intents/events; they MUST NOT settle
   listings directly.
4. all listing transitions MUST be modeled as explicit state transitions:
   `ACTIVE -> RESERVED -> SOLD | CANCELLED | EXPIRED`.

## 6. Versioning and Rollout Policy

1. SDK packs MUST be versioned independently (`sdk.meta.auction@v1`, etc.).
2. Symbol additions are backward-compatible.
3. Signature or behavior changes are breaking and MUST require profile/version
   bump.
4. Compiler SHOULD support dual-pack validation for migration windows.
5. Persistence schema changes MUST define migration and rollback behavior before
   rollout.

## 7. Suggested Milestones

Phase 1 (foundational):

1. `sdk.shared`, `sdk.edge.intent`, `sdk.sim.resource`, `sdk.sim.combat`,
   `sdk.sim.status`, `sdk.edge.session`, `sdk.obs.metrics`

Phase 2 (MMO RPG core):

1. `sdk.meta.inventory`, `sdk.meta.economy`, `sdk.meta.quest`,
   `sdk.meta.progression`, `sdk.meta.trade`, `sdk.meta.instance`,
   `sdk.meta.session`, `sdk.meta.persistence`, `sdk.sim.npc`,
   `sdk.sim.monster`, `sdk.sim.named_unit`, `sdk.sim.ai`,
   `sdk.sim.interactable`, `sdk.sim.terrain`, `sdk.meta.recipe`,
   `sdk.meta.crafting`, `sdk.sim.spell`, `sdk.sim.skill`,
   `sdk.meta.talent`, `sdk.meta.loadout`

Phase 3 (marketplace and social):

1. `sdk.meta.auction`, `sdk.meta.guild`, `sdk.meta.party`,
   `sdk.meta.raid`, `sdk.meta.pvp`, `sdk.meta.matchmaking`,
   `sdk.meta.leaderboard`, `sdk.meta.season`, `sdk.meta.liveops`,
   `sdk.meta.mail`, `sdk.meta.reputation`, `sdk.meta.housing`

Phase 4 (RTS gameplay packs):

1. `sdk.sim.unit`, `sdk.sim.command`, `sdk.sim.build`, `sdk.sim.tech`,
   `sdk.sim.vision`, `sdk.sim.formation`, `sdk.meta.replay`

Phase 5 (MOBA gameplay packs):

1. `sdk.meta.draft`, `sdk.sim.hero_kit`, `sdk.sim.lane`, `sdk.sim.wave`,
   `sdk.sim.jungle`, `sdk.sim.structure`, `sdk.meta.shop`, `sdk.sim.respawn`

Phase 6 (operations and trust):

1. `sdk.meta.moderation`, `sdk.meta.notify`, `sdk.meta.match_policy`,
   `sdk.meta.admin`, `sdk.meta.ops`, advanced conformance/audit packs
