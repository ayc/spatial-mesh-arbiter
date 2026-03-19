# SK-123: Concentration

## Designer Intent

Some of my most powerful spells require CONCENTRATION to maintain. While concentrating, I can move, attack, and use non-concentration abilities freely. But I can only concentrate on ONE spell at a time — casting a second concentration spell ends the first. And taking damage risks breaking my concentration — each hit triggers a check, and if I fail, the spell ends prematurely.

## Primitive Composition

P-55 (Concentration Intercept) → P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Concentration ability (cast normally, then maintained)
- Damage events on the caster (trigger concentration checks)

## Observable Behavior

1. Cast a concentration spell (e.g., a persistent buff zone, a summoned creature, an ongoing debuff on an enemy)
2. The spell takes effect normally and PERSISTS as long as concentration is maintained
3. While concentrating: caster can move, auto-attack, and use non-concentration abilities freely
4. Casting ANOTHER concentration spell: the first one ENDS immediately (mutual exclusion)
5. Taking damage: CONCENTRATION CHECK — roll against a threshold
   - Pass: concentration maintained, spell persists
   - Fail: concentration broken, spell ends immediately
6. The check difficulty scales with damage taken (higher damage = harder to maintain)
7. Concentration indicator visible on the caster (which spell they're concentrating on)
8. Voluntarily ending concentration: caster can choose to stop concentrating at any time
9. Visual: subtle glow indicating active concentration, flash on concentration check, fizzle on break

## Engine Primitives Required

### Concentration as a Status Effect Category

Concentration is a new CATEGORY of status effect — effects that are "maintained" by the caster:

```
struct ConcentrationState {
    active_effect_id: Option<EffectId>,  // Currently maintained effect (only one)
    check_threshold_base: SimFixed,       // Base threshold for concentration checks
}

struct StatusEffect {
    // ... existing fields
    requires_concentration: bool,  // Does this effect require concentration?
    concentration_owner: Option<EntityID>,  // Who is concentrating on this effect
}
```

### Mutual Exclusion (One Concentration at a Time)

When a caster activates a new concentration effect:
1. Check: does the caster already have an active concentration? (`concentration_state.active_effect_id.is_some()`)
2. If yes: END the existing concentration effect (remove it from whatever entity it's on)
3. Set the new effect as the active concentration: `concentration_state.active_effect_id = Some(new_effect_id)`

This mutual exclusion is enforced at CAST TIME — the old effect is removed before the new one is applied. The engine doesn't need to check continuously; the check happens once when a new concentration ability is cast.

### Damage-Triggered Concentration Check

On each damage event where the caster takes damage:
1. Check: does the caster have active concentration? If no → skip
2. Calculate check difficulty: `threshold = max(10, damage_taken / 2)` (D&D formula: DC = max(10, damage/2))
3. Roll deterministic RNG: `roll = deterministic_rng(caster.entity_id, current_tick, "concentration")`
4. If `roll >= threshold`: PASS — concentration maintained
5. If `roll < threshold`: FAIL — concentration BROKEN, effect removed

```
fn on_damage_received(entity: &mut Entity, damage: SimFixed) {
    if let Some(effect_id) = entity.concentration_state.active_effect_id {
        let dc = max(SimFixed::from(10), damage / SimFixed::from(2));
        let roll = deterministic_rng_roll(entity.entity_id, current_tick(), "concentration");

        if roll < dc {
            // Concentration broken
            remove_effect(effect_id);
            entity.concentration_state.active_effect_id = None;
            emit_event(ConcentrationBroken { entity_id, effect_id });
        }
    }
}
```

### Concentration vs Channeling

Concentration and channeling are DIFFERENT maintained-effect patterns:

| Aspect | Channeling (SK-64 Mosh Pit) | Concentration (SK-123) |
|---|---|---|
| Can move? | No (locked in place) | Yes (free movement) |
| Can use other abilities? | No | Yes (non-concentration abilities) |
| Interrupted by CC? | Yes (any CC ends channel) | No (CC doesn't break concentration) |
| Interrupted by damage? | Sometimes (design choice) | Probabilistic (check on each hit) |
| Duration | Fixed (channel duration) | Indefinite (until broken or voluntarily ended) |
| Mutual exclusion | One channel at a time | One concentration at a time |

Concentration is the MORE PERMISSIVE version — the caster can act normally, but the maintained effect is at risk every time they take damage.

### Effects That Require Concentration

Many different effect types can require concentration:
- Persistent buff zone (SK-29 Blizzard that persists via concentration instead of a timer)
- Summoned creature (SK-06 that despawns if concentration breaks)
- Ongoing debuff on an enemy (DoT that requires concentration to maintain)
- Team-wide buff (SK-20 Battle Cry that persists via concentration)

The `requires_concentration: true` flag can be set on ANY status effect or entity spawned by an ability. The compiler defines which abilities require concentration.

### Concentration Duration

Unlike channeling (fixed duration), concentration has NO INHERENT DURATION — the effect persists as long as concentration is maintained (or up to a maximum duration defined per spell). The caster can maintain concentration indefinitely if they avoid damage or pass all checks.

Optional: some concentration effects have a maximum duration regardless of concentration: "maintain for up to 10 minutes." The effect has an expiry tick but can end earlier if concentration breaks.

## Cross-Boundary Concerns

TODO: Concentration is local to the caster's entity. The concentration check happens on the caster's Arbiter when the caster takes damage. All local.

The concentrated EFFECT might be on a different entity or Arbiter:
1. **Buff on ally (different Arbiter)**: If concentration breaks, the caster's Arbiter must relay "remove effect X from entity Y" to the ally's Arbiter. One relay on break.
2. **Zone on the ground (different Arbiter)**: If concentration breaks, the zone's Arbiter must be notified to despawn the zone. One relay on break.
3. **Debuff on enemy (different Arbiter)**: Same pattern — relay the removal.

The concentration break event must propagate to whatever entity/Arbiter hosts the concentrated effect. This is a single cross-boundary relay on break — not per-tick.

## Compiler Requirements

TODO: Designer specifies: per-ability `requires_concentration: bool`, concentration check formula (DC = max(10, damage/2) or custom), mutual exclusion (one concentration at a time), concentration broken on failed check, voluntary ending allowed, can act freely while concentrating. Compiler produces:
- ConcentrationState as per-entity state
- `requires_concentration` flag on status effect / ability definitions
- Mutual exclusion enforcement at cast time
- Damage-received hook: concentration check with deterministic RNG
- Effect removal on concentration break
- Cross-boundary removal relay for remote concentrated effects
- Downstream payload: concentration indicator (which effect is being maintained)

The compiler adds concentration as a maintained-effect category alongside channeling. The game defines which abilities require concentration and the check formula.

## Open Questions

- Does SK-44 Burrow (invulnerable) protect concentration (can't take damage → no checks needed)?
- Does SK-17 Shield absorption trigger a concentration check (damage was absorbed, not taken)?
- Does SK-113 Hit-Count Shield block trigger a concentration check (hit was blocked, but an "impact" occurred)?
- Can concentration be maintained during SK-91 Stasis (timers paused, no damage taken)?
- Does SK-73 Death Immunity interact (HP floors at 1 → massive damage → very hard concentration check)?
- Can concentration effects be dispelled by enemies independently of breaking concentration (SK-15 Purify removes the effect but concentration state persists)?
- Does SK-110 Mute break concentration (mute disables passives — is concentration a "passive" maintaining an effect)?
- Can multiple entities concentrate on the same effect (team concentration)?
- Does the concentration check use the caster's stats (e.g., higher Willpower = easier checks)?
- Should failed concentration checks have a grace period (don't check again for N ticks after a failure)?
- Does Kinematic Dilation affect concentration check timing?
