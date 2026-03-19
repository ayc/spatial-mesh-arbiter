# SK-17: Sacrifice Shield

## Designer Intent

I sacrifice 20% of my maximum HP (dealing true damage to myself) to grant an ally a damage-absorbing shield worth 150% of the HP I sacrificed. The shield lasts 5 seconds or until fully consumed by incoming damage.

## Primitive Composition

P-18 (Absorption Barrier) → P-21 (Value Conversion)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Cast on ally — caster loses 20% of max HP immediately (cannot kill the caster — minimum 1 HP)
2. Target gains a shield equal to 150% of HP sacrificed
3. Incoming damage to the shielded target is absorbed by the shield first
4. When shield HP reaches 0, remaining damage carries through to real HP
5. Shield expires after 5 seconds if not fully consumed
6. Expired shield HP is lost (no conversion back to caster HP)
7. Visual: golden barrier around the target, cracks as shield is consumed

## Engine Primitives Required

TODO: SoftState needs a `shield_hp` field (or a list of shield instances with independent durations). Damage resolution must check for active shields before applying to real HP. Shield consumption order matters if multiple shields are active (oldest first? strongest first? most recent first?). The self-damage cost is "true damage" — bypasses all defensive stats. How is this represented — a damage event with a bypass flag?

## Cross-Boundary Concerns

TODO: Caster and target may be on different Arbiters. The self-damage is resolved locally on the caster's Arbiter. The shield application is a mutation on the target's Arbiter — relayed as what? A "grant shield" command? What happens if the caster and target are so far apart that the relay latency causes the shield to arrive a few ticks late — does the target take unmitigated damage during that window?

## Compiler Requirements

TODO: Designer specifies: self-damage (20% max HP, true damage, non-lethal), shield amount (150% of damage dealt to self), shield duration (5s), shield consumption priority. Compiler produces: self-damage event + cross-entity shield grant + shield expiry timer. How does the compiler model the shield as a data structure in SoftState?

## Open Questions

- Can the caster shield themselves, or is it ally-only?
- If the caster is at 1 HP, can they still cast (sacrifice would be 0 HP, producing a 0-value shield)?
- Does the shield stack with other shields (from another support casting the same ability)?
- What is the consumption order when multiple shields are active?
- Does damage sharing from SK-04 Tether apply before or after shield absorption?
- Does SK-19 Guardian Angel's damage redirect apply before or after shield absorption?
- Can the shield be cleansed by enemies (SK-15 Purify in reverse — enemy dispel)?
- Does the shield block all damage types equally, or can some damage bypass shields (true damage)?
