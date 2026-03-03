# T3-01: Projectile Simulation

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/02-ability-framework.md`

## Audit Notes

**Core projectile mechanics ARE specified** in `03-mesh-arbiter-state.md` (ProjectileActor tick pseudocode, lines 1425-1534):

| Aspect | Status | Source |
|--------|--------|--------|
| Integration | **Specified** — Euler: `pos += vel * step_dilation` | line 1491 |
| Homing steering | **Specified** — `desired_dir = (target_pos - pos).normalize(); vel = desired_dir * speed` | lines 1474-1480 |
| Pierce field | **Specified** — `pierce_remaining` tracked on ProjectileActor | line 978 |
| Fuse decrement | **Specified** — `fuse_remaining_ticks.saturating_sub(1)` | line 1493 |
| Collision call | **Specified** — `calculate_collisions(local_hitboxes)` called | line 1496 |
| Cross-boundary dilation | **Specified** — `compute_projectile_step_dilation()` with blend equation | lines 1561-1578 |
| Handoff protocol | **Specified** — 3-phase Prepare/Ack/Commit | `01-core-primitives.md` |

## Remaining Gap (Narrowed)

### 1. Turn Rate Limiting
Line 1477 has a TODO: "In a full implementation, apply a max `turn_rate` here to prevent instant 180-degree snaps." No turn rate formula or config value.

### 2. Explosion/Detonation Trigger
When exactly does a projectile detonate? On collision? On lifetime expiry? On fuse arm? The collision handling code calls `generate_impact_event()` but the trigger conditions are implicit.

### 3. Pierce Decrement
`pierce_remaining` exists but the decrement logic isn't shown. Does it decrement per target hit? Per frame? Is damage reduced per pierce?

### 4. `calculate_collisions()` Body
Called but never defined. What intersection tests? What about multi-victim ordering?

## Questions to Resolve

- [ ] Turn rate formula and config value
- [ ] Detonation trigger conditions (exhaustive list)
- [ ] Pierce decrement: per-target or per-frame? Damage reduction per pierce?
- [ ] `calculate_collisions()` implementation

## Proposed Resolution

_To be drafted._

## References

- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` lines 1425-1534 — ProjectileActor tick
- `docs/3-gameplay-systems/02-ability-framework.md` — Homing Missile example, pierce description
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` — ProjectileHandoffMessage
