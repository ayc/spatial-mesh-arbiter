# SK-74: Hit-Confirmed Dash

## Designer Intent

I fire a skillshot projectile. If it hits an enemy hero, I automatically dash forward a short distance in the cast direction. If I miss, no dash — I stay where I am. Hitting the skillshot is both damage AND a mobility reward.

## Primitive Composition

P-07 (Entity-as-Kinematic-Volume) → P-17 (Conditional Thresholds) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (from requested aim direction)

## Observable Behavior

1. Fire skillshot in the cast direction
2. Projectile travels, checks for first-hit collision (like SK-43 Drag)
3. If HIT: deal damage to the enemy + caster dashes forward (e.g., 3 meters in the cast direction)
4. If MISS (no enemy hit before max range): projectile expires, no dash, ability goes on cooldown
5. The dash is automatic — no second input needed
6. The dash is instant (or very fast — near-instant displacement)
7. The ability's cooldown is reduced on hit (e.g., 6s on hit, 12s on miss)
8. Visual: dark projectile, on-hit: caster slides forward with a flourish

## Engine Primitives Required

Hit-Confirmed Dash is now a canonical first-hit projectile plus hit-only self-follow-up reference.

The recommended lowering is:

1. one first-hit skillshot projectile with:
   - authored speed / max range
   - `detonation_policy = { entity_impact = detonate, world_impact = stop, expiry = despawn }`
   - no pierce
2. the public ability's base cooldown is the miss cooldown
3. on the first admitted enemy impact:
   - deal the ordinary hit damage
   - trigger one hit-only self dash in the original cast direction through canonical
     `kinematic_sweep`
   - use the bounded Lua helper `set_cooldown` to replace the miss cooldown with the shorter
     hit-confirmed cooldown

This keeps the mechanic inside existing bounded surfaces:

- the projectile remains an ordinary first-hit hostile shot
- the movement reward is an ordinary self `kinematic_sweep`, not a bespoke "dash if hit" primitive
- miss-versus-hit cooldown branching stays inside the existing bounded `set_cooldown` fallback

## Cross-Boundary Concerns

The dash decision stays with the projectile / caster owner.

1. The projectile's first-hit admission is determined on the projectile's current owner through the
   ordinary local-or-Ghost collision contract.
2. If the admitted hit target is remote/Ghost, the hostile damage payload still relays to the
   target owner as normal.
3. The hit-only self dash does not wait for a second remote acknowledgment. Once the projectile
   owner has admitted the hit, that same owner schedules the self `kinematic_sweep` and hit-only
   cooldown replacement locally.
4. If the caster crosses an Arbiter boundary during the dash, the sweep follows the existing
   authoritative mover handoff rules just like other `kinematic_sweep` movement.

## Compiler Requirements

Designer specifies:

- projectile speed / range
- dash distance / duration
- miss cooldown
- hit-confirmed cooldown

Compiler emits:

- one first-hit projectile spawn
- one hit-only self `kinematic_sweep` that uses the committed cast direction
- one hit-only `set_cooldown` mutation that replaces the base miss cooldown with the shorter
  hit-confirmed cooldown

Compiler validates:

1. the projectile uses first-hit collision semantics
2. the follow-up movement is expressed through canonical `kinematic_sweep`, not a bespoke mobility
   outcome primitive
3. the hit-only cooldown branch stays inside the bounded `set_cooldown` helper rather than a hidden
   second public ability
4. the hit-confirmed cooldown is non-negative and does not exceed the authored miss cooldown in this
   reference version

## Resolved Interaction Notes

- The dash uses the original cast direction, not a recomputed vector toward the struck target.
- Because the follow-up movement is ordinary mover-owned motion, roots or other movement denial may
  prevent the dash from starting if they are active when the hit-confirmed follow-up would execute.
- The dash is still ordinary movement for downstream interactions, so entering a minefield or other
  movement-sensitive area triggers those systems the same way other dashes do.
- This reference is single-hit only. If a future pierce variant is authored, it would still need to
  specify whether the follow-up fires once per cast or once per admitted hit.
- Spell replay or echo mechanics may generate another dash only if they generate another admitted
  hit envelope; there is no special exemption for this sketch.
