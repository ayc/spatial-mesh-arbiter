# Architecture Section Mapping to Core Layers

This mapping links `docs/1-architecture/*` sections to the core abstraction layers in `docs-core/*`, and flags where game-specific logic should be separated.

## Disposition Legend

- `retain-core`: Keep in core framework docs with only wording cleanup.
- `split`: Keep framework contract, move game semantics/examples to a game template doc set.
- `move-template`: Move fully out of framework docs into a game template (ARPG starter kit).

## High-Level Findings

- Strong core candidates now: `03-mesh-controller.md`, `07-framework-boundary.md` (mostly framework-native).
- Mixed core/template docs: `01-core-concepts-and-mesh.md`, `02-npc-architecture.md`, `05-ai-node-protocol.md`, `06-kinematic-dilation.md`, `08-edge-p2p-visual-layer.md`.
- Template-heavy doc: `04-meta-services.md` (economy/progression/social are game-layer, not framework-layer).

## Section Mapping

### `01-core-concepts-and-mesh.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:7` Executive Summary | `00-scope-and-principles`, `README` | `split` | Keep engine intent; move ARPG/MOBA framing/examples to template docs. |
| `:30` Architectural Overview | `00-scope-and-principles`, `01-spatial-runtime-kernel` | `retain-core` | Core spatial actor model belongs in framework. |
| `:37` Proxy Actors (Edge Nodes) | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane` | `split` | Keep trusted-edge pattern; move concrete ability examples. |
| `:59` Identity Triad | `03-durability-bridge`, `04-game-adapter-interface` | `split` | Session/entity split is core; character semantics stay game/platform specific. |
| `:69` EntityID Allocation Contract | `03-durability-bridge` | `retain-core` | Generational identity and ABA protection are framework invariants. |
| `:82` Spatial Actors (Mesh Arbiters) | `01-spatial-runtime-kernel` | `split` | Keep single-authority and ownership rules; move combat-specific wording. |
| `:117` Ghost Entity Lifecycle | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Cross-boundary ghost model is reusable engine behavior. |
| `:138` Arbiter Relay Protocol | `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | TTL-1 relay and terminal outcome rules are core messaging contracts. |
| `:152` State Model (hard vs soft) | `03-durability-bridge` | `split` | Keep classification rule; move game-economy examples. |
| `:216` Propose -> Validate -> Commit | `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Core deterministic intent lifecycle. |
| `:243` Resolution Policies | `04-game-adapter-interface` | `move-template` | Target-lock/projectile/AoE resolution policy is game combat design. |
| `:324` Spatial Partitioning/Rebalancing | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `retain-core` | Split/merge/slide/transfer protocols are engine kernel contracts. |
| `:437` Mesh Controller and Epochs | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane` | `retain-core` | Control-plane and epoch handshake are framework-level. |
| `:501` Load Management/Graceful Degradation | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `split` | Keep load adaptation contract; move gameplay framing. |
| `:537` Meta Services Layer intro | `03-durability-bridge`, `04-game-adapter-interface` | `split` | Keep durable bridge boundaries; move service-domain content. |
| `:546` Sidecar Dispatch Pattern | `02-spatial-messaging-plane`, `04-game-adapter-interface` | `retain-core` | Lane split (simulation vs meta) is reusable. |
| `:554` Cross-Layer Handshake/Event Bus | `03-durability-bridge` | `retain-core` | At-least-once + idempotent consumer model is core bridge contract. |
| `:674` Reconnection/Entity Recovery | `01-spatial-runtime-kernel`, `03-durability-bridge` | `retain-core` | Session rebind and snapshot bootstrap are framework-runtime patterns. |
| `:683` Spawn & Logout Protocol | `04-game-adapter-interface` | `split` | Keep generic spawn/logout interfaces; move save-zone/JRPG semantics. |
| `:700` Death & Respawn Lifecycle | `04-game-adapter-interface` | `move-template` | Healer window/monster death flow is template-specific gameplay. |
| `:717` Arbiter Crash Recovery | `03-durability-bridge`, `05-conformance-invariants` | `split` | Keep crash/fate invariants; move player-facing UX copy and examples. |
| `:767` Cross-Layer Transaction Ledger | `03-durability-bridge` | `retain-core` | Pending/confirmed/refund reconciliation is reusable durability pattern. |
| `:829` Recovery Inbox | `03-durability-bridge` | `split` | Keep generic compensation inbox pattern; move loot/mail flavor. |
| `:874` Deferred Loot Recovery | `04-game-adapter-interface` | `move-template` | Loot policy is game economy/social rules. |
| `:914` Edge Node Crash Recovery | `01-spatial-runtime-kernel`, `03-durability-bridge`, `05-conformance-invariants` | `split` | Keep liveness/orphan/bootstrap contracts; move ARPG-specific bootstrap details. |
| `:1016` Divergence Philosophy | `00-scope-and-principles` | `retain-core` | Core consistency model statement. |
| `:1029` Summary of Authority Model | `00-scope-and-principles` | `retain-core` | Layered authority model belongs in framework abstract. |

