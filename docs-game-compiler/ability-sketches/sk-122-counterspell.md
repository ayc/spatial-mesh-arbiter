# SK-122: Counterspell

## Designer Intent

I see an enemy begin casting a powerful spell. Before it resolves, I use my reaction to COUNTER it — the spell is cancelled entirely. No damage, no effect, no projectile. The enemy's mana/resource is consumed but nothing happens. I've nullified their ability at the cost of my reaction cooldown.

## Primitive Composition

P-40 (On-Cast Intercept)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (the counterspeller)
- Target entity (the enemy currently casting)
- Timing: must be used DURING the enemy's cast time (before resolution)

## Observable Behavior

1. Enemy begins casting an ability (cast bar visible)
2. During the cast time: I use Counterspell targeting the casting enemy
3. If successful: enemy's ability is CANCELLED — no damage, no projectile, no effect
4. The enemy's resource cost is still consumed (mana spent, slot used)
5. The enemy's ability goes on full cooldown (as if it was cast, but produced nothing)
6. My counterspell goes on cooldown
7. If the enemy's ability was instant (no cast time): cannot be countered (nothing to react to)
8. Visual: magical disruption effect on the enemy, fizzle animation, "Countered!" indicator

## Engine Primitives Required

### Cast-State Detection

For counterspell to work, the engine must expose an entity's CASTING STATE to other entities:

```
struct CastingState {
    is_casting: bool,
    ability_being_cast: AbilityId,
    cast_start_tick: u64,
    cast_end_tick: u64,       // When the ability would resolve
    can_be_counterspelled: bool,   // Some abilities are uncounterspellable
}
```

The casting state must be visible to nearby entities (and their Edge Nodes for UI). When an entity begins casting an ability with a cast time > 0, `is_casting = true` and the casting info is populated.

### Mid-Cast Ability Cancellation

When counterspell hits a casting entity:
1. Check: `target.casting_state.is_casting == true`
2. Check: `target.casting_state.can_be_counterspelled == true`
3. If both: CANCEL the cast
   - Set `target.casting_state.is_casting = false`
   - Do NOT resolve the ability (no damage, no effects, no projectile spawning)
   - Consume the ability's resource cost (mana/resource already committed)
   - Put the ability on full cooldown
   - Emit "ability countered" event (for visual feedback, metrics)
4. If the target isn't casting or ability is uncounterable: counterspell fizzles (wasted)

```
fn resolve_counterspell(caster: &Entity, target: &mut Entity) -> bool {
    if target.casting_state.is_casting && target.casting_state.can_be_counterspelled {
        target.casting_state.is_casting = false;
        // Ability's resource was already deducted at cast start — leave it consumed
        // Ability goes on cooldown as if it was cast
        set_cooldown(target, target.casting_state.ability_being_cast, full_cooldown);
        emit_event(AbilityCountered { target_id, ability_id });
        return true;
    }
    false
}
```

### Timing Window

Counterspell can only be used during the target's cast time — the window between cast start and cast resolution. For abilities with:
- **Long cast time (2+ seconds)**: large counter window, easy to react to
- **Short cast time (0.5 seconds)**: small counter window, requires fast reaction
- **Instant cast (0 seconds)**: NO counter window, cannot be countered

The counterspell must HIT the target before `cast_end_tick`. If the counterspell's own travel time (if it's a projectile) means it arrives after the cast resolves, the counter fails.

### Counterable Classification

Not all abilities should be counterable. The compiler must tag abilities:
- `can_be_counterspelled: true` — standard abilities with cast times
- `can_be_counterspelled: false` — instant abilities, auto-attacks, passive procs, and specific "uncounterspellable" abilities

The `can_be_counterspelled` flag is part of the ability definition in SpellData.

### Reaction System (Optional)

In D&D, counterspell uses your REACTION — a limited resource (one per round). In a real-time engine, this could be:
- A separate ability with its own cooldown (simplest)
- A "reaction" resource: one reaction per N seconds, counterspell consumes it
- No special resource — just cooldown-gated

The simplest approach: counterspell is an ability with a cooldown. No special reaction system needed.

### Cast Bar Visibility

For counterplay to work, the enemy's cast bar must be visible:
- The casting entity's Arbiter includes casting state in downstream payloads
- Edge Nodes render the cast bar for enemies in view
- The cast bar shows which ability is being cast (so the counterspeller can decide if it's worth countering)

## Cross-Boundary Concerns

TODO: The caster (counterspeller) and target (casting enemy) may be on different Arbiters:

1. **Same Arbiter**: Counterspell checks the target's casting state locally. If casting → cancel. Simple.

2. **Target is a Ghost**: The counterspeller's Arbiter sees the target as a Ghost. Does the Ghost carry casting state? Currently GhostUpdate has position, velocity, movement_class — no casting state.
   - **Option A**: Add casting state to Ghost updates. Adds bandwidth but enables cross-boundary countering.
   - **Option B**: Counterspell only works on same-Arbiter targets. Simpler but limits range.
   - **Option C**: Counterspell relays to the target's Arbiter: "cancel if still casting." The relay might arrive after the cast resolves (latency).

3. **Latency concern**: If the counterspell relay arrives AFTER the cast resolved (ability already fired), the counter fails. The target already dealt damage. This creates a timing unfairness for cross-boundary countering. For PvE (boss on same Arbiter as players), this isn't an issue.

## Compiler Requirements

TODO: Designer specifies: targeted ability, must be used during target's cast time, cancels the ability (no resolution), resource still consumed by target, target ability goes on cooldown, counterspell has its own cooldown, some abilities marked uncounterable. Compiler produces:
- Counterspell ability definition
- Per-ability `can_be_counterspelled: bool` flag in SpellData
- CastingState tracking on entities (start tick, end tick, ability ID)
- Mid-cast cancellation hook
- Casting state in downstream payloads (for cast bar rendering)

The compiler adds casting state visibility and mid-cast cancellation as engine capabilities.

## Open Questions

- Can counterspell be counterspelled (counter the counter)?
- Does counterspell work on channeled abilities (cancel mid-channel)?
- If the countered ability was SK-83 empowered, is the empowerment consumed or preserved?
- Does counterspell consume the target's SK-42 charges (charge-based ability countered)?
- Can counterspell cancel SK-05 Global Strike's channel?
- Does the counterspell need to deal damage to cancel, or is it a pure cancel effect?
- Can the enemy fake a cast to bait the counterspell (start casting, cancel own cast)?
- Does SK-51 Unstoppable prevent counterspell (the cast can't be interrupted)?
- Can counterspell cancel SK-119 Counter Window boss attacks (counter the boss's counterable attack with counterspell instead of a counter ability)?
- Should counterspell have a success check (D&D: roll to counter higher-level spells) or be guaranteed?
