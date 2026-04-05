# SK-102: Disarm

## Designer Intent

I curse nearby enemies so they can't auto-attack for 2 seconds. They can still move freely and cast abilities — only their basic attacks are disabled. This shuts down auto-attack-reliant enemies while leaving casters mostly unaffected.

## Primitive Composition

P-26 (Capability Bitmask) → P-41 (DR Tracker)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- AoE centered on caster (or targeted)

## Observable Behavior

1. Cast — enemies in radius are disarmed for 2 seconds
2. Disarmed enemies CANNOT auto-attack (basic attacks are blocked)
3. Disarmed enemies CAN move (full movement control)
4. Disarmed enemies CAN cast abilities (all abilities functional)
5. Duration reduced by Tenacity
6. Subject to Diminishing Returns (SK-28) — soft CC category
7. Cleansable by SK-15 Purify
8. Visual: weapon-broken icon, disarmed enemies show a "no attack" indicator

## Engine Primitives Required

Disarm is now a canonical `apply_cc(cc_type = disarm)` reference.

The recommended lowering is:

1. apply one generated CC status with:
   - `cc_type = disarm`
   - `category = soft_disable`
   - `duration_ticks = 120`
   - `dr_category = soft_disable`
   - `duration_scaling = status_resistance`
   - `is_cleansable = true`
2. let the canonical disarm profile suppress only `CAN_ATTACK`

This keeps the mechanic inside existing surfaces:

- disarm is already a first-class canonical `cc_type`
- auto-attacks are blocked through the existing attack-capability gate
- movement and ability casts remain legal because the disarm profile only suppresses attacks

## Cross-Boundary Concerns

Disarm follows the ordinary target-owner CC path.

1. The origin owner admits local targets and relays remote/Ghost targets through the hostile
   target-owner path.
2. Each target owner applies the generated disarm status locally and enforces the attack-capability
   block there.
3. Cross-boundary auto-attack attempts do not create a special case; they simply fail local attack
   validation while the disarm status is active.

## Compiler Requirements

Designer specifies:

- hostile target set
- duration
- cleansable / status-resistance behavior

Compiler emits:

- one canonical `apply_cc` using `cc_type = disarm`
- one generated status that suppresses attack capability only

Compiler validates:

1. `category = soft_disable` for disarm
2. `dr_category = soft_disable` for this reference
3. the effect uses canonical `apply_cc`, not a bespoke "reject auto-attack" validator

## Resolved Interaction Notes

- Empowered or modified basic attacks are still attacks unless the ability is explicitly authored as
  a separate castable ability, so disarm blocks them in this reference.
- Movement remains fully player-controlled while disarmed.
- Ability casts remain fully legal while disarmed.
- Blind and disarm stay distinct: blind allows attacks that miss; disarm forbids the attack from
  starting at all.
