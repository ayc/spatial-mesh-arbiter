# Ability Sketch Completion Checklist

> Historical / closed as of 2026-04-05.
> All 125 sketches are now `Sketch-Complete`. This file remains as closure criteria plus
> historical completion log; it is no longer an active work queue.

This tracker defines what it means for an ability sketch to be "designer-recreatable with the compiler" rather than merely "decomposed into primitives."

It exists because the current sketch set already has broad primitive coverage, but many sketches still leave cross-boundary behavior and compiler output details as TODOs. Those gaps are the remaining blocker for using the sketches as reliable designer-facing references.

This file is the historical **closure tracker**. It is distinct from:

- `COMPILER_COMPATIBILITY_CHECKLIST.md` — per-sketch audit of whether the current compiler docs already support each sketch
- `COMPILER_GAP_REGISTER.md` — grouped backlog of missing canonical compiler contracts revealed by that audit

## Goal

For a sketch to count as complete, a game designer should be able to:

1. Understand the intended gameplay behavior.
2. See the canonical primitive chain that expresses it.
3. Know the cross-boundary/runtime contract required for the ability.
4. Know what authoring inputs the compiler accepts.
5. Know what compiler output / IR / validation shape the compiler must produce.

## Completion Criteria

Every sketch is complete only when all of the following are true:

1. `Primitive Composition` matches the canonical primitive taxonomy in `../ability-primitives/`.
2. `Observable Behavior` is concrete enough to define player-visible semantics without relying on TODO notes.
3. `Cross-Boundary Concerns` contains resolved behavior, not open TODOs.
4. `Compiler Requirements` states:
   - what the designer specifies
   - what the compiler emits
   - what the compiler validates or rejects
5. Any reusable rule discovered while closing the sketch is promoted into canonical compiler or contract docs instead of being left as sketch-local prose.
6. Open questions are either resolved or converted into explicit backlog items elsewhere. A completed sketch should not hide unresolved contract questions behind TODO markers.

## Working Statuses

Use these statuses when reviewing or updating sketches:

| Status | Meaning |
|---|---|
| `Primitive-Covered` | Sketch has a primitive chain, but still contains unresolved TODOs. |
| `Closure-In-Progress` | Cross-boundary and compiler sections are actively being resolved. |
| `Sketch-Complete` | Sketch satisfies the completion criteria above and has no remaining TODOs. |
| `Canonicalized` | Reusable outcomes from the sketch have been folded into the relevant compiler/core/docs contracts. |

Current baseline: all 125 sketches are now `Sketch-Complete`, and the closure queue is exhausted.
This file remains as the closure criteria reference plus the historical completion log.

## Resolution Workflow

Apply this sequence to each sketch:

1. Read the sketch and verify the primitive chain against `../ability-primitives/README.md`.
2. Resolve `Cross-Boundary Concerns` using authoritative engine contracts in `docs-core/`.
3. Resolve `Compiler Requirements` into:
   - designer-facing fields
   - emitted semantic IR / runtime artifacts
   - validation rules and compile-time errors
4. If the sketch exposes a recurring pattern, promote that rule into the canonical compiler docs (`01-*`, `02-*`, `03-*`, `04-*`, `05-*`) or the primitive catalog.
5. Remove TODOs from the sketch once the canonical destination exists.

## Prioritization Rule

Prioritize sketches using this order:

1. Common designer building blocks that many other abilities depend on.
2. Mechanics that force compiler-surface decisions not yet made canonically.
3. Mechanics that stress cross-boundary authority and therefore expose engine/compiler contract gaps.
4. Exotic or mode-specific mechanics after the baseline authoring surface is stable.

TODO count alone is not a sufficient priority signal. Reusable leverage matters more.

## Priority Queue

### Priority A — Core authoring baseline

These sketches should be closed first because they define common mechanics a designer will reach for immediately, and they force canonical answers the compiler needs anyway.

