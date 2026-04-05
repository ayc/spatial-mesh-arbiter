# Lua Whitelisted API Contract v0.1

This document defines the strict callable surface for the Lua authoring profile
defined in `01-1-lua-subset-profile.md`.

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Scope and Precedence

1. This contract is normative for symbol-level API admission in Lua game source.
2. `01-1-lua-subset-profile.md` defines syntax/features policy.
3. This document defines which symbols are legal, where they are legal, and how they are validated.
4. **Architectural Note:** The primary authoring surface for most combat abilities is the declarative YAML schema defined in `02-schema-and-validation.md`. The Lua `MUT` symbols in this document mirror those YAML effect types, providing a procedural fallback for complex, highly conditional logic that cannot be expressed purely in YAML.
5. `08-sdk-catalog-wishlist.md` is roadmap-level and non-binding when conflicts exist.

## 2. Contract Model

1. Any callable symbol not listed in this document MUST fail compilation.
2. API calls MUST be validated at compile time for:
   1. symbol identity
   2. context legality (`edge`, `arbiter`, `meta`)
   3. arity and argument types
   4. boundedness preconditions
3. Compilation MUST lower accepted calls to canonical IR operations.
4. Runtime nodes MUST execute lowered IR only, not direct Lua function dispatch.

## 3. Primitive Types and Value Domains

Primitive argument and return domains in this document use:

1. `bool`
2. `int`
3. `fixed`
4. `string`
5. `id`
6. `list<T>` (explicit bound required for authoritative flow)
7. `record`

Numeric literals accepted from Lua source MUST normalize to canonical fixed/int
representation before IR emission.

## 4. Determinism Classes

Each symbol is classified as one of:

1. `DECL`: declaration-only construct.
2. `PURE`: deterministic read/predicate helper (no mutation).
3. `MUT`: mutation intent helper (lowers to mutation IR op).
4. `EMIT`: internal event emission helper.
5. `DURABLE`: durable workflow/event helper.
6. `OBS`: observability helper (non-authoritative side-channel metadata only).

## 5. Whitelisted Symbols (v0.1)

## 5.1 Rule Declaration Symbols

| Symbol | Class | Signature | Allowed Contexts | Notes |
|---|---|---|---|---|
| `rule` | `DECL` | `rule(name: string)` | all | Top-level rule block declaration only. |
| `context` | `DECL` | `context(kind: string)` | all | `kind` must be one of `edge`, `arbiter`, `meta`. |
| `on_intent` | `DECL` | `on_intent(intent_name: string)` | all | Exactly one trigger function is required per rule. |
| `on_event` | `DECL` | `on_event(event_name: string)` | all | Exactly one trigger function is required per rule. |
| `on_tick` | `DECL` | `on_tick(stream: string)` | all | Exactly one trigger function is required per rule. |
| `outcome_accept` | `DECL` | `outcome_accept()` | all | Required terminal outcome path for non-continuous intent rules. |
| `outcome_reject` | `DECL` | `outcome_reject(code: string)` | all | Reject code must be from configured stable code set. |
| `require_predicate` | `DECL` | `require_predicate(cond: bool, reject_code: string)` | all | Deterministic guard that lowers to validate-stage reject logic. |

## 5.2 Predicate and Query Symbols

Symbols marked as **[Guard-Eligible]** can be extracted by the compiler from Lua `if` statements into `GuardExpr` IR blocks (Phase 3).

