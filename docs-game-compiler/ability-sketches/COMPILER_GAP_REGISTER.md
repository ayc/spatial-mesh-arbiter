# Compiler Gap Register

> Historical / resolved as of 2026-04-05.
> All recorded compiler gap families are now resolved canonically. This file remains as the
> historical record of what was missing and how it was closed.

This register groups repeated compiler gaps discovered during the full sketch compatibility audit.

Use `COMPILER_COMPATIBILITY_CHECKLIST.md` to see **which sketches** mapped to each gap. Use this
file to see what was added canonically and where it landed.

## Status Legend

- `Resolved` — gap already closed in canonical compiler docs
- `Open` — unresolved compiler contract gap

There are no remaining `Open` entries in the current register.

## Resolved Baseline

### CG-00 — Status polarity, cleanse, and status-application immunity

- `Status:` Resolved
- `Primary sketches:` `SK-15 Purify`
- `What was missing:` A first-class way to classify statuses, cleanse them deterministically, and block new status admissions during immunity windows.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`, `ability-primitives/04-entity-state-capability.md`
- `Resolution type:` Added `cleanse`, `polarity`, `status_application_immunity`, `apply_cc.is_cleansable`, and `P-66 Status Effect Filter Mutation`

### CG-03 — Advanced CC lifecycle and target-control policy

- `Status:` Resolved
- `Primary sketches:` `SK-24`, `SK-25`, `SK-26`, `SK-27`, `SK-28`, `SK-50`, `SK-51`, `SK-65`, `SK-78`, `SK-101`, `SK-102`, `SK-106`, `SK-110`, `SK-118`
- `What was missing:` The compiler had baseline `apply_cc` coverage, but it did not canonically define duration scaling, CC-immunity authoring, break policies, miss-before-hit resolution, target override, hostility inversion, or the built-in behavior profiles behind the supported CC types.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added canonical `cc_type` behavior profiles, `duration_scaling`, `apply_cc.on_expire_effects`, `StatusEffectDefinition.cc_immunity_categories`, deterministic CC admission/enforcement ordering, and wire-level `cc_behavior_profile` / `cc_immunity_mask`.

### CG-07 — Reactivation, temporal memory, combo windows, and charge-state authoring

- `Status:` Resolved
- `Primary sketches:` `SK-35`, `SK-36`, `SK-37`, `SK-39`, `SK-41`, `SK-42`, `SK-52`, `SK-59`, `SK-79`, `SK-83`, `SK-84`, `SK-87`, `SK-116`
- `What was missing:` The compiler lacked a canonical way to express hold-release abilities, ordered same-key reactivation, bookmark/snapshot/sequence/charge runtime state, and status-owned next-cast / first-hit consumption windows.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `InputModeBlock`/`InputMode_Wire`, `ActivationModes` that redirect to hidden compiled variants, `RuntimeStateDefinition` plus a canonical runtime-state table/index, IR/runtime-state ops and state-payload refs, and status-owned `snapshot_recorder_state` / `consumption_window` metadata with `AbilityOverride` support.

### CG-16 — Special resolution policies for non-HP combat state

- `Status:` Resolved
- `Primary sketches:` `SK-21`, `SK-46`, `SK-47`, `SK-53`, `SK-73`, `SK-93`, `SK-97`, `SK-108`, `SK-109`, `SK-112`, `SK-114`, `SK-117`, `SK-119`
- `What was missing:` The primitive layer already covered block, deferred ledger, resource burn, movement-scaled damage, resolution bypass, desperation costs, stagger bars, and counter windows individually, but the compiler docs lacked explicit end-to-end authoring, validation, lowering, and wire contracts tying those mechanics together.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `ResourceCost.escalation`, `VulnerabilityWindowBlock`, `resource_burn`, `swap_hp_percent`, `execute`, `BlockDefenseDef`, status-owned `damage_accumulator` / `deferred_ledger` / `hp_floor` / `death_prevention` / `movement_damage`, shield lifecycle hooks with remaining-value bindings, and deterministic stage ordering for block, death-prevention, stagger depletion, and counter windows.

### CG-11 — Control topology, identity swap, and multi-owner loadout authoring

- `Status:` Resolved
- `Primary sketches:` `SK-07`, `SK-40`, `SK-57`, `SK-61`, `SK-66`, `SK-67`, `SK-68`, `SK-77`, `SK-81`, `SK-107`
- `What was missing:` The primitive taxonomy already covered control authority swap, input multiplexing, and identity/loadout swap, but the compiler docs lacked canonical authoring for persistent control topologies, temporary control overrides, named loadout profiles, and borrowed-slot projection.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `swap_identity`, `borrow_ability_slot`, `control_override`, `LoadoutProfileDef`, `ControlTopologyDef`, `ControlMemberDef`, `LoadoutSource`, Stage 1 routing-mutation / Stage 11 `P-31` lowering rules, wire-level loadout-profile and control-topology records, and procedural fallback symbols for identity/loadout/control projection.

### CG-02 — Channel, maintained-cast, and interruption lifecycle

- `Status:` Resolved
- `Primary sketches:` `SK-05`, `SK-18`, `SK-40`, `SK-63`, `SK-64`, `SK-122`, `SK-123`
- `What was missing:` Cast-time existed, but the compiler docs did not yet define one canonical lifecycle for visible cast state, mid-cast cancellation, per-tick channel execution, continuous steering input, concentration ownership, or deterministic teardown of maintained outputs.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `ChannelBlock` and `ConcentrationBlock`, visible cast-state publication for non-zero `cast_time`, per-tick channel execution cadence, continuous-input policies, deterministic channel break rules, concentration-slot ownership with default `P-55` checks, Stage 11 maintained-output teardown, and optional `ChannelPolicy_Wire` / `ConcentrationPolicy_Wire`.

### CG-01 — Cross-boundary relay matrix for target-side authority

- `Status:` Resolved
- `Primary sketches:` `SK-35 Blink Strike`, `SK-108 Mana Burn`
- `What was missing:` The compiler docs referenced Ghost-aware queries and target-side authoritative reads separately, but they did not yet state one canonical rule for when origin owners relay parameters, when destination/target owners recompute results, and how instant cross-boundary snaps preserve single authority.
- `Canonical destination:` `03-1-compiler-ir-specification.md`
- `Resolution type:` Added a consolidated authority matrix covering local execution, destination-based handoff for `Blink Strike`, target-owner `resource_burn`, and the general rule that Ghost data is advisory while authoritative owners recompute final state-dependent math.

### CG-04 — Persistent linkage, redirection, and event cloning authoring

- `Status:` Resolved
- `Primary sketches:` `SK-04`, `SK-19`, `SK-43`, `SK-66`, `SK-111`
- `What was missing:` The primitive layer already had linkage, redirection, and cloning concepts, but the compiler docs did not canonically define one bounded `link` authoring surface, one runtime binding record, break-distance timing, pre-mitigation redirect splitting, post-resolution heal mirroring, anti-recursive single-target replay, or remote origin/observer-anchor behavior.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added first-class `link` schema/validation, procedural `link_entities` fallback, a consolidated `P-34` runtime contract for break checks / redirect branches / heal mirroring / event cloning / origin anchors, and wire-format guidance that link policy lives in `P-34` directive payloads plus ordinary `P-20` / `P-60` param blocks.

### CG-08 — Recursive and bounded reactive propagation

- `Status:` Resolved
- `Primary sketches:` `SK-09`, `SK-10`, `SK-11`, `SK-12`, `SK-38`
- `What was missing:` The IR already had `reactive_depth`, but the compiler docs did not define one canonical authoring surface for multi-generation bounce/fan-out/replay behavior, per-chain dedup, repeat-cast snapshots, or autonomous status spread carrying stable chain metadata across relays.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`
- `Resolution type:` Added `PropagationBlock` on triggers, `SpreadBlock` on statuses, and one shared compiler/runtime contract for `chain_id`, generation bounds, deterministic chance/effect scaling, root-seeded visited sets, same-snapshot repeat casts, and carrier-owned spread queries.