| Sketch | Why it is high leverage |
|---|---|
| `SK-15 Purify` | Forces canonical status-effect classification, cleanse filters, and immunity interception rules. |
| `SK-24 Stun` | Establishes the baseline hard-CC authoring model and DR/capability interactions. |
| `SK-29 Blizzard` | Canonical hostile stationary zone pattern: pulse timer + AoE query + periodic effect. |
| `SK-34 Charge` | Resolves complex multi-phase movement, entity pinning, and conditional movement outcomes. |
| `SK-35 Blink Strike` | Establishes instant teleport semantics and instant cross-boundary handoff rules. |
| `SK-108 Mana Burn` | Forces compiler support for resource-targeting combat, not just HP-targeting effects. |
| `SK-117 Stagger Bar` | Defines secondary combat bars and non-HP depletion states for bosses. |
| `SK-122 Counterspell` | Clarifies cast interception and mid-cast cancellation in the authoring and IR model. |

### Priority B — High-value boundary and systems closure

These sketches should follow once the baseline is stable because they define important but more specialized runtime/compiler patterns.

| Sketch | Why it is next |
|---|---|
| `SK-30 Trail of Fire` | Canonical moving-deposit geometry and movement-driven effect authoring. |
| `SK-31 Vortex` | Resolves continuous forced movement and moving-zone authority interactions. |
| `SK-32 Minefield` | Forces stealth/visibility, dormant actors, and long-lived proximity actors. |
| `SK-33 Shifting Sands` | Resolves self-propelled zones and zone boundary handoff behavior. |
| `SK-66 Symbiote` | High-value remote-origin ability pattern for cross-entity casting. |
| `SK-69 Portal Pair` | Canonical linked-structure teleport pattern. |
| `SK-82 Projectile Deflect` | Clarifies projectile ownership hijacking and projectile return semantics. |
| `SK-120 Combo Field Matrix` | Defines systemic cross-player interactions and compiler-side combo tagging. |

### Priority C — Systemic, group, or mode-specific mechanics

These should be tackled after the baseline designer surface is stable.

| Sketch | Why it is later |
|---|---|
| `SK-68 Multi-Entity Control` | Game-mode level ownership model, not baseline ability authoring. |
| `SK-77 Two-Player Entity` | Specialized multi-session control topology. |
| `SK-105 Pocket Arena` | Separate simulation-space extraction, high complexity, niche usage. |
| `SK-121 Downed State` | Important game-system mechanic, but larger lifecycle/system design than baseline ability authoring. |
| `SK-124 Group Sequential Combo` | Group-state machine mechanic, valuable but not foundational. |
| `SK-125 Group Simultaneous Input` | Group coordination mechanic, valuable but not foundational. |

## Historical Completion Log

Current Batch 1 status:

- `SK-15 Purify` — complete on 2026-04-04
- `SK-24 Stun` — complete on 2026-04-04
- `SK-29 Blizzard` — complete on 2026-04-04
- `SK-35 Blink Strike` — complete on 2026-04-04
- `SK-108 Mana Burn` — complete on 2026-04-04

Priority A completion status:

- `SK-34 Charge` — complete on 2026-04-04
- `SK-117 Stagger Bar` — complete on 2026-04-04
- `SK-122 Counterspell` — complete on 2026-04-04

Priority B closure progress:

