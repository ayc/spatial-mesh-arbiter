# Compiler IR Specification

Keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

**Status:** DRAFT
**Purpose:** Define the Intermediate Representation (IR) that the Game Compiler emits when lowering designer-authored Lua ability definitions into engine-executable primitive chains plus bounded runtime-state operations. This IR is the compilation target — the contract between the compiler and the engine runtime.

**Relationship to docs-core/:** This specification proposes the canonical pipeline stages that the engine MUST support for ability resolution. It serves as the compiler team's concrete answer to `docs-core/PRIMITIVE_IMPACT_ASSESSMENT.md` Amendment B (Adapter Hook Taxonomy). The engine team should validate and adopt these stages into `04-1-game-adapter-contract.md`.

---

## 1. IR Overview

The compiler transforms a designer's Lua ability definition into an **Ability IR Block** — a static, deterministic data structure that the engine evaluates at runtime. The IR Block is stored in the compiled game image's Ability IR Table section (`04-game-image-format.md` §3, section type 0x10).

An Ability IR Block consists of:
1. **Metadata** — ability ID, cooldown, resource cost, targeting type, cast time, input mode, activation redirects
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
    channel:          Option<ChannelPolicyIR>,
    concentration:    Option<ConcentrationPolicyIR>,
    input_mode:       InputModeIR,      // Instant or hold-release admission contract
    activation_modes: Vec<ActivationModeIR>,  // Ordered state-based redirects to hidden variants
    instructions:     Vec<IRInstruction>,
    directives:       Vec<IRDirective>,
    bindings:         Vec<BindingSlot>,
}
```

```
enum InputModeIR {
    Instant,
    HoldRelease {
        min_charge_ticks: u32,
        max_charge_ticks: u32,
        move_speed_multiplier_while_holding: SimFixed,
        blocks_other_abilities: bool,
        retains_max_charge_until_release: bool,
    }
}

ChannelPolicyIR {
    execution_mode: ChannelExecutionModeIR,
    tick_interval_ticks: u16,
    movement_lock: ChannelMovementLockIR,
    allow_other_abilities: bool,
    continuous_input: ChannelContinuousInputIR,
    break_on_displacement: bool,
    break_on_target_invalid: bool,
    interrupt_on_damage_above: Option<SimFixed>,
    partial_cooldown_refund: SimFixed,
}

enum ChannelExecutionModeIR {
    CompleteOnly,
    TickWhileActive,
}

enum ChannelMovementLockIR {
    None,
    Root,
}

enum ChannelContinuousInputIR {
    None,
    SteerAim,
    SteerTargetMovement,
}

ConcentrationPolicyIR {
    check_formula: ConcentrationFormulaIR,
    max_duration_ticks: Option<u32>,
    allow_manual_cancel: bool,
    replace_existing: bool,
}

enum ConcentrationFormulaIR {
    StandardHalfDamageFloor10,
}

ActivationModeIR {
    predicate: StatePredicateIR,
    variant_ability_id: AbilityId,   // Compiler-generated hidden variant block
}

enum StatePredicateIR {
    StatePresent(RuntimeStateId),
    StateAbsent(RuntimeStateId),
    SequenceStep(RuntimeStateId, u8),
    ChargeCount(RuntimeStateId, CompareOp, u8),
}
```

## 2. IR Instructions

Each instruction invokes exactly one engine primitive or one compiler-owned bounded runtime-state op
at a specific pipeline stage.

```
IRInstruction {
    op:          InstructionOp,  // Primitive(P-01..P-66) or RuntimeState(...)
    stage:       PipelineStage,  // Which tick-loop phase this executes in
    params:      ParamBlock,     // Op-specific parameters (compile-time constants + binding refs)
    output:      Option<BindingRef>,  // Named output for downstream instructions
    guard:       Option<GuardExpr>,   // Conditional: only execute if guard evaluates true
}

enum InstructionOp {
    Primitive(PrimitiveId),
    RuntimeState(RuntimeStateOp),
}

enum RuntimeStateOp {
    WriteState,
    ClearState,
    AdvanceSequence,
    ModifyChargePool,
}
```

### 2.1 Parameter Blocks

Parameters are either **compile-time constants** (embedded in the IR) or **binding references** (resolved at runtime from a previous instruction's output).

```
type RuntimeStateId = u32

enum ParamValue {
    Const(SimFixed),
    ConstInt(i32),
    ConstBool(bool),
    ConstEnum(u16),            // Index into a compile-time enum table
    Binding(BindingRef),       // Runtime value from a prior instruction
    EntityField(FieldPath),    // Read from caster/target entity state
    RuntimeState(RuntimeStateId),  // Referenced runtime state slot
    StatePayload(RuntimeStateId, StatePayloadSelector),  // Stored position/entity/snapshot reads
}

