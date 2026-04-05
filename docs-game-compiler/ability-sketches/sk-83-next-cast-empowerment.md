# SK-83: Next-Cast Empowerment

## Designer Intent

I activate my trait to empower my next ability. The next Q, W, or E I cast will be enhanced — more damage, larger AoE, additional effects, or modified behavior. The empowerment is consumed on the next ability cast. If I don't cast within 6 seconds, the empowerment expires unused.

## Primitive Composition

P-16 (Stat Layering) → P-40 (On-Cast Intercept)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Trait activation (separate from Q/W/E)
- Then: any ability cast consumes the empowerment

## Observable Behavior

1. Activate trait — gain "Empowered" buff
2. Next Q cast while empowered: enhanced Q (e.g., larger AoE, extra damage)
3. OR next W cast while empowered: enhanced W (e.g., spreads to additional targets)
4. OR next E cast while empowered: enhanced E (e.g., stuns instead of slows)
5. The empowerment is consumed on the first ability cast
6. Only ONE ability is empowered per trait activation
7. If 6 seconds pass without casting: empowerment expires (wasted)
8. Trait has its own cooldown separate from Q/W/E
9. Visual: glowing hands indicator, enhanced ability has flashier visual effect

## Engine Primitives Required

Next-Cast Empowerment is now the canonical `consumption_window = cast_ability` pattern.

The recommended lowering is:

1. the trait activation applies one positive `Empowered` status for 360 ticks
2. that status authors:
   - `consumption_window = {`
     `consume_on = cast_ability,`
     `allowed_abilities = [Q, W, E],`
     `max_consumptions = 1,`
     `consume_only_on_success = true,`
     `ability_overrides = [`
     `{ ability_id = Q, damage_multiplier = ..., radius_multiplier = ... },`
     `{ ability_id = W, add_effects = [...] },`
     `{ ability_id = E, replace_effects = [...] or add_effects = [...] }`
     `]`
     `}`

This keeps the mechanic entirely inside the canonical status/consumption-window surface. The
empowerment is not a bespoke cross-ability modifier subsystem. It is just a bounded status that:

- watches for the next successful cast of one of the allowed abilities
- applies the compiled override for that specific ability before the cast resolves
- consumes itself after the first successful qualifying cast or on ordinary status expiry

## Cross-Boundary Concerns

The cross-boundary story is the ordinary one for status-owned cast modification.

1. The empowerment status lives on the caster's current authoritative owner.
2. `consume_on = cast_ability` is checked there in Stage 2 after activation-mode selection but
   before the consuming cast resolves.
3. If the consuming cast targets a Ghost/remote entity, the empowered damage/radius/effect payload
   is already compiled into that cast before any later hostile relay occurs.
4. The remote target owner does not need a separate "empowered cast" contract; it simply resolves
   the already-enhanced cast payload through ordinary defense / admission rules.

## Compiler Requirements

Designer specifies:

- empowerment duration
- which abilities are eligible to consume it
- per-ability override payloads (damage/radius multipliers, added effects, or replacement effects)
- whether the status is cleansable

Compiler emits:

- one positive empowerment status
- one `consumption_window` on that status with `consume_on = cast_ability`
- one compiled override table keyed by ability ID
- one consume-on-success rule with `max_consumptions = 1`

Compiler validates:

1. every `ability_id` referenced in `ability_overrides` exists
2. every `allowed_abilities` entry exists
3. the empowerment is expressed through `consumption_window` rather than by duplicating empowered
   shadow copies of every affected ability as separate public skills
4. `max_consumptions = 1` for this sketch's one-shot empower semantics

## Resolved Interaction Notes

- Only the authored Q/W/E abilities consume the empowerment in this reference. Auto-attacks do not.
- The empowerment is consumed on the first successful qualifying cast. Replay mechanics such as
  Spell Echo do not consume a second stack because the status is already gone after the root cast.
- The empowerment status is cleansable if the designer leaves the positive status cleansable.
- Silence and other ordinary cast denial do not pause the 6-second timer. Only canonical timer-pause
  states such as `stasis` do that.
- This reference is non-stacking: reapplying the empowerment refreshes/replaces the existing one
  rather than keeping multiple next-cast windows alive.
- The override is applied before the consuming cast resolves, so all later damage / radius / proc
  logic sees the empowered version of the cast as the base event.
