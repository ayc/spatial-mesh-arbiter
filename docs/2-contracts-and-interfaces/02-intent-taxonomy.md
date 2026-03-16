# Intent Taxonomy & Stable `intent_id` Registry

This document is the canonical source for **client-intent taxonomy** and stable numeric `intent_id` assignments used by gameplay design, content tooling, and observability.

It defines:
- intent categories and naming rules,
- stable `intent_id` ranges and lifecycle policy,
- the current full intent registry,
- design-archetype to intent mapping.

Canonical split:
- Wire schemas, envelopes, auth, sequencing, and reject behavior remain canonical in [Client <-> Edge Message Contract](01-client-edge-wire-protocol.md).
- Protobuf-style wire encoding profile guidance remains in architecture documentation (appendix in the client-edge contract family).
- Intent taxonomy and IDs are canonical in this document.

---

## 1. Scope and Non-Goals

### In scope
- Human-readable intent taxonomy (`intent_key`).
- Stable numeric `intent_id` assignments.
- Target-data shape catalog for gameplay and meta intents.
- Mapping from design archetypes to runtime intents.

### Non-goals
- This document does not redefine wire payload schemas.
- This document does not redefine auth/bootstrap or transport behavior.
- This document does not introduce mandatory new fields on client wire messages.
- This phase does not allocate new client intent IDs; existing IDs remain canonical.

---

## 2. ID Model and Lifecycle Policy

1. `intent_id` type is `u16`.
2. IDs are immutable once published.
3. IDs MUST NOT be reused, including deprecated IDs.
4. Each registry row has a lifecycle `status`:
   - `ACTIVE`
   - `DEPRECATED`
   - `RESERVED`
5. New intents MUST be appended to an unused ID in the correct lane range.

### 2.1 Global ID Ranges

| Range | Purpose |
| :--- | :--- |
| `0000-0099` | System/auth reserved |
| `0100-0199` | Simulation authoritative intents |
| `0200-0299` | Simulation reserved |
| `0300-0399` | Meta intents |
| `0400-0499` | Meta reserved |
| `0500-0599` | Control non-authoritative intents |
| `0600-65535` | Reserved |

---

## 3. Registry Schema

Every row in the canonical registry MUST include:
- `intent_id`
- `intent_key`
- `lane`
- `authoritative`
- `wire_shape`
- `target_data_shape`
- `edge_translation`
- `ack/reject semantics`
- `status`
- `notes`

Field conventions:
- `intent_key` uses lowercase dot notation (for example `ability.cast_targeted`).
- `lane` is one of `SIMULATION | META | CONTROL`.
- `authoritative` is `yes` only if intent contributes to authoritative gameplay/meta outcomes.

---

## 4. Canonical Intent Registry (Current)

| intent_id | intent_key | lane | authoritative | wire_shape | target_data_shape | edge_translation | ack/reject semantics | status | notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `0100` | `movement.control_update` | `SIMULATION` | `yes` | `SimulationInput` (`movement`, `aim`, `buttons`) | `none` | `ActionPayload::Engine(EngineAction::Movement)` | Immediate `EdgeAck` on ingress acceptance; deterministic `EdgeReject` on validation/sequence failure | `ACTIVE` | Continuous stream; may be coalesced to latest under pressure |
| `0110` | `ability.cast_targeted` | `SIMULATION` | `yes` | `DiscreteIntent::TargetedAbility` | `entity_ref(target_id)` | `ActionPayload::Game(ArpgAction::TargetedAbility)` | Immediate `EdgeAck` on acceptance; `EdgeReject` (`InvalidIntent`, `StaleSequence`, etc.) on failure | `ACTIVE` | Lock-on or direct-target cast |
| `0111` | `ability.cast_ground_targeted` | `SIMULATION` | `yes` | `DiscreteIntent::GroundTargetedAbility` | `world_point(destination_x,destination_y)` | `ActionPayload::Game(ArpgAction::GroundTargetedAbility)` | Immediate `EdgeAck` on acceptance; deterministic reject semantics on invalid destination/schema | `ACTIVE` | AoE placement cast |
| `0112` | `ability.cast_directional_projectile` | `SIMULATION` | `yes` | `DiscreteIntent::SpawnProjectile` | `direction(direction_x,direction_y)` + optional `entity_ref(target_id)` hint | `ActionPayload::Game(ArpgAction::SpawnProjectile)` | Immediate `EdgeAck` on acceptance; deterministic reject semantics on invalid direction/schema | `ACTIVE` | Skillshot and projectile launch intent |
| `0113` | `item.use_consumable` | `SIMULATION` | `yes` | `DiscreteIntent::UseConsumable` | `item_ref(item_id)` | `ActionPayload::Game(ArpgAction::UseConsumable)` | Immediate `EdgeAck` on acceptance; reject on invalid item/rate-limit/session | `ACTIVE` | Gameplay consumable activation |
| `0114` | `world.interact_entity` | `SIMULATION` | `yes` | `DiscreteIntent::Interact` | `entity_ref(target_entity)` | `ActionPayload::Game(ArpgAction::Interact)` | Immediate `EdgeAck` on acceptance; reject on invalid target/session/rules | `ACTIVE` | Interaction semantics are canonical in [NPC and World Interaction](../3-gameplay-systems/04-npc-and-world-interaction.md) |
| `0300` | `meta.send_chat_message` | `META` | `yes` (meta domain) | `MetaRequest::SendChatMessage` | `chat_payload(channel,text)` | Meta service forward | Immediate `EdgeAck` on accepted forward; `EdgeReject` on local schema/rate/session failure | `ACTIVE` | Low-frequency social intent |
| `0301` | `meta.move_inventory_item` | `META` | `yes` (meta domain) | `MetaRequest::MoveInventoryItem` | `inventory_slot_pair(from_slot,to_slot)` | Meta service forward | Immediate `EdgeAck` on accepted forward; deterministic reject on invalid slot/schema | `ACTIVE` | Strongly consistent inventory workflow |
| `0302` | `meta.invite_to_party` | `META` | `yes` (meta domain) | `MetaRequest::InviteToParty` | `player_name(target_character_name)` | Meta service forward | Immediate `EdgeAck` on accepted forward; reject on invalid schema/rules/session | `ACTIVE` | Party/social workflow |
| `0303` | `meta.request_logout` | `META` | `yes` (meta domain) | `MetaRequest::RequestLogout` | `none` | Meta/logout workflow | Immediate `EdgeAck` on accepted forward; reject when session state disallows logout request | `ACTIVE` | Logout handshake initiation |
| `0500` | `control.client_ping` | `CONTROL` | `no` | `ClientControlPayload::ClientPing` | `none` | Keepalive only | Optional control ack/notice path; rejects only for schema/session abuse | `ACTIVE` | Non-authoritative control message |
| `0501` | `control.pong` | `CONTROL` | `no` | `ClientControlPayload::Pong` | `none` | Keepalive only | Usually no explicit ack required; reject on malformed schema abuse | `ACTIVE` | Liveness response |
| `0510` | `control.device_telemetry` | `CONTROL` | `no` | `ClientControlPayload::DeviceTelemetry` | `telemetry_batch(samples)` | Analytics/anti-cheat/debug pipeline only | Best-effort ingest; may drop under load without gameplay impact; reject malformed schema only | `ACTIVE` | Never authoritative for gameplay outcome |

