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

- `Cmp`: 1
- `Sup`: 43
- `Par`: 32
- `Blk`: 49

Highest-leverage open gap families right now:

- `CG-16` Special resolution policies for non-HP combat state
- `CG-11` Control topology, identity swap, and multi-owner loadout authoring
- `CG-02` Channel, maintained-cast, and interruption lifecycle
- `CG-05` Zone actor lifecycle variants

See `COMPILER_GAP_REGISTER.md` for the grouped backlog behind those IDs.

## Batch 1 — Priority A
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-15 Purify | Cmp | Cmp | Cmp | Cmp | Cmp | Cmp | CG-00 | Closed and canonicalized in compiler docs. |
| SK-24 Stun | Sup | Sup | Sup | Sup | Sup | Sup | — | Canonical CC lifecycle now covers duration scaling, immunity windows, and interrupt policy. |
| SK-29 Blizzard | Sup | Par | Par | Par | Par | Par | CG-05 | Common zone pattern exists, but zone lifecycle rules are incomplete. |
| SK-34 Charge | Sup | Par | Blk | Blk | Blk | Blk | CG-06 | Sweep volume and collision-capture authoring are missing. |
| SK-35 Blink Strike | Sup | Par | Sup | Par | Sup | Par | CG-01 | Instant teleport authoring is now canonical; the remaining gap is the snap/relay authority matrix. |
| SK-108 Mana Burn | Sup | Par | Par | Par | Par | Par | CG-01, CG-16 | Resource-targeted combat exists conceptually but lacks full contract. |
| SK-117 Stagger Bar | Sup | Sup | Par | Par | Par | Par | CG-16 | Core schema exists; broader combat/lifecycle policy is still thin. |
| SK-122 Counterspell | Sup | Par | Blk | Blk | Par | Par | CG-02 | Counterspell metadata exists; targeted mid-cast cancel flow is still thin. |

## Batch 2 — Priority B
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-30 Trail of Fire | Sup | Par | Blk | Blk | Blk | Blk | CG-06 | Polyline/path-volume authoring is missing. |
| SK-31 Vortex | Sup | Par | Par | Par | Par | Par | CG-05 | Moving zone with continuous pull profile is not fully canonicalized. |
| SK-32 Minefield | Sup | Par | Blk | Blk | Par | Blk | CG-09, CG-10 | Dormant invisible proximity actors are not fully modeled. |
| SK-33 Shifting Sands | Sup | Par | Par | Par | Par | Par | CG-05 | Self-propelled zone ownership/lifecycle is not fully canonicalized. |
| SK-66 Symbiote | Sup | Blk | Blk | Blk | Blk | Blk | CG-04, CG-11 | Remote-origin casting and binding authoring are missing. |
| SK-69 Portal Pair | Sup | Blk | Blk | Blk | Blk | Blk | CG-12 | Portal network semantics are not surfaced canonically. |
| SK-82 Projectile Deflect | Sup | Par | Blk | Par | Par | Blk | CG-14 | Projectile ownership hijack lacks authoring surface. |
| SK-120 Combo Field Matrix | Sup | Sup | Sup | Sup | Sup | Sup | — | Combo matrix and finisher metadata already exist. |

## Batch 3 — Priority C
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-68 Multi-Entity Control | Sup | Blk | Blk | Blk | Blk | Blk | CG-11 | Multi-owner control topology lacks schema-level support. |
| SK-77 Two-Player Entity | Sup | Blk | Blk | Blk | Blk | Blk | CG-11 | Dual-owner entity control is outside current schema surface. |
| SK-105 Pocket Arena | Sup | Blk | Blk | Blk | Blk | Blk | CG-12 | Spatial instance forking/return semantics are missing. |
| SK-121 Downed State | Sup | Par | Blk | Blk | Par | Par | CG-13 | Downed-state schema exists, but lifecycle details remain thin. |
| SK-124 Group Sequential Combo | Sup | Blk | Blk | Blk | Blk | Blk | CG-15 | Group-step aggregation authoring is missing. |
| SK-125 Group Simultaneous Input | Sup | Blk | Blk | Blk | Blk | Blk | CG-15 | Group-choice aggregation authoring is missing. |

