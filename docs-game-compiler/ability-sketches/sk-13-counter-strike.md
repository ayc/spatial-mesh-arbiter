# SK-13: Counter-Strike

## Designer Intent

When I successfully block a melee attack, I automatically riposte against the attacker, dealing
80% of my weapon damage. The riposte is a guaranteed retaliatory hit in the sense that it does not
open a second miss/block gate on the attacker.

## Primitive Composition

P-12 (Facing/Dot-Product Check) -> P-38 (On-Block/Defend Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- triggering block event (`on_block`)
- the attacker entity from the block context
- blocker's offensive stats / weapon scaling snapshot

## Observable Behavior

1. An incoming melee/front-guard attack is successfully blocked.
2. The block emits a retaliatory riposte targeting that same attacker.
3. The riposte deals 80% weapon-scaled damage using the blocker's current offensive stats.
4. The riposte does not open a second attacker-side evasion/block admission pass.
5. The riposte may crit for damage using the blocker's ordinary crit logic.
6. The target still gets normal later mitigation such as shields, resistances, and DR.
7. Visual presentation may render a parry followed by a near-immediate riposte.

## Engine Primitives Required

Counter-Strike is the canonical `on_block` riposte reference.

The recommended lowering is:

1. one passive `on_block` trigger owned by the blocker
2. that trigger emits one reactive retaliatory damage packet with:
   - `target = target`, where the `on_block` trigger context resolves `target` to the triggering
     attacker
   - weapon/offense scaling equal to 80% of the blocker's normal weapon profile
   - the ordinary crit rule still enabled
3. the riposte is treated as a committed retaliatory hit from `P-38`, not as a fresh player-aimed
   melee swing

This keeps the mechanic inside existing surfaces:

- block admission is still handled by the canonical defender-side block gate
- the riposte is ordinary hostile damage sourced from blocker offense
- no second player intent, cursor aim, or fresh target-acquisition query is introduced
- "cannot be blocked or evaded" is modeled by not reopening a second miss/block gate for the
  already identified attacker, not by bypassing later mitigation

## Cross-Boundary Concerns

Counter-Strike follows the ordinary reverse-relay story for reactive retaliatory damage.

1. The original block succeeds on the defender's current owner during Stage 7 and emits `P-38`
   during Stage 9.
2. Because `P-38` is a reactive PostDamage hook, the riposte is queued for the NEXT tick rather
   than resolving inline.
3. If the attacker is remote/Ghost, the defender's owner relays the retaliatory prepared-hit packet
   back to the attacker's owner with ordinary source/target identity plus `reactive_depth = 1`.
4. The attacker's owner resolves the riposte locally through the ordinary later mitigation path.
   No second target-acquisition query is needed because the blocked-event context already supplied
   the attacker entity.

## Compiler Requirements

Designer specifies:

- which blocking profile qualifies for the riposte (this reference assumes the melee/front-guard
  variant)
- riposte damage scaling
- damage type
- whether the riposte may crit

Compiler emits:

- one passive `on_block` trigger
- one retaliatory `damage` payload back to the triggering attacker
- the ordinary reverse-relay packet when the attacker is remote

Compiler validates:

1. the mechanic is authored as reactive `on_block` damage, not as a second cast/attack intent
2. the triggering profile is the intended melee/front-guard variant for this reference
3. the retaliatory event inherits the canonical reactive-depth safety bound and therefore cannot
   create unbounded counter loops

## Resolved Interaction Notes

- Counter-Strike resolves on the next tick, not inline on the same tick, because `P-38` is a Stage
  9 reactive hook.
- In this reference, "cannot be blocked or evaded" means the riposte does not perform a second
  miss/block admission pass on the attacker. It does NOT bypass shields, resistances, armor, or
  other later mitigation.
- The riposte may crit for damage, but under the canonical default reactive-depth bound it does not
  start a fresh PostDamage proc tree of its own.
- If both combatants carry Counter-Strike, one successful block does not create infinite ping-pong
  because the retaliatory event is already reactive.
- Ranged-block or spell-block variants are separate game-data designs; this reference assumes the
  triggering block is the intended melee/front-facing guard case.
