# SK-48: Death Coil

## Designer Intent

I cast a projectile at a target. If the target is an enemy, it deals damage. If the target is an ally, it heals them instead. Same ability, same cooldown, same projectile — different effect based on who I'm targeting.

## Primitive Composition

P-17 (Conditional Thresholds) → P-21 (Value Conversion)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target entity (enemy OR ally — player chooses)

## Observable Behavior

1. Cast on an enemy: projectile launches, on hit deals X damage
2. Cast on an ally: projectile launches, on hit heals for Y HP
3. Can also cast on self: heals self for Y HP (projectile is instant / zero travel time to self)
4. Same cooldown regardless of target type
5. Same resource cost regardless of target type
6. Visual: dark projectile when targeting enemy, green projectile when targeting ally

## Engine Primitives Required

### Dual-Mode Ability Resolution

All existing abilities have a fixed effect: damage, heal, CC, buff, etc. Death Coil resolves differently based on the **target's allegiance relative to the caster**.

The `validate_intent` hook must:
1. Accept any entity as a valid target (not filtered to enemies-only or allies-only)
2. Determine the target's team/faction relative to the caster

The `resolve_external` hook must:
1. Check target allegiance: `is_ally(caster, target)` or `is_enemy(caster, target)`
2. If enemy: resolve as damage (Phase 1 offense → Phase 2 defense on target)
3. If ally: resolve as heal (apply healing directly)

This branching must happen inside the game adapter hooks, not in the engine. The engine just delivers the proposal — the adapter decides the outcome.

### Target Validation Flexibility

Current ability sketches have a targeting filter compiled into the ability definition:
- `target_filter: Enemies` (SK-02 Poison Shot)
- `target_filter: Allies` (SK-15 Purify)
- `target_filter: Ground` (SK-29 Blizzard)

Death Coil needs: `target_filter: Any` or `target_filter: AnyEntity` — the filter accepts both friends and foes. The ability definition must express "any valid entity is a legal target."

### CombatContext Branching

If the target is an enemy, the caster's offensive stats are used to build a CombatContext for damage. If the target is an ally, no CombatContext is needed — it's a direct heal. The Phase 1 pre-roll (building CombatContext with offensive stats) should only happen for the damage path.

Does the Arbiter pre-roll CombatContext before knowing the resolution path? If yes, it wastes computation on heal targets. If no, the ability must declare "CombatContext is conditional" — only built for enemy targets.

## Cross-Boundary Concerns

TODO: Two scenarios:

1. **Target is an enemy Ghost:** Standard damage relay. Caster's Arbiter builds CombatContext (Phase 1), sends relay to target's Arbiter for Phase 2. No difference from any other damage ability.

2. **Target is an ally Ghost:** Heal relay. Caster's Arbiter determines "this is a heal," sends a heal event to the ally's Arbiter. This is the same cross-boundary pattern as SK-16 Holy Ground (healing a Ghost ally). The relay carries the heal amount, not a CombatContext.

The caster's Arbiter must determine the target's allegiance from the Ghost data. Do Ghosts carry team/faction information? Currently GhostUpdate has position, velocity, movement_class — no team field. The Arbiter might need to know which Ghosts are friendly vs hostile for this to work.

## Compiler Requirements

TODO: Designer specifies: target filter (any entity), on-enemy-target (damage X), on-ally-target (heal Y), on-self-target (heal Y, instant), same cooldown/cost for both. Compiler produces:
- Ability definition with `target_filter: Any`
- Branching resolution logic: `if is_enemy(target) → damage_payload else → heal_payload`
- Conditional CombatContext: only pre-roll offensive stats for enemy targets
- Two distinct outcome payloads within a single ability definition

The compiler needs to support **conditional resolution** — one ability definition that produces different outcomes based on runtime context. This is more complex than "always damage" or "always heal."

## Open Questions

- Does the damage path trigger on-hit procs (SK-09 Chain Lightning)?
- Does the heal path trigger on-heal effects (SK-04 Tether healing share)?
- Can the ability be used on untargetable allies (SK-44 Burrow)? They're untargetable — so no.
- Can the ability heal minions/summons (SK-06 Summon Swarm minions)?
- If the caster and an ally are on the same position, and the caster targets "self" while an enemy is also on that position, how does targeting disambiguate?
- Does the heal version benefit from healing-power stats, or is it a fixed amount?
- Does the damage version use the full two-phase combat pipeline, or is it a simplified single-phase?
- Can the ability hit an enemy that is currently being mind-controlled (SK-40) by the caster? Is a mind-controlled enemy treated as "ally" or "enemy"?
- How does the visual distinguish between the two modes on the wire (Edge Node needs to know which projectile effect to render)?
