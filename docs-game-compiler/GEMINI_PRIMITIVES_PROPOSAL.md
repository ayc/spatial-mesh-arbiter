# Engine Primitives Proposal

> **Adopted and extended into `ability-primitives/`.** See that directory for the canonical 65-primitive taxonomy covering all 125 sketches. This file is retained as the original working draft for reference.

**Status:** Archived — superseded by `ability-primitives/`
**Origin:** Derived from an exhaustive analysis of 107 capability sketches in `ability-sketches/`
**Purpose:** To define the "Virtual Instruction Set for Spatial Logic." Instead of hardcoding 100+ unique abilities into the Rust 60Hz loop, the engine must expose these 62 atomic primitives. The Game Compiler's job is to lower designer logic into chains of these fundamental building blocks.

---

## 1. Spatial & Kinematic Primitives (8)
*How things move and exist in space.*
1. **Instant Translation:** Teleportation without physical traversal (e.g., Blink).
2. **Forced Displacement:** Modifying velocity over time with friction/decay (e.g., Toss, Drag).
3. **Trajectory Steering:** Forcing vectors toward/away from a moving target (e.g., Homing, Fear, Charm).
4. **Positional Clamping:** Hard distance limits that zero-out or reverse velocity upon crossing a threshold (e.g., Leash, Tether).
5. **Historical State Buffer:** Opt-in rolling memory of `(x, y, tick)` over the last N seconds (e.g., Time Rewind).
6. **Attached Kinematics:** Parenting a volume/entity to another moving entity (e.g., Mobile Aura, Symbiote).
7. **Entity-as-Kinematic-Volume:** Temporarily promoting a player's hitbox to a sweeping collision projectile (e.g., Charge).
8. **Dynamic Collision Injection:** Temporarily adding/removing static geometry from the `static_grid` (e.g., Terrain Wall).

## 2. Targeting & Query Primitives (6)
*How the engine asks "who is involved?"*
9. **Shape Overlap Query:** `is_inside_with_tolerance` for Box, Circle, Cone, and Donut/Ring.
10. **Swept-Segment Raycast:** For Line-of-Sight and reflection vectors.
11. **N-Nearest Neighbor Selection:** Spatial sorting for chaining and bouncing.
12. **Facing/Dot-Product Check:** Determining if a target is looking at/away from the source.
13. **Tag/Allegiance Filtering:** Querying based on team, dead/alive state, or structural tags.
14. **Continuous Proximity Monitor:** Edge-triggered `OnEnter` and `OnLeave` events for spatial zones.

## 3. Combat Resolution Primitives (11)
*How numbers go up and down in Phase 2.*
15. **Value Modification:** Flat or percentage application of Damage/Healing.
16. **Stat Layering:** Applying additive/multiplicative modifiers to base stats.
17. **Conditional Thresholds:** "If Target HP < X" or "If Caster has Y buff."
18. **Absorption Barrier:** A secondary HP pool depleted before actual HP.
19. **Instance Barrier:** A shield that tracks *number of hits*, not damage amounts.
20. **Damage Redirection:** Siphoning X% of damage applied to Entity A over to Entity B.
21. **Value Conversion:** Converting dealt damage to healing (Lifesteal) or resource destruction to damage (Mana Burn).
22. **Deferred Ledger:** Suppressing HP changes temporarily to apply them as a net sum later.
23. **Floor Clamping:** "Cannot drop below 1 HP."
24. **Resolution Bypass:** "True execution" that ignores all immunities, shields, and floor clamps.
25. **Multi-Phase Vitals:** Allowing an entity to hit 0 HP, but transition to a secondary vital pool instead of dying (e.g., Downed State).

## 4. Entity State & Capability Primitives (9)
*How the engine limits what an entity is allowed to do.*
26. **Capability Bitmask:** Independent flags for `CAN_MOVE`, `CAN_CAST`, `CAN_ATTACK`, `CAN_USE_ITEMS` (Silence, Disarm, Mute).
27. **Targetability Overrides:** Removing an entity from spatial queries entirely (e.g., Burrow).
28. **Hostility Inversion:** Forcing friendly fire or treating allies as enemies (e.g., Berserk).
29. **Control Authority Swap:** Disconnecting the Edge Node's inputs and routing another player's inputs to the entity (e.g., Mind Control).
30. **Input Multiplexing:** Routing one player's inputs to multiple entities or multiple players to one entity.
31. **Identity/Loadout Swap:** Replacing the `OffensiveStats` and `SpellData` pointers at runtime (e.g., Form Transformation).
32. **Actor Spawning:** Instantiating logic-driven `ProjectileActors` or `ZoneActors`.
33. **Entity Dormancy:** Pausing an entity's 60Hz evaluation while preserving its state.
34. **Persistent Linkage (Bindings):** Registering a two-way dependency graph between entities that survives server handoffs.

