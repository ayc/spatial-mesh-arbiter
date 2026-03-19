# SK-112: Deferred Resolution

## Designer Intent

I buff an ally with a false promise. For 8 seconds, they appear to take no damage and receive no healing — their HP bar doesn't move. In reality, all damage and healing is secretly accumulated in a hidden ledger. When the buff expires, the NET result is applied: if more healing than damage occurred, they're fine. If more damage than healing, they take the difference and might die.

## Primitive Composition

P-22 (Deferred Ledger)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity

## Observable Behavior

1. Cast on ally — False Promise buff applied for 8 seconds
2. For the duration: ally's HP bar DOES NOT CHANGE regardless of damage/healing
3. Ally appears immortal (no visible HP loss) — but they're NOT invulnerable (damage is accumulating)
4. All healing also accumulates (not visible on HP bar)
5. On expiry: calculate NET = total_healing - total_damage
6. If NET >= 0: ally's HP is adjusted upward (effective healing received)
7. If NET < 0: ally's HP drops by |NET| (potentially killing them instantly)
8. If the ally would have died during the buff (accumulated damage > max HP + accumulated healing): they die on expiry
9. Visual: golden shield effect during buff, dramatic HP bar resolution on expiry (jumps up or drops)

## Engine Primitives Required

### HP Change Suppression + Hidden Ledger

This requires the engine to SUPPRESS all HP modifications on the target while maintaining a hidden accumulator:

```
status_effect: DeferredResolution {
    accumulated_damage: SimFixed,
    accumulated_healing: SimFixed,
    expires_at_tick: u64,
}
```

The damage/healing pipeline must be intercepted:
```
fn apply_hp_change(entity: &mut Entity, change: SimFixed, is_damage: bool) {
    if let Some(deferred) = entity.find_effect::<DeferredResolution>() {
        if is_damage {
            deferred.accumulated_damage += change.abs();
        } else {
            deferred.accumulated_healing += change;
        }
        return;  // HP does NOT change — suppressed
    }
    // Normal HP modification
    entity.hp += change;
}
```

### Visible HP Deception

The ally's HP bar must NOT change during the buff. But the Edge Node normally displays authoritative HP. Options:
- **Server-side**: the Arbiter doesn't send HP changes during the buff. The Edge Node shows stale HP. On expiry, the Arbiter sends the final HP value.
- **Client-side**: the Arbiter sends a "deferred resolution active" flag, and the client freezes the HP bar until the flag is removed.

Server-side suppression is simpler — the downstream payload just doesn't include HP updates for this entity during the buff.

### Expiry Resolution

On buff expiry:
1. `net = accumulated_healing - accumulated_damage`
2. `entity.hp = entity.hp + net` (HP frozen at pre-buff value + net)
3. If `entity.hp <= 0`: entity dies
4. If `entity.hp > entity.max_hp`: cap at max HP
5. Remove the buff

The resolution is a single HP modification that reflects ALL accumulated changes. This can be a massive HP swing — either a huge heal or instant death.

### All Damage/Healing Sources Affected

Every damage and healing source must go through the interception:
- Direct damage, DoT ticks (SK-02), AoE damage (SK-29), proc damage (SK-09)
- Direct heals, HoT ticks (SK-16 Holy Ground), drain heals (SK-02), burst heals
- Shield damage? Design choice: does damage absorbed by shields still accumulate?
- SK-92 Anti-Heal: does anti-heal reduce the accumulated healing?

### Death During Buff

If accumulated damage is massive (ally took 10,000 damage but only 3,000 healing), the ally APPEARS alive during the buff but will die on expiry. There's no way to see this coming unless you track the hidden ledger.

Can the ally be saved? If an ally lands a massive heal during the buff, the healing accumulates and offsets the damage. The hidden ledger is the ally's lifeline.

## Cross-Boundary Concerns

TODO: The deferred resolution buff is on the ally's entity (their Arbiter). All damage and healing on the ally is intercepted locally. No special cross-boundary handling — damage relays arrive and are intercepted locally instead of modifying HP.

The only concern: allies on other Arbiters healing the buffed entity. The heal relay arrives, and instead of modifying HP, it's accumulated. This is transparent to the healing source — they don't need to know the heal was deferred.

## Compiler Requirements

TODO: Designer specifies: ally buff (8s), all HP changes suppressed and accumulated, on-expiry apply NET (healing - damage), death if NET < negative current HP, HP bar frozen during buff. Compiler produces:
- DeferredResolution status effect with damage/healing accumulators
- HP change interception hook: redirect all damage/healing to the ledger
- On-expiry hook: calculate NET, apply to HP, death check
- Downstream payload suppression: don't send HP updates during buff

The compiler needs to support **HP change interception** — a status effect that redirects all HP modifications to a hidden accumulator instead of the actual HP value.

## Open Questions

- Does shield absorption count as "damage" for the accumulator (shield absorbs 100, does 100 accumulate as damage)?
- Does SK-92 Anti-Heal reduce accumulated healing (anti-heal applied during the buff)?
- Does SK-73 Death Immunity interact (if the ally has death immunity and deferred resolution, what happens on expiry)?
- Does SK-93 Death Prevention trigger on the expiry death (death prevention intercepts the net-damage death)?
- Can the ally see their own hidden ledger (UI showing accumulated damage vs healing)?
- Can enemies see that the ally has the buff (knowing they can "bank" damage for the expiry)?
- Does SK-46 Adaptation's accumulator track the deferred damage (damage is suppressed — does Adaptation see it)?
- If the ally enters SK-91 Stasis during the buff, does the buff timer pause (stasis pauses all timers)?
- Does SK-114 Piercing Execute bypass the deferred resolution (instant kill regardless)?
- What happens if the buff is cleansed before expiry (SK-15 Purify) — is the current NET applied immediately, or is all accumulated change discarded?
