# SK-91: Team-Agnostic Stasis

## Designer Intent

I create a void prison at a target area. After a brief delay, ALL entities inside — enemies AND allies — are put in stasis for 5 seconds. Entities in stasis can't act, can't be damaged, can't be targeted. This is a strategic tool: freeze enemies to set up a combo, but accidentally freezing your own allies is a misplay.

## Primitive Composition

P-33 (Entity Dormancy) → P-27 (Targetability Overrides) → P-13 (Tag/Allegiance Filtering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position (requested ground-target position)

## Observable Behavior

1. Cast at target position — visible indicator appears (0.5s delay before activation)
2. After delay: ALL entities in the area enter stasis (friend AND foe, including the caster if inside)
3. Stasis: can't act, invulnerable, untargetable — effectively frozen in time
4. Duration: 5 seconds (fixed; not reduced by Tenacity / status resistance)
5. When stasis ends: all affected entities resume exactly where they were
6. Entities OUTSIDE the area when it activates are NOT affected (snapshot at activation)
7. Entities cannot enter the stasis zone after activation (it's a one-time effect, not a persistent zone)
8. The stasis is NOT cleansable (cannot be removed early by any means)
9. Visual: purple crystal prison effect, frozen entities, time-stopped area

## Engine Primitives Required

Team-Agnostic Stasis is now a canonical `SuspensionBlock(mode = stasis)` reference.

The recommended lowering is:

1. resolve the delayed area as one snapshot query after the 0.5s warning window
2. use `filter = all_alive` for that activation-time query so allies, enemies, and the caster are
   all admitted if they are inside
3. apply one negative uncleansable stasis status to every admitted entity with:
   - `suspension = {`
     `mode = stasis,`
     `invulnerable = true,`
     `pause_status_timers = true,`
     `pause_ability_cooldowns = true,`
     `interrupt_active_casts = true,`
     `interrupt_active_channels = true`
     `}`
   - targetability / collision overrides that make the target untargetable and non-blocking while
     the stasis is active
   - `is_cleansable = false`
4. let the canonical stasis expiry-shift rule resume timers when the status ends

This keeps the mechanic inside existing compiler surfaces:

- team-agnostic targeting is the canonical `all_alive` filter
- full time-stop behavior is the canonical `stasis` suspension mode
- untargetability and non-interaction are ordinary targetability overlays on the same status

## Cross-Boundary Concerns

Team-Agnostic Stasis is snapshot-at-activation and target-owner authoritative.

1. The area owner's Arbiter runs the delayed activation query using current local and Ghost poses at
   the activation tick.
2. Any admitted remote/Ghost entity is relayed to its current owner, which admits the stasis status
   locally and pauses that entity's timers there.
3. Later movement into or out of the area is irrelevant because this reference is not a persistent
   zone; it is one delayed snapshot application.
4. Once admitted, all targeting, AoE admission, and timer-pause behavior are handled entirely on
   the stasis target's owner. No cross-boundary special case exists beyond the initial relay.

## Compiler Requirements

Designer specifies:

- ground-target position
- warning delay
- radius
- duration
- snapshot filter of `all_alive`
- uncleansable stasis behavior

Compiler emits:

- one delayed snapshot area query using `all_alive`
- one negative status with canonical `suspension.mode = stasis`
- one targetability / collision overlay that makes affected entities untargetable and non-blocking

Compiler validates:

1. the one-time capture is authored as a delayed snapshot effect, not a persistent zone
2. `is_cleansable = false` for this reference
3. timer pausing uses canonical `stasis` suspension flags rather than a bespoke per-timer script

## Resolved Interaction Notes

- The caster is affected too if they are still inside when the delay ends; this is a true
  team-agnostic snapshot.
- Entities may dodge out during the warning window because admission happens only at the activation
  tick.
- Stasis pauses attached status timers and ability cooldowns through the canonical expiry-shift
  rule; it does not require one-off logic for every affected mechanic.
- Unstoppable / Super Armor do not create a special exception here. Any immunity interaction must be
  authored through the same canonical status-admission rules used elsewhere.
