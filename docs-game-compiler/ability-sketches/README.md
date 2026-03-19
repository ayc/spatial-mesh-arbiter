# Ability Sketches

Scratch space for exploring ability designs and what it takes to implement them in the engine. Each sketch describes an ability from the designer's perspective, then breaks down the engine primitives, actor chains, cross-boundary concerns, and compiler requirements needed to make it work.

These are not specs — they're test cases for validating that the compiler pipeline and engine actor model can express the kinds of abilities the game needs.

## Sketches

### Abilities
1. [SK-01: Toss](sk-01-toss.md) — Forced displacement with AoE on landing
2. [SK-02: Poison Shot](sk-02-poison-shot.md) — Ranged DoT with refresh-on-hit, drain, and stacking damage buff
3. [SK-03: Terrain Wall](sk-03-terrain-wall.md) — Temporary impassable wall that blocks movement and projectiles
4. [SK-04: Tether](sk-04-tether.md) — Persistent link sharing damage and healing, breaks at distance
5. [SK-05: Global Strike](sk-05-global-strike.md) — Channeled ability dealing damage to all enemies on the map
6. [SK-06: Summon Swarm](sk-06-summon-swarm.md) — Spawn autonomous minions with AI behavior and lifecycle
7. [SK-07: Ability Steal](sk-07-ability-steal.md) — Copy an enemy's last-used ability and cast it yourself
8. [SK-08: Aura](sk-08-aura.md) — Passive continuous AoE with enter/leave detection and debuff management

### Procs
9. [SK-09: Chain Lightning](sk-09-chain-lightning.md) — On-hit proc with recursive spatial chaining and bounce targeting
10. [SK-10: Crit Explosion](sk-10-crit-explosion.md) — On-crit proc spawning recursive AoE explosions
11. [SK-11: On-Kill Cascade](sk-11-on-kill-cascade.md) — On-kill AoE that chains through groups of enemies
12. [SK-12: Spell Echo](sk-12-spell-echo.md) — On-cast proc that replays the full ability pipeline
13. [SK-13: Counter-Strike](sk-13-counter-strike.md) — On-block defensive proc triggering an offensive counter-attack
14. [SK-14: Execute Threshold](sk-14-execute-threshold.md) — Conditional damage modifier based on target HP with cooldown reset on kill

### Support
15. [SK-15: Purify](sk-15-purify.md) — Cleanse all debuffs from an ally and grant debuff immunity
16. [SK-16: Holy Ground](sk-16-holy-ground.md) — Stationary healing zone that pulses heals to allies inside it
17. [SK-17: Sacrifice Shield](sk-17-sacrifice-shield.md) — Self-damage cost to grant an ally an absorb shield
18. [SK-18: Resurrect](sk-18-resurrect.md) — Channel to revive a dead ally at their corpse position
19. [SK-19: Guardian Angel](sk-19-guardian-angel.md) — Redirect a portion of an ally's incoming damage to yourself
20. [SK-20: Battle Cry](sk-20-battle-cry.md) — Snapshot AoE granting attack speed and movement speed to nearby allies

### Defensive Reactions
21. [SK-21: Block](sk-21-block.md) — Chance to fully negate incoming damage with diminishing returns
22. [SK-22: Damage Reflection](sk-22-damage-reflection.md) — Reflect a percentage of incoming damage back to the attacker
23. [SK-23: Thorns Aura](sk-23-thorns-aura.md) — Flat damage to melee attackers on every hit received

### Crowd Control
24. [SK-24: Stun](sk-24-stun.md) — Hard disable preventing all actions, with CC immunity after expiry
25. [SK-25: Root](sk-25-root.md) — Movement disable that allows attacking and casting
26. [SK-26: Silence](sk-26-silence.md) — Cast disable that allows movement and auto-attacks
27. [SK-27: Sleep](sk-27-sleep.md) — Long hard disable that breaks on any damage taken
28. [SK-28: Slow + DR](sk-28-slow-diminishing-returns.md) — Movement speed reduction with the diminishing returns system

