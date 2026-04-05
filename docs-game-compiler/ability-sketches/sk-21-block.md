# SK-21: Block

## Designer Intent

My character has a chance to fully block incoming attacks, negating all damage from that hit. Block
chance is derived from my shield/armor stats. After a successful block, block chance is temporarily
reduced (diminishing returns) to prevent permanent invulnerability under rapid attacks.

## Primitive Composition

P-38 (On-Block/Defend Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Incoming damage event
- Defender's block chance stat
- Defender's current block DR penalty

## Observable Behavior

1. An eligible incoming attack reaches the defender-side block gate.
2. The engine evaluates effective block chance from the authored block stat minus any current DR
   penalty.
3. If the block succeeds, eligible HP/resource damage from that hit is reduced to zero and a
   "Blocked!" indicator may be shown.
4. Each successful block adds the authored DR penalty, reducing later block chance until the penalty
   decays.
5. The DR penalty decays over time using the authored decay interval and optional stack cap.
6. Successful blocks may trigger ordinary `on_block` follow-up effects such as `SK-13
   Counter-Strike`.
7. In this reference, non-damage payloads continue unless the authored profile explicitly negates
   them.
8. Visual: shield raise / parry response and spark effect on successful block.

## Engine Primitives Required

Block is now the canonical `BlockDefenseDef` reference.

The recommended lowering is:

1. author defender block policy as:
   - `block_defense = {`
     `chance_stat = block_chance,`
     `applies_to = weapon_hits_only,`
     `dr_penalty_per_block = 0.15,`
     `dr_decay_interval_ticks = 180,`
     `max_dr_stacks = ...,`
     `negates_non_damage_effects = false`
     `}`
2. let successful blocks emit the ordinary Stage 9 `on_block` marker for any separate follow-up
   passives such as Counter-Strike

This keeps the mechanic inside existing compiler/core surfaces:

- the block gate is already a canonical PreMitigation engine policy
- diminishing returns are the built-in block DR penalty/decay model, not a sketch-local timer
- successful blocks automatically publish the `on_block` event for later reactive hooks

## Cross-Boundary Concerns

Block is resolved entirely on the current target owner.

1. The defender's current owner evaluates `BlockDefenseDef` during Stage 7 PreMitigation.
2. A successful block prevents eligible HP/resource damage from entering later barrier/shield or
   mitigation resolution on that branch.
3. If the attacker is remote, there is no extra combat relay for the blocked branch itself; the
   only possible follow-up relay is from later reactive `on_block` outputs such as Counter-Strike.
4. If damage was already split onto multiple targets through another mechanic such as Guardian Angel,
   each branch target evaluates its own block gate independently on its own owner.

## Compiler Requirements

Designer specifies:

- which derived stat supplies block chance
- which incoming hit classes are eligible (`applies_to`)
- DR penalty per successful block
- DR decay interval and optional stack cap
- whether non-damage payloads are also negated
- any separate `on_block` follow-up effects

Compiler emits:

- one `block_defense` profile on the entity definition
- any optional passive `on_block` triggers that react to successful blocks

Compiler validates:

1. `chance_stat` references a valid derived defensive stat
2. `dr_decay_interval_ticks > 0`
3. `dr_penalty_per_block >= 0`
4. `applies_to` is one of the canonical block profile enums

## Resolved Interaction Notes

- This reference uses `applies_to = weapon_hits_only`, so direct melee/ranged weapon attacks are
  eligible but DoTs and ordinary spell ticks are not.
- Successful block happens before shield absorption, so blocked hits do not consume ordinary
  absorption barriers.
- Reflection and thorns are keyed from `on_damage_received`; fully blocked hits therefore do not
  produce those reactions in this reference because no committed damage reaches PostDamage.
- If the wider combat pipeline rejects a hit earlier for some other reason, this block gate never
  sees it.
- Guardian-style redirected branches can still be blocked independently by the branch target,
  because each branch resolves on that target's own authoritative owner.
