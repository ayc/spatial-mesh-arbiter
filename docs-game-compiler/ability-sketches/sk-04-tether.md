# SK-04: Tether

## Designer Intent

My character links to an ally. While the link is active, we share 30% of damage taken and 50% of
healing received. The tether is visible as a beam between us. If the distance between us exceeds a
threshold, the tether snaps and the effect ends.

## Primitive Composition

P-34 (Persistent Linkage) → P-04 (Positional Clamping)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Tether establishes between caster and target; a visible beam connects them.
2. While active, when either entity takes damage, 30% of that incoming packet is redirected to the
   partner.
3. While active, when either entity receives healing, 50% of the final committed heal is mirrored
   onto the partner.
4. Distance is checked continuously. If distance exceeds the break threshold, the tether snaps.
5. Tether has a maximum duration (for example 12 seconds) even if distance is maintained.
6. Either partner dying or being removed breaks the tether.
7. The tether can be dispelled/cleansed.

## Engine Primitives Required

Tether is now a canonical symmetric `link` reference with break distance, pre-mitigation damage
redirection, and post-resolution heal mirroring.

The recommended lowering is:

```yaml
type: link
target: target
duration_ticks: 720
symmetric: true
break_distance: ...
is_cleansable: true
damage_redirect:
  ratio: 0.30
  direction: both
  max_hops: 1
heal_mirror_ratio: 0.50
heal_mirror_direction: both
```

This keeps the mechanic inside the canonical linkage surface:

- the tether is one logical symmetric `P-34` binding pair, not a standalone actor
- damage sharing is canonical `damage_redirect`, which splits the original pre-mitigation packet
  into a remainder plus one redirected sibling branch
- healing share is canonical `heal_mirror_ratio`, which emits a fresh partner heal from the final
  committed heal amount
- the visible beam is presentation/state derived from the active binding, not a second gameplay
  subsystem

## Cross-Boundary Concerns

Tether follows the canonical cross-Arbiter binding contract.

1. Each endpoint's current authoritative owner carries its local half of the symmetric binding as
   ordinary SoftState.
2. `break_distance` is checked in Stage 6 after movement commits using the endpoints' current
   local-or-Ghost positions, so teleports, Toss, Charge, and handoffs can snap the link in the same
   tick.
3. `damage_redirect` is evaluated on the owner of the entity currently taking damage. If the
   partner is remote, the redirected sibling branch is relayed to the partner's owner for ordinary
   mitigation there.
4. `heal_mirror_ratio` resolves after the source heal commits. If the partner is remote, the mirror
   heal is relayed as one fresh partner-heal branch.
5. Anti-recursion metadata on redirected/mirrored branches prevents A -> B -> A ping-pong through
   the same binding.

## Compiler Requirements

Designer specifies:

- ally target filter and cast range
- tether duration
- break distance
- damage-share ratio
- healing-share ratio
- whether the binding is cleansable

Compiler emits:

- one symmetric `link`
- one `damage_redirect` payload with `direction = both`
- one `heal_mirror_ratio` payload with `direction = both`
- one break-distance rule evaluated from current committed poses

Compiler validates:

1. `duration_ticks > 0`
2. `break_distance > 0`
3. `damage_redirect.ratio` is in `(0, 1]`
4. `heal_mirror_ratio` is in `[0, 1]`
5. `damage_redirect.max_hops = 1` for this bounded share pattern
6. the mechanic is expressed through canonical `link` metadata, not a bespoke tether actor or
   status-local callback loop

## Resolved Interaction Notes

- Damage sharing is redirect, not copy. The original target keeps the unredirected remainder, while
  the partner receives a fresh redirected branch for the shared portion.
- Because the redirected branch is a new combat branch against the partner, the partner's own
  shields, mitigation, death-prevention rules, and on-damage hooks may trigger normally.
- Heal mirroring copies the final committed heal amount after the source-side heal resolves, then
  applies 50% of that result as a fresh heal on the partner.
- Toss, teleports, and other movement do not pull the partner. If post-move distance exceeds the
  authored threshold, the tether snaps through the ordinary Stage 6 break-distance check.
- This reference does not impose a one-tether-per-entity cap. If the game wants that restriction,
  it should be authored separately as a design rule or cast guard.
