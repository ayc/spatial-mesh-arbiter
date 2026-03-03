# T1-06: Reactive Proc & Cascade Depth

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/02-ability-framework.md`

## Audit Notes

**Much of this IS specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| Proc depth guard | **Specified** — Thorns only fires on `DirectCast` + `proc_depth == 0`. Counter-hit sent with `proc_depth + 1`. | `01-rpg-mechanics.md` lines 625-635 |
| Cross-boundary flow | **Specified** — Uses standard Arbiter Relay Protocol. `proc_depth` is carried in `CombatContext`. | `02-ability-framework.md` lines 272-273 |
| Processing timing | **Specified** — Cascades are deferred to next tick via `internal_inbox.push()` | `02-ability-framework.md` lines 251-264 |

## Remaining Gap (Narrow)

### 1. Hard Proc Depth Ceiling

The `proc_depth == 0` check for thorns implies a ceiling of 1, but:
- Is this a universal rule (`MAX_PROC_DEPTH = 1`)? Or can some abilities chain deeper?
- What if a future ability needs depth 2? Is there a config knob?

### 2. Proc Types Beyond Thorns

Only thorns is shown. Are there other reactive proc categories?
- On-spell-hit procs
- On-crit procs
- On-block procs
- Do these follow the same `proc_depth == 0` guard?

### 3. Cross-Boundary Recursive Edge Case

Entity A (Arbiter 1) has thorns, Entity B (Arbiter 2) has thorns:
- B hits A → A's thorns fires back at B (proc_depth=1) → B's thorns would want to fire, but `proc_depth == 1` blocks it
- This works. But is it explicitly tested/stated?

## Questions to Resolve

- [ ] Is `MAX_PROC_DEPTH = 1` a universal rule, or per-ability-type?
- [ ] Full list of reactive proc categories (thorns, on-hit, on-crit, on-block?)
- [ ] Do all proc types share the same depth guard?
- [ ] Should MAX_PROC_DEPTH be a config value?

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/01-rpg-mechanics.md` lines 625-635 — Thorns proc with depth guard
- `docs/3-gameplay-systems/02-ability-framework.md` lines 251-264 — Cascade via internal_inbox
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` — CombatContext.proc_depth
