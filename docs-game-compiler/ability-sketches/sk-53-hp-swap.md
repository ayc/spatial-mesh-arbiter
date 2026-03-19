# SK-53: HP Swap

## Designer Intent

I channel on an enemy for 2 seconds. When the channel completes, our HP percentages are swapped. If I'm at 20% HP and they're at 80% HP, after the swap I'm at 80% and they're at 20%. This lets me dive in, take damage, then swap to steal the enemy's health advantage.

## Primitive Composition

P-17 (Conditional Thresholds) → P-15 (Value Modification)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Channel on an enemy for 2 seconds (can be interrupted)
2. During channel: both entities can take damage normally (percentages keep changing)
3. On channel complete: read both entities' current HP as a percentage of their max HP
4. Caster's HP is set to (target's percentage × caster's max HP)
5. Target's HP is set to (caster's percentage × target's max HP)
6. The swap is instantaneous — happens in a single tick
7. Neither entity can die from the swap (minimum 1 HP after swap)
8. Visual: dark energy connecting both entities during channel, dramatic HP bar swap on completion

## Engine Primitives Required

### Bidirectional HP Percentage Swap

This is the first ability that **reads AND writes HP on two entities simultaneously** in a single atomic operation. The swap must be atomic — you can't set the caster's HP first (based on target's percentage) and then set the target's HP (based on caster's old percentage that was already overwritten).

```
fn resolve_hp_swap(caster: &mut Entity, target: &mut Entity) {
    let caster_pct = caster.hp / caster.max_hp;  // Fixed-point division
    let target_pct = target.hp / target.max_hp;

    caster.hp = max(1, target_pct * caster.max_hp);  // Minimum 1 HP
    target.hp = max(1, caster_pct * target.max_hp);
}
```

Both reads must happen BEFORE either write. This is trivially safe when both entities are on the same Arbiter (local variables). But cross-boundary...

### HP Overwrite (Not Damage or Heal)

Like SK-37 Time Rewind, the HP change is a **state overwrite**, not a damage or heal event:
- No on-hit procs trigger
- No on-heal procs trigger
- No damage numbers display
- Shields (SK-17) are NOT affected (only base HP swaps)
- SK-46 Adaptation's damage accumulator does NOT count the HP loss as "damage taken"
- SK-22 Damage Reflection does NOT fire (no incoming damage event)

The HP overwrite bypasses the entire combat pipeline. It's a direct SoftState mutation.

## Cross-Boundary Concerns

TODO: This is the hardest cross-boundary problem in the sketch set. If caster and target are on different Arbiters:

1. **Channel phase:** Caster channels on their Arbiter. Target is a Ghost. Channel break conditions (interrupt, range) are checked locally.

2. **Swap resolution:** On channel complete, the caster's Arbiter needs the target's CURRENT HP percentage. But the target is a Ghost — Ghosts don't carry HP data (only position, velocity, movement_class).

Options:
- **Query the target's Arbiter:** Send a "what is your HP percentage right now?" request. But this adds a round-trip at the critical moment. During the round-trip, both entities' HP can change.
- **Relay the swap to the target's Arbiter:** Caster's Arbiter sends "set your entity to X% HP, and tell me what their percentage was." Target's Arbiter responds with the old percentage. Caster's Arbiter sets caster HP. Problem: two-message round-trip, non-atomic.
- **Optimistic swap:** Caster's Arbiter uses the last known Ghost HP approximation (if Ghosts carried HP). Not accurate for a critical ability.
- **Require same Arbiter:** Only allow the ability on non-Ghost targets. Limits usability near boundaries.

This ability may fundamentally require both entities to be on the same Arbiter for correct resolution. That's a unique constraint.

## Compiler Requirements

TODO: Designer specifies: channel (2s), on-complete (swap HP percentages), minimum 1 HP, not damage/heal (bypasses combat pipeline), interruptible. Compiler produces:
- Channel definition with target reference
- On-complete hook: atomic HP percentage swap
- HP overwrite (not damage/heal event)
- Same-Arbiter requirement or cross-boundary resolution strategy

The compiler needs to flag this ability as requiring **simultaneous read/write access to two entities' state** — a constraint no other ability has. This may need a new resolution category beyond "external action" and "internal relay."

## Open Questions

- Can the swap kill either entity? (Minimum 1 HP prevents this, but should it?)
- Does the swap account for shields — swap total effective HP (HP + shield) or just base HP?
- If the target gains or loses HP between channel start and channel end, the swap uses END values — is this correct?
- Can the swap be used on allies (heal swap — give your high HP to a low-HP ally)?
- Does Unstoppable (SK-51) prevent the HP swap? It's not CC — it's a state mutation.
- Does invulnerability (SK-44 Burrow) prevent the HP swap? Burrow prevents damage, but the swap isn't damage.
- If the caster is at 1% HP and the target has SK-19 Guardian Angel active, does the swap interact with the redirect?
- What happens if the target dies during the channel (before swap completes)?
- Can the swap target entities with different max HP pools (caster has 5000 max HP, target has 2000)?
- How does the swap interact with SK-46 Adaptation — if the caster takes 3000 damage then swaps to 80% HP, does Adaptation heal for the 3000 damage taken before the swap?
