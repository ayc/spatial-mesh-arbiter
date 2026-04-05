# SK-111: Soulbind

## Designer Intent

I link two enemy heroes together with dark magic for 8 seconds. Any single-target ability that hits one of them ALSO hits the other. Stun one → both stunned. Silence one → both silenced. The link doubles the impact of every targeted ability against the pair.

## Primitive Composition

P-34 (Persistent Linkage) → P-60 (Event Cloning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- First target: enemy hero (hit by the ability)
- Second target: nearest enemy hero within range of the first (auto-selected)

## Observable Behavior

1. Cast hits first enemy — dark tether links them to the nearest other enemy hero
2. For 8 seconds: any single-target ability that hits either linked enemy also hits the other
3. Stun on A → B is also stunned (same duration)
4. Damage ability on A → B also takes the damage (same amount, using same CombatContext)
5. Heal reduction on A → B also gets heal reduction
6. AoE abilities are NOT duplicated (only single-target)
7. The link is one-way per ability: ability hits A, duplicates to B. It does NOT bounce back (no infinite loop)
8. Both entities can be linked for the full duration — breaking LOS doesn't break the link
9. Visual: dark chain connecting both enemies, mirrored effect visuals on both

## Engine Primitives Required

Soulbind is now a canonical target-to-target `link` pattern with event cloning.

The recommended lowering is:

1. admit the first target as an ordinary hostile `single_target`
2. run one bounded nearest-neighbor helper query around that first target to resolve
   `second_target`
3. emit one generated symmetric link:
   - `link(source_entity = target, target = { binding: second_target }, duration_ticks = 480,`
     `symmetric = true, is_cleansable = true,`
     `event_clone = {`
     `scope = single_target_only,`
     `clone_damage = true,`
     `clone_healing = true,`
     `clone_status = true,`
     `prevent_reclone = true`
     `})`

The important point is that Soulbind is not a special replay subsystem. It is an ordinary symmetric
`P-34` binding between two resolved non-caster endpoints, and the replay behavior comes from the
already-canonical `event_clone` policy on that binding.

When a qualifying single-target event later resolves on either endpoint, the struck endpoint's
owner clones the ORIGINAL event envelope onto the partner. The cloned branch is a NEW resolution
against the partner's own state, so damage, CC, healing, cleanse admission, and other downstream
checks all run on the partner normally.

## Cross-Boundary Concerns

Soulbind follows the ordinary cross-Arbiter binding / event-clone contract.

1. The initial second-target helper query may resolve through local-or-Ghost data, but the final
   binding is committed only on the authoritative owners of the two resolved targets.
2. Once the symmetric binding exists, each endpoint's owner carries the local half of the binding
   as ordinary SoftState. Handoffs move that state like any other authoritative entity state.
3. If a qualifying single-target event resolves on endpoint A while endpoint B is remote, A's owner
   emits the cloned original event envelope toward B's owner.
4. B's owner resolves that cloned branch against B's own defenses, immunities, and later hooks.
5. The cloned branch carries the binding's anti-recursion tag, so it cannot bounce back through the
   same Soulbind pair and create a replay loop.

## Compiler Requirements

Designer specifies:

- first hostile target
- partner-search radius / filter for the second target
- link duration
- whether the binding is cleansable
- which event classes clone (for this reference: damage, healing, and status)

Compiler emits:

- one root single-target admit
- one deterministic nearest-neighbor helper query around the first target to produce
  `second_target`
- one symmetric `link` between the two resolved enemy targets using
  `source_entity = target`
- one `event_clone` payload restricted to `single_target_only`
- anti-recursion tagging on cloned branches through `prevent_reclone = true`

Compiler validates:

1. the second target exists and is distinct from the first target, otherwise the cast fails
   cleanly with no binding committed
2. `event_clone.prevent_reclone = true`
3. the link is expressed through canonical `link` / `event_clone` authoring rather than a bespoke
   "replay last ability" subsystem
4. the duplication scope remains `single_target_only`; AoE and self-targeted effects are not
   replayed by this sketch

## Resolved Interaction Notes

- The cloned branch uses the original event envelope from the original caster / source branch; it
  does not re-roll offense. The partner still resolves that branch against the partner's OWN
  defenses, immunities, and damage-prevention rules.
- Beneficial single-target effects clone too in this reference, because `event_clone` is authored
  for damage, healing, and status without a hostility restriction.
- The replayed branch may trigger ordinary downstream hooks on the partner, but it cannot clone
  again through the same Soulbind binding because the originating `binding_id` and anti-recursion
  flag are part of the canonical event-clone contract.
- The link is cleansable. Cleanse, expiry, or removal of either endpoint removes both directions
  atomically because the binding is one logical symmetric pair.
- Soulbind does not retarget when one endpoint dies. The binding simply breaks; it does not hop to
  a new nearby enemy.
