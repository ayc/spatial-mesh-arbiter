# Compiler IR Specification

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define the Intermediate Representation (IR) that the Game Compiler emits when lowering designer-authored Lua ability definitions into engine-executable primitive chains. This IR is the compilation target — the contract between the compiler and the engine runtime.

**Relationship to docs-core/:** This specification proposes the canonical pipeline stages that the engine MUST support for ability resolution. It serves as the compiler team's concrete answer to `docs-core/PRIMITIVE_IMPACT_ASSESSMENT.md` Amendment B (Adapter Hook Taxonomy). The engine team should validate and adopt these stages into `04-1-game-adapter-contract.md`.

---

## 1. IR Overview

The compiler transforms a designer's Lua ability definition into an **Ability IR Block** — a static, deterministic data structure that the engine evaluates at runtime. The IR Block is stored in the compiled game image's Ability IR Table section (`04-game-image-format.md` §3, section type 0x10).

An Ability IR Block consists of:
1. **Metadata** — ability ID, cooldown, resource cost, targeting type, cast time
2. **Instruction list** — an ordered sequence of IR Instructions
3. **Directive list** — cross-cutting primitive declarations not bound to one pipeline stage
4. **Binding table** — named intermediate values passed between instructions/directives

```
AbilityIRBlock {
    ability_id:       AbilityId,
    cooldown_ticks:   u32,
    resource_pool:    PoolId,         // Which resource pool to debit (e.g., mana, energy, rage)
    resource_cost:    SimFixed,       // Amount to debit from the pool
    cast_time_ticks:  u32,
    targeting_type:   TargetingType,    // SingleTarget | AoE | Self | None
    self_cc_immunity_during_cast: Option<CcImmunityTier>,
    can_counter_vulnerability_window: bool,  // P-65: this ability can trigger a vulnerability-window counter
    can_be_counterspelled: bool,        // P-40: this ability can be counterspelled mid-cast
    combo_finisher:   Option<ComboFinisherType>,  // P-64: finisher classification
    requires_concentration: bool,       // P-55: maintained effect
    instructions:     Vec<IRInstruction>,
    directives:       Vec<IRDirective>,
    bindings:         Vec<BindingSlot>,
}
```

## 2. IR Instructions

Each instruction invokes exactly one primitive at a specific pipeline stage.

```
IRInstruction {
    primitive:   PrimitiveId,    // P-01 through P-65
    stage:       PipelineStage,  // Which tick-loop phase this executes in
    params:      ParamBlock,     // Primitive-specific parameters (compile-time constants + binding refs)
    output:      Option<BindingRef>,  // Named output for downstream instructions
    guard:       Option<GuardExpr>,   // Conditional: only execute if guard evaluates true
}
```

### 2.1 Parameter Blocks

