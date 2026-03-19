# SK-15: Purify

## Designer Intent

I target an ally and instantly remove all negative status effects (debuffs, DoTs, crowd control). The ally then gains 1.5 seconds of debuff immunity — new debuffs applied during this window are blocked.

## Primitive Composition

P-15 (Value Modification)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Cast on ally — all negative status effects are immediately removed
2. This includes: DoTs, slows, stuns, roots, silences, damage-over-time, movement debuffs
3. Target gains a "Purified" buff granting debuff immunity for 1.5 seconds
4. During immunity window: any incoming debuff application is blocked (not just delayed)
5. Purify itself has a long cooldown (e.g., 120 seconds)
6. Visual: cleansing light effect on the target, immunity glow during the window

## Engine Primitives Required

TODO: The Arbiter needs to iterate the target's `active_effects` list, classify each as positive or negative, and remove all negatives. How is "negative" defined — a flag on the effect definition? A compiler-assigned classification? After removal, a special immunity effect is applied that intercepts future debuff applications. How does the immunity intercept work — a check during apply_status_effect that looks for an active immunity buff?

## Cross-Boundary Concerns

TODO: If caster and target are on different Arbiters, the cleanse is a cross-boundary action. The caster's Arbiter sends a "cleanse" command to the target's Arbiter. The target's Arbiter performs the actual effect removal (it owns the target's SoftState). What if a debuff is applied to the target between the cleanse being sent and arriving? Race condition.

## Compiler Requirements

TODO: The compiler needs to tag every status effect definition as cleansable/uncleansable and positive/negative. Designer specifies per-effect: "this DoT is a debuff and is cleansable." How does the compiler validate that the cleanse ability correctly references the classification system? Does the compiler produce a cleanse "filter" that the Arbiter evaluates?

## Open Questions

- Are all debuffs cleansable, or can some be marked "uncleansable" (e.g., ultimate ability debuffs)?
- Does cleansing a DoT (SK-02 Poison) also remove the caster's stacking damage buff, or do those persist independently?
- Does cleansing a displacement mid-flight (SK-01 Toss) drop the entity at its current airborne position?
- Can Purify remove the "Purified" immunity buff from an enemy (double-cleanse interaction)?
- Does the immunity window block ALL debuffs or just new applications? (What about DoT reapplication from SK-02?)
- How does Purify interact with SK-04 Tether — does cleansing one partner break the tether?
- If the target has 15 active debuffs, is there a performance concern with bulk removal in a single tick?
