# SK-114: Piercing Execute

## Designer Intent

I swing my axe at an enemy. If they're below an HP threshold (e.g., 400 HP), they are INSTANTLY KILLED. Not "take 99999 damage" — KILLED. This kill bypasses EVERYTHING: invulnerability, shields, death immunity, death prevention, hit-count shields. Nothing saves them. If they're below the threshold, they die.

## Primitive Composition

P-17 (Conditional Thresholds) → P-24 (Resolution Bypass)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in melee range)

## Observable Behavior

1. Check target's current HP
2. If HP is above threshold: deal normal damage (ability functions as a regular attack)
3. If HP is at or below threshold: TARGET IS INSTANTLY KILLED
4. The kill bypasses: invulnerability (SK-44), death immunity (SK-73), death prevention (SK-93), shields (SK-17, SK-113), deferred resolution (SK-112), all other protective mechanics
5. The kill triggers: on-kill effects (SK-11 On-Kill Cascade), kill credit, HardEvent
6. If the kill succeeds: ability's cooldown is reset (can be used again immediately)
7. Visual: massive executioner axe animation, distinct kill effect (no damage number — just DEAD)

## Engine Primitives Required

### Absolute Kill Command

All existing damage goes through the damage resolution pipeline: damage → shields → mitigation → block → HP reduction → death check → death prevention checks. The Piercing Execute BYPASSES THE ENTIRE PIPELINE:

```
fn resolve_piercing_execute(target: &mut Entity, hp_threshold: SimFixed) {
    if target.hp <= hp_threshold {
        // BYPASS everything: shields, invulnerability, death immunity, death prevention
        force_kill(target);  // Directly trigger death, no interception allowed
    } else {
        // Normal damage (not an execute — target is above threshold)
        apply_normal_damage(target, base_damage);
    }
}

fn force_kill(entity: &mut Entity) {
    entity.hp = SimFixed::ZERO;
    // Skip ALL death prevention checks:
    // - Do NOT check SK-73 Death Immunity
    // - Do NOT check SK-93 Death Prevention
    // - Do NOT check SK-57 death-triggered form transformation
    // - Do NOT check SK-112 Deferred Resolution
    trigger_death(entity, bypass_prevention: true);
}
```

### Death Pipeline Bypass Flag

The death pipeline currently supports interception (SK-93, SK-73, SK-57 death-form). Piercing Execute needs a `bypass_prevention: true` flag that skips ALL interception:

```
fn check_death(entity: &mut Entity, bypass_prevention: bool) -> bool {
    if entity.hp <= SimFixed::ZERO {
        if !bypass_prevention {
            // Normal death checks
            if entity.has_death_immunity() { entity.hp = SimFixed::ONE; return false; }
            if entity.has_death_prevention() { entity.hp = entity.max_hp; return false; }
            if entity.has_death_form() { transform(entity); return false; }
        }
        // Bypass = true OR no prevention: entity dies for real
        return true;
    }
    false
}
```

### HP Threshold Check vs Actual HP

The execute threshold checks the target's ACTUAL current HP, not effective HP (no shields, no deferred damage). This means:
- Target at 300 HP with a 1000 HP shield: HP = 300 < 400 threshold → KILLED (shield doesn't matter)
- Target at 500 HP but has SK-112 Deferred Resolution with 200 accumulated damage: visible HP = 500 > 400 threshold → NOT executed (deferred damage is hidden)

Design choice: should the threshold use visible HP, actual HP, or effective HP (including shields)?

### Cooldown Reset on Kill

If the execute kills the target (HP was below threshold), the ability's cooldown is immediately reset. This allows chain executions in team fights — execute one low-HP enemy, then immediately execute another.

The cooldown reset is conditional on the EXECUTE path succeeding — if the target was above threshold and normal damage was dealt, no reset.

## Cross-Boundary Concerns

TODO: If the target is a Ghost, the caster's Arbiter uses Ghost HP for the threshold check. Ghost HP might be stale — the target's actual HP could be different. Scenarios:

1. **Ghost HP shows 350 (below 400 threshold)** but actual HP is 450 (above threshold): Caster's Arbiter sends the execute relay. Target's Arbiter re-checks HP → above threshold → resolves as normal damage, not execute. Cooldown NOT reset.

2. **Ghost HP shows 450 (above threshold)** but actual HP is 350 (below threshold): Caster's Arbiter resolves as normal damage (not execute). The execute opportunity is missed due to stale Ghost data.

The execute threshold check should happen on the TARGET's Arbiter (where HP is authoritative). The caster sends "execute with threshold 400" and the target's Arbiter determines execute vs normal damage.

## Compiler Requirements

TODO: Designer specifies: melee range, HP threshold check, below threshold = instant kill (bypasses everything), above threshold = normal damage, cooldown reset on execute kill. Compiler produces:
- Execute ability definition with HP threshold
- Two resolution paths: execute (force_kill with bypass) or normal damage
- Death pipeline bypass flag (`bypass_prevention: true`)
- Conditional cooldown reset on execute path

The compiler needs to support **death pipeline bypass** — the ability to mark a kill as unprevantable. This is a new flag on the death trigger that skips all interception hooks.

### docs-core/ Impact

This may require a `docs-core/` change:
- The death pipeline must support a bypass flag that skips all game-adapter-provided death interception hooks
- This is a safety concern: the engine must ensure that bypass is only available through authorized ability definitions, not exploitable

## Open Questions

- Does the execute work on entities in SK-44 Burrow (invulnerable + untargetable)? If untargetable, you can't target them. Execute only works if you can TARGET the entity.
- Does the execute work through SK-91 Stasis (entity is in stasis — untargetable)?
- Does the execute bypass SK-57 death-triggered form transformation (Anivia egg, Meepo clones)?
- Does the execute bypass SK-112 Deferred Resolution (kill despite hidden ledger)?
- Should the execute deal the threshold as damage instead of an instant kill (for proc purposes)?
- Does the execute trigger on-kill effects (SK-11 On-Kill Cascade, kill credit)?
- Does the execute generate a HardEvent (kill tracking, loot, XP)?
- Can the HP threshold scale with the caster's stats (higher stats = higher threshold)?
- Does SK-100 Ally-Untargetable's permanent CC immunity prevent the execute (execute isn't CC)?
- Is this the ONLY ability with death pipeline bypass, or can the compiler generate others?