| Symbol | Class | Signature | Allowed Contexts | Boundedness Contract |
|---|---|---|---|---|
| `cooldown_ready` | `PURE` | `cooldown_ready(actor: id, cooldown_id: string) -> bool` | `edge`, `arbiter` | O(1) state lookup only. |
| `resource_at_least` | `PURE` | `resource_at_least(actor: id, pool_id: string, amount: fixed) -> bool` | `edge`, `arbiter` | **[Guard-Eligible]** O(1) state lookup. |
| `distance_leq` | `PURE` | `distance_leq(a: id, b: id, max_dist: fixed) -> bool` | `edge`, `arbiter` | O(1) numeric predicate only. |
| `target_exists` | `PURE` | `target_exists(target: id) -> bool` | `edge`, `arbiter` | O(1) ownership-aware lookup only. |
| `target_is_hostile` | `PURE` | `target_is_hostile(a: id, b: id) -> bool` | `edge`, `arbiter` | O(1) relation lookup only. |
| `collect_targets_in_radius` | `PURE` | `collect_targets_in_radius(origin: id, radius: fixed, max_targets: int, filter_id: string) -> list<id>` | `arbiter` | `max_targets` literal is required and must be `<= selector_max_targets`. |
| `has_status` | `PURE` | `has_status(target: id, status_id: string) -> bool` | `edge`, `arbiter` | **[Guard-Eligible]** O(1) status lookup. |
| `hp_below` | `PURE` | `hp_below(target: id, threshold_pct: fixed) -> bool` | `edge`, `arbiter` | **[Guard-Eligible]** O(1) vital check. |
| `hp_above` | `PURE` | `hp_above(target: id, threshold_pct: fixed) -> bool` | `edge`, `arbiter` | **[Guard-Eligible]** O(1) vital check. |
| `is_in_zone` | `PURE` | `is_in_zone(target: id, zone_type: string) -> bool` | `arbiter` | **[Guard-Eligible]** Bounds-checked zone presence. |
| `facing_toward` | `PURE` | `facing_toward(viewer: id, target: id, dot_threshold: fixed) -> bool` | `arbiter` | **[Guard-Eligible]** Vector dot-product check. |
| `stack_count` | `PURE` | `stack_count(target: id, pool_id: string) -> int` | `edge`, `arbiter` | **[Guard-Eligible]** when used with comparison ops. |
| `state_present` | `PURE` | `state_present(actor: id, state_id: string) -> bool` | `arbiter` | **[Guard-Eligible]** O(1) runtime-state presence lookup only. |
| `sequence_step` | `PURE` | `sequence_step(actor: id, state_id: string) -> int` | `arbiter` | **[Guard-Eligible]** O(1) sequence-window step read only. |
| `charge_count` | `PURE` | `charge_count(actor: id, state_id: string) -> int` | `arbiter` | **[Guard-Eligible]** O(1) charge-pool count read only. |
| `is_npc` | `PURE` | `is_npc(entity: id) -> bool` | `edge`, `arbiter` | O(1) type-tag lookup only. |
| `is_monster` | `PURE` | `is_monster(entity: id) -> bool` | `edge`, `arbiter` | O(1) type-tag lookup only. |
| `is_named_unit` | `PURE` | `is_named_unit(entity: id) -> bool` | `edge`, `arbiter` | O(1) identity-tag lookup only. |
| `ai_state` | `PURE` | `ai_state(entity: id) -> string` | `arbiter` | O(1) AI state read only. |
| `threat_value` | `PURE` | `threat_value(source: id, target: id) -> fixed` | `arbiter` | bounded deterministic lookup only. |
| `stat_base` | `PURE` | `stat_base(actor: id, stat_id: string) -> fixed` | `edge`, `arbiter`, `meta` | O(1) base-stat lookup only. |
| `stat_effective` | `PURE` | `stat_effective(actor: id, stat_id: string) -> fixed` | `edge`, `arbiter`, `meta` | Bounded modifier resolution only. |
| `spell_can_cast` | `PURE` | `spell_can_cast(caster: id, spell_id: string, target: id) -> bool` | `edge`, `arbiter` | deterministic cast-admission predicate only. |
| `skill_level` | `PURE` | `skill_level(actor: id, skill_id: string) -> int` | `edge`, `arbiter`, `meta` | O(1) skill-level lookup only. |
| `talent_is_unlocked` | `PURE` | `talent_is_unlocked(actor: id, talent_id: string) -> bool` | `edge`, `arbiter`, `meta` | deterministic unlock-state lookup only. |
| `talent_points_available` | `PURE` | `talent_points_available(actor: id, tree_id: string) -> int` | `edge`, `meta` | O(1) talent point balance lookup only. |
| `mailbox_unread_count` | `PURE` | `mailbox_unread_count(actor: id) -> int` | `edge`, `meta` | O(1) indexed mailbox summary lookup only. |
| `can_interact` | `PURE` | `can_interact(actor: id, object_id: id, action_id: string) -> bool` | `edge`, `arbiter` | O(1) permission and state predicate only. |
| `object_state` | `PURE` | `object_state(object_id: id) -> string` | `edge`, `arbiter` | O(1) object-state lookup only. |
| `terrain_has_tag` | `PURE` | `terrain_has_tag(subject: id, tag: string) -> bool` | `edge`, `arbiter` | Query count contributes to `max_terrain_queries_per_rule`. |
| `region_id_at` | `PURE` | `region_id_at(subject: id) -> string` | `edge`, `arbiter`, `meta` | O(1) region identity lookup only. |
| `housing_has_access` | `PURE` | `housing_has_access(actor: id, plot_id: id) -> bool` | `edge`, `meta` | O(1) access-policy lookup only. |
| `housing_item_count` | `PURE` | `housing_item_count(plot_id: id) -> int` | `meta` | O(1) indexed housing summary lookup only. |
| `recipe_can_craft` | `PURE` | `recipe_can_craft(actor: id, recipe_id: string, qty: int) -> bool` | `edge`, `meta` | deterministic eligibility check only. |
| `recipe_preview` | `PURE` | `recipe_preview(recipe_id: string, qty: int) -> record` | `edge`, `meta` | deterministic output preview only. |
| `craft_queue_size` | `PURE` | `craft_queue_size(actor: id, station_id: id) -> int` | `meta` | O(1) indexed queue summary lookup only. |
| `party_is_member` | `PURE` | `party_is_member(actor: id, party_id: id) -> bool` | `edge`, `arbiter`, `meta` | O(1) membership lookup only. |
| `party_member_count` | `PURE` | `party_member_count(party_id: id) -> int` | `edge`, `arbiter`, `meta` | O(1) indexed party size lookup only. |
| `raid_member_count` | `PURE` | `raid_member_count(raid_id: id) -> int` | `edge`, `meta` | O(1) indexed raid size lookup only. |
| `raid_has_lockout` | `PURE` | `raid_has_lockout(actor: id, lockout_id: string) -> bool` | `edge`, `meta` | deterministic lockout-state lookup only. |
| `pvp_queue_state` | `PURE` | `pvp_queue_state(actor: id, queue_id: string) -> string` | `edge`, `meta` | O(1) queue-state lookup only. |
| `pvp_rating` | `PURE` | `pvp_rating(actor: id, ladder_id: string) -> int` | `edge`, `meta` | O(1) rating lookup only. |

