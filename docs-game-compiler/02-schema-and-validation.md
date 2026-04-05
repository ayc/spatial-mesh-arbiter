# Schema and Validation

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define the authorable schemas for game content — what designers write — and the validation rules applied before compilation. This document is the "front door" of the compiler pipeline (`03-compiler-pipeline.md`): it specifies valid input.

---

## 1. Canonical Schema Rules

1. Every authorable type MUST have explicit schema versioning.
2. Required fields MUST be explicit and machine-validated.
3. Unknown fields MUST be rejected (no silent passthrough).
4. Numeric fields that affect authoritative mutation MUST include scale semantics.
5. Enum fields MUST reference a closed, compile-time-known domain.
6. All schemas MUST be expressible in both YAML and the Lua-subset grammar (`01-designer-language.md`). Equivalent definitions in either format MUST produce identical IR.

## 2. Validation Tiers

1. **Structural validation:** Shape, types, required fields, enum domains.
2. **Semantic validation:** Reference integrity (IDs exist), constraint satisfaction (range > 0), cross-field consistency.
3. **Determinism validation:** Banned constructs, bounded collections, numeric normalization to `I32F32`.
4. **Compatibility validation:** Adapter API major version, wire schema version intersections.

## 3. Compile Gate

Compilation MUST fail closed if any required validation tier fails. Diagnostics MUST identify the failing tier, schema, field, and rule.

---

## 4. Authorable Content Types

Game content is organized into these top-level authorable types, corresponding to the module layout in `01-designer-language.md` §3.2:

| Content Type | Module | Description |
|-------------|--------|-------------|
| AbilityDefinition | `rules` | A castable ability — the primary compilation unit |
| EntityDefinition | `entities` | An entity archetype (player class, monster, summon) |
| StatusEffectDefinition | `tables` | A buff, debuff, or CC effect |
| RuntimeStateDefinition | `tables` | A bounded per-entity runtime state slot used by reactivation, combos, charges, and temporal recall |
| TriggerDefinition | `rules` | A reactive hook registration (on-hit, on-death, etc.) |
| ComboMatrixDefinition | `tables` | Combo field × finisher lookup table |
| FormulaDefinition | `tables` | A deterministic numeric formula |

The following sections define each schema.

---

## 5. AbilityDefinition Schema

An ability is the primary compilation unit. Each ability compiles into one `AbilityIRBlock` (`03-1-compiler-ir-specification.md` §1).

### 5.1 Metadata Fields

| Field | Type | Required | Default | IR Target | Validation |
|-------|------|----------|---------|-----------|------------|
| `ability_id` | `string` | YES | — | `AbilityIRBlock.ability_id` | Must be unique across all abilities. |
| `cooldown` | `fixed` | YES | — | `AbilityIRBlock.cooldown_ticks` | Must be > 0. Converted to ticks at 60Hz. |
| `resource_cost` | `ResourceCost` | NO | none | `AbilityIRBlock.resource_pool` + `AbilityIRBlock.resource_cost` | Pool ID must reference a valid resource pool. |
| `cast_time` | `fixed` | NO | `0` | `AbilityIRBlock.cast_time_ticks` | Must be >= 0. Converted to ticks. |
| `input_mode` | `InputModeBlock` | NO | `{ type: instant }` | `AbilityIRBlock.input_mode` | Hold-release modes MUST declare bounded charge timing and release policy. |
| `targeting` | `TargetingBlock` | YES | — | IR instructions (P-09/P-13) | See §5.2. |
| `self_cc_immunity_during_cast` | `enum` | NO | `none` | `AbilityIRBlock.self_cc_immunity_during_cast` | One of: `none`, `push_immune`, `full_super_armor`. |
| `can_counter_vulnerability_window` | `bool` | NO | `false` | `AbilityIRBlock.can_counter_vulnerability_window` | P-65: flags ability as eligible to trigger vulnerability-window counters. |
| `can_be_counterspelled` | `bool` | NO | `true` | `AbilityIRBlock.can_be_counterspelled` | P-40: this ability can be counterspelled mid-cast. |
| `combo_finisher` | `enum` | NO | `none` | `AbilityIRBlock.combo_finisher` | One of: `none`, `projectile`, `blast`, `whirl`, `leap`. |
| `group_interaction_tags` | `list<string>` | NO | none | Ability metadata | Tags matched by sequential group-interaction steps. |
| `requires_concentration` | `bool` | NO | `false` | `AbilityIRBlock.requires_concentration` | P-55: maintained effect. |
| `channel` | `ChannelBlock` | NO | none | `AbilityIRBlock.channel` | Only valid when `cast_time > 0`. |
| `concentration` | `ConcentrationBlock` | NO | Canonical defaults when `requires_concentration = true` | `AbilityIRBlock.concentration` | Only valid when `requires_concentration = true`. |
| `global_event` | `GlobalEventBlock` | NO | none | `AbilityIRBlock.global_event` | Only valid for controller-escalated `P-46` execution. |
| `vulnerability_window` | `VulnerabilityWindowBlock` | NO | none | `IRDirective(P-65)` | Only valid on abilities with a bounded cast/attack window. |
| `group_interaction` | `GroupInteractionBlock` | NO | none | `IRDirective(P-54)` | Opens a bounded group interaction session. |
| `split_form` | `SplitFormBlock` | NO | none | `IRDirective(P-30)` + compiler-owned reform session | References multiple spawned member bindings, suspends the original body, and installs one single-selection split-form group. |
| `stagger_damage` | `fixed` | NO | `0` | IR instruction params | P-48: parallel stagger damage. |

`self_cc_immunity_during_cast` is authoring sugar for a temporary positive status applied for the cast
window. `push_immune` lowers to `cc_immunity_categories = [displacement]`. `full_super_armor`
lowers to a temporary status that grants immunity to every canonical CC category.

### 5.1.1 ResourceCost

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `pool` | `string` | YES | — |
| `amount` | `fixed` | YES | — |
| `escalation` | `CostEscalationBlock` | NO | none |

If `escalation` is omitted, the ability uses a fixed base cost. If `escalation` is present, the
compiler lowers the base `pool` + `amount` plus the escalation policy into the Stage 2 `P-51`
desperation-cost contract.

### 5.1.2 CostEscalationBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `multiplier_per_stack` | `fixed` | YES | — |
| `decay_interval_ticks` | `int` | YES | — |
| `max_stacks` | `int` | NO | uncapped |
| `shared_counter_id` | `string` | NO | owning `ability_id` |

Lowering rule: the compiler materializes a bounded per-entity escalation counter keyed by
`shared_counter_id`. During Stage 2, `P-51` computes
`effective_cost = amount * multiplier_per_stack ^ current_stacks` before affordability checks. The
counter increments only if the cast commits successfully. If the owning entity does not cast any
ability sharing that counter for `decay_interval_ticks`, one stack decays; decay repeats one stack
at a time until the counter reaches zero or the entity casts again.

### 5.2 TargetingBlock

Defines who the ability affects. Compiles to TargetResolution-stage instructions.

| Field | Type | Required | Default | Primitive Mapping |
|-------|------|----------|---------|-------------------|
| `type` | `enum` | YES | — | Determines instruction pattern |
| `range` | `fixed` | YES | — | Query radius / max distance |
| `filter` | `FilterExpr` | NO | `enemy_alive` | P-13 (Tag/Allegiance Filtering) |
| `shape` | `enum` | When type=`area` | — | P-09 shape parameter (`circle`, `box`, `cone`, `ring`) |
| `radius` | `fixed` | When shape is set | — | P-09 shape dimension |
| `cone_angle` | `fixed` | When shape=`cone` | — | P-09 cone half-angle |
| `ring_inner` | `fixed` | When shape=`ring` | — | P-09 ring inner radius |
| `max_targets` | `int` | NO | `selector_max_targets` | Result cap. MUST be <= `selector_max_targets`. |
| `facing_check` | `fixed` | NO | none | P-12 dot-product threshold |

Targeting `type` enum:

| Value | Meaning | IR Pattern |
|-------|---------|------------|
| `single_target` | One entity | P-13 filter only |
| `area` | Ground-targeted AoE | P-09 + P-13 |
| `self` | Caster only | No targeting instruction |
| `none` | No target (passive) | No targeting instruction |
| `cone` | Directional cone from caster | P-09 (cone) + P-12 + P-13 |
| `line` | Raycast from caster | P-10 + P-13 |
| `chain` | Bounce to N nearest | P-11 + P-13 |

### 5.3 Effects List

An ability contains an ordered list of effects. Each effect compiles to one or more IR instructions.

```yaml
effects:
  - type: damage
    target: target
    amount: 150
    damage_type: physical
  - type: displacement
    target: target
    destination: cursor_position
    arc: true
    duration_ticks: 30
```

See §6 for per-effect-type schemas.

### 5.4 Requirements List

Pre-conditions checked during IntentValidation. Compile to P-26 directives or IntentValidation-stage instructions.

```yaml
requirements:
  - capability: can_cast        # P-26
  - capability: can_move         # P-26 (for movement abilities)
  - resource: { pool: mana, amount: 75 }
```

### 5.5 Triggers List

Reactive hooks registered by the ability. See §8 TriggerDefinition.

```yaml
triggers:
  - hook: on_hit
    condition: { crit: true }   # Guard: only on crit
    effects:
      - type: aoe_damage
        center: target
        shape: circle
        radius: 4.0
        amount: 50
```

### 5.6 InputModeBlock

Defines how the Edge/Arbiter pair turns player input into an authoritative ability activation.

| Field | Type | Required | Default | Applies When |
|-------|------|----------|---------|--------------|
| `type` | `enum` | YES | — | Always |
| `max_charge_ticks` | `int` | When `type = hold_release` | — | P-43 |
| `min_charge_ticks` | `int` | NO | `0` | P-43 |
| `move_speed_multiplier_while_holding` | `fixed` | NO | `1.0` | P-26 while `type = hold_release` |
| `blocks_other_abilities` | `bool` | NO | `true` | P-26 while `type = hold_release` |
| `retains_max_charge_until_release` | `bool` | NO | `true` | P-43 |

`type` enum:

- `instant`
- `hold_release`

`hold_release` abilities begin with the ordinary discrete cast intent for the ability's targeting
shape (`TargetedAbility`, `GroundTargetedAbility`, or `SpawnProjectile`). The Edge Node MAY predict
the charging bar locally, but the Arbiter MUST stamp the authoritative hold start tick. Release is
derived from the authoritative held-button transition in continuous `SimulationInput` for the same
ability slot; this contract does NOT introduce a new external intent variant. On handoff, the
current hold state transfers with the entity. When release is observed, the runtime clamps the
authoritative charge duration into `[min_charge_ticks, max_charge_ticks]` and feeds that into P-43,
using the latest accepted aim/cursor state for the final shot direction/placement.

### 5.7 ActivationModes

Optional guarded variants that override the base ability's targeting/requirements/effects when
runtime-state predicates match. This is the canonical authoring surface for same-key reactivation,
multi-step combo routing, and state-aware charge spenders.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `when` | `StatePredicate` | YES | — |
| `targeting` | `TargetingBlock` | NO | Inherit base ability targeting |
| `requirements` | `list<Requirement>` | NO | Inherit base ability requirements |
| `resource_cost` | `ResourceCost` | NO | Inherit base ability resource cost |
| `cooldown` | `fixed` | NO | Inherit base ability cooldown |
| `effects` | `EffectList` | YES | — |

Evaluation rule: activation modes are checked in authored order during IntentValidation. The first
matching mode wins. If no mode matches, the base ability definition (`targeting`, `requirements`,
and `effects`) is used as the default mode.

Typical uses:

- Reactivation: `{ state_present: shadow_step_bookmark }`
- Combo routing: `{ sequence_step: { state_id: combo_q, step: 2 } }`
- Finisher gating: `{ charge_count: { state_id: martial_charge_pool, op: gte, value: 1 } }`

### 5.8 ChannelBlock

Defines a bounded maintained cast that exists for the duration of `cast_time`. This is the
canonical authoring surface for interruptible channels, continuous steering casts, and
"complete-after-X-seconds" cast bars.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `execution_mode` | `enum` | NO | `complete_only` |
| `tick_interval_ticks` | `int` | NO | `1` |
| `movement_lock` | `enum` | NO | `root` |
| `allow_other_abilities` | `bool` | NO | `false` |
| `continuous_input` | `enum` | NO | `none` |
| `break_on_displacement` | `bool` | NO | `true` |
| `break_on_target_invalid` | `bool` | NO | `true` |
| `interrupt_on_damage_above` | `fixed` | NO | none |
| `partial_cooldown_refund` | `fixed` | NO | `0` |

`execution_mode` enum:

- `complete_only`
- `tick_while_active`

`movement_lock` enum:

- `none`
- `root`

`continuous_input` enum:

- `none`
- `steer_aim`
- `steer_target_movement`

Validation rules:

1. `cast_time` MUST be non-zero when `channel` is present.
2. `tick_interval_ticks > 0` when `execution_mode = tick_while_active`.
3. `continuous_input != none` requires `execution_mode = tick_while_active`.
4. `partial_cooldown_refund` MUST be in `[0, 1]`.
5. If present, `interrupt_on_damage_above > 0`.

Lowering rule:

- `complete_only` keeps the normal cast-time contract: the root `effects` list resolves once at
  successful completion and does NOT resolve if the channel breaks early.
- `tick_while_active` re-evaluates the root `effects` list every `tick_interval_ticks` while the
  channel remains active, beginning in the same tick after cast admission. This is the canonical
  lowering path for steerable beams and channel-owned aura/control effects.
- Any persistent outputs created by a channel-owned cast instance are tagged to that channel
  instance and are removed or reverted automatically if the channel breaks or ends.

### 5.9 ConcentrationBlock

Extends `requires_concentration = true` with explicit mutual-exclusion and break policy. This is
the canonical authoring surface for maintained effects that survive ordinary movement and
non-concentration ability use.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `check_formula` | `enum` | NO | `standard_half_damage_floor_10` |
| `max_duration_ticks` | `int` | NO | none |
| `allow_manual_cancel` | `bool` | NO | `true` |
| `replace_existing` | `bool` | NO | `true` |

`check_formula` enum:

- `standard_half_damage_floor_10`

Validation rules:

1. `concentration` is only valid when `requires_concentration = true`.
2. `channel` and `requires_concentration` MUST NOT both be set on the same ability.
3. If present, `max_duration_ticks > 0`.

Lowering rule: the caster owns exactly one active concentration slot. If
`replace_existing = true`, beginning a new concentration cast tears down the previous
concentration-owned persistent outputs before installing the new ones. On each committed damage
event to the owner, `P-55` evaluates the deterministic concentration check. On failure, manual
cancel, owner removal, or `max_duration_ticks` expiry, the runtime removes all persistent outputs
owned by that concentration instance. Concentration does not root the caster and does not block
non-concentration abilities.

### 5.10 GlobalEventBlock

Defines controller-escalated deterministic execution through `P-46 (Global Event Scheduler)`. This
is the canonical authoring surface for mesh-wide cast completion effects such as `SK-05 Global
Strike`.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `schedule_lead_ticks` | `int` | YES | — |
| `filter` | `FilterExpr` | YES | — |
| `target_class` | `enum` | NO | `all_entities` |
| `geometry` | `enum` | NO | `whole_mesh` |
| `epicenter` | `PositionRef` | NO | `caster_position` |
| `radius` | `fixed` | When `geometry = circle` or `ring` | — |
| `ring_inner` | `fixed` | When `geometry = ring` | — |
| `pulse_interval_ticks` | `int` | NO | none |
| `duration_ticks` | `int` | NO | none |
| `cancel_if_owner_removed` | `bool` | NO | `true` |

`target_class` enum:

- `all_entities`
- `heroes_only`
- `structures_only`

`geometry` enum:

- `whole_mesh`
- `circle`
- `ring`

Validation rules:

1. `schedule_lead_ticks > 0`.
2. `targeting.type` MUST be `none` or `self` when `global_event` is present. Local targeting is
   not used for the controller-escalated fan-out path.
3. `radius > 0` when `geometry = circle` or `ring`.
4. `ring_inner >= 0` and `ring_inner < radius` when `geometry = ring`.
5. `pulse_interval_ticks > 0` when present.
6. `duration_ticks > 0` when present.
7. `pulse_interval_ticks` and `duration_ticks` MUST either both be present or both be omitted.

Lowering rule: `global_event` emits a `P-46` scheduling directive at Stage 11 only after the cast
instance commits successfully. Broken/interrupted channels do NOT schedule the event. At schedule
time, the caster's authoritative Arbiter captures the ability ID, data epoch, baked offense-side
context, compiled `filter` / `target_class` / geometry policy, and `execute_at_tick =
current_tick + schedule_lead_ticks`, then escalates that payload to the Mesh Controller. At the
coordinated execute tick, every Arbiter evaluates the event locally against its OWN currently
authoritative entities: it applies the geometry gate, filters by `filter` + `target_class`, and
then resolves the ability's root `effects` list independently against each admitted target. This
means newly spawned or newly arrived valid targets CAN be hit if they match at execute time, while
entities that no longer exist or no longer match are skipped. If `pulse_interval_ticks` and
`duration_ticks` are present, the controller schedules a periodic global event window using the
same baked offense context for each pulse.

### 5.11 VulnerabilityWindowBlock

Defines a timed counter window emitted by the broadcasting ability itself. This is the canonical
authoring surface for boss-style counterable attacks (`P-65`).

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `start_offset_ticks` | `int` | YES | — |
| `duration_ticks` | `int` | YES | — |
| `bonus_damage` | `fixed` | YES | — |
| `bonus_damage_type` | `enum` | YES | — |
| `stagger_duration_ticks` | `int` | YES | — |
| `vulnerability_bonus` | `fixed` | NO | `0` |
| `consume_on_first_counter` | `bool` | NO | `true` |
| `interrupt_current_cast` | `bool` | NO | `true` |

Validation rules:

1. `start_offset_ticks >= 0`.
2. `duration_ticks > 0`.
3. `cast_time` MUST be non-zero when `vulnerability_window` is present.
4. `start_offset_ticks + duration_ticks` MUST be `<= cast_time_ticks` after normalization.

Lowering rule: the compiler emits a `P-65` directive attached to the broadcasting ability. When an
incoming hit from an ability with `can_counter_vulnerability_window = true` lands during the open
window, the target's current cast is interrupted if `interrupt_current_cast = true`, the authored
bonus damage resolves through the normal damage pipeline, and the runtime applies a generated
mechanical stagger state for `stagger_duration_ticks` plus the authored `vulnerability_bonus`. This
counter-generated stagger is a mechanical boss-check state, not ordinary authored CC, and is NOT
shortened by status resistance or DR.

### 5.12 GroupInteractionBlock