## 5. Hook & Reactive Triggers (6)
*The Event Listener system for abilities that watch other actions.*
35. **On-Damage-Dealt / On-Hit Hook**
36. **On-Damage-Received Hook**
37. **On-Crit Hook**
38. **On-Block / On-Defend Hook**
39. **On-Death Hook**
40. **On-Cast Intercept:** Reading an intent *before* it resolves to optionally cancel or duplicate it (e.g., Counterspell).

## 6. Temporal & Accumulator Primitives (6)
*How abilities scale with time or repetition.*
41. **Diminishing Returns (DR) Tracker:** A historical registry of CC applied to reduce subsequent durations.
42. **Stacking Counters w/ Decay:** Combo points or charges that scale effects and fall off over time.
43. **Charge-Up State:** A multiplier driven by the delta between `Intent::Start` and `Intent::Release`.
44. **Pulse Timer:** An internal clock that triggers a secondary primitive on an interval.
45. **Delay Timer:** A scheduled trigger for future evaluation.
46. **Global Event Scheduler:** Escalating local logic to the Mesh Controller for deterministic map-wide execution.

## 7. Advanced Resource & Economy Primitives (5)
47. **Spatial Corpse Registry:** Tracking the location and "stat-ghost" of dead entities for consumption logic.
48. **Secondary "Stagger" Bar:** A parallel health track that accumulates "posture damage" and triggers vulnerability upon depletion.
49. **Resource Destruction-to-Damage Scalar:** A combat multiplier utilizing the delta of resources successfully destroyed.
50. **Typed Multi-Charge Pool:** An accumulator that tracks the *sequence/type* of charges (e.g., Fire-Fire-Ice) to branch finisher logic.
51. **Desperation Cost Modifiers:** Stacking multipliers on an ability's base cost that decay over time.

## 8. Advanced Visibility & UI Primitives (4)
52. **Asymmetric Team-Rendering:** A flag system making an entity invisible or differently-textured based on the observer's team (e.g., Decoys, Traps).
53. **Entity Suspension:** Removing an entity from all spatial/targeting/rendering systems while preserving its existence in memory (e.g., Swallowed).
54. **Group Choice Aggregator:** A synchronized UI window that collects inputs from N players and pattern-matches them to a result.
55. **Concentration Intercept:** A combat-pipeline hook forcing a background RNG check upon taking damage to maintain a buff.

## 9. Spatial & Instance Manipulation Primitives (4)
56. **Spatial Instance Forking:** Dynamically spawning a "Pocket Arena" (a private R-Tree node) and migrating a subset of entities into it.
57. **Polyline Collision Generator:** Building damage/collision geometry from a sequence of points (a path) rather than a static shape.
58. **Container/Vehicle Logic:** Locking N entities to a "Parent" entity's transform and suppressing their direct spatial input.
59. **N-Way Portal Network:** A registry of spatial anchors allowing any-to-any instant translation across the mesh.

## 10. Advanced Resolution Primitives (3)
60. **Event Cloning (Mirroring):** Forcing all damage/healing applied to Entity A to be immediately duplicated and applied to Entity B.
61. **Projectile Ownership Hijacking:** Dynamically swapping the `OwnerID` and `Velocity` of an active projectile (e.g., Deflect).
62. **Categorized CC Immunity:** Granular flags for "Push Immunity", "Stun Immunity", or "Interrupt Immunity" rather than a blanket "Unstoppable" flag.

---

## Example: Composition in Practice

By relying on these orthogonal primitives, complex abilities do not require custom engine logic. For example, **SK-121 (Downed State)** is not built as a monolithic "Downed System", but is instead compiled into a chain of 5 distinct primitives:

1. `[39. On-Death Hook]` (The Trigger)
2. `[23. Floor Clamping: 1 HP]` (Prevents actual entity deletion)
3. `[31. Identity/Loadout Swap]` (Changes the player's abilities to the "Downed" skill bar)
4. `[26. Capability Bitmask: CANNOT_MOVE]` (Locks the player in place)
5. `[43. Charge-Up State]` (Used for the "Rally" channel by allies)