## 5.3 Mutation Symbols

| Symbol | Class | Signature | Allowed Contexts | Boundedness Contract |
|---|---|---|---|---|
| `spend_resource` | `MUT` | `spend_resource(actor: id, pool_id: string, amount: fixed)` | `arbiter` | One mutation record per call. |
| `refund_resource` | `MUT` | `refund_resource(actor: id, pool_id: string, amount: fixed)` | `arbiter`, `meta` | One mutation record per call. |
| `set_cooldown` | `MUT` | `set_cooldown(actor: id, cooldown_id: string, ticks: int)` | `arbiter` | `ticks` must be bounded non-negative int. |
| `apply_status` | `MUT` | `apply_status(target: id, status_id: string, duration_ticks: int, stacks: int)` | `arbiter` | `duration_ticks` and `stacks` must satisfy schema caps. |
| `remove_status` | `MUT` | `remove_status(target: id, status_id: string)` | `arbiter` | One mutation record per call. |
| `apply_damage` | `MUT` | `apply_damage(source: id, target: id, amount: fixed, damage_type: string)` | `arbiter` | One mutation record per call. |
| `apply_heal` | `MUT` | `apply_heal(source: id, target: id, amount: fixed)` | `arbiter` | One mutation record per call. |
| `apply_cc` | `MUT` | `apply_cc(target: id, cc_type: string, duration_ticks: int, is_cleansable: bool)` | `arbiter` | CC type must be a valid canonical profile (`stun`, `root`, `silence`, `sleep`, `disarm`, `blind`, `fear`, `charm`, `taunt`, `berserk`, `mute`). Higher-level authoring sugar supplies category pairing, duration-scaling policy, DR metadata, and optional expiry follow-ups; the compiler lowers those into generated status metadata. |
| `cleanse` | `MUT` | `cleanse(target: id, polarity: string, require_cleansable: bool, cc_categories: list<string>?)` | `arbiter` | `polarity` must be `negative`, `positive`, or `all`. Optional `cc_categories` filters removal to statuses whose compiled `cc_category` matches one of the supplied canonical names. Matching is against canonical status metadata, not string tags. |
| `write_state` | `MUT` | `write_state(actor: id, state_id: string, spec: record)` | `arbiter` | `spec.capture` must be `position` or `entity_ref`; referenced runtime state must accept that payload. |
| `clear_state` | `MUT` | `clear_state(actor: id, state_id: string)` | `arbiter` | One runtime-state clear per call. |
| `restore_from_state` | `MUT` | `restore_from_state(target: id, state_id: string, spec: record)` | `arbiter` | `spec` may request `apply_position` and/or `apply_hp`; relocation follows the canonical teleport/handoff validation path. |
| `advance_sequence` | `MUT` | `advance_sequence(actor: id, state_id: string, action: string)` | `arbiter` | `action` must be `advance` or `reset`; referenced runtime state must be `sequence_window`. |
| `modify_charge_pool` | `MUT` | `modify_charge_pool(actor: id, state_id: string, spec: record)` | `arbiter` | `spec.action` must be `add`, `consume`, or `reset`; referenced runtime state must be `charge_pool`. |
| `modify_resource` | `MUT` | `modify_resource(target: id, pool_id: string, mode: string, amount: fixed)` | `arbiter` | `mode` must be `add` or `remove`; canonical runtime clamps to `[0, max_resource(pool_id)]` on the target owner. |
| `apply_shield` | `MUT` | `apply_shield(target: id, shield_type: string, amount: fixed, charges: int, duration_ticks: int)` | `arbiter` | Shield type must be absorption or instance. Higher-level compiler authoring may attach absorb / break / expire callbacks plus binding names; this helper is only the core shield mutation. |
| `consume_status` | `MUT` | `consume_status(target: id, status_id: string, source_entity: id, spec: record)` | `arbiter` | `spec` must lower to canonical `consume_status` only: optional `max_instances` plus optional `on_consume_effects`. Matching is exact on `status_id` + source identity, not on polarity / cleanse flags. |
| `burn_resource` | `MUT` | `burn_resource(target: id, pool_id: string, amount: fixed, damage_ratio: fixed, damage_type: string, grant_to_caster: bool)` | `arbiter` | Target-side authoritative pool read only; bonus damage derives from the actual destroyed amount. |
| `displace` | `MUT` | `displace(target: id, destination: record, arc: bool, duration_ticks: int)` | `arbiter` | Destination must be resolvable fixed-point vector. |
| `inject_geometry` | `MUT` | `inject_geometry(position: record, spec: record)` | `arbiter` | `spec` must lower to canonical `inject_geometry` only: bounded lifetime, one supported mode (`circle`, `box`, `ring`, or `segment`), and at least one blocking flag. |
| `spawn_polyline_zone` | `MUT` | `spawn_polyline_zone(source: id, spec: record)` | `arbiter` | `spec` must lower to canonical `polyline_zone` only: bounded sampling cadence, bounded segment TTL/count, and optional pulse/enter/leave payloads within rule limits. |
| `kinematic_sweep` | `MUT` | `kinematic_sweep(target: id, spec: record)` | `arbiter` | `spec` must lower to canonical `kinematic_sweep` only: bounded duration, bounded collision radius, and optional capture/orbit policy within the shared sweep contract. |
| `steer_trajectory` | `MUT` | `steer_trajectory(target: id, mode: string, duration_ticks: int)` | `arbiter` | Mode must be toward_source, away_from_source, or toward_target. |
| `value_conversion` | `MUT` | `value_conversion(source: id, target: id, source_type: string, target_type: string, ratio: fixed)` | `arbiter` | Bounded scalar conversion (e.g., lifesteal, mana burn). |
| `swap_hp_percent` | `MUT` | `swap_hp_percent(caster: id, target: id, min_hp: fixed, same_arbiter_only: bool)` | `arbiter` | Captures both HP percentages before either write; default lowering rejects remote/Ghost targets. |
| `execute_threshold` | `MUT` | `execute_threshold(source: id, target: id, threshold: fixed, normal_damage: fixed, damage_type: string, bypass_prevention: bool)` | `arbiter` | Threshold check must occur on target authority; bypass is only legal for compiler-authorized execute definitions. |
| `swap_identity` | `MUT` | `swap_identity(target: id, source: record, duration_ticks: int, hp_policy: string, cooldown_policy: string)` | `arbiter` | `source` must lower to one `LoadoutSource`; projection preserves entity identity/position and uses compiler-authored revert state only. `source` MAY be `corpse_snapshot` when the corpse profile retained a projected loadout snapshot. |
| `revive_corpse` | `MUT` | `revive_corpse(corpse: id, hp_ratio: fixed, clear_statuses: bool, cooldown_policy: string, consume_corpse: bool)` | `arbiter` | Lowers to canonical `revive_corpse` only. The referenced corpse must be in the CURRENT Arbiter's authoritative corpse registry; this helper does not author alternate Meta respawn routing. |
| `restore_phase` | `MUT` | `restore_phase(target: id, hp_ratio: fixed, required_phase: string, clear_negative_statuses: bool)` | `arbiter` | Lowers to canonical `restore_phase` only: one Stage 10 return from a non-zero lifecycle phase back to Active. |
| `consume_corpse` | `MUT` | `consume_corpse(spec: record)` | `arbiter` | `spec` must lower to canonical `consume_corpse` only: bounded corpse query/count, optional atomic claim, optional corpse-derived bindings, and per-corpse child effects against the CURRENT Arbiter's corpse registry. |
| `borrow_ability_slot` | `MUT` | `borrow_ability_slot(target: id, source_entity: id, source_selector: string, source_slot_id: string, destination_slot_id: string, duration_ticks: int, usage_limit: int)` | `arbiter` | `source_selector` must be `last_cast_ability` or `slot_id`; last-cast reads one bounded public cast-history register. |
| `control_override` | `MUT` | `control_override(target: id, controller: id, duration_ticks: int, input_policy: string, controller_lock_mode: string, target_lock_mode: string)` | `arbiter` | Routing mutation never commits mid-tick; it becomes a pending Stage 1 P-29 update for the next tick. |
| `cycle_split_form` | `MUT` | `cycle_split_form(controller: id, source_ability_id: string)` | `arbiter` | `source_ability_id` must reference an ability that authors canonical `split_form`; the helper only advances to the next surviving split member in authored order. |
| `link_entities` | `MUT` | `link_entities(source: id, target: id, spec: record)` | `arbiter` | `spec` must lower to canonical `link` policy only: bounded duration, optional break distance, optional `damage_redirect`, `heal_mirror_ratio`, `event_clone`, and/or `origin_override`. Mirrored/cloned events always carry anti-recursion metadata; origin override never transfers authority or stats. |
| `spawn_entity` | `MUT` | `spawn_entity(archetype_id: string, owner: id, at: id) -> id` | `arbiter` | Spawn count per rule must satisfy `max_spawns_per_rule`. |
| `spawn_portal_anchor` | `MUT` | `spawn_portal_anchor(archetype_id: string, owner: id, at: id, spec: record) -> id` | `arbiter` | `spec` must lower to canonical `PortalAnchorBlock` only: bounded interaction range, bounded cooldown/channel timing, and one supported network mode. |
| `spawn_zone` | `MUT` | `spawn_zone(shape: string, radius: fixed, position: record, duration_ticks: int) -> id` | `arbiter` | Zone spawn count must satisfy `max_spawns_per_rule`. |
| `enter_container` | `MUT` | `enter_container(occupant: id, container: id, eject_after_ticks: int)` | `arbiter` | The target container must currently expose a compiled `ContainerProfileDef`; range, capacity, and allowed-filter checks follow that profile. |
| `exit_container` | `MUT` | `exit_container(container: id, spec: record)` | `arbiter` | `spec.mode` must be `specific_occupant` or `all_occupants`; exit placement follows the canonical `exit_container` effect contract. |
| `fork_instance` | `MUT` | `fork_instance(spec: record) -> id` | `arbiter` | `spec` must lower to canonical `fork_instance` only, and all listed members must already be authoritative on the current Arbiter. |
| `schedule_global_event` | `MUT` | `schedule_global_event(caster: id, spec: record)` | `arbiter` | `spec` must lower to canonical `global_event` only: positive lead, bounded geometry, bounded optional pulse window, and controller-escalated execution with local target-owner defense resolution. |
| `despawn_entity` | `MUT` | `despawn_entity(entity: id, reason: string)` | `arbiter`, `meta` | One mutation record per call. Mirrors canonical declarative `despawn_entity` when a design needs an imperative fallback. |
| `add_stat_modifier` | `MUT` | `add_stat_modifier(target: id, modifier_id: string, stat_id: string, value: fixed, duration_ticks: int)` | `arbiter`, `meta` | Modifier count must satisfy `max_stat_modifiers_per_entity`. |
| `remove_stat_modifier` | `MUT` | `remove_stat_modifier(target: id, modifier_id: string)` | `arbiter`, `meta` | One mutation record per call. |
| `cast_spell` | `MUT` | `cast_spell(caster: id, spell_id: string, target: id, variant_id: string)` | `arbiter` | spell effect ops must satisfy `max_spell_effect_ops_per_cast`. |
| `activate_skill` | `MUT` | `activate_skill(actor: id, skill_id: string, target: id)` | `arbiter` | skill activation count must satisfy `max_skill_activations_per_rule`. |
| `ai_set_state` | `MUT` | `ai_set_state(entity: id, state_id: string)` | `arbiter` | AI transition count must satisfy `max_ai_state_transitions_per_rule`. |
| `ai_set_target` | `MUT` | `ai_set_target(entity: id, target: id)` | `arbiter` | target-update count must satisfy `max_ai_target_updates_per_rule`. |
| `ai_set_leash_anchor` | `MUT` | `ai_set_leash_anchor(entity: id, anchor: id, max_range: fixed)` | `arbiter` | one leash update mutation per call. |
| `interact_object` | `MUT` | `interact_object(actor: id, object_id: id, action_id: string)` | `arbiter` | Interaction count must satisfy `max_interactions_per_rule`. |
| `set_object_state` | `MUT` | `set_object_state(object_id: id, state_id: string)` | `arbiter`, `meta` | One state-transition mutation per call. |
| `apply_terrain_modifier` | `MUT` | `apply_terrain_modifier(region_id: string, modifier_id: string, duration_ticks: int)` | `arbiter`, `meta` | Modifier fan-out must satisfy trigger/region bounds. |
| `clear_terrain_modifier` | `MUT` | `clear_terrain_modifier(region_id: string, modifier_id: string)` | `arbiter`, `meta` | One mutation record per call. |
| `grant_item` | `MUT` | `grant_item(actor: id, item_id: string, qty: int)` | `meta` | `qty` must be bounded positive int. |
| `deduct_currency` | `MUT` | `deduct_currency(actor: id, currency_id: string, amount: int)` | `meta` | `amount` must be bounded positive int. |

