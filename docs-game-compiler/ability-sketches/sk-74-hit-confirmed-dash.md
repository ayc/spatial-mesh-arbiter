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

### Conditional Post-Resolution Effect

All existing abilities have a fixed outcome: they either succeed or fail. Hit-Confirmed Dash has a **branching outcome**: the ability's effect on the CASTER depends on whether the OFFENSIVE portion succeeded.

```
enum ProjectileOutcome {
    Hit { target_id: EntityID },
    Miss,
}

// After projectile resolution:
match outcome {
    Hit { target_id } => {
        apply_damage(target_id, combat_context);
        self_dash(caster, cast_direction, dash_distance);  // Conditional!
        set_cooldown(ability, hit_cooldown);
    },
    Miss => {
        set_cooldown(ability, miss_cooldown);
    },
}
```

The conditional dash is the new primitive — a self-displacement that only fires if a preceding offensive action succeeded.

### Hit Detection → Self-Displacement Pipeline

The ability is a single cast that produces two effects:
1. Offensive: damage to the target (standard)
2. Mobility: self-dash in the cast direction (conditional on hit)

These must resolve in order: first confirm the hit, then apply the dash. The dash uses the cast direction (not the direction to the target), so the caster dashes forward regardless of where the target was in the skillshot path.

### Conditional Cooldown

The ability has two cooldown values:
- Hit: shorter cooldown (reward for accuracy)
- Miss: longer cooldown (penalty for whiffing)

The cooldown is set AFTER the outcome is known. This requires the ability definition to express: `cooldown_on_hit: 6s, cooldown_on_miss: 12s`.

## Cross-Boundary Concerns

TODO: The skillshot might hit a Ghost. If the projectile hits a Ghost:
1. Damage is relayed to the Ghost's owning Arbiter (standard)
2. The caster's Arbiter confirms "hit" and triggers the self-dash locally
3. The dash is a local self-displacement on the caster's Arbiter

The key question: does the caster's Arbiter confirm the hit BEFORE relaying damage, or does it wait for the target's Arbiter to confirm? If the caster's Arbiter can determine "projectile collided with Ghost hitbox" locally (using Ghost position data), the hit confirmation and dash can be immediate without waiting for the cross-boundary relay.

This is the likely approach — the caster's Arbiter detects the collision locally (Ghost position is approximate but sufficient for hit detection) and triggers the dash immediately. The damage relay proceeds in parallel.

## Compiler Requirements

TODO: Designer specifies: skillshot (direction, first-hit), on-hit effects (damage + self-dash in cast direction + reduced cooldown), on-miss effects (no dash + longer cooldown). Compiler produces:
- ProjectileActor with `CollisionMode::FirstHit`
- Branching post-resolution: hit → damage + self-dash + cooldown_A, miss → cooldown_B
- Self-displacement definition (direction, distance, instant)
- Conditional cooldown values

The compiler needs to support **outcome-dependent ability resolution** — where the ability's effect on the caster branches based on the offensive result.

## Open Questions

- Does the dash trigger SK-32 Minefield if the caster dashes onto a mine?
- Does the dash break SK-25 Root (dash is movement — root prevents movement)?
- Can the dash cross an Arbiter boundary (instant handoff)?
- Does the dash trigger any on-dash effects (if such effects exist)?
- If the skillshot hits multiple targets (future pierce variant), does the dash trigger once or per-hit?
- Does the hit confirmation use Ghost position accuracy (dash on approximate hit) or wait for authority (dash delayed by relay)?
- Can the dash direction differ from the cast direction (e.g., dash backward on hit)?
- Does SK-12 Spell Echo interact — if the echo fires and hits, does it trigger another dash?
- If the caster is rooted (SK-25) when the skillshot hits, does the conditional dash fail silently or override the root?
- Does the reduced cooldown on hit interact with cooldown reset (SK-14 Execute Threshold)?
