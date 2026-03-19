# SK-95: Mass Effect Detonation

## Designer Intent

I have two abilities that apply effects to enemies and allies. My trait is a DETONATOR — when I press D, every active instance of my effects across all targets simultaneously triggers a burst effect. Healing effects burst-heal, damage effects burst-damage + root. One button, every target, all at once.

## Primitive Composition

P-16 (Stat Layering) → P-09 (Shape Overlap Query) → P-64 (Combo Field × Finisher Matrix)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (global — detonates ALL active instances of caster's effects)

## Observable Behavior

1. Over time, I've applied Healing Pathogen to 4 allies and Weighted Pustule to 3 enemies
2. Press D — ALL 7 effects detonate simultaneously
3. Each Healing Pathogen: burst-heals the ally for a large amount, then the HoT is removed
4. Each Weighted Pustule: burst-damages + roots the enemy for 1.5 seconds, then the slow is removed
5. Effects that were about to expire still detonate (maximum value extraction)
6. After detonation: all effects are consumed — targets are clean
7. Visual: simultaneous burst effects on every affected target across the battlefield

## Engine Primitives Required

### Global Effect Query by Caster

The detonation needs to find ALL active status effects owned by this caster across ALL targets. This requires either:

**Option A: Caster-tracked effect registry**
```
struct CasterEffectRegistry {
    active_effects: Vec<(EntityID, EffectId, EffectType)>,
    // target_entity_id, effect_instance_id, type (for detonation behavior)
}
```
The caster maintains a list of all effects they've applied. On detonation, iterate the list and trigger each one.

**Option B: Per-entity scan**
On detonation, the Arbiter scans ALL entities for effects owned by this caster. Expensive but doesn't require a separate registry.

Option A is better — bounded cost, O(N) where N is the number of active effects.

### Simultaneous Multi-Target Resolution

The detonation triggers on multiple targets at the same tick. Each target's detonation resolves independently:
- Ally with Healing Pathogen: burst heal
- Enemy with Weighted Pustule: burst damage + root

All resolutions must happen in the same tick for the "simultaneous" feel. The Arbiter processes them sequentially (deterministic order) but they all resolve within one tick.

### Cross-Entity Effect Ownership

Status effects must carry `caster_id` — who applied this effect. This is needed for:
1. Detonation: only detonate effects from THIS caster
2. Kill credit: damage from detonated effects credits the caster
3. Proc attribution: detonation damage triggers the caster's on-hit procs

Most effects already carry `caster_id` for damage attribution. The detonation mechanic makes this field CRITICAL for the mass-query pattern.

## Cross-Boundary Concerns

TODO: The caster's effects may be active on targets across multiple Arbiters:
- Ally on Arbiter A has Healing Pathogen
- Enemy on Arbiter B has Weighted Pustule
- Enemy on Arbiter C has Weighted Pustule

On detonation, the caster's Arbiter must:
1. Query the caster's effect registry
2. For local targets: detonate directly
3. For cross-boundary targets: relay "detonate effect X on entity Y" to the target's Arbiter

This is a **fan-out detonation** — one command produces N relays to potentially N different Arbiters. Bounded by the number of active effects (typically < 10).

The caster's effect registry must track which Arbiter each target is on. If a target crossed a boundary (entity handoff), the registry must update the Arbiter reference.

## Compiler Requirements

TODO: Designer specifies: trait activation (detonate all active effects), per-effect-type detonation behavior (Pathogen: burst heal + remove, Pustule: burst damage + root + remove), global scope (all targets, any distance). Compiler produces:
- Effect definitions with detonation behavior
- CasterEffectRegistry for tracking active effect instances
- Detonation action: query registry → trigger each effect's detonation behavior → remove effects
- Cross-boundary relay for remote detonation

The compiler needs to support **effect detonation callbacks** — effects that have a "detonate" action in addition to their normal tick/expiry behavior.

## Open Questions

- Does detonation count as "damage from caster" for SK-02 Poison Shot refresh and similar triggers?
- Does the burst heal from detonated Pathogen go through SK-92 Anti-Heal?
- Can the detonation be activated while the caster is CC'd (stunned, silenced)?
- If a target with an active effect dies before detonation, is the effect removed from the registry?
- Does detonation trigger on-hit procs per target (SK-09 Chain Lightning per enemy detonated)?
- Can the caster detonate selectively (only Pathogens, only Pustules), or is it always all?
- Does the root from Pustule detonation go through DR (SK-28)?
- What happens if a detonated effect is on an entity in SK-91 Stasis (timers paused)?
- If the caster has effects on 20 targets across 5 Arbiters, is the 5-way fan-out relay within acceptable traffic bounds?
