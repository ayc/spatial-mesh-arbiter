# SK-05: Global Strike

## Designer Intent

My character channels for 3 seconds, then deals damage to all enemy heroes across the entire map, regardless of distance or line of sight. The channel can be interrupted by stuns, silences, or displacement.

## Primitive Composition

P-43 (Charge-Up State) → P-46 (Global Event Scheduler)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (hits all enemies globally)

## Observable Behavior

1. Caster begins channeling — movement locked, cast bar visible to all players
2. Enemy players see a warning indicator (visual/audio cue that the channel is in progress)
3. If channel completes (3 seconds uninterrupted): every enemy hero on the map takes X damage
4. Damage is applied simultaneously on all targets at the same tick
5. If channel is interrupted (stun, silence, displacement, death): ability fizzles, cooldown is partially refunded
6. Each target's defensive stats are evaluated independently (resistances, shields, evasion)

## Engine Primitives Required

TODO: This uses the Global Event path through the Controller (§10 of mesh-controller.md). The Arbiter escalates to the Controller, the Controller fans out ExecuteGlobalEvent to all Arbiters at a synchronized future tick. How does the channel state machine work — is it a status effect on the caster? How are interrupts detected during the channel?

## Cross-Boundary Concerns

TODO: The entire mesh is involved. The Controller calculates which Arbiters have enemy heroes and fans out the event. Each Arbiter independently resolves damage against their local entities. The CombatContext must be pre-rolled (offensive stats baked in) so every Arbiter gets the same attack parameters. What happens if the caster dies or disconnects mid-channel on a different Arbiter than some targets?

## Compiler Requirements

TODO: How does the designer express "channel for 3s, then global damage"? What does the compiler produce — a channel definition + a global event trigger? How does the compiler validate that the ability correctly uses the escalation path?

## Open Questions

- Is the damage calculated once (flat X to everyone) or per-target (using each target's defensive stats)?
- Can the damage be blocked, evaded, or shielded per-target?
- Does the ability interact with spell immunity / invulnerability?
- What if a new enemy hero spawns (reconnects) during the channel — are they hit?
- What is the maximum latency between the channel completing and damage being applied (Controller fan-out time)?
- How does this interact with Kinematic Dilation — if the caster's zone is dilated, does the channel take longer in real time?