Declares a bounded `P-54` group interaction session opened by this ability.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `participant_scope` | `enum` | YES | — |
| `mode` | `enum` | YES | — |
| `timeout_ticks` | `int` | YES | — |
| `participant_order` | `enum` | NO | `party_slot` |
| `sequential` | `GroupSequentialBlock` | When `mode = sequential` | — |
| `simultaneous` | `GroupSimultaneousBlock` | When `mode = simultaneous` | — |

`participant_scope` enum:

- `party`
- `raid_subgroup`

`mode` enum:

- `sequential`
- `simultaneous`

`participant_order` enum:

- `party_slot`
- `raid_subgroup_slot`
- `entity_id`

Validation rules:

1. `timeout_ticks > 0`.
2. Exactly one of `sequential` or `simultaneous` MUST be present according to `mode`.

Lowering rule: `group_interaction` emits one `P-54` session-opening directive only after the
opening ability commits successfully. The session snapshots the expected participant set from the
authored scope, publishes group UI for those participants, accepts bounded contributions until the
deadline, and then resolves one authored result path.

### 5.12.1 GroupSequentialBlock

Declares an ordered role/tag contribution chain. Participants advance the session by using ordinary
abilities whose `group_interaction_tags` match the current step.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `steps` | `list<GroupSequenceStepDef>` | YES | — |
| `success_result` | `GroupResultBlock` | YES | — |
| `failure_result` | `GroupResultBlock` | NO | none |

### 5.12.2 GroupSequenceStepDef

| Field | Type | Required |
|-------|------|----------|
| `required_role_id` | `string` | YES |
| `required_ability_tag` | `string` | YES |
| `time_limit_ticks` | `int` | YES |

Validation rules:

1. `steps` MUST NOT be empty.
2. Every `time_limit_ticks > 0`.

### 5.12.3 GroupSimultaneousBlock

Declares a one-shot simultaneous choice window where each participant selects exactly one option
before the deadline.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `options` | `list<string>` | YES | — |
| `default_option_id` | `string` | YES | — |
| `allow_reselection` | `bool` | NO | `true` |
| `ordered_patterns` | `list<GroupOrderedPatternDef>` | NO | none |
| `count_patterns` | `list<GroupCountPatternDef>` | YES | — |

Validation rules:

1. `options` MUST NOT be empty.
2. `options` MUST be unique.
3. `default_option_id` MUST be one of `options`.
4. `count_patterns` MUST NOT be empty.

### 5.12.4 GroupOrderedPatternDef

| Field | Type | Required |
|-------|------|----------|
| `option_sequence` | `list<string>` | YES |
| `result` | `GroupResultBlock` | YES |

Validation rules:

1. `option_sequence` MUST NOT be empty.
2. Every `option_sequence` entry MUST be present in `simultaneous.options`.

### 5.12.5 GroupCountPatternDef

| Field | Type | Required |
|-------|------|----------|
| `required_counts` | `list<GroupOptionCountDef>` | YES |
| `result` | `GroupResultBlock` | YES |

Validation rules:

1. `required_counts` MUST NOT be empty.
2. `required_counts.option_id` values MUST be unique within one pattern.

### 5.12.6 GroupOptionCountDef

| Field | Type | Required |
|-------|------|----------|
| `option_id` | `string` | YES |
| `count` | `int` | YES |

Validation rules:

1. `count > 0`.
2. `option_id` MUST be present in `simultaneous.options`.

### 5.12.7 GroupResultBlock

Declares the effect payload resolved when a group interaction succeeds, fails, or matches a pattern.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `apply_to` | `enum` | NO | `all_participants` |
| `effects` | `EffectList` | YES | — |

`apply_to` enum:

- `all_participants`
- `trigger_owner`

If `apply_to = all_participants`, the runtime executes `effects` once per participant with
implicit `participant` / `participant_position` bindings available to the effect resolver.

### 5.13 SplitFormBlock

Declares a bounded one-controller / many-spawned-members split-form session that suspends the
original body, routes inputs to exactly one active member at a time, and later reforms or kills the
stored owner deterministically.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `controller` | `EntityRef` | NO | `caster` |
| `member_bindings` | `list<string>` | YES | — |
| `inactive_mode` | `enum` | NO | `hold_position` |
| `follow_distance` | `fixed` | When `inactive_mode = follow_active` | — |
| `leash_radius` | `fixed` | NO | none |
| `reactivation_behavior` | `enum` | NO | `reform_owner` |
| `restore_position` | `enum` | When `reactivation_behavior = reform_owner` | `active_member_position` |
| `restore_hp_policy` | `enum` | When `reactivation_behavior = reform_owner` | `sum_alive_members_cap_original_max` |
| `on_all_members_removed` | `enum` | NO | `kill_owner` |

`inactive_mode` enum:

- `hold_position`
- `follow_active`

`reactivation_behavior` enum:

- `reform_owner`
- `ignore`

`restore_position` enum:

- `active_member_position`
- `original_owner_position`

`restore_hp_policy` enum:

- `preserve_stored_owner`
- `active_member_ratio`
- `sum_alive_members_cap_original_max`

`on_all_members_removed` enum:

- `kill_owner`

Validation rules:

1. `member_bindings` MUST contain between `2` and `max_multiplex_group_size` entries.
2. `member_bindings` entries MUST be unique.
3. Every `member_bindings` entry MUST resolve to a prior `spawn_actor.output_binding` in the same
   ability.
4. Every referenced `spawn_actor` MUST have `count = 1`.
5. `follow_distance >= 0` when `inactive_mode = follow_active`.
6. `leash_radius > 0` when authored.

Lowering rule: `split_form` opens one compiler-owned split session only after every referenced
member spawn commits successfully. The runtime stores and suspends the original owner's body,
installs one `P-30` `OneToMany + AdapterRouted` routing group over the referenced members, and
treats the first surviving binding in authored order as the initial active member. Exactly one
member receives direct movement/ability proposals at a time. When `inactive_mode = follow_active`,
inactive members run a bounded follow loop toward the current active member using the authored
distance/leash settings and ordinary Ghost-backed pose sampling across seams. Re-casting the same
public ability while the split session is active resolves `reactivation_behavior`; `reform_owner`
despawns all surviving members and restores the stored owner using the selected position / HP
policy. If every member is removed first, `kill_owner` discards the stored owner snapshot and
triggers terminal death on the original owner.

### 5.14 Full Example: SK-01 (Toss) in YAML

```yaml
ability:
  ability_id: toss
  cooldown: 10.0
  resource_cost: { pool: mana, amount: 75 }
  cast_time: 0
  targeting:
    type: single_target
    range: 8.0
    filter: enemy_alive
  can_be_counterspelled: false
  requirements:
    - capability: can_cast
  effects:
    - type: displacement
      target: target
      destination: cursor_position
      arc: true
      duration_ticks: 30
      max_distance: 8.0
      output_binding: landing_pos
    - type: damage
      target: target
      amount: 150
      damage_type: physical
    - type: aoe_damage
      center: { binding: landing_pos }
      shape: circle
      radius: 3.0
      filter: enemy_alive
      amount: 100
      damage_type: physical
```

---

## 6. Effect Type Schemas

Each effect type maps to specific primitives and IR instructions.

### 6.1 `damage`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `amount` | `fixed` | YES | P-15 (Value Modification) |
| `damage_type` | `enum` | YES | Combat context parameter |
| `scaling` | `ScalingExpr` | NO | P-16 (Stat Layering) for coefficient |

### 6.2 `heal`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `amount` | `fixed` | YES | P-15 (Value Modification) |
| `scaling` | `ScalingExpr` | NO | P-16 |

### 6.3 `aoe_damage` / `aoe_heal`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `center` | `PositionRef` | YES | P-09 (Shape Overlap) |
| `shape` | `enum` | YES | P-09 shape param |
| `radius` | `fixed` | YES | P-09 radius param |
| `filter` | `FilterExpr` | NO | P-13 |
| `amount` | `fixed` | YES | P-15 |
| `max_targets` | `int` | NO | Result cap |

If `center` references a binding from a kinematic effect (e.g., `landing_pos`), the compiler MUST place the P-09 query at PostKinematic, not TargetResolution.

### 6.4 `displacement`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `destination` | `PositionRef` | YES | P-02 (Forced Displacement) or P-01 (Instant Translation) |
| `arc` | `bool` | NO | P-02 arc parameter |
| `duration_ticks` | `int` | When arc | P-02 duration |
| `max_distance` | `fixed` | NO | Kinematic clamp |
| `output_binding` | `string` | NO | Exposes resolved landing position for downstream effects |
| `is_teleport` | `bool` | NO | If true, uses P-01 instead of P-02 |
| `flight_policy` | `KinematicFlightBlock` | NO | P-07-style collision/hit policy while the displaced entity is in flight |

### 6.4.1 KinematicFlightBlock

Declares projectile-like collision behavior for an entity being moved by `displacement`.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `collision_radius` | `fixed` | YES | — |
| `unique_hit_scope` | `enum` | NO | `entity_once_per_flight` |
| `continue_after_entity_hit` | `bool` | NO | `true` |
| `pass_through_effects` | `EffectList` | NO | none |
| `wall_impact_effects` | `EffectList` | NO | none |

`unique_hit_scope` enum:

- `none`
- `entity_once_per_flight`

Validation rules:

1. `collision_radius > 0`.
2. At least one of `pass_through_effects` or `wall_impact_effects` MUST be present.

Lowering rule: `displacement` with `flight_policy` compiles to ordinary `P-02` motion plus a
compiler-owned `P-07`-style kinematic-flight overlay. The displaced entity carries a bounded
per-flight hit ledger, evaluates overlap against new entities using `collision_radius`, emits
`pass_through_effects` for newly admitted hits, and emits `wall_impact_effects` when the flight
stops on world collision. The flight overlay survives handoff as ordinary displacement SoftState.

### 6.5 `apply_cc`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `cc_type` | `enum` | YES | P-26 (Capability Bitmask) |
| `category` | `enum` | YES | P-62 (CC Immunity) category check |
| `duration_ticks` | `int` | YES | Status duration |
| `dr_category` | `enum` | NO | P-41 (DR Tracker) category |
| `duration_scaling` | `enum` | NO | Default `status_resistance`; controls whether the target's `status_effect_resistance` shortens the admitted duration |
| `is_cleansable` | `bool` | NO | Default true. Participates in generic `cleanse` filters. |
| `on_expire_effects` | `EffectList` | NO | Lowered onto the generated status entry and emitted when the CC expires or breaks |

`cc_type` enum: `stun`, `root`, `silence`, `sleep`, `disarm`, `blind`, `fear`, `charm`, `taunt`, `berserk`, `mute`.

`category` enum (for immunity checking): `displacement`, `hard_disable`, `soft_disable`, `forced_movement`, `target_override`, `mute`.

`duration_scaling` enum:

- `fixed`
- `status_resistance`

Compiler lowering rule: `apply_cc` MUST compile to a generated negative status entry in the target's active status registry. The generated entry carries the authored `duration_ticks`, `category`, capability suppression/steering semantics for the selected `cc_type`, and the authored `is_cleansable` value. This allows generic `cleanse` effects and status-application immunity checks to treat crowd control the same way they treat authored debuffs.

### 6.5.1 Canonical `cc_type` Profiles

The `cc_type` selects a **normative runtime behavior profile**. The compiler MUST reject any
`cc_type` / `category` pairing that conflicts with this table.

| `cc_type` | Canonical category | Generated behavior |
|-----------|--------------------|--------------------|
| `stun` | `hard_disable` | Suppress `CAN_MOVE`, `CAN_ATTACK`, and `CAN_CAST`; interrupt active casts/channels on admission |
| `root` | `soft_disable` | Suppress `CAN_MOVE`; movement abilities are blocked because relocation abilities MUST require `can_move` in `requirements` |
| `silence` | `soft_disable` | Suppress `CAN_CAST`; interrupt active casts/channels on admission |
| `sleep` | `hard_disable` | Same suppression as `stun`; breaks after any non-zero committed damage instance |
| `disarm` | `soft_disable` | Suppress `CAN_ATTACK` only |
| `blind` | `soft_disable` | Engine-owned auto-attacks resolve as `Miss` before `CombatContext` generation; authored ability casts are unaffected |
| `fear` | `forced_movement` | Suppress attacks and casts; emit deterministic movement steering away from the source each tick |
| `charm` | `forced_movement` | Suppress attacks and casts; emit deterministic movement steering toward the source each tick |
| `taunt` | `target_override` | Force engine-owned auto-attacks to target the source while the source lives; ordinary ability casts keep their authored targets |
| `berserk` | `target_override` | Suppress voluntary movement and casts; force engine-owned auto-attacks against the nearest ally and authorize that attack's friendly-fire resolution |
| `mute` | `mute` | Clear `PASSIVES_ACTIVE`; passive statuses and passive item effects are suspended, not removed |

`taunt` carries an implicit source-death break condition. If the taunt source dies, the status
ends immediately. `sleep` break evaluation is profile-defined and does not require separate
authoring.

Slow-style effects and other clamp-only movement debuffs SHOULD be authored as negative
`StatusEffectDefinition` entries using `stat_modifiers`, `cc_category = soft_disable`, and
`duration_scaling = status_resistance`. They SHOULD NOT use `apply_cc` unless they also require one
of the canonical behavior profiles above.

### 6.6 `apply_buff` / `apply_debuff`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `status_id` | `string` | YES | References a StatusEffectDefinition |
| `duration_ticks` | `int` | YES | Status duration |
| `stacks` | `int` | NO | P-42 (Stacking Counters) |

Validation rule: `apply_buff` MUST reference a `StatusEffectDefinition` whose `polarity = positive`. `apply_debuff` MUST reference a `StatusEffectDefinition` whose `polarity = negative`.

### 6.6.1 `cleanse`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-66 (Status Effect Filter Mutation) |
| `polarity` | `enum` | NO | Default `negative` |
| `require_cleansable` | `bool` | NO | Default `true` |
| `cc_categories` | `list<enum>` | NO | Optional CC-only subset filter |

`polarity` enum: `negative`, `positive`, `all`.

Validation rules:

1. If authored, `cc_categories` entries MUST be unique.
2. `cc_categories` is only legal when `polarity != positive`, because canonical CC entries are
   always negative runtime statuses.

`cleanse` removes matching active status entries from the target's authoritative status registry in
a single mutation batch. Matching is driven by compiled status metadata, not string tags. If
`require_cleansable = true`, only statuses with `is_cleansable = true` are removed. If
`cc_categories` is authored, only matching entries whose compiled `cc_category` is in that set are
removed; ordinary non-CC negatives survive. Generated `apply_cc` statuses participate
automatically because they are lowered into the same runtime status registry. Abilities that also
grant an immunity window SHOULD follow `cleanse` with `apply_buff` of a positive status whose
`status_application_immunity` field declares what new statuses are blocked during the window, or
whose `cc_immunity_categories` field declares which CC categories are rejected during that window.

### 6.6.2 `consume_status`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-66 (Status Effect Filter Mutation) |
| `status_id` | `string` | YES | References a StatusEffectDefinition |
| `source_entity` | `EntityRef` | NO | Defaults to `caster` |
| `max_instances` | `int` | NO | Default all matches |
| `on_consume_effects` | `EffectList` | NO | Optional follow-up payload if at least one match was consumed |

Validation rules:

1. `status_id` MUST reference a valid `StatusEffectDefinition`.
2. If present, `max_instances > 0`.

`consume_status` is the canonical authoring surface for primer/detonator style "find matching
status instances from this source, remove them, then burst" mechanics. Matching is exact on
`status_id` plus the stored original source/applier identity, not on status polarity or
`is_cleansable`.

Lowering rule:

- The target's authoritative owner scans the active status registry for entries whose `status_id`
  matches and whose stored source identity equals `source_entity`.
- Matching entries are ordered by deterministic oldest-first application order.
- The runtime removes up to `max_instances` matches atomically as one registry mutation batch. If
  `max_instances` is omitted, it removes all matches.
- If at least one entry was removed, `on_consume_effects` is queued as one deferred follow-up
  payload against the SAME target context for the next tick. If no entry matched, the effect is a
  clean no-op.

### 6.6.3 `despawn_entity`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-32 runtime actor lifecycle |
| `reason` | `string` | NO | Optional authored removal label |

Validation rules:

1. `target` MUST resolve to a CURRENT-Arbiter authoritative non-root runtime actor (spawned actor,
   zone actor, projectile actor, shield actor, portal anchor, or equivalent compiler/runtime-owned
   actor state), not a root player / monster body.
2. `target` MUST NOT resolve to a corpse-registry entry.

`despawn_entity` is the canonical declarative removal surface for authored teardown of compiler-owned
runtime actors. It is the declarative counterpart to the existing Lua fallback helper of the same
name; root-body death/removal still uses the ordinary lifecycle, corpse, and Meta contracts instead.

Lowering rule:

- The target's current authoritative owner applies one deterministic actor-removal mutation in the
  current effect sequence.
- Later effects in the same authored list MUST NOT treat the removed actor as a live query target,
  but any contextual positions or bindings snapshotted before the removal remain valid for the rest
  of that list.

### 6.7 `spawn_actor`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `archetype_id` | `string` | YES | P-32 (Actor Spawning) |
| `position` | `PositionRef` | YES | Spawn location |
| `owner` | `EntityRef` | NO | Defaults to caster |
| `lifetime_ticks` | `int` | YES | Bounded actor duration |
| `count` | `int` | NO | Default 1. MUST be <= `max_spawns_per_rule`. |
| `placement` | `SpawnPlacementBlock` | NO | Optional deterministic expansion of one anchor into multiple spawn points (see §6.7.13) |
| `output_binding` | `string` | NO | Exposes the created actor ID for downstream state writes or follow-up effects |
| `projectile` | `ProjectileBlock` | NO | Projectile-specific fields (see §6.7.1) |
| `portal_anchor` | `PortalAnchorBlock` | NO | Optional P-59 network/interaction metadata for spawned anchors (see §6.7.6) |
| `autonomy` | `SpawnAutonomyBlock` | NO | Optional deterministic combat/follow AI for spawned minions or stationary structures (see §6.7.7) |
| `interaction` | `SpawnInteractionBlock` | NO | Optional arming + proximity-trigger / pickup behavior (see §6.7.8) |
| `coverage` | `SpawnCoverageBlock` | NO | Optional provider/consumer coverage-network behavior for placed structures (see §6.7.9) |
| `instance_limit` | `SpawnInstanceLimitBlock` | NO | Optional per-owner live-count cap with deterministic overflow policy (see §6.7.10) |
| `loadout_projection` | `SpawnLoadoutProjectionBlock` | NO | Optional runtime loadout/profile snapshot overlay for clone-style spawns (see §6.7.11) |
| `control_projection` | `SpawnControlProjectionBlock` | NO | Optional single-actor owner-control / body-return policy for clone or bomb spawns (see §6.7.12) |
| `respawn_anchor` | `SpawnRespawnAnchorBlock` | NO | Optional one-use owner-scoped rebirth route override for post-terminal spawn handling (see §6.7.14) |