### Area Zones
29. [SK-29: Blizzard](sk-29-blizzard.md) — Stationary hostile zone with pulsing damage and slow
30. [SK-30: Trail of Fire](sk-30-trail-of-fire.md) — Movement-deposited path zone with non-circular geometry
31. [SK-31: Vortex](sk-31-vortex.md) — Stationary pull zone with continuous forced movement toward center
32. [SK-32: Minefield](sk-32-minefield.md) — Invisible dormant actors with proximity-triggered detonation
33. [SK-33: Shifting Sands](sk-33-shifting-sands.md) — Autonomously moving zone that drifts across the battlefield

### Movement Abilities
34. [SK-34: Charge](sk-34-charge.md) — Self-displacement with collision capture, entity pinning, and wall impact
35. [SK-35: Blink Strike](sk-35-blink-strike.md) — Instant teleport behind a target with no traversal
36. [SK-36: Shadow Step](sk-36-shadow-step.md) — Blink with positional bookmark and optional return teleport
37. [SK-37: Time Rewind](sk-37-time-rewind.md) — Revert position and HP to 3-second-old state via ability-driven rolling buffer

### Sylvanas-Inspired
38. [SK-38: Contagion](sk-38-contagion.md) — Debuff that autonomously spreads to nearby enemies after a delay
39. [SK-39: Spectral Dash](sk-39-spectral-dash.md) — Moving projectile as a teleport destination (reactivatable)
40. [SK-40: Mind Control](sk-40-mind-control.md) — Channel that overrides enemy movement with caster's real-time steering
41. [SK-41: Detonation Arrow](sk-41-detonation-arrow.md) — Projectile with player-controlled detonation timing
42. [SK-42: Withering Fire](sk-42-withering-fire.md) — Charge-based rapid fire with auto-targeting

### Dehaka-Inspired
43. [SK-43: Drag](sk-43-drag.md) — Skillshot grab that pulls the target toward the moving caster
44. [SK-44: Burrow](sk-44-burrow.md) — Invulnerable + untargetable state with self-heal
45. [SK-45: Essence Collection](sk-45-essence-collection.md) — Death-spawned pickups, passive collection, secondary resource
46. [SK-46: Adaptation](sk-46-adaptation.md) — Damage accumulator over time window with deferred proportional heal

### Tank-Inspired (Imperius / Arthas / Johanna)
47. [SK-47: Shield Burst](sk-47-shield-burst.md) — Shield that converts remaining value to AoE damage on expiry/break
48. [SK-48: Death Coil](sk-48-death-coil.md) — Dual-mode ability: damages enemies OR heals allies based on target
49. [SK-49: Cone Strike](sk-49-cone-strike.md) — Non-circular AoE geometry (cone/fan) with direction-dependent query
50. [SK-50: Blind](sk-50-blind.md) — CC that causes auto-attacks to miss without blocking other actions
51. [SK-51: Unstoppable](sk-51-unstoppable.md) — CC immunity while still taking damage and being targetable

### Multi-Hero Inspired (Mal'Ganis / Mei / Muradin / Stitches / Tyrael)
52. [SK-52: Combo Strike](sk-52-combo-strike.md) — Multi-press ability with escalating effects per press in a combo window
53. [SK-53: HP Swap](sk-53-hp-swap.md) — Bidirectional HP percentage swap between caster and target
54. [SK-54: Entity Consumption](sk-54-entity-consumption.md) — Swallow an entity, removing them from the world, release later
55. [SK-55: Growing Projectile](sk-55-growing-projectile.md) — Projectile that grows in size and power, accumulates hit entities
56. [SK-56: Knockback Projectile](sk-56-knockback-projectile.md) — Displaced entity becomes a projectile damaging enemies in its path
57. [SK-57: Form Transformation](sk-57-form-transformation.md) — Swap stat block and ability set temporarily, with death-triggered variant

### Tank/Warrior Inspired (Anub'arak / Blaze / Chen / Diablo / E.T.C. / Garrosh)
58. [SK-58: Cocoon](sk-58-cocoon.md) — Destructible stasis container with ally-breakable HP shell
59. [SK-59: Oil Ignite](sk-59-oil-ignite.md) — Zone with reactivatable state change (slow → fire damage)
60. [SK-60: Bunker](sk-60-bunker.md) — Enterable structure where allies are protected but can attack out
61. [SK-61: Spirit Split](sk-61-spirit-split.md) — One entity splits into three with control rotation and recombine
62. [SK-62: Boomerang](sk-62-boomerang.md) — Projectiles that reverse direction and return to caster (double-hit)
63. [SK-63: Steerable Beam](sk-63-steerable-beam.md) — Continuous line damage with real-time rotation during channel
64. [SK-64: Mosh Pit](sk-64-mosh-pit.md) — Channeled AoE where stun persists only while channel is active
65. [SK-65: Taunt](sk-65-taunt.md) — Forced auto-attack target override CC