enum StatePayloadSelector {
    StoredPosition,
    StoredEntityId,
    StoredEntityPosition,
    SnapshotPosition,
    SnapshotHp,
    SequenceStep,
    ChargeCount,
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
    type:  BindingType, // EntitySet | SimFixed | EntityId | Bool | Vec2F | U32
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

### 2.5 Hidden Variant Blocks

`ActivationModes` do NOT patch one `AbilityIRBlock` in place. Each authored activation mode compiles
to a hidden ordinary `AbilityIRBlock` with its own metadata, instructions, directives, and
bindings. The public/root ability block keeps the player-facing `ability_id` plus an ordered
`activation_modes` redirect table. During Stage 2, the engine selects at most one hidden variant;
that selected variant becomes the active block for the remainder of the pipeline.

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
│  Block gates, pre-mitigation intercepts, CC checks       │
│  Primitives: P-19, P-22, P-62, P-65                     │
├──── 8. DamageResolution ────────────────────────────────┤
│  Shields, mitigation, value modification, conversion     │
│  Primitives: P-15, P-16, P-18, P-20, P-21, P-49         │
├──── 9. PostDamage ──────────────────────────────────────┤
│  On-hit, damage-received, concentration, reactive procs   │
│  Primitives: P-35, P-36, P-37, P-38, P-55, P-60, P-61   │
├──── 10. DeathCheck ─────────────────────────────────────┤
│  Floor clamping, death prevention, bypass, on-death      │
│  Primitives: P-23, P-24, P-25, P-39                     │
├──── 11. StateUpdate ────────────────────────────────────┤
│  Maintained teardown, counters, charges, loadout swaps,  │
│  status registry, stagger, DR, timers                    │
│  Primitives: P-31, P-41, P-42, P-44, P-45, P-46,        │
│              P-48, P-50, P-66                             │
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

**Engine contract:** The engine MUST route all Edge Node proposals through input routing before
intent validation. Routing state is per-entity SoftState. Static `control_topology` metadata from
entity definitions installs and re-installs here at spawn, reconnect, and handoff boundaries.
Compiled `control_override` effects that resolve later in the tick enqueue pending Stage 1 routing
mutations; those pending mutations commit atomically at the NEXT tick's Stage 1 boundary, using the
same P-29/P-30 relay behavior defined by `docs-core/01-3-entity-relationship-contract.md`.

#### Stage 2: IntentValidation

**Executes:** After input routing, before any spatial or combat resolution.
**Purpose:** Determine whether an intent is legal.

| Primitive | Role |
|-----------|------|
| P-26 (Capability Bitmask) | Check `CAN_CAST`, `CAN_ATTACK`, `CAN_USE_ITEMS` flags |
| P-40 (On-Cast Intercept) | Counterspell: cancel the cast. Spell Echo: duplicate the cast. Ability Steal: copy the ability. |
| P-43 (Charge-Up State) | Validate charge duration, compute multiplier |
| P-51 (Desperation Cost) | Compute escalated cost, validate affordability |

**Engine contract:** The engine MUST invoke intent validation hooks in registration order. A
rejected intent MUST NOT proceed to later stages. On-Cast Intercept MUST fire after the caster's
own validation succeeds but before resolution begins. Any ability with `cast_time_ticks > 0` MUST
publish a bounded visible cast-state record (`ability_id`, start tick, scheduled end tick,
counterspellability, channel/concentration flags) until it resolves, breaks, or is cancelled.

Activation-mode evaluation also lives in Stage 2. After base capability and legality checks pass,
the engine MUST evaluate `activation_modes` in authored order and select the first matching hidden
variant. The selected variant's targeting, costs, and instructions replace the root block for the
rest of the resolution path. `consume_on = cast_ability` windows are checked after variant
selection but before resource/cooldown commit for the selected block.

If a selected block carries `resource_cost.escalation`, the engine MUST evaluate `P-51` before the
final affordability check using the compiled escalation counter for that entity and
`shared_counter_id`. `effective_cost = base_cost * multiplier_per_stack ^ current_stacks`. The
counter increments only after the cast commits successfully and decays one stack per authored decay
interval of inactivity.

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

**Engine contract:** The engine MUST resolve all kinematic primitives in a deterministic order:
forced displacement first, then voluntary movement, then attached kinematics, then sweeps. Final
positions MUST be committed before PostKinematic. If the requested destination is adjusted by range
caps, collision policy, or other bounded kinematic rules, downstream bindings MUST expose the
resolved position rather than the raw requested input. A `displacement.flight_policy` overlay is
still one deterministic kinematic move: the displaced entity carries a bounded per-flight hit set
and optional world-impact payloads, but ownership and handoff follow the same single-authority rule
as ordinary `P-02`.

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

**Engine contract:** Proximity monitor events generated here MUST be available as triggers for
pulse timers (P-44) in the StateUpdate stage. Displacement damage from P-63 enters the combat
pipeline at DamageResolution. If a spatial query depends on a resolved landing point, collision
stop point, or other committed movement output, the compiler MUST place that query here rather than
in TargetResolution. Moving or tracking zones resolve occupant diffs from their committed current
position in this stage; they MUST NOT query from stale pre-kinematic zone positions. Geometry
injection and polyline extension likewise use committed current positions from this stage, so
movement-authored walls, trails, and leash anchors all see the same authoritative pose that later
PostKinematic admission and clamp checks use.

#### Stage 7: PreMitigation

**Executes:** After combat events are queued (from target resolution + kinematic consequences), before damage numbers are calculated.
**Purpose:** Intercept or modify combat events before the damage pipeline.

| Primitive | Role |
|-----------|------|
| Compiled BlockDefense policy | Deterministic block gate before barrier/shield resolution; successful blocks emit a P-38 marker |
| P-19 (Instance Barrier) | Consume a charge, negate the entire hit |
| P-22 (Deferred Ledger) | Suppress the HP change, accumulate in hidden ledger |
| P-62 (Categorized CC Immunity) | Check per-category immunity flags, reject blocked CC |
| P-65 (Vulnerability Window) | Check if target is in counter window, trigger counter |

**Engine contract:** PreMitigation sub-order MUST be: (1) compiled block gate, (2) P-19 instance
barriers, (3) P-22 deferred ledger interception, (4) P-62 CC admission checks, (5) P-65 counter
window checks. If the target has `BlockDefenseDef`, the engine evaluates the effective block chance
using the compiled `chance_stat` minus current DR penalty. A successful block negates eligible
HP/resource damage components, marks the event as blocked for Stage 9 `P-38`, and prevents those
damage components from entering DamageResolution. Non-damage payloads continue only if the compiled
block profile does not suppress them. If P-19 consumes a charge and negates the hit, the combat
event MUST NOT proceed to DamageResolution. If P-22 is active, the combat event MUST be redirected
to the ledger accumulator. CC immunity checks MUST run before CC application.

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

**Engine contract:** The engine MUST evaluate this stage in a defined sub-order: stat evaluation →
link-based redirection split → branch-local shield absorption → branch-local base mitigation →
branch-local value modification → branch-local conversion. `P-20` operates on the incoming
pre-mitigation damage packet for the currently resolving target. If an active `P-34` binding
authored `damage_redirect`, the runtime splits that packet into an unredirected remainder for the
current target plus one redirected sibling branch for the linked partner, bounded by `max_hops`.
Each branch then resolves independently through shields, mitigation, value modification, and
conversion using that branch target's own defensive state. `resource_burn` style P-49 effects use
the target's authoritative resource pools and derive their bonus damage from the actual destroyed
amount during this stage. The sub-order is normative and MUST NOT vary between ticks.

#### Stage 9: PostDamage

**Executes:** After HP/resource changes are committed.
**Purpose:** Fire reactive hooks and secondary effects.

| Primitive | Role |
|-----------|------|
| P-35 (On-Hit Hook) | Trigger secondary effects from the attacker side |
| P-36 (On-Damage-Received Hook) | Trigger reactive effects from the defender side |
| P-37 (On-Crit Hook) | Fire crit-specific effects |
| P-38 (On-Block/Defend Hook) | Fire block-specific effects |
| Compiled channel break policy | Evaluate damage-threshold interruption for active channels |
| P-55 (Concentration Intercept) | Roll concentration check on damage received |
| P-60 (Event Cloning) | Mirror the combat event to a linked entity |
| P-61 (Projectile Ownership Hijacking) | Redirect a projectile mid-flight |

**Engine contract:** Hooks in this stage MUST be flagged as "reactive." Effects triggered by
reactive hooks MUST NOT re-enter PostDamage (no infinite chains). The engine MUST enforce a
bounded cascade depth (configurable, default: 1). `P-55` concentration checks, compiled
damage-threshold channel breaks, and any status-owned `projectile_intercept` / `P-61` redirects
evaluate after the triggering hit has finished its local protection/mitigation path but before any
reactive payloads are emitted for the next tick. `P-60` cloned events and compiler-owned
heal-mirror events emitted from active `P-34` bindings MUST carry their originating `binding_id`
plus anti-recursion tags, so they cannot re-clone or re-mirror through the same link. `P-61`
redirects likewise carry a bounded redirect-generation counter so returned projectiles cannot bounce
between interceptors forever. Secondary combat events generated here re-enter at PreMitigation of
the NEXT tick (deferred), not the current tick.

#### Stage 10: DeathCheck

**Executes:** After all damage for the tick is applied.
**Purpose:** Determine if any entity transitions to dead or to a secondary life phase.

| Primitive | Role |
|-----------|------|
| P-23 (Floor Clamping) | Prevent HP from dropping below floor value |
| P-24 (Resolution Bypass) | Skip all death prevention — force kill |
| P-25 (Multi-Phase Vitals) | Transition to secondary HP pool instead of death |
| P-39 (On-Death Hook) | Trigger on-kill effects, spawn corpses, award credit |

**Engine contract:** Death check evaluation order MUST be: (1) Check Resolution Bypass — if set,
skip to death. (2) Check Floor Clamping. (3) Evaluate compiled death-prevention policies. (4) Check
Multi-Phase transition. (5) If entity is dead, fire On-Death hooks. The engine MUST support
game-adapter-defined life phases beyond the default Alive/Dead pair. Intermediate phase
transitions MUST suppress terminal `on_death` hook execution and MUST NOT create `P-47`
corpse-registry entries. Terminal death MAY create one corpse-registry record when the entity type
authored `corpse_profile`.

#### Stage 11: StateUpdate

**Executes:** After death checks.
**Purpose:** Update accumulators, timers, status registry state, and persistent state.

| Primitive | Role |
|-----------|------|
| Compiled maintained-effect registry | Commit channel completion/break teardown and concentration cleanup |
| P-31 (Identity/Loadout Swap) | Execute pending form transformations, slot overrides, and revert timers |
| P-41 (DR Tracker) | Update diminishing returns tiers |
| P-42 (Stacking Counters) | Increment/decrement/decay stack counts |
| P-44 (Pulse Timer) | Fire interval-based triggers (zone ticks, DoT pulses) |
| P-45 (Delay Timer) | Fire scheduled triggers whose tick has arrived |
| P-46 (Global Event Scheduler) | Process controller-escalated global events |
| P-48 (Secondary Stagger Bar) | Update stagger bar, check depletion |
| P-50 (Typed Multi-Charge Pool) | Update charge pool composition |
| P-66 (Status Effect Filter Mutation) | Remove matching statuses / apply status-admission filters |

**Engine contract:** Non-timer primitives evaluate in-place. Compiled maintained-effect teardown
for broken/completed channels and broken/replaced concentration instances commits here before timers
fire, so same-tick break/cancel decisions suppress later timer emissions from removed maintained
artifacts. P-66 cleanse/registry mutations MUST execute before P-44 and P-45 timer firings in the
same stage, so a same-tick cleanse suppresses later timer emissions from statuses it removed. Pulse
(P-44) and Delay (P-45) timers that fire in this stage MUST NOT execute their payloads in the
current tick. Instead, they MUST emit deferred events queued for the NEXT tick. Exact-match
`consume_status` mutations use the same Stage 11 ordering: if a consume batch removed any matching
statuses, its `on_consume_effects` are also emitted as deferred next-tick events in the same target
context. The re-entry stage depends on the event class (defined in §6.1). Global events (P-46) are
routed to the Mesh Controller for deterministic future-tick injection.

#### Stage 12: ObserverScopedPayloadEmission

**Executes:** Last stage of the tick.
**Purpose:** Build downstream payloads for Edge Nodes.

| Primitive | Role |
|-----------|------|
| P-52 (Asymmetric Team-Rendering) | Filter entities per-team for downstream payloads |
| P-53 (Entity Suspension) | Exclude suspended entities from all payloads |
| P-54 (Group Choice Aggregator) | Include group UI state in payloads |

**Engine contract:** The engine MUST evaluate visibility flags per-entity per-team when building downstream payloads. Suspended entities MUST NOT appear in any payload. Group aggregator state MUST be included for entities with active group interactions. Downstream-only presentation aliases (appearance mirroring, fake enemy HP bars, ally-only markers) are legal here, but they MUST NOT alter authoritative gameplay state.

## 4. Cross-Cutting Primitives

Some primitives are not bound to a single pipeline stage. They are emitted as `IRDirective` entries or metadata fields and then checked by the engine at one or more stages:

| Primitive | Emission Form | Checked At |
|-----------|---------------|-----------|
| P-26 (Capability Bitmask) | `IRDirective` / metadata | IntentValidation (CAN_CAST / CAN_ATTACK), PreKinematic (CAN_MOVE), passive evaluation (PASSIVES_ACTIVE), TargetResolution (filtering) |
| P-27 (Targetability Overrides) | `IRDirective` / metadata | TargetResolution (excluded from queries), ObserverScopedPayloadEmission (excluded from payloads) |
| P-28 (Hostility Inversion) | `IRDirective` / metadata | TargetResolution (inverted team filter / nearest-ally selection for berserk-style control) |
| P-62 (Categorized CC Immunity) | status metadata | CC admission before any new status is inserted |
| P-32 (Actor Spawning) | `IRDirective` | Any stage may request actor creation; spawned actors begin evaluation on the NEXT tick |
| P-33 (Entity Dormancy) | `IRDirective` / metadata | All stages — dormant entities are skipped entirely |
| P-34 (Persistent Linkage) | `IRDirective` / metadata | Cross-cutting — bindings are checked wherever the linked primitives operate |
| P-47 (Spatial Corpse Registry) | `IRDirective` / metadata | DeathCheck (create corpse), TargetResolution (query corpses) |
| P-56 (Spatial Instance Forking) | `IRDirective` / metadata | Cross-cutting — instance enter/exit occurs outside normal per-stage instruction scheduling |

The compiler MUST NOT emit these as stage-specific `IRInstruction` entries. They are emitted as `IRDirective` entries or ability metadata and interpreted by the engine at the points listed above.

### 4.1 Crowd-Control Admission and Enforcement

Crowd control authored through `apply_cc` compiles to a generated negative status entry that carries
the selected `cc_category`, an internal `cc_behavior_profile`, duration-scaling policy, ordinary
status-cleanse metadata, and any authored expiry follow-up effects.

The engine MUST enforce crowd control in the following deterministic order:

1. **Admission check:** Before inserting a new status, evaluate `P-62` by scanning active statuses
   for `cc_immunity_categories`, plus any temporary immunity granted by
   `self_cc_immunity_during_cast`. If the category is blocked, reject the CC component only;
   sibling damage/heal effects from the same ability continue.
2. **Effective duration:** Start from authored `duration_ticks`. If the status uses
   `duration_scaling = status_resistance`, apply the source's status-duration modifier and the
   target's `status_effect_resistance` modifier multiplicatively, then apply DR for the authored
   `dr_category`. Clamp admitted duration to at least one tick.
3. **Status insert:** Insert the generated status into the target's authoritative status registry.
   From this point forward, `cleanse`, `status_application_immunity`, and generic status queries
   treat CC and non-CC statuses identically.
4. **Immediate interruption:** The `stun`, `silence`, and `sleep` behavior profiles terminate the
   target's current cast/channel immediately on admission. Detailed teardown of maintained effects
   still follows the channel lifecycle contract.
5. **Offense-side miss policy:** The `blind` profile is checked on the attacker before
   `CombatContext` generation for the engine-owned auto-attack action. A blinded auto-attack
   becomes `Miss` and MUST NOT generate damage, on-hit hooks, or relay payloads.
6. **Target-control policy:** The `taunt` and `berserk` profiles mutate the engine-owned
   auto-attack action before target resolution. `taunt` rewrites target selection to the status
   source while that source is alive. `berserk` rewrites target selection to the nearest ally and
   authorizes ally damage for that auto-attack only. Neither profile retargets ordinary authored
   ability casts.
7. **Forced-movement policy:** The `fear` and `charm` profiles emit deterministic `P-03`
   steering directives each tick while suppressing voluntary attacks and casts. `fear` steers away
   from the source; `charm` steers toward the source.
8. **Profile-defined breaks:** `sleep` breaks after any non-zero committed damage instance. `taunt`
   breaks when the source entity dies. A break removes the status before later same-stage timer
   firings; the hit that broke `sleep` still resolves normally.
9. **Passive suppression:** The `mute` profile clears `PASSIVES_ACTIVE` while the status is
   present. Passive statuses, aura pulses, passive item effects, and passive proc registrations are
   suspended, not removed, and resume when the status ends.

### 4.2 Activation Modes, Runtime States, and Consumption Windows

The `CG-07` stateful authoring surface lowers into four canonical runtime constructs:

1. ordered activation-mode redirects (`ActivationModeIR`)
2. bounded per-entity runtime states keyed by `RuntimeStateId`
3. status-owned snapshot recorders backed by engine `P-05`
4. status-owned consumption windows that modify the next matching cast/hit/damage event

The engine/runtime MUST enforce the following rules:

1. **Hold-release ingress stays inside the existing intent taxonomy.** The hold START uses the
   ordinary discrete cast intent for the ability's targeting shape (`TargetedAbility`,
   `GroundTargetedAbility`, or `SpawnProjectile`). Release is derived from the authoritative
   held-button transition in continuous `SimulationInput`; the compiler/runtime MUST NOT require a
   new external intent variant. The Arbiter owns `hold_start_tick` and transfers it during handoff.