## Batch 4A — Remaining SK-01 to SK-23
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-01 Toss | Sup | Sup | Sup | Sup | Sup | Sup | — | Canonical YAML example in schema doc. |
| SK-02 Poison Shot | Sup | Sup | Sup | Sup | Sup | Sup | — | Projectile + on-hit DoT path is already modeled. |
| SK-03 Terrain Wall | Sup | Par | Blk | Blk | Blk | Blk | CG-06 | Dynamic collision injection lacks authoring surface. |
| SK-04 Tether | Sup | Par | Blk | Blk | Blk | Blk | CG-04 | Persistent linkage/clamp flow is not surfaced. |
| SK-05 Global Strike | Sup | Blk | Blk | Blk | Par | Blk | CG-02, CG-17 | Needs channel lifecycle plus controller escalation contract. |
| SK-06 Summon Swarm | Sup | Par | Blk | Par | Par | Blk | CG-09 | Spawned minion AI/lifecycle is not canonicalized. |
| SK-07 Ability Steal | Sup | Blk | Blk | Blk | Blk | Blk | CG-11 | Identity/loadout swap authoring is missing. |
| SK-08 Aura | Sup | Sup | Sup | Sup | Sup | Sup | — | Attached zone + pulse + status layering are covered. |
| SK-09 Chain Lightning | Sup | Par | Par | Par | Par | Par | CG-08 | Chain state, dedup, and bounds need canonical policy. |
| SK-10 Crit Explosion | Sup | Par | Par | Par | Par | Par | CG-08 | Recursive proc depth exists in IR but not in authoring rules. |
| SK-11 On-Kill Cascade | Sup | Par | Par | Par | Par | Par | CG-08 | Bounded recursive kill fan-out needs explicit lowering contract. |
| SK-12 Spell Echo | Sup | Sup | Par | Par | Par | Par | CG-08 | Delayed repeated casts now reduce to a bounded recursion/decay policy gap, not a temporal-state gap. |
| SK-13 Counter-Strike | Sup | Sup | Sup | Sup | Sup | Sup | — | Facing guard + on-block trigger are already present. |
| SK-14 Execute Threshold | Sup | Sup | Sup | Sup | Sup | Sup | — | Conditional threshold guards are already canonical. |
| SK-16 Holy Ground | Sup | Sup | Sup | Sup | Sup | Sup | — | Stationary ally-heal zone is expressible with current schema. |
| SK-17 Sacrifice Shield | Sup | Sup | Sup | Sup | Sup | Sup | — | Shield + value conversion path is already present. |
| SK-18 Resurrect | Sup | Par | Blk | Blk | Par | Blk | CG-02, CG-13 | Corpse-targeted channel/resurrection flow is not canonicalized. |
| SK-19 Guardian Angel | Sup | Par | Blk | Blk | Blk | Blk | CG-04 | Damage-redirection linkage lacks schema and runtime contract. |
| SK-20 Battle Cry | Sup | Sup | Sup | Sup | Sup | Sup | — | AoE ally stat buff is covered by query + layering. |
| SK-21 Block | Sup | Sup | Par | Par | Par | Par | CG-16 | Block-negation policy exists conceptually but lacks a full compiler contract. |
| SK-22 Damage Reflection | Sup | Sup | Sup | Sup | Sup | Sup | — | On-damage trigger path already supports the core mechanic. |
| SK-23 Thorns Aura | Sup | Sup | Sup | Sup | Sup | Sup | — | Reactive damage-on-hit behavior is already representable. |