### Specialist/Support Inspired (Abathur / Lost Vikings / Medivh / Zarya)
66. [SK-66: Symbiote](sk-66-symbiote.md) — Remote ability attachment: caster's abilities fire from an ally's position
67. [SK-67: Entity Clone](sk-67-entity-clone.md) — Duplicate an allied hero's ability set onto a temporary entity
68. [SK-68: Multi-Entity Control](sk-68-multi-entity-control.md) — One player permanently controls 3 independent entities
69. [SK-69: Portal Pair](sk-69-portal-pair.md) — Two linked placed structures offering bidirectional ally teleportation
70. [SK-70: Energy Shield](sk-70-energy-shield.md) — Shield absorption converts to offensive resource (damage feedback loop)

### Assassin/Specialist Inspired (Tracer / Zagara / Zul'jin / Orphea / Probius / Sgt. Hammer)
71. [SK-71: Sticky Bomb](sk-71-sticky-bomb.md) — Attached delayed AoE that detonates at target's future position
72. [SK-72: Nydus Network](sk-72-nydus-network.md) — N-way portal network with dynamic membership and any-to-any travel
73. [SK-73: Death Immunity](sk-73-death-immunity.md) — Cannot die for duration, takes full damage but HP floors at 1
74. [SK-74: Hit-Confirmed Dash](sk-74-hit-confirmed-dash.md) — Skillshot hit triggers automatic self-dash, miss = no dash
75. [SK-75: Self-Sustaining Zone](sk-75-self-sustaining-zone.md) — Zone persists as long as pulses hit enemies, ends on empty pulse
76. [SK-76: Build Zone](sk-76-build-zone.md) — Pylon power fields that enable turret placement, dependency graph

### Multi-Hero Sweep (Kel'Thuzad / Li-Ming / Gul'Dan / Hanzo / Junkrat / Kael'thas / Chromie / Jaina / Fenix / Genji / Nova / Cho'Gall)
77. [SK-77: Two-Player Entity](sk-77-two-player-entity.md) — Two players share one body (inverse of SK-68)
78. [SK-78: Fear](sk-78-fear.md) — CC that forces involuntary movement away from caster
79. [SK-79: Charge-Up Shot](sk-79-charge-up-shot.md) — Hold-to-charge input model with scaling damage/range
80. [SK-80: Wall Bounce](sk-80-wall-bounce.md) — Projectile that reflects off static geometry
81. [SK-81: Remote Control Summon](sk-81-remote-control-summon.md) — Player directly steers a summon's movement (WASD control)
82. [SK-82: Projectile Deflect](sk-82-projectile-deflect.md) — Catch incoming projectiles and return them to attackers
83. [SK-83: Next-Cast Empowerment](sk-83-next-cast-empowerment.md) — Buff that modifies the next ability cast (cross-ability modifier)
84. [SK-84: Temporal Trap](sk-84-temporal-trap.md) — Store enemy's position, force them back after delay
85. [SK-85: Ring Geometry](sk-85-ring-geometry.md) — Donut/ring AoE where only the circumference hits
86. [SK-86: Decoy](sk-86-decoy.md) — Illusory entity copy with per-team visual deception

### Melee/Assassin Inspired (Alarak / Butcher / Murky / Qhira / Zeratul)
87. [SK-87: Conditional Counter](sk-87-conditional-counter.md) — Defensive stance that activates only if attacked during the window
88. [SK-88: Positional Leash](sk-88-positional-leash.md) — Bounded movement area: free within radius, yanked back at the edge
89. [SK-89: Respawn Anchor](sk-89-respawn-anchor.md) — Hidden placed entity that overrides respawn location on death
90. [SK-90: Orbital Sweep](sk-90-orbital-sweep.md) — Circular orbital movement around a target entity
91. [SK-91: Team-Agnostic Stasis](sk-91-team-agnostic-stasis.md) — AoE stasis affecting ALL entities regardless of team, with timer pause

