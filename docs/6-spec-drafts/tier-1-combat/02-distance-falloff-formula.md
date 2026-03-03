# T1-02: Distance Falloff Formula

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md`

## Problem Statement

The combat resolution pseudocode calls `calculate_falloff(distance)` but the function is never defined. This multiplier affects final damage for AoE and ranged abilities.

## Questions to Resolve

- [ ] Shape of falloff curve: linear, inverse-square, step function, or designer-configurable per ability?
- [ ] Is falloff relative to ability max_range or to geometry radius?
- [ ] Does falloff affect the full CombatContext or only base_damage?
- [ ] Is there a minimum falloff (e.g., always at least 20% damage at edge)?
- [ ] Do targeted (single-target) abilities have falloff, or only AoE?

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/01-rpg-mechanics.md` — `apply_combat_math` pseudocode
- `docs/3-gameplay-systems/02-ability-framework.md` — Geometry types with radius
