# SK-51: Unstoppable

## Designer Intent

I activate a defensive ability that grants me Unstoppable status for 2 seconds and a shield. While Unstoppable, I am completely immune to all crowd control effects. I can still take damage, be targeted by abilities, and interact normally — I just can't be CC'd.

## Primitive Composition

P-62 (Categorized CC Immunity)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — gain Unstoppable status for 2 seconds + shield
2. While Unstoppable: all incoming CC is negated (stuns, roots, silences, slows, blinds, sleep, displacement, pulls)
3. CC abilities still deal their damage (if any) — only the CC component is stripped
4. While Unstoppable: I can still take damage normally (NOT invulnerable)
5. While Unstoppable: I can still be targeted by abilities (NOT untargetable)
6. Existing CC is removed on activation (acts as a self-cleanse)
7. Shield provides additional survivability during the Unstoppable window
8. Visual: glowing golden outline, "Unstoppable" text indicator

## Engine Primitives Required

### New Entity State: Unstoppable

A third defensive state alongside invulnerable (SK-44) and untargetable (SK-44):

| State | Takes damage? | Targetable? | Affected by CC? |
|---|---|---|---|
| Normal | Yes | Yes | Yes |
| Unstoppable (SK-51) | Yes | Yes | **No** |
| Invulnerable (SK-44) | **No** | Depends | Depends |
| Untargetable (SK-44) | Depends | **No** | Depends |

`is_unstoppable` is a flag on the entity's capability state. When true:
- All incoming CC applications are negated (status effect application is rejected)
- Damage components of CC abilities still apply (SK-24 Stun deals damage AND stuns — Unstoppable blocks the stun but not the damage)
- Forced movement is prevented (SK-01 Toss, SK-31 Vortex pull, SK-43 Drag — none move the entity)
- Existing CC is purged on activation (self-cleanse)

### CC Application Check

Every CC application in the engine must check `is_unstoppable` before applying:
```
fn try_apply_cc(target: &Entity, cc_effect: StatusEffect) -> bool {
    if target.is_unstoppable { return false; }
    if target.is_cc_immune_window { return false; }  // Post-CC immunity (SK-24)
    // Apply DR (SK-28), tenacity, etc.
    apply_status_effect(target, cc_effect);
    return true;
}
```

This check must be in the CC application path, AFTER the damage portion of the ability has resolved. The ability's damage goes through normally — only the CC component is stripped.

### Splitting Damage From CC

Many abilities deal damage AND apply CC in a single action (SK-24 Stun deals damage + stuns, SK-49 Cone Strike deals damage + slows). Against an Unstoppable target, the engine must:
1. Apply damage normally (full pipeline)
2. Attempt to apply CC → rejected by Unstoppable check
3. Result: target takes damage but is not CC'd

This means abilities must have separable damage and CC components — the engine can't treat "stun + damage" as an atomic unit. The compiler must decompose abilities into independent effects that can be partially applied.

### Self-Cleanse on Activation

When Unstoppable is activated, all existing CC effects on the entity are removed:
- All active stuns, roots, silences, slows, blinds, sleep — all removed
- Similar to SK-15 Purify but self-targeted and immediate

## Cross-Boundary Concerns

TODO: Minimal cross-boundary complexity. Unstoppable is a local state on the entity's Arbiter. When CC arrives via relay (cross-boundary stun), the entity's Arbiter checks `is_unstoppable` and rejects the CC component while applying the damage component. The attacker's Arbiter doesn't need to know the target is Unstoppable — the CC rejection is handled locally.

One consideration: if the attacker's Arbiter pre-rolls a CombatContext that assumes the target will be stunned (for follow-up abilities), the stun not applying might cause unexpected behavior. But the engine doesn't pre-assume CC success — it's always evaluated on the defender's Arbiter.

## Compiler Requirements

TODO: Designer specifies: self-cast, duration (2s), Unstoppable (immune to all CC), self-cleanse on activation, shield amount, does NOT prevent damage or targeting. Compiler produces:
- Status effect with `is_unstoppable: true` flag
- On-apply hook: remove all active CC effects from the entity (self-cleanse)
- Shield instance (same as SK-17)
- Duration expiry removes Unstoppable flag

The compiler needs to ensure that ALL CC application paths check `is_unstoppable`. This is a system-wide invariant — any new CC type added in the future must also check this flag. The compiler should validate this statically: every status effect tagged as CC must go through the `try_apply_cc` function.

## Open Questions

- Does Unstoppable prevent friendly CC (ally roots you for protection)?
- Does Unstoppable prevent self-inflicted CC (abilities that stun yourself as a drawback)?
- Does Unstoppable block displacement from allies (SK-01 Toss by an ally to reposition you)?
- Does Unstoppable block SK-40 Mind Control? Mind Control is CC — should be blocked.
- Does Unstoppable prevent the slow component of SK-29 Blizzard while still taking the damage?
- Can Unstoppable be purged by enemies (removing the Unstoppable buff)?
- Does Unstoppable interact with Diminishing Returns — does time spent Unstoppable count toward the DR window?
- If an Unstoppable entity enters SK-31 Vortex, are they immune to the pull force? (Pull is forced movement = CC)
- Does Unstoppable prevent the "pinning" from SK-34 Charge?
- Can Unstoppable be stacked with SK-44 Burrow (Unstoppable + Invulnerable)?
- How does Unstoppable interact with SK-27 Sleep's break-on-damage — if Unstoppable prevents Sleep from being applied, there's nothing to break.
