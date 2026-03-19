# SK-28: Slow + Diminishing Returns

## Designer Intent

I apply a 50% movement speed reduction to an enemy for 3 seconds. If the same or another slow is applied again within 8 seconds of the first slow expiring, the new slow is 50% less effective. Repeated slows become increasingly weak, preventing perma-slow from stacking.

## Primitive Composition

P-16 (Stat Layering) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. First slow applied: target moves at 50% speed for 3 seconds
2. Slow expires. 8-second DR window begins.
3. If slowed again within the window: new slow is 25% (50% * 0.5 DR) for 3 seconds
4. If slowed a third time within the window: 12.5% slow for 3 seconds
5. After 8 seconds with no new slow: DR resets, next slow is full effectiveness
6. Multiple different slow sources each apply DR independently... or do they share a DR category?
7. Movement speed has a floor (e.g., minimum 20% of base speed — cannot be fully immobilized by slows alone)
8. Visual: frost/sluggish effect, intensity matches slow percentage

## Engine Primitives Required

TODO: This sketch is primarily about the **diminishing returns system** itself, not any single ability. The Arbiter needs to track per-entity CC history:

```
struct CcHistory {
    category: CcCategory,          // e.g., Slow, HardCC, Silence
    applications_in_window: u32,
    last_expiry_tick: u64,
    dr_window_ticks: u64,          // e.g., 480 ticks (8 seconds)
}
```

On each CC application, the Arbiter looks up the history for that category, calculates the DR multiplier, applies it to the incoming CC's effectiveness/duration, and updates the history. The DR formula needs to be deterministic and configurable.

## DR System Design Questions

The DR system is shared across all CC sketches (SK-24 through SK-28). Key design decisions:

1. **Category grouping:** Are stun/sleep in one category (hard CC) and root/silence/slow in another (soft CC)? Or is each CC type its own category?
2. **What diminishes:** Duration only? Or also effectiveness (slow percentage)?
3. **DR formula:** Exponential decay (0.5^n)? Linear reduction? Hard cap after N applications?
4. **Immunity window:** After hard CC, brief immunity. After soft CC, just DR? Or immunity for all?
5. **DR reset:** Time-based (8s window)? Or count-based (resets after N seconds of no CC)?

## Cross-Boundary Concerns

TODO: The DR history is per-entity state on the entity's owning Arbiter. When CC is applied cross-boundary (relay from attacker's Arbiter), the defender's Arbiter calculates the effective CC using its local DR history. The attacker doesn't need to know the DR state — they just send "apply 50% slow for 3s" and the defender's Arbiter applies DR reduction before applying the effect.

## Compiler Requirements

TODO: Designer specifies per-ability: CC category for DR purposes, base effectiveness, base duration, tenacity-reducible flag. The compiler needs a global DR configuration: categories, DR formula, window duration, immunity rules. This configuration is part of the game rules (SpellData / game image), not per-ability. How does the compiler validate that all CC abilities reference valid DR categories?

## Open Questions

- Is the DR window per-category or per-specific-effect (two different slows share DR, but slow and root don't)?
- Does tenacity reduce the DR'd duration (applied after DR) or the base duration (applied before DR)?
- Is there a hard immunity after N applications in a window (e.g., after 3 stuns, immune for 5 seconds)?
- Do friendly CC effects (ally roots you in place for protection) consume DR charges?
- Does the movement speed floor interact with root (SK-25) — root is 100% slow, but slow floor is 20%?
- How does the DR system persist across Arbiter boundaries during entity handoff — is CcHistory part of the entity's transferable state?
- Does Kinematic Dilation affect DR windows (dilated time = longer real-time DR window)?
- Should DR be visible to players (UI indicator showing current DR reduction)?
