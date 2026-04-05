# SK-87: Conditional Counter

## Designer Intent

I enter a defensive stance for 1 second. If any enemy hits me during that window, the stance activates — I become Protected (invulnerable) and deal AoE damage around me. If nobody attacks me during the window, nothing happens and the ability goes on full cooldown. High risk, high reward — I'm gambling that the enemy will attack.

## Primitive Composition

P-36 (On-Damage-Received Hook) → P-17 (Conditional Thresholds) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only defensive activation)

## Observable Behavior

1. Activate — enter counter stance for 1 second
2. During the stance: caster can't move or act (locked in place, vulnerable)
3. If hit by ANY damage during the stance: counter TRIGGERS
4. On trigger: caster becomes Protected for 0.75 seconds, AoE damage to all nearby enemies
5. If NOT hit during the 1-second window: stance expires, nothing happens, full cooldown
6. The trigger check is binary — any damage source triggers it (melee, ranged, DoT tick, AoE)
7. Visual: defensive pose during stance, flash of energy on trigger, underwhelming fizzle on expiry

## Engine Primitives Required

Conditional Counter is now a canonical `consumption_window = damage_received` reference.

The recommended lowering is:

1. apply one positive `counter_stance` status to the caster for 60 ticks
2. that status authors:
   - capability suppression for movement / attacks / casts during the stance window
   - `consumption_window = {`
     `consume_on = damage_received,`
     `max_consumptions = 1,`
     `on_consume_effects = [`
     `apply protected-status,`
     `aoe_damage(...)`
     `]`
     `}`
3. let ordinary status expiry remove the stance with no payoff if no qualifying hit arrived

This keeps the mechanic inside existing canonical surfaces:

- the wait-for-a-hit window is ordinary status metadata
- the trigger is the canonical `damage_received` consumption window
- the payoff is just an ordinary protected buff plus ordinary AoE damage

## Cross-Boundary Concerns

Conditional Counter is local to the stance holder's owner.

1. Any qualifying `damage_received` event, including cross-boundary relayed hits, is observed on the
   defended entity's current owner during Stage 9.
2. The same owner consumes the stance window, applies the protected follow-up, and emits the AoE
   damage payload.
3. The later AoE damage then follows the ordinary local-query / target-owner relay path for any
   remote admitted targets.
4. The Stage 9 consumption-window ordering already gives the canonical answer when a qualifying hit
   and the stance expiry happen in the same tick.

## Compiler Requirements

Designer specifies:

- stance duration
- stance lockdown flags
- whether any qualifying `damage_received` event consumes it
- protected duration
- AoE damage / radius

Compiler emits:

- one positive stance status
- one `consumption_window` with `consume_on = damage_received`
- one protected follow-up status
- one AoE damage follow-up

Compiler validates:

1. `max_consumptions = 1` for this one-shot counter window
2. the stance lockdown is expressed through ordinary capability flags
3. the trigger path is authored through canonical `consumption_window`, not a bespoke per-status
   damage callback system

## Resolved Interaction Notes

- This reference triggers from the first qualifying `damage_received` event only; later hits in the
  same or later ticks do not retrigger it because the stance window is already consumed.
- The counter stance itself is vulnerable. Enemies may choose not to hit into it, in which case the
  status simply expires with no payoff.
- The protected follow-up is a separate beneficial status and is not CC, so Tenacity/DR do not
  shorten it unless the designer authors some other nonstandard policy.
- Because the payoff AoE is ordinary deferred damage, later proc consumers see it the same way they
  see other AoE damage events.
