# Sketch/Compiler Compatibility Checklist

This audit answers a narrower question than `COMPLETION_CHECKLIST.md`:

- `COMPLETION_CHECKLIST.md` asks whether a sketch is fully closed as a designer-recreatable reference.
- This file asks whether the **current canonical compiler docs** already support the sketch, partially support it, or still have a real compiler-contract gap.

This is a diagnostic artifact. It does not itself change compiler policy.

## Audit Basis

The audit is based on the current canonical compiler layer:

- `docs-game-compiler/01-*`
- `docs-game-compiler/02-schema-and-validation.md`
- `docs-game-compiler/03-1-compiler-ir-specification.md`
- `docs-game-compiler/04-game-image-format.md`
- `docs-game-compiler/05-runtime-loading-and-activation.md`
- `docs-game-compiler/ability-primitives/`

It is **not** based on sketch TODO count alone. A sketch can still contain TODO prose while the compiler surface is already sufficient for the mechanic.

## Status Legend

Overall status:

- `Cmp` = `Complete` — closed sketch with canonical compiler support.
- `Sup` = `Supported` — current compiler docs appear sufficient.
- `Par` = `Partial` — most surface exists, but one or more canonical contracts remain thin or implicit.
- `Blk` = `Blocked` — the compiler lacks a necessary first-class concept or canonical authoring/lowering contract.

Column legend:

- `Prim` — primitive taxonomy coverage
- `XB` — cross-boundary / authority contract
- `Auth` — designer-facing authoring surface
- `IR` — lowering / runtime-artifact contract
- `Val` — validation / compile-time rule coverage

## Summary Counts

- `Cmp`: 119
- `Sup`: 6
- `Par`: 0
- `Blk`: 0

There are currently no open compiler-gap families. Remaining sketch work is now entirely
designer-facing closure of already-supported references.

See `COMPILER_GAP_REGISTER.md` for the grouped backlog behind those IDs.

## Batch 1 — Priority A
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-15 Purify | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | CG-00 | Closed and canonicalized in compiler docs. |
| SK-24 Stun | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at the canonical CC lifecycle, DR, immunity, and follow-up status rules. |
| SK-29 Blizzard | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at the canonical stationary-zone, pulse, and target-owner relay contract. |
| SK-34 Charge | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at the canonical `kinematic_sweep` + `capture_first` + world-impact contract. |
| SK-35 Blink Strike | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at destination-owner snap recomputation and same-tick follow-up strike resolution. |
| SK-108 Mana Burn | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at deferred `on_hit` -> `resource_burn` lowering and target-owner burn authority. |
| SK-117 Stagger Bar | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `stagger_bar`, `stagger_damage`, and target-owner mechanical break-state resolution. |
| SK-122 Counterspell | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at visible cast-state publication and deterministic `P-40` mid-cast cancellation. |

## Batch 2 — Priority B
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-30 Trail of Fire | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at the canonical `polyline_zone` corridor-sampling and contact-payload contract. |
| SK-31 Vortex | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical stationary `zone` pulses plus `continuous_force` pre-kinematic inward drag. |
| SK-32 Minefield | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at deterministic `spawn_actor.placement`, spawned interaction, and visibility/targetability trap policy. |
| SK-33 Shifting Sands | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `zone.mobility = self_propelled` plus pulse-driven current-position evaluation. |
| SK-66 Symbiote | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at link-bound remote origin, observer anchoring, projected loadouts, and body lockout semantics. |
| SK-69 Portal Pair | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at bookmark-linked `portal_anchor` pair placement plus ordinary `P-59` bidirectional use. |
| SK-82 Projectile Deflect | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at a channel-owned self-status with canonical `projectile_intercept` deflect-to-source behavior. |
| SK-120 Combo Field Matrix | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `combo_field_type`, `combo_finisher`, and game-data `combo_matrix` lookup behavior. |

## Batch 3 — Priority C
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-68 Multi-Entity Control | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `control_topology(mode = one_to_many)` with routed subset selection and grouped elimination policy. |
| SK-77 Two-Player Entity | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `control_topology(mode = many_to_one)` with role-scoped control and loadout restrictions. |
| SK-105 Pocket Arena | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `fork_instance` single-host isolation plus pre-instance remote admission and stored return positions. |
| SK-121 Downed State | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `downed_state`, `restore_phase`, and Stage 10 rally/finish/self-rally lifecycle behavior. |
| SK-124 Group Sequential Combo | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `group_interaction(mode = sequential)` with role-tagged ordinary casts advancing the session. |
| SK-125 Group Simultaneous Input | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `group_interaction(mode = simultaneous)` with temporary option abilities and ordered/count pattern resolution. |

