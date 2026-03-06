# SDK Catalog Wishlist (v0)

This document lists desired standard-library concepts for the game compiler
ecosystem.

Goal: give designers reusable, safe building blocks while preserving `docs-core/`
runtime contracts.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative where used.

## 1. Catalog Principles

1. Modules SHOULD be declarative and composable.
2. Authoritative-path modules MUST be deterministic and bounded.
3. Every API concept MUST declare allowed execution contexts (`edge`, `arbiter`, `meta`).
4. Module behavior MUST compile through adapter and messaging contracts in `docs-core/`.

## 2. Core Runtime-Safe Concepts

### 2.1 Intent and Validation

1. intent registry helpers
2. input schema validators
3. target filters and permission predicates
4. reject-code policy helpers

Preferred contexts:

1. `edge`
2. `arbiter`

### 2.2 Resource and Cooldown

1. resource pools (`mana`, `energy`, custom bars)
2. spend/refund primitives
3. cooldown timers
4. shared cooldown groups

Preferred contexts:

1. `arbiter`

### 2.3 Effects and Status

1. status effect application/removal
2. duration/pulse timers
3. stacking/refresh policies
4. immunity and cleansing helpers

Preferred contexts:

1. `arbiter`

### 2.4 Damage and Mitigation

1. damage packet construction
2. mitigation pipeline stages
3. resist/armor formulas
4. critical/conditional modifiers

Preferred contexts:

1. `arbiter`

### 2.5 Spatial Queries

1. distance/range predicates
2. area shape selectors
3. target-collection filters

Preferred contexts:

1. `arbiter`

### 2.6 Spawn and Lifecycle

1. spawn request helpers
2. despawn/finalize rules
3. ownership-safe transfer markers

Preferred contexts:

1. `arbiter`
2. `meta` (for lifecycle orchestration references)

### 2.7 Combat Stats and Formula Engine

1. stat query helpers (`base`, `derived`, `effective`)
2. deterministic formula registry helpers
3. damage/heal formula composition helpers
4. mitigation and penetration formula helpers
5. clamp/rounding policy helpers for final values

Preferred contexts:

1. `arbiter`
2. `edge` (preview/validation only)
3. `meta` (progression-side stat derivation)

### 2.8 NPC, Monster, Named Unit, and AI Runtime

1. npc/monster archetype query helpers
2. named-unit identity and encounter-role helpers
3. aggro/threat and target-priority helpers
4. deterministic AI state transition helpers
5. leash/territory and behavior policy helpers

Preferred contexts:

1. `arbiter`
2. `meta` (authoring and live config of AI policies)

### 2.9 Interactable Objects and World Props

1. interactability and permission predicates
2. object state transition helpers (locked/open/active/cooldown)
3. trigger/switch and scripted object chain helpers
4. lootable and one-shot object policy helpers

Preferred contexts:

1. `arbiter`
2. `edge` (precheck and preview only)

### 2.10 Terrain, Regions, and Navigation Policy

1. terrain tag query helpers (`water`, `lava`, `slow`, `highground`)
2. region/zone identity and policy helpers
3. movement penalty/bonus lookup helpers
4. deterministic terrain effect application helpers

Preferred contexts:

1. `arbiter`
2. `edge` (admission and hint checks)
3. `meta` (world configuration/policy authoring)

### 2.11 Spells, Skills, and Talent Systems

1. spell cast eligibility and target-policy helpers
2. deterministic spell effect composition helpers
3. skill activation and cooldown integration helpers
4. skill progression/xp grant helpers
5. talent unlock/allocate/refund helpers
6. loadout and specialization constraint helpers

Preferred contexts:

1. `arbiter` (cast/activate simulation)
2. `edge` (cast preview and eligibility checks)
3. `meta` (skill/talent progression and respec workflows)

## 3. Durability and Meta Concepts

### 3.1 Durable Event Helpers

1. hard-event emit wrappers
2. idempotency key helpers
3. compensation signal helpers

Preferred contexts:

1. `arbiter`
2. `meta`

### 3.2 Transaction and Reconciliation Helpers

1. pending/confirmed/compensated state helpers
2. late-ack classification helpers
3. duplicate-command safe handlers

Preferred contexts:

1. `meta`

### 3.3 Progression and Economy Primitives

1. inventory mutation DSL
2. currency transfer DSL
3. reward grant helpers
4. progression checkpoint helpers

Preferred contexts:

1. `meta`
2. `arbiter` (emit-only or intent-side semantics)

### 3.4 Auction House and Marketplace

1. listing create/cancel helpers
2. bid and buyout submission helpers
3. escrow and reservation helpers
4. settlement and fee distribution helpers
5. listing expiry and relist helpers
6. anti-duplication and idempotency guards

Preferred contexts:

1. `meta`
2. `arbiter` (event emission only; no direct settlement mutation)

### 3.5 Session and State Management

1. session start/renew/end helpers
2. presence and reconnect helpers
3. shard/world transfer markers
4. conflict-safe state token helpers

