# SK-56: Knockback Projectile

## Designer Intent

I hit a target so hard they become the projectile. They fly backward, bowl through other enemies on
the way, and take bonus impact damage if they slam into terrain.

## Primitive Composition

P-32 (Actor Spawning) → P-02 (Forced Displacement)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Enemy target in melee range

## Observable Behavior

1. The target takes the initial punch damage and is launched backward away from the caster.
2. During flight, the launched target cannot act.
3. Other enemies the launched body passes through take pass-through damage and a brief mini-stun.
4. The launched target continues through those enemies; it does not stop on first body contact.
5. If the launched target hits a wall, it stops and takes bonus impact damage.
6. If no wall is hit, it stops when the authored knockback distance is exhausted.
7. The pass-through damage is attributed to the original caster, not to the launched target.

## Engine Primitives Required

This is already the canonical `displacement + flight_policy` path.

1. The punch applies an initial ordinary damage payload from the caster to the target.
2. The same effect then applies one authored `displacement` to the target, moving it away from the
   caster over the configured flight duration.
3. The displacement carries a `flight_policy` with:
   - collision radius for body-as-projectile overlap
   - per-flight dedup (`unique_hit_scope = entity_once_per_flight`)
   - `continue_after_entity_hit = true`
   - `pass_through_effects` for damage + brief hard-disable on newly hit enemies
   - `wall_impact_effects` for the launched target's bonus impact damage
4. A fixed-duration hard-disable on the launched target covers the "cannot act while flying"
   behavior during the authored flight window.

No special projectile actor is required. The target remains the authoritative entity; the flight
overlay only changes how its forced displacement resolves collisions while the knockback is active.

## Cross-Boundary Concerns

The flight overlay follows the displaced target's authority:

1. If the launched target crosses an Arbiter boundary mid-flight, the displacement state and its
   per-flight hit ledger transfer with the target through ordinary handoff.
2. Newly overlapped pass-through victims are still resolved on their own authoritative owners using
   the same target-side relay rules as any other effect.
3. The original caster remains the damage source for pass-through and wall-impact payloads; the
   launched target does not become the new source of those effects.

## Compiler Requirements

Designer specifies:

- melee target admission
- initial punch damage
- knockback distance / duration
- pass-through damage and mini-stun duration
- wall-impact bonus damage

Compiler emits:

- one initial damage payload
- one authored `displacement` away from the caster
- one `flight_policy` with collision radius, per-flight dedup, pass-through payloads, and optional
  wall-impact payloads
- one short action-lock / hard-disable window on the launched target for the duration of the flight

Compiler validates:

1. `flight_policy.collision_radius > 0`
2. at least one of `pass_through_effects` or `wall_impact_effects` is present
3. the launched target remains the displacement owner; the compiler does not synthesize a second
   projectile actor for this mechanic

## Resolved Interaction Notes

- Unstoppable/displacement immunity blocks the launch because the movement is still authored CC.
- The launched target may still be healed or buffed by allies during flight unless the game authors
  additional targetability restrictions.
- Pass-through damage is sourced from the original caster, so reflection/thorns evaluate against
  that source identity.
- Terrain walls and other ordinary world blockers count as wall-impact stops if they admit world
  collision for the displacement path.
