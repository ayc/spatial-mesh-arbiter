# SK-22: Damage Reflection

## Designer Intent

A buff or passive that reflects a percentage of incoming damage back to the attacker. When I take
100 damage and have 30% reflection, I take the full 100 but the attacker also takes 30 damage. The
reflected damage uses the attacker's own defensive stats for mitigation.

## Primitive Composition

P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Incoming damage event
- Defender's reflection percentage
- Attacker entity

## Observable Behavior

1. I take qualifying incoming damage normally.
2. After my branch resolves, reflection computes `reflected_amount = committed_damage_taken *
   reflection_ratio`.
3. One reactive reverse damage packet is emitted against the triggering attacker.
4. The attacker mitigates that reflected hit through their own shields, block, resistances, and
   later mitigation rules.
5. In this reference, the reflected packet mirrors the triggering branch's damage type.
6. Fully negated hits reflect zero because no committed damage reached the defender.
7. Visual: mirror/shimmer response on the defender and reflected damage feedback on the attacker.

## Engine Primitives Required

Damage Reflection is now a canonical passive `on_damage_received` reverse-hit reference using the
bounded trigger-local fallback surface.

The recommended lowering is:

1. apply one passive/status-owned `on_damage_received` trigger to the defender
2. when that trigger fires, read the triggering branch's committed damage amount and damage type
   from the current P-36 event context
3. emit one reactive reverse damage packet to the triggering attacker with:
   - `amount = damage_received * reflection_ratio`
   - `damage_type = triggering_damage_type`
4. carry the canonical reactive-depth safety bound on that reverse packet

This keeps the mechanic inside existing surfaces:

- the percentage scales from committed damage already resolved on the defender branch
- the return hit is ordinary damage against the attacker, not a bespoke reflection subsystem
- the implementation stays inside `on_damage_received` plus one bounded trigger-local calculation

## Cross-Boundary Concerns

Reflection follows the ordinary reverse-relay story for defender-side reactive damage.

1. The defender's current owner computes the committed-damage amount in Stage 9 after the local
   branch has already finished protection and mitigation.
2. If the attacker is remote, the reflected prepared-hit packet relays back to the attacker's
   current owner and resolves there on the next tick.
3. If the original hit was split by other mechanics, reflection is branch-local: each target
   reflects only the committed damage that actually landed on that branch.
4. The canonical reactive-depth bound prevents reflected damage from opening a fresh reflection or
   thorns ping-pong tree.

## Compiler Requirements

Designer specifies:

- reflection ratio
- which incoming damage classes qualify
- whether the reflected packet mirrors the triggering damage type or uses a fixed authored type
- whether the effect is passive, buff-owned, or item-owned

Compiler emits:

- one passive/status-owned `on_damage_received` trigger
- one bounded trigger-local calculation from the committed damage amount
- one reactive reverse damage payload to the triggering attacker

Compiler validates:

1. `reflection_ratio` is in `[0, 1]` for this reference
2. the sketch keys from committed received damage, not from pre-mitigation attacker-side state
3. the return packet remains reactive and therefore inherits the canonical reactive-depth bound

## Resolved Interaction Notes

- This reference reflects committed damage taken on the defender branch. Blocked hits, fully negated
  barrier hits, or zero-damage branches reflect zero.
- Guardian Angel and similar split mechanics are branch-local here: the ward reflects only what the
  ward actually took, and the guardian reflects only what the guardian actually took.
- Reflection may apply to any qualifying committed damage source in this reference, including DoT or
  AoE branches, as long as there is an attributed attacker/source entity to receive the reverse hit.
- Reflected damage is a reactive reverse packet, not a fresh attack roll. It does not crit in this
  reference.
- Under the canonical default reactive-depth bound, reflected damage does not start a fresh
  `on_damage_received` / `on_hit` proc tree of its own.
