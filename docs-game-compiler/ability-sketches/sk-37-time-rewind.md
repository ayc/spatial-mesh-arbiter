# SK-37: Time Rewind

## Designer Intent

I activate this ability to revert my position and HP to what they were 3 seconds ago. I snap back to where I was, and my health is restored to whatever it was at that moment. Everything else (cooldowns, buffs, debuffs) stays current — only position and HP rewind.

## Primitive Composition

P-05 (Historical State Buffer) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — caster disappears from current position
2. Caster reappears at the position they occupied 3 seconds ago
3. Caster's HP is restored to the value it was 3 seconds ago (could be higher or lower than current)
4. If HP 3 seconds ago was lower than current: caster LOSES health (rewinding into a worse state)
5. Cooldowns, buffs, debuffs, resource — all remain at their CURRENT values (no rewind)
6. Visual: time-reverse particle trail from current position through recent movement path to destination

## Engine Primitives Required

### Ability-Driven Rolling Buffer

The rewind is NOT a global engine feature. It's an ability that opts the caster into snapshot recording via a hidden status effect:

```
status_effect: TimeRewindRecorder {
    buffer: RingBuffer<RewindSnapshot, 180>,  // 3 seconds at 60Hz
    write_index: usize,
}

struct RewindSnapshot {
    position: Vec2F,
    hp: SimFixed,
    tick: u64,
}
```

**Lifecycle:**
1. When the caster equips/learns the Time Rewind talent, the compiler applies the `TimeRewindRecorder` hidden effect
2. Each tick: the effect's per-tick evaluation writes `(position, hp, tick)` to the ring buffer
3. When the ability is activated: read the oldest entry in the buffer (3 seconds ago), snap position and set HP
4. When the talent is unlearned/unequipped: effect is removed, buffer is freed

**Cost:**
- Per-entity, opt-in only — entities without the talent have zero overhead
- 180 entries × (8 + 4 + 8 bytes) = ~3.5 KB per entity with the talent
- One write per tick (append to ring buffer) — negligible
- The buffer is part of the entity's status effect extension state, not a global engine structure

### Position Snap
Same instant position snap as SK-35 and SK-36. No traversal, no intermediate positions.

### HP Overwrite
The rewind directly sets `soft_state.hp = snapshot.hp`. This bypasses damage/heal resolution — it's not "dealing damage" or "healing," it's a state overwrite. This means:
- No on-hit procs trigger
- No on-heal procs trigger
- No damage/heal numbers display (optional: show the delta as a special "rewind" indicator)
- Shield (SK-17) is not affected — only base HP rewinds

## Cross-Boundary Concerns

TODO: The stored position from 3 seconds ago might be in a different Arbiter's region:

1. **Caster hasn't moved far:** Position is in the same Arbiter. Simple snap.
2. **Caster crossed a boundary in the last 3 seconds:** Stored position is in the previous Arbiter's region. Instant cross-boundary handoff required (same problem as SK-35/SK-36).
3. **Topology changed in the last 3 seconds:** The stored position's owning Arbiter may have changed due to split/merge. The rewind needs to query the current owner.

Additional concern: the `TimeRewindRecorder` buffer snapshots are recorded on whichever Arbiter the entity was on at each tick. If the entity crossed boundaries during the 3-second window, some snapshots were recorded on Arbiter A and some on Arbiter B. But the buffer travels with the entity during handoff, so the current Arbiter has the complete buffer. The stored positions are absolute world coordinates, not relative to any Arbiter — so they're valid regardless of which Arbiter recorded them.

## Compiler Requirements

TODO: Designer specifies:
- Passive component: "while this talent is equipped, record position and HP every tick in a 3-second ring buffer"
- Active component: "on activation, read the 3-second-old snapshot, snap position, set HP"

Compiler produces:
- Hidden status effect definition (`TimeRewindRecorder`) with ring buffer allocation
- Per-tick write hook (append current position + HP to buffer)
- Active ability definition that reads the buffer and applies the rewind
- Buffer size validation: compiler calculates `duration_ticks = duration_seconds * 60` and sets the ring buffer capacity

The compiler validates:
- Buffer is bounded (fixed capacity, not growable)
- Per-tick cost is O(1) (append to ring buffer)
- Ability correctly reads from the buffer (oldest entry, not newest)
- Buffer is allocated/freed with the effect lifecycle

## Open Questions

- If the position from 3 seconds ago is inside a SK-03 Terrain Wall that was placed since then, where does the caster appear?
- If the caster was dead 3 seconds ago (revived by SK-18 Resurrect within the window), does the rewind kill them?
- Does the HP overwrite interact with shields — if the caster had no shield 3 seconds ago but has one now, is the shield removed?
- Should the buffer record additional state beyond position and HP? (Resource/mana? Active effects?)
- Can the rewind be used while CC'd (stun/root/silence)?
- Does the rewind trigger SK-32 Minefield at the destination?
- If the caster has SK-04 Tether active, does the rewind snap break the tether?
- Is 3 seconds at 60Hz (180 snapshots) the right granularity, or can the buffer sample at a lower rate (every 3rd tick = 60 snapshots) to save memory?
- When multiple entities have this talent in a Blackhole scenario (200+ entities with recorders), what is the total memory cost? (200 × 3.5 KB = 700 KB — bounded and reasonable)
- Does the rewind visual (showing the caster's movement path in reverse) require the buffer to be sent to the client, or is it purely cosmetic and client-predicted?
