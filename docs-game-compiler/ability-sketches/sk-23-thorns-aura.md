# SK-23: Thorns Aura

## Designer Intent

Passive: whenever an enemy hits me with a melee attack, they take flat damage back. This damage is
not based on how much they hit me for; it's a fixed amount derived from my stats. Ranged attacks
and spells do not trigger thorns.

## Primitive Composition

P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Incoming direct melee/weapon hit
- Defender's flat thorns value
- Attacker entity

## Observable Behavior

1. An enemy lands a qualifying direct melee/weapon hit on me.
2. After that hit resolves on my branch, thorns emits one flat retaliatory damage packet back to the
   attacker.
3. The retaliatory amount is fixed from my authored/derived thorns value; it does not scale from
   the incoming hit amount.
4. The retaliatory damage uses the authored thorns damage type.
5. The attacker mitigates that retaliatory hit independently unless the authored damage type bypasses
   mitigation.
6. Ranged attacks, spells, and non-qualifying periodic damage do not trigger thorns in this
   reference.
7. Visual: spike/thorn burst effect on the defender when the retaliatory packet is emitted.

## Engine Primitives Required

Thorns Aura is now a canonical passive `on_damage_received` reference restricted to direct
melee/weapon hits.

The recommended lowering is:

1. expose one flat thorns value from the defender's current passive/buff/item state
2. author one passive `on_damage_received` trigger owned by the defender
3. gate that trigger to direct melee/weapon-hit envelopes with an attributed attacker entity
4. emit one reactive flat damage packet back to the triggering attacker using the authored thorns
   damage type and amount

This keeps the mechanic inside existing surfaces:

- thorns is ordinary defender-side reactivity through `P-36`
- the return hit is ordinary hostile damage back to the attacker
- the returned amount is flat and independent of the triggering hit's magnitude

## Cross-Boundary Concerns

Thorns uses the same reverse-relay pattern as other defender-side reactive hits.

1. The defender's current owner inspects the committed triggering hit during Stage 9.
2. The melee-only restriction is taken from the triggering hit classification itself; this
   reference does not perform a second defender-side range test against Ghost positions.
3. If the attacker is remote, the retaliatory thorns packet relays to the attacker's current owner
   and resolves there on the next tick.
4. The canonical reactive-depth bound prevents thorns-vs-thorns ping-pong from creating an
   unbounded proc tree.

## Compiler Requirements

Designer specifies:

- which incoming hits qualify (this reference uses direct melee/weapon hits only)
- flat thorns amount or the derived stat that supplies it
- thorns damage type
- whether the effect is passive, buff-owned, or item-owned

Compiler emits:

- one passive/status-owned `on_damage_received` trigger with a direct-melee/weapon-hit guard
- one reactive flat damage payload back to the triggering attacker

Compiler validates:

1. the trigger is restricted to the intended direct melee/weapon-hit class
2. the outgoing retaliatory amount is flat for this reference, not scaled from incoming damage
3. the retaliatory hit remains reactive and therefore inherits the canonical reactive-depth bound

## Resolved Interaction Notes

- Fully evaded or fully blocked hits do not fire thorns in this reference because no qualifying
  damage reaches `on_damage_received`.
- Reflection and thorns may both fire from the same qualifying received hit: reflection scales from
  committed damage, while thorns emits its own flat retaliatory packet.
- Guardian Angel does not make the guardian "the melee victim." The original melee victim's thorns
  may fire from the victim branch; the guardian's thorns do not fire merely because redirected
  damage later lands there.
- Thorns damage is reactive and, under the canonical default reactive-depth bound, does not start a
  fresh thorns/reflection ping-pong tree.
- If a summoned minion is the triggering attacker, that minion takes the thorns hit. The mechanic
  targets the actual attacker entity, not the summoner behind it.