2. **Release-time targeting uses current authoritative input state.** When a hold-release ability
   resolves, the engine uses the latest accepted aim/cursor state for final direction/placement and
   clamps duration into `[min_charge_ticks, max_charge_ticks]` before feeding it to `P-43`.
3. **Runtime states are authoritative SoftState, not ad hoc effect-local blobs.** `bookmark`,
   `snapshot_buffer`, `sequence_window`, and `charge_pool` entries live in bounded per-entity
   runtime state keyed by compiled `RuntimeStateId`. They survive handoff and are validated by the
   compiled `RuntimeStateDefinition` table.
4. **Absolute-position semantics follow the core spatial contract.** `bookmark(position)` and
   `snapshot_buffer.position` store absolute world coordinates. If a later `P-01` relocation uses a
   stored coordinate that now belongs to a different Arbiter, owner resolution uses the CURRENT
   topology and the move follows the normal cross-boundary teleport/handoff rule from
   `docs-core/01-1-spatial-primitive-catalog.md`.
5. **Entity-reference bookmarks resolve late.** `bookmark(entity_ref)` stores an authoritative
   entity/actor ID. When a later read asks for `StoredEntityPosition`, the runtime resolves that
   entity's current local-or-Ghost position at execution time rather than preserving a stale
   coordinate snapshot.
6. **Compiler-owned runtime-state ops use the same stage scheduler as primitive instructions.**
   `WriteState`, `ClearState`, `AdvanceSequence`, and `ModifyChargePool` are not new engine
   primitives, but they execute in the same ordered instruction stream and obey the same
   intra-stage ordering rules. A `WriteState` that captures a pre-teleport origin MUST execute
   earlier in the same stage than the `P-01`/`P-02` relocation it feeds.
7. **Snapshot recorder states reuse core `P-05` semantics.** A status carrying
   `snapshot_recorder_state` requests the engine's canonical `P-05 Historical State Buffer`
   behavior. Recording timing, rewind semantics, and handoff preservation are exactly those defined
   in `docs-core/01-1-spatial-primitive-catalog.md` §3.5.
8. **Consumption windows are deterministic status metadata.** `consume_on = cast_ability` is
   checked in Stage 2 after activation-mode selection. `damage_received` and `on_hit` windows are
   checked in Stage 9. Matching windows apply their compiled `AbilityOverride` data to the active
   cast/event, increment consumption count, run any `on_consume_effects`, and then remove the
   status if its maximum consumption count is reached.
9. **Exact-match status consumption stays target-side authoritative.** `consume_status` resolves on
   the target's current authoritative owner by scanning that target's active status registry for
   exact `(status_id, source_entity)` matches. Matching entries are removed in deterministic
   oldest-first order as one `P-66` batch, and any `on_consume_effects` are deferred to the next
   tick in the same target context. When paired with `global_event`, this yields one mesh-wide
   detonation tick without a separate source-side status registry.

### 4.3 Special Combat-State Policies

The `CG-16` authoring surface lowers into a small set of deterministic compiler/runtime policies
instead of sketch-local one-offs.

1. **Escalating costs are Stage 2 policy, not ad hoc status logic.** `resource_cost.escalation`
   lowers to `P-51` plus a compiler-owned per-entity counter keyed by `shared_counter_id`.
2. **Shield absorb callbacks use the authoritative per-hit absorbed amount.** If `apply_shield`
   authors `bind_absorbed_value_as` plus `on_absorb_effects`, the runtime computes the actual
   damage prevented by that shield instance after higher-priority shields have already consumed
   their share of the incoming payload. It snapshots that scalar, preserves `caster` as the
   original shield source and `target` as the current bearer, and emits exactly one reactive
   callback payload for that absorb event. Any mutation aimed at a remote entity inside that
   callback, such as `modify_resource(target = caster, ...)` on an ally shield, uses the ordinary
   target-owner relay path.
3. **Shield removal hooks capture final shield state before removal.** If `apply_shield` authors
   `bind_remaining_value_as`, the runtime snapshots the remaining value immediately before removal
   and exposes it to `on_break_effects` / `on_expire_effects`. Lifecycle payloads are reactive and
   therefore obey the deferred-execution rule from §6.1.
4. **`modify_resource` is target-side authoritative and clamped.** The runtime resolves the target
   entity's current owner, computes `delta = amount + optional scaling contribution`, and applies
   the authored add/remove operation with a hard clamp to `[0, max_resource]`. Cross-boundary use
   does not introduce a special resource-credit event type; it is just another deferred target-owner
   mutation.
5. **`resource_stat_links` are live stat overlays, not one-shot snapshots.** While a status with
   `resource_stat_links` is active, the carrier's current local resource pool is read whenever the
   runtime builds effective offensive/defensive stat snapshots. The runtime computes
   `current_pool * coefficient` and applies it through the authored `StatModifier.operation`.
   Resource-linked offense therefore decays naturally as the underlying pool decays, without a
   second bespoke stat cache.
6. **Resource burn is target-side authoritative.** `resource_burn` reads and mutates the target's
   resource pool on the target owner, computes `actual_destroyed`, and derives bonus damage from
   that actual amount. Optional caster refund occurs only after the authoritative burn commits.
7. **Damage accumulators track resolved HP loss, not raw pre-mitigation numbers.**
   `damage_accumulator` records post-mitigation HP loss after barrier/shield/redirection decisions.
   If `include_absorbed_damage = true`, shield-absorbed damage is added explicitly by policy.
8. **Deferred ledger release is a single committed HP mutation.** `deferred_ledger` intercepts all
   HP damage/healing while active, freezes observer HP if configured, and on expiry/remove produces
   one net HP change without re-running mitigation or anti-heal. `P-24` bypass skips the ledger.
9. **HP-floor and death-prevention ordering is fixed.** `hp_floor` resolves before
   `death_prevention`. If the floor leaves the entity alive, death-prevention does not trigger.
   `death_prevention` restores HP according to its compiled ratio and optional anti-heal bypass
   policy, then consumes itself if configured.
10. **HP percentage swap is atomic and same-Arbiter by default.** `swap_hp_percent` captures both
   entities' current HP percentages before either write occurs. If `same_arbiter_only = true`, the
   cast is rejected when the resolved target is remote/Ghost at resolution time. The overwrite is
   not damage or healing and does not trigger damage/heal hooks.
11. **Execute checks happen on target authority.** `execute` uses `P-17` on the target owner to
   evaluate the threshold against the target's actual current HP. If the threshold succeeds and
   `bypass_prevention = true`, the runtime emits a `P-24` bypass-marked kill. Otherwise the
   authored fallback damage resolves normally.
12. **Stagger depletion is a mechanical break state.** `P-48` depletion applies the compiled
   stagger duration and vulnerability bonus from the target's `StaggerBarDef`, resets the bar only
   after the stagger window ends, and does not route that mechanical stagger through ordinary DR or
   status-resistance scaling.
13. **Counter windows belong to the broadcasting ability.** `vulnerability_window` lowers to a
    `P-65` directive on the broadcasting ability. A successful counter consumes the window, applies
    its authored bonus damage, and interrupts the active cast if the compiled policy allows it.

### 4.4 Control Topologies and Loadout Projection

The `CG-11` authoring surface lowers into deterministic Stage 1 routing metadata plus Stage 11
`P-31` loadout projection. The compiler MUST treat those as one shared contract rather than as
ten sketch-specific mechanics.

1. **Static control topologies are entity-definition metadata, not ability-local instructions.**
   `control_topology` serializes with `EntityDefinition` and installs its backing P-29/P-30 routing
   metadata when the entity or grouped entities become active. Reconnects, handoffs, and
   re-materialization MUST re-install the same topology from the static definition rather than from
   sketch-local runtime logic.
2. **`control_override` always commits at a Stage 1 boundary.** When an ability/status resolves a
   `control_override`, the active stage does not mutate routing immediately. Instead, the runtime
   captures the resolved target/controller pair plus lock metadata into a pending routing mutation.
   The next tick's Stage 1 commits that mutation atomically, so no tick ever sees split-brain input
   between old and new controller state.
3. **`swap_identity` and `borrow_ability_slot` are `P-31` policies.** Their authored effects lower
   to Stage 11 `P-31` instructions plus compiler-owned revert records keyed by `duration_ticks` and
   `usage_limit`. Revert payloads preserve the target entity's `entity_id`, authority owner, and
   spatial position; only loadout/profile/cooldown/stat projection changes.
4. **`entity_current_loadout` snapshots the source entity's EFFECTIVE committed loadout.** When
   `swap_identity.source = { entity_current_loadout: source_entity }`, the runtime reads the source
   entity's current ability/passive/profile projection at the moment the `P-31` instruction
   resolves. For cross-boundary cases, that snapshot is taken on the source entity's authoritative
   owner and relayed as immutable payload data; the target does not hold a live pointer into the
   source entity's later loadout state.
5. **Borrowed-slot selection reads a bounded public cast-history register.**
   `source_selector = last_cast_ability` resolves to the source entity's last ACCEPTED public
   `ability_id`, not to a hidden activation variant ID. The register is updated when Stage 2 admits
   the cast and is bounded to the single most recent public ability.
6. **Cooldown and HP projection are explicit policy, not inferred side effects.** `hp_policy` and
   `cooldown_policy` fully determine how `swap_identity` preserves or remaps state. The compiler
   MUST materialize any original-state snapshot needed for later revert as part of the same `P-31`
   instruction payload, so reversion is deterministic and does not query stale pre-swap state.