## Batch 4B — Remaining SK-25 to SK-49
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-25 Root | Sup | Sup | Sup | Sup | Sup | Sup | — | Root is now covered by the canonical soft-disable profile plus movement-ability admission rules. |
| SK-26 Silence | Sup | Sup | Sup | Sup | Sup | Sup | — | Silence now has canonical cast-block and interrupt behavior. |
| SK-27 Sleep | Sup | Sup | Sup | Sup | Sup | Sup | — | Sleep break-on-damage and expiry-follow-up semantics are now canonical. |
| SK-28 Slow + DR | Sup | Sup | Sup | Sup | Sup | Sup | — | Canonical path is a negative status with `cc_category = soft_disable` and `duration_scaling = status_resistance`. |
| SK-36 Shadow Step | Sup | Sup | Sup | Sup | Sup | Sup | — | Bookmark runtime state plus ordered activation modes now cover blink-and-return routing canonically. |
| SK-37 Time Rewind | Sup | Sup | Sup | Sup | Sup | Sup | — | Snapshot-buffer runtime state plus restore semantics now cover self rewind end-to-end. |
| SK-38 Contagion | Sup | Par | Par | Par | Par | Par | CG-08 | Autonomous spread and dedup need bounded lowering rules. |
| SK-39 Spectral Dash | Sup | Par | Par | Par | Par | Par | CG-14 | Moving reactivation state is now modeled; the remaining gap is specialized live-projectile lifecycle authoring. |
| SK-40 Mind Control | Sup | Blk | Blk | Blk | Blk | Blk | CG-02, CG-11 | Cross-entity control transfer is not surfaced canonically. |
| SK-41 Detonation Arrow | Sup | Sup | Sup | Sup | Sup | Sup | — | Manual-trigger projectile config plus entity-ref runtime state now cover launch-then-detonate routing. |
| SK-42 Withering Fire | Sup | Sup | Sup | Sup | Sup | Sup | — | Independent recharge, minimum-use interval, and count-only charge state are now canonical. |
| SK-43 Drag | Sup | Par | Blk | Blk | Blk | Blk | CG-04 | Moving linkage between caster and target lacks schema. |
| SK-44 Burrow | Sup | Par | Blk | Blk | Par | Blk | CG-10 | Dormancy/untargetable/visibility state lacks authoring surface. |
| SK-45 Essence Collection | Sup | Par | Blk | Blk | Par | Blk | CG-13 | Corpse pickup and resource extraction flows are missing. |
| SK-46 Adaptation | Sup | Sup | Par | Par | Par | Par | CG-16 | Deferred damage-window accumulation lacks an end-to-end contract. |
| SK-47 Shield Burst | Sup | Sup | Par | Par | Par | Par | CG-16 | Shield break/expiry conversion needs clearer lowering semantics. |
| SK-48 Death Coil | Sup | Sup | Sup | Sup | Sup | Sup | — | Conditional heal-or-damage is expressible with current schema. |
| SK-49 Cone Strike | Sup | Sup | Sup | Sup | Sup | Sup | — | Cone targeting and facing checks are already canonical. |

## Batch 4C — Remaining SK-50 to SK-74
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-50 Blind | Sup | Sup | Sup | Sup | Sup | Sup | — | Blind now has a canonical offense-side miss profile on the engine-owned auto-attack path. |
| SK-51 Unstoppable | Sup | Sup | Sup | Sup | Sup | Sup | — | Full CC immunity and self-cleanse windows now lower through canonical status-immunity metadata. |
| SK-52 Combo Strike | Sup | Sup | Sup | Sup | Sup | Sup | — | Sequence-window runtime state now canonically covers same-key combo routing. |
| SK-53 HP Swap | Sup | Sup | Par | Par | Par | Par | CG-16 | HP exchange ordering/floor semantics need explicit policy. |
| SK-54 Entity Consumption | Sup | Blk | Blk | Blk | Blk | Blk | CG-12 | Containment/removal-and-release flow lacks schema. |
| SK-55 Growing Projectile | Sup | Par | Blk | Par | Par | Blk | CG-14 | Projectile size/power mutation lacks canonical authoring. |
| SK-56 Knockback Projectile | Sup | Par | Blk | Par | Par | Blk | CG-14 | Entity-as-projectile behavior is not surfaced canonically. |
| SK-57 Form Transformation | Sup | Blk | Blk | Blk | Blk | Blk | CG-11 | Identity/loadout swap authoring is still missing. |
| SK-58 Cocoon | Sup | Par | Blk | Blk | Par | Blk | CG-10 | Suspension/dormancy shell lifecycle lacks compiler support. |
| SK-59 Oil-Ignite | Sup | Par | Par | Par | Par | Par | CG-05 | Reactivation/state-change routing is now covered; the remaining gap is zone lifecycle and transform policy. |
| SK-60 Bunker | Sup | Blk | Blk | Blk | Blk | Blk | CG-12 | Vehicle/container semantics lack canonical authoring. |
| SK-61 Spirit Split | Sup | Blk | Blk | Blk | Blk | Blk | CG-11, CG-12 | Multi-body control plus instance topology are both missing. |
| SK-62 Boomerang | Sup | Par | Blk | Par | Par | Par | CG-14 | Return-flight projectile policy lacks canonical support. |
| SK-63 Steerable Beam | Sup | Par | Blk | Blk | Par | Blk | CG-02 | Channel steering and interrupt semantics are not fully canonical. |
| SK-64 Mosh Pit | Sup | Par | Blk | Blk | Par | Blk | CG-02 | Channel-bound AoE CC lifecycle is not canonicalized. |
| SK-65 Taunt | Sup | Sup | Sup | Sup | Sup | Sup | — | Taunt target override and source-death break policy are now canonical. |
| SK-67 Entity Clone | Sup | Blk | Blk | Blk | Blk | Blk | CG-09, CG-11 | Spawned clone plus borrowed loadout is not canonicalized. |
| SK-70 Energy Shield | Sup | Sup | Sup | Sup | Sup | Sup | — | Absorb-to-resource loop is already representable. |
| SK-71 Sticky Bomb | Sup | Par | Blk | Par | Par | Par | CG-14 | Attached delayed projectile detonation lacks full projectile-policy coverage. |
| SK-72 Nydus Network | Sup | Blk | Blk | Blk | Blk | Blk | CG-12 | N-way portal membership/topology is missing. |
| SK-73 Death Immunity | Sup | Sup | Par | Par | Par | Par | CG-16 | Floor-clamp lifecycle needs a clearer compiler contract. |
| SK-74 Hit-Confirmed Dash | Sup | Par | Blk | Blk | Blk | Blk | CG-06 | Hit-confirmed sweep/dash authoring is not canonicalized. |