## 5.4 Event and Durable Symbols

| Symbol | Class | Signature | Allowed Contexts | Boundedness and Safety Contract |
|---|---|---|---|---|
| `emit_event` | `EMIT` | `emit_event(event_name: string, payload: record)` | `arbiter`, `meta` | Count per rule must satisfy `max_internal_emits_per_rule`. |
| `emit_hard_event` | `DURABLE` | `emit_hard_event(topic: string, payload: record, idempotency_key: string)` | `meta` | `idempotency_key` is required and must be stable under retry. |
| `send_notification` | `DURABLE` | `send_notification(actor: id, template_id: string, payload: record, idempotency_key: string)` | `meta` | deterministic notification side-effect only; bounded payload and idempotency key required. |
| `mailbox_send` | `DURABLE` | `mailbox_send(actor: id, subject_key: string, body_key: string, attachments: list<record>, expires_at_ms: int, idempotency_key: string)` | `meta` | `attachments` length must be `<= max_mail_attachments_per_message`. |
| `mailbox_claim` | `DURABLE` | `mailbox_claim(actor: id, mail_id: id, idempotency_key: string)` | `meta` | duplicate-safe claim semantics required. |
| `mailbox_delete` | `DURABLE` | `mailbox_delete(actor: id, mail_id: id, idempotency_key: string)` | `meta` | duplicate-safe delete semantics required. |
| `housing_place_item` | `DURABLE` | `housing_place_item(actor: id, plot_id: id, item_id: string, transform: record, idempotency_key: string)` | `meta` | `housing_item_count(plot_id)` plus pending placement count must be `<= max_housing_items_per_plot`. |
| `housing_remove_item` | `DURABLE` | `housing_remove_item(actor: id, plot_id: id, placement_id: id, idempotency_key: string)` | `meta` | duplicate-safe removal semantics required. |
| `housing_set_permission` | `DURABLE` | `housing_set_permission(plot_id: id, subject_id: id, role_id: string, idempotency_key: string)` | `meta` | bounded permission entry updates only. |
| `craft_execute` | `DURABLE` | `craft_execute(actor: id, recipe_id: string, qty: int, station_id: id, idempotency_key: string)` | `meta` | ingredient/output entries must satisfy recipe bounds and atomic consume/grant semantics. |
| `craft_queue_start` | `DURABLE` | `craft_queue_start(actor: id, station_id: id, recipe_id: string, qty: int, idempotency_key: string)` | `meta` | queue operations per rule must satisfy `max_craft_queue_ops_per_rule`. |
| `craft_queue_cancel` | `DURABLE` | `craft_queue_cancel(actor: id, queue_entry_id: id, idempotency_key: string)` | `meta` | duplicate-safe queue cancel semantics required. |
| `talent_allocate` | `DURABLE` | `talent_allocate(actor: id, talent_id: string, idempotency_key: string)` | `meta` | talent mutation count must satisfy `max_talent_mutations_per_rule`. |
| `talent_refund` | `DURABLE` | `talent_refund(actor: id, talent_id: string, idempotency_key: string)` | `meta` | duplicate-safe refund semantics required. |
| `skill_grant_xp` | `DURABLE` | `skill_grant_xp(actor: id, skill_id: string, xp: int, idempotency_key: string)` | `meta` | grant count must satisfy `max_skill_xp_grants_per_rule`. |
| `party_create` | `DURABLE` | `party_create(leader: id, party_type: string, idempotency_key: string) -> id` | `meta` | party mutation count must satisfy `max_party_mutations_per_rule`. |
| `party_invite` | `DURABLE` | `party_invite(party_id: id, inviter: id, target: id, idempotency_key: string)` | `meta` | invite/send count contributes to `max_party_mutations_per_rule`. |
| `party_join` | `DURABLE` | `party_join(party_id: id, actor: id, idempotency_key: string)` | `meta` | join operations must satisfy `max_party_mutations_per_rule` and `max_party_size`. |
| `party_leave` | `DURABLE` | `party_leave(party_id: id, actor: id, idempotency_key: string)` | `meta` | duplicate-safe leave semantics required. |
| `raid_assign_subgroup` | `DURABLE` | `raid_assign_subgroup(raid_id: id, member: id, subgroup: int, idempotency_key: string)` | `meta` | raid mutation count must satisfy `max_raid_mutations_per_rule` and `max_raid_size`. |
| `raid_set_lockout` | `DURABLE` | `raid_set_lockout(actor: id, lockout_id: string, expires_at_ms: int, idempotency_key: string)` | `meta` | lockout updates must satisfy `max_raid_mutations_per_rule`. |
| `pvp_queue_join` | `DURABLE` | `pvp_queue_join(actor: id, queue_id: string, idempotency_key: string)` | `meta` | queue operations must satisfy `max_pvp_queue_ops_per_rule`. |
| `pvp_queue_leave` | `DURABLE` | `pvp_queue_leave(actor: id, queue_id: string, idempotency_key: string)` | `meta` | duplicate-safe leave semantics required. |
| `pvp_report_result` | `DURABLE` | `pvp_report_result(match_id: id, winning_side: string, payload: record, idempotency_key: string)` | `meta` | result reports must satisfy `max_pvp_result_reports_per_rule`. |
| `txn_begin` | `DURABLE` | `txn_begin(txn_type: string, key: string)` | `meta` | One active transaction scope per rule evaluation. |
| `txn_confirm` | `DURABLE` | `txn_confirm(key: string)` | `meta` | Must reference existing transaction key. |
| `txn_compensate` | `DURABLE` | `txn_compensate(key: string, reason: string)` | `meta` | Must reference existing transaction key. |

