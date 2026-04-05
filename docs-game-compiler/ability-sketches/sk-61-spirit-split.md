# SK-61: Spirit Split

## Designer Intent

I split into three elemental spirits: Storm, Earth, and Fire. Each spirit is an independent entity
with its own HP and one unique ability. I control one spirit at a time and can swap between them.
When a spirit dies, it is gone. When the duration expires, or I reactivate, I reform at the
position of the spirit I am currently controlling.

## Primitive Composition

P-32 (Actor Spawning) → P-53 (Entity Suspension) → P-30 (Input Multiplexing)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)
- Swap input to rotate control between surviving spirits

## Observable Behavior

1. On activation, the original body disappears and three spirits spawn
2. Each spirit has its own HP pool and one unique spirit ability
3. The player directly controls exactly one spirit at a time
4. Inactive spirits either hold position or follow the active spirit according to the authored
   split-form profile
5. The player can rotate control across surviving spirits
6. Spirits can die independently
7. If all spirits die, the original owner dies for real
8. On expiry or manual reactivation, the original owner reforms at the chosen restore position
9. Reform HP is computed from the authored restore-HP policy, typically the sum of surviving member
   HP capped at the original max
10. Visual: three distinct elemental spirits, one active highlight, reform effect on merge

## Engine Primitives Required

Spirit Split is now the canonical `split_form` pattern, not a private instance or freeform pet-AI
 mechanic.

### Spawned Members Plus Stored Owner

The ability authors:

1. three ordinary `spawn_actor` effects, each with `count = 1` and an `output_binding`
2. one `split_form` block referencing those member bindings

When the member spawns commit, `split_form`:

1. stores and suspends the original owner body
2. opens one compiler-owned split session
3. installs one `OneToMany + AdapterRouted` multiplex group over the spawned spirits
4. chooses the first surviving member in authored order as the initial active spirit

This is not `fork_instance`. The spirits remain ordinary spatial entities in the main world.

### Control Rotation

Exactly one spirit receives direct movement and ability proposals at a time.

The swap input is the canonical `cycle_split_form` helper:

1. it resolves the live split session for the original source ability
2. picks the next surviving member in authored order
3. enqueues one Stage 1 routing mutation for the next tick

No tick ever sees two active spirits or split-brain direct input.

### Inactive Spirit Behavior

`split_form.inactive_mode` determines how non-active spirits behave.

For the intended Warcraft-style split:

- `inactive_mode = follow_active`
- authored `follow_distance`
- optional `leash_radius`

This is a bounded follow loop, not a second combat-AI system. Inactive members follow the active
spirit through ordinary authoritative-or-Ghost pose sampling.

### Reform And Death

Re-casting the same public ability while the split session is active evaluates
`reactivation_behavior`.

For this sketch:

1. `reactivation_behavior = reform_owner`
2. `restore_position = active_member_position`
3. `restore_hp_policy = sum_alive_members_cap_original_max`
4. `on_all_members_removed = kill_owner`

That yields the intended result:

- early manual reform is allowed
- duration expiry can also reform the owner
- if every spirit dies first, the stored owner snapshot is discarded and true death commits

## Cross-Boundary Concerns

Spirit Split uses the existing `P-30` coordinator model plus ordinary spawned-actor handoff.

1. Each spirit is its own ordinary spawned entity and can hand off independently.
2. If the active spirit changes or hands off, coordinator ownership follows the new active member
   at the next Stage 1 boundary.
3. Inactive follow behavior samples the active spirit's authoritative-or-Ghost pose, so follow
   motion remains bounded across seams without inventing a new remote-control AI plane.
4. Reform occurs on whichever Arbiter currently owns the selected restore position; if that restore
   point is cross-boundary, the ordinary post-restore handoff rules apply.
5. The original owner body remains suspended and absent from the world until reform or `kill_owner`.

## Compiler Requirements

Designer specifies:

- the spawned spirit member roster
- the spirit ability sets
- how inactive members behave
- whether reactivation reforms the owner
- the reform position policy
- the reform HP policy

Compiler emits:

- one `spawn_actor` per spirit member
- one `split_form` block referencing those member bindings
- optional `cycle_split_form` helper ability for swap input
- one stored-owner split session keyed to the source ability

Compiler validates:

1. `member_bindings` length is within `[2, max_multiplex_group_size]`
2. member bindings are unique
3. each binding resolves to a prior single-spawn `spawn_actor.output_binding` in the same ability
4. `follow_distance >= 0` when `inactive_mode = follow_active`
5. any authored `leash_radius > 0`
6. reformation uses canonical `reactivation_behavior`, `restore_position`, and `restore_hp_policy`
   values instead of sketch-local merge logic

## Resolved Notes

- Spirits are ordinary separate entities, so they can be healed, buffed, crowd-controlled, or
  killed independently.
- The active spirit is a routing property, not a hidden untargetability flag. Enemies can still
  target any visible spirit normally.
- Swapping control does not require spatial co-location. `cycle_split_form` rotates to the next
  surviving member through the split-session routing state.
- Early reform is the intended player-controlled exit path because `reactivation_behavior` is
  `reform_owner`.
- This sketch does not transfer the original owner's external bindings, containment state, or other
  relationships onto a special composite actor. The original body is suspended until the split
  session ends.
- Spirit Split no longer uses the instance-forking primitive. The canonical decomposition is spawned
  members plus stored-owner suspension plus routed one-to-many control.
