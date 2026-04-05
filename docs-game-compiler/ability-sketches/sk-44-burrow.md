# SK-44: Burrow

## Designer Intent

I burrow underground for 2 seconds. While burrowed, I am invulnerable (take no damage), untargetable (cannot be selected by any ability), and unable to act. I heal rapidly while underground. I can reactivate early to emerge before the 2 seconds are up.

## Primitive Composition

P-27 (Targetability Overrides) → P-33 (Entity Dormancy)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)
- Optional reactivation to emerge early

## Observable Behavior

1. Activate — caster burrows underground instantly
2. While burrowed: caster is invulnerable (all incoming damage is negated)
3. While burrowed: caster is untargetable (cannot be selected as a target by any ability — friendly or hostile)
4. While burrowed: caster cannot move, attack, or cast
5. While burrowed: caster heals for X HP per second
6. After 2 seconds (or on reactivation): caster emerges at the same position
7. All previously applied debuffs continue ticking but deal no damage (invulnerable) — or are they paused?
8. Visual: caster sinks into the ground, dirt mound visible, emerges with a burst

## Engine Primitives Required

Burrow is now a canonical self-status plus early-reactivation reference.

The recommended lowering is:

1. the public Burrow ability writes one bounded runtime-state marker such as
   `burrow_window = bookmark(position)` and applies one positive `burrowed` status for 120 ticks
2. `burrowed` authors:
   - capability suppression for movement / attacks / casts / items
   - `targetability_policy = {`
     `hostile_effects = false,`
     `allied_beneficial_effects = false,`
     `allied_harmful_effects = false,`
     `self_effects = true,`
     `affected_by_area_effects = false,`
     `collidable_for_skillshots = false,`
     `collidable_for_pathing = false`
     `}`
   - `suspension = {`
     `mode = dormant,`
     `invulnerable = true,`
     `pause_status_timers = false,`
     `pause_ability_cooldowns = false,`
     `exclude_from_payloads = false`
     `}`
   - `periodic_effects = { interval_ticks = ... , effects = [apply_heal(target = caster, amount = ...)] }`
3. `ActivationModes` on the same public ability key redirect to one hidden `Emerge` variant while
   `state_present(burrow_window)` is true
4. that hidden `Emerge` variant clears the runtime-state marker and removes the `burrowed` status
   early through the bounded `remove_status` helper

This keeps the mechanic inside current canonical surfaces:

- relation-scoped target denial handles untargetability / AoE / skillshot admission
- `suspension.mode = dormant` plus `invulnerable = true` handles the "cannot act, cannot be hurt"
  part
- the heal is an ordinary self-heal periodic payload
- early emerge is just activation-mode redirection while the burrow marker is present

## Cross-Boundary Concerns

Burrow follows the ordinary targetability/suspension overlay rules.

1. The burrowed entity stays on its current owner because it does not move.
2. The effective targetability overlay is part of the entity's authoritative state and therefore
   propagates through the same Ghost/filter path as other targetability and observer metadata.
   Neighboring Arbiters already need those flags for seam-local AoE, skillshot, and collision
   admission.
3. Because the overlay sets `affected_by_area_effects = false`,
   `collidable_for_skillshots = false`, and `collidable_for_pathing = false`, neighbors skip the
   burrowed entity for local overlap, impact, and pathing checks instead of relaying doomed hits.
4. Early emerge and natural expiry both clear the same local status/state pair on the burrowed
   entity's owner; there is no special boundary case beyond ordinary downstream state publication.

## Compiler Requirements

Designer specifies:

- burrow duration
- self-heal cadence / amount
- whether the burrowed body remains visible to enemies/allies
- whether status timers or cooldowns pause
- whether early reactivation is allowed

Compiler emits:

- one positive `burrowed` status with targetability denial, `suspension.mode = dormant`,
  `invulnerable = true`, and periodic self-heal
- one runtime-state presence marker for reactivation gating
- one hidden early-emerge activation variant that clears the marker and removes the status

Compiler validates:

1. burrow is self-only
2. `duration_ticks > 0`
3. the active burrow overlay denies hostile, allied, and area-based admission while leaving
   `self_effects = true` so the self-heal still resolves
4. early reactivation is expressed through `ActivationModes` plus bounded state presence, not a
   bespoke second input plane
5. timer pause behavior is explicit; this reference leaves status timers and cooldowns running

## Resolved Interaction Notes

- Existing debuffs and cooldowns continue ticking in this reference because the burrowed status does
  not pause them. DoTs remain active but deal no damage while invulnerability is in force.
- The burrowed entity is skipped by hostile AoE, skillshots, and pathing/collision checks, so
  Toss-, Vortex-, and projectile-style interactions do not move or hit it while the burrow status
  is active.
- Burrow can dodge an already-in-flight projectile if the projectile resolves after the targetability
  overlay has become active; the projectile simply no longer admits the burrowed body for impact.
- The self-heal is ordinary healing and therefore participates in canonical heal-side consumers if
  some other link/mirror effect is still valid; the burrow contract itself does not special-case
  healing semantics.
- This reference keeps the burrowed body visible downstream as a mound/presence marker by leaving
  `exclude_from_payloads = false`; hiding it further would be an additional observer-presentation
  choice, not part of the base burrow contract.
- Burrow does not automatically break existing links. If some other mechanic wants links to break on
  burrow, that must come from the authored link policy rather than from targetability denial alone.