Preferred contexts:

1. `edge` (admission and reconnect screening)
2. `meta` (durable session lifecycle)

### 3.6 Persistence and Recovery

1. profile persistence helpers
2. inventory/economy snapshot helpers
3. savepoint/checkpoint helpers
4. restore and reconciliation helpers

Preferred contexts:

1. `meta`
2. `arbiter` (emit-only checkpoint intents/events)

### 3.7 Administration and Operations

1. GM action helpers (grant/revoke/move/unstick)
2. safe account penalty helpers
3. maintenance-mode policy helpers
4. feature gate and kill-switch helpers
5. audit trail emit helpers

Preferred contexts:

1. `meta`
2. `edge` (maintenance admission policy checks)

### 3.8 Messaging, Notifications, and Mailbox

1. direct notification emit helpers
2. broadcast/system announcement helpers
3. mailbox send/claim/delete helpers
4. attachment-safe delivery helpers
5. unread-state and expiry helpers

Preferred contexts:

1. `meta`
2. `edge` (read-only preview and policy checks)

### 3.9 Housing and Player Property

1. plot ownership and permission helpers
2. housing item placement/removal helpers
3. placement budget and collision-policy helpers
4. visit/access policy helpers
5. housing persistence snapshot helpers

Preferred contexts:

1. `meta`
2. `arbiter` (instance-side interaction only; no ownership transfer mutation)

### 3.10 Crafting and Production Pipelines

1. recipe eligibility and input-check helpers
2. deterministic ingredient consume/output grant helpers
3. crafting queue start/cancel/complete helpers
4. station and permission policy helpers
5. anti-duplication/idempotent crafting command helpers

Preferred contexts:

1. `meta`
2. `edge` (preview and validation only)
3. `arbiter` (station interaction and intent emission only)

### 3.11 Party and Group Mechanics

1. party create/disband/invite/join/leave helpers
2. leader assignment and role policy helpers
3. ready-check and queue-readiness helpers
4. loot mode and distribution policy helpers
5. anti-abuse membership and invite-rate guards

Preferred contexts:

1. `meta`
2. `edge` (invite and queue-readiness prechecks)
3. `arbiter` (read-only party state for sim policy)

### 3.12 Raid and Instance Orchestration

1. raid roster and subgroup assignment helpers
2. raid lockout/eligibility helpers
3. encounter gate and checkpoint helpers
4. instance reservation/open/close helpers
5. deterministic phase-token and wipe/restart helpers

Preferred contexts:

1. `meta`
2. `edge` (eligibility/lobby prechecks)
3. `arbiter` (read-only encounter policy state)

### 3.13 PvP, Matchmaking, and Competitive Governance

1. queue join/leave and queue policy helpers
2. team assembly and role-balance helpers
3. match admission and anti-smurf policy helpers
4. result submission and rating/MMR update helpers
5. deserter penalty and cooldown helpers

Preferred contexts:

1. `meta`
2. `edge` (queue/admission prechecks)
3. `arbiter` (read-only match policy and team state)

## 4. AI and State Machine Concepts

1. finite-state machine definition helpers
2. transition predicates
3. cooldown-gated transitions
4. deterministic action selection policies

Preferred contexts:

1. `arbiter`
2. `edge` (screening/prediction-adjacent checks only)

## 5. Observability and Conformance Concepts

1. structured outcome/reject emission helpers
2. budget metric emitters
3. deterministic test hooks
4. conformance evidence emit wrappers

Preferred contexts:

1. `edge`
2. `arbiter`
3. `meta`

## 6. Determinism Utility Concepts

1. fixed-point literal helpers
2. canonical rounding/normalization helpers
3. bounded map/list helpers
4. canonical sort/iteration helpers

Preferred contexts:

1. `arbiter`
2. `meta` (for deterministic business workflows)

## 7. Anti-Pattern Guard Modules

Wishlist lints and guards:

1. missing terminal outcome detector
2. unbounded fan-out detector
3. forbidden context API usage detector
4. unsafe numeric conversion detector
5. non-idempotent durable emit detector

## 8. Priority Backlog

Phase 1 (minimum useful SDK):

1. intent/validation
2. resource/cooldown
3. effects/status
4. combat stats/formula helpers
5. spells/skills/talents helpers
6. deterministic utilities
7. reject/outcome/observability helpers

Phase 2:

1. damage/mitigation
2. durable event helpers
3. transaction/reconciliation helpers
4. state-machine helpers
5. session/state management helpers
6. npc/monster/named-unit and AI helpers
7. crafting/recipe helpers
8. party/group runtime helpers

Phase 3:

1. progression/economy higher-level packs
2. auction house and marketplace packs
3. persistence and recovery helpers
4. administration and operations helpers
5. messaging/notifications/mailbox helpers
6. interactable/terrain/housing helpers
7. raid/instance orchestration helpers
8. pvp/matchmaking/rating helpers
9. genre packs (MMO RPG/RTS/MOBA) as first-class targets