7. **Loadout projection does not change Arbiter ownership.** `swap_identity`, `borrow_ability_slot`,
   `control_override`, and `control_topology` can change who supplies inputs and which abilities are
   exposed, but they MUST NOT move authority to another Arbiter. Single spatial authority remains
   the engine invariant from `docs-core/01-spatial-runtime-kernel.md`.

### 4.5 Channel, Cast-State, and Concentration Lifecycle

The `CG-02` authoring surface lowers into one maintained-cast contract covering visible cast bars,
mid-cast cancellation, per-tick channel execution, and post-cast concentration ownership.

1. **Any non-zero cast publishes visible cast state.** When Stage 2 admits an ability with
   `cast_time_ticks > 0`, the runtime records a cast-state entry visible to nearby observers and to
   `P-40` interceptors. That record includes the public `ability_id`, scheduled completion tick,
   `can_be_counterspelled`, and whether the cast is a channel or concentration source.
2. **Counterspell cancels the cast, not the resource commit.** A successful `P-40` counter sets the
   cast state to cancelled, prevents completion effects from firing, preserves the already-committed
   resource cost, and leaves the ability on full cooldown. If the cancelled cast owns active
   channel outputs, Stage 11 teardown removes them in the same tick.
3. **`channel.execution_mode = complete_only` preserves the ordinary cast-time contract.** The root
   `effects` list resolves once on successful completion. If the cast breaks early, those effects do
   not fire, and `partial_cooldown_refund` applies after teardown.
4. **`channel.execution_mode = tick_while_active` re-evaluates the root effects on a fixed cadence.**
   The root `effects` list executes every `tick_interval_ticks` while the channel remains active,
   starting in the same tick after admission. This is the canonical lowering path for steerable
   beams, maintained control rays, and channel-owned area denial.
5. **Continuous input samples the already-authoritative player stream.** `steer_aim` reads the
   latest accepted aim/orientation state for the caster. `steer_target_movement` reads the
   controller's accepted steering state and feeds it into the controlled target through the Stage 1
   routing contract from §4.4. The compiler does NOT introduce a second external input API for
   channels.
6. **Channel break conditions are deterministic and bounded.** Active channels break on owner
   removal, on admission of canonical cast-interrupting CC profiles (`stun`, `silence`, `sleep`),
   on displacement if `break_on_displacement = true`, on target invalidation if
   `break_on_target_invalid = true`, and on any committed damage instance that exceeds
   `interrupt_on_damage_above` if that threshold is authored.
7. **Channels and concentration own persistent outputs by cast instance.** Statuses, zones, spawned
   actors, control overrides, and other persistent artifacts emitted by a channel or concentration
   instance are tagged to that maintained instance. Stage 11 teardown removes or reverts all
   instance-owned outputs on break, cancel, replacement, or expiry without requiring sketch-local
   cleanup logic.
8. **Concentration is post-resolution maintenance, not a channel.** A concentration ability may
   have `cast_time_ticks = 0` or `> 0`, but once its initial resolution succeeds the owner may move
   and cast other non-concentration abilities freely. The caster has exactly one active
   concentration slot; `replace_existing = true` tears down the previous concentration instance
   before installing the new one.
9. **`P-55` uses compiled default concentration policy unless overridden.** The default formula is
   `max(10, damage_taken / 2)` in deterministic fixed-point terms. `max_duration_ticks`, manual
   cancel, owner removal, and replacement all converge on the same Stage 11 teardown path.

### 4.6 Cross-Boundary Authority Matrix for Snaps and Target-Side Reads

The `CG-01` gap is not "more relay cases." It is one missing rule: when an effect depends on
remote authoritative state, the origin owner sends PARAMETERS, and the owner that already has the
authoritative data computes the result.

| Effect / Pattern | Local Resolution | Remote / Ghost Resolution | Authoritative Owner | Relay Payload |
|---|---|---|---|---|
| `P-01` instant translation to a known local position | Current owner validates destination and commits the snap locally. | If the committed destination belongs to another Arbiter, perform destination-based handoff at the same tick boundary after the snap resolves. | Destination owner after handoff; origin owner before handoff. | Destination position + ability instance identity only. |
| `P-01` destination derived from a target entity (`Blink Strike`) | Current owner computes "behind target" from the target's local pose/facing, validates walkability, snaps, and resolves the immediate follow-up strike. | Origin owner MAY use Ghost data only for admission/range preview. If the target is remote/Ghost or the computed destination is in another Arbiter's region, the origin owner emits a `cross_boundary_snap` request. The destination owner re-derives the behind-target point from the TARGET'S authoritative pose/facing, validates it, commits the snap, and resolves the follow-up strike there in the same tick. | Destination owner for the final snap + strike when the snap crosses or targets remote authority. | `ability_id`, caster entity ID, target entity ID, relative-offset spec, and any already-committed offensive payload needed for the follow-up strike. No guessed destination coordinates from Ghost data are authoritative. |
| `P-49` resource destruction to damage (`resource_burn`, `Mana Burn`) | Target owner reads the local resource pool, computes `actual_destroyed`, mutates the pool, and derives bonus damage in-place. | Origin owner sends only the authored burn parameters with the prepared hit. The target owner reads current resource, computes `actual_destroyed`, mutates the pool, and derives bonus damage locally before continuing ordinary damage resolution. | Target owner. | Authored burn amount, damage ratio, resource pool ID, optional caster refund flag, and the prepared-hit combat payload. |
| Target-side threshold / paired-write mechanics (`execute`, `swap_hp_percent`) | Current owner resolves directly using the local target state. | `execute` always runs the threshold check on the target owner. `swap_hp_percent` rejects remote targets when `same_arbiter_only = true`; if a future cross-Arbiter variant is added, both HP reads/writes must be committed by the owners that already hold those pools. | Target owner for threshold checks; paired owners for future non-local paired writes. | Parameters only; no origin-side guessed thresholds or HP percentages. |

Normative consequences:

1. **Ghost data is advisory for admission, never authoritative for final state-dependent math.**
   Ghost pose/facing may be used to decide whether a cast is worth attempting, but any snap point,
   resource read, or threshold check that materially changes authoritative state is recomputed on
   the owner that already holds that state.
2. **Origin owners relay intents, not outcomes.** For `Blink Strike`, the relay says "snap behind
   target using this relative rule," not "teleport to coordinate X." For `Mana Burn`, the relay says
   "burn up to X mana at ratio Y," not "I already burned 28 mana."
3. **Destination-based snaps keep single authority.** A cross-boundary instant snap does not create
   a travel window or dual ownership. The destination owner becomes the sole authority for the
   post-snap entity state and any immediate follow-up strike in that same tick.
4. **Result payloads flow backward only as observation.** If the origin owner needs `actual_destroyed`
   or final snap outcome for UI, metrics, or later deferred logic, that value returns as a result
   payload after the authoritative owner commits it. The backward payload does not reopen authority.

### 4.7 Persistent Linkage, Redirection, Mirroring, and Origin Anchors

The `CG-04` authoring surface lowers into one canonical `P-34` binding record with optional
consumers in Stage 6, Stage 8, Stage 9, and Stage 12.

1. **Binding record shape:** `link` compiles to `P-34` metadata carrying a stable `binding_id`,
   resolved source entity ID (default `caster`, but compiler-authored helpers may supply another
   resolved entity ref), target entity ID, expiry tick, optional `break_distance`, removal flags,
   optional generated cleansable-status handle, and any authored `damage_redirect`,
   `heal_mirror_ratio`, `event_clone`, or `origin_override` policy payloads.
2. **Symmetric bindings are one logical pair.** If `symmetric = true`, the compiler emits a
   single logical binding pair with mirrored direction metadata under one `binding_id`. Expiry,
   cleanse, source/target removal, or break-distance failure removes both directions atomically
   before later same-tick consumers run.
3. **Break-distance checks happen after movement commits.** If a binding authored
   `break_distance`, the engine evaluates that threshold in Stage 6 using the entities' current
   local-or-Ghost positions after KinematicResolution. A failing check removes the binding before
   later Stage 8/9/12 consumers observe it, so teleports, pulls, and handoffs can snap links in
   the same tick.
4. **Damage redirection consumes the binding at Stage 8.** `damage_redirect` is the canonical
   authoring path for Tether-style sharing and Guardian-style interception. The currently resolving
   target's owner splits the incoming pre-mitigation damage packet according to the compiled ratio,
   keeps the unredirected remainder on the current target, and emits one redirected sibling branch
   toward the linked partner. That redirected branch is a NEW combat branch against the partner and
   therefore uses the partner's own shields, mitigation, block checks, death-prevention rules, and
   later hooks. `max_hops` is the recursion bound; the current canonical default is `1`.
5. **Heal mirroring and event cloning consume the binding at Stage 9.** `heal_mirror_ratio`
   copies the final committed healing amount from the source resolution and emits a fresh reactive
   heal against the linked partner. `event_clone` replays only the authored envelope classes
   (`clone_damage`, `clone_healing`, `clone_status`) and currently only for `SingleTarget`
   abilities. Both behaviors resolve the partner branch against the partner's own state rather than
   copying the first target's final result.
6. **Anti-recursion is part of the canonical contract.** Any event emitted from `heal_mirror_ratio`
   or `event_clone` carries the originating `binding_id` plus anti-recursion flags. A reactive
   branch MUST NOT emit another mirror or clone through the same binding. This keeps
   `SK-04 Tether` and `SK-111 Soulbind` bounded without sketch-local loop policy.
7. **Origin override changes spatial origin queries only.** `origin_override` lets an actor use
   the linked partner's CURRENT position when resolving range checks, projectile spawn points,
   ground-target centers, and other origin-derived spatial queries. It does not move the actor
   body, transfer authority, borrow the partner's stats/cooldowns, or change which entity owns the
   cast input. If the linked partner is remote, ordinary cross-boundary relay rules still determine
   which Arbiter authoritatively resolves the spatial query.
8. **Observer anchors change payload anchoring only.** If `origin_override.observer_anchor = true`,
   Stage 12 downstream payloads for the acting entity are emitted from the linked partner's
   vicinity instead of the body's vicinity. This is a camera/observer anchor rule only; it does
   not make the body untargetable, does not transfer visibility ownership, and does not change
   gameplay authority.
9. **Bindings survive handoff as ordinary SoftState.** `P-34` link metadata lives on both
   participants and survives Arbiter handoff exactly like other authoritative SoftState. Consumers
   that need only the partner pose use current local-or-Ghost data. Consumers that need a fresh
   partner-side resolution, such as redirected damage or cloned single-target effects, relay the
   original branch parameters to the partner owner instead of relaying guessed outcomes.

### 4.8 Recursive Propagation, Repeated Casts, and Autonomous Spread