### CG-10 — Visibility, targetability overrides, dormancy, and suspension authoring

- `Status:` Resolved
- `Primary sketches:` `SK-32`, `SK-44`, `SK-58`, `SK-86`, `SK-91`, `SK-100`, `SK-104`
- `What was missing:` The compiler docs already referenced `P-27`, `P-33`, `P-52`, and `P-53`, but they did not yet define one canonical authoring surface for relation-scoped targetability, team-scoped observer presentation, or bounded suspension/stasis behavior with timer pausing and Ghost-side admission filtering.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added shared `TargetabilityPolicyBlock`, `ObserverPresentationBlock`, and `SuspensionBlock` surfaces on entities/statuses, plus one runtime contract for relation-scoped query admission, downstream-only deception, suspension modes, timer-pause semantics, and Ghost-visible targeting bits.

### CG-14 — Advanced projectile lifecycle mutation

- `Status:` Resolved
- `Primary sketches:` `SK-39`, `SK-55`, `SK-56`, `SK-62`, `SK-71`, `SK-80`, `SK-82`
- `What was missing:` Basic projectile archetypes already covered speed, homing, pierce, and simple detonation, but the compiler docs did not yet surface one canonical authoring/lowering contract for travel-based mutation, outbound-to-return phase changes, wall-bounce counters, delayed attachment detonation, entity-as-projectile collision overlays, or bounded projectile interception/return.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `spawn_actor.output_binding`, `displacement.flight_policy`, projectile travel scalars / return / bounce / attachment blocks, status-owned `projectile_intercept`, one shared IR/runtime contract for handoff-stable projectile phase state and redirect generations, and matching wire subrecords for advanced projectile policy.