- `SK-30 Trail of Fire` — complete on 2026-04-04
- `SK-31 Vortex` — complete on 2026-04-05 after rewriting it around canonical `zone.continuous_force` and pulse semantics
- `SK-32 Minefield` — complete on 2026-04-04
- `SK-33 Shifting Sands` — complete on 2026-04-05 after rewriting it around canonical self-propelled `zone.mobility` and pulse-driven current-position evaluation
- `SK-66 Symbiote` — complete on 2026-04-04
- `SK-69 Portal Pair` — complete on 2026-04-05 after rewriting it around bookmark-linked `spawn_actor.portal_anchor` pair placement
- `SK-82 Projectile Deflect` — complete on 2026-04-05 after rewriting it around a channel-owned self-status plus canonical `projectile_intercept`
- `SK-96 Death Ghost` — complete on 2026-04-05 after reframing it as a pre-terminal `ghost_phase` instead of a post-terminal active shell
- `SK-89 Respawn Anchor` — complete on 2026-04-05 after adding a revocable `spawn_actor.respawn_anchor` / HardEvent / Meta respawn-route contract
- `SK-120 Combo Field Matrix` — complete on 2026-04-05 after rewriting it around canonical `combo_field_type`, `combo_finisher`, and game-data `combo_matrix` lowering
- `SK-121 Downed State` — complete on 2026-04-05 after rewriting it around canonical `downed_state`, `restore_phase`, and Stage 10 finish/self-rally resolution
- `SK-68 Multi-Entity Control` — complete on 2026-04-05 after rewriting it around canonical `control_topology(mode = one_to_many)` and routed subset selection
- `SK-77 Two-Player Entity` — complete on 2026-04-05 after rewriting it around canonical `control_topology(mode = many_to_one)` with role-scoped loadout access
- `SK-105 Pocket Arena` — complete on 2026-04-05 after rewriting it around canonical `fork_instance` single-host isolation and stored parent-world return positions
- `SK-124 Group Sequential Combo` — complete on 2026-04-05 after rewriting it around canonical `group_interaction(mode = sequential)` with role-tagged ordinary casts
- `SK-125 Group Simultaneous Input` — complete on 2026-04-05 after rewriting it around canonical `group_interaction(mode = simultaneous)` with temporary option abilities
- `SK-61 Spirit Split` — complete on 2026-04-05 after rewriting it around canonical `split_form`, `cycle_split_form`, and stored-owner suspension
- `SK-40 Mind Control` — complete on 2026-04-05 after rewriting it around canonical `control_override`, `steer_target_movement`, and maintained-channel teardown
- `SK-72 Nydus Network` — complete on 2026-04-05 after rewriting it around owner-scoped `spawn_actor.portal_anchor` networks and player-choice `P-59` routing
- `SK-95 Mass Effect Detonation` — complete on 2026-04-05 after adding canonical exact-match `consume_status` and rewriting the sketch around mesh-wide `global_event` detonation
- `SK-67 Entity Clone` — complete on 2026-04-05 after rewriting it around canonical `loadout_projection`, `control_projection`, and stored-body restore semantics
- `SK-59 Oil-Ignite` — complete on 2026-04-05 after adding combo-field callback refs, declarative `despawn_entity`, `zone.owner`, and rewriting the sketch around deterministic oil-to-fire field replacement
- `SK-81 Remote Control Summon` — complete on 2026-04-05 after adding canonical `control_projection` teardown callbacks and rewriting the sketch around generated manual detonate action semantics
- `SK-107 Corpse Possession` — complete on 2026-04-05 after rewriting it around local `corpse_snapshot`, retained corpse loadout/effective-stat snapshots, and ordinary `swap_identity` restoration
- `SK-62 Boomerang` — complete on 2026-04-05 after adding placement-authored projectile heading vectors and rewriting it around canonical `return_policy` plus per-leg hit ledgers
- `SK-71 Sticky Bomb` — complete on 2026-04-05 after rewriting it around canonical projectile `attachment_policy` and carrier-owned delayed detonation
- `SK-111 Soulbind` — complete on 2026-04-05 after extending `link` with `source_entity` and rewriting it around canonical `event_clone` replay between two non-caster endpoints
- `SK-42 Withering Fire` — complete on 2026-04-05 after rewriting it around canonical count-only `charge_pool` runtime state, nearest-neighbor auto-target helpers, and post-commit charge consumption
- `SK-58 Cocoon` — complete on 2026-04-05 after rewriting it around a spawned shell actor, `enter_container(off_world_stored)`, target-owned `stasis`, and explicit break/expiry release cleanup
- `SK-06 Summon Swarm` — complete on 2026-04-05 after rewriting it around canonical multi-spawn `spawn_actor`, placement offsets, autonomy, and per-owner live-count policy
- `SK-60 Bunker` — complete on 2026-04-05 after rewriting it around canonical stationary `attached_visible` containment and bunker-shell targetability/collision policy
- `SK-83 Next-Cast Empowerment` — complete on 2026-04-05 after rewriting it around canonical `consumption_window = cast_ability` and one-shot override semantics
- `SK-98 Mobile Transport` — complete on 2026-04-05 after adding canonical `start_actor_transit` and rewriting the sketch around spawned-shell loading, late launch, arrival eject, and crash cleanup
- `SK-43 Drag` — complete on 2026-04-05 after rewriting it around first-hit projectile admission, a cleansable latch `link`, and status-owned per-tick `displacement` toward `caster_position`
- `SK-44 Burrow` — complete on 2026-04-05 after rewriting it around targetability denial, `suspension.mode = dormant`, periodic self-heal, and activation-mode early emerge
- `SK-46 Adaptation` — complete on 2026-04-05 after rewriting it around canonical `damage_accumulator` and expiry-bound healing
- `SK-47 Shield Burst` — complete on 2026-04-05 after rewriting it around canonical `apply_shield` lifecycle hooks and `bind_remaining_value_as`
- `SK-48 Death Coil` — complete on 2026-04-05 after rewriting it around any-target admission and bounded relation-conditional damage/heal branching
- `SK-49 Cone Strike` — complete on 2026-04-05 after rewriting it around canonical cone targeting, facing gates, and snapshot damage/slow payloads

