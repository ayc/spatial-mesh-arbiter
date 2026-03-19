# SK-103: Facing-Dependent Effect

## Designer Intent

I unleash a petrifying gaze in a cone in front of me. Enemies FACING me are turned to stone (stunned for 2 seconds). Enemies facing AWAY from me are only slowed (40% for 2 seconds). The effect depends on which direction the target is looking at the moment the ability hits.

## Primitive Composition

P-12 (Facing/Dot-Product Check) → P-17 (Conditional Thresholds)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Cast direction (cone in front of caster)

## Observable Behavior

1. Cast — cone AoE in front of the caster (like SK-49 Cone Strike)
2. For each enemy hit, check: is the enemy's facing direction toward the caster or away?
3. If facing TOWARD caster (within ~90° of looking at caster): stunned for 2 seconds
4. If facing AWAY from caster (looking away): slowed 40% for 2 seconds
5. The check is instantaneous — based on facing at the moment of impact
6. Duration reduced by Tenacity
7. Subject to Diminishing Returns (SK-28)
8. Visual: enemies facing caster turn to stone, enemies facing away get frost effect

## Engine Primitives Required

### Entity Facing Direction

This is the first ability that READS an entity's facing direction for gameplay purposes. The engine must track facing as an authoritative property:

```
struct EntityCore {
    position: Vec2F,
    velocity: Vec2F,
    facing: Vec2F,       // Normalized direction the entity is "looking"
    // ... other fields
}
```

Facing is typically derived from:
- Last movement direction (if moving)
- Last attack direction (if attacking a target)
- Explicit facing/orientation input from the client (requested aim direction)

Facing must be authoritative (server-determined) and included in the entity state. Currently, the spec's entity state doesn't explicitly track facing — this may be a new field.

### Facing Angle Check

For each target hit by the cone, determine their orientation relative to the caster:

```
fn is_facing_toward(target: &Entity, caster_position: Vec2F) -> bool {
    let to_caster = normalize(caster_position - target.position);
    let facing_dot = dot(target.facing, to_caster);
    facing_dot > 0.0  // Positive = facing toward, Negative = facing away
}
```

If `facing_dot > 0` (angle between facing and direction-to-caster is less than 90°): target is facing toward → stun.
If `facing_dot <= 0` (angle is greater than 90°): target is facing away → slow.

This is a dot-product check (same fixed-point math as SK-49 Cone Strike's angle check) but between the TARGET's facing and the direction TO THE CASTER, not between the caster's facing and the direction to the target.

### Branching CC Based on Geometry

The ability applies DIFFERENT effects to different targets based on a spatial/geometric condition:
- SK-85 Ring Geometry: different effect based on DISTANCE (in ring = hit, inside = safe)
- SK-103: different effect based on ANGLE (facing toward = stun, facing away = slow)

Both are "geometric conditionals" — the effect branches based on spatial relationships at resolution time.

### Facing in Ghost Updates

If the target is a Ghost, does the Ghost carry facing data? Currently, GhostUpdate has position, velocity, movement_class — no facing. The caster's Arbiter would need facing data for Ghost targets to determine the stun-vs-slow branch.

Options:
- Add facing to GhostUpdate (small overhead — one Vec2F per Ghost update)
- Use velocity as a proxy for facing (if moving, facing = movement direction)
- Always apply the weaker effect (slow) for Ghosts (conservative)

Using velocity as a facing proxy is reasonable for entities in motion. Stationary entities have ambiguous facing — design choice needed.

## Cross-Boundary Concerns

TODO: The cone AoE hits enemies, some of which may be Ghosts. For local entities, facing is known authoritatively. For Ghosts:

1. **Ghost with velocity**: facing = movement direction (proxy). Can determine stun vs slow.
2. **Stationary Ghost**: facing is unknown (Ghost doesn't carry facing). Must default to one effect.
3. **Relay question**: does the caster's Arbiter determine stun vs slow locally (using Ghost data), or does it relay "check facing and apply stun or slow" to the Ghost's owning Arbiter?

If the caster determines locally: fast, but uses approximate Ghost facing. If relayed: accurate, but adds a round-trip. The caster's Arbiter should determine locally using Ghost velocity as facing proxy — the edge case of stationary Ghosts defaults to slow (safer).

## Compiler Requirements

TODO: Designer specifies: cone AoE, per-target facing check (toward caster = stun 2s, away = slow 40% 2s), instantaneous facing check at moment of impact, Tenacity/DR apply to both effects. Compiler produces:
- Cone AoE query (SK-49)
- Per-target facing check: dot product between target.facing and direction_to_caster
- Branching effect application: stun if facing toward, slow if facing away
- Ghost facing approximation (velocity proxy)

The compiler needs to support **geometric conditional effects** — effects where the outcome depends on spatial relationships (facing, distance, angle) evaluated at resolution time.

### Entity Facing as Engine Property

This may require a `docs-core/` change: the entity state model must include `facing: Vec2F` as an authoritative property. This affects:
- `docs-core/01-spatial-runtime-kernel.md`: entity state includes facing
- Ghost updates: optionally include facing data
- Edge Node input: facing is derived from movement direction or explicit orientation input

## Open Questions

- Is entity facing derived from movement direction, or explicitly controlled by aim/orientation input?
- For stationary entities, what is their facing direction? Last movement direction? Last requested orientation?
- Does facing change instantaneously or smoothly (turn rate)?
- Should facing be included in GhostUpdate (adds bandwidth) or approximated from velocity?
- Can the facing check be manipulated (turn away at the last tick to avoid the stun)?
- Does the stun/slow distinction apply to each target independently (some stunned, some slowed in the same cast)?
- How does this interact with SK-78 Fear (feared entity is running away — their facing is away from the fear source, but toward or away from the caster?)?
- Does SK-51 Unstoppable prevent both the stun AND the slow (both are CC)?
- If the target is inside SK-91 Stasis (frozen — can't change facing), what's their facing at the check?
