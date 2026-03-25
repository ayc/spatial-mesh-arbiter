# T1-05: Stat Caps & Overflow Clamping

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md`

## Audit Notes

**Most of this is already specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| Cap values | **Fully listed** — crit 75%, crit_mult 5.0, CDR 50%, block 75%, evasion 60%, resist 85, dmg_red 50%, lifesteal 25%, spell_vamp 25% | `04-meta-services.md` lines 645-656 |
| Enforcement timing | **Specified** — At stat compilation time via `min()` calls | `04-meta-services.md` lines 574-580 |
| Resistance floor | **Specified** — `-100` (double damage) to `85` (15% damage), enforced at **resolution time** | `01-rpg-mechanics.md` lines 608-609 |

## Resolution

### 1. Intermediate Overflow: Caps Are Re-Enforced After Buffs

**Rule:** Stat caps apply at **evaluation time** (when the stat is read for combat resolution), not only at compilation time. Buffs CAN push a stat above the compiled cap in the raw modifier stack, but the effective value seen by the damage formula is always clamped.

```rust
fn get_effective_stat(entity: &Entity, stat_id: StatId) -> SimFixed {
    let base = entity.compiled_stats[stat_id];  // Post-compilation, already capped
    let buff_total = sum_active_modifiers(entity, stat_id); // Flat + percent from buffs
    let raw = apply_modifier_stack(base, buff_total);       // May exceed cap
    let cap = get_stat_cap(stat_id);
    raw.min(cap)  // Re-clamped at evaluation time
}
```

**Consequence:** Excess buff points above the cap ARE "banked" in the modifier stack. If a debuff later reduces the stat, the banked excess absorbs the debuff before the effective value drops below the cap. This is standard ARPG behavior (matches Diablo, PoE, Lost Ark).

**Example:** Player has 70% crit from gear (compilation capped at 75%). A buff adds +20% crit → raw = 90%. Effective crit = min(90%, 75%) = 75%. A debuff applies -25% crit → raw = 65%. Effective crit = min(65%, 75%) = 65%. The banked 15% above cap absorbed the first 15% of the debuff.

### 2. Non-Resistance Negative Floors

**Rule:** Each stat category has an explicit floor. Stats CANNOT go below their floor even under debuffs.

| Stat | Floor | Rationale |
|------|-------|-----------|
| `crit_chance` | 0% | Cannot have negative crit chance |
| `crit_multiplier` | 1.0 | Cannot deal less than base damage on crit |
| `cooldown_reduction` | 0% | Cannot have negative CDR (abilities can't take longer than base) |
| `block_chance` | 0% | Cannot have negative block |
| `evasion_rating` | 0% | Cannot have negative evasion |
| `resistance` (per element) | -100 | Already specified — double damage floor |
| `damage_reduction_pct` | -50% | Can take amplified damage, floored at +50% incoming |
| `lifesteal_pct` | 0% | Cannot have negative lifesteal |
| `spell_vamp_pct` | 0% | Cannot have negative spell vamp |
| `move_speed` | 10% of base | Cannot be fully immobilized by speed debuffs (Root uses CAN_MOVE flag instead) |

**Implementation:** Floors are enforced at evaluation time alongside caps:

```rust
fn get_effective_stat(entity: &Entity, stat_id: StatId) -> SimFixed {
    let raw = /* ... modifier stack ... */;
    let cap = get_stat_cap(stat_id);
    let floor = get_stat_floor(stat_id);
    raw.clamp(floor, cap)
}
```

### 3. Configuration

Floors are defined alongside caps in the game configuration:

```json
"stat_floors": {
    "crit_chance": 0.0,
    "crit_multiplier": 1.0,
    "cooldown_reduction": 0.0,
    "block_chance": 0.0,
    "evasion_rating": 0.0,
    "resistance_min": -100,
    "damage_reduction_pct": -0.50,
    "lifesteal_pct": 0.0,
    "spell_vamp_pct": 0.0,
    "move_speed_min_pct": 0.10
}
```

## References

- `docs/1-architecture/04-meta-services.md` lines 574-580 — Cap enforcement pseudocode
- `docs/1-architecture/04-meta-services.md` lines 645-656 — Cap values
- `docs/3-gameplay-systems/01-rpg-mechanics.md` lines 608-609 — Resistance floor/ceiling
