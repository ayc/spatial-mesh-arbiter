# Compiler Gap Register

This register groups repeated compiler gaps discovered during the full sketch compatibility audit.

Use `COMPILER_COMPATIBILITY_CHECKLIST.md` to see **which sketches** map to each gap. Use this file to see **what needs to be added canonically** and where it should land.

## Status Legend

- `Resolved` — gap already closed in canonical compiler docs
- `Open` — unresolved compiler contract gap

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

## Open Gaps

### CG-01 — Cross-boundary relay matrix for target-side authority

- `Status:` Open
- `Primary sketches:` `SK-35 Blink Strike`, `SK-108 Mana Burn`
- `Missing surface area:` The compiler docs do not yet give one consolidated matrix for Ghost targets, target-side authoritative reads, instant cross-boundary snaps, and relay payload ownership for nonstandard effects.
- `Canonical destination:` `03-1-compiler-ir-specification.md`
- `Severity:` High
- `Recommended resolution:` Add a primitive/effect-to-authority matrix covering local execution, Ghost relay, target-side authoritative reads, and instant destination-based handoff.

### CG-02 — Channel, maintained-cast, and interruption lifecycle

- `Status:` Open
- `Primary sketches:` `SK-05`, `SK-18`, `SK-40`, `SK-63`, `SK-64`, `SK-122`, `SK-123`
- `Missing surface area:` Cast-time exists, but canonical docs do not yet define long-lived channel state, break conditions, interrupt ordering, maintained-effect teardown, or targetable mid-cast interception as a complete authoring/lowering contract.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Add an explicit channel/maintained-cast block with interruption policy, break conditions, and IR placement rules.

### CG-04 — Persistent linkage, redirection, and event cloning authoring

- `Status:` Open
- `Primary sketches:` `SK-04`, `SK-19`, `SK-43`, `SK-66`, `SK-111`
- `Missing surface area:` The primitive layer has linkage concepts, but there is no canonical schema for creating links, defining break conditions, redirecting damage/healing, or cloning single-target events across linked entities.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`
- `Severity:` High
- `Recommended resolution:` Add first-class link definitions and mirrored-event policy fields.

### CG-05 — Zone actor lifecycle variants

- `Status:` Open
- `Primary sketches:` `SK-29`, `SK-31`, `SK-33`, `SK-59`, `SK-75`, `SK-99`, `SK-104`
- `Missing surface area:` Stationary zone basics exist, but the docs do not fully define moving zones, tracking zones, sustain conditions, enter/leave cleanup policy, or continuous pull/force profiles.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`
- `Severity:` High
- `Recommended resolution:` Extend `zone` authoring to cover lifecycle variants, mobility modes, and membership/cleanup policy.

### CG-06 — Dynamic geometry, collision injection, and sweep-volume authoring

- `Status:` Open
- `Primary sketches:` `SK-03`, `SK-30`, `SK-34`, `SK-74`, `SK-76`, `SK-88`, `SK-90`
- `Missing surface area:` The primitive taxonomy covers walls, trails, and sweep volumes, but the compiler docs lack canonical authoring for dynamic geometry injection, polyline/path volumes, and collision-capturing sweeps.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Add geometry/collision authoring blocks with bounded shape rules and stage-placement semantics.

### CG-08 — Recursive and bounded reactive propagation

- `Status:` Open
- `Primary sketches:` `SK-09`, `SK-10`, `SK-11`, `SK-12`, `SK-38`
- `Missing surface area:` The IR spec has `reactive_depth`, but the compiler docs do not yet define a canonical authoring contract for bounded recursion, dedup keys, generation counters, repeated-cast envelopes, or termination validation.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`
- `Severity:` Medium
- `Recommended resolution:` Add explicit recursion-bounding fields for chain/spread/proc patterns and wire them to IR depth/next-hop state.

### CG-09 — Spawned actor behavior, summon AI, and pickup/structure lifecycle

- `Status:` Open
- `Primary sketches:` `SK-06`, `SK-32`, `SK-67`, `SK-76`, `SK-81`, `SK-94`
- `Missing surface area:` `spawn_actor` covers spawning, but not AI/state-machine behavior, pickup consumption, arming/activation state, or structure dependency graphs.
- `Canonical destination:` `02-schema-and-validation.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Add spawned-actor behavior blocks for AI, pickup, arming, and structure lifecycle policy.

