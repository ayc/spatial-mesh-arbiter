# SK-36: Shadow Step

## Designer Intent

I blink to a target position instantly. For the next 3 seconds, I can reactivate the ability to
teleport back to my original position. If I don't reactivate, the bookmark expires and I stay where
I am.

## Primitive Composition

P-01 (Instant Translation) → P-05 (Historical State Buffer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position
- Same-key reactivation within 3 seconds

## Observable Behavior

1. First cast: the caster blinks instantly to the requested target position.
2. The caster's original position is bookmarked for 3 seconds.
3. While that bookmark is present, the same ability key changes into a return cast.
4. Reactivating within the window snaps the caster back to the stored origin position instantly.
5. If the window expires or the caster dies first, the bookmark is cleared and no return remains.
6. Visual: a shadow marker at the bookmarked origin and a distinct return-state presentation on the
   ability slot.

## Engine Primitives Required

Shadow Step is now a canonical bookmark-plus-reactivation reference built from one runtime state and
one activation-mode override.

The recommended lowering is:

1. define one runtime state:
   - `state_id = shadow_step_bookmark`
   - `kind = bookmark(position)`
   - `expires_after_ticks = 180`
   - `capture_topology_epoch = true`
   - `clear_on_owner_death = true`
2. base ability mode (no bookmark present):
   - `write_state(state_id = shadow_step_bookmark, capture = position, position = caster_position)`
   - one forward `P-01` blink to the requested target position
3. activation override:
   - `when = { state_present: shadow_step_bookmark }`
   - `effects = [restore_from_state(target = caster, state_id = shadow_step_bookmark,`
     `apply_position = true, position_validation = nearest_walkable),`
     `clear_state(state_id = shadow_step_bookmark)]`

This keeps the mechanic inside existing canonical surfaces:

- the stored return location is a runtime bookmark, not a bespoke status-effect payload
- same-key reactivation is the canonical `ActivationModes` surface
- both the forward and return snaps are ordinary `P-01` teleports

## Cross-Boundary Concerns

Shadow Step follows the canonical absolute-bookmark relocation rule.

1. The bookmarked origin stores absolute world coordinates plus topology epoch at the moment of the
   first cast.
2. If the return destination is now owned by another Arbiter, the reactivation resolves through the
   ordinary destination-based teleport/handoff path.
3. Current topology, not stale stored arbiter identity, decides who owns the return snap.
4. `clear_on_owner_death = true` cleanly removes the bookmark if the caster dies during the return
   window.

## Compiler Requirements

Designer specifies:

- forward blink range / targeting
- bookmark lifetime
- whether the bookmark is cleared on death
- return cast presentation

Compiler emits:

- one `bookmark(position)` runtime state
- one forward blink that writes the bookmark before the relocation
- one `ActivationModes` override gated on `state_present`
- one return `restore_from_state` plus `clear_state`

Compiler validates:

1. the referenced runtime state exists and is `bookmark(position)`
2. the bookmark lifetime is bounded
3. same-key reactivation is expressed through `ActivationModes`, not a second public ability ID
4. the return snap uses one canonical `position_validation` rule

## Resolved Interaction Notes

- Because the return is still a cast on the same public ability key, stun and silence block the
  reactivation normally.
- Root or leash-style effects block/clamp the return only if their authored status metadata applies
  to teleports; the bookmark itself does not bypass those broader movement constraints automatically.
- The bookmark is runtime state, not a normal buff/debuff entry, so generic cleanse does not remove
  it unless the game authors a separate state-clearing rule.
- The shadow marker is presentation derived from the active bookmark state; it is not a second
  attackable gameplay actor in this reference.