## Batch 4A — Remaining SK-01 to SK-23
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-01 Toss | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `displacement`, committed `landing_pos`, and PostKinematic landing-blast resolution. |
| SK-02 Poison Shot | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at a projectile-applied poison status with periodic drain, source buff stacks, and a bounded refresh helper. |
| SK-03 Terrain Wall | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `inject_geometry(mode = segment)` plus boundary-replicated corridor blocking. |
| SK-04 Tether | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at a symmetric `link` with break distance, `damage_redirect`, and `heal_mirror_ratio`. |
| SK-05 Global Strike | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at `channel(complete_only)` plus controller-escalated `global_event` execution. |
| SK-06 Summon Swarm | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical multi-spawn `spawn_actor`, placement lattices, summon autonomy, and per-owner live-count semantics. |
| SK-07 Ability Steal | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `borrow_ability_slot(source_selector = last_cast_ability)` with one-use revert semantics. |
| SK-08 Aura | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at an attached passive `zone` with pulse damage and refresh-style slow application. |
| SK-09 Chain Lightning | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at `on_hit` plus `PropagationBlock(mode = bounce_nearest)` with per-chain dedup and falloff. |
| SK-10 Crit Explosion | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at `on_crit` plus `PropagationBlock(mode = fanout_query)` with bounded recursive child explosions. |
| SK-11 On-Kill Cascade | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at killer-attributed `on_death`, refresh-style killer buffs, and bounded corpse-burst propagation from `death_position`. |
| SK-12 Spell Echo | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at `on_cast` plus `PropagationBlock(mode = repeat_same_cast)` with same-snapshot replay and explicit finite generation bounds. |
| SK-13 Counter-Strike | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at reactive `on_block` riposte damage, reverse prepared-hit relay, and no second miss/block admission pass on the attacker. |
| SK-14 Execute Threshold | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at target-owner low-HP threshold branching plus a bounded `set_cooldown` kill follow-up. |
| SK-16 Holy Ground | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at a stationary allied `zone` with pulse-heal behavior and ordinary remote-heal relay. |
| SK-17 Sacrifice Shield | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at full-cost-or-reject self sacrifice plus bounded formula-derived shield amount and ordinary `apply_shield(absorption)` runtime. |
| SK-18 Resurrect | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at `channel(complete_only)` plus local `revive_corpse` re-materialization and pending Meta timer cancel. |
| SK-19 Guardian Angel | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at an asymmetric `link` with `damage_redirect(direction = target_to_source)` and partner-side defensive resolution. |
| SK-20 Battle Cry | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at a self-centered snapshot ally query plus positive `apply_buff`/`stat_modifiers` layering. |
| SK-21 Block | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `block_defense`, built-in block DR decay, and ordinary `on_block` follow-up semantics. |
| SK-22 Damage Reflection | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at passive `on_damage_received` reflection from committed branch-local damage with reactive reverse-hit bounds. |
| SK-23 Thorns Aura | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at direct-melee `on_damage_received` retaliation with flat damage and canonical reactive-depth bounds. |

## Batch 4B — Remaining SK-25 to SK-49
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-25 Root | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = root)`, movement-only suppression, and shared soft-disable DR. |
| SK-26 Silence | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = silence)`, cast suppression, and immediate cast/channel interruption. |
| SK-27 Sleep | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = sleep)`, built-in break-on-damage behavior, and follow-up hard-disable immunity. |
| SK-28 Slow + DR | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at a negative slow status with `cc_category = soft_disable`, `duration_scaling = status_resistance`, and ordinary movement-speed stat layering. |
| SK-36 Shadow Step | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at `bookmark(position)`, ordered activation modes, and `restore_from_state` for same-key blink-and-return routing. |
| SK-37 Time Rewind | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at a passive `snapshot_buffer` recorder plus `restore_from_state` for self position+HP rewind. |
| SK-38 Contagion | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at status-owned `spread`, compiler-owned `chain_id` / generation metadata, and per-chain infection dedup. |
| SK-39 Spectral Dash | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at `spawn_actor.output_binding`, `bookmark(entity_ref)`, and same-key `restore_from_state` to a live projectile bookmark. |
| SK-40 Mind Control | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `control_override`, Stage 1 routed steering, and maintained-channel teardown semantics. |
| SK-41 Detonation Arrow | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at projectile `detonation_policy.manual_trigger`, `bookmark(entity_ref)`, and same-key live-projectile detonation routing. |
| SK-42 Withering Fire | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical count-only `charge_pool` state, nearest-neighbor auto-target helpers, and post-commit charge consumption. |
| SK-43 Drag | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at first-hit projectile admission, cleansable latch binding, and status-owned per-tick pull toward `caster_position`. |
| SK-44 Burrow | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at targetability denial, dormant suspension, periodic self-heal, and activation-mode early emerge. |
| SK-45 Essence Collection | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at collector-owned corpse claims, owner-scoped pickup orbs, and a bounded count-only `essence_pool` consume/heal flow. |
| SK-46 Adaptation | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `damage_accumulator`, expiry-bound healing, and remove-vs-expire separation. |
| SK-47 Shield Burst | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_shield` lifecycle hooks and remaining-value AoE scaling. |
| SK-48 Death Coil | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at any-target admission plus bounded relation-conditional damage/heal branching. |
| SK-49 Cone Strike | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical cone targeting, facing gates, and snapshot damage/slow payloads. |

