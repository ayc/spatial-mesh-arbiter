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
| `requires_concentration` | `bool` | NO | `false` | `AbilityIRBlock.requires_concentration` | P-55: maintained effect. |
| `stagger_damage` | `fixed` | NO | `0` | IR instruction params | P-48: parallel stagger damage. |

`self_cc_immunity_during_cast` is authoring sugar for a temporary positive status applied for the cast
window. `push_immune` lowers to `cc_immunity_categories = [displacement]`. `full_super_armor`
lowers to a temporary status that grants immunity to every canonical CC category.

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

### 5.8 Full Example: SK-01 (Toss) in YAML

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

`polarity` enum: `negative`, `positive`, `all`.

`cleanse` removes matching active status entries from the target's authoritative status registry in a single mutation batch. Matching is driven by compiled status metadata, not string tags. If `require_cleansable = true`, only statuses with `is_cleansable = true` are removed. Generated `apply_cc` statuses participate automatically because they are lowered into the same runtime status registry. Abilities that also grant an immunity window SHOULD follow `cleanse` with `apply_buff` of a positive status whose `status_application_immunity` field declares what new statuses are blocked during the window.

### 6.7 `spawn_actor`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `archetype_id` | `string` | YES | P-32 (Actor Spawning) |
| `position` | `PositionRef` | YES | Spawn location |
| `owner` | `EntityRef` | NO | Defaults to caster |
| `lifetime_ticks` | `int` | YES | Bounded actor duration |
| `count` | `int` | NO | Default 1. MUST be <= `max_spawns_per_rule`. |
| `projectile` | `ProjectileBlock` | NO | Projectile-specific fields (see §6.7.1) |

#### 6.7.1 ProjectileBlock (optional, for projectile/trap actors)

| Field | Type | Required | Mapping |
|-------|------|----------|---------|
| `speed` | `fixed` | YES | Projectile velocity (units/tick) |
| `homing` | `bool` | NO | Default false. If true, `turn_rate` is required. |
| `turn_rate` | `fixed` | When homing | P-03: max angular change per tick |
| `pierce` | `int` | NO | Default 0. Targets passed through before stopping. |
| `arming_delay_ticks` | `int` | NO | Default 0. Ticks before detonation-capable triggers arm. |
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

#### 6.7.3 Compilation Path: Ability → Entity Archetype

Projectile fields defined in `spawn_actor.projectile` do NOT compile into the ability's `AbilityIRBlock`. Instead, the compiler merges them into the **entity archetype** referenced by `archetype_id`. The data flow is:

1. The ability's `spawn_actor` effect compiles to a P-32 (Actor Spawning) `IRDirective` carrying the `archetype_id`.
2. The `ProjectileBlock` fields compile into the `EntityDefinitions` section (0x11) of the game image, as part of the archetype's data.
3. At runtime, when the engine processes the P-32 directive and calls `initialize_spawn_configuration`, the adapter reads the archetype's projectile fields from the game image's `EntityDefinitions` and returns them in the `SpawnConfiguration`.
4. The engine uses the archetype's `ProjectileDetonationPolicy`, `arming_delay_ticks`, `pierce`, `homing`, and `turn_rate` to configure the spawned `ProjectileActor`.

This separation exists because projectile configuration is per-entity-type (all fireballs behave the same), not per-ability-cast. Multiple abilities can spawn the same projectile archetype with different damage values but identical flight/detonation behavior.

#### 6.7.4 Shared-Archetype Conflict Rule

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

### 6.9 `steering`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | P-03 (Trajectory Steering) |
| `mode` | `enum` | YES | `toward_source` (charm), `away_from_source` (fear), `toward_target` (homing) |
| `duration_ticks` | `int` | YES | Steering duration |

### 6.10 `value_conversion`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `source_type` | `enum` | YES | Input value type (e.g., `damage_dealt`, `resource_destroyed`) |
| `target_type` | `enum` | YES | Output value type (e.g., `healing`, `damage`) |
| `ratio` | `fixed` | YES | Conversion scalar |
| `target` | `EntityRef` | YES | P-21 (Value Conversion) |

### 6.11 `zone`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `position` | `PositionRef` | YES | P-32 (Actor Spawning) zone actor |
| `shape` | `enum` | YES | Zone shape |
| `radius` | `fixed` | YES | Zone dimension |
| `duration_ticks` | `int` | YES | Zone lifetime |
| `pulse_interval_ticks` | `int` | NO | P-44 (Pulse Timer) |
| `pulse_effects` | `EffectList` | When pulse | Effects per pulse |
| `enter_effects` | `EffectList` | NO | P-14 OnEnter effects |
| `leave_effects` | `EffectList` | NO | P-14 OnLeave effects |
| `combo_field_type` | `enum` | NO | P-64 combo field tag |
| `attached_to` | `EntityRef` | NO | P-06 (Attached Kinematics) |