#### 6.7.1 ProjectileBlock (optional, for projectile/trap actors)

| Field | Type | Required | Mapping |
|-------|------|----------|---------|
| `speed` | `fixed` | YES | Projectile velocity (units/tick) |
| `homing` | `bool` | NO | Default false. If true, `turn_rate` is required. |
| `turn_rate` | `fixed` | When homing | P-03: max angular change per tick |
| `pierce` | `int` | NO | Default 0. Targets passed through before stopping. |
| `arming_delay_ticks` | `int` | NO | Default 0. Ticks before detonation-capable triggers arm. |
| `radius_growth_per_unit` | `fixed` | NO | Default `0`; deterministic collision-radius growth per world unit traveled |
| `payload_scale_per_unit` | `fixed` | NO | Default `0`; deterministic scalar applied to carried projectile payload per world unit traveled |
| `max_scaled_radius` | `fixed` | NO | Optional cap for radius growth |
| `return_policy` | `ProjectileReturnBlock` | NO | Optional outbound → return lifecycle |
| `bounce_policy` | `ProjectileBounceBlock` | NO | Optional wall-reflection lifecycle |
| `attachment_policy` | `ProjectileAttachmentBlock` | NO | Optional attach-to-carrier delayed detonation lifecycle |
| `carry_policy` | `ProjectileCarryBlock` | NO | Optional bounded rolling multi-target carry behavior |
| `detonation_policy` | `DetonationPolicyBlock` | NO | Default: `{ entity_impact: detonate, world_impact: stop, expiry: despawn }` |

#### 6.7.2 DetonationPolicyBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `manual_trigger` | `bool` | NO | `false` |
| `proximity_radius` | `fixed` | NO | none |
| `entity_impact` | `enum` | NO | `detonate` |
| `world_impact` | `enum` | NO | `stop` |
| `expiry` | `enum` | NO | `despawn` |

`entity_impact` enum: `ignore`, `stop`, `detonate`, `detonate_after_pierce`.
`world_impact` enum: `ignore`, `bounce`, `stop`, `detonate`.
`expiry` enum: `despawn`, `detonate`.

#### 6.7.3 ProjectileReturnBlock

Declares an outbound projectile that transitions into a tracked return leg.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `trigger` | `enum` | YES | — |
| `track` | `enum` | YES | — |
| `despawn_radius` | `fixed` | YES | — |
| `allow_repeat_hits_on_return` | `bool` | NO | `false` |
| `preserve_speed` | `bool` | NO | `true` |

`trigger` enum:

- `max_range`
- `manual_recall`
- `world_impact`

`track` enum:

- `source_entity_current`
- `source_entity_last_known_on_loss`

Validation rules:

1. `despawn_radius > 0`.
2. `manual_recall` requires the parent `spawn_actor` effect to declare `output_binding`, because the
   return trigger is driven by a later authored reference to the live actor.

#### 6.7.4 ProjectileBounceBlock

Declares deterministic wall reflection for a projectile.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `max_bounces` | `int` | YES | — |
| `preserve_speed` | `bool` | NO | `true` |

Validation rules:

1. `max_bounces > 0`.
2. `bounce_policy` requires `detonation_policy.world_impact = bounce`.

#### 6.7.5 ProjectileAttachmentBlock

Declares that a projectile impact converts into an attached delayed detonation carried by the struck
entity.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `delay_ticks` | `int` | YES | — |
| `follow_attached_entity` | `bool` | NO | `true` |
| `on_carrier_loss` | `enum` | NO | `last_known_position` |
| `preserve_original_payload` | `bool` | NO | `true` |

`on_carrier_loss` enum:

- `last_known_position`
- `fizzle`

Validation rules:

1. `delay_ticks > 0`.
2. `attachment_policy` requires `detonation_policy.entity_impact != ignore`.

Lowering rule: when `attachment_policy` is present, the projectile's first admitted entity impact
does not resolve its carried impact payload immediately. Instead, the impacted entity's current
owner records an attached timed payload carrying the projectile's remaining lifetime policy, the
authored delay, and optionally the original projectile payload snapshot. At expiry, the detonation
is anchored to the carrier's current position when `follow_attached_entity = true`; otherwise it
uses the impact position. If the carrier no longer exists, `on_carrier_loss` selects either the
last authoritative carrier position or a clean fizzle.

#### 6.7.5.1 ProjectileCarryBlock

Declares a bounded carried-target roster owned by one live projectile actor. This is the canonical
authoring surface for rolling snowball-style transport that accumulates multiple struck entities and
releases them on wall impact or expiry.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `max_carried_targets` | `int` | YES | — |
| `carry_offset_distance` | `fixed` | NO | `0` |
| `lateral_spacing` | `fixed` | NO | `0` |

Validation rules:

1. `max_carried_targets > 0`.
2. `carry_offset_distance >= 0`.
3. `lateral_spacing >= 0`.
4. `carry_policy` requires `detonation_policy.entity_impact = ignore`.
5. `carry_policy` is incompatible with `attachment_policy`.

Lowering rule: when `carry_policy` is present, each newly admitted valid entity impact appends that
target to the projectile's ordered carried-target set until `max_carried_targets` is reached. Hits
after the cap still resolve their ordinary impact payload, but they are not added to the carry set.
While carried, a target's position is derived from the projectile's current committed position plus
an authored front offset (`carry_offset_distance`) and a deterministic perpendicular slot offset
computed from capture order and `lateral_spacing`. Carried targets remain ordinary authoritative
entities in the R-tree, but their voluntary movement, casts, attacks, and item use are suppressed
while the carry lock is active. On projectile world impact, expiry, or removal, all carried targets
are released at the projectile's current committed position in their preserved capture order and
resume ordinary action capability on the next tick. Cross-boundary transfer serializes the carried
entity ID list with the projectile snapshot; the carried entities themselves continue to use the
ordinary single-authority entity handoff path, with projectile-shadow following as the temporary
fallback when co-located handoff finishes a tick later.

#### 6.7.6 PortalAnchorBlock

Declares that a spawned actor participates in a portal network (`P-59`).

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `network_mode` | `enum` | YES | — |
| `paired_anchor_state` | `string` | When `network_mode = pair_follower` | — |
| `interaction_range` | `fixed` | YES | — |
| `allowed_filter` | `FilterExpr` | YES | — |
| `destination_mode` | `enum` | YES | — |
| `per_user_cooldown_ticks` | `int` | NO | `0` |
| `channel_ticks` | `int` | NO | `0` |
| `destroy_network_on_removed` | `bool` | NO | `false` |

`network_mode` enum:

- `new_pair_leader`
- `pair_follower`
- `owner_scoped`

`destination_mode` enum:

- `paired_other`
- `player_choice`

Validation rules:

1. `interaction_range > 0`.
2. `per_user_cooldown_ticks >= 0`.
3. `channel_ticks >= 0`.
4. `pair_follower` requires `paired_anchor_state`, and that runtime state MUST be a
   `RuntimeStateDefinition` of kind `bookmark(entity_ref)`.
5. `new_pair_leader` and `pair_follower` require `destination_mode = paired_other`.

Lowering rule:

- `new_pair_leader` registers one new anchor in a fresh portal network. The authored ability SHOULD
  pair it with `spawn_actor.output_binding` plus `write_state(entity_ref)` when a later cast needs
  to find that first anchor deterministically.
- `pair_follower` resolves the previously stored anchor from `paired_anchor_state` and joins the
  newly spawned actor to that same two-anchor network.
- `owner_scoped` creates or joins one owner-scoped network keyed by the spawning owner plus the
  public ability identity, enabling N-way destination choice among all other live anchors in that
  network.
- Portal usage, per-user cooldown checks, cross-Arbiter registry replication, and destination
  handoff follow the engine-owned `P-59` contract in `docs-core/`.

#### 6.7.7 SpawnAutonomyBlock

Declares a bounded compiler-owned behavior profile for spawned actors that should autonomously
follow, acquire targets, and attack without bespoke script loops.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `engage_filter` | `FilterExpr` | YES | — |
| `engage_radius` | `fixed` | YES | — |
| `attack_mode` | `enum` | NO | `basic_attack_only` |
| `idle_mode` | `enum` | NO | `hold_position` |
| `follow_entity` | `EntityRef` | When `idle_mode = follow_entity` | — |
| `follow_distance` | `fixed` | When `idle_mode = follow_owner` or `follow_entity` | — |
| `leash_radius` | `fixed` | NO | none |
| `on_owner_removed` | `enum` | NO | `despawn` |

`attack_mode` enum:

- `basic_attack_only`
- `use_authored_abilities`

`idle_mode` enum:

- `hold_position`
- `follow_owner`
- `follow_entity`

`on_owner_removed` enum:

- `despawn`
- `die`
- `persist`

Validation rules:

1. `engage_radius > 0`.
2. `follow_distance >= 0` when required.
3. `leash_radius > 0` when present.
4. `follow_entity` MUST NOT be authored together with `idle_mode = follow_owner`.

#### 6.7.8 SpawnInteractionBlock

Declares a spawned actor that waits for an optional arming period and then resolves a proximity
interaction such as a pickup or mine detonation.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `arming_delay_ticks` | `int` | NO | `0` |
| `trigger_filter` | `FilterExpr` | YES | — |
| `trigger_radius` | `fixed` | YES | — |
| `resolution_mode` | `enum` | NO | `collector_only` |
| `effect_radius` | `fixed` | When `resolution_mode = radius_query` | — |
| `effect_filter` | `FilterExpr` | When `resolution_mode = radius_query` | — |
| `effects` | `EffectList` | YES | — |
| `consume_on_trigger` | `bool` | NO | `true` |

`resolution_mode` enum:

- `collector_only`
- `radius_query`

Validation rules:

1. `arming_delay_ticks >= 0`.
2. `trigger_radius > 0`.
3. `radius_query` requires `effect_radius > 0`.
4. `radius_query` requires `effect_filter`.

#### 6.7.9 SpawnCoverageBlock

