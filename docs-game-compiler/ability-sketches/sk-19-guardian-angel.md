# SK-19: Guardian Angel

## Designer Intent

I mark an ally for 5 seconds. During this time, 50% of all damage they would take is redirected to
me instead. I take the redirected damage using my own defensive stats.

## Primitive Composition

P-34 (Persistent Linkage) → P-20 (Damage Redirection)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the guardian)
- Target ally entity (the ward)

## Observable Behavior

1. Cast on an ally; a visible mark/link appears for 5 seconds.
2. While active, incoming damage on the ward is split before mitigation.
3. The ward keeps the unredirected 50% and resolves it through their own defenses.
4. The guardian receives the redirected 50% as a fresh damage branch and resolves it through the
   guardian's own shields, block, mitigation, and death-prevention rules.
5. If the guardian dies or is otherwise removed, the mark breaks immediately and future damage is no
   longer redirected.
6. The mark can be dispelled/cleansed if the game allows ordinary positive-link removal.
7. Visual: a golden link between guardian and ward, flashing on each redirect.

## Engine Primitives Required

Guardian Angel is now a canonical asymmetric `link` reference with one-way `damage_redirect`.

The recommended lowering is:

```yaml
type: link
target: target
duration_ticks: 300
symmetric: false
is_cleansable: true
damage_redirect:
  ratio: 0.50
  direction: target_to_source
  max_hops: 1
```

This keeps the mechanic inside the existing linkage surface:

- the mark is one `P-34` binding from ward to guardian, not a separate shield/ward actor
- the split is canonical pre-mitigation `damage_redirect`
- the guardian share is a fresh combat branch, so the guardian's own defenses resolve it
- guardian death/removal breaks the binding automatically through the normal source-removal rule

## Cross-Boundary Concerns

Guardian Angel uses the same target-owner redirect model as the broader `link` contract.

1. The ward's current owner evaluates the binding at Stage 8 when the ward takes damage.
2. That owner splits the PRE-mitigation packet into the ward's remainder and one redirected sibling
   branch for the guardian.
3. If the guardian is remote, the redirected branch relays to the guardian's current owner for
   ordinary shield/block/mitigation/death-prevention resolution there.
4. If the guardian dies from redirected damage, the source-removal rule breaks the binding before
   later same-tick consumers observe it; future hits no longer redirect.
5. This reference keeps `max_hops = 1`, so redirected damage cannot continue chaining through
   later Guardian-style redirects.

## Compiler Requirements

Designer specifies:

- ally target filter and cast range
- mark duration
- redirect ratio
- whether the binding is cleansable
- any presentation/FX for the visible guardian link

Compiler emits:

- one asymmetric `link` from the guardian (`source_entity = caster`) to the ward
- one `damage_redirect` payload with `direction = target_to_source`
- the ordinary source-removal break rule

Compiler validates:

1. `duration_ticks > 0`
2. `damage_redirect.ratio` is in `(0, 1]`
3. `damage_redirect.max_hops = 1` for this bounded protective reference
4. the sketch is expressed as an asymmetric `link`, not as a bespoke Phase 2 interception
   subsystem

## Resolved Interaction Notes

- The redirect split is PRE-mitigation. Relative defenses therefore change how much final damage
  each side actually suffers after the split.
- The ward's own shields and mitigation apply only to the ward remainder. The guardian's shields and
  mitigation apply only to the redirected branch.
- Because the guardian share is a fresh combat branch, guardian-side `on_block`,
  `on_damage_received`, shield hooks, and death-prevention behavior may trigger normally.
- This sketch is intentionally one-directional. It does not mirror healing and does not share damage
  both ways; symmetric sharing remains `SK-04 Tether`.
- If the game wants one-mark-per-guardian or one-mark-per-ward limits, those are separate design
  restrictions, not part of the baseline compiler contract.