### CG-05 — Zone actor lifecycle variants

- `Status:` Resolved
- `Primary sketches:` `SK-29`, `SK-31`, `SK-33`, `SK-59`, `SK-75`, `SK-99`, `SK-104`
- `What was missing:` Stationary zone basics already existed, but the compiler docs did not yet define one canonical contract for moving/attached/tracking zones, occupant-set diffs, pulse-conditioned persistence, continuous radial force, live zone output bindings, or zone-conditioned hostile admission based on current membership.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `ZoneMobilityBlock`, `ZonePersistenceBlock`, `ZoneForceBlock`, `zone.output_binding`, status-owned `zone_relation_gate`, one shared IR/runtime contract for moving-zone membership and force evaluation, and wire-format guidance that zone lifecycle policy stays in ability param data while relation gates serialize as status subrecords.

### CG-06 — Dynamic geometry, collision injection, and sweep-volume authoring

- `Status:` Resolved
- `Primary sketches:` `SK-03`, `SK-30`, `SK-34`, `SK-74`, `SK-76`, `SK-88`, `SK-90`
- `What was missing:` The primitive taxonomy already covered temporary walls, recorded trails, sweep volumes, and clamp-style movement bounds, but the compiler docs did not yet define one canonical authoring/lowering contract for injected geometry, polyline corridors, body-based sweeps, capture-first carry, orbit-derived sweeps, or bookmark-driven movement constraints.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `inject_geometry`, `polyline_zone`, `kinematic_sweep`, status-owned `movement_constraint`, one shared IR/runtime contract for segment-as-`P-57` lowering, committed-position polyline sampling, capture-first temporary attachment, orbit-state sweep dedup, and wire-level `MovementConstraintDef_Wire` support.

### CG-17 — Mesh-wide/controller-mediated execution

- `Status:` Resolved
- `Primary sketches:` `SK-05 Global Strike`
- `What was missing:` The primitive layer already implied controller-mediated global execution through `P-46`, but the compiler docs did not yet expose a canonical authoring surface for scheduling the event, defining the mesh-wide target selector/geometry, or stating when offense is baked versus when target-owner defense is resolved.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `global_event`, `schedule_global_event`, one shared IR/runtime contract for post-commit controller scheduling and execute-time local target admission, and `GlobalEventPolicy_Wire` for serialized lead/pulse/class policy.