Declares a live provider/consumer coverage relationship among spawned actors, for mechanics like
power-field pylons and turrets that deactivate when coverage is lost.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mode` | `enum` | YES | — |
| `network_id` | `string` | YES | — |
| `radius` | `fixed` | When `mode = provider` | — |
| `member_filter` | `FilterExpr` | When `mode = provider` | — |
| `require_for_spawn` | `bool` | When `mode = consumer` | `false` |
| `unpowered_mode` | `enum` | When `mode = consumer` | `dormant` |

`mode` enum:

- `provider`
- `consumer`

`unpowered_mode` enum:

- `dormant`
- `suspended`

Validation rules:

1. `radius > 0` when `mode = provider`.
2. `member_filter` is required when `mode = provider`.

#### 6.7.10 SpawnInstanceLimitBlock

Declares a deterministic live-count cap for spawned actors owned by one entity.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `scope` | `enum` | YES | — |
| `max_live` | `int` | YES | — |
| `overflow_policy` | `enum` | NO | `reject_new` |

`scope` enum:

- `owner_by_ability`
- `owner_by_archetype`

`overflow_policy` enum:

- `reject_new`
- `despawn_oldest`

Validation rules:

1. `max_live > 0`.

#### 6.7.11 SpawnLoadoutProjectionBlock

Declares that a spawned actor should snapshot another entity's current projected loadout/profile at
spawn time instead of using only its static archetype ability/passive set. This is the canonical
surface for clone-shell style spawns.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `source` | `LoadoutSource` | YES | — |
| `max_hp_multiplier` | `fixed` | NO | `1.0` |
| `stat_multiplier` | `fixed` | NO | `1.0` |
| `excluded_abilities` | `list<string>` | NO | none |

Validation rules:

1. `count = 1` is required when `loadout_projection` is authored.
2. `max_hp_multiplier > 0`.
3. `stat_multiplier > 0`.

Lowering rule: when `loadout_projection` is present, the runtime resolves `source` once at spawn
commit, captures an immutable projected loadout/passive/appearance snapshot, applies any
`excluded_abilities`, and overlays that snapshot onto the spawned actor's archetype-defined shell.
`entity_current_loadout` follows the same authority rule as `swap_identity`: if the source entity
is remote, the source owner snapshots the current projected loadout and relays it as immutable
payload to the spawn owner. `max_hp_multiplier` scales the spawned actor's max HP after the
projected loadout/profile is applied, and `stat_multiplier` scales the projected effective combat
stats. Later source changes do NOT live-update the spawned actor.

#### 6.7.12 SpawnControlProjectionBlock

Declares that a single spawned actor temporarily receives a controller's input stream, optionally
while the controller's original body is suspended and later restored.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `controller` | `EntityRef` | NO | `caster` |
| `owner_body_policy` | `enum` | YES | — |
| `control_scope` | `enum` | NO | `full` |
| `on_actor_removed` | `enum` | NO | `release_control` |
| `on_expire` | `enum` | NO | `release_control` |
| `manual_trigger_effects` | `EffectList` | NO | Optional same-slot manual trigger while control is active |
| `on_expire_effects` | `EffectList` | NO | Optional payload emitted immediately before natural expiry cleanup |
| `on_controller_break_effects` | `EffectList` | NO | Optional payload emitted when controller-side maintenance/control breaks |
| `restore_position` | `enum` | When either end policy is `restore_owner` | `projected_actor_position` |
| `restore_hp_policy` | `enum` | When either end policy is `restore_owner` | `preserve_stored_owner` |

`owner_body_policy` enum:

- `root_owner`
- `suspend_owner`

`control_scope` enum:

- `full`
- `movement_only`
- `abilities_only`

`on_actor_removed` / `on_expire` enum:

- `release_control`
- `restore_owner`

`restore_position` enum:

- `projected_actor_position`
- `original_owner_position`

`restore_hp_policy` enum:

- `preserve_stored_owner`
- `projected_actor_ratio`

Validation rules:

1. `count = 1` is required when `control_projection` is authored.
2. `owner_body_policy = suspend_owner` is required when either end policy is `restore_owner`.
3. `projected_actor` and `projected_actor_position` refs are only legal inside
   `manual_trigger_effects`, `on_expire_effects`, and `on_controller_break_effects`.

Lowering rule: `control_projection` installs one dynamic routing record from `controller` to the
spawned actor and commits it at the next Stage 1 routing boundary. `root_owner` leaves the owner in
the world; any immobilization, channeling, or cast lock still comes from ordinary status/channel
authoring. `suspend_owner` snapshots the owner's body state, suspends it, and later restores it if
an authored end policy selects `restore_owner`. `projected_actor_position` means the actor's
current authoritative position on expiry or its last authoritative position if it was removed. This
surface intentionally covers only one controlled spawned actor; multi-member split/reform groups
remain outside the current canonical profile.

When `manual_trigger_effects` is present, the compiler exposes one temporary same-slot manual
trigger action to the `controller` while the control session remains active.

`manual_trigger_effects`, `on_expire_effects`, and `on_controller_break_effects` execute in the
controlled actor's callback context:

- `caster` remains the resolved `controller`, so authored scaling and source identity still come
  from the summoner/controller.
- `projected_actor` resolves to the live controlled actor.
- `projected_actor_position` resolves to that actor's authoritative current position, snapshotted at
  callback admission.

`on_expire_effects` fire only for natural lifetime expiry, immediately before the runtime applies
the authored `on_expire` owner-body cleanup. `on_controller_break_effects` fire only when the
control session ends because controller-side maintenance/control is broken (for example
interruption, controller removal, or another control replacement) before actor expiry or manual
trigger. Ordinary external actor destruction/removal does NOT fire either callback; it still follows
`on_actor_removed` cleanup only. Authored callback effects may include
`despawn_entity(target = projected_actor)` when the mechanic intends detonation/teardown to consume
the shell.

#### 6.7.13 SpawnPlacementBlock

Declares deterministic expansion of one resolved spawn anchor into multiple authored spawn points.
This surface is intentionally explicit: the compiler does NOT synthesize random scatters or infer a
rotation from targeting state.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `offsets` | `list<SpawnOffsetDef>` | YES | — |

`SpawnOffsetDef`:

| Field | Type | Required |
|-------|------|----------|
| `x` | `fixed` | YES |
| `y` | `fixed` | YES |
| `heading_x` | `fixed` | NO |
| `heading_y` | `fixed` | When `heading_x` is authored |

Validation rules:

1. `offsets` MUST NOT be empty.
2. `count > 1` is required when `placement` is authored.
3. `count` MUST equal `len(offsets)`.
4. Either every authored offset carries both `heading_x` and `heading_y`, or none of them do.
5. Placement-authored heading vectors are only legal when the parent `spawn_actor` also authors
   `projectile`.
6. Every authored `(heading_x, heading_y)` vector MUST be non-zero.

Lowering rule: the authored `position` resolves once to an anchor point. The runtime then applies
each authored `(x, y)` offset to that anchor in authored order and emits one independent `P-32`
spawn request per derived point. If an offset also authors `(heading_x, heading_y)`, that
world-space vector is normalized deterministically and carried as an ability-local initial launch
heading for the derived spawn. For projectile actors, that heading seeds the created projectile's
outbound velocity and bypasses external aim/cursor state for that derived spawn only. If
`placement` is omitted, all spawned actors use the same resolved `position`. Placement offsets and
optional placement-authored headings are explicit world-space data, not inferred rotations or
random samples, so the same input produces the same ordered spawn lattice on every replay.

#### 6.7.14 SpawnRespawnAnchorBlock

Declares that a single spawned actor acts as a revocable, one-use rebirth anchor for its resolved
`owner`.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `respawn_delay_ticks` | `int` | YES | — |

Validation rules:

1. `count = 1` is required when `respawn_anchor` is authored.
2. `respawn_delay_ticks > 0`.

Lowering rule: `respawn_anchor` binds to the parent `spawn_actor` effect's resolved `owner`
(`caster` when `owner` is omitted). The spawned actor survives ordinary owner terminal-death cleanup,
registers one owner-scoped live rebirth-anchor record while it exists, and does not itself alter
normal observer/targetability policy; authors still use `observer_presentation`,
`targetability_policy`, and `instance_limit` for hidden/low-HP/one-at-a-time behavior. That live
record follows the anchor across handoffs/removals so the owner's current Stage 10 host can still
resolve a remote anchor deterministically. When Stage 10 commits terminal death for that owner and
the anchor is still live, the runtime emits `PlayerDied` with
`respawn_override = Some(RespawnAnchor { anchor_entity_id, position, respawn_delay_ticks })` in
addition to any `respawn_delay_credit_ticks`. If the anchor is removed before the respawn commits, its
current authoritative owner emits `RespawnOverrideRevoked { victim, source_entity_id }`, and Meta
falls back to the stored base respawn schedule. When Meta later routes `SpawnEntity` with
`respawn_context = Some(RespawnSpawnContext::RespawnAnchor { anchor_entity_id })`, the target
Arbiter validates that the
anchor still exists, consumes it atomically on success, and materializes the owner at the anchor's
authoritative position using the ordinary spawn-state defaults. Validation failure emits the same
revocation event and MUST NOT spawn the player at the anchor. This surface changes only route/timer
selection; HP, resource, status reset, and cooldown reset policy on return remain the ordinary Meta
spawn configuration.

#### 6.7.15 Compilation Path: Ability → Entity Archetype

Projectile fields defined in `spawn_actor.projectile` do NOT compile into the ability's `AbilityIRBlock`. Instead, the compiler merges them into the **entity archetype** referenced by `archetype_id`. The data flow is:

1. The ability's `spawn_actor` effect compiles to a P-32 (Actor Spawning) `IRDirective` carrying the `archetype_id`.
2. The `ProjectileBlock` fields compile into the `EntityDefinitions` section (0x11) of the game image, as part of the archetype's data.
3. At runtime, when the engine processes the P-32 directive and calls `initialize_spawn_configuration`, the adapter reads the archetype's projectile fields from the game image's `EntityDefinitions` and returns them in the `SpawnConfiguration`.
4. The engine uses the archetype's `ProjectileDetonationPolicy`, `arming_delay_ticks`, `pierce`, `homing`, `turn_rate`, travel scalars, return policy, bounce policy, and attachment policy to configure the spawned `ProjectileActor`.

This separation exists because projectile configuration is per-entity-type (all fireballs behave the same), not per-ability-cast. Multiple abilities can spawn the same projectile archetype with different damage values but identical flight/detonation behavior.

If `spawn_actor.output_binding` is present, the runtime exposes the created actor ID as a binding
that MAY feed `write_state(entity_ref)`, `{ binding: name }` entity refs, or later follow-up
effects. `output_binding` is only legal when `count = 1`.

`portal_anchor` is ability-local spawn metadata, not archetype-static projectile behavior. It stays
in `AbilityIREntry.ParamData` and is copied into the spawned actor's live portal-anchor state when
the `P-32` spawn resolves.

`placement`, `autonomy`, `interaction`, `coverage`, `instance_limit`, `loadout_projection`,
`control_projection`, and `respawn_anchor` are also ability-local spawn metadata. They stay in
`AbilityIREntry.ParamData`, keyed to the specific `spawn_actor` effect that emitted the spawn, and
initialize compiler-owned live behavior state on the created actor. They do NOT merge into
`EntityDefinitions`, because two abilities may spawn the same archetype with different formation
offsets, instance limits, proximity payloads, provider/consumer network IDs, source-snapshot
overlays, owner-body return policies, or rebirth-anchor delays.

#### 6.7.16 Shared-Archetype Conflict Rule

If multiple authored `spawn_actor` effects reference the same `archetype_id` and provide a
`ProjectileBlock`, the compiler MUST normalize those projectile blocks and compare the normalized
results byte-for-byte.

- If all explicit `ProjectileBlock` values for that `archetype_id` normalize identically, the
  compiler emits one canonical archetype projectile config into `EntityDefinitions`.
- If any explicit `ProjectileBlock` for that `archetype_id` differs after normalization, the
  compile MUST fail deterministically with `ENTITY_PROJECTILE_CONFIG_CONFLICT`.
- `spawn_actor` effects that omit `projectile` do not contribute a new archetype definition; they
  inherit the archetype's canonical projectile config.

This rule preserves the invariant that projectile behavior is owned by the entity archetype rather
than by individual ability casts.

### 6.8 `apply_shield`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `shield_type` | `enum` | YES | `absorption` (P-18) or `instance` (P-19) |
| `amount` | `fixed` | When absorption | Shield HP |
| `charges` | `int` | When instance | Hit count |
| `duration_ticks` | `int` | YES | Shield expiry |
| `priority` | `int` | NO | Resolution order among multiple shields |
| `output_binding` | `string` | NO | Exposes the created shield instance to authored lifecycle effects |
| `bind_absorbed_value_as` | `string` | NO | Exposes the authoritative absorbed amount for each shield-hit callback |
| `on_absorb_effects` | `EffectList` | NO | Effects emitted once per authoritative absorb event |
| `bind_remaining_value_as` | `string` | NO | Exposes shield remaining value at removal time |
| `on_expire_effects` | `EffectList` | NO | Effects emitted when the shield expires naturally |
| `on_break_effects` | `EffectList` | NO | Effects emitted when the shield is removed by damage depletion |

Validation rule: `bind_absorbed_value_as` requires `on_absorb_effects`.

If `bind_absorbed_value_as` is present, the runtime captures the actual damage prevented by that
specific shield instance on each admitted hit, after higher-priority shields have already consumed
their share of the same payload. The binding is exposed only to `on_absorb_effects` through
`ScalingExpr` binding reads. For `instance` shields, the absorbed amount is the residual hit value
negated by the consumed charge. If `bind_remaining_value_as` is present, the runtime separately
captures the shield's remaining value immediately before removal and exposes it to the authored
lifecycle effects through `ScalingExpr` binding reads. `on_break_effects` see `0` when the shield
is fully consumed. Shield absorb/break/expiry payloads are reactive effects and therefore follow
the same deferred execution rule as other reactive effects: target-free combat payloads re-enter on
the next tick, and any spatial queries re-enter at next-tick TargetResolution.

### 6.9 `resource_burn`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `pool_id` | `string` | YES | Target-side resource pool |
| `amount` | `fixed` | YES | P-49 |
| `damage_ratio` | `fixed` | YES | P-49 / P-21 |
| `damage_type` | `enum` | YES | P-15 damage payload |
| `grant_to_caster` | `bool` | NO | Default `false`; if true, destroyed amount is refunded to the caster's matching pool |

Lowering rule: the target owner performs the authoritative resource read. The actual destroyed
amount is `min(authored amount, target current pool)`. Bonus damage is
`actual_destroyed * damage_ratio` and continues through ordinary HP damage resolution. If
`grant_to_caster = true`, the same authoritative destroyed amount is refunded to the caster after
the target-side burn commits.

### 6.10 `steering`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-03 (Trajectory Steering) |
| `mode` | `enum` | YES | `toward_source` (charm), `away_from_source` (fear), `toward_target` (homing) |
| `duration_ticks` | `int` | YES | Steering duration |

### 6.11 `value_conversion`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `source_type` | `enum` | YES | Input value type (e.g., `damage_dealt`, `resource_destroyed`) |
| `target_type` | `enum` | YES | Output value type (e.g., `healing`, `damage`) |
| `ratio` | `fixed` | YES | Conversion scalar |
| `target` | `EntityRef` | YES | P-21 (Value Conversion) |

### 6.12 `zone`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `position` | `PositionRef` | YES | P-32 (Actor Spawning) zone actor |
| `owner` | `EntityRef` | NO | Default `caster`; source/ownership identity for the created zone actor |
| `shape` | `enum` | YES | Zone shape |
| `radius` | `fixed` | YES | Zone dimension |
| `duration_ticks` | `int` | YES | Zone lifetime hard cap |
| `pulse_interval_ticks` | `int` | NO | P-44 (Pulse Timer) |
| `pulse_effects` | `EffectList` | When pulse | Effects per pulse |
| `enter_effects` | `EffectList` | NO | P-14 OnEnter effects |
| `leave_effects` | `EffectList` | NO | P-14 OnLeave effects |
| `combo_field_type` | `enum` | NO | P-64 combo field tag |
| `output_binding` | `string` | NO | Exposes the created zone actor ID for runtime-state writes or follow-up checks |
| `mobility` | `ZoneMobilityBlock` | NO | Optional attached / drifting / tracking motion profile |
| `persistence` | `ZonePersistenceBlock` | NO | Optional early-end / source-death policy |
| `continuous_force` | `ZoneForceBlock` | NO | Optional per-tick pull/push profile for occupants |
| `attached_to` | `EntityRef` | NO | Legacy shorthand for `mobility.mode = attached_entity` |

### 6.12.1 ZoneMobilityBlock

Declares how a zone actor moves after creation. If absent, the zone is stationary.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mode` | `enum` | YES | — |
| `target` | `EntityRef` | When `mode = attached_entity` or `tracking_entity` | — |
| `heading_from` | `PositionRef` | When `mode = self_propelled` | — |
| `heading_to` | `PositionRef` | When `mode = self_propelled` | — |
| `speed` | `fixed` | When `mode = self_propelled` or `tracking_entity` | — |
| `world_impact` | `enum` | NO | `ignore` |
| `on_target_removed` | `enum` | NO | `hold_last_position` |

`mode` enum:

- `attached_entity`
- `self_propelled`
- `tracking_entity`

`world_impact` enum:

- `ignore`
- `stop`
- `dissipate`

`on_target_removed` enum:

- `hold_last_position`
- `dissipate`

Validation rules:

1. `speed > 0` when required.
2. `on_target_removed` is only legal for `attached_entity` and `tracking_entity`.

### 6.12.2 ZonePersistenceBlock