The `CG-08` authoring surface lowers into compiler-owned propagation state attached to trigger
instances or status instances. This state is not a new engine primitive; it is bounded metadata the
engine/runtime must preserve when scheduling deferred child generations.

1. **Every propagation tree has one stable `chain_id`.** The root trigger or initial status
   application mints a `chain_id` and starts at `generation = 0`. All descendants inherit that same
   `chain_id` and increment `generation` before their own child emission logic runs.
2. **`max_generations` is the cross-tick termination bound.** If the current generation is already
   equal to the authored `max_generations`, the event/status instance resolves normally but MUST NOT
   emit further children. This bound is separate from `reactive_depth`: `reactive_depth` limits
   within-tick hook chains, while `max_generations` limits deferred multi-tick trees.
3. **Chance scaling is deterministic.** If authored, the effective emission chance for a child
   generation is `base_chance * chance_multiplier_per_generation ^ generation`, clamped into
   `[0, 1]`, and evaluated through the engine's deterministic combat-roll path. Child generations do
   not invent fresh probability state.
4. **Effect scaling is generation-based metadata.** `effect_multiplier_per_generation` scales the
   emitted child payload before it re-enters the pipeline. Chain Lightning-style decay and
   Crit-Explosion-style generation falloff both lower through this one multiplier rule instead of
   sketch-local math.
5. **`bounce_nearest` chooses exactly one next target.** The emitting owner runs a bounded spatial
   query within `query_radius`, sorts candidates by `(distance, entity_id)`, removes any candidate
   excluded by `dedup_scope = entity_once_per_chain`, and selects the first remaining target only.
6. **`fanout_query` emits one child per eligible result.** The emitting owner runs the authored
   bounded query, sorts candidates deterministically, applies any `entity_once_per_chain` filter,
   truncates to `max_targets_per_generation`, and emits one child branch per remaining target.
   Those branches all share the same `chain_id` and next `generation`.
7. **`repeat_same_cast` snapshots the original targeting envelope.** At root emission time, the
   runtime stores the public `ability_id`, target entity or ground position snapshot, and any
   compiler-authored replay bypass policy for resources/cooldown. Child generations re-enter as full
   ability casts using that same snapshot, flagged as replayed so cost/cooldown handling follows the
   compiled policy rather than player-input admission.
8. **Status spread uses the carrier's owner, not the original caster's owner.** `SpreadBlock`
   timers fire on the current carrier's authoritative Arbiter. That Arbiter performs the bounded
   query locally, relays child applications for Ghost/remote results, and preserves the original
   `chain_id`, caster/credit owner, and incremented `generation`.
9. **Dedup state is part of the propagation metadata.** `entity_once_per_chain` carries a bounded
   visited-entity set keyed by `chain_id`. Any candidate already present in that set is skipped
   before child scheduling. The root target/carrier is seeded into that set before the first child
   query. Cross-boundary relays carry the same visited-set metadata so a chain cannot re-hit an
   earlier target just because authority changed.

### 4.9 Targetability, Observer Presentation, and Suspension

The `CG-10` authoring surface lowers into entity/status metadata consumed by `P-27`, `P-33`,
`P-52`, and `P-53`.

1. **Targetability is relation-scoped, not one global boolean.** The runtime resolves incoming
   components against `hostile_effects`, `allied_beneficial_effects`, `allied_harmful_effects`, and
   `self_effects`, plus the spatial-admission flags `affected_by_area_effects`,
   `collidable_for_skillshots`, and `collidable_for_pathing`.
2. **Entity defaults and status overlays stack by restriction.** Entity-definition
   `targetability_policy` / `observer_presentation` establish the permanent base state. Active
   statuses may overlay stricter targeting or presentation rules. For targeting, the most
   restrictive effective value wins for the current query channel.
3. **AoE and skillshot admission use the same policy.** If `affected_by_area_effects = false`, the
   entity is skipped by overlap/pulse application even when spatially inside the authored shape. If
   `collidable_for_skillshots = false`, line/projectile collision tests MUST ignore the entity for
   impact purposes. If `collidable_for_pathing = false`, ordinary movement/pathing/body-separation
   logic MUST ignore the entity as a blocking body.
4. **Observer presentation is downstream-only.** `appearance_source = mirror_entity`,
   `enemy_hp_presentation`, visibility-to-team flags, and ally markers are applied only during
   Stage 12 payload construction. They do not change authoritative HP, stats, or entity identity.
5. **Suspension has three canonical modes.** `suspended` suppresses ordinary action execution while
   leaving timers active unless explicitly paused. `dormant` lowers to `P-33` dormant-state
   metadata that skips ordinary active evaluation. `stasis` is the timer-pause variant and may also
   combine with invulnerability and targetability denial for full time-stop behavior.
6. **Timer pausing is expiry-shift semantics, not ad hoc freezing.** When a stasis effect pauses
   status timers or cooldowns, the runtime resumes them by shifting their stored expiry ticks
   forward by the elapsed stasis duration. This keeps timer ordering deterministic across relays and
   avoids per-tick mutation of every paused timer.
7. **Targetability admission must survive handoff and Ghost filtering.** The neighbor-visible
   admission bits needed for hostile/allied/self targeting, AoE inclusion, and skillshot/pathing
   collision MUST be mirrored into the Ghost/query metadata used for local admission filtering, so
   nearby Arbiters do not waste relays on targets that are guaranteed to reject.

### 4.10 Advanced Projectile Lifecycle Mutation

The `CG-14` authoring surface lowers into a mix of archetype-owned projectile metadata,
ability-local kinematic-flight params, and status-owned `P-61` interception policy.

1. **Spawned projectile IDs may be bound only when one actor is created.** `spawn_actor.output_binding`
   is legal only for `count = 1` and yields the created actor ID for later runtime-state writes,
   reactivation lookups, or follow-up targeting. This is the canonical path for mechanics like
   `Spectral Dash` that need a live projectile as a moving bookmark.
2. **Travel-based mutation is deterministic from cumulative world distance traveled.** If an
   archetype declares `radius_growth_per_unit` or `payload_scale_per_unit`, the runtime derives the
   projectile's current collision radius and payload scalar from the projectile's authoritative
   `distance_traveled`. These values survive handoff as ordinary projectile SoftState.
3. **Return flight is a phase transition, not a new projectile.** `return_policy` flips one live
   projectile from outbound to return mode, preserves its stable actor ID, and swaps steering to
   the compiled source-entity tracking rule. If `allow_repeat_hits_on_return = true`, the runtime
   keeps separate outbound and return hit ledgers so one target may be hit once per leg but not
   repeatedly within a single leg.
4. **Wall bounce is multi-segment within one tick.** `bounce_policy` with
   `detonation_policy.world_impact = bounce` authorizes repeated wall reflection during the same
   movement step until the projectile either consumes its remaining travel distance, hits an entity,
   or reaches `max_bounces`. Bounce count and reflected heading survive handoff.
5. **Attachment converts impact into a carried delayed payload.** `attachment_policy` turns the
   first admitted entity impact into an attached timed payload owned by the struck entity's current
   Arbiter. At expiry, the payload resolves at the carrier's current position when
   `follow_attached_entity = true`; otherwise it resolves from the original impact point.
6. **Entity-as-projectile behavior reuses displacement plus a bounded flight overlay.**
   `displacement.flight_policy` does not create a new actor. It layers `P-07`-style overlap checks,
   per-flight dedup, and optional world-impact payloads onto one forced-displacement move for the
   already authoritative entity.
7. **Projectile interception is one bounded `P-61` policy.** A status carrying
   `projectile_intercept` may hijack an incoming projectile after the local hit resolves, increment
   redirect generation, and retarget it to the original source entity. Returned projectiles
   preserve their carried payload only when the authored status allows it, and redirects that would
   exceed `max_redirect_generations` are rejected instead of spawning a new ping-pong loop.
8. **`carry_policy` adds a bounded projectile-local carry roster, not a second container system.**
   The projectile keeps an ordered list of currently carried target entity IDs, capped by
   `max_carried_targets`. The roster is runtime state on the projectile actor itself; it does not
   serialize full entity state into the projectile.
9. **Carried targets remain ordinary entities with projectile-driven kinematics.** While carried,
   a target stays in the authoritative R-tree and may still be targeted by ordinary effects, but
   its voluntary movement, casts, attacks, and item use are suppressed. Its current position is
   derived each tick from projectile heading plus the compiled front/lateral slot offsets.
10. **Projectile handoff carries the roster; entity handoff carries the entities.** The projectile
    snapshot serializes the ordered carried-target ID list. Those entities still transfer through
    the ordinary single-authority entity handoff path; if the projectile handoff commits one tick
    before a carried entity's co-located handoff, the entity follows the projectile shadow/ghost
    until reunified. World impact, expiry, or projectile removal releases the entire roster at the
    projectile's current committed position in preserved capture order.

### 4.11 Zone Lifecycle, Mobility, and Relation Gates

The `CG-05` authoring surface lowers into one shared contract for zone actors, mobility, early-end
rules, continuous force, and zone-conditioned hostile admission.

1. **Zones are ordinary spawned actors with zone-local state.** A zone actor owns its current
   center, radius/shape, remaining lifetime cap, pulse schedule, optional occupant set, and any
   mobility / force metadata. It begins evaluation on the next tick like other `P-32` actors.
2. **Zone mobility has three canonical moving modes.** `attached_entity` samples the target's
   current authoritative local-or-Ghost position every tick. `self_propelled` advances by a fixed
   heading derived from `heading_from -> heading_to`. `tracking_entity` moves toward the target's
   current position at capped speed and obeys the authored `on_target_removed` rule.
3. **`duration_ticks` is always a hard cap.** `ZonePersistenceBlock` may end a zone earlier, but it
   never removes the hard cap. `until_empty_on_pulse` evaluates on pulse ticks using the zone's
   admitted target count after filtering and after the authored `count_ghost_hits_as_occupants`
   choice is applied.
4. **Enter/leave and persistence checks reuse one occupant-set model.** If a zone authors
   `enter_effects`, `leave_effects`, or `until_empty_on_pulse`, the runtime maintains a bounded
   occupant set keyed by entity ID. Diffs are computed from the zone's committed current position so
   stationary, drifting, attached, and tracking zones all use one deterministic membership rule.
5. **Continuous radial force is pre-kinematic, not a post-hit patch.** `continuous_force` is
   evaluated every tick for currently admitted occupants and emits deterministic movement influence
   into the next kinematic step using a linear interpolation from `strength_at_edge` to
   `strength_at_center`. Escape is therefore the result of net movement after normal input plus the
   authored force field, not a bespoke zone-only displacement exception.
6. **Zone output bindings expose one live zone actor ID.** `zone.output_binding` yields the created
   actor ID so later runtime-state writes or follow-up effects can refer to that specific live zone
   instance. This is the canonical path for zone-conditioned defensive logic.
