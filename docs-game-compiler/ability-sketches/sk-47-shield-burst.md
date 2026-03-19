# SK-47: Shield Burst

## Designer Intent

I activate an ability that grants me a massive shield. When the shield expires naturally or is fully consumed by damage, it explodes — dealing AoE damage to nearby enemies proportional to how much shield was REMAINING when it broke. A shield that expires at full value deals maximum damage. A shield that was chipped down deals less.

## Primitive Composition

P-18 (Absorption Barrier) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — gain a large shield (e.g., 800 HP)
2. Shield absorbs incoming damage normally (same as SK-17)
3. If shield expires (3 seconds) with remaining value: explosion deals damage = remaining_shield * 1.0
4. If shield is fully consumed by damage before expiry: explosion deals 0 damage (nothing remained)
5. If shield is partially consumed: explosion deals proportional damage (e.g., 400 remaining = 400 damage explosion)
6. Explosion hits all enemies within blast radius
7. Visual: golden shield grows brighter as it nears expiry, detonates in a nova

## Engine Primitives Required

### Shield With On-Break and On-Expiry Hooks

SK-17 Sacrifice Shield defined shields as a damage absorption layer. This sketch adds **lifecycle hooks** on the shield itself:

```
struct ShieldInstance {
    shield_hp: SimFixed,
    max_shield_hp: SimFixed,
    expires_at_tick: u64,
    on_expiry: Option<ShieldExpiryAction>,
    on_break: Option<ShieldBreakAction>,
}

enum ShieldExpiryAction {
    AoeDamage { radius: SimFixed, damage_multiplier: SimFixed },
    // Future: could be heal, buff, etc.
}
```

Two distinct hooks:
- **On-expiry** (timer runs out, shield still has HP): read `shield_hp`, calculate AoE damage, resolve against all enemies in radius
- **On-break** (shield HP reaches 0): `shield_hp` is 0, so explosion deals 0. Or: designer could define different on-break behavior.

The shield system needs to distinguish "expired naturally" from "consumed by damage" — currently SK-17's shield just disappears in both cases.

### Remaining Value as Ability Input

This is the first ability where a **defensive resource's current value feeds into an offensive calculation**. The shield isn't just a buffer — its remaining HP becomes a damage parameter. The engine needs to read the shield's current value at the moment of expiry/break and pass it to the damage resolution pipeline.

This creates an interesting decision: do you protect the shield (stay safe, deal more damage later) or accept damage (survive now, deal less explosion damage)?

## Cross-Boundary Concerns

TODO: The shield and explosion are both on the caster's Arbiter. The explosion is a local AoE spatial query — same as SK-29 Blizzard pulses. Enemies in the blast radius that are Ghosts receive damage relays. No special cross-boundary complexity beyond standard AoE.

One edge case: if the shield is consumed by cross-boundary damage (a relay arrives that depletes the shield), the on-break hook fires immediately on the caster's Arbiter. The explosion is local.

## Compiler Requirements

TODO: Designer specifies: shield amount (800 HP), duration (3s), on-expiry action (AoE damage = remaining_shield * multiplier, radius), on-break action (AoE damage = 0 or different behavior). Compiler produces:
- Shield instance with `max_shield_hp`, `expires_at_tick`
- On-expiry hook: read `shield_hp` → AoE damage resolution
- On-break hook: read `shield_hp` (0) → minimal or no damage
- AoE payload with damage derived from shield state, not from offensive stats

The compiler needs to express "this shield has side effects on lifecycle events" — extending the shield primitive beyond simple absorption.

## Open Questions

- Can the explosion crit?
- Does the explosion use the caster's offensive stats (for penetration, damage bonuses) or is it purely shield-value-based?
- Can enemies cleanse/purge the shield to prevent the explosion (SK-15 Purify in reverse)?
- If the shield is cleansed, does it count as "break" (0 damage explosion) or "removal" (no explosion at all)?
- Does damage redirected via SK-19 Guardian Angel consume the shield? If so, the explosion deals less damage because of your ally's redirected damage.
- Can multiple Shield Burst shields stack? If so, do they all explode independently?
- Does the explosion trigger on-hit procs (SK-09 Chain Lightning per enemy hit)?
- Does SK-22 Damage Reflection interact — if reflected damage consumes the shield, does the explosion fire?
