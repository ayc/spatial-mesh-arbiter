# SK-116: Charge-Finisher

## Designer Intent

My martial arts abilities are split into two categories: charge-up skills and finishing moves. Charge-up skills build charges (up to 3). Each charge-up skill does minor damage AND adds 1 charge to a shared pool. When I'm ready, I use a finishing move — it CONSUMES all charges and deals a powerful effect that scales with the number of charges consumed. More charges = stronger finisher.

## Primitive Composition

P-50 (Typed Multi-Charge Pool) → P-42 (Stacking Counters w/ Decay)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Charge-up abilities: standard targeted attacks that also build charges
- Finisher abilities: consume all accumulated charges for an empowered effect

## Observable Behavior

1. Use Fists of Fire (charge-up): deal minor fire damage + gain 1 charge (max 3)
2. Use Claws of Thunder (charge-up): deal minor lightning damage + gain 1 charge (now at 2)
3. Use Blades of Ice (charge-up): deal minor cold damage + gain 1 charge (now at 3)
4. Use Dragon Talon (finisher): consume all 3 charges → kick with massive damage + elemental effects from all 3 charge types
5. Each charge-up skill adds a DIFFERENT elemental charge — the finisher's effect depends on WHICH charge-ups were used
6. Charges decay after 15 seconds of not using a charge-up skill
7. Visual: glowing charge indicators (1, 2, 3), flashy finisher with combined elemental effects

## Engine Primitives Required

Charge-Finisher is now a canonical typed `charge_pool` reference.

The recommended lowering is:

1. define one shared `RuntimeStateDefinition(kind = charge_pool)` with:
   - `capacity = 3`
   - `charge_types = [fire, lightning, cold]`
   - `decay_mode = all_at_once`
   - `decay_ticks = 900`
2. let each generator ability emit one `modify_charge_pool` on successful commit:
   - `state_id = martial_charge_pool`
   - `action = add`
   - `charge_type = fire|lightning|cold`
3. gate each finisher on at least one stored charge, then consume the full pool with:
   - `modify_charge_pool(state_id = martial_charge_pool, action = consume, consume_policy = all)`
4. let downstream finisher effects branch or scale from the consumed count/composition bindings that
   canonical typed charge-pool consumption already exposes

This keeps the mechanic entirely inside existing runtime-state surfaces:

- the pool is one ordinary per-entity `charge_pool`, not a new custom martial-arts subsystem
- generator abilities are just ordinary casts that append typed charges to that shared pool
- finisher abilities are just ordinary casts that consume the pool and read count/composition
- decay timing is the canonical `decay_mode = all_at_once`, not a bespoke timeout script

## Cross-Boundary Concerns

Charge-Finisher is caster-owner authoritative.

1. The typed charge pool lives in the caster's ordinary runtime state.
2. Generator abilities that land on remote targets still credit charges locally on the caster owner
   because the pool belongs to the caster, not the target.
3. Finisher abilities consume charges locally on the caster owner before their empowered effects
   continue through the ordinary target/relay path.
4. If the caster hands off, the charge pool and its current stored composition transfer as ordinary
   runtime state.

## Compiler Requirements

Designer specifies:

- shared pool capacity
- legal charge types
- decay timeout / decay mode
- which generator abilities add which typed charge
- which finisher abilities consume the pool and how they branch/scale on consumed count/composition

Compiler emits:

- one typed `charge_pool` runtime-state definition
- one `modify_charge_pool(action = add, charge_type = ...)` for each generator ability
- one finisher guard requiring available charges for this reference
- one `modify_charge_pool(action = consume, consume_policy = all)` for each finisher
- ordinary finisher effect branches/scalars driven by the consumed charge bindings

Compiler validates:

1. the referenced shared pool exists and is of kind `charge_pool`
2. generator `charge_type` values are declared in that pool's `charge_types`
3. `capacity > 0`
4. the sketch uses canonical typed `charge_pool` behavior rather than inventing a second typed
   combo-resource system

## Resolved Interaction Notes

- This reference requires at least one stored charge to cast a finisher; zero-charge casts fail
  cleanly instead of producing a weak empty version.
- Generator abilities add their typed charge on successful committed generator resolution in this
  reference, not on whiff.
- The shared pool preserves insertion order, so downstream finisher logic can branch on both total
  count and exact composition.
- If the pool is already full, further generator adds saturate at capacity; they do not exceed the
  authored max.
- Stasis and other canonical timer-pause states pause charge decay the same way they pause other
  runtime-state timers.
- The finisher's offensive scaling uses the finisher's own authored damage/effect definitions; the
  consumed charges provide count/composition inputs, not a borrowed offensive-stat snapshot from the
  generators.