---

## 5. Target Data Shape Catalog

Canonical target-data shape names:
- `none`
- `entity_ref` (`u64`)
- `world_point` (`i32 x, i32 y` in NetCoord space)
- `direction` (`i32 x, i32 y`, normalized/validated at edge)
- `item_ref` (`u16`)
- `inventory_slot_pair` (`u8,u8`)
- `chat_payload` (`channel,text`)
- `player_name` (`string`)
- `telemetry_batch` (`Vec<DeviceTelemetrySample>`)

---

## 6. Design Archetype -> Intent Mapping

Gameplay/content archetypes map to canonical intents as follows:

| Design archetype | Canonical intent_key | intent_id | Runtime wire shape |
| :--- | :--- | :--- | :--- |
| `TargetedAbility` | `ability.cast_targeted` | `0110` | `DiscreteIntent::TargetedAbility` |
| `GroundTargetedAbility` | `ability.cast_ground_targeted` | `0111` | `DiscreteIntent::GroundTargetedAbility` |
| `SpawnProjectile` | `ability.cast_directional_projectile` | `0112` | `DiscreteIntent::SpawnProjectile` |
| `UseConsumable` | `item.use_consumable` | `0113` | `DiscreteIntent::UseConsumable` |
| `Interact` | `world.interact_entity` | `0114` | `DiscreteIntent::Interact` |

Design phrasing such as "I cast fireball" MUST resolve to one of these intent entries depending on targeting mode.

---

## 7. Hard Rules

1. Internal-only server payloads are never client intents.
   - Examples: `ImpactEvent`, `InternalPreparedHit`, prepared proc/hit envelopes.
2. `EdgeAck` means ingress acceptance, not authoritative gameplay success.
3. `CONTROL` telemetry intents are explicitly non-authoritative and droppable under load.
4. Registry IDs are for taxonomy/tooling/observability in this phase; wire payload shape remains unchanged.

---

## 8. Observability Guidance

Edge observability SHOULD include derived intent metadata for accepted/rejected ingress:
- `intent_id`
- `intent_key`
- `lane`
- `authoritative`

This is additive documentation guidance and does not require wire-schema changes.

---

## 9. Conformance Checklist

1. Every active client-intent variant in contract docs has exactly one registry row.
2. No duplicate `intent_id` and no duplicate `intent_key`.
3. Every simulation discrete intent maps to exactly one `ActionPayload` variant.
4. No internal-only payload appears as client-intent.
5. All control intents are marked `authoritative = no`.
6. Ability-framework examples resolve to valid intent keys/IDs.
7. Cross-document links from README, ability framework, and client-edge contract resolve.
8. Deprecation policy is status-only; IDs are never reused.

---

## 10. References

- Wire contract and ingress behavior: [Client-Edge Wire Protocol](01-client-edge-wire-protocol.md)
- Runtime-facing interfaces and translation layer: [Core Primitives](internal-mesh-types/01-core-primitives.md)
- Ability semantics and content examples: [Ability Framework](../3-gameplay-systems/02-ability-framework.md)
- NPC and world interaction semantics for `0114`: [NPC and World Interaction](../3-gameplay-systems/04-npc-and-world-interaction.md)
