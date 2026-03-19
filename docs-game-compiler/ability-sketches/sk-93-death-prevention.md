# SK-93: Death Prevention

## Designer Intent

I place a protective buff on an ally. If that ally would die within the next 3 seconds, instead of dying they are healed to full HP. The buff is consumed on activation. If the ally doesn't take lethal damage within 3 seconds, the buff expires unused.

## Primitive Composition

P-39 (On-Death Hook) → P-23 (Floor Clamping) → P-15 (Value Modification)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Cast on ally — they receive the "Divine Palm" buff for 3 seconds
2. If the ally's HP would reach 0 during the buff: death is PREVENTED
3. The ally is healed to 100% of their max HP instantly
4. The buff is consumed (one-time use)
5. If the buff expires without triggering: nothing happens, cooldown was spent
6. The prevention is absolute — no damage amount can overcome it (even 50,000 damage)
7. Visual: golden palm icon on the ally, dramatic full-heal burst if triggered

## Engine Primitives Required

### Death Check Interception

The death pipeline currently:
1. Damage is applied → HP reaches 0
2. Death is declared
3. Entity removed from Arbiter
4. Meta handles respawn

Death Prevention intercepts at step 2:
1. Damage is applied → HP reaches 0
2. **Check: does this entity have a Death Prevention buff?**
3. If yes: DO NOT declare death. Instead: heal to max HP, consume the buff.
4. If no: proceed with normal death.

```
fn check_death(entity: &mut Entity) -> bool {
    if entity.hp <= SimFixed::ZERO {
        if let Some(palm) = entity.find_effect::<DeathPreventionBuff>() {
            entity.hp = entity.max_hp;  // Full heal
            entity.remove_effect(palm.effect_id);  // Consume
            return false;  // Death prevented
        }
        return true;  // Entity dies
    }
    false
}
```

### Distinct From Other Death Mechanics

| Mechanic | When HP hits 0 | Result |
|---|---|---|
| Normal | Death declared | Entity removed, respawn |
| SK-73 Death Immunity | HP floors at 1, never reaches 0 | Entity alive at 1 HP |
| SK-57 Death-Triggered Form | Intercepted, transform instead of die | Entity alive in new form |
| SK-89 Respawn Anchor | Death declared, fast respawn elsewhere | Entity removed, quick respawn |
| **SK-93 Death Prevention** | **Intercepted, full heal instead of die** | **Entity alive at full HP** |

Death Prevention is unique: the entity's HP actually reaches 0 (or below), but the death is reversed with a full heal. This is the most dramatic save — from 0 HP to 100% in one tick.

### Window-Based Conditional (Like SK-87 Counter)

Like SK-87 Conditional Counter ("if attacked during window → payoff"), Death Prevention is "if ally would die during window → payoff." The trigger is: ally HP reaches 0 while the buff is active. If no lethal damage occurs, the buff expires unused.

### Interaction With SK-92 Anti-Heal

Critical interaction: if the ally has Anti-Heal (100% healing reduction) and Death Prevention triggers, the "heal to full" could be reduced to 0 by anti-heal. The ally's HP reaches 0 → Death Prevention triggers → heal to full → anti-heal reduces heal to 0 → HP is still 0 → dies anyway?

Design choice: Death Prevention's heal BYPASSES anti-heal (it's a death prevention mechanic, not a normal heal), or Death Prevention is countered by anti-heal (adding counterplay).

## Cross-Boundary Concerns

TODO: The buff is applied to the ally via standard relay. The death check happens on the ally's Arbiter (where their HP is authoritative). The ally's Arbiter checks for the buff and applies the heal locally. No cross-boundary concern for the death check itself.

The only cross-boundary element is the initial buff application (if caster and ally are on different Arbiters).

## Compiler Requirements

TODO: Designer specifies: target (ally), buff duration (3s), trigger (ally HP reaches 0), on-trigger (prevent death + heal to 100% max HP), consumed on trigger, expires if not triggered. Compiler produces:
- DeathPreventionBuff status effect
- Death check hook: intercept death → check for buff → heal → consume
- Single-use consumption on trigger
- Expiry on timeout without trigger

The compiler needs to support **death check hooks** — the game adapter can intercept the death pipeline and conditionally prevent it.

## Open Questions

- Does the full heal bypass SK-92 Anti-Heal?
- Does the heal trigger on-heal effects (SK-04 Tether heal sharing)?
- Can the buff be purged by enemies (removing it before it triggers)?
- If the ally takes 10,000 damage in one hit (overkill), is death still prevented?
- Does the death prevention trigger before or after SK-73 Death Immunity check?
- If both SK-73 and SK-93 are active, which takes priority? (SK-73 prevents reaching 0, so SK-93 never triggers)
- Can Death Prevention trigger on damage from SK-53 HP Swap (HP set to a lethal value)?
- Does the full heal generate SK-70 Energy Shield energy (it's technically incoming healing)?
- Can the buff be applied to the caster (self-cast)?
- If the ally is in SK-91 Team-Agnostic Stasis, can they receive the buff? (Untargetable during stasis)
