# SK-89: Respawn Anchor

## Designer Intent

I place a hidden egg at a location. If I later die while the egg still exists, my next respawn is
routed through that egg instead of the normal long respawn flow: I come back there after 5 seconds,
then the egg is consumed because I have "hatched." If enemies find and destroy the egg first, or
destroy it during the 5-second rebirth window, the override is lost and I fall back to my normal
respawn.

## Primitive Composition

P-32 (Actor Spawning) → P-39 (On-Death Hook) → P-52 (Asymmetric Team-Rendering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position for egg placement (ground-targeted)

## Observable Behavior

1. Place one egg at the target position
2. The egg is visible to self/allies and hidden from enemies until ordinary reveal/detection rules expose it
3. The egg is stationary, low-HP, and destructible
4. Only one egg may exist at a time; placing a new egg despawns the old one
5. If the caster reaches terminal death while the egg still exists, the next respawn is rerouted to
   the egg's position after 5 seconds instead of using the normal long respawn timer
6. The egg remains vulnerable during that 5-second rebirth window
7. If enemies destroy the egg before the respawn actually commits, the rebirth is canceled and the
   normal respawn schedule resumes
8. On successful respawn at the egg, the egg is consumed
9. Respawn state is the ordinary Meta spawn state, not a corpse revive or preserved in-combat body state

## Engine Primitives Required

Respawn Anchor is now a canonical `spawn_actor` rebirth pattern.

The compiler lowers it to one `spawn_actor` effect with:

1. `count = 1`
2. `position = target position`
3. a static egg archetype with low HP, no movement, and authored observer/targetability policy
4. `instance_limit = { scope = owner_by_ability, max_live = 1, overflow_policy = despawn_oldest }`
5. `respawn_anchor = { respawn_delay_ticks = 300 }`
6. ordinary `observer_presentation` / `targetability_policy` authoring for ally visibility and enemy discovery / destruction

The egg is still an ordinary spawned actor. `respawn_anchor` does not invent a second stealth,
revive, or container system. It only gives that actor one extra role: if its resolved `owner`
commits terminal death while the anchor is still alive, Stage 10 may attach a bounded respawn
override to `PlayerDied`.

## Post-Terminal Respawn Route

When the owner reaches terminal death and the egg is still alive, the runtime emits:

- ordinary `PlayerDied` kill credit / death signaling
- `respawn_override = Some(RespawnAnchor { anchor_entity_id, position, respawn_delay_ticks = 300 })`

Meta stores both:

- the ordinary base respawn schedule for that death
- the shorter anchor override schedule

If the egg is removed before the rebirth commits, the anchor owner emits
`RespawnOverrideRevoked { victim, source_entity_id }`. Meta clears the override and falls back to
the stored base respawn schedule measured from the original death time.

When the 5-second anchor schedule expires, Meta executes the normal spawn handshake at the egg's
position and includes `respawn_context = Some(RespawnSpawnContext::RespawnAnchor { anchor_entity_id })`.
The target Arbiter validates that the egg still exists, consumes it atomically, and materializes
the player at the egg's authoritative position. If validation fails, the Arbiter emits the same
revocation event and does not spawn the player there.

This keeps the override revocable until the actual spawn commit, which is required because enemies
are allowed to destroy the egg during the 5-second window.

## Hidden Placement and Enemy Counterplay

The egg reuses the ordinary observer/targetability surfaces.

- Allies and self can see the egg normally
- Enemies do not receive it in downstream payloads until the game's reveal/detection policy exposes it
- Once revealed, it is just an ordinary low-HP hostile target and can be attacked normally

So "hidden egg that enemies can still stumble across and destroy" is downstream observer filtering
plus ordinary destructible-actor rules, not a bespoke hidden-entity mechanic.

## Cross-Boundary Concerns

The death Arbiter and the egg Arbiter may be different.

1. Stage 10 on the death Arbiter resolves whether a live rebirth anchor exists for the owner and
   snapshots its current authoritative position / anchor ID into `PlayerDied`
2. Meta does not query live egg state directly; it consumes the death-time snapshot plus later
   `RespawnOverrideRevoked` events
3. If the egg hands off because of topology changes, it remains the same authoritative live actor;
   the override still points at that actor ID and current position
4. Final validation happens on the target Arbiter during the respawn commit, so late destruction
   still cancels the rebirth cleanly

## Compiler Requirements

Designer specifies:

- target ground position
- egg lifetime and HP
- observer-presentation / reveal policy
- one-at-a-time live limit
- rebirth delay override

Compiler emits:

- one `spawn_actor` effect with `respawn_anchor = { respawn_delay_ticks = 300 }`
- one egg entity archetype with authored observer/targetability metadata
- one owner-scoped live-anchor registration
- HardEvent / Meta respawn-route metadata for the owner's next terminal death while the egg lives

Compiler validates:

1. `count = 1` when `respawn_anchor` is authored
2. `respawn_delay_ticks > 0`
3. the mechanic uses ordinary spawned-actor, observer, and targetability surfaces rather than
   sketch-local revive flags

## Resolved Interaction Notes

- The 5-second timer replaces the normal respawn timer for that death only while the egg remains valid
- The egg survives owner death, but only until it is destroyed or successfully consumed on respawn
- Egg replacement is immediate: placing a second egg despawns the first one
- The egg is soft-state only; disconnect/crash does not make it durable
- If the owner first uses a pre-terminal phase such as `ghost_phase`, the rebirth anchor is checked
  only when terminal death finally commits