Declares how a zone may end early before its authored `duration_ticks` hard cap.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mode` | `enum` | YES | — |
| `end_on_source_removed` | `bool` | NO | `false` |
| `count_ghost_hits_as_occupants` | `bool` | NO | `true` |

`mode` enum:

- `fixed_duration`
- `until_empty_on_pulse`

Validation rules:

1. `until_empty_on_pulse` requires `pulse_interval_ticks`.
2. `until_empty_on_pulse` requires `pulse_effects`.

### 6.12.3 ZoneForceBlock

Declares a continuous radial force applied every tick to entities currently inside the zone.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `filter` | `FilterExpr` | YES | — |
| `direction` | `enum` | YES | — |
| `strength_at_edge` | `fixed` | YES | — |
| `strength_at_center` | `fixed` | YES | — |

`direction` enum:

- `toward_center`
- `away_from_center`

Validation rules:

1. `strength_at_edge >= 0`.
2. `strength_at_center >= 0`.

Lowering rule: `zone` always lowers to one spawned zone actor. If `owner` is omitted, the zone's
source/ownership identity is the current `caster`; if authored, it uses the resolved `owner`
instead, which allows combo- or relay-driven replacement fields to preserve the original field's
ownership. `attached_to` is canonical shorthand for `mobility = { mode: attached_entity, target:
attached_to }` and MUST NOT be combined with an explicit attached-entity mobility block. All zones
obey `duration_ticks` as a hard cap even when their persistence mode can end them earlier. If
`enter_effects` or `leave_effects` are present, or `persistence.mode = until_empty_on_pulse`, the
runtime maintains a bounded occupant set and diffs it each tick against the zone actor's committed
current position. `continuous_force` emits deterministic per-tick displacement influence using a linear interpolation from
`strength_at_edge` to `strength_at_center`.

### 6.12.4 `inject_geometry`

Declares bounded runtime collision geometry that is NOT an autonomous actor. This is the canonical
authoring surface for temporary walls, build blockers, and other injected spatial obstacles.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `position` | `PositionRef` | YES | P-08 / P-57 origin |
| `mode` | `enum` | YES | P-08 or P-57 |
| `duration_ticks` | `int` | YES | Geometry lifetime |
| `blocks_movement` | `bool` | NO | Default `true` |
| `blocks_projectiles` | `bool` | NO | Default `false` |
| `radius` | `fixed` | When `mode = circle` | P-08 circle radius |
| `inner_radius` | `fixed` | When `mode = ring` | P-08 ring inner radius |
| `outer_radius` | `fixed` | When `mode = ring` | P-08 ring outer radius |
| `half_width` | `fixed` | When `mode = box` | P-08 box half-width |
| `half_height` | `fixed` | When `mode = box` | P-08 box half-height |
| `length` | `fixed` | When `mode = segment` | P-57 corridor length |
| `width` | `fixed` | When `mode = segment` | P-57 corridor width |
| `heading_from` | `PositionRef` | When `mode = segment` | Orientation source |
| `heading_to` | `PositionRef` | When `mode = segment` | Orientation target |
| `orientation` | `enum` | NO | Default `along_heading`; only for `segment` |

`mode` enum:

- `circle`
- `box`
- `ring`
- `segment`

`orientation` enum:

- `along_heading`
- `perpendicular_to_heading`

Validation rules:

1. `duration_ticks > 0`.
2. At least one of `blocks_movement` or `blocks_projectiles` MUST be `true`.
3. `radius > 0` for `circle`.
4. `half_width > 0` and `half_height > 0` for `box`.
5. `inner_radius > 0` and `outer_radius > inner_radius` for `ring`.
6. `length > 0` and `width > 0` for `segment`.
7. `segment` requires both `heading_from` and `heading_to`.

Lowering rule:

- `circle`, `box`, and `ring` lower directly to one `P-08` injection whose lifetime is bounded by
  `duration_ticks`.
- `segment` lowers to one fixed `P-57` corridor with `max_segments = 1`. The runtime computes the
  segment heading from `heading_from -> heading_to`, optionally rotates it by ninety degrees when
  `orientation = perpendicular_to_heading`, then centers the resulting corridor on `position`.
- All injected geometry participates in the same core `max_dynamic_geometry_per_arbiter`,
  `max_dynamic_geometry_area`, and boundary-replication rules from `docs-core/`.

### 6.12.5 `polyline_zone`

Declares a bounded corridor that is built from a moving entity's committed positions. This is the
canonical authoring surface for trail mechanics that need collision, pulse damage, or enter/leave
events on a recorded path.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `source` | `EntityRef` | YES | P-57 point source |
| `duration_ticks` | `int` | YES | Generator lifetime hard cap |
| `width` | `fixed` | YES | P-57 corridor width |
| `segment_ttl_ticks` | `int` | YES | Per-segment expiry |
| `max_segments` | `int` | NO | Default compiler/runtime bound |
| `sample_interval_ticks` | `int` | NO | `1` |
| `sample_on_stationary` | `bool` | NO | `false` |
| `blocks_movement` | `bool` | NO | `false` |
| `blocks_projectiles` | `bool` | NO | `false` |
| `filter` | `FilterExpr` | NO | Admission filter for `enter_effects` / `leave_effects` / `pulse_effects` |
| `pulse_interval_ticks` | `int` | NO | P-44 |
| `pulse_effects` | `EffectList` | When pulse | P-44 payload |
| `enter_effects` | `EffectList` | NO | P-14 OnEnter payload |
| `leave_effects` | `EffectList` | NO | P-14 OnLeave payload |
| `ignore_source` | `bool` | NO | `true` |

Validation rules:

1. `duration_ticks > 0`.
2. `width > 0`.
3. `segment_ttl_ticks > 0`.
4. `sample_interval_ticks > 0`.
5. If authored, `max_segments > 0`.
6. `pulse_interval_ticks` requires `pulse_effects`.
7. At least one of `blocks_movement`, `blocks_projectiles`, `pulse_effects`, `enter_effects`, or
   `leave_effects` MUST be present.

Lowering rule: `polyline_zone` lowers to one bounded `P-57` generator keyed to the source entity's
committed current position in PostKinematic. Every `sample_interval_ticks`, the runtime samples the
source's current authoritative (or Ghost-resolved) position and appends a new segment only if the
sampled point differs from the previous tail point, unless `sample_on_stationary = true`. Active
segments share one corridor-local occupant-set model: if `enter_effects`, `leave_effects`, or
`pulse_effects` are authored, the runtime diffs admitted occupants against the CURRENT active
corridor after segment expiry/removal. `ignore_source = true` excludes the tracked source entity
from those admission checks.

### 6.12.6 `kinematic_sweep`

Declares deterministic movement where the moving entity's body is the collision volume. This is the
canonical authoring surface for charges, body dashes, hit-confirmed sweeps, and orbiting pass-through
attacks.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-07 mover |
| `mode` | `enum` | YES | Sweep path mode |
| `destination` | `PositionRef` | When `mode = toward_position` | P-07 destination |
| `anchor` | `EntityRef` | When `mode = orbit_entity` | P-06 / P-07 anchor |
| `duration_ticks` | `int` | YES | Sweep lifetime |
| `collision_radius` | `fixed` | YES | Circular sweep volume radius |
| `hit_filter` | `FilterExpr` | YES | Candidate admission filter |
| `unique_hit_scope` | `enum` | NO | `entity_once_per_sweep` |
| `on_entity_hit` | `enum` | NO | `continue` |
| `max_hits` | `int` | NO | Unbounded until duration or authored stop condition |
| `on_hit_effects` | `EffectList` | NO | Payload for admitted sweep hits |
| `on_complete_effects` | `EffectList` | NO | Payload when the sweep ends normally |
| `world_impact_effects` | `EffectList` | NO | Payload when the sweep stops on world collision |
| `capture` | `SweepCaptureBlock` | NO | Optional first-hit carry policy |
| `orbit` | `OrbitSweepBlock` | When `mode = orbit_entity` | Orbit movement parameters |
| `output_binding` | `string` | NO | Exposes the sweep's resolved final position |

`mode` enum:

- `toward_position`
- `orbit_entity`

`unique_hit_scope` enum:

- `none`
- `entity_once_per_sweep`
- `entity_once_per_revolution`

`on_entity_hit` enum:

- `continue`
- `stop`
- `capture_first`

Validation rules:

1. `duration_ticks > 0`.
2. `collision_radius > 0`.
3. If authored, `max_hits > 0`.
4. `capture` is only legal when `on_entity_hit = capture_first`.
5. `mode = toward_position` requires `destination`.
6. `mode = orbit_entity` requires both `anchor` and `orbit`.
7. `unique_hit_scope = entity_once_per_revolution` is only legal when `mode = orbit_entity`.

Lowering rule: `kinematic_sweep` lowers to one compiler-owned `P-07` state bundle on the
authoritative moving entity. The engine advances the mover during Stage 5, checks overlap against a
circle of radius `collision_radius`, records admitted hits according to `unique_hit_scope`, and
emits `on_hit_effects` in collision order. `output_binding`, when present, exposes the mover's
resolved final position after the sweep ends or stops early. Manual or same-key finishers that
reuse the sweep's current position are authored through the existing `ActivationModes` /
runtime-state surface from §5.7 and §10; `kinematic_sweep` does NOT introduce a new client intent
shape.

#### 6.12.6.1 SweepCaptureBlock

Declares deterministic first-hit capture for `kinematic_sweep`.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `carry_offset_distance` | `fixed` | NO | `0` |
| `break_on_source_removed` | `bool` | NO | `true` |
| `break_on_target_removed` | `bool` | NO | `true` |
| `release_on_world_impact` | `bool` | NO | `true` |

Lowering rule: on the first admitted hit, the runtime installs a compiler-owned `P-06`
attached-kinematics latch from the captured target to the sweep source for the remainder of the
sweep. The carried target never shares authority with the source: if the source hands off, the
captured target follows through the ordinary co-located `P-06` handoff path.

#### 6.12.6.2 OrbitSweepBlock

Declares orbit-derived motion for `kinematic_sweep`.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `radius` | `fixed` | YES | — |
| `angular_velocity_per_tick` | `fixed` | YES | — |
| `max_revolutions` | `fixed` | YES | — |
| `end_on_anchor_removed` | `bool` | NO | `true` |

Validation rules:

1. `radius > 0`.
2. `angular_velocity_per_tick > 0`.
3. `max_revolutions > 0`.

Lowering rule: `orbit_entity` mode keeps the mover authoritative on the anchor's current owner,
recomputes a deterministic orbit offset from the anchor's current local-or-Ghost position each
tick, and then runs the ordinary sweep collision pass at that derived position. When
`unique_hit_scope = entity_once_per_revolution`, the hit ledger resets only after the accumulated
orbit angle crosses a full turn. If `end_on_anchor_removed = true` and the anchor disappears, the
sweep ends immediately and the mover remains at its current committed position.

### 6.13 `swap_hp_percent`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-15 paired overwrite path |
| `min_hp` | `fixed` | NO | Default `1` |
| `same_arbiter_only` | `bool` | NO | Default `true` |

`swap_hp_percent` reads the caster's and target's current HP percentages, captures BOTH values
before either write occurs, and then overwrites each entity's HP with the other's percentage scaled
to local max HP. This is not damage, not healing, and not a combat event for proc purposes.

Validation rules:

1. `min_hp >= 0`.
2. If `same_arbiter_only = true`, the compiler/runtime MUST reject casts whose resolved target is a
   Ghost or otherwise remote at resolution time.

### 6.14 `execute`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-17 / P-24 |
| `hp_threshold` | `fixed` | YES | Authoritative threshold check |
| `normal_damage` | `fixed` | NO | Default `0` |
| `damage_type` | `enum` | NO | Default `physical` |
| `reset_cooldown_on_execute` | `bool` | NO | Default `false` |
| `bypass_prevention` | `bool` | NO | Default `true` |

Lowering rule: the threshold check is performed on the TARGET owner using the target's actual
current HP. If the target is at or below `hp_threshold`, the runtime emits a bypass-marked kill
using `P-24` when `bypass_prevention = true`; otherwise it resolves the optional `normal_damage`
through the ordinary damage pipeline. `reset_cooldown_on_execute` fires only on the execute path.

### 6.15 `write_state`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `state_id` | `string` | YES | Runtime-state mutation |
| `capture` | `enum` | YES | Capture mode |
| `position` | `PositionRef` | When `capture = position` | World-position snapshot |
| `entity` | `EntityRef` | When `capture = entity_ref` | Entity/actor reference snapshot |

`capture` enum:

- `position`
- `entity_ref`

`write_state` writes into a referenced `RuntimeStateDefinition`. The referenced state kind MUST be
compatible with the selected capture mode. For `position` capture, the runtime stores absolute world
coordinates and, when enabled by the state definition, the current topology epoch. For
`entity_ref` capture, the runtime stores the authoritative entity/actor ID and later resolves that
actor's current position at read time.

### 6.16 `clear_state`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `state_id` | `string` | YES | Runtime-state mutation |

`clear_state` removes any currently active payload for the referenced runtime state slot.

### 6.17 `restore_from_state`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `state_id` | `string` | YES | Runtime-state read |
| `target` | `EntityRef` | YES | Target entity to mutate |
| `apply_position` | `bool` | NO | Default `true` |
| `apply_hp` | `bool` | NO | Default `false` |
| `position_validation` | `enum` | NO | Default `nearest_walkable` |

`position_validation` enum:

- `require_walkable`
- `nearest_walkable`

`restore_from_state` reads the referenced runtime state and applies the stored snapshot to the
target. Behavior depends on the state kind:

- `bookmark(position)` — use the stored world position
- `bookmark(entity_ref)` — dereference the linked entity/actor and use its CURRENT position
- `snapshot_buffer` — read the nearest sample at or before the configured lookback horizon

If `apply_position = true`, the runtime performs P-01-style instant relocation using the resolved
position. If `apply_hp = true`, it overwrites HP from the stored snapshot directly rather than
producing a heal/damage event.

### 6.18 `advance_sequence`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `state_id` | `string` | YES | Runtime-state mutation |
| `action` | `enum` | YES | Sequence transition |

`action` enum:

- `advance`
- `reset`

`advance_sequence` applies to runtime states of kind `sequence_window`. `advance` increments the
current step, refreshes the expiry window, and wraps to the state's configured reset step after the
maximum step. `reset` clears the current sequence back to the configured reset step immediately.

### 6.19 `modify_charge_pool`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `state_id` | `string` | YES | P-42 / P-50 |
| `action` | `enum` | YES | Charge mutation |
| `charge_type` | `string` | When `action = add` | Typed charge value |
| `count` | `int` | NO | Default `1` |
| `consume_policy` | `enum` | NO | Default `one`; only for `consume` |

`action` enum:

- `add`
- `consume`
- `reset`

`consume_policy` enum:

- `one`
- `all`

For self-recharging charge models, `consume` decrements the available charge count and starts the
next recharge timer according to the referenced state definition. For typed charge pools, `add`
appends the authored charge type (up to capacity) and refreshes decay timing; `consume` removes one
or all stored charges and exposes the consumed count/composition to downstream bindings.

### 6.19.1 `modify_resource`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `pool_id` | `string` | YES | Existing resource pool on the target entity |
| `mode` | `enum` | YES | `add` or `remove` |
| `amount` | `fixed` | YES | Base scalar delta |
| `scaling` | `ScalingExpr` | NO | Optional stat/binding-derived delta |

Validation rules:

1. `amount >= 0`.
2. If `scaling` is present, the resolved scalar delta MUST be non-negative at runtime.

Lowering rule: `modify_resource` resolves on the target entity's authoritative owner. The runtime
computes `delta = amount + optional scaling contribution`, then applies the authored `mode` with a
hard clamp to the target entity's `[0, max_resource[pool_id]]` range. `add` saturates at the pool's
maximum. `remove` subtracts at most the current pool value and never underflows. Unlike
`resource_burn`, `modify_resource` is a pure gameplay-resource mutation: it does not derive bonus
damage, refund the caster, or create a special relay format beyond the ordinary target-owner
mutation path.

### 6.20 `swap_identity`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-31 |
| `source` | `LoadoutSource` | YES | P-31 |
| `duration_ticks` | `int` | NO | P-45 / P-31 revert timing |
| `hp_policy` | `enum` | NO | Default `preserve_ratio` |
| `cooldown_policy` | `enum` | NO | Default `store_and_restore` |
| `stat_multiplier` | `fixed` | NO | Default `1.0` |
| `excluded_abilities` | `list<string>` | NO | none |

`hp_policy` enum:

- `preserve_ratio`
- `preserve_absolute`
- `set_to_new_max`
- `cap_to_new_max`

`cooldown_policy` enum:

- `store_and_restore`
- `reset_new_slots`
- `preserve_matching_slots`

`swap_identity` is the canonical authoring surface for temporary transformations, borrowed
loadouts, and same-entity profile swaps. It preserves the target entity's `entity_id` and
position. If `duration_ticks` is present, the runtime stores the original loadout and reverts when
the duration ends or the swap is explicitly broken by a later effect.

### 6.21 `borrow_ability_slot`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-31 slot override path |
| `source_entity` | `EntityRef` | YES | Runtime source lookup |
| `source_selector` | `enum` | YES | Borrowed-ability selection |
| `source_slot_id` | `string` | When `source_selector = slot_id` | Source ability slot |
| `destination_slot_id` | `string` | YES | Overridden slot on target |
| `duration_ticks` | `int` | NO | P-45 / P-31 revert timing |
| `usage_limit` | `int` | NO | Default `1` |
| `fallback_if_missing` | `enum` | NO | Default `fail` |

`source_selector` enum:

- `last_cast_ability`
- `slot_id`

`fallback_if_missing` enum:

- `fail`
- `ignore`

Lowering rule: the runtime installs a bounded slot override on `target`. `last_cast_ability`
selects the source entity's last accepted public ability ID from its bounded cast-history register.
The borrowed slot uses the target's own stats and resource pools unless a later effect says
otherwise.

### 6.22 `control_override`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-29 |
| `controller` | `EntityRef` | NO | Default `caster` |
| `duration_ticks` | `int` | NO | P-45 / Stage 1 revert timing |
| `movement_speed_multiplier` | `fixed` | NO | Default `1.0` |
| `input_policy` | `enum` | NO | Default `adapter_routed` |
| `controller_lock_mode` | `enum` | NO | Default `none` |
| `target_lock_mode` | `enum` | NO | Default `all_actions` |
| `break_on_controller_removed` | `bool` | NO | `true` |
| `break_on_target_removed` | `bool` | NO | `true` |

`input_policy` enum:

- `mirror`
- `role_split`
- `adapter_routed`

`controller_lock_mode` / `target_lock_mode` enum:

- `none`
- `movement_only`
- `all_actions`

`control_override` declares that `controller` supplies inputs for `target` through the engine's
Stage 1 P-29 routing contract. If authored during a later stage, the routing mutation becomes
effective at the NEXT tick's Stage 1 boundary.

### 6.22.1 `cycle_split_form`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `controller` | `EntityRef` | NO | P-30 pending Stage 1 selection change |
| `source_ability_id` | `string` | YES | Current split-form session lookup |

`cycle_split_form` advances the active member for the current split-form session created by
`source_ability_id`. It is the canonical authoring surface for Spirit Split style "swap body"
utility abilities without introducing a new input plane.

Validation rules:

1. `source_ability_id` MUST reference an ability that authors `split_form`.

Lowering rule: `cycle_split_form` resolves the current active split-form session for
`(controller, source_ability_id)`, picks the next surviving member in authored `member_bindings`
order, and enqueues one pending Stage 1 routing mutation for the next tick. If the session does not
exist or no alternate surviving member is available, the effect fails cleanly with no mutation.

### 6.23 `link`

Declares a persistent cross-entity binding with optional combat, healing, event-clone, and
origin-anchor policy. This is the canonical authoring surface for tethers, guardian links,
soulbind-style mirroring, drag latches, and symbiote-style remote origin anchors.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `source_entity` | `EntityRef` | NO | Defaults to `caster`; source endpoint for the binding |
| `target` | `EntityRef` | YES | P-34 |
| `duration_ticks` | `int` | YES | P-34 expiry |
| `symmetric` | `bool` | NO | Default `false` |
| `break_distance` | `fixed` | NO | Optional P-04 break clamp |
| `break_on_source_removed` | `bool` | NO | `true` |
| `break_on_target_removed` | `bool` | NO | `true` |
| `is_cleansable` | `bool` | NO | `true` |
| `damage_redirect` | `DamageRedirectBlock` | NO | P-20 |
| `heal_mirror_ratio` | `fixed` | NO | Post-resolution heal copy |
| `heal_mirror_direction` | `enum` | NO | Default `both` when `symmetric = true`, else `target_to_source` |
| `event_clone` | `EventCloneBlock` | NO | P-60 |
| `origin_override` | `OriginOverrideBlock` | NO | Stage 12 / origin-anchor metadata |

`heal_mirror_direction` enum:

- `source_to_target`
- `target_to_source`
- `both`

Validation rules:

1. `duration_ticks > 0`.
2. If authored, `break_distance > 0`.
3. At least one of `break_distance`, `damage_redirect`, `heal_mirror_ratio`, `event_clone`, or
   `origin_override` MUST be present.
4. If authored, `heal_mirror_ratio` MUST be in `[0, 1]`.
5. If authored, `damage_redirect.ratio` MUST be in `(0, 1]`.
6. If authored, `damage_redirect.max_hops >= 1`.
7. If `event_clone` is present, at least one of `clone_damage`, `clone_healing`, or
   `clone_status` MUST be `true`.
8. The current canonical compiler profile requires `event_clone.prevent_reclone = true`.

Lowering rule: `link` emits cross-cutting `P-34` metadata tying `source_entity` (default `caster`)
and `target` together for the authored duration and break rules. If `symmetric = true`, the runtime
installs the same link policy in both directions as one logical binding pair between those resolved
endpoints. This allows compiler-emitted bindings between two non-caster entities without inventing
a second linkage subsystem. `is_cleansable = true` means the compiler lowers a generated status
handle for the link so ordinary cleanse/dispel flows can break it deterministically.

### 6.23.1 DamageRedirectBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `ratio` | `fixed` | YES | — |
| `direction` | `enum` | NO | `target_to_source` |
| `max_hops` | `int` | NO | `1` |

`direction` enum:

- `source_to_target`
- `target_to_source`
- `both`

Lowering rule: `ratio` is evaluated against PRE-mitigation damage on the source side of the
redirection pair. The redirected portion resolves against the partner through that partner's own
defensive pipeline. `max_hops = 1` is the canonical anti-recursion default; any additional hops
must be explicitly authored and remain bounded.

### 6.23.2 EventCloneBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `scope` | `enum` | NO | `single_target_only` |
| `clone_damage` | `bool` | NO | `true` |
| `clone_healing` | `bool` | NO | `true` |
| `clone_status` | `bool` | NO | `true` |
| `prevent_reclone` | `bool` | NO | `true` |

`scope` enum:

- `single_target_only`

Lowering rule: the runtime clones the ORIGINAL event envelope onto the partner, then resolves the
cloned event against the partner's own state. If `prevent_reclone = true`, the cloned event is
tagged so it cannot trigger further link-based cloning.

### 6.23.3 OriginOverrideBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `direction` | `enum` | NO | `source_uses_target_position` |
| `observer_anchor` | `bool` | NO | `false` |

`direction` enum:

- `source_uses_target_position`
- `target_uses_source_position`
- `both`

Lowering rule: the linked actor keeps its own stats, cooldowns, and authority ownership, but its
ability-origin queries use the linked partner's current position while the link is active. If
`observer_anchor = true`, observer-scoped payloads for that actor are emitted from the linked
partner's vicinity instead of the body's vicinity.

### 6.24 `enter_container`

Declares entry of one entity into another entity's active `ContainerProfileDef`.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `occupant` | `EntityRef` | YES | P-58 |
| `container` | `EntityRef` | YES | P-58 |
| `eject_after_ticks` | `int` | NO | Container-owned forced-exit timer |
| `on_forced_eject_effects` | `EffectList` | NO | Payload emitted if the timed eject fires |

Validation rules:

1. If authored, `eject_after_ticks > 0`.

Lowering rule: `enter_container` emits one `P-58` enter mutation. The target container entity MUST
currently expose a compiled `ContainerProfileDef`; the runtime validates capacity, range, and
`allowed_filter` against that profile. If `eject_after_ticks` is authored, the runtime records a
bounded container-owned timer; when it fires, the occupant is ejected at the container's current
position and `on_forced_eject_effects` are emitted for that occupant on the next tick.
`occupant_storage_mode = off_world_stored` removes the occupant from the spatial world while
contained and restores it only when the exit mutation commits.

### 6.25 `exit_container`

Declares deterministic exit/ejection from a container.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `container` | `EntityRef` | YES | P-58 |
| `mode` | `enum` | YES | Exit selection |
| `occupant` | `EntityRef` | When `mode = specific_occupant` | Occupant to eject |
| `exit_position` | `enum` | NO | `container_position` |
| `on_exit_effects` | `EffectList` | NO | Payload emitted for each ejected occupant |

`mode` enum:

- `specific_occupant`
- `all_occupants`

`exit_position` enum:

- `container_position`
- `stored_entry_position`

Lowering rule: `exit_container` emits one `P-58` exit/eject mutation. `all_occupants` iterates over
the container's current occupant set in deterministic occupant-ID order. `stored_entry_position`
uses the container's recorded per-occupant entry point when available; otherwise the runtime falls
back to `container_position`.

### 6.25.1 `start_actor_transit`

Declares late-bound directed transit for one live actor toward an authored destination. This is the
canonical "launch the already-spawned shell/vehicle to the chosen point" surface.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | Compiler-owned actor transit |
| `destination` | `PositionRef` | YES | Absolute transit endpoint |
| `speed` | `fixed` | YES | Units per tick |
| `arrival_radius` | `fixed` | YES | Arrival threshold |
| `on_arrival_effects` | `EffectList` | NO | Payload emitted once on arrival |

Validation rules:

1. `speed > 0`.
2. `arrival_radius > 0`.
3. `transit_actor` and `transit_actor_position` refs are only legal inside
   `on_arrival_effects`.

Lowering rule: `start_actor_transit` installs one bounded transit record on the resolved live
target actor. The runtime snapshots the authored `destination` to one absolute world position at
cast commit, records the authored `speed` and `arrival_radius`, and then each current owner moves
the actor in a straight line toward that destination during kinematic resolution until arrival or
actor removal. This is not voluntary movement input and it does not rewrite the actor's
targetability, HP, or ordinary lifecycle; the actor remains a normal spawned/targetable body and
hands off across Arbiter boundaries normally while carrying the transit record as SoftState.

When the actor comes within `arrival_radius` (or the next transit step would overshoot), the
current owner snaps it to the authored destination, clears the transit record, and emits
`on_arrival_effects` immediately in the transit callback context:

- `caster` remains the entity that cast `start_actor_transit`
- `transit_actor` resolves to the arrived actor
- `transit_actor_position` resolves to that actor's committed arrival position

If the actor is removed or terminally dies before arrival, the transit record is simply discarded.
Crash/destruction behavior remains authored through ordinary container / `on_death` / removal
hooks, not through a second transit-failure callback surface.

### 6.26 `fork_instance`

Declares creation of a host-Arbiter spatial instance and immediate migration of a bounded member
set into it. This is the canonical compiler surface for `P-56` arena-style isolation, including
controller-coordinated remote member admission before the instance begins.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `members` | `list<EntityRef>` | YES | P-56 |
| `duration_ticks` | `int` | YES | Instance lifetime |
| `output_binding` | `string` | NO | Exposes the created instance ID for follow-up references |

Validation rules:

1. `members` MUST contain at least 1 entity.
2. `duration_ticks > 0`.

Lowering rule: `fork_instance` emits one `P-56` instance-fork directive on the CURRENT Arbiter,
followed by migration of the authored member set into that new instance. If some members are
currently authoritative on other Arbiters, the engine admits them through the `docs-core`
controller-coordinated pre-instance transfer and inserts them directly into the host instance. The
live instance still remains single-Arbiter once created. Member queries and observer payloads then
resolve against the instance R-tree per `docs-core/01-4-dynamic-topology-contract.md`. The engine
stores each member's current parent-world exit position automatically and routes standard handoff on
instance exit if a stored return point is no longer owned by the host Arbiter.

### 6.27 `revive_corpse`

Declares resurrection of a corpse-registry entry back into an active entity.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `corpse` | `EntityRef` | YES | P-47 / Stage 10 respawn routing |
| `hp_ratio` | `fixed` | YES | Phase/HP restore |
| `clear_statuses` | `bool` | NO | `true` |
| `cooldown_policy` | `enum` | NO | `full_cooldown` |
| `consume_corpse` | `bool` | NO | `true` |

`cooldown_policy` enum:

- `preserve_predeath`
- `full_cooldown`
- `refresh_all`

Validation rules:

1. `hp_ratio` MUST be in `(0, 1]`.
2. `corpse` MUST resolve to a corpse-registry entry, not an active entity.
3. The targeted corpse's source entity type MUST define `corpse_profile`.

Lowering rule: `revive_corpse` emits a Stage 10 lifecycle mutation that re-materializes the corpse's
source entity at the corpse's stored death position, restores its active life phase with HP set to
`base_max_hp * hp_ratio`, applies the authored cooldown/status reset policy, and clears the corpse
record when `consume_corpse = true`. If the revived entity already had a pending Meta respawn
timer, the runtime emits `PlayerResurrected` so Meta cancels that timer deterministically. The
current canonical `P-47` profile resolves `revive_corpse` only against the CURRENT Arbiter's
authoritative corpse registry; remote/Ghost corpse revival is not supported. This is the
in-combat corpse-return path and MUST NOT be used to author alternate post-terminal respawn
locations or respawn timers.

### 6.28 `restore_phase`

Declares recovery of a non-active intermediate life phase back to the entity's active phase.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-25 |
| `hp_ratio` | `fixed` | YES | Active-phase HP restore |
| `required_phase` | `enum` | NO | `downed` |
| `clear_negative_statuses` | `bool` | NO | `false` |

`required_phase` enum:

- `downed`
- `any_non_active`

Validation rules:

1. `hp_ratio` MUST be in `(0, 1]`.
2. `target` MUST resolve to an active entity in a non-zero lifecycle phase.

Lowering rule: `restore_phase` emits a Stage 10 phase-transition mutation that moves the target
back to lifecycle phase `0` (Active) with HP set to `base_max_hp * hp_ratio`. It is the canonical
recovery path for ally rally and self-rally mechanics; terminal corpse resurrection remains
`revive_corpse`, not `restore_phase`.

### 6.29 `consume_corpse`

Declares deterministic corpse selection, optional atomic corpse consumption, and per-corpse effect
evaluation with corpse-derived bindings.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `selection` | `enum` | YES | P-47 |
| `corpse` | `EntityRef` | When `selection = target` | Corpse handle |
| `center` | `PositionRef` | When `selection = nearest_to_position` | Query origin |
| `range` | `fixed` | When query mode | Query radius |
| `count` | `int` | NO | `1` |
| `filter` | `FilterExpr` | YES | Corpse filter |
| `consume` | `bool` | NO | `true` |
| `bind_entity_as` | `string` | NO | Exposes the selected corpse handle |
| `bind_position_as` | `string` | NO | Exposes the corpse death position |
| `bind_stats` | `list<CorpseStatBindingDef>` | NO | Exposes requested corpse stat snapshots |
| `effects` | `EffectList` | YES | Evaluated once per selected corpse |

`selection` enum:

- `target`
- `nearest_to_caster`
- `nearest_to_target`
- `nearest_to_position`

Validation rules:

1. `count > 0`.
2. `filter` MUST be one of the canonical dead/corpse filters.
3. Query modes require `range > 0`.
4. `selection = target` requires `corpse`.
5. `selection = nearest_to_position` requires `center`.
6. `bind_stats.stat_id` values MUST be unique within one `consume_corpse` block.

Lowering rule: `consume_corpse` resolves an ordered corpse candidate set from the targeted corpse
or an in-range `P-47` query, sorts it deterministically by `(distance, corpse_id)`, and selects up
to `count` currently unclaimed corpses. If `consume = true`, each selected corpse is claimed
atomically before its child `effects` run; later claims on the same corpse fail cleanly. The child
`effects` list then runs once per selected corpse with the authored bindings populated from that
corpse's stored death position and optional retained stat snapshot. Query modes read only the
CURRENT Arbiter's authoritative corpse registry; remote/Ghost corpse consumption is not part of the
current canonical `P-47` profile.

---

## 7. EntityDefinition Schema

Defines an entity archetype. Not compiled to IR directly — stored as static data in the game image.

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `entity_type_id` | `string` | YES | Unique |
| `base_stats` | `map<string, fixed>` | YES | Keys must reference valid stat IDs |
| `max_hp` | `fixed` | YES | Must be > 0 |
| `max_resource` | `map<string, fixed>` | NO | Resource pool definitions |
| `movement_speed` | `fixed` | YES | Must be > 0 |
| `abilities` | `list<string>` | NO | References AbilityDefinition IDs |
| `passive_status_effects` | `list<string>` | NO | References StatusEffectDefinition IDs |
| `stagger_bar` | `StaggerBarDef` | NO | P-48 optional component |
| `downed_state` | `DownedStateDef` | NO | P-25 optional component |
| `ghost_phase` | `GhostPhaseDef` | NO | P-25 optional component for non-terminal heal-only linger phases |
| `corpse_profile` | `CorpseProfileDef` | NO | P-47 corpse-registry persistence and snapshot policy |
| `block_defense` | `BlockDefenseDef` | NO | Deterministic defender-side block gate + post-block hook |
| `container_profile` | `ContainerProfileDef` | NO | Static P-58 entry/capacity/cast policy for this entity archetype |
| `loadout_profiles` | `list<LoadoutProfileDef>` | NO | P-31 named swap targets for this entity archetype |
| `control_topology` | `ControlTopologyDef` | NO | P-29/P-30 routing profile for one-to-many or many-to-one play patterns |
| `group_role_id` | `string` | NO | P-54 sequential-step role classification |
| `targetability_policy` | `TargetabilityPolicyBlock` | NO | Permanent relation-scoped targeting / AoE / collision / pathing flags |
| `observer_presentation` | `ObserverPresentationBlock` | NO | Permanent team-scoped downstream presentation override |
| `combo_field_type` | `enum` | NO | If the entity emits a combo field |

### 7.1 StaggerBarDef

| Field | Type | Required |
|-------|------|----------|
| `max_stagger` | `fixed` | YES |
| `regen_rate_per_tick` | `fixed` | YES |
| `regen_delay_ticks` | `int` | YES |
| `stagger_duration_ticks` | `int` | YES |
| `vulnerability_bonus` | `fixed` | YES |

### 7.2 DownedStateDef

| Field | Type | Required |
|-------|------|----------|
| `downed_hp_ratio` | `fixed` | YES |
| `downed_ability_set` | `list<string>` | YES |
| `downed_movement_speed_ratio` | `fixed` | YES |
| `rally_hp_ratio` | `fixed` | YES |
| `rally_channel_ticks` | `int` | YES |
| `finish_channel_ticks` | `int` | YES |
| `self_rally_on_kill` | `bool` | NO |

Validation rules:

1. `downed_hp_ratio` MUST be in `(0, 1]`.
2. `rally_hp_ratio` MUST be in `(0, 1]`.
3. `downed_movement_speed_ratio` MUST be in `[0, 1]`.
4. `rally_channel_ticks > 0`.
5. `finish_channel_ticks > 0`.
6. `downed_ability_set` MUST NOT be empty.

`downed_state` defines a non-terminal intermediate life phase. While an entity is in that phase,
the engine routes damage to the phase HP pool defined by `docs-core/01-2-entity-lifecycle-contract.md`,
exposes `downed_ability_set` on the next tick, and applies the authored movement/capability
overrides through the phase config. Ally rally and self-rally return through `restore_phase`;
terminal corpse resurrection remains `revive_corpse`. If `self_rally_on_kill = true`, any
terminal kill credited to the entity while it is still downed schedules one Stage 10 return to
Active at `rally_hp_ratio`.

### 7.2.1 GhostPhaseDef

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `ghost_duration_ticks` | `int` | YES | — |
| `ghost_ability_set` | `list<string>` | YES | — |
| `respawn_delay_credit_ticks` | `int` | NO | `ghost_duration_ticks` |
| `clear_statuses_on_enter` | `bool` | NO | `true` |

Validation rules:

1. `ghost_duration_ticks > 0`.
2. `respawn_delay_credit_ticks >= 0`.
3. `respawn_delay_credit_ticks <= ghost_duration_ticks`.
4. `ghost_ability_set` MUST NOT be empty.
5. Each ability in `ghost_ability_set` MUST compile to allied-beneficial and/or self-beneficial
   effects only. Damage, hostile CC, hostile spawned actors, and hostile global events are rejected.

`ghost_phase` defines a non-terminal intermediate life phase for "linger before true death"
mechanics. When Stage 10 sees lethal HP on an entity type with `ghost_phase`, the runtime
transitions the entity into that phase instead of committing terminal death. The phase exposes
`ghost_ability_set` on the next tick, forces `CAN_MOVE = false`, `CAN_ATTACK = false`,
`CAN_USE_ITEMS = false`, and `PASSIVES_ACTIVE = false`, and leaves only `CAN_CAST = true` for the
authored healing/support whitelist. The phase also installs a generated targeting/collision overlay
equivalent to `hostile_effects = false`, `allied_beneficial_effects = false`,
`allied_harmful_effects = false`, `self_effects = false`, `affected_by_area_effects = false`,
`collidable_for_skillshots = false`, and `collidable_for_pathing = false`; the ghost therefore
remains in-world for observer/vision purposes without blocking pathing or receiving further hostile
effects. If `clear_statuses_on_enter = true`, the runtime performs one
`cleanse(polarity = all, require_cleansable = false)` batch on phase entry before the ghost ability
set becomes active. When `ghost_duration_ticks` expires, the entity transitions to terminal death
and publishes `PlayerDied` with `respawn_delay_credit_ticks` so Meta may subtract that credit from
the resolved base respawn timer. This is still an intermediate `P-25` phase, not a post-terminal
active shell.

### 7.2.2 CorpseProfileDef

| Field | Type | Required |
|-------|------|----------|
| `persist_ticks` | `int` | YES |
| `retain_effective_stats` | `bool` | NO |
| `retain_loadout_snapshot` | `bool` | NO |

If `corpse_profile` is present, terminal death creates a corpse-registry record keyed by the source
entity's ID and death position for `persist_ticks`. `retain_effective_stats = true` preserves the
entity's final effective stat snapshot for later corpse-derived bindings. `retain_loadout_snapshot =
true` additionally preserves a bounded projected loadout/appearance snapshot so `swap_identity` may
target the corpse later through `LoadoutSource`. Under the current canonical `P-47` profile, corpse
records are queried and consumed only on the Arbiter that owns that corpse registry entry; remote
or Ghost-backed corpse access is not supported.

Validation rule: `persist_ticks > 0`.

### 7.3 BlockDefenseDef

| Field | Type | Required |
|-------|------|----------|
| `chance_stat` | `string` | YES |
| `applies_to` | `enum` | NO |
| `dr_penalty_per_block` | `fixed` | YES |
| `dr_decay_interval_ticks` | `int` | YES |
| `max_dr_stacks` | `int` | NO |
| `negates_non_damage_effects` | `bool` | NO |

`applies_to` enum:

- `direct_hits`
- `weapon_hits_only`
- `all_damage_events`

The effective block chance is the derived `chance_stat` value minus the currently accumulated block
DR penalty. On a successful block, the engine negates eligible HP/resource damage components before
shield absorption or ordinary mitigation, marks the event as blocked for `on_block` triggers, and
continues non-damage payloads only if `negates_non_damage_effects = false`.

### 7.3.1 ContainerProfileDef

Static containment metadata consumed by `enter_container` / `exit_container` and the engine-owned
`P-58` contract.

| Field | Type | Required |
|-------|------|----------|
| `max_capacity` | `int` | YES |
| `entry_range` | `fixed` | YES |
| `allowed_filter` | `FilterExpr` | YES |
| `occupant_storage_mode` | `enum` | NO |
| `occupant_can_be_targeted` | `bool` | NO |
| `occupant_cast_policy` | `enum` | NO |
| `allow_manual_exit` | `bool` | NO |
| `eject_on_removed` | `bool` | NO |

`occupant_storage_mode` enum:

- `attached_visible`
- `off_world_stored`

`occupant_cast_policy` enum:

- `none`
- `basic_attacks_only`
- `all`

This profile is static archetype data. Runtime effects and scripted interactions decide WHEN an
entity enters or exits the container, but capacity, range, occupant targeting, and occupant cast
policy are defined here so bunker-style structures, moving transports, and devour-style carriers
all reuse one bounded containment contract. `attached_visible` is the ordinary P-06-style vehicle
mode. `off_world_stored` is the devour-style mode: the occupant is removed from the spatial world,
excluded from queries/payloads, and restored only on exit or container destruction.

Validation rules:

1. `max_capacity > 0`.
2. `entry_range > 0`.
3. `occupant_storage_mode = off_world_stored` requires `occupant_can_be_targeted = false`.
4. `occupant_storage_mode = off_world_stored` requires `occupant_cast_policy = none`.

### 7.4 LoadoutProfileDef

| Field | Type | Required |
|-------|------|----------|
| `profile_id` | `string` | YES |
| `abilities` | `list<string>` | NO |
| `passive_status_effects` | `list<string>` | NO |
| `max_hp_multiplier` | `fixed` | NO |
| `movement_speed_multiplier` | `fixed` | NO |
| `resource_multipliers` | `map<string, fixed>` | NO |
| `stat_multipliers` | `map<string, fixed>` | NO |
| `stat_overrides` | `map<string, fixed>` | NO |
| `appearance_id` | `string` | NO |

`LoadoutProfileDef` is a bounded named profile attached to one `EntityDefinition`. It is the
canonical static target for self-transform and role-based ability-set swaps. Omitted ability/passive
lists inherit the parent entity definition.

### 7.5 ControlTopologyDef

| Field | Type | Required |
|-------|------|----------|
| `mode` | `enum` | YES |
| `input_policy` | `enum` | YES |
| `members` | `list<ControlMemberDef>` | YES |
| `selection_mode` | `enum` | NO |
| `elimination_policy` | `enum` | NO |

`mode` enum:

- `one_to_many`
- `many_to_one`

`input_policy` enum:

- `mirror`
- `role_split`
- `adapter_routed`

`selection_mode` enum:

- `single`
- `multiple`
- `all`

`elimination_policy` enum:

- `all_members_removed`
- `primary_removed`
- `shared_entity_removed`

`ControlTopologyDef` is the canonical static authoring surface for persistent one-session-to-many
entity control and many-sessions-to-one entity control. It does not replace the engine's Stage 1
routing contract; it declares the routing shape the runtime installs at spawn and re-establishes on
handoff/reconnect.

### 7.6 ControlMemberDef

| Field | Type | Required |
|-------|------|----------|
| `role_id` | `string` | YES |
| `control_scope` | `enum` | YES |
| `entity_type_id` | `string` | When `mode = one_to_many` |
| `loadout_profile_id` | `string` | NO |
| `is_primary` | `bool` | NO |

`control_scope` enum:

- `full`
- `movement_only`
- `abilities_only`
- `observer_only`

For `many_to_one`, all members address the same underlying entity and `loadout_profile_id` MAY
restrict which authored abilities a given role may invoke. For `one_to_many`, `entity_type_id`
declares the archetype each controlled member uses; the actual spawn/respawn rules remain part of
the game-mode/adaptation layer.

---

## 8. TriggerDefinition Schema

Reactive hooks that fire in response to combat events. Compile to PostDamage or DeathCheck IR instructions.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `hook` | `enum` | YES | See hook mapping below |
| `condition` | `GuardExpr` | NO | Compiled to IR guard |
| `effects` | `EffectList` | YES | Effect chain to execute on trigger |
| `propagation` | `PropagationBlock` | NO | Compiler-owned bounded recursion / replay policy |

Hook enum → primitive mapping:

| Hook | Primitive | Pipeline Stage |
|------|-----------|---------------|
| `on_hit` | P-35 | PostDamage |
| `on_damage_received` | P-36 | PostDamage |
| `on_crit` | P-37 | PostDamage |
| `on_block` | P-38 | PostDamage |
| `on_death` | P-39 | DeathCheck |
| `on_cast` | P-40 | IntentValidation |

`on_death` is terminal-death only under the current canonical compiler/core profile. It fires after
the engine has determined there is no surviving intermediate life phase. `on_death` effects may
read two implicit runtime bindings:

- `death_position` — the terminal death position as a `PositionRef` binding
- `killer_entity` — the killing entity as an `EntityRef` binding when the death had an attributed
  killer; environmental or unattributed deaths leave this binding absent

Trigger effects are subject to the deferred execution rule (`03-1-compiler-ir-specification.md` §6.1): combat events generated by PostDamage triggers are queued for the next tick.

### 8.1 PropagationBlock

Declares a bounded child-generation policy for recursive proc chains, repeated-cast envelopes, and
fan-out cascades.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mode` | `enum` | YES | — |
| `base_chance` | `fixed` | NO | `1.0` |
| `chance_multiplier_per_generation` | `fixed` | NO | `1.0` |
| `max_generations` | `int` | YES | — |
| `effect_multiplier_per_generation` | `fixed` | NO | `1.0` |
| `dedup_scope` | `enum` | NO | `none` |
| `query_radius` | `fixed` | When query mode | — |
| `max_targets_per_generation` | `int` | NO | `1` |
| `filter` | `FilterExpr` | When query mode | — |
| `replay_targeting` | `enum` | When `mode = repeat_same_cast` | `same_snapshot` |
| `repeat_resource_policy` | `enum` | When `mode = repeat_same_cast` | `free` |
| `repeat_cooldown_policy` | `enum` | When `mode = repeat_same_cast` | `ignore` |

