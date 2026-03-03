# T1-01: Stat Compilation Formulas

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md` + `1-architecture/04-meta-services.md`

## Audit Notes

**The original draft overstated the gap.** Several aspects ARE specified:

| Aspect | Status | Source |
|--------|--------|--------|
| Compilation pipeline | **Fully specified** — 6-step algorithm with pseudocode | `04-meta-services.md` lines 509-582 |
| Durability penalty | **Specified as multiplicative** — `equipment_primaries += item_def.base_stats.primary * penalty` where penalty is `degraded_stat_penalty_pct` (e.g., 0.50) | `04-meta-services.md` lines 534-542 |
| Stat caps | **Fully listed** with values and enforcement pseudocode (`min()` calls) | `04-meta-services.md` lines 574-580, 645-656 |
| Which attrs map to which stats | **Specified** — Full mapping table showing primary/minor contributions | `01-rpg-mechanics.md` lines 112-173 |

## Remaining Gaps (Narrowed)

### 1. `attribute-formulas.json` — Referenced But Does Not Exist

The Meta Services doc references:
```json
"attribute_formulas_file": "data/attribute-formulas.json"
```

And the RPG Mechanics doc explicitly states (line 110):
> "The specific coefficients are designer-tuned values in the configuration file, not hardcoded."

The mapping table shows *which* attributes feed *which* stats, but provides **no numeric coefficients**. Example: Vigor is the "primary" contributor to `physical_damage_multiplier`, but "1 point of Vigor = ???% physical damage" is never stated.

### 2. Secondary Attribute Formulas

Momentum, Poise, Echo, Affinity, Synchrony are documented narratively (what they do conceptually) but have no implementation formulas, thresholds, or numeric values. Even if hidden from players, implementers need concrete numbers.

### 3. Conversion Formula Shape

Are formulas linear (`derived = coeff * minor_attr`)? Diminishing returns? Breakpoint-based? The spec says "designer-configured" but doesn't specify the function signature or parameter types.

## Questions to Resolve

- [ ] Schema for `attribute-formulas.json` (what fields, what types)
- [ ] Initial coefficient values (can be tuned later, but need starting points)
- [ ] Function shape: linear, polynomial, or lookup table?
- [ ] Secondary Attribute formulas (Momentum, Poise, Echo, Affinity, Synchrony)
- [ ] Are there per-level scaling factors on top of attribute coefficients?

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/01-rpg-mechanics.md` — Attribute mapping table (lines 112-173), secondary attributes (lines 193-211)
- `docs/1-architecture/04-meta-services.md` — Compilation algorithm (lines 509-582), config schema (lines 640-656)
