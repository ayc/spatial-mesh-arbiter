# SK-81: Remote Control Summon

## Designer Intent

I deploy a motorized bomb. While the bomb is active, I directly control its movement with my movement keys — my character becomes immobile. I steer the bomb around the battlefield. When I press the detonation button (or after a timeout), the bomb explodes dealing massive AoE damage. Enemies can destroy the bomb if they hit it.

## Primitive Composition

P-32 (Actor Spawning) → P-29 (Control Authority Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Movement/aim input redirected to the summon
- Detonation input (reactivation key)

## Observable Behavior

1. Activate — bomb spawns at caster's position
2. Caster becomes immobile and channeling (vulnerable, can be interrupted)
3. Movement input controls the bomb, not the caster
4. The bomb moves at fixed speed, can be steered freely
5. The bomb has HP and can be destroyed by enemies
6. Reactivate or timeout: bomb detonates, AoE damage at bomb's position
7. If the bomb is destroyed: no detonation (reduced cooldown)
8. If the caster is interrupted (stunned): bomb detonates immediately at current position
9. Visual: rolling bomb entity, caster in trance state

## Engine Primitives Required

### Player Input Redirected to Summon

This is distinct from:
- SK-06 Summon Swarm: AI-controlled summons, player doesn't steer
- SK-40 Mind Control: caster's input steers an ENEMY
- SK-66 Symbiote: caster's ABILITIES fire from ally's position, not movement control

SK-81 is: caster's MOVEMENT INPUT controls a FRIENDLY SUMMON's movement. The caster spawns an entity and their Edge Node's movement stream is rerouted:

```
struct RemoteControlState {
    controlled_entity_id: EntityID,
    caster_body_position: Vec2F,  // Frozen
    detonation_damage: SimFixed,
    detonation_radius: SimFixed,
    expires_at_tick: u64,
}
```

The Arbiter must:
1. Accept movement proposals from the caster's session
2. Apply them to the controlled entity (bomb), not the caster
3. Reject ability proposals (caster can only steer and detonate)
4. On detonation: AoE at bomb's position using caster's offensive stats

### Destructible Controlled Entity

The bomb has HP — enemies can attack and destroy it:
- If destroyed: no detonation, bomb despawns, caster regains control
- The bomb is a valid target for enemies (not stealthed, not invulnerable)
- The bomb has collision (can be blocked by terrain, can't pass through walls)

### Channel-Like State on Caster

While controlling the bomb, the caster is in a channel-like state:
- Immobile (position frozen)
- Vulnerable (can be targeted and damaged)
- Interruptible (CC on caster → bomb detonates immediately)
- Can only send steering input and detonation command

## Cross-Boundary Concerns

TODO: The bomb can move freely, potentially crossing Arbiter boundaries:

1. **Bomb crosses boundary:** Standard entity handoff for the bomb entity. But the caster (on Arbiter A) is still sending steering input. After handoff, the bomb is on Arbiter B. Steering input must be relayed from A to B per-tick.

2. **Continuous cross-boundary steering:** Like SK-40 Mind Control, the caster's input stream must reach the bomb's Arbiter every tick. If the bomb is on a different Arbiter than the caster, this is per-tick cross-boundary relay.

3. **Detonation command cross-boundary:** Caster sends "detonate" from Arbiter A. Bomb is on Arbiter B. The command must reach B and trigger the AoE locally on B.

4. **Bomb destroyed cross-boundary:** Bomb on Arbiter B is destroyed. Caster on Arbiter A must be notified to exit the control state.

## Compiler Requirements

TODO: Designer specifies: spawn bomb at caster position, caster immobile + channeling, movement input redirected to bomb, bomb HP (destructible), detonate on command or timeout or caster interrupt, AoE damage at bomb position, caster's stats for damage. Compiler produces:
- Bomb entity definition (HP, movement speed, collision)
- RemoteControlState on caster (input redirect, immobile, channel-like)
- Input routing: movement from caster session → bomb entity
- Detonation trigger: reactivation, timeout, caster interrupt
- AoE resolution at bomb's position with caster's CombatContext

## Open Questions

- Can the bomb go through SK-69 Portal Pair (steer it into a portal)?
- Does the bomb trigger SK-32 Minefield when it rolls over mines?
- Can the bomb enter SK-29 Blizzard and take damage from zones?
- If the caster dies while controlling the bomb, does the bomb detonate or despawn?
- Can allies heal the bomb?
- Does the bomb have collision with other entities (push them aside)?
- How fast can the bomb move — is it faster than normal movement speed?
- Can the bomb cross SK-03 Terrain Wall (blocked by walls)?
- Does the bomb's detonation trigger on-hit procs for the caster?
- Performance: per-tick cross-boundary steering relay for the control duration
