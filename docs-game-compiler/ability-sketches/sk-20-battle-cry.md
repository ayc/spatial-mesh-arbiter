# SK-20: Battle Cry

## Designer Intent

I shout, granting all allies within radius +20% attack speed and +15% movement speed for 8
seconds. The buff is applied at cast time; allies who enter the radius later do not receive it.

## Primitive Composition

P-09 (Shape Overlap Query) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (AoE centered on caster)

## Observable Behavior

1. Cast performs one snapshot ally query around the caster at that instant.
2. Every admitted ally, including the caster, receives an 8-second positive speed buff.
3. That buff grants +20% attack speed and +15% movement speed.
4. Allies who move out of range keep the buff for its full remaining duration.
5. Allies who enter range after the cast do not receive anything from this cast.
6. Each recipient tracks its own ordinary buff timer locally after application.
7. Visual: war cry animation plus speed-line buff FX on affected allies.

## Engine Primitives Required

Battle Cry is now a canonical self-centered snapshot ally-buff reference.

The recommended lowering is:

1. resolve one instant circle query centered on the caster's committed position at cast commit
2. filter that query to allied living entities for this reference
3. apply one positive `battle_cry_buff` status to every admitted recipient
4. define that status with:
   - `duration_ticks = 480`
   - `polarity = positive`
   - `stat_modifiers = [`
     `{ stat_id = attack_speed, operation = add_percent, value = 0.20 },`
     `{ stat_id = movement_speed, operation = add_percent, value = 0.15 }`
     `]`

This keeps the mechanic inside existing compiler surfaces:

- the AoE part is one ordinary snapshot `P-09` query, not a persistent zone
- the buff payload is one ordinary positive `apply_buff`
- the speed bonuses use canonical `P-16` stat layering through `stat_modifiers`

## Cross-Boundary Concerns

Battle Cry is snapshot-at-cast and target-owner authoritative after admission.

1. The caster's current owner performs the snapshot ally query using current local and Ghost poses
   at the cast tick.
2. Any admitted remote/Ghost ally receives the ordinary target-owner relay for positive status
   application.
3. Once the buff is applied, each recipient's current owner advances and eventually expires that
   status locally like any other buff.
4. Later movement relative to the caster is irrelevant because the mechanic is not a persistent
   aura or zone.

## Compiler Requirements

Designer specifies:

- the self-centered ally radius
- buff duration
- the attack-speed and movement-speed bonuses
- whether the caster is included in the admitted recipient set

Compiler emits:

- one snapshot circle query centered on the caster
- one positive `StatusEffectDefinition` carrying the two `stat_modifiers`
- one `apply_buff` payload for every admitted ally recipient

Compiler validates:

1. query radius is positive
2. buff duration is positive
3. the generated status is `positive`
4. the mechanic stays a one-time snapshot query rather than a persistent aura/zone

## Resolved Interaction Notes

- Later entrants do not gain the buff because the query runs only once at cast commit.
- Recipients who leave the radius keep the buff because it is an ordinary positive status on the
  target, not a distance-maintained tether or zone membership.
- Multiple Battle Cry casts follow the same ordinary `StatusEffectDefinition.max_stacks` and
  `P-16` layering rules as any other positive status. This sketch does not introduce bespoke
  stack-capping logic.
- Buff duration is in simulation ticks, so Kinematic Dilation does not create a second real-time
  expiration clock.
- Whether the buff survives death, can be dispelled, or is capped with other haste effects is
  governed by the broader status/death rules the game authors elsewhere, not by a special Battle
  Cry exception.
