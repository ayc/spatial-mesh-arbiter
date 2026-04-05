# SK-108: Mana Burn

## Designer Intent

My auto-attacks destroy the target's mana. For each point of mana destroyed, the target also takes bonus magical damage. This lets me shut down mana-reliant enemies by draining their resource pool while simultaneously dealing damage.

## Primitive Composition

P-35 (On-Hit Hook) → P-49 (Resource Destruction-to-Damage)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Attacker entity (passive on auto-attacks)
- Target enemy entity

## Observable Behavior

1. Auto-attack hits target
2. Destroy X mana from the target's mana pool (e.g., 28 mana per hit)
3. If target has less mana than X: destroy all remaining mana
4. Deal bonus damage equal to the mana actually destroyed (28 mana burned = 28 bonus damage)
5. Bonus damage is in addition to normal auto-attack damage
6. If target has 0 mana: no mana is burned, no bonus damage from the burn
7. Visual: mana drain effect, blue energy pulled from target

## Engine Primitives Required

Mana Burn is the canonical `P-35 (On-Hit Hook) -> P-49 (Resource Destruction-to-Damage)` pattern.

The sketch does not require a bespoke "mana combat" primitive. It lowers to:

1. a passive `TriggerDefinition { hook = on_hit }`
2. whose effect list contains `resource_burn`
3. with `pool_id = mana`, authored `amount`, authored `damage_ratio`, and `grant_to_caster = false`

Because `on_hit` is a Stage 9 PostDamage hook, the burn payload is deferred to the NEXT tick's
Stage 7 under the compiler's normal deferred-execution rule. The base weapon hit resolves first;
the follow-up burn then:

1. reads the target's current authoritative mana pool
2. computes `actual_destroyed = min(authored amount, current mana)`
3. subtracts that amount from the pool
4. derives bonus damage as `actual_destroyed * damage_ratio`
5. feeds that bonus damage back through ordinary HP damage resolution

This already covers the important secondary-resource rule: the target owner, not the attacker,
performs the authoritative pool read and floor-at-zero behavior. Mana Burn is therefore just one
authored use of the generic `resource_burn` surface. A true mana-drain variant would use the same
target-side read plus `grant_to_caster = true`.

## Cross-Boundary Concerns

Mana Burn follows the canonical `CG-01` target-side-read rule.

If the struck target is remote/Ghost:

1. the base auto-attack already resolves through the ordinary prepared-hit relay path
2. once that hit is admitted, the `on_hit` hook schedules the Mana Burn follow-up
3. the follow-up relay carries only the authored burn parameters, not a guessed destroyed amount
4. the target owner reads current mana, computes `actual_destroyed`, mutates the pool, derives the
   bonus damage, and resolves that damage locally

So the authoritative statement is: the attacker never decides how much mana was actually burned on a
remote target. It only supplies `pool_id`, `amount`, `damage_ratio`, and the already-committed hit
context. Any returned "you burned 17 mana" number is observational data sent back after the target
owner commits the result.

## Compiler Requirements

Designer specifies:

- a passive trigger on admitted weapon/attack hits
- target resource pool (`mana`)
- amount destroyed per proc
- bonus damage ratio per destroyed resource point
- bonus damage type

Compiler emits:

- a Stage 9 `on_hit` trigger
- a deferred follow-up combat payload containing `resource_burn`
- target-side `P-49` lowering using the named pool, amount, ratio, and `grant_to_caster = false`

Compiler validates:

1. the trigger is authored as a reactive `on_hit` rule rather than as inline same-tick damage math
2. `pool_id` references a valid resource pool
3. `amount`, `damage_ratio`, and `damage_type` are present
4. the effect is modeled as target-side resource destruction, not as origin-side guessed bonus damage

## Resolved Interaction Notes

- Mana Burn is not inline with the base hit. The admitted auto-attack resolves first, then the
  `on_hit` hook schedules the burn follow-up through the compiler's deferred PostDamage contract.
- The mana destruction itself is authoritative on the target owner. The attacker never computes the
  real burned amount for a remote target.
- The bonus HP damage still goes through ordinary damage resolution after the resource mutation, so
  shields, mitigation, reflection, and other downstream HP-side rules apply to that bonus packet
  exactly as they would for any other damage event.
- Mana Burn is resource manipulation, not crowd control. CC immunity / Unstoppable-style status
  admission rules do not apply to it.
- `resource_burn` is a general compiler surface, so the same mechanic can be authored on active
  abilities too; this sketch simply attaches it to `on_hit`.
