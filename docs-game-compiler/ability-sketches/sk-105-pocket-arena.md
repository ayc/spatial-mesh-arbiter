# SK-105: Pocket Arena

## Designer Intent

I drag a target enemy into a shadow realm: a private 1v1 arena where only the two of us exist. For
7 seconds, no other players can see us, help us, or interfere. We fight alone. After 7 seconds, or
if one of us dies first, the survivor returns to the main world at the stored parent-world
position.

## Primitive Composition

P-56 (Spatial Instance Forking) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity
- Arena duration (`420` ticks)

## Observable Behavior

1. Cast on an enemy and open a private 1v1 instance containing only the caster and target
2. Both entities disappear from the parent world for the duration
3. Inside the arena, the two entities fight normally against each other
4. Other players cannot see, target, heal, buff, or otherwise interact with either member while the
   instance is active
5. Status effects, cooldowns, and ordinary combat state persist into the arena because the same
   entities continue simulating there
6. After 7 seconds, surviving members return to their stored parent-world positions
7. If one member dies first, the survivor returns immediately and the dead member continues through
   the normal death flow
8. Visual: entry flash, private arena environment, return flash on exit

## Engine Primitives Required

Pocket Arena is now the canonical `fork_instance` pattern, not a request for a separate mini-Arbiter
feature.

### Single-Host Spatial Instance

The compiler lowers the mechanic to one `fork_instance` effect with:

1. `members = [caster, target]`
2. `duration_ticks = 420`
3. optional `output_binding` if later effects need to reference the instance ID

The current Arbiter is the instance host. The instance is a secondary private R-tree on that host,
not a new Arbiter process. Authority stays on the host Arbiter for the full live instance.

### Remote Admission Before The Instance Starts

If the target is currently authoritative on another Arbiter, the engine uses the canonical
controller-coordinated pre-instance transfer:

1. validate the target may leave its current parent-world context
2. record the target's current parent-world exit position
3. remove the target from the source parent R-tree
4. transfer authoritative state directly to the host instance

The instance starts only after the full member set is admitted. Once live, all members are local to
the host and the instance is not cross-Arbiter state.

### Isolation Semantics

While the instance is active:

1. member spatial queries resolve only against the instance R-tree
2. parent-world entities cannot query or target instance members
3. instance members cannot query or affect parent-world entities
4. downstream payloads for the involved players include only the instance-local view

This gives the intended "private duel" behavior without inventing a parallel combat system. The
same entities continue ticking; only their spatial context changes.

### Exit And Return

`fork_instance` automatically stores each member's parent-world exit position at entry time.

On expiry or explicit early exit:

1. surviving members are removed from the instance R-tree
2. they are re-inserted into the host Arbiter's parent R-tree at the stored parent-world positions
3. if a stored return point is no longer owned by the host, the normal handoff protocol begins
   immediately after exit commit

If one member dies inside the arena, that member follows the normal death, corpse, and respawn
contracts. The surviving member returns to the stored parent-world position with current HP, buffs,
debuffs, and cooldowns intact.

## Cross-Boundary Concerns

Pocket Arena is cross-boundary only at admission and return time.

1. If both members are already on the current Arbiter, the instance opens locally.
2. If one member is remote, pre-instance transfer admits that remote member to the host before the
   arena begins.
3. Once live, the instance remains single-host. It does not split across Arbiters.
4. If parent-world topology changes while the arena is active, the stored exit positions are still
   used on exit; any needed post-exit handoff runs through the normal spatial authority protocol.
5. Instance members do not participate in ordinary parent-world handoff while the instance is live.
   The instance must end before they return to normal world routing.

## Compiler Requirements

Designer specifies:

- the member set, usually `[caster, target]`
- arena duration
- any instance-scoped follow-up effects tied to the created instance ID

Compiler emits:

- one `fork_instance` directive
- the bounded member list for admission into the instance
- any optional timer or death-driven follow-up that ends the duel early and returns the survivor

Compiler validates:

1. `members` is non-empty
2. `duration_ticks > 0`
3. all instance members are valid entity refs at the point of lowering
4. the sketch uses canonical `fork_instance` exit semantics rather than sketch-local spatial
   extraction logic

## Resolved Notes

- Status effects and cooldowns continue inside the arena because the same entities keep simulating;
  the arena changes spatial context, not entity identity.
- Main-world allies cannot dispel, heal, or otherwise interact with arena members because the
  members are absent from the parent R-tree and from parent-world downstream payloads.
- Only the authored `members` enter. Minions, summons, or linked actors remain outside unless the
  game explicitly includes them in the member set.
- This sketch assumes arena combat is local to the instance. Mesh-wide or main-world-scoped effects
  are outside the intended duel profile and are not part of this reference mechanic.
- The arena shares the host Arbiter's ordinary simulation environment, including any active KiDi on
  that host. This sketch does not introduce a separate instance-local dilation regime.
- This sketch no longer requires new `docs-core` work. `fork_instance` plus pre-instance remote
  admission and stored parent-world return positions already cover the mechanic canonically.
