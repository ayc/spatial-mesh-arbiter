# SK-71: Sticky Bomb

## Designer Intent

I throw a bomb that attaches to an enemy hero. The bomb sticks to them and follows their movement. After 2 seconds, the bomb detonates at the target's CURRENT position, dealing AoE damage to the target and all nearby enemies. The target can't remove the bomb — they can only try to run away from their allies to minimize collateral.

## Primitive Composition

P-06 (Attached Kinematics) → P-45 (Delay Timer) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy — bomb attaches to the target
2. The bomb is visible on the target (ticking indicator)
3. The bomb moves with the target — wherever they go, the bomb follows
4. After 2 seconds: bomb detonates at the target's current position
5. AoE damage: the target takes full damage, nearby enemies take AoE damage
6. The target cannot remove the bomb (not cleansable? Design choice)
7. Visual: glowing bomb attached to the target, countdown timer, explosion on detonation

## Engine Primitives Required

Sticky Bomb is now a canonical projectile-attachment delayed detonation.

The recommended lowering is:

1. one ordinary targeted projectile spawn
2. a projectile archetype with:
   - `attachment_policy = {`
     `delay_ticks = 120,`
     `follow_attached_entity = true,`
     `on_carrier_loss = last_known_position,`
     `preserve_original_payload = true`
     `}`
   - a carried detonation payload that resolves one hostile radius query from the detonation center
3. a hostile/direct-hit branch in that payload so the carrier takes the primary hit and nearby
   hostile neighbors take the AoE splash

The important point is that the bomb is not modeled as a generic cleansable debuff. It is an
attached delayed projectile payload owned by the struck entity's current Arbiter. The carrier's
movement, teleports, pulls, and ordinary handoffs simply move the future detonation center because
`follow_attached_entity = true`.

At expiry, the carrier owner reads the carrier's CURRENT position, resolves the authored hostile
AoE from there, applies the primary hit to the carrier when the carrier is still present, and then
removes the attached payload.

## Cross-Boundary Concerns

Sticky Bomb follows the canonical attachment-owner model.

1. The initial projectile impact attaches on the struck entity's CURRENT owner.
2. If the carrier later hands off, the attached timed payload hands off with the carrier as ordinary
   authoritative SoftState.
3. At detonation time, the carrier's CURRENT owner performs the local radius query and resolves the
   hostile payload from the carrier's CURRENT position.
4. The original caster does not need to stay involved. Offensive payload and source identity were
   already baked into the carried projectile payload when the impact attached.
5. If the carrier dies or is otherwise removed before detonation, `on_carrier_loss =
   last_known_position` means the explosion still resolves once at the carrier's last authoritative
   position instead of silently fizzling.

## Compiler Requirements

Designer specifies:

- hostile target admit
- detonation delay
- whether the payload follows the attached carrier
- primary-hit damage and splash payload
- splash radius and hostile filter
- carrier-loss rule

Compiler emits:

- one targeted projectile spawn
- one projectile archetype with canonical `attachment_policy`
- one attached delayed payload owned by the carrier's CURRENT owner
- one expiry-time hostile radius query centered on the carrier's CURRENT position
- one fallback detonation-at-last-known-position rule for carrier loss

Compiler validates:

1. `delay_ticks > 0`
2. the projectile impact path is attachment-driven rather than a bespoke per-target timer subsystem
3. any carrier-loss fallback is one of the canonical `attachment_policy.on_carrier_loss` modes
4. the splash payload uses ordinary hostile filters and effect lists rather than sketch-local
   "sticky bomb" special casing

## Resolved Interaction Notes

- This reference is not cleansable. The bomb is an attached projectile payload, not a negative
  status participating in generic `cleanse`.
- The explosion is hostile-relative-to-caster, so it damages the carrier and nearby enemies of the
  bomber. It does not damage the bomber's allies unless a different filter is authored.
- If the carrier later becomes untargetable, suspended, or otherwise harder to affect, the attached
  payload still expires on schedule. Ordinary target-side immunity / admission rules still apply to
  the final direct hit and splash at detonation time.
- If the carrier dies before expiry, the reference behavior is still one last explosion at the
  carrier's last authoritative position.
- Multiple sticky bombs may coexist on one carrier unless the game authors an additional live-limit
  or replacement rule elsewhere.
- The detonation payload is an ordinary hostile effect list, so normal downstream procs and kill
  credit follow the same rules as other authored AoE payloads.