## 5.5 Determinism and Utility Symbols

| Symbol | Class | Signature | Allowed Contexts | Notes |
|---|---|---|---|---|
| `fixed` | `PURE` | `fixed(value: string) -> fixed` | all | Canonical fixed parser for deterministic numeric form. |
| `clamp_fixed` | `PURE` | `clamp_fixed(v: fixed, min_v: fixed, max_v: fixed) -> fixed` | all | Deterministic pure arithmetic helper. |
| `min_int` | `PURE` | `min_int(a: int, b: int) -> int` | all | Deterministic pure arithmetic helper. |
| `max_int` | `PURE` | `max_int(a: int, b: int) -> int` | all | Deterministic pure arithmetic helper. |
| `formula_eval` | `PURE` | `formula_eval(formula_id: string, vars: record) -> fixed` | `edge`, `arbiter`, `meta` | `formula_id` must exist in deterministic registry and satisfy `max_formula_ops_per_eval`. |
| `formula_damage` | `PURE` | `formula_damage(formula_id: string, source: id, target: id, coeff: fixed, damage_type: string) -> fixed` | `arbiter` | deterministic damage value only; mutation requires explicit mutator call. |
| `formula_heal` | `PURE` | `formula_heal(formula_id: string, source: id, target: id, coeff: fixed) -> fixed` | `arbiter` | deterministic heal value only; mutation requires explicit mutator call. |
| `canonical_sort_ids` | `PURE` | `canonical_sort_ids(values: list<id>, max_len: int) -> list<id>` | `arbiter`, `meta` | `max_len` literal required; input length must be bounded. |