Parameters are either **compile-time constants** (embedded in the IR) or **binding references** (resolved at runtime from a previous instruction's output).

```
enum ParamValue {
    Const(SimFixed),
    ConstInt(i32),
    ConstBool(bool),
    ConstEnum(u16),            // Index into a compile-time enum table
    Binding(BindingRef),       // Runtime value from a prior instruction
    EntityField(FieldPath),    // Read from caster/target entity state
}
```

### 2.2 Guards

Guards enable conditional branching without arbitrary scripting. A guard is a compile-time expression over entity state:

```
enum GuardExpr {
    HpBelow(EntityRef, SimFixed),       // P-17: target HP < threshold
    HpAbove(EntityRef, SimFixed),
    HasBuff(EntityRef, BuffId),
    StackCount(EntityRef, PoolId, CompareOp, u8),
    IsInZone(EntityRef, ZoneTypeId),
    FacingToward(EntityRef, EntityRef, SimFixed),  // P-12: dot product > threshold
    Not(Box<GuardExpr>),
    And(Box<GuardExpr>, Box<GuardExpr>),
    Or(Box<GuardExpr>, Box<GuardExpr>),
}
```

Guards are evaluated by the engine, not by Lua. The compiler lowers Lua `if` statements into guard expressions at compile time. Unbounded or recursive conditions MUST be rejected by the compiler.

### 2.3 Binding Table

Instructions communicate via named bindings. The binding table has a fixed, bounded size per ability (compile-time allocated).

```
BindingSlot {
    name:  &str,        // e.g., "targets_0", "damage_amount", "nearest_corpse"
    type:  BindingType, // EntitySet | SimFixed | EntityId | Bool | Vec2F
}
```

Example flow for Chain Lightning (SK-09):
1. Directive 1 (P-32, ActorSpawn): spawn projectile actor `→ "projectile_0"`
2. Instruction 2 (P-11, NearestNeighbor): `input ← "projectile_0".position`, `output → "next_target"`
3. Instruction 3 (P-35, OnHitHook): `input ← "next_target"`, registers the chain bounce

### 2.4 IR Directives

Some primitives are **cross-cutting declarations** rather than one-shot stage-local instructions. The compiler emits these as `IRDirective` entries attached to the `AbilityIRBlock`.

```
IRDirective {
    primitive: PrimitiveId,      // Only cross-cutting primitives are legal here
    params:    ParamBlock,
    guard:     Option<GuardExpr>,
}
```

Directives have no `stage` field. Their evaluation points are defined by the primitive's cross-cutting contract in §4 rather than by the stage scheduler used for `IRInstruction`.

## 3. Canonical Pipeline Stages

The engine evaluates one authoritative tick as an ordered sequence of **12 pipeline stages**. Each stage processes all relevant IR instructions for all active abilities/effects on the Arbiter. The stages are non-reentrant — an instruction in stage 5 cannot trigger execution of stage 3.

### Stage Map

```
┌─────────────────────────────────────────────────────────┐
│                    TICK BOUNDARY                         │
├──── 1. ControlAuthorityAndInputRouting ────────────────┤
│  Control authority swap, input multiplexing              │
│  Primitives: P-29, P-30                                  │
├──── 2. IntentValidation ────────────────────────────────┤
│  Capability checks, resource costs, cast interception    │
│  Primitives: P-26, P-40, P-43, P-51                     │
├──── 3. TargetResolution ────────────────────────────────┤
│  Intent-time spatial queries, filtering, target selection│
│  Primitives: P-09, P-10, P-11, P-12, P-13               │
├──── 4. PreKinematic ────────────────────────────────────┤
│  Movement modifier setup (roots, slows, steering)        │
│  Primitives: P-03, P-26 (movement flags)                 │
├──── 5. KinematicResolution ─────────────────────────────┤
│  Execute all movement: teleport, displacement, sweeps    │
│  Primitives: P-01, P-02, P-06, P-07                     │
├──── 6. PostKinematic ───────────────────────────────────┤
│  Clamping, resolved impact queries, proximity events     │
│  Primitives: P-04, P-05, P-08, P-09, P-14, P-57, P-63   │
├──── 7. PreMitigation ──────────────────────────────────┤
│  Hit-count shields, deferred ledger, CC immunity check   │
│  Primitives: P-19, P-22, P-62, P-65                     │
├──── 8. DamageResolution ────────────────────────────────┤
│  Shields, mitigation, value modification, conversion     │
│  Primitives: P-15, P-16, P-18, P-20, P-21, P-49         │
├──── 9. PostDamage ──────────────────────────────────────┤
│  On-hit, on-damage-received, reactive procs, mirroring   │
│  Primitives: P-35, P-36, P-37, P-38, P-55, P-60, P-61   │
├──── 10. DeathCheck ─────────────────────────────────────┤
│  Floor clamping, bypass, phase transitions, on-death     │
│  Primitives: P-23, P-24, P-25, P-39                     │
├──── 11. StateUpdate ────────────────────────────────────┤
│  Counters, charges, loadout swaps, stagger, DR, timers   │
│  Primitives: P-31, P-41, P-42, P-44, P-45, P-46,        │
│              P-48, P-50                                   │
├──── 12. ObserverScopedPayloadEmission ─────────────────┤
│  Downstream payloads, asymmetric rendering, group UI     │
│  Primitives: P-52, P-53, P-54                            │
├─────────────────────────────────────────────────────────┤
│                    TICK BOUNDARY                         │
└─────────────────────────────────────────────────────────┘
```

### Stage Definitions

#### Stage 1: ControlAuthorityAndInputRouting

**Executes:** Before any intent processing.
**Purpose:** Resolve which Edge Node's input drives which entity.

| Primitive | Role |
|-----------|------|
| P-29 (Control Authority Swap) | Redirect input from controlling player to controlled entity |
| P-30 (Input Multiplexing) | Fan-out one player's input to N entities, or merge N inputs to one |

**Engine contract:** The engine MUST route all Edge Node proposals through input routing before intent validation. Routing state is per-entity SoftState.

#### Stage 2: IntentValidation

**Executes:** After input routing, before any spatial or combat resolution.
**Purpose:** Determine whether an intent is legal.

| Primitive | Role |
|-----------|------|
| P-26 (Capability Bitmask) | Check `CAN_CAST`, `CAN_ATTACK`, `CAN_USE_ITEMS` flags |
| P-40 (On-Cast Intercept) | Counterspell: cancel the cast. Spell Echo: duplicate the cast. Ability Steal: copy the ability. |
| P-43 (Charge-Up State) | Validate charge duration, compute multiplier |
| P-51 (Desperation Cost) | Compute escalated cost, validate affordability |

**Engine contract:** The engine MUST invoke intent validation hooks in registration order. A rejected intent MUST NOT proceed to later stages. On-Cast Intercept MUST fire after the caster's own validation succeeds but before resolution begins.

#### Stage 3: TargetResolution

**Executes:** After intent validation.
**Purpose:** Determine which entities are affected when the query can be resolved from intent-time inputs.

| Primitive | Role |
|-----------|------|
| P-09 (Shape Overlap Query) | Circle, Box, Cone, Ring intersection using intent-known centers/anchors |
| P-10 (Swept-Segment Raycast) | Line-of-sight, beam, reflection |
| P-11 (N-Nearest Neighbor) | Chain/bounce target selection |
| P-12 (Facing/Dot-Product Check) | Directional ability gating |
| P-13 (Tag/Allegiance Filtering) | Team/alive/tag filtering |

**Engine contract:** The engine MUST provide these as callable query operations returning bounded result sets. Ghost entities MUST be included in results to enable cross-boundary relay. The engine MUST enforce a configurable max-result cap. Queries whose center or anchor depends on committed movement output MUST NOT execute here; they execute in PostKinematic instead.

#### Stage 4: PreKinematic

**Executes:** After targets are known, before movement.
**Purpose:** Apply movement modifiers that affect kinematic resolution.

| Primitive | Role |
|-----------|------|
| P-03 (Trajectory Steering) | Set steering vectors for fear/charm/homing |
| P-26 (Capability Bitmask) | Apply `CAN_MOVE = false` for roots, stuns |

**Engine contract:** Movement-modifying effects applied here MUST take effect in the immediately following KinematicResolution stage.

#### Stage 5: KinematicResolution

**Executes:** After PreKinematic.
**Purpose:** Resolve all movement for the tick.

| Primitive | Role |
|-----------|------|
| P-01 (Instant Translation) | Teleport to target position |
| P-02 (Forced Displacement) | Apply knockback/pull velocity with decay; emit resolved destination/landing bindings |
| P-06 (Attached Kinematics) | Update child positions to match parent |
| P-07 (Entity-as-Kinematic-Volume) | Advance charge/dash sweep, check collisions per step |

**Engine contract:** The engine MUST resolve all kinematic primitives in a deterministic order: forced displacement first, then voluntary movement, then attached kinematics, then sweeps. Final positions MUST be committed before PostKinematic. If the requested destination is adjusted by range caps, collision policy, or other bounded kinematic rules, downstream bindings MUST expose the resolved position rather than the raw requested input.

#### Stage 6: PostKinematic

**Executes:** After all movement is committed.
**Purpose:** Evaluate position-dependent consequences after movement is committed.

| Primitive | Role |
|-----------|------|
| P-04 (Positional Clamping) | Enforce leash/tether distance limits |
| P-05 (Historical State Buffer) | Record current `(position, hp, tick)` to buffer |
| P-08 (Dynamic Collision Injection) | Insert/remove geometry from spatial grid |
| P-09 (Shape Overlap Query) | Resolve impact/landing AoE using committed kinematic output bindings |
| P-14 (Continuous Proximity Monitor) | Emit zone OnEnter/OnLeave events |
| P-57 (Polyline Collision Generator) | Extend trail geometry from current position |
| P-63 (Movement-Damage Scalar) | Calculate `displacement × damage_per_unit` |

**Engine contract:** Proximity monitor events generated here MUST be available as triggers for pulse timers (P-44) in the StateUpdate stage. Displacement damage from P-63 enters the combat pipeline at DamageResolution. If a spatial query depends on a resolved landing point, collision stop point, or other committed movement output, the compiler MUST place that query here rather than in TargetResolution.

#### Stage 7: PreMitigation

**Executes:** After combat events are queued (from target resolution + kinematic consequences), before damage numbers are calculated.
**Purpose:** Intercept or modify combat events before the damage pipeline.

| Primitive | Role |
|-----------|------|
| P-19 (Instance Barrier) | Consume a charge, negate the entire hit |
| P-22 (Deferred Ledger) | Suppress the HP change, accumulate in hidden ledger |
| P-62 (Categorized CC Immunity) | Check per-category immunity flags, reject blocked CC |
| P-65 (Vulnerability Window) | Check if target is in counter window, trigger counter |

**Engine contract:** If P-19 consumes a charge and negates the hit, the combat event MUST NOT proceed to DamageResolution. If P-22 is active, the combat event MUST be redirected to the ledger accumulator. CC immunity checks MUST run before CC application.

#### Stage 8: DamageResolution

**Executes:** After PreMitigation passes the event through.
**Purpose:** Calculate final damage/healing and apply to entity state.

| Primitive | Role |
|-----------|------|
| P-15 (Value Modification) | Apply flat/percentage damage or healing |
| P-16 (Stat Layering) | Evaluate stacked modifiers to compute effective stats |
| P-18 (Absorption Barrier) | Absorb damage through HP shields (in priority order) |
| P-20 (Damage Redirection) | Siphon percentage of damage to another entity |
| P-21 (Value Conversion) | Lifesteal, mana-to-damage conversion |
| P-49 (Resource Destruction-to-Damage) | Destroy target resource, convert to bonus damage |

**Engine contract:** The engine MUST evaluate this stage in a defined sub-order: stat evaluation → shield absorption → base mitigation → value modification → redirection → conversion. The sub-order is normative and MUST NOT vary between ticks.

#### Stage 9: PostDamage

**Executes:** After HP/resource changes are committed.
**Purpose:** Fire reactive hooks and secondary effects.

| Primitive | Role |
|-----------|------|
| P-35 (On-Hit Hook) | Trigger secondary effects from the attacker side |
| P-36 (On-Damage-Received Hook) | Trigger reactive effects from the defender side |
| P-37 (On-Crit Hook) | Fire crit-specific effects |
| P-38 (On-Block/Defend Hook) | Fire block-specific effects |
| P-55 (Concentration Intercept) | Roll concentration check on damage received |
| P-60 (Event Cloning) | Mirror the combat event to a linked entity |
| P-61 (Projectile Ownership Hijacking) | Redirect a projectile mid-flight |

**Engine contract:** Hooks in this stage MUST be flagged as "reactive." Effects triggered by reactive hooks MUST NOT re-enter PostDamage (no infinite chains). The engine MUST enforce a bounded cascade depth (configurable, default: 1). Secondary combat events generated here re-enter at PreMitigation of the NEXT tick (deferred), not the current tick.

#### Stage 10: DeathCheck

**Executes:** After all damage for the tick is applied.
**Purpose:** Determine if any entity transitions to dead or to a secondary life phase.

| Primitive | Role |
|-----------|------|
| P-23 (Floor Clamping) | Prevent HP from dropping below floor value |
| P-24 (Resolution Bypass) | Skip all death prevention — force kill |
| P-25 (Multi-Phase Vitals) | Transition to secondary HP pool instead of death |
| P-39 (On-Death Hook) | Trigger on-kill effects, spawn corpses, award credit |

**Engine contract:** Death check evaluation order MUST be: (1) Check Resolution Bypass — if set, skip to death. (2) Check Floor Clamping. (3) Check Multi-Phase transition. (4) If entity is dead, fire On-Death hooks. The engine MUST support game-adapter-defined life phases beyond the default Alive/Dead pair.

#### Stage 11: StateUpdate

**Executes:** After death checks.
**Purpose:** Update accumulators, timers, and persistent state.

| Primitive | Role |
|-----------|------|
| P-31 (Identity/Loadout Swap) | Execute pending form transformations |
| P-41 (DR Tracker) | Update diminishing returns tiers |
| P-42 (Stacking Counters) | Increment/decrement/decay stack counts |
| P-44 (Pulse Timer) | Fire interval-based triggers (zone ticks, DoT pulses) |
| P-45 (Delay Timer) | Fire scheduled triggers whose tick has arrived |
| P-46 (Global Event Scheduler) | Process controller-escalated global events |
| P-48 (Secondary Stagger Bar) | Update stagger bar, check depletion |
| P-50 (Typed Multi-Charge Pool) | Update charge pool composition |

**Engine contract:** Non-timer primitives evaluate in-place. Pulse (P-44) and Delay (P-45) timers that fire in this stage MUST NOT execute their payloads in the current tick. Instead, they MUST emit deferred events queued for the NEXT tick. The re-entry stage depends on the event class (defined in §6.1). Global events (P-46) are routed to the Mesh Controller for deterministic future-tick injection.

#### Stage 12: ObserverScopedPayloadEmission

**Executes:** Last stage of the tick.
**Purpose:** Build downstream payloads for Edge Nodes.

| Primitive | Role |
|-----------|------|
| P-52 (Asymmetric Team-Rendering) | Filter entities per-team for downstream payloads |
| P-53 (Entity Suspension) | Exclude suspended entities from all payloads |
| P-54 (Group Choice Aggregator) | Include group UI state in payloads |

**Engine contract:** The engine MUST evaluate visibility flags per-entity per-team when building downstream payloads. Suspended entities MUST NOT appear in any payload. Group aggregator state MUST be included for entities with active group interactions.

## 4. Cross-Cutting Primitives

Some primitives are not bound to a single pipeline stage. They are emitted as `IRDirective` entries or metadata fields and then checked by the engine at one or more stages:

| Primitive | Emission Form | Checked At |
|-----------|---------------|-----------|
| P-26 (Capability Bitmask) | `IRDirective` / metadata | IntentValidation (CAN_CAST), PreKinematic (CAN_MOVE), TargetResolution (filtering) |
| P-27 (Targetability Overrides) | `IRDirective` / metadata | TargetResolution (excluded from queries), ObserverScopedPayloadEmission (excluded from payloads) |
| P-28 (Hostility Inversion) | `IRDirective` / metadata | TargetResolution (inverted team filter) |
| P-32 (Actor Spawning) | `IRDirective` | Any stage may request actor creation; spawned actors begin evaluation on the NEXT tick |
| P-33 (Entity Dormancy) | `IRDirective` / metadata | All stages — dormant entities are skipped entirely |
| P-34 (Persistent Linkage) | `IRDirective` / metadata | Cross-cutting — bindings are checked wherever the linked primitives operate |
| P-47 (Spatial Corpse Registry) | `IRDirective` / metadata | DeathCheck (create corpse), TargetResolution (query corpses) |
| P-56 (Spatial Instance Forking) | `IRDirective` / metadata | Cross-cutting — instance enter/exit occurs outside normal per-stage instruction scheduling |

The compiler MUST NOT emit these as stage-specific `IRInstruction` entries. They are emitted as `IRDirective` entries or ability metadata and interpreted by the engine at the points listed above.

## 5. Complete Primitive → Stage Mapping

| Primitive | Stage | Category |
|-----------|-------|----------|
| P-01 Instant Translation | KinematicResolution | Spatial |
| P-02 Forced Displacement | KinematicResolution | Spatial |
| P-03 Trajectory Steering | PreKinematic | Spatial |
| P-04 Positional Clamping | PostKinematic | Spatial |
| P-05 Historical State Buffer | PostKinematic | Spatial |
| P-06 Attached Kinematics | KinematicResolution | Spatial |
| P-07 Entity-as-Kinematic-Volume | KinematicResolution | Spatial |
| P-08 Dynamic Collision Injection | PostKinematic | Spatial |
| P-09 Shape Overlap Query | TargetResolution / PostKinematic | Targeting |
| P-10 Swept-Segment Raycast | TargetResolution | Targeting |
| P-11 N-Nearest Neighbor | TargetResolution | Targeting |
| P-12 Facing/Dot-Product Check | TargetResolution | Targeting |
| P-13 Tag/Allegiance Filtering | TargetResolution | Targeting |
| P-14 Continuous Proximity Monitor | PostKinematic | Targeting |
| P-15 Value Modification | DamageResolution | Combat |
| P-16 Stat Layering | DamageResolution | Combat |
| P-17 Conditional Thresholds | *(guard expression, not a stage)* | Combat |
| P-18 Absorption Barrier | DamageResolution | Combat |
| P-19 Instance Barrier | PreMitigation | Combat |
| P-20 Damage Redirection | DamageResolution | Combat |
| P-21 Value Conversion | DamageResolution | Combat |
| P-22 Deferred Ledger | PreMitigation | Combat |
| P-23 Floor Clamping | DeathCheck | Combat |
| P-24 Resolution Bypass | DeathCheck | Combat |
| P-25 Multi-Phase Vitals | DeathCheck | Combat |
| P-26 Capability Bitmask | *(cross-cutting)* | State |
| P-27 Targetability Overrides | *(cross-cutting)* | State |
| P-28 Hostility Inversion | *(cross-cutting)* | State |
| P-29 Control Authority Swap | ControlAuthorityAndInputRouting | State |
| P-30 Input Multiplexing | ControlAuthorityAndInputRouting | State |
| P-31 Identity/Loadout Swap | StateUpdate | State |
| P-32 Actor Spawning | *(cross-cutting)* | State |
| P-33 Entity Dormancy | *(cross-cutting)* | State |
| P-34 Persistent Linkage | *(cross-cutting)* | State |
| P-35 On-Hit Hook | PostDamage | Hook |
| P-36 On-Damage-Received Hook | PostDamage | Hook |
| P-37 On-Crit Hook | PostDamage | Hook |
| P-38 On-Block/Defend Hook | PostDamage | Hook |
| P-39 On-Death Hook | DeathCheck | Hook |
| P-40 On-Cast Intercept | IntentValidation | Hook |
| P-41 DR Tracker | StateUpdate | Accumulator |
| P-42 Stacking Counters | StateUpdate | Accumulator |
| P-43 Charge-Up State | IntentValidation | Accumulator |
| P-44 Pulse Timer | StateUpdate | Temporal |
| P-45 Delay Timer | StateUpdate | Temporal |
| P-46 Global Event Scheduler | StateUpdate | Temporal |
| P-47 Spatial Corpse Registry | *(cross-cutting)* | Resource |
| P-48 Secondary Stagger Bar | StateUpdate | Resource |
| P-49 Resource Destruction-to-Damage | DamageResolution | Resource |
| P-50 Typed Multi-Charge Pool | StateUpdate | Resource |
| P-51 Desperation Cost Modifiers | IntentValidation | Resource |
| P-52 Asymmetric Team-Rendering | ObserverScopedPayloadEmission | Visibility |
| P-53 Entity Suspension | ObserverScopedPayloadEmission | Visibility |
| P-54 Group Choice Aggregator | ObserverScopedPayloadEmission | Visibility |
| P-55 Concentration Intercept | PostDamage | Hook |
| P-56 Spatial Instance Forking | *(cross-cutting)* | Spatial |
| P-57 Polyline Collision Generator | PostKinematic | Spatial |
| P-58 Container/Vehicle Logic | KinematicResolution | Spatial |
| P-59 N-Way Portal Network | KinematicResolution | Spatial |
| P-60 Event Cloning | PostDamage | Advanced |
| P-61 Projectile Ownership Hijacking | PostDamage | Advanced |
| P-62 Categorized CC Immunity | PreMitigation | Advanced |
| P-63 Movement-Damage Scalar | PostKinematic | Systemic |
| P-64 Combo Field × Finisher Matrix | PostKinematic | Systemic |
| P-65 Vulnerability Window Broadcast | PreMitigation | Systemic |

## 6. Cascade and Re-entrancy Rules

The most critical safety constraint in the IR is **preventing unbounded within-tick cascades**.

### 6.1 Deferred Execution Rule

The engine MUST enforce strict re-entry boundaries to prevent infinite cascades within a single tick. 

**PostDamage Hooks (Stage 9):**
Any combat event generated by a PostDamage hook (P-35, P-36, P-37, P-38, P-60) MUST be queued for the NEXT tick. It re-enters the pipeline at **Stage 7 (PreMitigation)**, skipping target/kinematic resolution because the target and source are already known.

**StateUpdate Timers (Stage 11):**
Stage 11 operations are classified into three behaviors:
1. **`in_place_state_update`**: Primitives like DR Tracker (P-41), Stacking Counters (P-42), and Charge Pools (P-50) mutate state directly during Stage 11. They emit no deferred events.
2. **`deferred_spatial_event`**: Timers (P-44, P-45) whose payloads contain spatial queries (e.g., a delayed bomb explosion, a pulsing Blizzard zone). These MUST be queued for the NEXT tick and re-enter at **Stage 3 (TargetResolution)** so the engine can query the R-Tree for affected entities.
3. **`deferred_combat_event`**: Timers whose payloads target a known, specific entity without needing a spatial query (e.g., a DoT pulse applied directly to a victim). These MUST be queued for the NEXT tick and re-enter at **Stage 7 (PreMitigation)**.

The Game Compiler MUST explicitly tag timer payloads as either spatial or combat during Phase 3 lowering so the Engine's Stage Scheduler knows which queue to place them in.

**Deterministic Queue Ordering Rule:**
When the Engine's Stage Scheduler injects deferred events into a pipeline stage, the events MUST be evaluated in a deterministic order. If a stage receives a mixed batch of deferred events, the Engine MUST sort them by:
1. `ready_tick` (ascending)
2. `target_stage` (ascending)
3. `sort_key` (ascending, using the event's stable identity/priority key)

### 6.2 Reactive Depth Bound

The engine MUST track a `reactive_depth` counter per combat event:
- Original ability resolution: `reactive_depth = 0`
- PostDamage hook fires a secondary event: `reactive_depth = 1`
- That secondary event's PostDamage hooks: `reactive_depth = 2`

Events at `reactive_depth >= MAX_REACTIVE_DEPTH` (configurable, default: 1) MUST NOT trigger further PostDamage hooks. This bounds the cascade to a finite, configurable depth.

### 6.3 Mirror Loop Prevention

Event Cloning (P-60) MUST tag cloned events with a `is_clone: true` flag. Cloned events MUST NOT trigger further cloning. This prevents A → B → A infinite mirroring.

## 7. Compiler Emission Rules

The compiler MUST enforce these rules when emitting IR:

1. **Stage assignment is automatic for stage-specific primitives.** The compiler determines each `IRInstruction` stage from its primitive ID and dependency context using the mapping in §5. Cross-cutting primitives are emitted as `IRDirective` entries and therefore have no `stage` field. Designers do not manually assign stages.

   For example: `P-09 Shape Overlap Query` targeting an intent-known center such as a requested ground-target position preview uses `TargetResolution`, while a `P-09` query centered on a binding emitted by `KinematicResolution` uses `PostKinematic`.

2. **Intra-stage ordering follows instruction order.** Within a stage, instructions execute in the order they appear in the IR Block.

3. **Cross-stage data flow uses bindings.** An instruction in TargetResolution that outputs a target set can be referenced by an instruction in DamageResolution via a binding.

4. **Guards are compile-time validated.** All guard expressions MUST be structurally validated at compile time. No runtime Lua evaluation.

5. **No unbounded loops.** The compiler MUST reject ability definitions that would produce unbounded instruction counts or unbounded binding tables.

6. **Primitive count per ability is bounded.** A single ability IR Block MUST NOT contain more than `MAX_INSTRUCTIONS_PER_ABILITY` instructions (configurable, default: 32).

7. **Binding count per ability is bounded.** A single ability IR Block MUST NOT contain more than `MAX_BINDINGS_PER_ABILITY` binding slots (configurable, default: 16).

## 8. Example: SK-01 (Toss) Compiled IR

```
AbilityIRBlock {
    ability_id: TOSS,
    cooldown_ticks: 600,        // 10 seconds
    resource_pool: MANA,        // pool to debit
    resource_cost: 75,          // amount
    cast_time_ticks: 0,         // instant
    targeting_type: SingleTarget,
    self_cc_immunity_during_cast: None,
    can_counter_vulnerability_window: false,
    can_be_counterspelled: true,
    combo_finisher: None,
    requires_concentration: false,
    instructions: [
        // 1. Target: is target valid?
        IRInstruction {
            primitive: P-13,
            stage: TargetResolution,
            params: { filter: Enemy | Alive, entity: Target },
            guard: None,
        },
        // 2. Kinematic: displace target along arc to landing position
        IRInstruction {
            primitive: P-02,
            stage: KinematicResolution,
            params: {
                entity: Target,
                destination: RequestedTargetPosition,
                arc: true,
                duration_ticks: 30,
                max_distance: 8.0,
            },
            output: Some("landing_pos"),
            guard: None,
        },
        // 3. PostKinematic: resolve AoE from the ACTUAL landing point,
        // not the raw requested target input. This matters if the requested
        // position is beyond max throw distance and the toss is clamped.
        IRInstruction {
            primitive: P-09,
            stage: PostKinematic,
            params: {
                shape: Circle,
                center: Binding("landing_pos"),
                radius: 3.0,
                filter: Enemy | Alive,
            },
            output: Some("aoe_targets"),
            guard: None,
        },
        // 4. Damage: impact damage to primary target
        IRInstruction {
            primitive: P-15,
            stage: DamageResolution,
            params: { target: Target, amount: 150, type: Physical },
            guard: None,
        },
        // 5. Damage: AoE damage to nearby enemies
        IRInstruction {
            primitive: P-15,
            stage: DamageResolution,
            params: { targets: Binding("aoe_targets"), amount: 100, type: Physical },
            guard: None,
        },
    ],
    directives: [
        // Cross-cutting requirement: caster must be allowed to cast
        IRDirective {
            primitive: P-26,
            params: { require: CAN_CAST, entity: Caster },
            guard: None,
        },
    ],
    bindings: [
        BindingSlot { name: "landing_pos", type: Vec2F },
        BindingSlot { name: "aoe_targets", type: EntitySet },
    ],
}
```

## 9. Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `ability-primitives/` | Defines the 65 primitives this IR targets. Each IR instruction or IR directive invokes exactly one primitive. |
| `03-compiler-pipeline.md` | Describes the compilation phases that produce IR Blocks. This document defines the IR output format. |
| `04-game-image-format.md` | IR Blocks are stored in the game image's Ability IR Table section (§3, type 0x10). |
| `docs-core/04-1-game-adapter-contract.md` | The 12 pipeline stages defined here are the proposed expansion of the adapter hook taxonomy (Amendment B). |
| `docs-core/PRIMITIVE_IMPACT_ASSESSMENT.md` | This document is the concrete deliverable for Amendment B. |

---

*This specification is the compiler team's proposal for the engine's ability resolution pipeline. The 12 canonical pipeline stages should be reviewed and adopted into `docs-core/04-1-game-adapter-contract.md` as the normative hook taxonomy.*