7. **Zone relation gates check live membership, not a static cast snapshot.** A status carrying
   `zone_relation_gate` resolves the referenced live zone actor from runtime state and checks
   defender/source membership against the zone's CURRENT position and radius. Missing hostile source
   position counts as outside. Rejected hostile effects are dropped before target admission, and
   rejected damage components are zeroed before ordinary mitigation.
8. **Combo-matrix results now expose the interacting field context.** When `P-64` detects an
   admitted finisher/field pair, the runtime snapshots `combo_field_entity`, `combo_field_owner`,
   `combo_field_position`, and `finisher_position` before any combo-result effects execute.
   `caster` remains the finisher user/source; the combo-field refs are additional contextual
   selectors available only inside the resolved `combo_matrix` entry's effect list.
9. **Live field replacement is ordinary authored effect sequencing.** Because a combo entry now
   carries an `EffectList`, a result may first `despawn_entity(combo_field_entity)` and then spawn
   a replacement zone/actor at `combo_field_position` with explicit `owner = combo_field_owner`.
   The field position snapshot survives the earlier removal, so oil-to-fire style transformations
   remain deterministic without inventing a second combo-only spawn path.

### 4.12 Injected Geometry, Polyline Corridors, Sweeps, and Movement Constraints

The `CG-06` authoring surface lowers into one shared spatial contract for temporary geometry,
path-recorded corridors, body-based sweeps, and bookmark-driven leash constraints.

1. **Injected geometry has two canonical lowering paths.** `inject_geometry` in `circle`, `box`,
   or `ring` mode lowers directly to one bounded `P-08` geometry record. `inject_geometry` in
   `segment` mode lowers to one fixed `P-57` corridor with `max_segments = 1`, because arbitrary
   wall orientation is represented as a segment corridor rather than as a rotated `P-08` box.
2. **Polyline corridors sample committed source motion, not intent.** `polyline_zone` owns a
   bounded ring buffer of sampled points and active segments. Sampling occurs after the source
   entity's movement for the tick is committed, so the corridor always reflects the same
   authoritative path seen by movement damage, zone admission, and cross-boundary handoff.
3. **Collision flags and occupant effects share one active corridor.** When `polyline_zone`
   authors blocking flags, enter/leave effects, or pulse effects, all of those behaviors operate on
   the same current active segment set after FIFO expiry/removal is processed. The compiler MUST
   NOT create separate blocking and damage geometries for one authored corridor.
4. **`kinematic_sweep` is the canonical `P-07` authoring surface.** The moving entity remains the
   sole authoritative actor. `toward_position` mode advances along one bounded path to the resolved
   destination. `orbit_entity` mode maintains compiler-owned orbit state and recomputes a derived
   offset from the anchor's current local-or-Ghost pose each tick before the sweep overlap pass.
5. **Capture-first sweeps become temporary attachment, not shared authority.** When
   `on_entity_hit = capture_first`, the first admitted hit installs a transient `P-06` attachment
   from the captured entity to the sweep source for the remainder of the sweep. The captured target
   follows the sweeper through ordinary co-located handoff and is released deterministically when
   the sweep ends or the authored break condition fires.
6. **Orbit sweeps use per-revolution dedup, not unbounded per-frame re-hits.** When
   `unique_hit_scope = entity_once_per_revolution`, the runtime carries a revolution-local hit
   ledger keyed to the orbit state and resets it only after the accumulated orbit angle crosses a
   full turn. This is the canonical anti-multi-hit contract for repeated circular pass-through
   motion.
7. **Movement constraints are status-owned `P-04` checks keyed by runtime bookmarks.** A status
   carrying `movement_constraint` resolves its bookmark payload every PostKinematic tick and applies
   the canonical distance-limit rule after all movement for the tick is committed. Because the
   anchor lives in runtime state, the same status surface supports fixed world anchors, moving
   entity anchors, and cross-boundary Ghost-backed anchors without a separate leash primitive.

### 4.13 Container Profiles, Portal Anchors, and Instance Forks

The `CG-12` surface lowers through one shared contract for containment, portal anchors, and bounded
single-host instance forks.

1. **Container rules are split between static profile and dynamic entry/exit mutations.**
   `ContainerProfileDef` is archetype-static entity metadata that defines capacity, entry range,
   occupant targeting, and occupant cast policy. `enter_container` / `exit_container` then emit the
   actual `P-58` mutations against live entities.
2. **Containment has two bounded storage modes.** `occupant_storage_mode = attached_visible` is the
   ordinary P-06 vehicle/bunker path: the occupant remains spatially present and follows the
   container. `off_world_stored` is the devour-style path: the occupant is removed from the spatial
   world, receives no queries or payloads, and is carried as preserved container-owned state until
   exit or forced eject. In both modes, container death still force-ejects the occupant before any
   authored follow-up effects run.
3. **Portal anchors are spawn-local network metadata, not a second actor class.**
   `spawn_actor.portal_anchor` configures a normal spawned actor to register as a `P-59` anchor.
   Pair-style portals use `spawn_actor.output_binding` plus a bookmark runtime state to remember the
   first anchor. Owner-scoped portals join one shared network keyed to owner + ability identity.
4. **Destination choice is engine-owned once the network exists.** For `destination_mode =
   player_choice`, the Arbiter hosting the source anchor already knows the live replicated network
   membership from the `P-59` registry and presents only valid destinations. The chosen destination
   then resolves through ordinary `P-01` teleport + destination handoff rules.
5. **`fork_instance` now supports one-time remote admission while staying single-host after
   creation.** The CURRENT Arbiter remains the host for the live instance. If some authored members
   are remote, the engine uses the `docs-core` pre-instance transfer protocol to admit them to that
   host before the instance begins. Once the instance is live, all members are local to the host
   and the instance itself still does NOT become cross-Arbiter state.

### 4.14 Controller-Escalated Global Events

The remaining `CG-17` surface that is already consistent with `docs-core/` lowers through one
shared contract for `P-46` scheduled fan-out.

1. **`global_event` is schedule metadata, not a second ability body.** The authored ability still
   compiles one normal `AbilityIREntry`. `global_event` adds a `P-46` scheduling policy to that
   entry; it does NOT define a separate hidden spell or side channel.
2. **Scheduling happens only after the cast instance commits.** If a channel breaks, a cast is
   counterspelled, or admission fails, no controller request is emitted. For `SK-05 Global Strike`,
   the schedule request is emitted only after the channel completes successfully.
3. **The offense-side payload is baked once at schedule time.** The caster's authoritative owner
   captures the current data epoch, ability ID, offense-side context, and compiled global-event
   selector/geometry policy into one deterministic controller request. Later target owners do NOT
   re-read the caster's future stats.
4. **Target owners still resolve defense locally at execute time.** At the coordinated execute
   tick, every Arbiter evaluates the event only against its OWN authoritative entities. It applies
   the authored geometry, `filter`, and `target_class`, then resolves the root ability `effects`
   list locally against each admitted target. This preserves the same single-authority rule as
   cross-boundary prepared-hit relays: offense is baked once, defense remains target-local.
5. **Membership is evaluated at execute time, not locked at schedule time.** If an entity newly
   matches the authored selector before the execute tick, it may be hit. If a previously eligible
   entity dies, leaves the geometry, or otherwise stops matching, it is skipped. Periodic
   controller-scheduled events reuse the same baked offense payload on each pulse while re-running
   local target admission every pulse tick.

### 4.15 Spawned Actor Autonomy, Proximity Interaction, Coverage Networks, Live Limits, and Split-Form Groups

The remaining `CG-09` surface that is already consistent with `docs-core/` lowers through one
shared contract for ability-local spawned-actor behavior metadata.

1. **`spawn_actor` now has eight ability-local behavior blocks.** `placement`, `autonomy`,
   `interaction`, `coverage`, `instance_limit`, `loadout_projection`, `control_projection`, and
   `respawn_anchor` stay on the spawn directive / param payload, not on the static entity
   archetype. The spawned actor still uses its normal `EntityDefinition` for HP, movement,
   abilities, targeting, and presentation; these blocks add bounded runtime behavior on top.
2. **Placement is one deterministic anchor expansion.** The authored `position` resolves once to
   one anchor point. If `placement` is present, the runtime applies each authored fixed-point
   offset in authored order and emits one independent `P-32` spawn request per derived point. If
   an offset also authors a heading vector, the runtime carries that normalized launch heading with
   the derived spawn and uses it as the initial outbound velocity direction for projectile actors.
   This is the canonical no-target radial/salvo launch path. No procedural scatter, random roll,
   or facing-derived rotation is implied by this surface. If `placement` is omitted, multi-count
   spawns still share the same resolved anchor point.
3. **Autonomy is one deterministic FSM, not arbitrary scripted AI.** `SpawnAutonomyBlock` installs
   a compiler-owned loop of: idle anchor selection -> target acquire -> chase/attack -> leash
   return. `attack_mode = basic_attack_only` uses the entity's ordinary auto-attack path.
   `use_authored_abilities` may only consume the actor's declared ability list in deterministic
   order with normal cooldown/range validation; it does not introduce freeform behavior trees.
   `idle_mode = follow_owner` or `follow_entity` samples the current local-or-Ghost anchor pose
   each tick, while `on_owner_removed` selects the bounded cleanup rule when the owner disappears.
4. **Interaction is one armed proximity state machine.** Before `arming_delay_ticks` elapses, the
   actor ignores trigger candidates. Once armed, the runtime runs the admitted `P-14` overlap check
   every tick in deterministic query order. `collector_only` applies the authored `effects`
   directly to the first admitted trigger entity. `radius_query` treats the actor's current
   position as the origin for one secondary overlap query using `effect_radius` / `effect_filter`,
   then applies the authored `effects` to that result set. If `consume_on_trigger = true`, removal
   happens only after the trigger effects commit.
5. **Triggered effects still use the ordinary authority/relay rules.** A potion collected by a
   Ghost or a mine blast that overlaps Ghost targets does not mutate Ghost state locally. The
   spawned actor's current owner emits the same effect parameters it would have used on a local
   target, and the authoritative target owner resolves healing/damage/status admission there.
6. **Visibility and targetability for mines or pickups reuse existing policy surfaces.** The
   interaction block does not invent a second stealth or dormancy system. Invisible mines still rely
   on canonical `observer_presentation`, `targetability_policy`, and optional suspension metadata;
   the interaction block only decides when the armed actor may resolve its trigger payload.
7. **Coverage is one live provider/consumer registry keyed by `network_id`.** Provider actors
   publish a coverage disc from their current position plus `radius`; consumer actors with the same
   `network_id` are considered powered when at least one admitted provider covers them. If
   `require_for_spawn = true`, spawn admission fails unless coverage exists at the requested spawn
   point. On provider or consumer spawn, removal, position change, or handoff, the runtime
   recomputes powered state. `unpowered_mode = dormant` or `suspended` then reuses the canonical
   suspension contract rather than inventing a bespoke "disabled turret" execution path.