## Batch 4C — Remaining SK-50 to SK-74
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-50 Blind | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = blind)` and the offense-side miss check on the engine-owned auto-attack path. |
| SK-51 Unstoppable | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at category-scoped `cleanse`, full `cc_immunity_categories`, and an ordinary paired shield. |
| SK-52 Combo Strike | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `sequence_window`, ordered `ActivationModes`, and finisher-reset cooldown routing. |
| SK-53 HP Swap | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical same-Arbiter `swap_hp_percent` with channel-complete paired overwrite semantics. |
| SK-54 Entity Consumption | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `off_world_stored` containment, early `exit_container` reactivation, and eject-on-removed behavior. |
| SK-55 Growing Projectile | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical projectile travel scalars, `ProjectileCarryBlock`, and handoff-stable carried-target roster semantics. |
| SK-56 Knockback Projectile | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `displacement.flight_policy` with per-flight dedup, pass-through payloads, and wall-impact effects. |
| SK-57 Form Transformation | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `swap_identity`, named self profiles, and a timed stat-buff overlay. |
| SK-58 Cocoon | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at spawned shell + `enter_container(off_world_stored)` plus target-owned `stasis` semantics and release-on-break cleanup. |
| SK-59 Oil-Ignite | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical combo-field callback refs, `despawn_entity`, and deterministic oil-to-fire field replacement. |
| SK-60 Bunker | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical stationary `attached_visible` containment, firing-port cast policy, and forced-eject-on-removal behavior. |
| SK-61 Spirit Split | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `split_form`, `cycle_split_form`, and stored-owner suspension/reform policy. |
| SK-62 Boomerang | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at placement-authored projectile heading lattices plus canonical `return_policy` and per-leg hit-ledger semantics. |
| SK-63 Steerable Beam | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `tick_while_active` channels, `steer_aim`, and maintained corridor damage queries. |
| SK-64 Mosh Pit | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at channel-owned maintained area control with source-tagged removal on leave and break teardown. |
| SK-65 Taunt | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = taunt)` and the built-in source-death break / auto-attack retarget profile. |
| SK-67 Entity Clone | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `loadout_projection`, `control_projection`, stored-body suspension, and projected-body restore semantics. |
| SK-70 Energy Shield | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_shield.on_absorb_effects`, `modify_resource`, and passive `resource_stat_links`-driven Energy decay plus weapon-damage scaling. |
| SK-71 Sticky Bomb | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical projectile `attachment_policy`, carrier-owned delayed payloads, and last-known-position carrier-loss detonation. |
| SK-72 Nydus Network | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at owner-scoped `portal_anchor` networks, controller-replicated `P-59` membership, and player-choice destination routing. |
| SK-73 Death Immunity | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `hp_floor` ordering and ordinary target-owner terminal-death suppression while the floor is active. |
| SK-74 Hit-Confirmed Dash | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical first-hit projectile admission, hit-only `kinematic_sweep`, and bounded `set_cooldown` miss-vs-hit branching. |

## Batch 4D — Remaining SK-75 to SK-99
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-75 Self-Sustaining Zone | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `ZonePersistenceBlock(mode = until_empty_on_pulse)` with the required hard-cap duration. |
| SK-76 Build Zone | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical provider/consumer `coverage` plus spawned-actor dormancy for depowered turrets. |
| SK-78 Fear | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = fear)` forced-movement steering, status-resistance scaling, and ordinary CC relay. |
| SK-79 Charge-Up Shot | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `input_mode = hold_release` plus authoritative release-time scaling. |
| SK-80 Wall Bounce | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical projectile `bounce_policy` and multi-segment same-tick wall reflection. |
| SK-81 Remote Control Summon | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `control_projection` teardown callbacks, projected-actor callback refs, and generated manual detonate action semantics. |
| SK-83 Next-Cast Empowerment | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `consumption_window = cast_ability` authoring with one-shot per-ability overrides. |
| SK-84 Temporal Trap | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical hostile `bookmark(position)` capture plus delayed `restore_from_state` return under current topology. |
| SK-85 Ring Geometry | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical ring-shaped area targeting plus an ordinary delayed cast window. |
| SK-86 Decoy | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical spawned-actor autonomy plus team-scoped `observer_presentation` mirroring. |
| SK-87 Conditional Counter | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `consumption_window = damage_received` with a one-shot protected/AoE payoff. |
| SK-88 Positional Leash | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical status-owned `movement_constraint` with bookmark anchors and PostKinematic clamp enforcement. |
| SK-89 Respawn Anchor | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `spawn_actor.respawn_anchor`, revocable `PlayerDied.respawn_override`, and Meta/SpawnEntity anchor-respawn handling. |
| SK-90 Orbital Sweep | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `kinematic_sweep(mode = orbit_entity)` plus same-slot detach follow-up and per-revolution dedup. |
| SK-91 Team-Agnostic Stasis | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical delayed snapshot application plus `suspension.mode = stasis` timer-pause semantics. |
| SK-92 Anti-Heal | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical stat-layering on `healing_received_multiplier` with relation-branching AoE application. |
| SK-93 Death Prevention | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical status-owned `death_prevention` with authored anti-heal bypass policy. |
| SK-94 Placed Potion | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical spawned-actor `interaction` plus `instance_limit` oldest-first overflow. |
| SK-95 Mass Effect Detonation | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at mesh-wide `global_event` execution plus exact-match `consume_status` target-side detonation. |
| SK-96 Death Ghost | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `ghost_phase` lifecycle, delayed kill credit, and respawn-delay credit semantics. |
| SK-97 Escalating Cost | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `resource_cost.escalation` and Stage 2 `P-51` affordability. |
| SK-98 Mobile Transport | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `start_actor_transit`, stationary `P-58` loading, and shell `on_death` crash-eject cleanup. |
| SK-99 Target-Tracking Zone | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `zone.mobility(mode = tracking_entity)` and zone-centered pulse damage. |