## 5.6 Observability Symbols

| Symbol | Class | Signature | Allowed Contexts | Notes |
|---|---|---|---|---|
| `log_reject` | `OBS` | `log_reject(code: string, detail: string)` | `edge`, `arbiter`, `meta` | Lowers to structured observability event only. |
| `metric_count` | `OBS` | `metric_count(name: string, value: int)` | `edge`, `arbiter`, `meta` | Does not alter gameplay state. |

## 6. Explicitly Forbidden Symbol Families

The following categories MUST fail compile-time admission in rule source:

1. Lua base dynamic loaders (`load`, `loadfile`, `dofile`, `require`).
2. Lua randomness/time APIs (`math.random`, `os.time`, `os.clock`) in
   authoritative paths.
3. File/network/process APIs (`io.*`, `os.execute`, socket bindings).
4. Reflection/metatable mutation (`debug.*`, `setmetatable`, `getmetatable`).
5. Any non-whitelisted global symbol.

## 7. Boundedness Profile Keys

The compiler MUST require the following profile keys for whitelist enforcement:

1. `selector_max_targets`
2. `max_mutations_per_rule`
3. `max_internal_emits_per_rule`
4. `max_durable_emits_per_rule`
5. `max_spawns_per_rule`
6. `max_rule_statements`
7. `max_expression_depth`
8. `max_local_bindings_per_rule`
9. `max_formula_ops_per_eval`
10. `max_formula_input_fields`
11. `max_stat_modifiers_per_entity`
12. `max_mail_attachments_per_message`
13. `max_mail_payload_bytes`
14. `max_interactions_per_rule`
15. `max_terrain_queries_per_rule`
16. `max_trigger_chain_steps_per_rule`
17. `max_housing_mutations_per_rule`
18. `max_housing_items_per_plot`
19. `max_ai_state_transitions_per_rule`
20. `max_ai_target_updates_per_rule`
21. `max_recipe_ingredient_entries`
22. `max_craft_output_entries_per_recipe`
23. `max_craft_queue_ops_per_rule`
24. `max_spell_effect_ops_per_cast`
25. `max_skill_activations_per_rule`
26. `max_talent_mutations_per_rule`
27. `max_skill_xp_grants_per_rule`
28. `max_party_mutations_per_rule`
29. `max_raid_mutations_per_rule`
30. `max_pvp_queue_ops_per_rule`
31. `max_pvp_result_reports_per_rule`
32. `max_party_size`
33. `max_raid_size`

