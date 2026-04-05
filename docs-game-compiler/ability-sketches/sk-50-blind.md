# SK-50: Blind

## Designer Intent

I flash a blinding effect at enemies. For a short duration, their basic attacks whiff completely:
no damage, no on-hit effects, no projectile or hit relay. Their authored ability casts still work
normally.

## Primitive Composition

P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Delivery shape for the blind application (this reference uses the same cone targeting surface as
  SK-49)

## Observable Behavior

1. Enemies hit by the blind application receive `blind` for 2 seconds.
2. While blinded, engine-owned basic attacks resolve as `Miss`.
3. A miss consumes the normal attack attempt/timing but produces no `CombatContext`, no damage, and
   no on-hit effects.
4. Authored ability casts are unaffected unless the game has explicitly modeled them as basic-attack
   replacements that still lower through the engine auto-attack path.
5. Blind does not block movement, casting, targeting, or other actions.
6. Blind is reduced by ordinary status resistance / tenacity (`duration_scaling = status_resistance`).
7. Blind is cleansable and participates in the `soft_disable` DR / immunity category.
8. Visual: flash on application plus a blinded-state indicator while the debuff is active.

## Engine Primitives Required

Blind is already the canonical `apply_cc(cc_type = blind)` profile.

1. The blind application lowers to one generated negative CC status with `cc_type = blind`,
   `category = soft_disable`, and `duration_scaling = status_resistance`.
2. The blinded attacker's authoritative Arbiter checks that status before engine-owned auto-attack
   `CombatContext` generation.
3. If the attacker is blinded, the attack attempt resolves as `Miss` and exits before any hit,
   crit, projectile-impact, or on-hit chain is generated.
4. Because this check lives on the attacker side before `CombatContext` creation, the defender never
   sees a prepared hit for a blinded miss.

This is distinct from defender-side evasion or block:

- evasion is a defender-side admission failure
- block is a defender-side mitigation gate after hit admission
- blind is an attacker-side pre-hit failure for engine-owned basic attacks

## Cross-Boundary Concerns

Blind itself is ordinary target-side status application, but the miss check happens later on the
blinded attacker's authority:

1. If the blind application hits a Ghost, the generated blind status is relayed and installed on the
   target's owning Arbiter like any other CC.
2. Later, when that entity attempts a basic attack, its own authoritative Arbiter checks the local
   blind status before creating a prepared hit.
3. Because the miss occurs before `CombatContext` generation, there is no defender-side relay or
   Phase 2 work for the blinded miss.

No extra cross-boundary contract is needed beyond the ordinary CC relay path.

## Compiler Requirements

Designer specifies:

- delivery shape/range (cone in this reference)
- blind duration
- whether the blind is cleansable
- any paired damage payload that the same ability may also carry

Compiler emits:

- one ordinary blind application using `apply_cc(cc_type = blind, category = soft_disable, ... )`
- the generated negative runtime status entry for blind
- delivery targeting/query data (cone, AoE, projectile, etc.) separate from the blind profile itself

Compiler validates:

1. `cc_type = blind` pairs only with the canonical `soft_disable` category
2. blind uses only the engine-owned basic-attack miss profile; it MUST NOT silently retarget or
   suppress ordinary authored ability casts
3. authored duration scaling is valid (`fixed` or `status_resistance`)
4. if the parent delivery shape is cone-based, the same targeting validation used by SK-49 applies

## Resolved Interaction Notes

- If a game has a "next basic attack is empowered" mechanic that still lowers through the engine
  auto-attack path, blind causes that attack to miss as well.
- If a mechanic is implemented as an explicit authored ability cast rather than a basic attack,
  blind does not affect it.
- Summons or projected actors that use `attack_mode = basic_attack_only` are affected by blind the
  same way player basic attacks are.
- A blinded miss consumes the normal attack cadence. There is no free retry.
- The reference version does not generate separate "on miss" proc hooks. Miss is simply a pre-hit
  failure.
- Because blind is a generated negative CC status, Purify-style cleanses and Unstoppable-style
  immunity windows already interact with it through the canonical status registry.
