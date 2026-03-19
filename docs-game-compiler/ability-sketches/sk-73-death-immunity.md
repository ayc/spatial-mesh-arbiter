# SK-73: Death Immunity

## Designer Intent

I activate this ability and for 4 seconds, I CANNOT DIE. I take full damage from everything — hits land, procs fire, HP decreases — but my HP cannot go below 1. When the duration expires, if I'm at 1 HP, I'm in extreme danger and can be killed by anything.

## Primitive Composition

P-23 (Floor Clamping) → P-45 (Delay Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — gain Death Immunity for 4 seconds
2. All incoming damage is applied normally (not reduced, not absorbed)
3. On-hit procs trigger normally (SK-09 Chain Lightning, SK-22 Reflection, etc.)
4. HP can decrease all the way to 1, but NEVER to 0
5. If incoming damage would reduce HP below 1: HP is set to 1 instead
6. Healing still works normally (can recover above 1 during the window)
7. When the duration expires: you're at whatever HP you have (potentially 1)
8. No special effect on expiry — you're just vulnerable again
9. Visual: fiery rage aura, HP bar flashes at low HP, "UNKILLABLE" indicator

## Engine Primitives Required

### HP Floor During Damage Resolution

This is a new modifier in the damage resolution pipeline. After all damage is calculated and applied:

```
fn apply_damage(entity: &mut Entity, damage: SimFixed) {
    entity.hp = entity.hp - damage;

    // Death Immunity check — AFTER damage, BEFORE death check
    if entity.has_death_immunity() && entity.hp < SimFixed::ONE {
        entity.hp = SimFixed::ONE;
    }

    // Normal death check
    if entity.hp <= SimFixed::ZERO {
        trigger_death(entity);
    }
}
```

The key: death immunity modifies the RESULT of damage, not the damage itself. The full damage amount is "dealt" (for purposes of SK-46 Adaptation accumulator, SK-22 Reflection, etc.), but HP is floored at 1.

### New Entity State: Death Immune

```
status_effect: DeathImmunity {
    expires_at_tick: u64,
}
```

When active: `is_death_immune = true`. The damage pipeline checks this flag after applying damage and before checking for death.

### Distinct From Other Defensive States

| State | Takes damage? | Can die? | Can be CC'd? | Can be targeted? |
|---|---|---|---|---|
| Normal | Yes | Yes | Yes | Yes |
| Invulnerable (SK-44) | No | No | Depends | Depends |
| Unstoppable (SK-51) | Yes | Yes | No | Yes |
| **Death Immune (SK-73)** | **Yes** | **No** | **Yes** | **Yes** |

Death Immunity is the most permissive defensive state — everything works normally EXCEPT dying. You take damage, you can be CC'd, you can be targeted. You just can't reach 0 HP.

### Interaction Cascade

Death Immunity creates extreme edge cases with other abilities:
- **SK-02 Poison Shot DoT:** DoT keeps ticking, HP keeps hitting 1, each tick triggers the "heals caster" drain. The poison caster gets infinite drain healing from a death-immune target.
- **SK-46 Adaptation:** Death-immune entity takes massive damage, accumulates it all, then heals for 100% when Adaptation expires. Combined with Death Immunity, you can take 10,000 damage and heal it all back.
- **SK-70 Energy Shield:** Shield absorbs while death-immune, generating Energy. Then shield breaks, HP goes to 1, but death immunity prevents death. Maximum Energy from maximum damage absorption.
- **SK-11 On-Kill Cascade:** Enemies can't die from cascade while death-immune, preventing the chain.

## Cross-Boundary Concerns

TODO: Minimal cross-boundary complexity. Death Immunity is a local flag on the entity's Arbiter. Incoming damage (local or relayed) is applied normally — the HP floor check is local. The entity's owning Arbiter manages the flag.

The only concern: if damage is relayed cross-boundary and the attacker expects a kill (for on-kill procs like SK-11), the kill doesn't happen. The attacker's Arbiter might have predicted a kill based on Ghost HP data, but the actual HP floor prevents it. This is a prediction mismatch, not a correctness issue.

## Compiler Requirements

TODO: Designer specifies: self-cast, duration (4s), HP floor at 1 (cannot die), all damage still applies, all other mechanics still function. Compiler produces:
- Status effect with `is_death_immune: true` flag
- Damage pipeline modification: after damage application, floor HP at 1 if flag is active
- Death check bypass: skip death trigger while flag is active
- Duration expiry removes the flag (no special on-expiry behavior)

The compiler needs to place this check at the correct point in the damage resolution pipeline — AFTER all damage is applied (so damage numbers, procs, and accumulators see the real damage) but BEFORE the death check.

## Open Questions

- Can Death Immunity be purged/cleansed by enemies (removing it to enable the kill)?
- Does the HP floor prevent execution effects (SK-14 Execute Threshold — bonus damage still applies, but the kill portion doesn't trigger)?
- If HP is at 1 and the entity takes 10,000 damage: is the damage "dealt" 10,000 (for Adaptation, Reflection) or is it clamped to "damage that would bring HP to 1"?
- Does Death Immunity prevent SK-53 HP Swap from setting HP to a value that would be 0?
- Can Death Immunity stack with SK-44 Burrow (invulnerable + death immune — redundant but valid)?
- Does the 4-second window have any interaction with SK-37 Time Rewind (rewind to a higher HP during death immunity)?
- Is there any visual/audio cue when damage is "prevented" by the floor (HP would have gone to 0 but was held at 1)?
- Does Kinematic Dilation affect the 4-second window?
- Can AI NPCs (SK-06 summons) receive Death Immunity?