### Healer/Support Inspired (Ana / Deckard / Kharazim / Morales / Stukov / Uther / Whitemane)
92. [SK-92: Anti-Heal](sk-92-anti-heal.md) — Debuff reducing all incoming healing on the target
93. [SK-93: Death Prevention](sk-93-death-prevention.md) — Buff on ally: if they would die, prevent death and heal to full
94. [SK-94: Placed Potion](sk-94-placed-potion.md) — Healer places healing pickups, allies collect on their own timing
95. [SK-95: Mass Effect Detonation](sk-95-mass-effect-detonation.md) — One button detonates all active caster effects across all targets
96. [SK-96: Death Ghost](sk-96-death-ghost.md) — On death, persist as active ghost with healing abilities for 8 seconds
97. [SK-97: Escalating Cost](sk-97-escalating-cost.md) — Each cast increases the mana cost of the next cast (self-stacking penalty)
98. [SK-98: Mobile Transport](sk-98-mobile-transport.md) — Enterable vehicle that flies allies to a global destination

### Final HotS Batch (Artanis / Deathwing)
99. [SK-99: Target-Tracking Zone](sk-99-target-tracking-zone.md) — Hostile zone that follows a specific enemy, dealing AoE at their position
100. [SK-100: Ally-Untargetable](sk-100-ally-untargetable.md) — Permanent CC immunity + allies cannot target with beneficial effects

### League of Legends Sweep (Ahri / Amumu / Cassiopeia / Gwen)
101. [SK-101: Charm](sk-101-charm.md) — Forced walk toward caster (inverse of Fear)
102. [SK-102: Disarm](sk-102-disarm.md) — Can't auto-attack but can move and cast — new capability flag
103. [SK-103: Facing-Dependent Effect](sk-103-facing-dependent-effect.md) — CC type changes based on target's facing direction relative to caster
104. [SK-104: Zone-Conditional Invulnerability](sk-104-zone-conditional-invulnerability.md) — Invulnerable only to attacks originating from outside a zone

### League of Legends Full Roster Sweep (Mordekaiser / Renata Glasc / Viego)
105. [SK-105: Pocket Arena](sk-105-pocket-arena.md) — Remove two entities into a private 1v1 instance separate from the main world
106. [SK-106: Berserk](sk-106-berserk.md) — Force enemy to auto-attack their own allies (friendly-fire CC)
107. [SK-107: Corpse Possession](sk-107-corpse-possession.md) — Temporarily become a dead enemy, gaining their abilities and items

### Dota 2 Roster Sweep
108. [SK-108: Mana Burn](sk-108-mana-burn.md) — Attacks destroy target's mana + deal damage equal to mana destroyed
109. [SK-109: Movement Damage](sk-109-movement-damage.md) — Debuff dealing damage proportional to distance moved per tick
110. [SK-110: Mute](sk-110-mute.md) — Disable all passive abilities and item effects (new capability flag)
111. [SK-111: Soulbind](sk-111-soulbind.md) — Link two enemies: targeted abilities on one duplicate to the other
112. [SK-112: Deferred Resolution](sk-112-deferred-resolution.md) — Suppress all HP changes, accumulate in hidden ledger, apply net on expiry
113. [SK-113: Hit-Count Shield](sk-113-hit-count-shield.md) — Shield blocking N damage instances regardless of amount
114. [SK-114: Piercing Execute](sk-114-piercing-execute.md) — Kill that bypasses all death prevention, invulnerability, and shields

### Diablo Series Sweep
115. [SK-115: Corpse Economy](sk-115-corpse-economy.md) — Multi-consumer spatial resource from death, different abilities consume corpses for different effects
116. [SK-116: Charge-Finisher](sk-116-charge-finisher.md) — Cross-ability charge pool: generators build typed charges, finishers consume them for scaling effects

### Lost Ark Sweep
117. [SK-117: Stagger Bar](sk-117-stagger-bar.md) — Secondary breakable bar that triggers vulnerability state on depletion
118. [SK-118: Partial CC Immunity](sk-118-partial-cc-immunity.md) — Per-CC-type immunity flags (push immune but not stun immune)
119. [SK-119: Counter Window](sk-119-counter-window.md) — Enemy vulnerability window that rewards player timing with an ability that can counter a vulnerability window

