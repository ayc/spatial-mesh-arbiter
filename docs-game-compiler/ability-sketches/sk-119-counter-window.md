# SK-119: Counter Window

## Designer Intent

During certain boss attack animations, the boss glows blue — signaling a COUNTER WINDOW. If a player hits the boss with a "counter" classified ability during this window, the attack is interrupted, the boss takes bonus damage, and the boss is briefly staggered. If no one counters, the boss completes its powerful attack. Timing the counter is a core skill check in raid encounters.

## Primitive Composition

P-65 (Vulnerability Window Broadcast) → P-40 (On-Cast Intercept)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Boss entity (broadcasts the counter window)
- Player entity (must use an ability that can counter a vulnerability window during the window)

## Observable Behavior

1. Boss begins a specific attack animation — blue glow appears (counter window opens)
2. Counter window lasts 1-2 seconds (tight timing)
3. If a player hits the boss with an ability that can counter a vulnerability window during the window:
   - Boss attack is INTERRUPTED (cancelled — doesn't deal damage)
   - Boss takes bonus damage from the counter hit
   - Boss enters a brief stagger (1.5 seconds — stunned + vulnerable)
   - Counter window closes
4. If NO counter lands during the window:
   - Boss completes the attack (potentially devastating damage/AoE)
   - Counter window closes
5. Only the FIRST counter that lands counts (no double-countering)
6. Visual: blue flash on boss during window, dramatic parry effect on successful counter

## Engine Primitives Required

Counter Window is now a canonical `vulnerability_window` reference.

The recommended lowering is:

1. on the boss attack definition, author:
   - `cast_time > 0`
   - `vulnerability_window = {`
     `start_offset_ticks = ...`
     `duration_ticks = ...`
     `bonus_damage = ...`
     `stagger_duration_ticks = ...`
     `vulnerability_bonus = ...`
     `interrupt_current_cast = true`
     `}`
2. on eligible player abilities, author `can_counter_vulnerability_window = true`
3. let the target owner's active vulnerability-window directive detect the first qualifying hit
   during the open window

This keeps the mechanic entirely inside the canonical counter-window surface:

- the window belongs to the broadcasting boss ability, not to a sketch-local sidecar state machine
- counter eligibility is a compile-time flag on the incoming player ability
- the first admitted qualifying counter interrupts the active cast if configured
- bonus damage still goes through the normal damage pipeline
- the follow-up stagger is a mechanical boss-check state, not ordinary CC

## Cross-Boundary Concerns

Counter Window is target-owner authoritative.

1. The boss's current owner tracks the open/closed vulnerability window from the boss ability's
   cast-state timeline.
2. Local and relayed hits are both checked against that same authoritative window when they arrive.
3. The first qualifying admitted counter consumes the window on the boss owner; later same-window
   attempts resolve as ordinary hits with no counter bonus.
4. Same-tick races are resolved by the target owner's ordinary deterministic hit ordering. There is
   no separate latency-grace side channel in the canonical contract.

## Compiler Requirements

Designer specifies:

- which boss abilities open a vulnerability window
- window start offset and duration
- bonus damage and stagger duration
- whether a successful counter interrupts the current cast
- which player abilities are eligible counters

Compiler emits:

- one `vulnerability_window` directive on the broadcasting boss ability
- `can_counter_vulnerability_window = true` on eligible player abilities
- the generated mechanical stagger/vulnerability follow-up owned by the boss ability's counter
  resolution

Compiler validates:

1. `cast_time > 0` when `vulnerability_window` is authored
2. `start_offset_ticks + duration_ticks <= cast_time_ticks`
3. the mechanic uses canonical `vulnerability_window`, not a bespoke boss-side interrupt table

## Resolved Interaction Notes

- The counter bonus damage goes through the normal damage pipeline.
- The counter-generated stagger is mechanical, not ordinary CC, and is not shortened by status
  resistance or DR.
- Boss super-armor / ordinary CC immunity do not suppress the counter-generated stagger, because it
  is not admitted through the ordinary CC system.
- A successful counter interrupts the current boss cast only if `interrupt_current_cast = true` on
  the authored window.
- Same-tick multiple counter attempts are deterministic first-hit-wins on the boss owner.
