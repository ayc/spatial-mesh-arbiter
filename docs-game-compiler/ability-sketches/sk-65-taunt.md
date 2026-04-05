# SK-65: Taunt

## Designer Intent

I force nearby enemies' basic attacks onto me for a short window. They can still move and cast, but
their engine-owned auto-attacks no longer choose their own target.

## Primitive Composition

P-03 (Trajectory Steering) → P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No explicit target; apply in an area around the caster

## Observable Behavior

1. Enemies in the area receive taunt for 1.5 seconds.
2. While taunted, their engine-owned auto-attacks are forcibly retargeted to the taunter.
3. They may still move and may still cast ordinary abilities.
4. If the taunter dies, the taunt ends immediately.
5. If the taunted enemy is out of auto-attack range, the forced attack simply does not fire until
   they are back in range.
6. Taunt is cleansable and reduced by ordinary status resistance / tenacity.

## Engine Primitives Required

Taunt is already one of the canonical `apply_cc` behavior profiles.

1. The AoE application lowers to `apply_cc(cc_type = taunt, category = target_override, ...)`.
2. The target owner installs a generated negative taunt status that stores the source entity.
3. While that status is active, the target owner's auto-attack path replaces the requested
   auto-attack target with the taunt source as long as the source still exists.
4. Ordinary authored ability casts keep their own authored targets. Taunt only overrides the
   engine-owned basic-attack path.
5. Source death is an implicit break condition in the canonical taunt profile.

## Cross-Boundary Concerns

1. If the target is remote/Ghost when taunt is applied, the target owner receives and installs the
   taunt status through the ordinary CC relay path.
2. Later, if the taunted entity basic-attacks the taunter across an Arbiter boundary, the standard
   cross-boundary combat relay path handles the attack like any other remote target.
3. Taunter death already clears the status through the canonical source-death break policy; no
   second bespoke death-broadcast contract is needed for this sketch.

## Compiler Requirements

Designer specifies:

- AoE radius
- taunt duration
- cleansability

Compiler emits:

- one area application of `apply_cc(cc_type = taunt, category = target_override, ... )`
- the generated taunt status entry carrying source identity and canonical target-override behavior

Compiler validates:

1. `cc_type = taunt` pairs only with `target_override`
2. taunt is used only for engine-owned auto-attack retargeting, not for arbitrary ability
   redirection
3. source identity is available so source-death break works deterministically

## Resolved Interaction Notes

- Blind and taunt stack cleanly: the target is forced to attack the taunter, but the attack still
  misses while blind is active.
- Unstoppable blocks taunt admission because taunt is ordinary CC in the `target_override` category.
- Minions or projected actors that use the engine-owned basic-attack path are redirected the same
  way as players.
- Taunt does not force walking in this reference. It only overrides the attack target when the
  target chooses or attempts a basic attack.
