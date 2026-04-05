# SK-121: Downed State

## Designer Intent

When my HP reaches 0, I do not die immediately. Instead, I enter a Downed State: I collapse to
the ground with a smaller HP pool and a restricted four-ability bar. I can crawl slowly and try to
fight back. Teammates can rally me with a channel, enemies can finish me with a shorter channel,
and if I score a kill while downed I self-rally automatically. If my downed HP reaches 0, I truly
die.

## Primitive Composition

P-39 (On-Death Hook) → P-25 (Multi-Phase Vitals) → P-31 (Identity/Loadout Swap) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Entity reaches 0 HP (automatic transition)
- Downed abilities (4 new limited abilities)
- Ally interaction: channel to rally (revive)
- Enemy interaction: channel to finish (execute)

## Observable Behavior

1. Main HP reaches 0 and the entity enters Downed instead of dying
2. Downed has its own HP pool, typically 30% of base max HP
3. While downed, the entity crawls slowly at 25% movement speed
4. While downed, the ordinary ability bar is replaced with the authored downed ability set
5. Allies can channel on the downed target for 3 seconds to rally them back to 25% HP
6. Enemies can channel on the downed target for 2 seconds to finish them immediately
7. If the downed entity scores a kill while still downed, it self-rallies automatically
8. If downed HP reaches 0 before rally succeeds, true death commits and the normal death flow begins
9. On rally, the entity returns to standing with partial HP and regains its normal ability bar
10. Visual: character on the ground, crawling animation, rally and finish progress bars

## Engine Primitives Required

Downed State is now a canonical `P-25` intermediate life phase, not a pending docs-core change.

### Downed Is A Non-Terminal Intermediate Phase

The mechanic lowers to one `downed_state` entity definition block with:

1. `downed_hp_ratio`
2. `downed_ability_set`
3. `downed_movement_speed_ratio`
4. `rally_hp_ratio`
5. `rally_channel_ticks`
6. `finish_channel_ticks`
7. optional `self_rally_on_kill = true`

Stage 10 behavior is:

1. lethal damage on `Active` transitions the entity into the downed phase instead of terminal death
2. the engine sets the phase HP pool from `downed_hp_ratio`
3. on the next tick, the downed ability set and phase movement and capability overrides become
   active
4. while downed, incoming damage is routed to `phase_hp`
5. only when the downed phase reaches terminal death does the entity leave the intermediate phase
   and enter the normal death, corpse, and respawn path

This is ordinary lifecycle behavior already formalized in
`docs-core/01-2-entity-lifecycle-contract.md`, not a sketch-specific exception.

### Downed Ability Set And Capability Profile

While downed, the entity's ordinary bar is replaced by the authored `downed_ability_set`. The
canonical profile for this sketch is:

- crawl movement at 25% of normal speed
- no items or consumables
- only the authored downed abilities are legal while the phase is active

The ability set swap is phase-owned rather than a bespoke ad hoc loadout rewrite. Normal attacks,
items, and ordinary non-downed abilities are rejected while the entity occupies the downed phase.

### Rally, Finish, And Self-Rally

Rally is the canonical `restore_phase` recovery path:

1. an ally channels on a target filtered as `ally_downed`
2. on successful completion, the ability emits
   `restore_phase { required_phase = downed, hp_ratio = 0.25 }`
3. the target returns to Active on Stage 10 with ordinary main HP restored to 25%

Finish is the hostile terminal execute path:

1. an enemy channels on a target filtered as `enemy_downed`
2. on successful completion, the finisher emits a terminal execute or kill path against the downed
   target
3. this bypasses the remaining downed HP pool and commits true death

Self-rally is phase-local Stage 10 recovery:

1. if `self_rally_on_kill = true` and the downed entity is credited with a terminal kill
2. the runtime schedules one `restore_phase` return to Active at `rally_hp_ratio`
3. multiple same-tick qualifying kills do not stack multiple restores

### Interaction With Death Prevention Mechanics

How Downed State interacts with adjacent death mechanics:

- **SK-73 Death Immunity** prevents main HP from reaching the downed transition
- **SK-93 Death Prevention** restores the entity before Stage 10 commits the downed transition
- **SK-114 Piercing Execute** bypasses `P-25` entirely and goes straight to terminal death
- **SK-96 Death Ghost** only evaluates after the downed phase reaches true terminal death

## Cross-Boundary Concerns

The downed entity remains an ordinary active entity under one Arbiter owner.

1. If the downed entity crawls across a seam, the current phase ID, phase HP, and phase config hand
   off with the entity like any other kernel-tracked lifecycle state.
2. Rally and finish are ordinary proximity and channel interactions. If the channeler and downed
   target straddle a seam, the normal authority and relay rules apply; the final `restore_phase` or
   terminal execute still commits on the downed target's owner.
3. Self-rally also resolves on the downed entity's owner during Stage 10 after the credited victim
   death commits.
4. Corpse creation and `PlayerDied` do not happen at the Active-to-Downed transition. They happen
   only if and when the downed phase reaches terminal death.

This means Downed State does not need a separate corpse or Meta-side detour. It stays entirely
inside the ordinary lifecycle contract until true death occurs.

## Compiler Requirements

Designer specifies:

- `downed_hp_ratio`
- `downed_ability_set`
- `downed_movement_speed_ratio`
- `rally_hp_ratio`
- `rally_channel_ticks`
- `finish_channel_ticks`
- optional `self_rally_on_kill`

Compiler emits:

- one entity-level `downed_state` definition
- Stage 10 lethal-HP interception into the non-terminal downed phase
- phase-specific ability-set exposure and movement and capability overrides on the next tick
- rally abilities lowered to `restore_phase`
- finish abilities lowered to a terminal execute path restricted to `enemy_downed`
- optional self-rally scheduling on credited kill while downed

Compiler validates:

1. `downed_hp_ratio` is in `(0, 1]`
2. `rally_hp_ratio` is in `(0, 1]`
3. `downed_movement_speed_ratio` is in `[0, 1]`
4. `rally_channel_ticks > 0`
5. `finish_channel_ticks > 0`
6. `downed_ability_set` is non-empty
7. rally paths target a non-active phase through `restore_phase`, not `revive_corpse`
8. finish paths that are meant to skip the remaining downed HP use an authored execute or
   terminal-kill path rather than a sketch-local death shortcut

## Resolved Notes

- Ordinary ally healing does not automatically restore downed HP in this sketch. Rally is the
  canonical recovery path unless a separate ability is explicitly authored against `ally_downed`.
- Being rallied does not grant an automatic immunity window in this sketch.
- Downed entities cannot use items or consumables here.
- Downed entities remain valid hostile targets and can still be damaged by direct hits or AoE; that
  damage is routed to the phase HP pool.
- Downed entities can still be displaced or affected by other ordinary active-entity mechanics
  unless a separate effect denies that interaction.
- Multiple allies may channel rally at once, but progress does not stack; the first successful
  rally or finish resolves and the remaining channels terminate against the changed target state.
- The downed state is optional per entity type. Player-like actors may author it; bosses or simple
  mobs may omit it entirely.
- Kinematic Dilation affects rally and finish timings like other cast and channel timers because
  they are still ordinary simulation-time abilities.
- Downed abilities use the entity's ordinary authored combat and stat context unless a specific
  downed ability overrides that behavior through its own canonical ability definition.
