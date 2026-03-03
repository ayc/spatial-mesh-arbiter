# T1-05: Stat Caps & Overflow Clamping

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md`

## Audit Notes

**Most of this is already specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| Cap values | **Fully listed** — crit 75%, crit_mult 5.0, CDR 50%, block 75%, evasion 60%, resist 85, dmg_red 50%, lifesteal 25%, spell_vamp 25% | `04-meta-services.md` lines 645-656 |
| Enforcement timing | **Specified** — At stat compilation time via `min()` calls | `04-meta-services.md` lines 574-580 |
| Resistance floor | **Specified** — `-100` (double damage) to `85` (15% damage), enforced at **resolution time** | `01-rpg-mechanics.md` lines 608-609 |

## Remaining Gap (Narrow)

### 1. Intermediate Overflow

If a buff pushes a stat over the cap, what happens? Example: player has 40% crit from gear (post-compilation, capped). A buff adds +50% crit.
- Is the buff evaluated as `min(40 + 50, 75) = 75%`?
- Or does the buff stack past the cap temporarily, only to be re-clamped?
- The buff evaluation algorithm in RPG Mechanics shows flat-then-multiplicative ordering, but doesn't show cap re-enforcement after buffs.

### 2. Non-Resistance Negative Floors

Resistance has an explicit floor (-100). But can other stats go negative?
- Can `crit_chance` be debuffed below 0%?
- Can `move_speed` go negative? (Entity moves backward?)
- Can `damage_reduction_pct` go negative? (Take amplified damage?)

## Questions to Resolve

- [ ] Are caps re-enforced after buff evaluation, or only at compilation?
- [ ] Negative floors for non-resistance stats (global rule: no stat below 0? Or per-stat?)
- [ ] Can buffs that exceed caps "bank" against future debuffs, or are excess points wasted?

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/04-meta-services.md` lines 574-580 — Cap enforcement pseudocode
- `docs/1-architecture/04-meta-services.md` lines 645-656 — Cap values
- `docs/3-gameplay-systems/01-rpg-mechanics.md` lines 608-609 — Resistance floor/ceiling
- `docs/3-gameplay-systems/01-rpg-mechanics.md` — Buff evaluation algorithm