Priority A, Priority B, and Priority C are now fully closed. If work continues now, the next
recommended batch should shift from the priority queue into an open-ended supported-sketch sweep,
starting with the next unresolved supported-sketch references. The supported-sketch sweep has now
also closed:

1. `SK-45 Essence Collection` — collector-owned corpse claims, owner-scoped pickup orbs, and a
   bounded count-only `essence_pool`
2. `SK-50 Blind` — canonical `apply_cc(cc_type = blind)` plus offense-side auto-attack miss
   handling
3. `SK-51 Unstoppable` — category-scoped `cleanse` plus canonical `cc_immunity_categories` and an
   ordinary shield
4. `SK-52 Combo Strike` — canonical `sequence_window`, ordered `ActivationModes`, and
   finisher-reset cooldown routing
5. `SK-53 HP Swap` — canonical same-Arbiter `swap_hp_percent` and interruptible channel completion
6. `SK-54 Entity Consumption` — canonical `off_world_stored` containment plus early
   `exit_container` reactivation

7. `SK-55 Growing Projectile` — canonical projectile travel scalars plus `ProjectileCarryBlock`
   for bounded rolling multi-target transport and handoff-stable release semantics

The supported-sketch sweep has also now closed:

8. `SK-56 Knockback Projectile` — canonical `displacement.flight_policy` with per-flight dedup,
   pass-through payloads, and wall-impact effects
9. `SK-57 Form Transformation` — canonical `swap_identity`, named self profiles, and a timed
   stat-buff overlay
10. `SK-63 Steerable Beam` — canonical `tick_while_active`, `steer_aim`, and maintained corridor
   damage queries
11. `SK-64 Mosh Pit` — channel-owned maintained area control with source-tagged removal on leave
    and break teardown
12. `SK-65 Taunt` — canonical `apply_cc(cc_type = taunt)` plus built-in auto-attack retargeting and
    source-death break
13. `SK-73 Death Immunity` — canonical `hp_floor` terminal-survival window with ordinary
    target-owner death suppression while active
14. `SK-74 Hit-Confirmed Dash` — first-hit projectile admission plus hit-only `kinematic_sweep`
    and bounded `set_cooldown` miss-vs-hit branching
15. `SK-75 Self-Sustaining Zone` — canonical `ZonePersistenceBlock(mode = until_empty_on_pulse)`
    with the required hard-cap duration
16. `SK-76 Build Zone` — canonical provider/consumer `coverage` plus spawned-actor dormancy for
    depowered turrets
17. `SK-78 Fear` — canonical `apply_cc(cc_type = fear)` forced-movement steering with ordinary
    status-resistance and CC relay semantics
18. `SK-79 Charge-Up Shot` — canonical `input_mode = hold_release` plus authoritative release-time
    scaling
19. `SK-80 Wall Bounce` — canonical projectile `bounce_policy` plus multi-segment same-tick wall
    reflection
20. `SK-84 Temporal Trap` — canonical hostile `bookmark(position)` capture plus delayed
    `restore_from_state` return under current topology
21. `SK-85 Ring Geometry` — canonical ring-shaped area targeting plus an ordinary delayed cast
    window
22. `SK-86 Decoy` — canonical spawned-actor autonomy plus team-scoped `observer_presentation`
    mirroring
23. `SK-87 Conditional Counter` — canonical `consumption_window = damage_received` with a one-shot
    protected/AoE payoff
24. `SK-88 Positional Leash` — canonical status-owned `movement_constraint` plus bookmark anchors
    and PostKinematic clamp enforcement