### CG-15 — Group aggregator and cooperative-input authoring

- `Status:` Resolved
- `Primary sketches:` `SK-124`, `SK-125`
- `What was missing:` The primitive layer already had `P-54`, but the compiler docs did not yet define one canonical authoring/lowering contract for sequential role/tag combo chains, simultaneous option windows, ordered/count-based pattern evaluation, participant-scoped result execution, or group UI sessions without inventing a second input plane.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `group_interaction`, sequential/simultaneous session blocks, participant role/tag metadata, implicit `participant` result bindings, and one shared IR/runtime contract for ordinary-cast contributions, compiler-generated option abilities, ordered/count pattern resolution, and `P-54` Stage 12 group UI payloads.

### CG-09 — Spawned actor behavior, summon AI, and pickup/structure lifecycle

- `Status:` Resolved
- `Primary sketches:` `SK-06`, `SK-32`, `SK-61`, `SK-67`, `SK-76`, `SK-81`, `SK-94`
- `What was missing:` The compiler first lacked one bounded spawned-actor surface for autonomy, proximity interaction, coverage fields, per-owner live-count policy, clone-shell loadout projection, remote-control routing, and finally multi-member split/reform groups.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added `spawn_actor.autonomy`, `interaction`, `coverage`, `instance_limit`, `loadout_projection`, `control_projection`, and finally `split_form` plus `cycle_split_form`, yielding one shared runtime contract for single-actor and split-form spawned projections without new engine primitives beyond existing `P-30` coordinator rules.

### CG-12 — Containment, vehicle, portal, and instance topology

- `Status:` Resolved
- `Primary sketches:` `SK-54`, `SK-60`, `SK-69`, `SK-72`, `SK-98`, `SK-105`
- `What was missing:` The compiler initially only had static bunker/portal metadata plus local instance forking. The remaining missing pieces were devour-style off-world carried occupants and cross-Arbiter member admission into a single-host `P-56` arena.
- `Canonical destination:` `docs-core/01-4-dynamic-topology-contract.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Extended `P-58` with `occupant_storage_mode = off_world_stored` and extended `P-56` with controller-coordinated remote admission before instance start, while keeping live containers and live instances single-owner / single-host after creation.

### CG-13 — Post-terminal respawn-route override

- `Status:` Resolved
- `Primary sketches:` `SK-89`
- `What was missing:` Canonical compiler docs already covered corpse-targeted revive, corpse consumption, corpse-derived loadout projection, downed/rally flows, and pre-terminal ghost phases with respawn-delay credit, but they still lacked one bounded post-terminal route override that remained revocable after `PlayerDied`.
- `Canonical destination:` `docs-core/04-1-game-adapter-contract.md`, `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md`, `docs/2-contracts-and-interfaces/internal-mesh-types/04-hard-state-events.md`, `docs/1-architecture/04-meta-services.md`, `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`
- `Resolution type:` Added `spawn_actor.respawn_anchor`, `PlayerDied.respawn_override`, `HardEvent::RespawnOverrideRevoked`, and `MetaCommand::SpawnEntity.respawn_context`, yielding one narrow revocable rebirth-anchor contract: Meta stores both base and override respawn schedules, anchor destruction revokes the override, and the target Arbiter validates/consumes the anchor atomically on respawn commit.

### CG-18 — Field-targeted combo and live-zone transformation context

- `Status:` Resolved
- `Primary sketches:` `SK-59`
- `What was missing:` The compiler now has `combo_field_type`, `combo_finisher`, and a game-data
  `combo_matrix`, but it still does not expose one canonical effect context for "the field actor
  that was just comboed" or a shared field-transform path that can replace one live zone/field with
  another. That leaves external oil-ignite style interactions only loosely implied.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`,
  `ability-primitives/11-systemic-interactions.md`