`mode` enum:

- `bounce_nearest`
- `fanout_query`
- `repeat_same_cast`

`dedup_scope` enum:

- `none`
- `entity_once_per_chain`

`replay_targeting` enum:

- `same_snapshot`

`repeat_resource_policy` enum:

- `free`
- `normal`

`repeat_cooldown_policy` enum:

- `ignore`
- `normal`

Validation rules:

1. `max_generations > 0`.
2. `base_chance` and `chance_multiplier_per_generation` MUST be in `[0, 1]`.
3. `effect_multiplier_per_generation > 0`.
4. Query modes (`bounce_nearest`, `fanout_query`) require `query_radius > 0`.
5. Query modes require `max_targets_per_generation > 0`.
6. `bounce_nearest` requires `max_targets_per_generation = 1`.
7. `repeat_same_cast` MUST NOT author `query_radius`, `filter`, or `dedup_scope = entity_once_per_chain`.
8. `repeat_same_cast` may only be attached to `hook = on_cast`.
9. `repeat_same_cast` requires the trigger's authored `effects` list to be empty; the replayed cast
   itself is the emitted child payload.

Lowering rule: `propagation` compiles to compiler-owned chain state containing a stable `chain_id`,
the current `generation`, the authored bounds/scalars, and either an optional visited-entity set
(`entity_once_per_chain`) or a replay snapshot of the original target/position envelope
(`repeat_same_cast`). If `entity_once_per_chain` is enabled, the root target is inserted into the
visited set before the first child query runs. For query modes, the trigger's authored `effects`
list is the child payload executed on each emitted target. Child generations inherit the same
`chain_id` and increment `generation` before re-entering the deferred execution queues.