### `02-npc-architecture.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:13` Scope | `04-game-adapter-interface` | `retain-core` | Useful framing for NPC boundary contracts. |
| `:29` NPC Intelligence Model | `04-game-adapter-interface` | `split` | Keep two-tier architecture; move concrete archetype taxonomy. |
| `:33` Two-Tier Classification | `04-game-adapter-interface` | `split` | Keep Arbiter-local vs external-AI model; move named archetypes. |
| `:47` Arbiter-Local NPCs | `04-game-adapter-interface` | `split` | Keep execution ownership; move FSM content to template docs. |
| `:57` AI Node Definition | `04-game-adapter-interface`, `02-spatial-messaging-plane` | `retain-core` | Unified ingress path for player and AI is a core reuse requirement. |
| `:84` Registration and Session Lifecycle | `02-spatial-messaging-plane`, `03-durability-bridge` | `retain-core` | Session/heartbeat/claim lifecycle are framework protocol concerns. |
| `:107` AI Node Crash Recovery | `01-spatial-runtime-kernel`, `03-durability-bridge`, `05-conformance-invariants` | `split` | Keep passive-mode/orphan recovery contract; move game-specific fallback tuning. |
| `:135` Commander Pattern | `04-game-adapter-interface` | `move-template` | Optional game mechanic, not required framework primitive. |
| `:166` AI Node Cluster Topology | `04-game-adapter-interface` | `split` | Keep assignment/lifecycle contract; move specialization presets. |
| `:185` AI Node Archetype Catalog | `04-game-adapter-interface` | `move-template` | Entirely gameplay/content taxonomy. |
| `:245` Core Timing Model | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `split` | Keep tier/cadence contract shape; move default archetype mappings. |
| `:274` Interest Management Contract | `01-spatial-runtime-kernel` | `retain-core` | Ring/budget/hysteresis are reusable engine replication policies. |
| `:309` Replication Interfaces | `02-spatial-messaging-plane`, `04-game-adapter-interface` | `split` | Keep envelope categories; move concrete NPC state enums to template. |
| `:429` Reliability Matrix | `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Reliable vs best-effort matrix is framework messaging policy. |
| `:443` Client Smoothing Contract | `02-spatial-messaging-plane` | `retain-core` | Interp/extrap/correction thresholds are engine netcode concerns. |
| `:455` Failure Modes and Edge Cases | `05-conformance-invariants` | `split` | Keep handoff/contention invariants; move encounter-specific examples. |
| `:475` Conformance Checklist | `05-conformance-invariants` | `split` | Keep protocol checks; move archetype-specific checks to template conformance. |

### `03-mesh-controller.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:15` Role and Identity | `01-spatial-runtime-kernel` | `retain-core` | Canonical control-plane role. |
| `:36` Transport | `02-spatial-messaging-plane` | `retain-core` | Controller/Arbiter control channels are framework contracts. |
| `:50` R-Tree Topology Management | `01-spatial-runtime-kernel` | `retain-core` | Core ownership topology model. |
| `:64` Topology Epochs | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `retain-core` | Epoch monotonicity and stale handling are engine invariants. |
| `:72` Minimum Cell Size Constraint | `01-spatial-runtime-kernel` | `split` | Keep rule, rename from spell-range framing to generic interaction extent. |
| `:80` Rebalancing Triggers | `01-spatial-runtime-kernel` | `retain-core` | Deterministic count-driven rebalancing is reusable. |
| `:100` Warm Pool Management | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `retain-core` | Fast-capacity orchestration is core MMO framework behavior. |
| `:210` Split Orchestration | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Hitless split protocol is core kernel contract. |
| `:233` Merge Orchestration | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Merge invariants are framework-level. |
| `:255` Boundary Sliding | `01-spatial-runtime-kernel` | `retain-core` | Reusable hotspot migration optimization. |
| `:267` Global Tick Synchronization | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `retain-core` | Metronome discipline is central runtime invariant. |
| `:316` Heartbeat Monitoring/Crash Detection | `03-durability-bridge`, `05-conformance-invariants` | `retain-core` | Crash declaration and repair path are framework contracts. |
| `:346` Global Event Routing | `02-spatial-messaging-plane`, `04-game-adapter-interface` | `split` | Keep escalation/fan-out protocol; move ability semantics to game adapter. |
| `:369` Live Data Distribution | `03-durability-bridge`, `04-game-adapter-interface` | `split` | Keep data-epoch transport; move concrete game asset schema names. |
| `:384` Spawn Topology Lookup | `03-durability-bridge` | `retain-core` | Reusable coordinate-to-owner lookup contract. |
| `:397` Failure Modes | `05-conformance-invariants` | `retain-core` | Topology freeze survival behavior is framework conformance. |
| `:417` Controller State Summary | `01-spatial-runtime-kernel` | `retain-core` | Internal control-plane state model remains core. |
| `:437` Debug Visualization | `05-conformance-invariants` | `retain-core` | Keep as optional conformance/tooling appendix. |

### `04-meta-services.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:17` Principles | `03-durability-bridge`, `05-conformance-invariants` | `split` | Keep durable authority/idempotent consumers/schema isolation; move product-domain assumptions. |
| `:28` Service Decomposition | `04-game-adapter-interface` | `move-template` | Concrete domain/service catalog is game/product specific. |
| `:45` Event Bus Subscription Matrix | `03-durability-bridge` | `split` | Keep matrix pattern; move event names tied to ARPG gameplay. |
| `:62` Core Platform | `03-durability-bridge`, `04-game-adapter-interface` | `split` | Keep interface boundaries; move game-flavored lifecycle semantics. |
| `:64` Identity & Session Service | `03-durability-bridge` | `split` | Session registry and identity handshake can stay core; auth/account policy stays template/platform. |
| `:172` Spawn & Lifecycle Service | `03-durability-bridge`, `04-game-adapter-interface` | `split` | Keep spawn orchestration pattern; move save-zone/respawn design policy. |
| `:271` Economy (all subsections) | `04-game-adapter-interface` | `move-template` | Inventory/loot/currency/trading are game systems, not framework. |
| `:1342` Transaction & Recovery | `03-durability-bridge` | `split` | Keep pending-transaction/reconcile pattern; move economy-specific flows. |
| `:1456` Progression (all subsections) | `04-game-adapter-interface` | `move-template` | XP/talent/quests/achievements are game semantics. |
| `:2212` Social (all subsections) | `04-game-adapter-interface` | `move-template` | Chat/party/guild/friends are product features, not core runtime. |
| `:2867` Cross-Cutting Concerns | `03-durability-bridge`, `05-conformance-invariants` | `retain-core` | Service communication, observability, config versioning are reusable platform patterns. |

### `05-ai-node-protocol.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:14` Scope | `04-game-adapter-interface` | `retain-core` | Good boundary statement for AI engine/runtime contract. |
| `:34` Architecture Overview | `04-game-adapter-interface`, `02-spatial-messaging-plane` | `retain-core` | Sidecar boundary is framework-level. |
| `:70` Transport and Connection | `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | gRPC/mTLS/liveness contract is reusable. |
| `:81` Protobuf Service Definition | `02-spatial-messaging-plane`, `04-game-adapter-interface` | `retain-core` | RPC shape is generic enough for multi-game use. |
| `:150` Connection/Lifecycle Messages | `02-spatial-messaging-plane` | `retain-core` | Claim/release/disconnect semantics are core protocol. |
| `:198` World State Messages | `02-spatial-messaging-plane`, `04-game-adapter-interface` | `split` | Keep transport shape; keep game fields opaque via adapter-owned payload structs. |
| `:236` Action Messages | `04-game-adapter-interface` | `split` | Replace fixed ability action union with adapter-defined action payload. |
| `:318` Commander Pattern Messages | `04-game-adapter-interface` | `move-template` | Optional mechanic, should not be required for framework conformance. |
| `:362` Session Lifecycle Messages | `02-spatial-messaging-plane` | `retain-core` | Runtime session event stream belongs in core protocol. |
| `:406` Heartbeat/Observability Messages | `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Core runtime health contract. |
| `:457` Session Lifecycle Flow | `02-spatial-messaging-plane`, `03-durability-bridge` | `retain-core` | Generic claim/bootstrap flow. |
| `:524` World State Delivery Contract | `02-spatial-messaging-plane` | `retain-core` | Monotonic ordering/bootstrap semantics are core. |
| `:534` Action Submission Contract | `02-spatial-messaging-plane`, `04-game-adapter-interface` | `split` | Keep idempotent terminal outcome rules; move action-type assumptions. |
| `:567` Error Model | `02-spatial-messaging-plane` | `retain-core` | Transport/application error taxonomy is reusable. |
| `:605` Crash Recovery/Reconnection | `03-durability-bridge`, `05-conformance-invariants` | `retain-core` | Recovery semantics are framework-level. |
| `:645` Versioning and Compatibility | `05-conformance-invariants` | `retain-core` | API evolution policy should remain core. |
| `:657` Observability Contract | `05-conformance-invariants` | `retain-core` | Runtime/engine metrics baseline is framework-wide. |
| `:687` Conformance Checklist | `05-conformance-invariants` | `split` | Keep generic protocol checks; move commander-specific checks to template appendix. |

### `06-kinematic-dilation.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:7` What KiDi Is | `01-spatial-runtime-kernel` | `split` | Keep load-adaptive time-scaling contract; move diegetic narrative language. |
| `:15` Temporal Swamp Philosophy | `04-game-adapter-interface` | `move-template` | UX/gameplay framing should be game-specific guidance. |
| `:22` When KiDi Activates | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `retain-core` | Activation thresholds and coexistence with split policy are core runtime. |
| `:36` How It Works | `01-spatial-runtime-kernel` | `retain-core` | Core formula/invariant material. |
| `:85` What Gets Dilated | `01-spatial-runtime-kernel`, `04-game-adapter-interface` | `split` | Keep category-level rules; move buff/ability examples to templates. |
| `:121` How Load Reduction Works | `01-spatial-runtime-kernel` | `retain-core` | Core operational behavior under pressure. |
| `:149` Cross-Boundary Blending | `01-spatial-runtime-kernel`, `05-conformance-invariants` | `retain-core` | Deterministic seam behavior is framework-critical. |
| `:172` Dilation Propagation | `02-spatial-messaging-plane` | `retain-core` | Propagation contract across controller/edge/neighbors is reusable. |
| `:184` Configuration | `03-durability-bridge` | `retain-core` | Config epoch and hot-tune model is framework-level. |
| `:198` Client-Side Indicator | `04-game-adapter-interface` | `move-template` | Pure UX policy; should live with game UI docs. |
| `:217` Self-Correcting Feedback Loop | `01-spatial-runtime-kernel` | `split` | Keep control-loop behavior; move player-behavior narrative. |
| `:240` Patterns and Anti-Patterns | `05-conformance-invariants` | `retain-core` | Strong implementation guardrails for framework conformance. |
| `:287` Relationship to Other Systems | `01-spatial-runtime-kernel`, `04-game-adapter-interface` | `split` | Keep system coupling rules; move game-specific references. |

### `07-framework-boundary.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:9` Design Principles | `00-scope-and-principles`, `04-game-adapter-interface` | `retain-core` | This is already core-boundary doctrine. |
| `:23` What the Engine Owns | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane`, `03-durability-bridge` | `retain-core` | Canonical engine ownership map. |
| `:97` What the Game Owns | `04-game-adapter-interface` | `retain-core` | Canonical game adapter ownership map. |
| `:344` Extension Points | `04-game-adapter-interface` | `retain-core` | Explicit callback surface for reusable engine integration. |
| `:362` Serialization Boundary | `04-game-adapter-interface`, `02-spatial-messaging-plane` | `retain-core` | Core handoff/opaque payload contract. |
| `:381` What Changes in Existing Docs | `README` | `split` | Keep as migration plan appendix, not normative engine contract. |
| `:393` Impact on Implementation Phases | `README` | `split` | Keep as rollout plan appendix. |
| `:405` What This Enables | `README`, template docs | `split` | Keep generic multi-genre statement; move genre examples to template materials. |
| `:418` One Stack, One Game | `04-game-adapter-interface`, `05-conformance-invariants` | `retain-core` | Hard deployment invariant for framework reuse strategy. |
| `:429` Open Questions | `README` | `retain-core` | Keep as backlog for abstraction hardening. |

