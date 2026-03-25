# T1-02: Distance Falloff Formula

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md`

## Problem Statement

The combat resolution pseudocode calls `calculate_falloff(distance)` but the function is never defined. This multiplier affects final damage for AoE and ranged abilities.

## Resolution

### Definition

```rust
fn calculate_falloff(distance: SimFixed, ability: &AbilityDef) -> SimFixed {
    match ability.falloff_mode {
        FalloffMode::None => SimFixed::ONE,
        FalloffMode::Linear { max_range, floor } => {
            let ratio = distance / max_range;
            let clamped = ratio.clamp(SimFixed::ZERO, SimFixed::ONE);
            let falloff = SimFixed::ONE - (clamped * (SimFixed::ONE - floor));
            falloff
        },
        FalloffMode::Step { thresholds } => {
            // thresholds: sorted Vec<(SimFixed, SimFixed)> = [(distance, multiplier), ...]
            let mut mult = SimFixed::ONE;
            for (threshold_dist, threshold_mult) in thresholds.iter().rev() {
                if distance >= *threshold_dist {
                    mult = *threshold_mult;
                    break;
                }
            }
            mult
        },
    }
}
```

### Falloff Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `None` | Always returns 1.0 (full damage) | Single-target abilities, melee |
| `Linear` | Scales from 1.0 at center to `floor` at `max_range` | Standard AoE (Blizzard, explosions) |
| `Step` | Discrete damage tiers at distance thresholds | Ring geometry (SK-85), tiered zones |

### Defaults

- **Single-target abilities:** `FalloffMode::None` (no falloff)
- **AoE abilities:** `FalloffMode::Linear { max_range: ability.radius, floor: 0.25 }` (25% damage at edge)
- **Global strikes:** `FalloffMode::None` (full damage everywhere in the geometry)

### Per-Ability Configuration

Falloff mode is specified in the ability definition schema (`02-schema-and-validation.md` §5) and compiled into the game image. Designers configure it per ability:

```yaml
effects:
  - type: aoe_damage
    center: target
    shape: circle
    radius: 5.0
    amount: 200
    falloff:
      mode: linear
      floor: 0.25   # 25% damage at edge
```

### Where It Executes

`calculate_falloff` is called during Stage 8 (`DamageResolution`) after the target set is determined. The `distance` parameter is the distance from the AoE center to each target's position. The returned multiplier is applied to `base_damage` before mitigation.

### Determinism

All falloff arithmetic uses `I32F32`. The `floor` value and `max_range` are `SimFixed` constants compiled into the game image. No floating-point operations.

## References

- `docs/3-gameplay-systems/01-rpg-mechanics.md` — `apply_combat_math` pseudocode line 570
- `docs-game-compiler/02-schema-and-validation.md` §6.3 — AoE effect schema
- `docs-game-compiler/ability-primitives/03-combat-resolution.md` — P-15 Value Modification