## Batch 4E — Remaining SK-100 to SK-123
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-100 Ally Untargetable | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical entity `targetability_policy` plus passive CC-immunity categories. |
| SK-101 Charm | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = charm)` with source-relative steering and ordinary target-owner relay. |
| SK-102 Disarm | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = disarm)` attack suppression with no bespoke validator path. |
| SK-103 Facing-Dependent Effect | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical cone targeting plus guarded per-target facing branches. |
| SK-104 Zone-Conditional Invuln. | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `zone_relation_gate`, live mist-zone binding, and hostile-source membership checks. |
| SK-106 Berserk | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = berserk)` with nearest-ally retargeting and friendly-fire authorization. |
| SK-107 Corpse Possession | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at local `corpse_snapshot` identity projection, retained loadout/effective-stat snapshots, and ordinary `swap_identity` restore semantics. |
| SK-109 Movement Damage | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical status-owned `movement_damage` with absolute-position delta and ordinary damage resolution. |
| SK-110 Mute | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_cc(cc_type = mute)` and `PASSIVES_ACTIVE` suspension semantics. |
| SK-111 Soulbind | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at non-caster-endpoint `link` authoring plus canonical `event_clone` replay and anti-recursion semantics. |
| SK-112 Deferred Resolution | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical status-owned `deferred_ledger` with frozen observer HP and immediate cash-out on removal. |
| SK-113 Hit-Count Shield | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `apply_shield(shield_type = instance)` with `P-19` ordering ahead of absorption barriers. |
| SK-114 Piercing Execute | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `execute` with target-owner threshold checks and the optional bypass-prevention kill path. |
| SK-115 Corpse Economy | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `corpse_profile` plus `consume_corpse` selection, claim, and corpse-binding semantics. |
| SK-116 Charge-Finisher | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical typed `charge_pool` state plus generator/spender `modify_charge_pool` semantics. |
| SK-118 Partial CC Immunity | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `self_cc_immunity_during_cast` and `cc_immunity_categories`. |
| SK-119 Counter Window | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `vulnerability_window` and counter-eligible ability metadata. |
| SK-123 Concentration | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | — | Closed sketch now points directly at canonical `requires_concentration = true` plus `concentration` ownership and teardown policy. |
