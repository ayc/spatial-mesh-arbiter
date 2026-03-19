# SK-44: Burrow

## Designer Intent

I burrow underground for 2 seconds. While burrowed, I am invulnerable (take no damage), untargetable (cannot be selected by any ability), and unable to act. I heal rapidly while underground. I can reactivate early to emerge before the 2 seconds are up.

## Primitive Composition

P-27 (Targetability Overrides) → P-33 (Entity Dormancy)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)
- Optional reactivation to emerge early

## Observable Behavior

1. Activate — caster burrows underground instantly
2. While burrowed: caster is invulnerable (all incoming damage is negated)
3. While burrowed: caster is untargetable (cannot be selected as a target by any ability — friendly or hostile)
4. While burrowed: caster cannot move, attack, or cast
5. While burrowed: caster heals for X HP per second
6. After 2 seconds (or on reactivation): caster emerges at the same position
7. All previously applied debuffs continue ticking but deal no damage (invulnerable) — or are they paused?
8. Visual: caster sinks into the ground, dirt mound visible, emerges with a burst

## Engine Primitives Required

### Invulnerability State
A new entity state flag: `is_invulnerable`. When true:
- All incoming damage events resolve to 0 (not blocked, not evaded — just negated)
- DoT ticks deal 0 damage
- Reactive procs that trigger on "taking damage" (SK-27 Sleep break, SK-22 Reflection) do NOT trigger (no damage was taken)
- Shield (SK-17) is NOT consumed (no damage reaches it)

### Untargetable State
A new entity state flag: `is_untargetable`. When true:
- The entity is excluded from ALL targeting queries (friendly and hostile)
- Skillshot projectiles (SK-43 Drag) pass through the entity as if it doesn't exist
- AoE abilities (SK-29 Blizzard, SK-08 Aura) do not affect the entity even if it's within radius
- Auto-targeting (SK-42 Withering Fire) skips the entity entirely
- Allies cannot target the entity with heals or buffs (SK-16 Holy Ground pulses skip it, SK-15 Purify cannot select it)
- The entity still has a position in the entity map — it's not despawned, just invisible to the combat system

### Interaction with Ghost System
If the burrowed entity is near an Arbiter boundary, it still exists as a Ghost to neighbors — but does the Ghost carry the untargetable/invulnerable flags? If not, neighbors might attempt to relay damage to a burrowed entity, which would be rejected by the owning Arbiter. If yes, it saves the wasted relay.

### Self-Heal During Burrow
A simple per-tick heal on the burrowed entity. Since the entity is invulnerable, this is uncontested — no incoming damage competes with the healing. The heal is a direct HP modification, not a "heal event" that triggers on-heal procs.

## Cross-Boundary Concerns

TODO: The burrowed entity is on a specific Arbiter. Cross-boundary concerns are minimal because:
- The entity can't move (no handoff risk)
- The entity is untargetable (no incoming relays)
- The entity is invulnerable (even stale relays that arrive are negated)

The main concern: does the Ghost representation update to reflect the burrowed state? Neighbors should know the entity is burrowed so they:
1. Don't waste relay messages targeting it
2. Can visually represent the burrowed state to their local clients
3. Exclude it from their own spatial queries (AoE, aura, vortex)

Does GhostUpdate need `is_untargetable: bool`? Currently GhostUpdate carries position, velocity, movement_class — no capability/state flags.

## Compiler Requirements

TODO: Designer specifies: self-cast, duration (2s), invulnerable + untargetable + unable to act, self-heal per tick, reactivatable (emerge early). Compiler produces:
- Status effect with flags: `is_invulnerable: true`, `is_untargetable: true`, `can_move: false`, `can_attack: false`, `can_cast: false` (except reactivation)
- Per-tick heal hook
- Reactivation removes the effect early (multi-phase like SK-36)
- Duration expiry removes the effect

The compiler needs to validate that invulnerability and untargetability are consistent — you shouldn't be invulnerable but targetable (enemies waste abilities) or untargetable but vulnerable (edge case if someone finds a way to deal damage without targeting).

## Open Questions

- Do existing debuffs (DoTs, slows) pause during burrow, or do their timers keep ticking (but deal no damage)?
- If a DoT timer expires during burrow, is the DoT removed, or does it persist?
- Can the burrowed entity be displaced (SK-01 Toss, SK-31 Vortex pull)? Untargetable should prevent Toss, but Vortex is area-based.
- Can the entity burrow to dodge a projectile already in flight (projectile arrives, entity is now untargetable — does it pass through)?
- Does the heal-over-time count as "healing received" for SK-04 Tether sharing?
- Is the burrowed entity visible on the minimap / to enemies? Or is it hidden like SK-32 Minefield stealth?
- Can the burrowed entity be revealed by detection abilities?
- Does burrow break SK-04 Tether (untargetable partner)?
- If the burrowed entity has SK-08 Aura, does the aura continue affecting nearby enemies (entity exists, just untargetable)?
- Does emerging from burrow trigger SK-32 Minefield if a mine was placed on top during burrow?
