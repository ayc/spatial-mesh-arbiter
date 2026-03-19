# SK-64: Mosh Pit

## Designer Intent

I channel a performance so sick that all nearby enemies can't help but headbang. For up to 4 seconds while I channel, all enemies within radius are stunned. If I'm interrupted, the stun ends immediately. Enemies who walk into the area mid-channel are also caught.

## Primitive Composition

P-09 (Shape Overlap Query) → P-26 (Capability Bitmask) → P-14 (Continuous Proximity Monitor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (AoE centered on caster)

## Observable Behavior

1. Channel begins — all enemies within radius are stunned
2. Stun persists for as long as the channel continues (up to 4 seconds)
3. Enemies who enter the radius mid-channel are stunned on entry
4. Enemies who are displaced OUT of the radius (by an ally's ability) are freed
5. If the caster is interrupted (stun, silence, displacement): channel ends, ALL stuns end immediately
6. Caster cannot move while channeling
7. The caster is vulnerable during the channel — enemies outside the radius can interrupt
8. Visual: rock concert stage effect, affected enemies headbanging

## Engine Primitives Required

### Channel-Bound Persistent CC Zone

This combines channeling (SK-05 Global Strike) with a CC zone (SK-29 Blizzard), but with a critical property: **the CC only exists while the channel is active**. When the channel ends, ALL applied stuns from this ability are immediately removed.

This is different from:
- SK-24 Stun: fixed duration, independent of the caster
- SK-29 Blizzard: zone persists independently of the caster
- SK-05 Global Strike: channel produces a one-time effect at the end

Mosh Pit's stun has no independent duration — it's directly tethered to the channel state.

```
struct MoshPitChannel {
    caster_id: EntityID,
    radius: SimFixed,
    affected_entities: HashSet<EntityID>,  // Currently stunned by this channel
}
```

Each tick during the channel:
1. Query enemies within radius
2. New entries (not in `affected_entities`): apply stun, add to set
3. Entities that left the radius: remove stun, remove from set
4. If channel ends: remove stun from ALL entities in `affected_entities`

### Enter/Leave with CC Application

Unlike SK-08 Aura (continuous debuff refresh) or SK-29 Blizzard (pulsed effects), Mosh Pit applies CC on enter and removes it on leave. The stun is not independent — it's managed by the zone:
- Enter zone: apply stun (no duration — it lasts as long as you're inside)
- Leave zone: remove stun
- Channel ends: remove stun from everyone

This is **zone-managed CC** — the zone owns the stun's lifecycle, not the stun itself.

### Channel Vulnerability

The caster is deliberately vulnerable. Unlike SK-44 Burrow (invulnerable during) or SK-51 Unstoppable (CC immune during), the Mosh Pit channeler CAN be interrupted. The channel is a high-risk, high-reward ability — 4 seconds of AoE stun if uninterrupted, but a single stun/silence on the caster cancels everything.

Enemies outside the Mosh Pit radius are the intended counterplay — they can walk up and stun the channeler.

## Cross-Boundary Concerns

TODO: The Mosh Pit zone is centered on the caster. Enemies near the boundary who are Ghosts enter the radius — the caster's Arbiter needs to relay "apply stun" to the Ghost's owning Arbiter. On channel end, the caster's Arbiter must relay "remove stun" to all affected Ghost owners.

If an affected Ghost crosses a boundary during the channel (entity handoff), the new Arbiter needs to know this entity is Mosh Pit stunned. Does the stun effect transfer with the handoff, or does the caster's Arbiter lose track?

The continuous enter/leave checking for Ghosts at 60Hz generates cross-boundary traffic proportional to the number of Ghosts near the Mosh Pit border.

## Compiler Requirements

TODO: Designer specifies: channel (up to 4s), AoE radius centered on caster, stun all enemies inside, stun bound to channel (no independent duration), enter/leave CC management, interruptible, caster immobile. Compiler produces:
- Channel definition with AoE zone
- Zone-managed CC: stun applied on enter, removed on leave, removed on channel end
- Affected entity tracking set
- Channel break → mass stun removal hook

The compiler needs to express **channel-bound effects** — status effects whose lifecycle is tied to a channel, not to their own timer.

## Open Questions

- Does Tenacity reduce the effectiveness (enemies can "resist" partially)?
- Does Diminishing Returns (SK-28) apply to Mosh Pit stun?
- Does SK-51 Unstoppable prevent Mosh Pit stun (yes — CC immunity)?
- Can the channeler be displaced OUT of their own Mosh Pit (ending it)?
- If an affected enemy is cleansed (SK-15 Purify), are they re-stunned next tick (still in radius)?
- Does the stun prevent passive effects (SK-23 Thorns) from triggering on the stunned entity?
- Can an ally's SK-01 Toss knock an enemy out of the Mosh Pit (freeing them)?
- If the channeler is silenced, does Mosh Pit end (silence blocks casting — does it end channels)?
- What happens if two Mosh Pits overlap — double stun from two different sources?
- Performance: per-tick enter/leave detection for a potentially large radius — bounded?