8. **Coverage remains single-authority even across boundaries.** Providers never split into a
   multi-owner field object. A consumer owner evaluates coverage from current local providers plus
   Ghost-backed provider poses replicated through the normal spawned-actor visibility path, so a
   pylon near a seam may still power a turret across the boundary without shared mutable state.
9. **Live-count caps are enforced before spawn commit.** `instance_limit` buckets live actors by
   `(owner, ability_id)` or `(owner, archetype_id)` according to `scope`. `reject_new` fails the
   spawn deterministically. `despawn_oldest` removes the oldest matching live actors first, ordered
   by original spawn tick then stable actor/entity ID, before the new spawn is inserted. The live
   count therefore never exceeds `max_live` after a commit.
10. **`respawn_anchor` is one revocable post-terminal route override.** At spawn commit, the
    runtime registers the created actor as the current rebirth anchor for its resolved `owner` in
    one owner-scoped live record that follows the anchor across handoffs/removals. When Stage 10
    later commits terminal death for that owner and the anchor is still live, the runtime snapshots
    `anchor_entity_id`, the anchor's authoritative position, and the authored
    `respawn_delay_ticks` into `PlayerDied.respawn_override = RespawnAnchor { ... }`. If the
    anchor is removed before Meta's re-injection commits, the current anchor owner emits
    `RespawnOverrideRevoked { victim, source_entity_id }`. When Meta later injects
    `SpawnEntity { respawn_context = Some(RespawnSpawnContext::RespawnAnchor { anchor_entity_id }) }`,
    the target Arbiter validates the anchor still exists, consumes it atomically, and spawns the
    owner at the anchor position. Validation failure emits the same revocation event and leaves
    Meta on the stored base respawn schedule.
11. **`loadout_projection` snapshots one source loadout at spawn commit.**
    `LoadoutSource = { entity_current_loadout: ... }` follows the same source-authority rule as
    `swap_identity`: if the source is remote, its owner captures the immutable projected
    loadout/passive/appearance snapshot and relays it to the spawn owner before the spawn commits.
    `corpse_snapshot` reads the retained corpse record locally through the canonical `CG-13`
    contract. Later source changes do not live-update the spawned actor.
12. **Clone-style stat scaling is part of the spawn payload, not a second transformation pass.**
    `loadout_projection.max_hp_multiplier` and `stat_multiplier` apply once when the projected
    shell is initialized. `excluded_abilities` removes authored public abilities from the projected
    loadout before the actor begins evaluation, so "clone basic skills but not the ultimate" does
    not require sketch-local pruning logic.
13. **`control_projection` is one single-actor dynamic routing overlay.** At spawn commit, the
    runtime records one controller -> spawned-actor routing relationship and commits it at the next
    Stage 1 boundary using the existing `P-29` / `P-30` routing machinery. `control_scope`
    constrains which portion of the controller's input stream is redirected; the actor otherwise
    remains a normal authoritative entity with ordinary targeting, damage, and handoff behavior.
14. **Owner-body handling is explicit and bounded.** `root_owner` leaves the owner in-world and
    expects ordinary channel/status authoring to immobilize or cast-lock it as needed. 
    `suspend_owner` snapshots and suspends the owner's body state before the Stage 1 routing
    redirect commits. If `on_actor_removed` or `on_expire` selects `restore_owner`, the runtime
    unsuspends the stored owner body at either the projected actor's current/last position or the
    owner's original position and applies the selected HP restore policy.
15. **Control teardown callbacks execute in a projected-actor context.** `manual_trigger_effects`,
    `on_expire_effects`, and `on_controller_break_effects` all run with `caster = controller` while
    additionally exposing `projected_actor` and `projected_actor_position`. This lets a remote bomb
    explode from its OWN current position while still scaling from the summoner/controller.
16. **Manual trigger is a generated same-slot action, not a second freeform input plane.** When
    `manual_trigger_effects` is authored, the compiler exposes one temporary same-slot action to the
    controller for the lifetime of that control session. The action resolves through the ordinary
    cast path using the callback context above, so "detonate while steering" does not require a new
    network transport or a global UI subsystem beyond temporary ability availability.
17. **Expiry and controller-break callbacks are lifecycle-local; destruction is not.**
    `on_expire_effects` fire only for natural lifetime expiry before `on_expire` owner cleanup.
    `on_controller_break_effects` fire only when the control session collapses because the controller
    lost the maintained control state before expiry or manual trigger. External destruction/removal
    still follows `on_actor_removed` cleanup only, which cleanly models "enemy killed the bomb, so
    no detonation."
18. **`control_projection` intentionally stops at one projected actor.** Clone-shell control
    transfer and remote-controlled bombs are canonical through `control_projection`. Multi-member
    split/reform groups use the separate `split_form` contract below rather than overloading the
    single-actor projection surface with ambiguous group semantics.
19. **Actors without these blocks remain ordinary spawned entities.** A spawned bomb, clone shell,
    rebirth anchor shell, or other controlled actor that authors no compiler-owned
    autonomy/interaction/coverage/loadout/control/respawn-anchor behavior still works through the
    existing control, channel, targeting, and lifetime contracts. The new blocks only cover the
    repeated actor-lifecycle patterns that were previously sketch-local.

#### Directed Transit

1. **`start_actor_transit` is a late-bound move on a live actor, not a second spawn type.** The
   effect resolves one current actor, snapshots one absolute destination position, and installs one
   bounded transit record on that actor. The actor may already be carrying occupants, projected
   loadout, control routing, or other spawned-actor state; transit adds destination-flight on top
   of the existing shell.
2. **Transit motion is compiler-owned kinematics, not voluntary input.** Each tick, the actor's
   current owner advances it in a straight line toward the stored destination at the authored fixed
   speed. Ordinary movement input, move-speed stats, and cast intent are not what drive the motion.
   The actor remains a normal targetable/damageable body unless other authored status/targetability
   rules say otherwise.
3. **Cross-boundary travel is repeated ordinary handoff.** The transit record survives actor
   handoff exactly like projectile return state, bookmark state, or container occupancy. The new
   owner resumes the same destination/speed record from the actor's committed current position.
4. **Arrival is one committed snap plus callback context.** When the actor enters
   `arrival_radius` or the next step would overshoot, the current owner snaps the actor to the
   stored destination, clears the transit record, and then resolves `on_arrival_effects` in a
   transit callback context where `caster` remains the original transit-cast source while
   `transit_actor` / `transit_actor_position` name the arrived shell. This is the canonical way to
   eject bunker-style occupants, despawn the shell, or emit arrival payloads on landing.
5. **Removal-before-arrival is not a transit callback problem.** If the actor dies or is removed
   mid-flight, the transit record simply disappears with it. Destruction fallout such as "eject all
   occupants and stun them" remains authored through ordinary `P-58` exit/eject rules and actor
   `on_death`/removal behavior, which keeps transport crash handling inside the existing lifecycle
   model rather than inventing a second transit-failure subsystem.
20. **`split_form` is the bounded multi-member exception.** Unlike `control_projection`,
    `split_form` does not live on one spawned actor. It references multiple prior
    `spawn_actor.output_binding` entries from the same ability, stores the original owner's body,
    and opens one compiler-owned split session keyed by `(controller, source_ability_id)`.
18. **Split sessions reuse the existing `P-30` coordinator model.** The runtime installs one
    `OneToMany + AdapterRouted` multiplex group whose current active member is the `primary_entity`
    and whose other surviving members are `secondary_entities`. At any tick, exactly one member
    receives direct movement/ability proposals. If the active member lives on another Arbiter after
    a handoff or a rotation, coordinator ownership follows the new `primary_entity` exactly as
    `docs-core/01-3-entity-relationship-contract.md` §4.4 already requires.
18. **Inactive members are bounded followers, not freeform AI scripts.** `inactive_mode =
    follow_active` samples the current active member's authoritative-or-Ghost pose each tick and
    applies one deterministic follow/leash loop using the authored distance/radius values. This
    governs movement only; it does not invent a second combat-AI system.
19. **`cycle_split_form` advances selection only at a Stage 1 boundary.** The helper resolves the
    live split session for `(controller, source_ability_id)`, picks the next surviving member in
    authored binding order, and enqueues one pending routing mutation for the next tick. No tick
    ever sees two active members or split-brain direct input.
20. **The stored owner body is restored only through the split session's authored end policy.**
    While the session is active, the original owner body is suspended and absent from the world.
    Re-casting the same public ability while its split session is active evaluates
    `reactivation_behavior`; `reform_owner` despawns surviving members and restores the stored owner
    at either the current active member's position or the original position with the authored HP
    policy.
21. **Group elimination is explicit.** If the active member dies, the runtime selects the next
    surviving member in authored order before the next Stage 1 boundary. If all members are gone,
    `kill_owner` discards the stored owner snapshot and resolves ordinary terminal death for the
    original owner. This keeps Spirit Split style reform/true-death behavior deterministic without
    introducing dual authority or off-world entity state.

### 4.16 Corpse Registry, Revive, and Downed-Phase Recovery

The `CG-13` surface splits into four supported compiler/runtime contracts today:

1. terminal-death corpse records used as local spatial resources; and
2. non-terminal intermediate life phases (for example `downed`) that return to Active through
   ordinary Stage 10 phase transitions; and
3. non-terminal ghost phases that delay terminal death, remain locally active for limited
   allied-beneficial casting, and convert their linger duration into Meta respawn-delay credit on
   true death; and
4. bounded post-terminal rebirth anchors that reroute one death's spawn location/timer while the
   anchor remains alive.

The engine/runtime MUST enforce the following rules:

1. **Corpse records are created only on terminal death.** When Stage 10 reaches terminal death for
   an entity type with `corpse_profile`, the runtime creates one bounded corpse-registry entry
   containing the source entity ID, death position, expiry tick, and any optional retained
   effective-stat/loadout snapshot authored by the corpse profile. Intermediate `P-25` phase
   transitions such as `downed` do not create corpse records.
2. **`P-47` is local to the death Arbiter under the current profile.** Corpse queries,
   `consume_corpse`, `revive_corpse`, and `LoadoutSource = { corpse_snapshot: ... }` resolve only
   against the CURRENT Arbiter's authoritative corpse registry. Remote/Ghost corpse access fails
   cleanly at resolution; the compiler/runtime does not relay corpse claims or revival across
   Arbiters in the current canonical profile.
3. **Corpse consumption is atomic before child effects execute.** When `consume_corpse` runs, it
   materializes the candidate corpse set from the authored target/query, sorts by `(distance,
   corpse_id)`, and then atomically claims each selected corpse before running child effects for
   that corpse. A corpse can therefore feed at most one successful consuming branch, and later
   contenders fail without partially applying child payloads.