25. `SK-90 Orbital Sweep` — canonical `kinematic_sweep(mode = orbit_entity)` plus same-slot detach
    follow-up and per-revolution dedup
26. `SK-91 Team-Agnostic Stasis` — canonical delayed snapshot application plus
    `suspension.mode = stasis` timer-pause semantics
27. `SK-92 Anti-Heal` — canonical stat-layering on `healing_received_multiplier` with
    relation-branching AoE application
28. `SK-93 Death Prevention` — canonical status-owned `death_prevention` with authored anti-heal
    bypass policy
29. `SK-94 Placed Potion` — canonical spawned-actor `interaction` plus `instance_limit`
    oldest-first overflow
30. `SK-97 Escalating Cost` — canonical `resource_cost.escalation` plus Stage 2 `P-51`
    affordability
31. `SK-99 Target-Tracking Zone` — canonical `zone.mobility(mode = tracking_entity)` plus
    zone-centered pulse damage
32. `SK-100 Ally-Untargetable` — canonical entity `targetability_policy` plus passive
    `cc_immunity_categories`
33. `SK-101 Charm` — canonical `apply_cc(cc_type = charm)` plus source-relative steering and
    ordinary target-owner relay
34. `SK-102 Disarm` — canonical `apply_cc(cc_type = disarm)` attack suppression with no bespoke
    validator path
35. `SK-103 Facing-Dependent Effect` — canonical cone targeting plus guarded per-target facing
    branches
36. `SK-70 Energy Shield` — canonical `apply_shield.on_absorb_effects`, `modify_resource`, and
    passive `resource_stat_links` with periodic decay for live Energy-to-weapon-damage scaling
37. `SK-104 Zone-Conditional Invuln.` — canonical `zone_relation_gate` plus live mist-zone
    binding and hostile-source membership checks against the current zone position
38. `SK-106 Berserk` — canonical `apply_cc(cc_type = berserk)` plus nearest-ally retargeting and
    forced friendly-fire auto-attack authorization
39. `SK-109 Movement Damage` — canonical status-owned `movement_damage` plus absolute-position
    displacement tracking and ordinary hostile damage emission
40. `SK-110 Mute` — canonical `apply_cc(cc_type = mute)` plus `PASSIVES_ACTIVE` suspension of
    passive statuses, aura pulses, and passive item effects
41. `SK-112 Deferred Resolution` — canonical status-owned `deferred_ledger` plus frozen observer
    HP and immediate cash-out on expiry/removal
42. `SK-113 Hit-Count Shield` — canonical `apply_shield(shield_type = instance)` plus `P-19`
    ordering ahead of absorption barriers and one-charge-per-damage-event semantics
43. `SK-114 Piercing Execute` — canonical `execute` plus target-owner threshold checks and the
    optional bypass-prevention kill path
44. `SK-115 Corpse Economy` — canonical `corpse_profile` plus `consume_corpse` selection, atomic
    claim, corpse bindings, and local corpse-registry limits
45. `SK-116 Charge-Finisher` — canonical typed `charge_pool` plus generator/spender
    `modify_charge_pool` semantics and all-at-once decay
46. `SK-118 Partial CC Immunity` — canonical `self_cc_immunity_during_cast` plus
    `cc_immunity_categories` for displacement-only or full-super-armor variants
47. `SK-119 Counter Window` — canonical `vulnerability_window` plus
    `can_counter_vulnerability_window` and mechanical counter-stagger semantics
48. `SK-123 Concentration` — canonical `requires_concentration = true` plus `concentration`
    slot ownership, damage checks, and instance-owned teardown
49. `SK-01 Toss` — canonical `displacement` plus committed `landing_pos`, sibling airborne lockout,
    and PostKinematic landing-blast resolution
50. `SK-02 Poison Shot` — canonical projectile-applied poison status with periodic damage, drain
    `value_conversion`, source buff stacks, and a bounded refresh helper on later qualifying hits
51. `SK-03 Terrain Wall` — canonical `inject_geometry(mode = segment)` plus timed corridor
    blocking and boundary-replicated collision
52. `SK-04 Tether` — canonical symmetric `link` with break distance, `damage_redirect`, and
    `heal_mirror_ratio`