---

## 9. StatusEffectDefinition Schema

Defines a buff, debuff, or persistent effect. Referenced by `apply_buff`/`apply_debuff` effects.

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `status_id` | `string` | YES | Unique |
| `max_stacks` | `int` | NO | Default 1 |
| `duration_ticks` | `int` | YES | Must be > 0 |
| `polarity` | `enum` | YES | One of `positive`, `negative`, `neutral` |
| `stat_modifiers` | `list<StatModifier>` | NO | P-16 (Stat Layering) |
| `capability_flags` | `map<string, bool>` | NO | P-26 (Capability Bitmask) |
| `periodic_effects` | `PeriodicBlock` | NO | P-44 (Pulse Timer) for DoTs/HoTs |
| `on_expire_effects` | `EffectList` | NO | Effects when status expires |
| `is_passive` | `bool` | NO | Affected by Mute (P-26 PASSIVES_ACTIVE) |
| `cc_category` | `enum` | NO | P-62 category for immunity checking |
| `duration_scaling` | `enum` | NO | Default `fixed`; `status_resistance` applies target debuff-duration reduction on admission |
| `is_cleansable` | `bool` | NO | Default true |
| `status_application_immunity` | `enum` | NO | Default `none`; blocks admission of incoming statuses by polarity while this status is active |
| `cc_immunity_categories` | `list<enum>` | NO | Grants P-62 immunity while this status is active |
| `snapshot_recorder_state` | `string` | NO | References a `RuntimeStateDefinition` of kind `snapshot_buffer` |
| `consumption_window` | `ConsumptionWindowBlock` | NO | Consumes this status on the next matching cast / hit / damage-received event |
| `damage_accumulator` | `DamageAccumulatorBlock` | NO | Tracks post-mitigation HP loss while active and exposes the total to `on_expire_effects` |
| `deferred_ledger` | `DeferredLedgerBlock` | NO | P-22 interception policy for all HP damage/healing |
| `hp_floor` | `HpFloorBlock` | NO | P-23 minimum-HP floor while the status is active |
| `death_prevention` | `DeathPreventionBlock` | NO | One-shot lethal intercept with authored HP restore |
| `movement_damage` | `MovementDamageBlock` | NO | P-63 displacement-based damage policy |
| `spread` | `SpreadBlock` | NO | Compiler-owned bounded status propagation policy |
| `targetability_policy` | `TargetabilityPolicyBlock` | NO | Relation-scoped targeting / AoE / collision / pathing override while active |
| `observer_presentation` | `ObserverPresentationBlock` | NO | Team-scoped downstream presentation override while active |
| `suspension` | `SuspensionBlock` | NO | Compiler-owned suspension / dormancy / stasis policy |
| `projectile_intercept` | `ProjectileInterceptBlock` | NO | P-61 redirect/return policy for incoming projectile impacts while active |
| `zone_relation_gate` | `ZoneRelationGateBlock` | NO | Live-zone-conditioned hostile admission / mitigation gate |
| `movement_constraint` | `MovementConstraintBlock` | NO | Status-owned P-04 clamp / reverse / excess-damage policy |
| `resource_stat_links` | `list<ResourceStatLink>` | NO | Dynamic P-16 modifiers derived from the carrier's current resource pools |

### 9.1 StatModifier

| Field | Type | Required |
|-------|------|----------|
| `stat_id` | `string` | YES |
| `operation` | `enum` | YES |
| `value` | `fixed` | YES |

`operation` enum: `add_flat`, `add_percent`, `multiply`.

### 9.2 PeriodicBlock

| Field | Type | Required |
|-------|------|----------|
| `interval_ticks` | `int` | YES |
| `effects` | `EffectList` | YES |
| `max_ticks` | `int` | NO |

### 9.3 ConsumptionWindowBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `consume_on` | `enum` | YES | — |
| `allowed_abilities` | `list<string>` | NO | all abilities |
| `max_consumptions` | `int` | NO | `1` |
| `ability_overrides` | `list<AbilityOverride>` | NO | none |
| `on_consume_effects` | `EffectList` | NO | none |
| `consume_only_on_success` | `bool` | NO | `true` |

`consume_on` enum:

- `cast_ability`
- `damage_received`
- `on_hit`

This block is the canonical authoring surface for "next cast is empowered" and
"trigger once when I am hit during the window" behavior. The status remains active until it expires
or reaches `max_consumptions`. On each qualifying event, the runtime applies any matching
`ability_overrides`, executes `on_consume_effects`, increments the consumption count, and removes the
status if the maximum is reached.

### 9.4 AbilityOverride

| Field | Type | Required |
|-------|------|----------|
| `ability_id` | `string` | YES |
| `damage_multiplier` | `fixed` | NO |
| `radius_multiplier` | `fixed` | NO |
| `add_effects` | `EffectList` | NO |
| `replace_effects` | `EffectList` | NO |

Overrides are bounded, compile-time-known modifications applied to the consuming ability's IR before
resolution begins. `replace_effects` replaces the ability's authored `effects` list for that cast.
`add_effects` appends additional effects after the base list.

### 9.5 DamageAccumulatorBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `bind_total_as` | `string` | YES | — |
| `include_absorbed_damage` | `bool` | NO | `false` |

`damage_accumulator` tracks post-mitigation HP loss while the status is active. If
`include_absorbed_damage = true`, shield-absorbed damage also contributes to the total. The
compiled binding named by `bind_total_as` is available only to this status's `on_expire_effects`;
it is not emitted for cleanse/remove.

### 9.6 DeferredLedgerBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `freeze_observer_hp` | `bool` | NO | `true` |
| `remove_policy` | `enum` | NO | `resolve_immediately` |

`remove_policy` enum:

- `resolve_immediately`
- `discard`

`deferred_ledger` intercepts all HP damage and healing while the status is active, accumulates
damage and healing separately, and on expiry computes `net = healing - damage` as one HP mutation.
Original mitigation, anti-heal, and conversion rules are applied when the sub-events are recorded;
they are NOT re-run on release.

### 9.7 HpFloorBlock

| Field | Type | Required |
|-------|------|----------|
| `min_hp` | `fixed` | YES |

### 9.8 DeathPreventionBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `restore_hp_ratio` | `fixed` | YES | — |
| `consume_on_trigger` | `bool` | NO | `true` |
| `bypass_anti_heal` | `bool` | NO | `true` |

`death_prevention` is checked only if the entity remains lethal after any active `hp_floor`
policies have already been applied. The restore is a death-prevention rewrite, not an ordinary heal
for anti-heal purposes unless `bypass_anti_heal = false`.

### 9.9 MovementDamageBlock

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `damage_per_unit` | `fixed` | YES | — |
| `damage_type` | `enum` | YES | — |
| `max_damage_per_tick` | `fixed` | NO | uncapped |

`movement_damage` evaluates after all movement for the tick is committed and uses absolute world
position delta. Voluntary movement, forced displacement, and teleports all contribute. Arc/vertical
travel does not; only 2D spatial displacement in the engine plane is counted.

### 9.10 SpreadBlock

Declares autonomous status propagation that runs from the carrier's Arbiter after a bounded delay.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `delay_ticks` | `int` | YES | — |
| `query_radius` | `fixed` | YES | — |
| `max_generations` | `int` | YES | — |
| `max_targets_per_spread` | `int` | NO | `8` |
| `filter` | `FilterExpr` | YES | — |
| `apply_status_id` | `string` | YES | — |
| `dedup_scope` | `enum` | NO | `entity_once_per_chain` |
| `allow_spread_from_corpse` | `bool` | NO | `false` |

`dedup_scope` enum:

- `none`
- `entity_once_per_chain`

Validation rules:

1. `delay_ticks > 0`.
2. `query_radius > 0`.
3. `max_generations > 0`.
4. `max_targets_per_spread > 0`.
5. `apply_status_id` MUST reference a valid `StatusEffectDefinition`.

Lowering rule: each applied status instance stores the original `chain_id`, the current
`generation`, and the next `spread_at_tick`. When `spread_at_tick` is reached and the instance's
`generation < max_generations`, the carrier's Arbiter performs the authored query locally, skips
any candidate excluded by `dedup_scope`, and applies `apply_status_id` to the resulting targets as
generation `+1`. New child status instances inherit the original caster/owner identity for credit
and continue the same `chain_id`. If `entity_once_per_chain` is enabled, the root carrier is seeded
into the visited set before the first spread query runs.

### 9.11 TargetabilityPolicyBlock

Declares relation-scoped targeting and spatial-admission rules for an entity or active status.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `hostile_effects` | `bool` | NO | `true` |
| `allied_beneficial_effects` | `bool` | NO | `true` |
| `allied_harmful_effects` | `bool` | NO | `true` |
| `self_effects` | `bool` | NO | `true` |
| `affected_by_area_effects` | `bool` | NO | `true` |
| `collidable_for_skillshots` | `bool` | NO | `true` |
| `collidable_for_pathing` | `bool` | NO | `true` |

Classification rule: `healing`, `apply_buff`, `apply_shield`, `cleanse`, and other positive status
applications are beneficial. `damage`, `apply_debuff`, `apply_cc`, suspension, and other hostile
mutations are harmful. Mixed payloads are checked per component at admission time.

### 9.12 ObserverPresentationBlock

Declares team-scoped downstream presentation overrides. This affects only observer payloads, never
authoritative gameplay state.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `visible_to_enemies` | `bool` | NO | `true` |
| `visible_to_allies` | `bool` | NO | `true` |
| `visible_to_self` | `bool` | NO | `true` |
| `appearance_source` | `enum` | NO | `self` |
| `source_entity` | `EntityRef` | When `appearance_source = mirror_entity` | — |
| `enemy_hp_presentation` | `enum` | NO | `authoritative` |
| `ally_marker` | `enum` | NO | `none` |

`appearance_source` enum:

- `self`
- `mirror_entity`

`enemy_hp_presentation` enum:

- `authoritative`
- `full`
- `mirror_source_percent`

`ally_marker` enum:

- `none`
- `decoy_indicator`

Validation rule: `appearance_source = mirror_entity` requires `source_entity`.

### 9.13 SuspensionBlock

Declares a bounded state where an entity may be unable to act, invulnerable, or have its timers
paused.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mode` | `enum` | YES | — |
| `invulnerable` | `bool` | NO | `false` |
| `pause_status_timers` | `bool` | NO | `false` |
| `pause_ability_cooldowns` | `bool` | NO | `false` |
| `interrupt_active_casts` | `bool` | NO | `true` |
| `interrupt_active_channels` | `bool` | NO | `true` |
| `exclude_from_payloads` | `bool` | NO | `false` |

`mode` enum:

- `suspended`
- `dormant`
- `stasis`

Lowering rule:

- `suspended` suppresses active action execution through ordinary capability/targetability policy,
  but status timers and cooldowns continue unless explicitly paused.
- `dormant` lowers to `P-33` dormant-state metadata; ordinary active evaluation is skipped, but the
  entity may still appear in downstream payloads unless `exclude_from_payloads = true`.
- `stasis` is a suspension variant intended for full time-stop semantics. If timer/cooldown pausing
  is enabled, the runtime shifts expiry ticks forward by the authored stasis duration rather than
  mutating every timer per tick.

### 9.14 ProjectileInterceptBlock

Declares status-owned interception of incoming projectile actors.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mode` | `enum` | YES | — |
| `max_redirect_generations` | `int` | NO | `1` |
| `fallback_target` | `enum` | NO | `last_known_source_position` |
| `preserve_original_payload` | `bool` | NO | `true` |

`mode` enum:

- `reflect_to_source`

`fallback_target` enum:

- `last_known_source_position`
- `despawn`

Validation rules:

1. `max_redirect_generations > 0`.

Lowering rule: while the status is active, inbound projectile impacts are inspected during the
`P-61` PostDamage interception path after the local hit has been resolved through ordinary
protection/mitigation rules but before other reactive payloads are emitted. Matching projectiles
increment a bounded redirect-generation counter, swap controlling ownership to the intercepting
side, and retarget toward the original source entity. If the original source no longer exists,
`fallback_target` selects either a last-known-position return or immediate despawn. When
`preserve_original_payload = true`, the returned projectile reuses the original carried combat
payload instead of generating a new one.

### 9.15 ZoneRelationGateBlock

Declares hostile admission or damage gating based on a live zone actor referenced through runtime
state.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `zone_state` | `string` | YES | — |
| `require_target_inside` | `bool` | NO | `true` |
| `require_hostile_source_inside` | `bool` | NO | `false` |
| `reject_damage` | `bool` | NO | `true` |
| `reject_hostile_effects` | `bool` | NO | `true` |

Validation rules:

1. `zone_state` MUST reference a `RuntimeStateDefinition` of kind `bookmark`.
2. At least one of `reject_damage` or `reject_hostile_effects` MUST be `true`.

Lowering rule: during hostile target admission and PreMitigation, the runtime resolves the current
zone actor from `zone_state` and evaluates the live zone membership relation for defender and
source. If `require_target_inside = true`, the protected entity must still be inside the zone. If
`require_hostile_source_inside = true`, hostile sources outside the same live zone are rejected.
Missing source position (for example no local-or-Ghost pose) counts as outside. Rejected hostile
effects do not enter the combat pipeline, and rejected hostile damage components are zeroed before
ordinary mitigation.

### 9.16 MovementConstraintBlock

Declares a status-owned positional constraint sourced from a runtime bookmark. This is the canonical
authoring surface for leash/tether mechanics that clamp or punish movement beyond a stored anchor.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `anchor_state` | `string` | YES | — |
| `max_distance` | `fixed` | YES | — |
| `on_violation` | `enum` | NO | `clamp` |
| `damage_per_unit` | `fixed` | When `on_violation = damage` | — |
| `apply_to_forced_movement` | `bool` | NO | `true` |
| `apply_to_teleports` | `bool` | NO | `true` |

`on_violation` enum:

- `clamp`
- `reverse`
- `damage`

Validation rules:

1. `anchor_state` MUST reference a `RuntimeStateDefinition` of kind `bookmark`.
2. `max_distance > 0`.
3. `damage_per_unit > 0` when `on_violation = damage`.

Lowering rule: while the status is active, the runtime resolves the bookmark payload in
`anchor_state` each PostKinematic tick and runs the canonical `P-04` distance check against the
carrier's committed position. Bookmark payloads of kind `position` use the stored absolute world
coordinate; payloads of kind `entity_ref` use the referenced entity/actor's current local-or-Ghost
position. Voluntary movement is always constrained. `apply_to_forced_movement = false` allows
ordinary `P-02` displacement to bypass the clamp, and `apply_to_teleports = false` allows
`P-01`-style snaps to bypass it. When `on_violation = damage`, the runtime emits the excess-distance
combat event through the ordinary deferred `P-04` damage path from `docs-core/`.

### 9.17 ResourceStatLink

| Field | Type | Required |
|-------|------|----------|
| `pool_id` | `string` | YES |
| `stat_id` | `string` | YES |
| `operation` | `enum` | YES |
| `coefficient` | `fixed` | YES |

`operation` enum: `add_flat`, `add_percent`, `multiply`.

Validation rule: `(pool_id, stat_id, operation)` tuples MUST be unique within one status.

While the status is active, the runtime reads the carrier's CURRENT value of `pool_id` whenever it
builds that entity's effective stat snapshot and computes:

`modifier_value = current_resource(pool_id) * coefficient`

That value is then applied to `stat_id` through the authored `operation`, using the same
deterministic P-16 layering semantics as ordinary `stat_modifiers`. `resource_stat_links` read only
the carrier's own local resource pools; cross-entity credit must first mutate the carrier through
ordinary `modify_resource`.

### 9.18 Status Metadata Semantics

`polarity` enum:

- `positive` — beneficial statuses such as buffs, protections, or ally-granted utility
- `negative` — harmful statuses such as debuffs, DoTs, anti-heal, and crowd control
- `neutral` — hidden/system statuses that SHOULD NOT be targeted by ordinary buff/debuff authoring

`status_application_immunity` enum:

- `none`
- `negative`
- `positive`
- `all`

`duration_scaling` enum:

- `fixed`
- `status_resistance`

Validation rules:

1. `apply_buff` MUST reference `positive` statuses only.
2. `apply_debuff` MUST reference `negative` statuses only.
3. `passive_status_effects` on `EntityDefinition` MAY reference `positive` or `neutral` statuses, but MUST NOT reference `negative` statuses.
4. `cleanse` matches `polarity` and `is_cleansable` on the runtime status entry, plus optional
   `cc_categories` filtering when authored. `is_cleansable` governs removal of already-active
   statuses only.
5. `status_application_immunity` is checked before a new status is admitted to the target's active registry. This is independent of `is_cleansable`: an effect may be uncleanseable after admission yet still be blocked from admission by an active immunity window.
6. `duration_scaling = status_resistance` means the compiler/runtime MUST apply the target's `DefensiveStats.status_effect_resistance` modifier when admitting the status. Generated `apply_cc` statuses default to this unless the effect explicitly selects `fixed`.
7. `cc_immunity_categories` is the canonical authoring surface for Unstoppable / Super Armor style effects. While such a status is active, incoming statuses whose `cc_category` is in that list MUST be rejected before admission. `self_cc_immunity_during_cast` lowers to a temporary positive status using this same field.
8. `snapshot_recorder_state` MAY only reference runtime states of kind `snapshot_buffer`. While the
   status is active, it requests the engine's canonical P-05 history-buffer behavior. Recording
   timing, rewind semantics, and handoff preservation follow `docs-core/01-1-spatial-primitive-catalog.md`
   §3.5 instead of introducing a compiler-local variant.
9. `consumption_window.consume_on = cast_ability` is evaluated after the candidate cast passes base
   validation but before its resolution begins. `damage_received` and `on_hit` are evaluated in
   PostDamage.
10. `damage_accumulator.bind_total_as` is a compiler-local binding name that is only valid inside
    the same status's `on_expire_effects`.