### Guild Wars 2 Sweep
120. [SK-120: Combo Field Matrix](sk-120-combo-field-matrix.md) — Generalized field × finisher = emergent effect, cross-player combo system
121. [SK-121: Downed State](sk-121-downed-state.md) — Multi-phase HP: Full → Downed (new HP pool + abilities) → Dead, with rally/finish mechanics

### Baldur's Gate / D&D Sweep
122. [SK-122: Counterspell](sk-122-counterspell.md) — Cancel a counterspellable enemy ability mid-cast before it resolves
123. [SK-123: Concentration](sk-123-concentration.md) — Exclusive maintained effect with damage-triggered probabilistic break

### Classic MMO Sweep (EQ2 / LOTRO / Warhammer Online)
124. [SK-124: Group Sequential Combo](sk-124-group-sequential-combo.md) — Multi-player sequential state machine: different roles contribute steps in order
125. [SK-125: Group Simultaneous Input](sk-125-group-simultaneous-input.md) — All players simultaneously select options, combination determines the group effect

## Coverage Matrix

| Sketch | Trigger | Unique engine stress |
|---|---|---|
| SK-01 Toss | Active cast | Forced displacement, deferred AoE, entity trajectory |
| SK-02 Poison Shot | Active cast | DoT with conditional refresh, cross-entity drain, stacking buffs |
| SK-03 Terrain Wall | Active cast | Dynamic collision geometry, runtime pathing changes |
| SK-04 Tether | Active cast | Persistent cross-entity link, bidirectional shared effects |
| SK-05 Global Strike | Active cast | Controller fan-out, channeling state machine, mesh-wide resolution |
| SK-06 Summon Swarm | Active cast | Dynamic entity creation, AI FSM lifecycle, entity density |
| SK-07 Ability Steal | Active cast | Dynamic ability lookup, portable ability definitions, data_epoch interaction |
| SK-08 Aura | Passive | Continuous spatial query at 60Hz, enter/leave tracking, performance under density |
| SK-09 Chain Lightning | On-hit (chance) | Recursive spatial chaining with bounce targeting, proc_depth |
| SK-10 Crit Explosion | On-crit | Recursive AoE spawning, exponential cascade potential |
| SK-11 On-Kill Cascade | On-kill | Post-resolution kill trigger, recursive cascade, cross-boundary buff relay |
| SK-12 Spell Echo | On-cast | Re-entering the full ability pipeline, probability-bounded recursion |
| SK-13 Counter-Strike | On-block | Defensive proc triggering offense, reverse cross-boundary relay |
| SK-14 Execute Threshold | Conditional (HP%) | Target-state-dependent modifier, cross-boundary HP visibility, cooldown manipulation |
| SK-15 Purify | Active cast (ally) | Status effect enumeration/removal, cleanse classification, immunity window |
| SK-16 Holy Ground | Active cast (ground) | Friendly-targeted zone, heal pulses, ally spatial query |
| SK-17 Sacrifice Shield | Active cast (ally) | Self-damage cost, shield HP layer, absorption ordering |
| SK-18 Resurrect | Channel (corpse) | Dead entity targeting, death→alive state transition, entity reconstruction |
| SK-19 Guardian Angel | Active cast (ally) | Damage interception/redirect in Phase 2, one-directional cross-boundary relay |
| SK-20 Battle Cry | Active cast (self AoE) | Snapshot multi-target friendly buff, expiry management, buff stacking rules |
| SK-21 Block | Defensive (on-hit) | Phase 2 pipeline ordering, diminishing returns, short-circuit on success |
| SK-22 Damage Reflection | Defensive (on-hit) | Percentage-based reverse damage, pre/post mitigation calculation, loop prevention |
| SK-23 Thorns Aura | Defensive (on-melee-hit) | Flat reverse damage, melee-only filter, independent of incoming damage amount |
| SK-24 Stun | Active cast | Hard disable, capability state flags, CC immunity window |
| SK-25 Root | Active cast | Partial disable (movement only), movement-ability classification |
| SK-26 Silence | Active cast | Partial disable (casting only), channel interruption, action type classification |
| SK-27 Sleep | Active cast | Break-on-damage condition, damage check ordering with defensive layers |
| SK-28 Slow + DR | Active cast | Diminishing returns system, CC history tracking, effectiveness reduction |
| SK-29 Blizzard | Active cast (ground) | Canonical stationary ZoneActor, pulse damage + CC, enter/leave |
| SK-30 Trail of Fire | Passive (movement) | Polyline geometry, movement-history tracking, segment lifecycle |
| SK-31 Vortex | Active cast (ground) | Continuous forced movement, per-tick velocity modification, gravity well |
| SK-32 Minefield | Active cast (ground) | Stealth/visibility, dormant actors, proximity triggers, long-lived entities |
| SK-33 Shifting Sands | Active cast (ground) | Self-propelled zone, moving geometry, zone-crosses-boundary handoff |
| SK-34 Charge | Active cast (direction) | Caster-as-projectile, entity pinning, wall impact trigger, two-entity handoff |
| SK-35 Blink Strike | Active cast (target) | Instant position snap, no traversal, derived destination, instant cross-boundary handoff |
| SK-36 Shadow Step | Active cast (reactivatable) | Positional bookmark as status effect, multi-phase ability, reverse instant handoff |
| SK-37 Time Rewind | Active cast (self) | Ability-driven rolling buffer (opt-in), historical state snapshot, HP overwrite |
| SK-38 Contagion | Active cast (target) | Autonomous delayed spreading, debuff as independent agent, cast_id dedup |
| SK-39 Spectral Dash | Active cast (reactivatable) | Moving bookmark (projectile-as-destination), caster interaction with live projectile |
| SK-40 Mind Control | Channel (target) | Real-time caster input → enemy movement, per-tick steering relay |
| SK-41 Detonation Arrow | Active cast (reactivatable) | Player-controlled projectile detonation, pass-through projectile |
| SK-42 Withering Fire | Active cast (auto-target) | Charge-based cost system, engine-side auto-targeting, rapid-fire rate limiting |
| SK-43 Drag | Skillshot (direction) | First-hit line collision, pull toward moving caster, continuous destination update |
| SK-44 Burrow | Active cast (self) | Invulnerable + untargetable entity state, targeting query exclusion, Ghost state flags |
| SK-45 Essence Collection | Passive + active (self) | Death-spawned pickup actors, proximity collection, secondary resource system |
| SK-46 Adaptation | Active cast (self) | Post-damage accumulator hook, on-expiry deferred heal, status effect lifecycle hooks |
| SK-47 Shield Burst | Active cast (self) | Shield remaining value → AoE damage, on-expiry/on-break lifecycle hooks |
| SK-48 Death Coil | Active cast (any target) | Dual-mode resolution (damage vs heal), target allegiance branching |
| SK-49 Cone Strike | Active cast (direction) | Cone/fan geometry, direction-dependent spatial query, dot-product angle check |
| SK-50 Blind | Active cast (AoE) | New CC type (auto-attacks miss), Phase 1 short-circuit, auto-attack classification |
| SK-51 Unstoppable | Active cast (self) | CC immunity entity state, separable damage/CC components, self-cleanse on activation |
| SK-52 Combo Strike | Active cast (multi-press) | Sequential combo state machine, per-step resolution branching, timeout decay |
| SK-53 HP Swap | Channel (target) | Bidirectional stat swap, atomic two-entity mutation, cross-boundary simultaneity |
| SK-54 Entity Consumption | Active cast (melee target) | Entity removal from world, state serialization/storage, deferred restoration |
| SK-55 Growing Projectile | Active cast (direction) | Dynamic projectile properties, growing collision radius, multi-entity accumulation |
| SK-56 Knockback Projectile | Active cast (melee target) | Entity-as-projectile, pass-through collision mode, remote caster damage attribution |
| SK-57 Form Transformation | Active cast (self) | Stat block swap, ability set replacement, HP scaling, death-triggered variant |
| SK-58 Cocoon | Active cast (target) | Destructible stasis container, linked lifecycle, team-inverted targeting |
| SK-59 Oil Ignite | Active cast (reactivatable) | Zone state machine (oil → fire), inter-ability ignition trigger, ability type tags |
| SK-60 Bunker | Active cast (ground) | Enterable multi-occupant structure, occupant untargetable + can attack out |
| SK-61 Spirit Split | Active cast (self) | Entity splitting into 3, control rotation, HP-summed recombine, group death check |
| SK-62 Boomerang | Active cast (radial) | Reversing projectile trajectory, return homing, per-direction hit lists |
| SK-63 Steerable Beam | Channel (direction) | Continuous line-segment damage, per-tick steering, turn-rate clamping |
| SK-64 Mosh Pit | Channel (self AoE) | Channel-bound CC zone, stun tied to channel lifecycle, enter/leave CC management |
| SK-65 Taunt | Active cast (self AoE) | Forced target override CC, proposal mutation, death-break hook |
| SK-66 Symbiote | Active cast (global ally) | Remote ability origin, persistent cross-boundary ability relay, vision redirect |
| SK-67 Entity Clone | Active cast (ally) | Runtime ability set copying, dynamic entity creation from template, control transfer |
| SK-68 Multi-Entity Control | Permanent (game mode) | One session → 3 entities, simultaneous multi-Arbiter control, per-entity lifecycle |
| SK-69 Portal Pair | Active cast (two-phase ground) | Linked placed structures, bidirectional instant teleportation, cross-boundary portal use |
| SK-70 Energy Shield | Active cast (self/ally) | Shield absorption → offensive resource, cross-entity resource credit, decay + feedback loop |
| SK-71 Sticky Bomb | Active cast (target) | Entity-attached delayed AoE, detonation at future position, moves with carrier |
| SK-72 Nydus Network | Active cast (ground, repeatable) | N-way portal network, dynamic membership, any-to-any routing, destination selection UI |
| SK-73 Death Immunity | Active cast (self) | HP floor at 1, takes full damage but cannot die, new entity state |
| SK-74 Hit-Confirmed Dash | Skillshot (direction) | Outcome-dependent ability resolution, conditional self-dash on hit, branching cooldowns |
| SK-75 Self-Sustaining Zone | Active cast (ground) | Conditional zone lifecycle (no fixed timer), persists while hitting, ends on miss |
| SK-76 Build Zone | Active cast (ground) | Spatial placement prerequisite, inter-entity dependency graph, pylon→turret power field |
| SK-77 Two-Player Entity | Permanent (game mode) | Two sessions → one entity, input multiplexing, shared HP with split abilities |
| SK-78 Fear | Active cast (self AoE) | Forced flee movement away from source, new CC type |
| SK-79 Charge-Up Shot | Hold-release input | Hold-to-charge input model, scaling damage/range with charge duration |
| SK-80 Wall Bounce | Active cast (direction) | Projectile reflects off static geometry, multi-segment raycast per tick |
| SK-81 Remote Control Summon | Active cast (spawn + steer) | Player WASD controls a summon's movement, caster immobile during |
| SK-82 Projectile Deflect | Active cast (self) | Catch + return projectile entities, projectile vs non-projectile classification |
| SK-83 Next-Cast Empowerment | Active cast (self buff) | Cross-ability modifier buff, per-ability enhancement definitions, consumed on next cast |
| SK-84 Temporal Trap | Active cast (target) | Hostile positional bookmark, forced enemy teleport after delay, stale position handling |
| SK-85 Ring Geometry | Active cast (ground) | Ring/donut AoE shape, inner safe zone, two-radius spatial query |
| SK-86 Decoy | Active cast (self) | Illusory entity, per-team visual deception, fake HP bar, targeting confusion |
| SK-87 Conditional Counter | Active cast (self) | Window-gated activation (if hit → counter), damage-received callback on status effect |
| SK-88 Positional Leash | Active cast (melee target) | Bounded movement area, position clamping in kinematics, constrains all movement types |
| SK-89 Respawn Anchor | Active cast (ground) | Death lifecycle override, hidden entity, respawn position/timer modification |
| SK-90 Orbital Sweep | Active cast (target) | Circular derived position around target, arc-sweep collision, anchor-following orbit |
| SK-91 Team-Agnostic Stasis | Active cast (ground) | TargetFilter::All (both teams), stasis with timer pause, per-entity time freeze |
| SK-92 Anti-Heal | Active cast (ground AoE) | Heal resolution modifier, healing reduction/amplification debuff, affects all heal sources |
| SK-93 Death Prevention | Active cast (ally) | Death check interception, conditional full heal on lethal damage, one-time consumption |
| SK-94 Placed Potion | Active cast (ground) | Friendly consumable pickup, healer/recipient agency split, per-caster instance limit |
| SK-95 Mass Effect Detonation | Active cast (global self) | Caster effect registry query, simultaneous multi-target detonation, fan-out relay |
| SK-96 Death Ghost | Passive (on death) | Post-death active phase, dead-but-present entity state, limited abilities while dead |
| SK-97 Escalating Cost | Cost modifier | Self-stacking cost inflation, exponential mana cost growth, stack decay timer |
| SK-98 Mobile Transport | Active cast (global) | Moving enterable vehicle, multi-boundary traversal, occupant storage during flight |
| SK-99 Target-Tracking Zone | Active cast (target) | Zone follows enemy entity, speed-limited tracking, collateral AoE at zone position |
| SK-100 Ally-Untargetable | Permanent (trait) | Per-team targeting flags, allies cannot target/heal/buff, enemies target normally |
| SK-101 Charm | Active cast (target) | Forced walk toward caster, dynamic direction tracking, inverse of Fear |
| SK-102 Disarm | Active cast (AoE) | Can't auto-attack / can move+cast, new capability suppression flag |
| SK-103 Facing-Dependent Effect | Active cast (cone) | Target facing angle determines CC type, entity facing as authoritative property |
| SK-104 Zone-Conditional Invulnerability | Active cast (self zone) | Attacker-position-dependent damage negation, spatial check during damage resolution |
| SK-105 Pocket Arena | Active cast (target) | Separate spatial instance, entity extraction/return, private 1v1 simulation context |
| SK-106 Berserk | Active cast (AoE) | Forced friendly-fire, team allegiance inversion for targeting, damage exception for same-team |
| SK-107 Corpse Possession | Interact (dead enemy) | Dead entity data persistence, ability/stat loading from corpse, model/identity swap |
| SK-108 Mana Burn | Passive (on-hit) | Resource-targeting combat, mana destruction + mana-to-damage conversion |
| SK-109 Movement Damage | Active cast (target) | Per-tick displacement tracking, distance-to-damage conversion, all movement types trigger |
| SK-110 Mute | Active cast (target) | Passive/item effect suppression, new capability flag, passive/active classification |
| SK-111 Soulbind | Active cast (two targets) | Targeted ability duplication on linked entities, resolution replay, loop prevention |
| SK-112 Deferred Resolution | Active cast (ally) | HP change suppression + hidden ledger, net damage/healing applied on expiry |
| SK-113 Hit-Count Shield | Active cast (self) | Charge-based damage blocking (count not amount), new shield type, DoT counterplay |
| SK-114 Piercing Execute | Active cast (melee) | Death pipeline bypass flag, kills through all protection, conditional cooldown reset |
| SK-115 Corpse Economy | Passive (death trigger) + active (consume) | Multi-consumer spatial resource, corpse data as ability input, contention resolution |
| SK-116 Charge-Finisher | Active cast (generators + spenders) | Shared cross-ability charge pool, typed charges, composition-based finisher scaling |
| SK-117 Stagger Bar | Passive (combat system) | Secondary breakable bar, parallel stagger damage, depletion triggers vulnerability state |
| SK-118 Partial CC Immunity | Passive (during casts) | Per-CC-category immunity flags, granular CC resistance, animation-bound immunity |
| SK-119 Counter Window | Boss mechanic (PvE) | Enemy vulnerability broadcast, abilities that can counter a vulnerability window, timing-based skill check |
| SK-120 Combo Field Matrix | Systemic (cross-player) | Field type × finisher type lookup matrix, emergent combo effects, cross-player detection |
| SK-121 Downed State | Entity lifecycle | Three-phase HP (Alive → Downed → Dead), separate downed HP pool, rally/finish channels |
| SK-122 Counterspell | Reactive (during enemy cast) | Mid-cast ability cancellation, casting state detection, prevents resolution entirely |
| SK-123 Concentration | Maintained effect | Exclusive one-at-a-time maintained effect, damage-triggered probabilistic break, free action during |
| SK-124 Group Sequential Combo | Group mechanic (triggered) | Multi-player state machine, role-typed ability contributions, sequential advancement |
| SK-125 Group Simultaneous Input | Group mechanic (triggered) | Synchronous N-player input collection, combination matrix evaluation, ordered + unordered patterns |