## Batch 4D — Remaining SK-75 to SK-99
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-75 Self-Sustaining Zone | Sup | Par | Par | Par | Par | Par | CG-05 | Hit-count-based zone persistence needs zone lifecycle rules. |
| SK-76 Build Zone | Sup | Par | Blk | Blk | Blk | Blk | CG-06, CG-09 | Buildable geometry plus spawned structure graph is not surfaced. |
| SK-78 Fear | Sup | Sup | Sup | Sup | Sup | Sup | — | Fear now has canonical forced-movement steering and suppression semantics. |
| SK-79 Charge-Up Shot | Sup | Sup | Sup | Sup | Sup | Sup | — | Hold-release input mode is now canonical without widening the client intent taxonomy. |
| SK-80 Wall Bounce | Sup | Par | Blk | Par | Par | Blk | CG-14 | Projectile bounce policy is not surfaced canonically. |
| SK-81 Remote Control Summon | Sup | Blk | Blk | Blk | Blk | Blk | CG-09, CG-11 | Summon lifecycle plus remote control topology are missing. |
| SK-83 Next-Cast Empowerment | Sup | Sup | Sup | Sup | Sup | Sup | — | Consumption-window status metadata now covers next-cast overrides and one-shot spend. |
| SK-84 Temporal Trap | Sup | Sup | Sup | Sup | Sup | Sup | — | Hostile bookmarks plus delayed forced return now fit the canonical runtime-state model. |
| SK-85 Ring Geometry | Sup | Sup | Sup | Sup | Sup | Sup | — | Ring targeting is already part of the schema. |
| SK-86 Decoy | Sup | Par | Blk | Blk | Par | Blk | CG-10 | Visibility/targetability spoofing lacks canonical support. |
| SK-87 Conditional Counter | Sup | Sup | Sup | Sup | Sup | Sup | — | Damage-received consumption windows now cover one-shot stance triggers cleanly. |
| SK-88 Positional Leash | Sup | Par | Blk | Blk | Blk | Blk | CG-06 | Clamp-style policy now exists, but leash authoring still lacks a canonical surface. |
| SK-89 Respawn Anchor | Sup | Par | Blk | Blk | Par | Blk | CG-13 | Respawn anchor lifecycle and corpse/death linkage are missing. |
| SK-90 Orbital Sweep | Sup | Par | Blk | Blk | Blk | Blk | CG-06 | Attached orbiting sweep volume lacks canonical authoring. |
| SK-91 Team-Agnostic Stasis | Sup | Par | Blk | Blk | Par | Blk | CG-10 | Dormancy/untargetable observer rules are not surfaced. |
| SK-92 Anti-Heal | Sup | Sup | Sup | Sup | Sup | Sup | — | Negative stat/status layering already covers the core mechanic. |
| SK-93 Death Prevention | Sup | Sup | Par | Par | Par | Par | CG-16 | Death-floor override semantics need fuller compiler treatment. |
| SK-94 Placed Potion | Sup | Par | Blk | Par | Par | Par | CG-09 | Pickup actor lifecycle is only partially covered. |
| SK-95 Mass Effect Detonation | Sup | Sup | Sup | Sup | Sup | Sup | — | Status layering + combo matrix already cover the core pattern. |
| SK-96 Death Ghost | Sup | Par | Blk | Blk | Par | Blk | CG-13 | Death-spawned alternate form lifecycle is missing. |
| SK-97 Escalating Cost | Sup | Sup | Par | Par | Par | Par | CG-16 | Desperation cost modifiers are not fully surfaced canonically. |
| SK-98 Mobile Transport | Sup | Blk | Blk | Blk | Blk | Blk | CG-12 | Transport/container semantics are not canonicalized. |
| SK-99 Target-Tracking Zone | Sup | Par | Par | Par | Par | Par | CG-05 | Autonomous target-following zone behavior is not fully canonicalized. |

