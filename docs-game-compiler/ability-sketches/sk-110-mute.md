# SK-110: Mute

## Designer Intent

I doom an enemy, disabling ALL their passive abilities and item effects for the duration. Their aura stops, their thorns stop, their lifesteal stops, their item procs stop. They become a basic entity with only their active abilities (which are also silenced by Doom). They're stripped of everything.

## Primitive Composition

P-26 (Capability Bitmask)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity

## Observable Behavior

1. Cast on enemy — Mute debuff applied
2. All PASSIVE abilities are disabled: SK-08 Aura stops pulsing, SK-23 Thorns stops firing, passive regen stops
3. All ITEM passive effects are disabled: on-hit procs, passive stat bonuses from items, lifesteal
4. Active abilities may or may not also be silenced (Doom silences + mutes; Mute alone is separable)
5. Duration: typically long (15+ seconds for Doom)
6. The target retains their base stats — only bonus effects from passives/items are suppressed
7. Cleansable? Design choice (Doom is typically NOT cleansable)
8. Visual: heavy debuff indicator, suppressed ability icons greyed out

## Engine Primitives Required

### New Capability Suppression: Passive Mute

Complete capability suppression matrix:

| Flag | Suppresses |
|---|---|
| `can_move: false` | Voluntary movement (Root SK-25) |
| `can_attack: false` | Auto-attacks (Disarm SK-102) |
| `can_cast: false` | Active ability casts (Silence SK-26) |
| **`passives_active: false`** | **Passive abilities + item effects (Mute SK-110)** |

```
status_effect: MuteDebuff {
    expires_at_tick: u64,
    also_silenced: bool,  // Doom: mute + silence combined
}
```

When `passives_active: false`:
- All passive status effects owned by the entity are SUSPENDED (not removed — they resume when mute ends)
- SK-08 Aura: stops pulsing, enemies in range lose the aura debuff
- SK-23 Thorns: stops triggering on being hit
- SK-22 Damage Reflection: stops reflecting
- Passive regen: stops regenerating HP/mana
- Item on-hit effects: stop triggering
- Item passive auras: stop applying
- Any "always-on" effect: paused

### Passive Suspension vs Removal

Mute SUSPENDS passives — it doesn't REMOVE them. When mute expires:
- All suspended passives resume from where they left off
- SK-08 Aura immediately resumes pulsing
- Item effects immediately reactivate

This is different from SK-15 Purify (which REMOVES effects permanently). Mute pauses; Purify deletes.

### Classification: What Is a "Passive"?

The engine (and compiler) must classify every effect as:
- **Active**: requires player input to trigger (ability casts, auto-attacks)
- **Passive**: functions automatically without player input (auras, procs, regen, item effects)

Mute disables passives. Silence disables actives. Both together = almost everything disabled.

The compiler must tag every ability and effect with `is_passive: bool` at compile time. At runtime, the Arbiter checks: is the entity muted? If yes, skip all passive effect evaluations.

### Per-Tick Passive Evaluation Skip

Each tick, the Arbiter evaluates passive effects for each entity:
- Tick auras (SK-08)
- Check reactive procs (SK-23 Thorns, SK-22 Reflection)
- Apply passive regen
- Evaluate item effects

When muted, the Arbiter SKIPS all of these for the affected entity. The skip is a single flag check at the start of passive evaluation.

## Cross-Boundary Concerns

TODO: Mute is a status effect on the target's entity. All passive suppression is local to the target's Arbiter. No special cross-boundary handling beyond the initial debuff application relay.

One concern: if the muted entity's SK-08 Aura was affecting Ghosts on neighboring Arbiters, muting the aura means those Ghosts stop receiving aura effects. The neighbors need to know the aura stopped. Does the aura cessation propagate via Ghost updates, or do neighbors continue applying a stale aura until the next Ghost update reveals the aura is gone?

## Compiler Requirements

TODO: Designer specifies: target debuff, duration, disable all passive abilities, disable all item passive effects, optionally also silence (disable active abilities), suspends (not removes) passives, resumes on expiry. Compiler produces:
- MuteDebuff status effect with `passives_active: false`
- Per-tick passive evaluation skip when muted
- Passive/active classification on all abilities and effects at compile time
- Suspension semantics (passives resume on mute expiry, not restart)

The compiler adds `is_passive: bool` to every ability and effect definition. The engine checks this flag during passive evaluation.

## Open Questions

- Does mute disable passive stat bonuses from items (flat +damage from equipment) or only proc effects?
- Does mute disable SK-37 Time Rewind's rolling buffer recording (it's a passive recording)?
- Does mute disable SK-45 Essence Collection's passive pickup (walking over orbs)?
- Does mute disable SK-100 Ally-Untargetable's permanent CC immunity (it's a permanent passive)?
- If the muted entity has SK-70 Energy Shield active, does the Energy decay still happen (is decay a passive)?
- Does mute affect summoned entities (SK-06 minions lose their AI while owner is muted)?
- Can mute and silence be applied independently (mute passives but allow casting)?
- Is mute subject to Tenacity/Diminishing Returns, or is it a unique debuff category?
- Does SK-51 Unstoppable prevent mute (mute isn't CC — it's capability suppression)?
