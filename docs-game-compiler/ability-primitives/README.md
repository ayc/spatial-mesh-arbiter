# Ability Primitive Taxonomy

**Status:** Canonical
**Origin:** Adapted from `GEMINI_PRIMITIVES_PROPOSAL.md` (62 primitives derived from SK-01 through SK-107), extended with 3 primitives covering SK-108 through SK-125, plus P-66 to close status-effect cleanse/dispel semantics.
**Purpose:** Define the atomic "Virtual Instruction Set for Spatial Logic." The Game Compiler lowers designer-authored abilities into chains of these 66 primitives. The engine exposes them; it never hardcodes individual abilities.

---

## Numbering Scheme

Primitives are numbered **P-01** through **P-66** and grouped into 11 categories. Numbers are stable — retired primitives leave a gap rather than renumbering.

## Category Index

| File | Category | Primitives |
|------|----------|------------|
| [01-spatial-kinematic.md](01-spatial-kinematic.md) | Spatial & Kinematic | P-01 through P-08 |
| [02-targeting-query.md](02-targeting-query.md) | Targeting & Query | P-09 through P-14 |
| [03-combat-resolution.md](03-combat-resolution.md) | Combat Resolution | P-15 through P-25 |
| [04-entity-state-capability.md](04-entity-state-capability.md) | Entity State & Capability | P-26 through P-34, P-66 |
| [05-hooks-reactive-triggers.md](05-hooks-reactive-triggers.md) | Hooks & Reactive Triggers | P-35 through P-40 |
| [06-temporal-accumulator.md](06-temporal-accumulator.md) | Temporal & Accumulator | P-41 through P-46 |
| [07-resource-economy.md](07-resource-economy.md) | Resource & Economy | P-47 through P-51 |
| [08-visibility-ui.md](08-visibility-ui.md) | Visibility & UI | P-52 through P-55 |
| [09-spatial-instance.md](09-spatial-instance.md) | Spatial & Instance Manipulation | P-56 through P-59 |
| [10-advanced-resolution.md](10-advanced-resolution.md) | Advanced Resolution | P-60 through P-62 |
| [11-systemic-interactions.md](11-systemic-interactions.md) | Systemic Interactions | P-63 through P-65 |

## Composition Rules

1. **Every ability is a chain of primitives.** No primitive is an ability by itself. Even "Blink" (a teleport) is `P-01 (Instant Translation)` — a single-primitive chain.
2. **Chains are ordered.** The compiler emits primitives in resolution order: targeting first, then state checks, then combat resolution, then hooks.
3. **Primitives are orthogonal.** Each primitive does exactly one thing. If two primitives overlap in function, one should be removed or the boundary clarified.
4. **Dependencies are explicit.** Some primitives require others (e.g., P-14 Continuous Proximity Monitor depends on P-09 Shape Overlap Query). Dependencies are listed per-primitive.
5. **Engine layer is declared.** Each primitive states whether it lives in `docs-core/` (engine contract), `game-adapter` (game-specific adapter hook), or `compiler-only` (resolved entirely at compile time).

## Sketch-to-Primitive Composition Table

Every ability sketch decomposed into its primitive chain. Chains are ordered by resolution sequence. P-15 (Value Modification) is omitted where damage/heal is an obvious downstream effect — it is implied unless the sketch's core identity IS the value application.

