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
| `targeting` | `TargetingBlock` | YES | — | IR instructions (P-09/P-13) | See §5.2. |
| `self_cc_immunity_during_cast` | `enum` | NO | `none` | `AbilityIRBlock.self_cc_immunity_during_cast` | One of: `none`, `push_immune`, `full_super_armor`. |
| `can_counter_vulnerability_window` | `bool` | NO | `false` | `AbilityIRBlock.can_counter_vulnerability_window` | P-65: flags ability as eligible to trigger vulnerability-window counters. |
| `can_be_counterspelled` | `bool` | NO | `true` | `AbilityIRBlock.can_be_counterspelled` | P-40: this ability can be counterspelled mid-cast. |
| `combo_finisher` | `enum` | NO | `none` | `AbilityIRBlock.combo_finisher` | One of: `none`, `projectile`, `blast`, `whirl`, `leap`. |
| `requires_concentration` | `bool` | NO | `false` | `AbilityIRBlock.requires_concentration` | P-55: maintained effect. |
| `stagger_damage` | `fixed` | NO | `0` | IR instruction params | P-48: parallel stagger damage. |

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

### 5.6 Full Example: SK-01 (Toss) in YAML

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

`cc_type` enum: `stun`, `root`, `silence`, `sleep`, `disarm`, `blind`, `mute`, `fear`, `charm`, `taunt`.

`category` enum (for immunity checking): `displacement`, `hard_disable`, `soft_disable`, `forced_movement`, `target_override`, `mute`.

### 6.6 `apply_buff` / `apply_debuff`

| Field | Type | Required | Primitive |
|-------|------|----------|-----------|
| `target` | `EntityRef` | YES | — |
| `status_id` | `string` | YES | References a StatusEffectDefinition |
| `duration_ticks` | `int` | YES | Status duration |
| `stacks` | `int` | NO | P-42 (Stacking Counters) |

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
| `stat_modifiers` | `list<StatModifier>` | NO | P-16 (Stat Layering) |
| `capability_flags` | `map<string, bool>` | NO | P-26 (Capability Bitmask) |
| `periodic_effects` | `PeriodicBlock` | NO | P-44 (Pulse Timer) for DoTs/HoTs |
| `on_expire_effects` | `EffectList` | NO | Effects when status expires |
| `is_passive` | `bool` | NO | Affected by Mute (P-26 PASSIVES_ACTIVE) |
| `cc_category` | `enum` | NO | P-62 category for immunity checking |
| `is_cleansable` | `bool` | NO | Default true |

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

---

## 10. ComboMatrixDefinition Schema

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

## 11. Common Sub-Schemas

### 11.1 EntityRef

Refers to an entity in the ability context:

| Value | Meaning |
|-------|---------|
| `caster` | The entity casting the ability |
| `target` | The targeted entity (for single-target abilities) |
| `{ binding: name }` | Runtime binding from a prior instruction |

### 11.2 PositionRef

Refers to a position:

| Value | Meaning |
|-------|---------|
| `caster_position` | Caster's current position |
| `target_position` | Target's current position |
| `cursor_position` | Requested ground-target from Edge Node |
| `{ binding: name }` | Runtime binding (e.g., resolved landing position) |

### 11.3 FilterExpr

Target filtering expression:

| Value | Meaning | Primitive |
|-------|---------|-----------|
| `enemy_alive` | Hostile, alive entities | P-13 |
| `ally_alive` | Friendly, alive entities | P-13 |
| `all_alive` | Any alive entity | P-13 |
| `enemy_dead` | Hostile corpses | P-13 + P-47 |
| `self` | Caster only | — |

### 11.4 ScalingExpr

Defines how a value scales with stats:

```yaml
scaling:
  stat: attack_power
  coefficient: 1.5
  formula_id: physical_damage  # Optional: references a FormulaDefinition
```

### 11.5 GuardExpr (YAML form)

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

---

## 12. Validation Rules Summary

### 12.1 Structural (Tier 1)

| Rule | Applies To |
|------|-----------|
| Required fields present | All schemas |
| Field types match declared type | All schemas |
| Enum values from closed domain | All enum fields |
| List lengths within bounds | All list fields |
| Numeric values are finite | All numeric fields |

### 12.2 Semantic (Tier 2)

| Rule | Applies To |
|------|-----------|
| `ability_id` unique across game image | AbilityDefinition |
| `status_id` unique across game image | StatusEffectDefinition |
| Resource pool ID exists in entity definitions | `resource_cost` |
| Stat ID exists in entity definitions | `stat_modifiers`, `scaling` |
| Referenced ability/status IDs exist | `abilities`, `passive_status_effects` |
| `max_targets` <= `selector_max_targets` | TargetingBlock |
| Spawn count <= `max_spawns_per_rule` | `spawn_actor` |
| Combo matrix has no duplicate `(field, finisher)` pairs | ComboMatrixDefinition |
| Binding references resolve to a prior effect's `output_binding` | `{ binding: name }` refs |

### 12.3 Determinism (Tier 3)

| Rule | Applies To |
|------|-----------|
| All numeric literals normalize to `I32F32` | All numeric fields |
| No floating-point values survive past normalization | All schemas |
| Effect lists are bounded (`MAX_INSTRUCTIONS_PER_ABILITY`) | AbilityDefinition |
| Binding table is bounded (`MAX_BINDINGS_PER_ABILITY`) | AbilityDefinition |
| Periodic effects have finite `max_ticks` or status `duration_ticks` | PeriodicBlock |
| Reactive trigger effects comply with deferred execution rule | TriggerDefinition |

### 12.4 Compatibility (Tier 4)

| Rule | Applies To |
|------|-----------|
| Schema version matches compiler version | All schemas |
| Adapter API major version compatible | Game image metadata |
| Wire schema version intersects runtime capabilities | Game image metadata |

---

## 13. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `01-designer-language.md` | Defines the grammar and module layout. This document defines the field-level schemas within those modules. |
| `01-2-lua-whitelisted-api.md` | Defines callable symbols in Lua. Each mutation symbol corresponds to an effect type in §6. |
| `03-compiler-pipeline.md` | Phase 1 parses these schemas; Phase 2 validates them. |
| `03-1-compiler-ir-specification.md` | Defines the compilation target. Each schema field maps to an IR element (metadata, instruction, directive, or guard). |
| `ability-primitives/` | The 65 primitives that effects and triggers map to. |