- `Resolution type:` Added combo-result callback refs (`combo_field_entity`,
  `combo_field_owner`, `combo_field_position`, `finisher_position`), widened `combo_matrix` rows to
  carry an `EffectList`, added declarative `despawn_entity`, added `zone.owner`, and explicitly
  documented deterministic field replacement through ordinary authored effect sequencing.

### CG-19 — Spawned-actor detonation and teardown callbacks for controlled shells

- `Status:` Resolved
- `Primary sketches:` `SK-81`
- `What was missing:` The compiler now covers single-actor `control_projection`, but it still does
  not expose one declarative lifecycle surface for manual detonate, on-expire detonate, or
  controller-break follow-up against a controlled spawned actor. The Lua fallback surface already
  has `despawn_entity`, but the canonical declarative compiler layer does not.
- `Canonical destination:` `01-2-lua-whitelisted-api.md`, `02-schema-and-validation.md`,
  `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Resolution type:` Added canonical declarative `despawn_entity`, added
  `control_projection.manual_trigger_effects`, `on_expire_effects`, and
  `on_controller_break_effects`, documented the projected-actor callback context plus generated
  same-slot manual trigger semantics, and aligned the Lua helper / game-image docs with that bounded
  teardown model.

### CG-20 — Spawned-actor directed transit to an authored destination

- `Status:` Resolved
- `Primary sketches:` `SK-98`
- `What was missing:` The compiler now canonically covers carried occupants (`P-58`) and spawned
  actor ownership/containment, but it still does not define a canonical way to tell a spawned actor
  "travel toward this authored destination at this speed, remain attackable in transit, and emit
  arrival effects when you get there." Existing spawned-actor surfaces cover autonomy
  follow/acquire/attack loops, portal anchors, and control projection, but not destination-bound
  transport flight.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`,
  `04-game-image-format.md`
- `Resolution type:` Added canonical `start_actor_transit` with late-bound destination, fixed-speed
  transit, arrival-radius commit, and arrival callback context (`transit_actor`,
  `transit_actor_position`). Mid-flight destruction remains authored through ordinary actor
  `on_death` / container exit cleanup rather than a second transit-failure subsystem.

### CG-21 — Projectile-side multi-target carry / rolling capture state

- `Status:` Resolved
- `Primary sketches:` `SK-55`
- `What was missing:` The compiler already supported projectile radius growth, payload scaling,
  wall detonation, and entity-as-projectile flight overlays, but it still lacked one bounded way
  for a single projectile actor to accumulate multiple collided targets as carried runtime state and
  transport them forward until wall impact or expiry.
- `Canonical destination:` `docs-core/01-1-spatial-primitive-catalog.md`,
  `docs/1-architecture/01-core-concepts-and-mesh.md`,
  `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md`,
  `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md`,
  `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`,
  `04-game-image-format.md`
- `Resolution type:` Added canonical `ProjectileCarryBlock`, documented projectile-local ordered
  carried-target rosters plus release rules, kept `P-06` entity-only, and extended projectile
  snapshot/runtime state so handoff transfers the carry roster while the carried entities
  themselves still use ordinary co-located entity handoff.

### CG-22 — Shield-absorb callbacks and decaying offense-backed energy loops

- `Status:` Resolved
- `Primary sketches:` `SK-70`
- `What was missing:` The compiler supported shield break/expiry callbacks, resource pools, charge
  pools, and ordinary stat layering, but it did not yet define one bounded way to react to each
  authoritative absorbed-damage amount on a shield and route that value into a live decaying
  offensive bonus for another entity. The sketch needed both the shield-side callback and a
  canonical "current stored energy affects present offense" contract.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`,
  `04-game-image-format.md`, `01-2-lua-whitelisted-api.md`
- `Resolution type:` Added `apply_shield.bind_absorbed_value_as` plus `on_absorb_effects`,
  canonical `modify_resource`, and status-owned `resource_stat_links`, yielding one bounded path
  for per-absorb shield credit, live resource decay, and present-tense offense scaling without a
  bespoke Energy subsystem.

## Open Gaps

None currently.