| Sketch | Name | Primitive Chain |
|--------|------|-----------------|
| SK-01 | Toss | P-02 (Forced Displacement) → P-09 (Shape Overlap Query) |
| SK-02 | Poison Shot | P-32 (Actor Spawning) → P-35 (On-Hit Hook) → P-44 (Pulse Timer) |
| SK-03 | Terrain Wall | P-08 (Dynamic Collision Injection) → P-45 (Delay Timer) |
| SK-04 | Tether | P-34 (Persistent Linkage) → P-04 (Positional Clamping) |
| SK-05 | Global Strike | P-43 (Charge-Up State) → P-46 (Global Event Scheduler) |
| SK-06 | Summon Swarm | P-32 (Actor Spawning) |
| SK-07 | Ability Steal | P-40 (On-Cast Intercept) → P-31 (Identity/Loadout Swap) |
| SK-08 | Aura | P-06 (Attached Kinematics) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer) → P-16 (Stat Layering) |
| SK-09 | Chain Lightning | P-32 (Actor Spawning) → P-11 (N-Nearest Neighbor) → P-35 (On-Hit Hook) |
| SK-10 | Crit Explosion | P-37 (On-Crit Hook) → P-09 (Shape Overlap Query) |
| SK-11 | On-Kill Cascade | P-39 (On-Death Hook) → P-09 (Shape Overlap Query) |
| SK-12 | Spell Echo | P-40 (On-Cast Intercept) → P-45 (Delay Timer) |
| SK-13 | Counter Strike | P-12 (Facing/Dot-Product Check) → P-38 (On-Block/Defend Hook) |
| SK-14 | Execute Threshold | P-17 (Conditional Thresholds) |
| SK-15 | Purify | P-66 (Status Effect Filter Mutation) |
| SK-16 | Holy Ground | P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer) → P-15 (Value Modification) |
| SK-17 | Sacrifice Shield | P-18 (Absorption Barrier) → P-21 (Value Conversion) |
| SK-18 | Resurrect | P-43 (Charge-Up State) → P-39 (On-Death Hook) |
| SK-19 | Guardian Angel | P-34 (Persistent Linkage) → P-20 (Damage Redirection) |
| SK-20 | Battle Cry | P-09 (Shape Overlap Query) → P-16 (Stat Layering) |
| SK-21 | Block | P-38 (On-Block/Defend Hook) |
| SK-22 | Damage Reflection | P-36 (On-Damage-Received Hook) |
| SK-23 | Thorns Aura | P-36 (On-Damage-Received Hook) |
| SK-24 | Stun | P-26 (Capability Bitmask) → P-41 (DR Tracker) |
| SK-25 | Root | P-26 (Capability Bitmask) → P-41 (DR Tracker) |
| SK-26 | Silence | P-26 (Capability Bitmask) → P-41 (DR Tracker) |
| SK-27 | Sleep | P-26 (Capability Bitmask) → P-36 (On-Damage-Received Hook) |
| SK-28 | Slow + Diminishing Returns | P-16 (Stat Layering) → P-41 (DR Tracker) |
| SK-29 | Blizzard | P-32 (Actor Spawning) → P-09 (Shape Overlap Query) → P-44 (Pulse Timer) |
| SK-30 | Trail of Fire | P-57 (Polyline Collision Generator) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer) |
| SK-31 | Vortex | P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-02 (Forced Displacement) |
| SK-32 | Minefield | P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-52 (Asymmetric Team-Rendering) |
| SK-33 | Shifting Sands | P-32 (Actor Spawning) → P-03 (Trajectory Steering) → P-44 (Pulse Timer) |
| SK-34 | Charge | P-07 (Entity-as-Kinematic-Volume) → P-02 (Forced Displacement) |
| SK-35 | Blink Strike | P-01 (Instant Translation) |
| SK-36 | Shadow Step | P-01 (Instant Translation) → P-05 (Historical State Buffer) |
| SK-37 | Time Rewind | P-05 (Historical State Buffer) → P-01 (Instant Translation) |
| SK-38 | Contagion | P-44 (Pulse Timer) → P-09 (Shape Overlap Query) → P-35 (On-Hit Hook) |
| SK-39 | Spectral Dash | P-07 (Entity-as-Kinematic-Volume) → P-27 (Targetability Overrides) |
| SK-40 | Mind Control | P-29 (Control Authority Swap) → P-26 (Capability Bitmask) → P-45 (Delay Timer) |
| SK-41 | Detonation Arrow | P-32 (Actor Spawning) → P-45 (Delay Timer) → P-09 (Shape Overlap Query) |
| SK-42 | Withering Fire | P-42 (Stacking Counters w/ Decay) → P-11 (N-Nearest Neighbor) |
| SK-43 | Drag | P-02 (Forced Displacement) → P-34 (Persistent Linkage) |
| SK-44 | Burrow | P-27 (Targetability Overrides) → P-33 (Entity Dormancy) |
| SK-45 | Essence Collection | P-14 (Continuous Proximity Monitor) → P-47 (Spatial Corpse Registry) |
| SK-46 | Adaptation | P-36 (On-Damage-Received Hook) → P-42 (Stacking Counters w/ Decay) → P-16 (Stat Layering) |
| SK-47 | Shield Burst | P-18 (Absorption Barrier) → P-09 (Shape Overlap Query) |
| SK-48 | Death Coil | P-17 (Conditional Thresholds) → P-21 (Value Conversion) |
| SK-49 | Cone Strike | P-09 (Shape Overlap Query) → P-12 (Facing/Dot-Product Check) |
| SK-50 | Blind | P-26 (Capability Bitmask) |
| SK-51 | Unstoppable | P-62 (Categorized CC Immunity) |
| SK-52 | Combo Strike | P-42 (Stacking Counters w/ Decay) |
| SK-53 | HP Swap | P-17 (Conditional Thresholds) → P-15 (Value Modification) |
| SK-54 | Entity Consumption | P-33 (Entity Dormancy) → P-47 (Spatial Corpse Registry) |
| SK-55 | Growing Projectile | P-32 (Actor Spawning) → P-09 (Shape Overlap Query) |
| SK-56 | Knockback Projectile | P-32 (Actor Spawning) → P-02 (Forced Displacement) |
| SK-57 | Form Transformation | P-31 (Identity/Loadout Swap) → P-16 (Stat Layering) |
| SK-58 | Cocoon | P-53 (Entity Suspension) → P-33 (Entity Dormancy) |
| SK-59 | Oil-Ignite | P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) → P-64 (Combo Field × Finisher Matrix) |
| SK-60 | Bunker | P-32 (Actor Spawning) → P-58 (Container/Vehicle Logic) → P-20 (Damage Redirection) |
| SK-61 | Spirit Split | P-32 (Actor Spawning) → P-56 (Spatial Instance Forking) → P-30 (Input Multiplexing) |
| SK-62 | Boomerang | P-32 (Actor Spawning) → P-03 (Trajectory Steering) → P-35 (On-Hit Hook) |
| SK-63 | Steerable Beam | P-10 (Swept-Segment Raycast) → P-03 (Trajectory Steering) → P-44 (Pulse Timer) |
| SK-64 | Mosh Pit | P-09 (Shape Overlap Query) → P-26 (Capability Bitmask) → P-14 (Continuous Proximity Monitor) |
| SK-65 | Taunt | P-03 (Trajectory Steering) → P-26 (Capability Bitmask) |
| SK-66 | Symbiote | P-06 (Attached Kinematics) → P-34 (Persistent Linkage) → P-60 (Event Cloning) |
| SK-67 | Entity Clone | P-32 (Actor Spawning) → P-31 (Identity/Loadout Swap) |
| SK-68 | Multi-Entity Control | P-30 (Input Multiplexing) → P-32 (Actor Spawning) |
| SK-69 | Portal Pair | P-32 (Actor Spawning) → P-59 (N-Way Portal Network) → P-01 (Instant Translation) |
| SK-70 | Energy Shield | P-18 (Absorption Barrier) → P-21 (Value Conversion) → P-16 (Stat Layering) |
| SK-71 | Sticky Bomb | P-06 (Attached Kinematics) → P-45 (Delay Timer) → P-09 (Shape Overlap Query) |
| SK-72 | Nydus Network | P-32 (Actor Spawning) → P-59 (N-Way Portal Network) → P-01 (Instant Translation) |
| SK-73 | Death Immunity | P-23 (Floor Clamping) → P-45 (Delay Timer) |
| SK-74 | Hit-Confirmed Dash | P-07 (Entity-as-Kinematic-Volume) → P-17 (Conditional Thresholds) → P-01 (Instant Translation) |
| SK-75 | Self-Sustaining Zone | P-32 (Actor Spawning) → P-44 (Pulse Timer) → P-09 (Shape Overlap Query) → P-17 (Conditional Thresholds) |
| SK-76 | Build Zone | P-08 (Dynamic Collision Injection) → P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) |
| SK-77 | Two-Player Entity | P-30 (Input Multiplexing) → P-31 (Identity/Loadout Swap) |
| SK-78 | Fear | P-03 (Trajectory Steering) → P-26 (Capability Bitmask) |
| SK-79 | Charge-Up Shot | P-43 (Charge-Up State) → P-32 (Actor Spawning) |
| SK-80 | Wall Bounce | P-32 (Actor Spawning) → P-10 (Swept-Segment Raycast) |
| SK-81 | Remote Control Summon | P-32 (Actor Spawning) → P-29 (Control Authority Swap) |
| SK-82 | Projectile Deflect | P-61 (Projectile Ownership Hijacking) → P-03 (Trajectory Steering) |
| SK-83 | Next-Cast Empowerment | P-16 (Stat Layering) → P-40 (On-Cast Intercept) |
| SK-84 | Temporal Trap | P-32 (Actor Spawning) → P-45 (Delay Timer) → P-05 (Historical State Buffer) → P-01 (Instant Translation) |
| SK-85 | Ring Geometry | P-09 (Shape Overlap Query) → P-45 (Delay Timer) |
| SK-86 | Decoy | P-32 (Actor Spawning) → P-52 (Asymmetric Team-Rendering) → P-27 (Targetability Overrides) |
| SK-87 | Conditional Counter | P-36 (On-Damage-Received Hook) → P-17 (Conditional Thresholds) → P-09 (Shape Overlap Query) |
| SK-88 | Positional Leash | P-04 (Positional Clamping) → P-26 (Capability Bitmask) |
| SK-89 | Respawn Anchor | P-32 (Actor Spawning) → P-39 (On-Death Hook) → P-01 (Instant Translation) |
| SK-90 | Orbital Sweep | P-06 (Attached Kinematics) → P-07 (Entity-as-Kinematic-Volume) → P-09 (Shape Overlap Query) |
| SK-91 | Team-Agnostic Stasis | P-33 (Entity Dormancy) → P-27 (Targetability Overrides) → P-13 (Tag/Allegiance Filtering) |
| SK-92 | Anti-Heal | P-16 (Stat Layering) |
| SK-93 | Death Prevention | P-39 (On-Death Hook) → P-23 (Floor Clamping) → P-15 (Value Modification) |
| SK-94 | Placed Potion | P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) |
| SK-95 | Mass Effect Detonation | P-16 (Stat Layering) → P-09 (Shape Overlap Query) → P-64 (Combo Field × Finisher Matrix) |
| SK-96 | Death Ghost | P-39 (On-Death Hook) → P-32 (Actor Spawning) → P-45 (Delay Timer) |
| SK-97 | Escalating Cost | P-42 (Stacking Counters w/ Decay) → P-51 (Desperation Cost Modifiers) |
| SK-98 | Mobile Transport | P-32 (Actor Spawning) → P-58 (Container/Vehicle Logic) → P-06 (Attached Kinematics) |
| SK-99 | Target-Tracking Zone | P-32 (Actor Spawning) → P-06 (Attached Kinematics) → P-09 (Shape Overlap Query) → P-44 (Pulse Timer) |
| SK-100 | Ally Untargetable | P-27 (Targetability Overrides) → P-62 (Categorized CC Immunity) |
| SK-101 | Charm | P-03 (Trajectory Steering) → P-26 (Capability Bitmask) |
| SK-102 | Disarm | P-26 (Capability Bitmask) → P-41 (DR Tracker) |
| SK-103 | Facing-Dependent Effect | P-12 (Facing/Dot-Product Check) → P-17 (Conditional Thresholds) |
| SK-104 | Zone-Conditional Invuln. | P-14 (Continuous Proximity Monitor) → P-17 (Conditional Thresholds) → P-27 (Targetability Overrides) |
| SK-105 | Pocket Arena | P-56 (Spatial Instance Forking) → P-45 (Delay Timer) |
| SK-106 | Berserk | P-28 (Hostility Inversion) → P-03 (Trajectory Steering) → P-26 (Capability Bitmask) |
| SK-107 | Corpse Possession | P-47 (Spatial Corpse Registry) → P-31 (Identity/Loadout Swap) → P-45 (Delay Timer) |
| SK-108 | Mana Burn | P-35 (On-Hit Hook) → P-49 (Resource Destruction-to-Damage) |
| SK-109 | Movement Damage | P-63 (Movement-Damage Scalar) |
| SK-110 | Mute | P-26 (Capability Bitmask) |
| SK-111 | Soulbind | P-34 (Persistent Linkage) → P-60 (Event Cloning) |
| SK-112 | Deferred Resolution | P-22 (Deferred Ledger) |
| SK-113 | Hit-Count Shield | P-19 (Instance Barrier) |
| SK-114 | Piercing Execute | P-17 (Conditional Thresholds) → P-24 (Resolution Bypass) |
| SK-115 | Corpse Economy | P-39 (On-Death Hook) → P-47 (Spatial Corpse Registry) → P-11 (N-Nearest Neighbor) |
| SK-116 | Charge-Finisher | P-50 (Typed Multi-Charge Pool) → P-42 (Stacking Counters w/ Decay) |
| SK-117 | Stagger Bar | P-48 (Secondary Stagger Bar) → P-26 (Capability Bitmask) → P-16 (Stat Layering) |
| SK-118 | Partial CC Immunity | P-62 (Categorized CC Immunity) |
| SK-119 | Counter Window | P-65 (Vulnerability Window Broadcast) → P-40 (On-Cast Intercept) |
| SK-120 | Combo Field Matrix | P-14 (Continuous Proximity Monitor) → P-64 (Combo Field × Finisher Matrix) |
| SK-121 | Downed State | P-39 (On-Death Hook) → P-25 (Multi-Phase Vitals) → P-31 (Identity/Loadout Swap) → P-26 (Capability Bitmask) |
| SK-122 | Counterspell | P-40 (On-Cast Intercept) |
| SK-123 | Concentration | P-55 (Concentration Intercept) → P-36 (On-Damage-Received Hook) |
| SK-124 | Group Sequential Combo | P-54 (Group Choice Aggregator) → P-42 (Stacking Counters w/ Decay) |
| SK-125 | Group Simultaneous Input | P-54 (Group Choice Aggregator) |

## Primitive Coverage Summary

Every primitive (P-01 through P-66) is used by at least one sketch. The most-referenced primitives:

| Primitive | Count | Role |
|-----------|-------|------|
| P-32 (Actor Spawning) | 32 | Most abilities spawn a projectile, zone, or summon |
| P-09 (Shape Overlap Query) | 21 | Core AoE targeting |
| P-26 (Capability Bitmask) | 18 | Every CC type sets a flag |
| P-14 (Continuous Proximity Monitor) | 15 | Zone enter/leave triggers |
| P-45 (Delay Timer) | 12 | Delayed effects and expiry |
| P-01 (Instant Translation) | 12 | Teleport and reposition |
| P-16 (Stat Layering) | 11 | Buff/debuff modifiers |
| P-44 (Pulse Timer) | 11 | DoTs and periodic zone ticks |

Least-referenced (1 sketch each): P-19, P-22, P-24, P-25, P-28, P-46, P-48, P-49, P-51, P-55, P-57, P-63, P-65, P-66. These are specialized primitives — high-value for the sketches that need them, but narrow in applicability.

---

*Adopted from the Gemini primitives analysis. See `GEMINI_PRIMITIVES_PROPOSAL.md` for the original working draft.*
