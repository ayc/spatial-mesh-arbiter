# SK-39: Spectral Dash

## Designer Intent

I send a wave of banshees forward in a line. The wave travels as a projectile. At any point while the wave is in flight, I can reactivate to instantly teleport to the wave's current position. If I don't reactivate, the wave dissipates at max range and nothing happens.

## Primitive Composition

P-32 (Actor Spawning) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (from requested aim direction)
- Reactivation input (same ability key, while wave is in flight)

## Observable Behavior

1. Cast — wave launches from caster in the specified direction
2. Wave travels forward at a constant speed (like a projectile, but passes through enemies without hitting)
3. While the wave is in flight: ability icon changes to "Teleport" — pressing it teleports the caster to the wave's current position
4. If reactivated: caster disappears and appears at the wave's position instantly. Wave dissipates.
5. If not reactivated: wave reaches max range and dissipates. Ability goes on cooldown.
6. The wave does not deal damage or interact with entities — it's purely a mobility tool
7. Visual: ghostly banshee wave traveling forward, caster dissolves and reforms at the wave on reactivation

## Engine Primitives Required

Spectral Dash is now a canonical moving-bookmark projectile pattern built from one live projectile
reference plus one same-key reactivation variant.

The recommended lowering is:

1. Define one runtime state:
   - `state_id = spectral_dash_wave_ref`
   - `kind = bookmark(entity_ref)`
   - `expires_after_ticks = wave_lifetime_ticks`
   - `clear_on_owner_death = true`
2. Base cast variant:
   - `spawn_actor {`
     `count = 1,`
     `output_binding = spectral_dash_wave,`
     `projectile = {`
       `speed = ... ,`
       `detonation_policy = { entity_impact = ignore, world_impact = ignore, expiry = despawn }`
     `}`
   - `write_state(state_id = spectral_dash_wave_ref, capture = entity_ref, entity = { binding: spectral_dash_wave })`
3. Reactivation variant:
   - `when = { state_present: spectral_dash_wave_ref }`
   - `effects = [restore_from_state(target = caster, state_id = spectral_dash_wave_ref,`
     `apply_position = true, position_validation = nearest_walkable),`
     `despawn_entity(target = { state_entity: spectral_dash_wave_ref }, reason = "spectral_dash_reactivate"),`
     `clear_state(state_id = spectral_dash_wave_ref)]`

This keeps the mechanic inside existing canonical surfaces:

- the moving destination is a `bookmark(entity_ref)` runtime state, not a bespoke status link
- the reactivation path is ordinary `ActivationModes`
- teleport destination resolution is late-bound from the projectile's CURRENT position at cast time

## Cross-Boundary Concerns

Spectral Dash follows the ordinary projectile handoff and teleport-destination rules.

1. The wave projectile hands off exactly like any other projectile actor if it crosses an Arbiter
   boundary.
2. The runtime state stores only the stable projectile actor ID, not a cached Arbiter identity.
3. On reactivation, `restore_from_state` resolves the projectile's CURRENT local-or-Ghost position
   at execution time. If that position now belongs to another Arbiter, the caster's teleport uses
   the ordinary destination-based cross-boundary handoff path.
4. Manual use, natural expiry, or owner death all clear the reactivation state, so the same-slot
   teleport variant disappears cleanly instead of leaving a stale actor reference behind.
5. Mid-handoff cases are handled by the same handoff-stable live-projectile state used for normal
   projectile ownership transfer; the reactivation lookup follows the projectile's current
   authoritative owner.

## Compiler Requirements

Designer specifies:

- wave speed
- wave lifetime / max range
- observer presentation
- same-key reactivation routing
- any broader teleport constraints that should also apply to the return snap

Compiler emits:

- one non-damaging single-spawn projectile actor with `output_binding`
- one `bookmark(entity_ref)` runtime state that stores the live projectile reference
- one `ActivationModes` reactivation variant gated on `state_present`
- one reactivation effect list that teleports to the projectile's current position, despawns the
  projectile, and clears the runtime state

Compiler validates:

1. `count = 1` because a single live actor reference is stored
2. the referenced runtime state exists and is `bookmark(entity_ref)`
3. the runtime-state lifetime is bounded and aligned with the projectile's flight window
4. the base cast remains non-damaging; this reference does not smuggle a weapon payload into the
   mobility projectile

## Resolved Interaction Notes

- This reference assumes the wave ignores both entity and world collision. It is a mobility marker,
  not a damage source or wall probe.
- The caster may move and use other abilities while the wave is in flight; only the same public
  ability slot is redirected to the teleport variant.
- Because reactivation is still a normal same-slot cast, stun and silence block it normally. Root,
  leash, or other movement constraints only clamp the teleport if their authored rules also apply
  to teleports.
- If the wave expires naturally, nothing happens beyond the ordinary cooldown; the teleport option
  simply disappears.
- If the caster dies, `clear_on_owner_death = true` removes the stored wave reference so no
  post-death teleport remains.