11. `deferred_ledger.remove_policy = resolve_immediately` cashes out the currently accumulated net
    if the status is removed before natural expiry. `discard` removes the ledger without applying
    the stored net.
12. `hp_floor` is checked before `death_prevention`. If the floor leaves the entity alive,
    `death_prevention` does not trigger.
13. `movement_damage` uses absolute world coordinates and survives handoff because the tracked
    previous position is stored in authoritative world-space, not Arbiter-local space.
14. Entity-definition `targetability_policy` / `observer_presentation` provide the permanent base
    state. Active status overlays may replace those values while the status is present; when
    multiple overlays exist, the most restrictive targetability result wins per query channel.
15. `targetability_policy` is checked for explicit targeting, AoE admission, skillshot/collision
    inclusion, and pathing occupancy. If `affected_by_area_effects = false`, area pulses and
    overlap queries MUST skip the entity even when it is spatially inside the shape. If
    `collidable_for_pathing = false`, ordinary movement/pathing/body-separation logic MUST ignore
    the entity as a blocking body.
16. `observer_presentation` affects only downstream payloads. Appearance aliases, fake enemy HP
    bars, and ally-only decoy markers MUST NOT change the entity's authoritative HP, stats, or
    identity in gameplay logic.
17. `suspension.mode = stasis` is the canonical timer-pause path. When `pause_status_timers` or
    `pause_ability_cooldowns` is true, the runtime resumes those timers by shifting their expiry
    ticks forward by the elapsed stasis duration.
18. `movement_constraint` is evaluated in PostKinematic after all committed movement for the tick.
    Teleports, forced displacement, attached motion, and sweeps are all subject to the constraint
    unless the authored status explicitly opts out of that class.
19. `resource_stat_links` are evaluated from the carrier's own current resource pools at
    stat-snapshot time. `operation = add_percent` uses the same additive-percent layer as ordinary
    `stat_modifiers`; remote entities are never read directly through this surface.

---

## 10. RuntimeStateDefinition Schema

Defines a bounded per-entity runtime state slot that abilities and statuses may write, read, and
consume deterministically.

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `state_id` | `string` | YES | Unique |
| `kind` | `enum` | YES | One of `bookmark`, `snapshot_buffer`, `sequence_window`, `charge_pool` |
| `bookmark` | `BookmarkStateDef` | When `kind = bookmark` | — |
| `snapshot_buffer` | `SnapshotBufferStateDef` | When `kind = snapshot_buffer` | — |
| `sequence_window` | `SequenceWindowStateDef` | When `kind = sequence_window` | — |
| `charge_pool` | `ChargePoolStateDef` | When `kind = charge_pool` | — |

### 10.1 BookmarkStateDef

| Field | Type | Required |
|-------|------|----------|
| `payload` | `enum` | YES |
| `expires_after_ticks` | `int` | YES |
| `capture_topology_epoch` | `bool` | NO |
| `clear_on_owner_death` | `bool` | NO |

`payload` enum:

- `position`
- `entity_ref`

Bookmarks store one bounded payload plus expiry metadata. `position` stores absolute world
coordinates. `entity_ref` stores an authoritative entity/actor ID that may later be dereferenced to
its current position.

### 10.2 SnapshotBufferStateDef

| Field | Type | Required |
|-------|------|----------|
| `window_ticks` | `int` | YES |
| `sample_interval_ticks` | `int` | NO |
| `fields` | `list<enum>` | YES |
| `clear_on_read` | `bool` | NO |

`fields` enum:

- `position`
- `hp`

The compiler MUST reject snapshot buffers whose `window_ticks / sample_interval_ticks` would exceed
bounded runtime limits. Snapshot buffers are ring buffers keyed by tick and transfer intact on
handoff.

### 10.3 SequenceWindowStateDef

| Field | Type | Required |
|-------|------|----------|
| `max_step` | `int` | YES |
| `window_ticks` | `int` | YES |
| `reset_to_step` | `int` | NO |

Sequence windows model same-key combo routing. `reset_to_step` defaults to `0`.

### 10.4 ChargePoolStateDef

| Field | Type | Required |
|-------|------|----------|
| `capacity` | `int` | YES |
| `charge_types` | `list<string>` | NO |
| `recharge_mode` | `enum` | NO |
| `recharge_interval_ticks` | `int` | When `recharge_mode != none` |
| `decay_mode` | `enum` | NO |
| `decay_ticks` | `int` | When `decay_mode != none` |
| `min_use_interval_ticks` | `int` | NO |

`recharge_mode` enum:

- `none`
- `independent`
- `all_at_once`

`decay_mode` enum:

- `none`
- `all_at_once`
- `oldest_first`

This block covers both self-recharging ability charges and shared typed charge pools. If
`charge_types` is omitted, the pool behaves as an untyped count-only charge model. If
`charge_types` is present, charge entries preserve insertion order and downstream effects MAY branch
or scale on both count and composition.

---

## 11. ComboMatrixDefinition Schema

Game-data lookup table for combo field × finisher interactions (P-64).

```yaml
combo_matrix:
  - field: fire
    finisher: leap
    effects:
      - type: apply_buff
        target: caster
        status_id: fire_shield
        duration_ticks: 300
  - field: water
    finisher: blast
    effects:
      - type: aoe_heal
        center: finisher_position
        radius: 5.0
        amount: 200
```

| Field | Type | Required |
|-------|------|----------|
| `field` | `enum` | YES |
| `finisher` | `enum` | YES |
| `effects` | `EffectList` | YES |

Field enum: `fire`, `water`, `lightning`, `poison`, `smoke`, `ice`, `light`, `dark`, `ethereal`, `oil`.
Finisher enum: `projectile`, `blast`, `whirl`, `leap`.

The matrix MUST NOT contain duplicate `(field, finisher)` pairs.
`effects` MUST NOT be empty.

`combo_matrix` effects resolve in the finisher's ordinary execution context: `caster` remains the
finisher user/source, not the field owner. In addition, combo-resolution payloads MAY reference the
following contextual refs:

- `combo_field_entity` — the specific live field/zone actor that admitted the combo
- `combo_field_owner` — the source/owner identity associated with that field actor
- `combo_field_position` — the field actor's authoritative current position, snapshotted at combo admission
- `finisher_position` — the resolved combo interaction point for the finisher, snapshotted at combo admission

This allows deterministic field replacement without inventing a second combo-specific spawn system.
For example, an oil field can author `effects = [despawn_entity(combo_field_entity), zone(position =
combo_field_position, owner = combo_field_owner, ...)]`. Any qualifying finisher may therefore
trigger the combo, while ownership of the replacement field remains explicit in authored data.

---

## 12. Common Sub-Schemas

### 12.1 EntityRef

Refers to an entity in the ability context:

| Value | Meaning |
|-------|---------|
| `caster` | The entity casting the ability |
| `target` | The targeted entity (for single-target abilities) |
| `participant` | Current participant while resolving `GroupResultBlock.apply_to = all_participants` |
| `combo_field_entity` | The live field actor that admitted the current combo-matrix result |
| `combo_field_owner` | The owner/source identity associated with the current combo field |
| `projected_actor` | The live controlled actor inside `control_projection` callback effect lists |
| `transit_actor` | The live actor that just completed `start_actor_transit` |
| `{ binding: name }` | Runtime binding from a prior instruction |
| `{ state_entity: state_id }` | Entity/actor reference stored in a runtime state |

When targeting uses a dead/corpse filter, `target` or any bound entity ref may resolve to a
corpse-registry handle keyed by the original entity ID rather than to a currently active entity.
`combo_field_entity` and `combo_field_owner` are valid only inside `combo_matrix` payloads.
`projected_actor` is valid only inside `control_projection` callback payloads.
`transit_actor` is valid only inside `start_actor_transit.on_arrival_effects`.

### 12.2 PositionRef

Refers to a position:

| Value | Meaning |
|-------|---------|
| `caster_position` | Caster's current position |
| `target_position` | Target's current position |
| `participant_position` | Current participant's position while resolving `GroupResultBlock.apply_to = all_participants` |
| `cursor_position` | Requested ground-target from Edge Node |
| `finisher_position` | Combo-matrix finisher interaction point for the current combo result |
| `combo_field_position` | Combo-matrix field actor position snapshotted at combo admission |
| `projected_actor_position` | Controlled actor position snapshotted for a `control_projection` callback payload |
| `transit_actor_position` | Arrived actor position snapshotted for a `start_actor_transit` callback payload |
| `{ binding: name }` | Runtime binding (e.g., resolved landing position) |
| `{ state_position: state_id }` | Position stored in a runtime state |
| `{ state_entity_position: state_id }` | CURRENT position of the entity/actor stored in a runtime state |

If the current `target` resolves to a corpse-registry entry, `target_position` means that corpse's
stored death position.
`finisher_position` and `combo_field_position` are valid only inside `combo_matrix` payloads.
`projected_actor_position` is valid only inside `control_projection` callback payloads.
`transit_actor_position` is valid only inside `start_actor_transit.on_arrival_effects`.

### 12.3 FilterExpr

Target filtering expression:

| Value | Meaning | Primitive |
|-------|---------|-----------|
| `enemy_alive` | Hostile, alive entities | P-13 |
| `ally_alive` | Friendly, alive entities | P-13 |
| `all_alive` | Any alive entity | P-13 |
| `ally_dead` | Friendly corpses | P-13 + P-47 |
| `enemy_dead` | Hostile corpses | P-13 + P-47 |
| `all_dead` | Any corpses | P-13 + P-47 |
| `ally_downed` | Friendly entities in a non-zero active downed phase | P-13 + P-25 |
| `enemy_downed` | Hostile entities in a non-zero active downed phase | P-13 + P-25 |
| `all_downed` | Any entities in a non-zero active downed phase | P-13 + P-25 |
| `self` | Caster only | — |

### 12.4 ResourceCost

`ResourceCost` is reusable across base abilities and activation-mode overrides.

```yaml
resource_cost:
  pool: mana
  amount: 30
  escalation:
    multiplier_per_stack: 1.5
    decay_interval_ticks: 240
    shared_counter_id: desperation_heal
```

### 12.5 ScalingExpr

Defines how a value scales with stats:

```yaml
scaling:
  stat: attack_power
  coefficient: 1.5
  formula_id: physical_damage  # Optional: references a FormulaDefinition
```

```yaml
scaling:
  binding: remaining_shield
  coefficient: 1.0
```

Exactly one of `stat` or `binding` MUST be supplied. `binding` reads a compiler-emitted scalar
binding from an earlier effect or lifecycle hook.

### 12.6 GuardExpr (YAML form)

Conditions for triggers and conditional effects. Compiled to `GuardExpr` in the IR.

```yaml
condition:
  hp_below: { entity: target, threshold: 0.25 }  # % of max HP
```

```yaml
condition:
  and:
    - has_buff: { entity: caster, status_id: enraged }
    - hp_above: { entity: caster, threshold: 0.5 }
```

Supported guard types: `hp_below`, `hp_above`, `has_buff`, `stack_count`, `is_in_zone`, `facing_toward`, `not`, `and`, `or`.

### 12.7 StatePredicate

Used by `ActivationModes` to choose a state-dependent ability variant.

Supported predicates:

- `{ state_present: state_id }`
- `{ state_absent: state_id }`
- `{ sequence_step: { state_id: string, step: int } }`
- `{ charge_count: { state_id: string, op: enum, value: int } }`

`op` enum: `eq`, `gte`, `lte`.

### 12.8 LoadoutSource

Used by `swap_identity` to choose either a static named profile or a runtime snapshot source.

Supported forms:

- `{ self_profile: string }`
- `{ entity_current_loadout: EntityRef }`

- `{ corpse_snapshot: EntityRef }`

`corpse_snapshot` requires the referenced corpse record to exist and the source entity type to have
`corpse_profile.retain_loadout_snapshot = true`. The reference resolves only against the CURRENT
Arbiter's authoritative corpse registry.

### 12.9 CorpseStatBindingDef

Used by `consume_corpse` to expose selected corpse stat snapshots to downstream bindings.

| Field | Type | Required |
|-------|------|----------|
| `stat_id` | `string` | YES |
| `binding` | `string` | YES |

---

## 13. Validation Rules Summary

### 13.1 Structural (Tier 1)

| Rule | Applies To |
|------|-----------|
| Required fields present | All schemas |
| Field types match declared type | All schemas |
| Enum values from closed domain | All enum fields |
| List lengths within bounds | All list fields |
| Numeric values are finite | All numeric fields |

### 13.2 Semantic (Tier 2)

| Rule | Applies To |
|------|-----------|
| `ability_id` unique across game image | AbilityDefinition |
| `status_id` unique across game image | StatusEffectDefinition |
| `state_id` unique across game image | RuntimeStateDefinition |
| Resource pool ID exists in entity definitions | `resource_cost`, `modify_resource`, `resource_stat_links` |
| Stat ID exists in entity definitions | `stat_modifiers`, `scaling`, `resource_stat_links` |
| Referenced ability/status IDs exist | `abilities`, `passive_status_effects` |
| Referenced runtime-state IDs exist | `write_state`, `clear_state`, `restore_from_state`, `advance_sequence`, `modify_charge_pool`, `snapshot_recorder_state`, `ActivationModes`, state-backed refs |
| `profile_id` unique within entity definition | `loadout_profiles` |
| Referenced `loadout_profile_id` exists on the same entity definition | `control_topology`, `{ self_profile: ... }` |
| `members` count <= `max_multiplex_group_size` | `control_topology` |
| `many_to_one` topologies define at least 2 members | `control_topology` |
| `one_to_many` topologies define exactly 1 primary member | `control_topology` |
| `many_to_one` topologies define at most 1 primary member | `control_topology` |
| `role_split` topologies define at least one `movement_only` or `full` role | `control_topology` |
| `occupant_storage_mode = off_world_stored` requires `occupant_can_be_targeted = false` and `occupant_cast_policy = none` | `container_profile` |
| `timeout_ticks > 0` | `group_interaction` |
| `steps` non-empty and each `time_limit_ticks > 0` | `group_interaction.sequential` |
| `options` unique and `default_option_id` in `options` | `group_interaction.simultaneous` |
| `required_counts.option_id` / `option_sequence` entries reference declared options | `group_interaction.simultaneous` |
| `cast_time > 0` when `channel` is present | AbilityDefinition |
| `tick_interval_ticks > 0` when `channel.execution_mode = tick_while_active` | `channel` |
| `continuous_input != none` requires `channel.execution_mode = tick_while_active` | `channel` |
| `partial_cooldown_refund` in `[0, 1]` | `channel` |
| `concentration` only valid when `requires_concentration = true` | AbilityDefinition |
| `channel` and `requires_concentration` are mutually exclusive | AbilityDefinition |
| `max_duration_ticks > 0` when authored | `concentration` |
| `schedule_lead_ticks > 0` | `global_event` |
| `targeting.type` is `none` or `self` when `global_event` is present | AbilityDefinition |
| `radius > 0` when `global_event.geometry = circle` or `ring` | `global_event` |
| `0 <= ring_inner < radius` when `global_event.geometry = ring` | `global_event` |
| `pulse_interval_ticks` and `duration_ticks` are both present or both omitted | `global_event` |
| `member_bindings` length in `[2, max_multiplex_group_size]` and entries unique | `split_form` |
| `member_bindings` resolve to prior single-spawn `spawn_actor.output_binding` entries in the same ability | `split_form` |
| `follow_distance >= 0` when `inactive_mode = follow_active` | `split_form` |
| `source_ability_id` references an ability that authors `split_form` | `cycle_split_form` |
| `max_targets` <= `selector_max_targets` | TargetingBlock |
| `start_offset_ticks + duration_ticks <= cast_time_ticks` | `vulnerability_window` |
| `chance_stat` references a valid derived stat | `block_defense` |
| `same_arbiter_only` remote-target rejection is enforced | `swap_hp_percent` |
| Spawn count <= `max_spawns_per_rule` | `spawn_actor` |
| `count = 1` when `loadout_projection`, `control_projection`, or `respawn_anchor` is authored | `spawn_actor` |
| `max_hp_multiplier > 0` and `stat_multiplier > 0` | `loadout_projection` |
| `suspend_owner` is used when a spawned actor may later `restore_owner` | `control_projection` |
| `respawn_delay_ticks > 0` | `respawn_anchor` |
| `speed > 0` and `arrival_radius > 0` | `start_actor_transit` |
| `hp_ratio` in `(0, 1]` | `revive_corpse`, `restore_phase` |
| `corpse` resolves to a corpse-registry entry | `revive_corpse`, `consume_corpse(selection = target)`, `{ corpse_snapshot: ... }` |
| `filter` is a dead/corpse filter | `consume_corpse` |
| `persist_ticks > 0` when `corpse_profile` is authored | `corpse_profile` |
| `rally_hp_ratio` in `(0, 1]` | `downed_state` |
| `ghost_duration_ticks > 0`, `respawn_delay_credit_ticks` in `[0, ghost_duration_ticks]`, and `ghost_ability_set` non-empty | `ghost_phase` |
| Combo matrix has no duplicate `(field, finisher)` pairs | ComboMatrixDefinition |
| Binding references resolve to a prior effect's `output_binding` | `{ binding: name }` refs |

### 13.3 Determinism (Tier 3)

| Rule | Applies To |
|------|-----------|
| All numeric literals normalize to `I32F32` | All numeric fields |
| No floating-point values survive past normalization | All schemas |
| Effect lists are bounded (`MAX_INSTRUCTIONS_PER_ABILITY`) | AbilityDefinition |
| Binding table is bounded (`MAX_BINDINGS_PER_ABILITY`) | AbilityDefinition |
| Periodic effects have finite `max_ticks` or status `duration_ticks` | PeriodicBlock |
| Reactive trigger effects comply with deferred execution rule | TriggerDefinition |
| Runtime states declare bounded capacity/window | RuntimeStateDefinition |
| ActivationModes use first-match deterministic order | AbilityDefinition |

### 13.4 Compatibility (Tier 4)

| Rule | Applies To |
|------|-----------|
| Schema version matches compiler version | All schemas |
| Adapter API major version compatible | Game image metadata |
| Wire schema version intersects runtime capabilities | Game image metadata |

---

## 14. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `01-designer-language.md` | Defines the grammar and module layout. This document defines the field-level schemas within those modules. |
| `01-2-lua-whitelisted-api.md` | Defines callable symbols in Lua. Each mutation symbol corresponds to an effect type in §6. |
| `03-compiler-pipeline.md` | Phase 1 parses these schemas; Phase 2 validates them. |
| `03-1-compiler-ir-specification.md` | Defines the compilation target. Each schema field maps to an IR element (metadata, instruction, directive, or guard). |
| `ability-primitives/` | The 66 primitives that effects and triggers map to. |