## Batch 4E — Remaining SK-100 to SK-123
| Sketch | Prim | XB | Auth | IR | Val | Overall | Gaps | Notes |
|---|---|---|---|---|---|---|---|---|
| SK-100 Ally Untargetable | Sup | Par | Blk | Blk | Par | Blk | CG-10 | Targetability override authoring is missing. |
| SK-101 Charm | Sup | Sup | Sup | Sup | Sup | Sup | — | Charm now has canonical forced-steering and control-loss semantics. |
| SK-102 Disarm | Sup | Sup | Sup | Sup | Sup | Sup | — | Disarm now has canonical attack-suppression behavior within the CC profile table. |
| SK-103 Facing-Dependent Effect | Sup | Sup | Sup | Sup | Sup | Sup | — | Facing guards are already canonical. |
| SK-104 Zone-Conditional Invuln. | Sup | Par | Blk | Blk | Par | Blk | CG-05, CG-10 | Zone-conditioned targetability override is not fully modeled. |
| SK-106 Berserk | Sup | Sup | Sup | Sup | Sup | Sup | — | Berserk now has canonical nearest-ally targeting and friendly-fire authorization semantics. |
| SK-107 Corpse Possession | Sup | Blk | Blk | Blk | Blk | Blk | CG-11, CG-13 | Corpse-targeted identity swap is not canonicalized. |
| SK-109 Movement Damage | Sup | Sup | Par | Par | Par | Par | CG-16 | Movement-scalar damage lacks end-to-end schema and validation rules. |
| SK-110 Mute | Sup | Sup | Sup | Sup | Sup | Sup | — | Mute now canonically suspends passive effects through `PASSIVES_ACTIVE`. |
| SK-111 Soulbind | Sup | Par | Blk | Blk | Blk | Blk | CG-04 | Cross-entity event cloning lacks schema and lowering contract. |
| SK-112 Deferred Resolution | Sup | Sup | Par | Par | Par | Par | CG-16 | Deferred ledger authoring is not fully canonicalized. |
| SK-113 Hit-Count Shield | Sup | Sup | Sup | Sup | Sup | Sup | — | Instance barrier is already present in the schema. |
| SK-114 Piercing Execute | Sup | Sup | Par | Par | Par | Par | CG-16 | Resolution-bypass policy needs clearer lowering support. |
| SK-115 Corpse Economy | Sup | Par | Blk | Blk | Par | Blk | CG-13 | Corpse-as-resource flows are not fully surfaced. |
| SK-116 Charge-Finisher | Sup | Sup | Sup | Sup | Sup | Sup | — | Typed shared charge pools now cover generator/spender finishers canonically. |
| SK-118 Partial CC Immunity | Sup | Sup | Sup | Sup | Sup | Sup | — | Per-category CC immunity now lowers through canonical status-immunity metadata and cast-tier sugar. |
| SK-119 Counter Window | Sup | Sup | Par | Par | Par | Par | CG-16 | Vulnerability-window broadcasting lacks full end-to-end contract. |
| SK-123 Concentration | Sup | Par | Blk | Blk | Par | Par | CG-02 | Concentration flag exists; check formula/lifecycle is not fully closed. |
