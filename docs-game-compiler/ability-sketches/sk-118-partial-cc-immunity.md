# SK-118: Partial CC Immunity

## Designer Intent

During certain ability animations, my character gains Push Immunity — I can't be knocked back, pulled, or displaced, but I CAN still be stunned, rooted, or frozen. This lets me commit to a big ability without being pushed out of position, while still being vulnerable to hard CC. A stronger tier grants Full Super Armor — immune to everything.

## Primitive Composition

P-62 (Categorized CC Immunity)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (automatic during ability animations)
- No target (self-applied)

## Observable Behavior

1. Begin casting a heavy ability — gain Push Immunity for the cast duration
2. While Push Immune: knockback (SK-01 Toss), pull (SK-43 Drag), charge (SK-34), vortex (SK-31) — all BLOCKED
3. While Push Immune: stun (SK-24), root (SK-25), silence (SK-26), fear (SK-78), sleep (SK-27) — still APPLY
4. Cast completes — Push Immunity ends
5. Some abilities grant Full Super Armor instead: ALL CC blocked (same as SK-51 Unstoppable)
6. Super Armor tier is visible as a buff icon with the specific immunity level
7. Visual: blue glow for Push Immune, yellow glow for Full Super Armor

## Engine Primitives Required

### Per-CC-Type Immunity Flags

SK-51 Unstoppable is a single flag: `is_unstoppable = true` → all CC blocked. Partial CC Immunity requires GRANULAR flags:

```
struct CcImmunityFlags {
    immune_to_displacement: bool,  // Knockback, pull, toss, charge pin, vortex, drag
    immune_to_hard_cc: bool,       // Stun, sleep
    immune_to_soft_cc: bool,       // Root, silence, slow, blind, disarm
    immune_to_forced_movement: bool, // Fear, charm, mind control
    immune_to_taunt: bool,         // Taunt
}
```

Or more simply, grouped by CC CATEGORY:
```
enum CcCategory {
    Displacement,    // SK-01, SK-31, SK-34, SK-43, SK-56
    HardDisable,     // SK-24 Stun, SK-27 Sleep
    SoftDisable,     // SK-25 Root, SK-26 Silence, SK-28 Slow
    ForcedMovement,  // SK-78 Fear, SK-101 Charm, SK-40 Mind Control
    TargetOverride,  // SK-65 Taunt, SK-106 Berserk
    Mute,            // SK-110 Mute
}
```

Each immunity level blocks specific categories:
- **Push Immune**: `immune_to_displacement = true`, all others false
- **CC Immune (Super Armor)**: ALL flags true (same as SK-51 Unstoppable)
- **Custom**: any combination (e.g., immune to displacement + forced movement, but not stun)

### CC Application With Category Check

Every CC application must check the target's immunity flags for the specific CC category:

```
fn try_apply_cc(target: &Entity, cc_effect: &CcEffect) -> bool {
    let immunity = target.get_cc_immunity_flags();

    match cc_effect.category {
        Displacement => if immunity.immune_to_displacement { return false; },
        HardDisable => if immunity.immune_to_hard_cc { return false; },
        SoftDisable => if immunity.immune_to_soft_cc { return false; },
        ForcedMovement => if immunity.immune_to_forced_movement { return false; },
        TargetOverride => if immunity.immune_to_taunt { return false; },
        Mute => if immunity.immune_to_mute { return false; },
    }

    // CC not blocked — apply normally (DR, tenacity, etc.)
    apply_cc(target, cc_effect);
    true
}
```

### CC Category Classification

Every CC ability must be classified into a category at compile time. The compiler tags each CC effect with its category:
- SK-01 Toss → `Displacement`
- SK-24 Stun → `HardDisable`
- SK-25 Root → `SoftDisable`
- SK-78 Fear → `ForcedMovement`
- SK-65 Taunt → `TargetOverride`

This classification also feeds into the DR system (SK-28) — DR categories should align with immunity categories.

### Animation-Bound Immunity

In Lost Ark, immunity is granted DURING ability animations — the entity gains immunity when the cast starts and loses it when the cast ends. This is a temporary buff tied to the ability's cast time:

```
fn on_ability_cast_start(entity: &mut Entity, ability: &AbilityDef) {
    if let Some(immunity) = ability.cast_immunity {
        entity.apply_temporary_cc_immunity(immunity, ability.cast_duration_ticks);
    }
}
```

The compiler defines per-ability: "during this ability's cast, grant this immunity tier." The engine automatically applies and removes the immunity buff.

## Cross-Boundary Concerns

TODO: CC immunity is a local state on the entity's Arbiter. When CC is applied via relay (cross-boundary attack), the target's Arbiter checks immunity flags locally and rejects blocked CC categories. The attacker doesn't need to know which immunities are active — the rejection happens on the target side.

## Compiler Requirements

TODO: Designer specifies: per-ability cast immunity tier (none, push immune, full super armor), CC category classification for all CC effects, per-category immunity flags. Compiler produces:
- CcImmunityFlags on entity state
- Per-ability `cast_immunity: Option<CcImmunityTier>` in ability definitions
- CC category enum with per-effect classification
- CC application check expanded to per-category immunity
- Temporary immunity buff tied to ability cast duration

The compiler adds CC categories as a first-class concept, extending the existing CC system (SK-24 through SK-28, SK-50, SK-65, SK-78, SK-101, SK-102, SK-106, SK-110) with categorical classification and per-category immunity.

## Open Questions

- Can immunity tiers be stacked (push immune + custom immunity from two sources)?
- Does immunity prevent the CC OR prevent the entire ability (damage + CC, or just the CC portion)?
- Can partial immunity be applied as a debuff on enemies (e.g., "this enemy is vulnerable to displacement but immune to stun")?
- Does the immunity prevent SK-88 Positional Leash (is leash "displacement" or its own category)?
- Does push immunity prevent SK-31 Vortex pull (yes — it's displacement)?
- Does push immunity prevent SK-101 Charm walk (charm is forced movement, not displacement)?
- Should the immunity tier be visible to enemies (they can see "this target is push immune")?
- How many tiers should exist (2: push immune + full, or N: customizable)?
- Does SK-114 Piercing Execute bypass CC immunity (execute bypasses everything)?
- Should partial immunity affect DR tracking (immune CC applications don't count toward DR)?