4. **Corpse-derived bindings are immutable snapshots for that effect execution.** `bind_position_as`
   exposes the corpse death position. `bind_stats` reads the retained effective-stat snapshot when
   available. `corpse_snapshot` in `swap_identity` reads the retained projected loadout/appearance
   snapshot from the corpse record, not a live pointer into the dead entity.
5. **`revive_corpse` is a Stage 10 re-materialization path, not Meta respawn override.**
   `revive_corpse` restores the corpse's source entity to lifecycle phase 0 (Active) at the stored
   death position with the authored HP/cooldown/status reset policy, then optionally clears the
   corpse record. If the source entity already had a pending Meta respawn timer, the runtime emits
   `PlayerResurrected` after the revive commits so Meta cancels that timer.
6. **`downed_state` is ordinary `P-25`, not post-death special casing.** While an entity occupies a
   non-zero intermediate phase, the engine routes damage to `phase_hp`, the adapter exposes the
   phase-specific ability set and movement/capability overrides on the next tick, and the entity is
   still alive for targeting/filter purposes unless a filter explicitly asks for `*_downed`.
7. **Rally, finish, and self-rally are deterministic Stage 10 outcomes.** Ally rally lowers to
   `restore_phase`; enemy finish is an authored terminal kill / execute path against a downed
   target. If `self_rally_on_kill = true` and a downed entity is credited with at least one
   terminal kill during the current tick, the runtime schedules one `restore_phase` return to
   Active at the authored `rally_hp_ratio` after the victim death has committed. Multiple same-tick
   qualifying kills do not stack multiple restores.
8. **`ghost_phase` is ordinary `P-25`, not post-terminal persistence.** On lethal HP, the runtime
   transitions the entity into a non-zero intermediate phase instead of emitting `PlayerDied`.
   The next tick exposes the authored `ghost_ability_set`, enforces the generated capability
   restrictions (`CAN_MOVE = false`, `CAN_ATTACK = false`, `CAN_USE_ITEMS = false`,
   `PASSIVES_ACTIVE = false`), and applies the generated targetability/pathing-denial overlay so the
   ghost remains visible for observer/vision purposes without being targetable, hittable by AoE, or
   blocking movement. If `clear_statuses_on_enter = true`, the same Stage 10 batch also applies a
   generated all-polarity cleanse before ghost casting begins.
9. **Ghost expiry is the terminal death boundary.** When `ghost_duration_ticks` expires, Stage 10
   commits terminal death, emits `PlayerDied`, and includes the authored
   `respawn_delay_credit_ticks`. Meta subtracts that credit from the resolved base respawn delay,
   clamped at zero. Kill credit, death-triggered objectives, and other `PlayerDied` consumers
   therefore fire only when the ghost phase ends, not when HP first reaches zero.
10. **`spawn_actor.respawn_anchor` is the narrow supported post-terminal route override.** When a
    live rebirth anchor is registered for the terminally dying entity, Stage 10 emits
    `PlayerDied { ..., respawn_override = Some(RespawnAnchor { anchor_entity_id, position,
    respawn_delay_ticks }) }`. Meta records both the ordinary base respawn schedule and the shorter
    anchor schedule. If the anchor is removed before the respawn commits, the current anchor owner
    emits `RespawnOverrideRevoked`; Meta then falls back to the stored base schedule measured from
    the original death time. When the anchor schedule expires, Meta injects `SpawnEntity` with
    `respawn_context = Some(RespawnSpawnContext::RespawnAnchor { anchor_entity_id })`, and the
    target Arbiter validates/consumes the anchor atomically before materializing the player.
11. **Broader post-terminal respawn policy replacement remains outside the current profile.** The
    runtime still does NOT support arbitrary post-terminal respawn-state rewrites such as custom
    HP/resource reset policy, arbitrary cooldown reset policy, or free-form non-anchor route
    selection. Those remain Meta/game-mode concerns unless later promoted canonically.

### 4.17 Group Interaction Sessions and Choice Aggregation

The `CG-15` surface lowers into one shared `P-54` contract for group-wide sequential combos and
simultaneous choice windows without introducing a second client-input plane.

1. **`group_interaction` opens a bounded session only after the opening ability commits.** The
   runtime snapshots the participant set from the authored `party` or `raid_subgroup` scope,
   records the deadline tick, and assigns one Arbiter as the session owner. Stage 12 then includes
   that session's UI payload for every participant through `P-54`.
2. **Sequential sessions are advanced by ordinary ability casts, not bespoke combo messages.**
   When any participant successfully admits an ability cast at Stage 2, the session owner checks the
   participant's `group_role_id` plus the ability's `group_interaction_tags` against the current
   step. A matching cast advances the session immediately, records the contributor, and starts the
   next step's deadline. If a step times out, `failure_result` resolves if authored; otherwise the
   session fails cleanly with no further effect.
3. **Simultaneous sessions use compiler-generated temporary option abilities.** The selection wheel
   does not require a new external intent kind. Instead, the runtime exposes one temporary public
   option ability per `simultaneous.options` entry to each participant while the session is active.
   Casting that option ability submits the participant's choice through the ordinary Stage 2 admit
   path. If `allow_reselection = true`, the latest admitted option before the deadline overwrites
   the earlier choice; otherwise later submissions are rejected.
4. **Cross-Arbiter participation relays contributions to the session owner.** If the participant
   lives on another Arbiter, that local owner validates the ordinary cast/selection first and then
   relays the contribution tuple `(session_id, participant_id, role/tag or option_id, tick)` to the
   session-owning Arbiter. Session deadlines remain deterministic because all Arbiters share the
   same authoritative tick.
5. **Pattern evaluation order is fixed.** In simultaneous mode, the session owner first checks
   `ordered_patterns` against the authored `participant_order` (`party_slot`, `raid_subgroup_slot`,
   or stable `entity_id` order). If no ordered pattern matches, it evaluates `count_patterns`
   against the completed/default-filled count distribution. Missing participants at deadline are
   filled with `default_option_id` before either pattern pass runs.
6. **Group results execute through ordinary effects with implicit participant bindings.**
   `GroupResultBlock.apply_to = all_participants` runs the authored `effects` list once per
   participant with implicit `participant` / `participant_position` bindings. Any damage/heal/buff
   still resolves on each participant's or target's authoritative owner using the ordinary relay
   rules; `trigger_owner` runs the result once on the opening ability's owner instead.
7. **One participant contributes at most one slot per session.** Sequential sessions record the
   participant that satisfied each step and do not allow the same admitted cast to satisfy multiple
   steps. Simultaneous sessions retain at most one current option per participant. This keeps the
   aggregator bounded and replayable.

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
| P-66 Status Effect Filter Mutation | StateUpdate | State |

Compiler-owned runtime-state ops (`WriteState`, `ClearState`, `AdvanceSequence`,
`ModifyChargePool`) are intentionally omitted from the primitive table above. They are IR-level
state mutations, not additions to the engine primitive catalog, but they still use the same stage
scheduler and deterministic ordering rules.

## 6. Cascade and Re-entrancy Rules

The most critical safety constraint in the IR is **preventing unbounded within-tick cascades**.

### 6.1 Deferred Execution Rule

The engine MUST enforce strict re-entry boundaries to prevent infinite cascades within a single tick. 

**PostDamage Hooks (Stage 9):**
Any combat event generated by a PostDamage hook (P-35, P-36, P-37, P-38, P-60) MUST be queued for the NEXT tick. It re-enters the pipeline at **Stage 7 (PreMitigation)**, skipping target/kinematic resolution because the target and source are already known.

**StateUpdate Timers (Stage 11):**
Stage 11 operations are classified into three behaviors:
1. **`in_place_state_update`**: Primitives like DR Tracker (P-41), Stacking Counters (P-42), Charge Pools (P-50), and Status Effect Filter Mutation (P-66), plus compiler-owned runtime-state ops scheduled for the same stage, mutate state directly during Stage 11. They emit no deferred events.
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

Compiler-owned `heal_mirror_ratio` events MUST likewise carry the originating `binding_id` and a
`link_mirror: true` marker. A generated heal mirror MUST NOT emit another heal mirror through that
same binding.

### 6.4 Propagation Generation Bound

Compiler-authored propagation and spread events MUST carry `chain_id`, `generation`,
`max_generations`, and any dedup/replay metadata required by their authored mode. Before scheduling
child generations, the engine MUST:

1. reject further child emission when `generation >= max_generations`
2. apply `entity_once_per_chain` filters before query truncation
3. sort query candidates deterministically by the authored query semantics plus stable entity ID
4. preserve the same `chain_id` on every relay, replay, and child status application

This keeps recursive trees finite even when they span multiple ticks and multiple Arbiters.

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

8. **Activation modes compile to hidden variants.** Each authored activation mode MUST lower to a
   compiler-generated hidden `AbilityIRBlock` plus one `ActivationModeIR` redirect entry on the
   public/root ability. The runtime MUST never evaluate more than one activation mode for a single
   cast.

9. **Hold-release abilities use existing input lanes.** The compiler MAY require a matching ability
   slot/button binding, but it MUST lower hold-release abilities onto the existing discrete-cast +
   continuous-button-state ingress model rather than inventing a new client intent shape.

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
    input_mode: Instant,
    activation_modes: [],
    instructions: [
        // 1. Target: is target valid?
        IRInstruction {
            op: Primitive(P-13),
            stage: TargetResolution,
            params: { filter: Enemy | Alive, entity: Target },
            guard: None,
        },
        // 2. Kinematic: displace target along arc to landing position
        IRInstruction {
            op: Primitive(P-02),
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
            op: Primitive(P-09),
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
            op: Primitive(P-15),
            stage: DamageResolution,
            params: { target: Target, amount: 150, type: Physical },
            guard: None,
        },
        // 5. Damage: AoE damage to nearby enemies
        IRInstruction {
            op: Primitive(P-15),
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
| `ability-primitives/` | Defines the 66 engine primitives this IR targets. Primitive instructions/directives use that catalog, while compiler-owned runtime-state ops remain an IR-layer construct. |
| `03-compiler-pipeline.md` | Describes the compilation phases that produce IR Blocks. This document defines the IR output format. |
| `04-game-image-format.md` | IR Blocks are stored in the game image's Ability IR Table section (§3, type 0x10). |
| `docs-core/04-1-game-adapter-contract.md` | The 12 pipeline stages defined here are the proposed expansion of the adapter hook taxonomy (Amendment B). |
| `docs-core/PRIMITIVE_IMPACT_ASSESSMENT.md` | This document is the concrete deliverable for Amendment B. |

---

*This specification is the compiler team's proposal for the engine's ability resolution pipeline. The 12 canonical pipeline stages should be reviewed and adopted into `docs-core/04-1-game-adapter-contract.md` as the normative hook taxonomy.*