### 6.12 `write_state`

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

### 6.13 `clear_state`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `state_id` | `string` | YES | Runtime-state mutation |

`clear_state` removes any currently active payload for the referenced runtime state slot.

### 6.14 `restore_from_state`

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

### 6.15 `advance_sequence`

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

### 6.16 `modify_charge_pool`

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
| `rally_channel_ticks` | `int` | YES |
| `finish_channel_ticks` | `int` | YES |

---

## 8. TriggerDefinition Schema

Reactive hooks that fire in response to combat events. Compile to PostDamage or DeathCheck IR instructions.

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `hook` | `enum` | YES | See hook mapping below |
| `condition` | `GuardExpr` | NO | Compiled to IR guard |
| `effects` | `EffectList` | YES | Effect chain to execute on trigger |

Hook enum → primitive mapping:

| Hook | Primitive | Pipeline Stage |
|------|-----------|---------------|
| `on_hit` | P-35 | PostDamage |
| `on_damage_received` | P-36 | PostDamage |
| `on_crit` | P-37 | PostDamage |
| `on_block` | P-38 | PostDamage |
| `on_death` | P-39 | DeathCheck |
| `on_cast` | P-40 | IntentValidation |

Trigger effects are subject to the deferred execution rule (`03-1-compiler-ir-specification.md` §6.1): combat events generated by PostDamage triggers are queued for the next tick.

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

### 9.5 Status Metadata Semantics

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
4. `cleanse` matches `polarity` and `is_cleansable` on the runtime status entry. `is_cleansable` governs removal of already-active statuses only.
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
    finisher: projectile
    effect: { type: apply_buff, status_id: burning, duration_ticks: 300 }
  - field: water
    finisher: blast
    effect: { type: aoe_heal, center: finisher_position, radius: 5.0, amount: 200 }
```

| Field | Type | Required |
|-------|------|----------|
| `field` | `enum` | YES |
| `finisher` | `enum` | YES |
| `effect` | `EffectDefinition` | YES |

Field enum: `fire`, `water`, `lightning`, `poison`, `smoke`, `ice`, `light`, `dark`, `ethereal`.
Finisher enum: `projectile`, `blast`, `whirl`, `leap`.

The matrix MUST NOT contain duplicate `(field, finisher)` pairs.

---

## 12. Common Sub-Schemas

### 12.1 EntityRef

Refers to an entity in the ability context:

| Value | Meaning |
|-------|---------|
| `caster` | The entity casting the ability |
| `target` | The targeted entity (for single-target abilities) |
| `{ binding: name }` | Runtime binding from a prior instruction |
| `{ state_entity: state_id }` | Entity/actor reference stored in a runtime state |

### 12.2 PositionRef

Refers to a position:

| Value | Meaning |
|-------|---------|
| `caster_position` | Caster's current position |
| `target_position` | Target's current position |
| `cursor_position` | Requested ground-target from Edge Node |
| `{ binding: name }` | Runtime binding (e.g., resolved landing position) |
| `{ state_position: state_id }` | Position stored in a runtime state |
| `{ state_entity_position: state_id }` | CURRENT position of the entity/actor stored in a runtime state |

### 12.3 FilterExpr

Target filtering expression:

| Value | Meaning | Primitive |
|-------|---------|-----------|
| `enemy_alive` | Hostile, alive entities | P-13 |
| `ally_alive` | Friendly, alive entities | P-13 |
| `all_alive` | Any alive entity | P-13 |
| `enemy_dead` | Hostile corpses | P-13 + P-47 |
| `self` | Caster only | — |

### 12.4 ScalingExpr

Defines how a value scales with stats:

```yaml
scaling:
  stat: attack_power
  coefficient: 1.5
  formula_id: physical_damage  # Optional: references a FormulaDefinition
```

### 12.5 GuardExpr (YAML form)

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

### 12.6 StatePredicate

Used by `ActivationModes` to choose a state-dependent ability variant.

Supported predicates:

- `{ state_present: state_id }`
- `{ state_absent: state_id }`
- `{ sequence_step: { state_id: string, step: int } }`
- `{ charge_count: { state_id: string, op: enum, value: int } }`

`op` enum: `eq`, `gte`, `lte`.

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
| Resource pool ID exists in entity definitions | `resource_cost` |
| Stat ID exists in entity definitions | `stat_modifiers`, `scaling` |
| Referenced ability/status IDs exist | `abilities`, `passive_status_effects` |
| Referenced runtime-state IDs exist | `write_state`, `clear_state`, `restore_from_state`, `advance_sequence`, `modify_charge_pool`, `snapshot_recorder_state`, `ActivationModes`, state-backed refs |
| `max_targets` <= `selector_max_targets` | TargetingBlock |
| Spawn count <= `max_spawns_per_rule` | `spawn_actor` |
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