53. `SK-05 Global Strike` — canonical `channel(complete_only)` plus controller-escalated
    `global_event` scheduling and target-owner defense resolution
54. `SK-07 Ability Steal` — canonical `borrow_ability_slot(source_selector = last_cast_ability)`
    with one-use revert and cross-boundary cast-history lookup
55. `SK-08 Aura` — canonical attached passive `zone` with pulse damage and refresh-style slow
    application
56. `SK-09 Chain Lightning` — canonical `on_hit` plus `PropagationBlock(mode = bounce_nearest)`
    with per-chain dedup and generation falloff
57. `SK-10 Crit Explosion` — canonical `on_crit` plus `PropagationBlock(mode = fanout_query)`
    with bounded recursive child explosions
58. `SK-11 On-Kill Cascade` — killer-attributed `on_death` plus refresh-style killer buff and
    bounded corpse-burst propagation from `death_position`
59. `SK-12 Spell Echo` — canonical `on_cast` plus
    `PropagationBlock(mode = repeat_same_cast)` with same-snapshot replay and finite generation
    bounds
60. `SK-13 Counter-Strike` — reactive `on_block` riposte damage with reverse relay and no second
    miss/block admission pass on the attacker
61. `SK-14 Execute Threshold` — target-owner low-HP threshold branching plus a bounded
    `set_cooldown` kill follow-up on the empowered branch
62. `SK-16 Holy Ground` — stationary allied `zone` with pulse-heal behavior and ordinary
    remote-heal relay
63. `SK-17 Sacrifice Shield` — full-cost-or-reject self sacrifice plus bounded formula-derived
    shield amount and ordinary `apply_shield(absorption)` runtime
64. `SK-18 Resurrect` — canonical `channel(complete_only)` plus local `revive_corpse`,
    corpse-targeted re-materialization, and pending Meta timer cancel
65. `SK-19 Guardian Angel` — canonical asymmetric `link` plus
    `damage_redirect(direction = target_to_source)` and guardian-side defensive resolution
66. `SK-20 Battle Cry` — self-centered snapshot ally query plus positive `apply_buff` and
    `stat_modifiers` for ordinary haste layering
67. `SK-21 Block` — canonical `block_defense` plus built-in block DR penalty/decay and ordinary
    `on_block` follow-up semantics
68. `SK-22 Damage Reflection` — passive `on_damage_received` reflection from committed branch-local
    damage with a reactive reverse-hit safety bound
69. `SK-23 Thorns Aura` — direct-melee `on_damage_received` retaliation with flat damage and
    canonical reactive-depth bounds
70. `SK-25 Root` — canonical `apply_cc(cc_type = root)` plus movement-only suppression and shared
    soft-disable DR
71. `SK-26 Silence` — canonical `apply_cc(cc_type = silence)` plus cast suppression and immediate
    cast/channel interruption
72. `SK-27 Sleep` — canonical `apply_cc(cc_type = sleep)` plus built-in break-on-damage behavior
    and follow-up hard-disable immunity
73. `SK-28 Slow + DR` — narrowed to the canonical negative slow-status path with
    `cc_category = soft_disable`, `duration_scaling = status_resistance`, and ordinary
    movement-speed stat layering
74. `SK-36 Shadow Step` — canonical `bookmark(position)` runtime state plus ordered activation
    modes and `restore_from_state` for same-key blink-and-return routing
75. `SK-37 Time Rewind` — passive `snapshot_buffer` recorder plus `restore_from_state` for self
    position+HP rewind without rewinding current buffs, resources, or cooldowns
76. `SK-38 Contagion` — canonical status-owned `spread` plus compiler-owned `chain_id` /
    generation metadata and per-chain infection dedup
77. `SK-39 Spectral Dash` — canonical `spawn_actor.output_binding`, `bookmark(entity_ref)`, and
    same-key `restore_from_state` to a live projectile bookmark
78. `SK-41 Detonation Arrow` — canonical projectile `detonation_policy.manual_trigger`,
    `bookmark(entity_ref)`, and same-key live-projectile detonation routing

The supported-sketch sweep is now fully complete. All 125 sketches are `Sketch-Complete`; there is
no remaining supported-sketch batch.