### CG-10 — Visibility, targetability overrides, dormancy, and suspension authoring

- `Status:` Open
- `Primary sketches:` `SK-32`, `SK-44`, `SK-58`, `SK-86`, `SK-91`, `SK-100`, `SK-104`
- `Missing surface area:` The engine/IR mention observer-scoped output and dormancy, but there is no canonical compiler surface for stealth, reveal policy, targetability overrides, suspension, or observer exceptions.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Add explicit visibility and targetability policy blocks with observer-scope rules.

### CG-11 — Control topology, identity swap, and multi-owner loadout authoring

- `Status:` Open
- `Primary sketches:` `SK-07`, `SK-40`, `SK-57`, `SK-61`, `SK-66`, `SK-67`, `SK-68`, `SK-77`, `SK-81`, `SK-107`
- `Missing surface area:` The primitive taxonomy covers control authority swap, input multiplexing, and identity/loadout swap, but the compiler docs do not surface them as authorable mechanics.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Add canonical authoring for control ownership, borrowed loadouts, and multi-edge/multi-entity control topology.

### CG-12 — Containment, vehicle, portal, and instance topology

- `Status:` Open
- `Primary sketches:` `SK-54`, `SK-60`, `SK-61`, `SK-69`, `SK-72`, `SK-98`, `SK-105`
- `Missing surface area:` Portal networks, containers, vehicles, and instance forking exist as primitives, but not as a complete compiler contract.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`, `05-runtime-loading-and-activation.md`
- `Severity:` High
- `Recommended resolution:` Add transport/container/portal/instance authoring blocks plus topology ownership and teardown rules.

### CG-13 — Corpse, death-state, respawn, and possession flows

- `Status:` Open
- `Primary sketches:` `SK-18`, `SK-45`, `SK-89`, `SK-96`, `SK-107`, `SK-115`, `SK-121`
- `Missing surface area:` The docs have corpse filters and downed-state schema, but not a full compiler surface for corpse interactions, respawn anchors, death-spawned alternate forms, corpse economy, or corpse-targeted possession.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Add explicit corpse/death interaction authoring and lifecycle rules.

### CG-14 — Advanced projectile lifecycle mutation

- `Status:` Open
- `Primary sketches:` `SK-39`, `SK-55`, `SK-56`, `SK-62`, `SK-71`, `SK-80`, `SK-82`
- `Missing surface area:` Basic projectile archetypes exist, but the compiler docs do not yet surface bouncing, return-flight, growth, attached detonation, entity-as-projectile, or ownership hijack behavior.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Extend projectile authoring to cover lifecycle mutation and ownership changes.

### CG-15 — Group aggregator and cooperative-input authoring

- `Status:` Open
- `Primary sketches:` `SK-124`, `SK-125`
- `Missing surface area:` The primitive layer has group-choice aggregation, but the compiler docs do not define authoring for group sequence windows, simultaneous input windows, combination matrices, or per-member participation policy.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` Medium
- `Recommended resolution:` Add first-class group interaction schemas and matching observer/UI payload rules.

### CG-16 — Special resolution policies for non-HP combat state

- `Status:` Open
- `Primary sketches:` `SK-21`, `SK-46`, `SK-47`, `SK-53`, `SK-73`, `SK-93`, `SK-97`, `SK-108`, `SK-109`, `SK-112`, `SK-114`, `SK-117`, `SK-119`
- `Missing surface area:` The primitive layer and some metadata cover these concepts individually, but the compiler docs do not yet provide a complete end-to-end contract for block negation, deferred ledgers, resource burn, movement-scaled damage, resolution bypass, desperation costs, stagger integration, or vulnerability windows.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`, `04-game-image-format.md`
- `Severity:` High
- `Recommended resolution:` Promote these patterns from primitive-only coverage into explicit authoring and validation constructs.

### CG-17 — Mesh-wide/controller-mediated execution

- `Status:` Open
- `Primary sketches:` `SK-05 Global Strike`
- `Missing surface area:` The primitive taxonomy and engine docs imply controller-mediated global execution, but the compiler docs do not expose how authoring targets that path, how future-tick fan-out is represented, or how interruption interacts with scheduled mesh-wide effects.
- `Canonical destination:` `02-schema-and-validation.md`, `03-1-compiler-ir-specification.md`
- `Severity:` Medium
- `Recommended resolution:` Add a global-event authoring block and controller-escalation lowering contract.
