# T1-01: Stat Compilation Formulas

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md` + `1-architecture/04-meta-services.md`

## Audit Notes

The compilation pipeline (6-step algorithm), durability penalty, stat caps, and attribute-to-stat mapping table are all specified. What's missing are the numeric coefficients, formula shape, and secondary attribute formulas.

## Resolution

### 1. Formula Shape: Linear with Per-Level Scaling

```
derived_stat = base_value + (coefficient × attribute_value × (1 + level_scaling × entity_level))
```

| Parameter | Type | Source |
|-----------|------|--------|
| `base_value` | `SimFixed` | Per-stat default from `attribute-formulas.json` |
| `coefficient` | `SimFixed` | Per-attribute-per-stat multiplier |
| `attribute_value` | `SimFixed` | Entity's current attribute points (post-equipment) |
| `level_scaling` | `SimFixed` | Global per-level modifier (default: 0.02 = 2% per level) |
| `entity_level` | `u16` | Entity's current level |

**Rationale for linear:** Transparent to designers and players. Diminishing returns are achieved through stat caps (T1-05), not formula curvature. Matches Diablo 4 and Lost Ark's approach.

### 2. `attribute-formulas.json` Schema

```json
{
    "$schema": "game/attribute-formulas/v1",
    "level_scaling": 0.02,
    "formulas": {
        "physical_damage_multiplier": {
            "base": 1.0,
            "contributors": [
                { "attribute": "vigor", "coefficient": 0.015 },
                { "attribute": "might", "coefficient": 0.005 }
            ]
        },
        "crit_chance": {
            "base": 0.05,
            "contributors": [
                { "attribute": "precision", "coefficient": 0.003 },
                { "attribute": "cunning", "coefficient": 0.001 }
            ]
        },
        "crit_multiplier": {
            "base": 1.5,
            "contributors": [
                { "attribute": "precision", "coefficient": 0.008 }
            ]
        },
        "cooldown_reduction": {
            "base": 0.0,
            "contributors": [
                { "attribute": "arcane_mastery", "coefficient": 0.002 }
            ]
        },
        "block_chance": {
            "base": 0.0,
            "contributors": [
                { "attribute": "fortitude", "coefficient": 0.004 }
            ]
        },
        "evasion_rating": {
            "base": 0.0,
            "contributors": [
                { "attribute": "cunning", "coefficient": 0.003 },
                { "attribute": "agility", "coefficient": 0.002 }
            ]
        },
        "hp_max": {
            "base": 100.0,
            "contributors": [
                { "attribute": "vitality", "coefficient": 10.0 },
                { "attribute": "fortitude", "coefficient": 3.0 }
            ]
        },
        "mana_max": {
            "base": 50.0,
            "contributors": [
                { "attribute": "arcane_mastery", "coefficient": 8.0 },
                { "attribute": "wisdom", "coefficient": 2.0 }
            ]
        },
        "move_speed": {
            "base": 1.0,
            "contributors": [
                { "attribute": "agility", "coefficient": 0.001 }
            ]
        }
    }
}
```

These are **starting coefficients** intended for designer tuning. The schema is the contract; the numbers are adjustable via Data Epoch hot-patches.

### 3. Secondary Attribute Formulas

Secondary attributes use the same linear formula shape and are added to `attribute-formulas.json`:

| Secondary | Description | Base | Contributor |
|-----------|-------------|------|-------------|
| Momentum | Charge generation rate bonus | 0.0 | agility × 0.005 |
| Poise | CC duration reduction (stacks with DR tracker P-41) | 0.0 | fortitude × 0.004 |
| Echo | Spell echo chance (proc check per cast) | 0.0 | arcane_mastery × 0.002 |
| Affinity | Elemental resistance bonus (flat per-element) | 0.0 | wisdom × 0.3 |
| Synchrony | Party buff effectiveness bonus (multiplicative on outgoing) | 0.0 | wisdom × 0.003 |

### 4. Compilation Integration

The Meta Service's step 4 ("Derive secondary stats from primaries") evaluates `attribute-formulas.json`:

```rust
fn compile_derived_stats(attrs: &Attributes, level: u16, formulas: &FormulaTable) -> DerivedStats {
    let mut result = DerivedStats::default();
    for (stat_id, formula) in formulas.entries() {
        let mut value = formula.base;
        for contrib in &formula.contributors {
            let attr_val = attrs.get(contrib.attribute);
            value += contrib.coefficient * attr_val * (SimFixed::ONE + formulas.level_scaling * SimFixed::from_num(level));
        }
        result.set(stat_id, value);
    }
    // Caps applied per T1-05 at evaluation time, not here
    result
}
```

## References

- `docs/3-gameplay-systems/01-rpg-mechanics.md` — Attribute mapping table
- `docs/1-architecture/04-meta-services.md` — Compilation pipeline, config schema
- `docs/6-spec-drafts/tier-1-combat/05-stat-caps-and-overflow.md` — Cap/floor enforcement