### `08-edge-p2p-visual-layer.md`

| Source section | Core destination | Disposition | Notes |
| --- | --- | --- | --- |
| `:9` Motivation | `02-spatial-messaging-plane` | `retain-core` | Low-latency visual lane rationale is framework-level. |
| `:30` Two-Channel Model | `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Intent/visual vs consequence separation is reusable. |
| `:39` P2P Visual Message Contents | `02-spatial-messaging-plane`, `04-game-adapter-interface` | `split` | Keep envelope and movement primitives; move discrete visual payload schema to game adapter. |
| `:101` Edge Node Pre-Validation | `01-spatial-runtime-kernel`, `04-game-adapter-interface` | `retain-core` | Shared ingress screening model for edge layer. |
| `:127` Reconciliation | `02-spatial-messaging-plane`, `05-conformance-invariants` | `retain-core` | Silence-as-correction and explicit correction events are core messaging behavior. |
| `:159` Proximity Manifest | `02-spatial-messaging-plane` | `retain-core` | Arbiter-managed peer discovery is reusable netcode. |
| `:163` Distance Tiers | `02-spatial-messaging-plane` | `retain-core` | Tier/cadence framework is reusable and configurable. |
| `:184` Manifest Structure | `02-spatial-messaging-plane` | `retain-core` | Core discovery contract. |
| `:211` Cadence Rules | `02-spatial-messaging-plane` | `retain-core` | Transport cadence policy belongs in framework messaging docs. |
| `:222` Cross-Boundary Peers | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane` | `retain-core` | Ghost + manifest interplay is core boundary behavior. |
| `:230` Arbiter Broadcast Reduction | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane` | `retain-core` | Core runtime load reduction strategy. |
| `:257` Security Model | `05-conformance-invariants` | `retain-core` | Trust boundary and authoritative override are framework safety rules. |
| `:281` Edge Node Implementation Changes | `01-spatial-runtime-kernel`, `02-spatial-messaging-plane` | `retain-core` | Runtime responsibilities are framework-owned. |
| `:337` Relationship to Existing Systems | `01-spatial-runtime-kernel`, `04-game-adapter-interface` | `split` | Keep system coupling; move game-tagged visual significance policy. |
| `:373` Bandwidth Analysis | `README` | `retain-core` | Keep as benchmark/non-normative performance appendix. |
| `:396` Open Questions | `README` | `retain-core` | Keep as design backlog for transport/caps/relay policy. |

## Recommended Extraction Order

1. Move `04-meta-services.md` economy/progression/social domains into a game template directory first (largest game-logic concentration).
2. Split `01-core-concepts-and-mesh.md` section 9 into:
   - framework bridge contracts (`docs-core/03-*`)
   - template lifecycle/economy behavior docs.
3. Normalize protocol docs (`02-npc-architecture.md`, `05-ai-node-protocol.md`, `08-edge-p2p-visual-layer.md`) so action payload semantics are adapter-owned and transport semantics are framework-owned.
4. Keep `03-mesh-controller.md` and `07-framework-boundary.md` as baseline core references with minimal semantic cleanup.
