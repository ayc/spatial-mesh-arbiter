# SK-46: Adaptation

## Designer Intent

I activate this ability and a 4-second window begins. At the end of the window, I am healed for 100% of all damage I took during those 4 seconds. The more damage I take, the bigger the heal. If I take no damage, I get no heal.

## Primitive Composition

P-36 (On-Damage-Received Hook) → P-42 (Stacking Counters w/ Decay) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — a 4-second tracking window begins
2. During the window: every point of damage I take is accumulated in a counter
3. All damage types count: direct hits, DoTs, reflected damage, AoE, everything
4. Damage is still applied normally — I take full damage during the window (not reduced)
5. After 4 seconds: I am healed for 100% of the accumulated damage total
6. The heal is a single burst heal at the end, not a heal-over-time
7. If I die during the 4-second window: the heal never fires (I'm dead)
8. If I take 0 damage during the window: I am healed for 0 (ability was wasted)
9. Visual: glowing adaptive carapace effect, damage counter visible to the player, burst heal on completion

## Engine Primitives Required

### Damage Accumulator
A status effect on the caster that tracks total damage taken over the window:

```
status_effect: AdaptationTracker {
    accumulated_damage: SimFixed,
    expires_at_tick: u64,
}
```

Each time the entity takes damage (during Phase 2 resolution), AFTER the damage is applied to HP, the tracker increments `accumulated_damage` by the amount of HP actually lost.

This is a **post-damage hook** — it fires after damage resolution is complete, reading the delta between pre-damage HP and post-damage HP. It's simpler than SK-37 Time Rewind (which snapshots full state per tick). The accumulator just adds a number.

Key question: what counts as "damage taken"?
- Direct damage: yes
- DoT ticks: yes
- Reflected damage from SK-22: yes (if reflected damage hits you from another source)
- Shield absorption (SK-17): does damage absorbed by a shield count? The HP didn't change, but you "would have taken" that damage.
- Damage redirected via SK-19 Guardian Angel: the guardian takes the redirected portion — does that count for the guardian's Adaptation?

### Deferred Heal on Expiry
When the status effect expires (4 seconds later), the expiry hook:
1. Reads `accumulated_damage`
2. Applies a burst heal to the entity for that amount
3. Removes the effect

This is a **status effect with an on-expiry action** — the effect does something when it's removed by timer, not just when it's applied or while it's ticking. Not all effects have on-expiry actions; most just disappear. The compiler needs to support on-expiry hooks.

### Timing Sensitivity
The heal fires at a specific tick (the expiry tick). If the entity is at 1 HP and takes fatal damage on tick T, but the adaptation heal was scheduled for tick T as well, the ordering matters:
- If damage resolves before the heal: entity dies, heal never fires (dead entities don't heal)
- If heal resolves before the damage: entity survives

The tick processing order must be deterministic: does the adaptation expiry heal resolve before or after incoming damage for that tick?

## Cross-Boundary Concerns

TODO: Minimal cross-boundary complexity. The accumulator runs entirely on the entity's owning Arbiter:
- All damage the entity receives is resolved locally (Phase 2 on the entity's Arbiter)
- The accumulator increments locally
- The expiry heal is local

The only cross-boundary concern: damage arriving via relay (cross-boundary attacks). These relays arrive and are resolved locally on the target's Arbiter, where the accumulator picks them up normally. No special handling needed.

If the entity crosses a boundary during the 4-second window, the AdaptationTracker effect transfers with the entity during handoff. The accumulated value carries over.

## Compiler Requirements

TODO: Designer specifies: self-cast, tracking window (4s), accumulate all damage taken, on-expiry heal for 100% of accumulated amount, does not reduce damage during window. Compiler produces:
- Status effect with `accumulated_damage: SimFixed` field
- Post-damage hook: increment accumulator by HP delta after each damage event
- On-expiry hook: apply burst heal for `accumulated_damage`
- Death check: if entity dies during window, effect is removed without healing

The compiler needs to support three hook points on a status effect:
1. On-apply (when the effect is first applied)
2. Per-tick (recurring logic)
3. On-expiry (logic when the effect naturally expires)
4. On-remove (logic when the effect is dispelled/cleansed — may differ from expiry)

Adaptation uses on-expiry but NOT on-remove — if the effect is cleansed (SK-15 Purify used offensively to remove a beneficial effect), the accumulated heal should NOT fire.

## Open Questions

- Does damage absorbed by shields (SK-17) count toward the accumulator?
- Does damage redirected away via SK-19 Guardian Angel (the 50% you DIDN'T take) count?
- If the entity has damage reduction buffs, does the accumulator track pre-reduction or post-reduction damage?
- Can enemies cleanse/purge the Adaptation buff to prevent the heal (SK-15 in reverse)?
- Does the 100% heal have a cap, or can you take 10,000 damage and heal for 10,000?
- Can the heal critically strike (applying crit to the burst heal)?
- Does the heal trigger on-heal effects (SK-04 Tether healing share)?
- Does Kinematic Dilation affect the 4-second window (dilated time = longer real-time window)?
- If the entity enters SK-44 Burrow during the window (invulnerable), the accumulator stops gaining. Is the window timer paused too, or does it keep ticking?
- Can multiple Adaptation activations stack (two overlapping windows, each tracking independently)?