If required bounds are missing, compilation MUST fail closed.

## 8. Admission Algorithm (Normative)

For each call expression in Lua source:

1. Resolve symbol in whitelist.
2. Validate arity.
3. Validate argument types and literal-domain constraints.
4. Validate context policy against enclosing rule context.
5. Validate boundedness predicates and counters for the enclosing rule.
6. Lower to canonical IR operation with normalized numeric fields.

Any failed step MUST terminate with deterministic compile diagnostics.

## 9. Required Diagnostics

Compiler MUST emit at least:

1. `LUA_API_UNKNOWN_SYMBOL`
2. `LUA_API_CONTEXT_FORBIDDEN`
3. `LUA_API_ARITY_MISMATCH`
4. `LUA_API_ARG_TYPE_MISMATCH`
5. `LUA_API_ARG_DOMAIN_VIOLATION`
6. `LUA_API_UNBOUNDED_SELECTOR`
7. `LUA_API_MUTATION_BUDGET_EXCEEDED`
8. `LUA_API_EMIT_BUDGET_EXCEEDED`
9. `LUA_API_DURABLE_POLICY_VIOLATION`
10. `LUA_API_FORMULA_UNKNOWN`
11. `LUA_API_FORMULA_UNBOUNDED`
12. `LUA_API_STAT_MODIFIER_BUDGET_EXCEEDED`
13. `LUA_API_MAILBOX_POLICY_VIOLATION`
14. `LUA_API_INTERACTION_POLICY_VIOLATION`
15. `LUA_API_TERRAIN_QUERY_BUDGET_EXCEEDED`
16. `LUA_API_HOUSING_POLICY_VIOLATION`
17. `LUA_API_AI_POLICY_VIOLATION`
18. `LUA_API_AI_BUDGET_EXCEEDED`
19. `LUA_API_CRAFTING_POLICY_VIOLATION`
20. `LUA_API_CRAFTING_BUDGET_EXCEEDED`
21. `LUA_API_SPELL_POLICY_VIOLATION`
22. `LUA_API_SKILL_POLICY_VIOLATION`
23. `LUA_API_TALENT_POLICY_VIOLATION`
24. `LUA_API_SPELL_BUDGET_EXCEEDED`
25. `LUA_API_SKILL_BUDGET_EXCEEDED`
26. `LUA_API_TALENT_BUDGET_EXCEEDED`
27. `LUA_API_PARTY_POLICY_VIOLATION`
28. `LUA_API_RAID_POLICY_VIOLATION`
29. `LUA_API_PVP_POLICY_VIOLATION`
30. `LUA_API_PARTY_BUDGET_EXCEEDED`
31. `LUA_API_RAID_BUDGET_EXCEEDED`
32. `LUA_API_PVP_BUDGET_EXCEEDED`

## 10. Forward Compatibility Rules

1. Adding a new symbol is backward-compatible.
2. Removing a symbol or changing signature/semantics is breaking.
3. Breaking changes MUST bump language profile minor/major per project policy.
4. Compiler SHOULD support dual-profile validation windows during migrations.
