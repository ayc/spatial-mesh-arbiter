# T1-03: Combat Modifier Pipeline & Proc Order

> **Status:** DRAFTING
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/01-rpg-mechanics.md`

## Problem Statement (Reframed)

The original gap was about "combat resolution ordering" — what happens when multiple events hit the same target in the same tick. But the real question is narrower and more important: **what is the guaranteed evaluation order for modifiers and procs within a single combat resolution?**

The spec defines `apply_combat_math` with 7 numbered steps, and the buff system uses flat-then-multiplicative evaluation. But several pieces are missing:

1. **Incoming damage modifiers** — Where do "take 20% more damage" (vulnerability) and "reduce damage by 15%" (damage reduction) apply in the pipeline? Before or after resistance? Before or after conditionals?
2. **Proc trigger points** — Thorns is defined (step 7), but where do on-hit procs, on-crit procs, on-block procs, on-kill procs fire?
3. **Modifier interaction with conditionals** — If the attacker has "50% bonus if target below 30% HP" and a previous hit in the same tick already dropped the target below 30%, does the conditional trigger?
4. **Multiple hits in the same tick** — Sequential application (each hit sees the result of previous hits) or snapshot (all hits see pre-tick state)?

## What's Already Specified

The spec defines two pipelines:

**Buff evaluation (stat compilation at evaluation time):**
- Flat additive modifiers summed first
- Multiplicative modifiers applied to the result
- Computed on-the-fly from immutable base + active `StatModifier` entries

**`apply_combat_math` (Phase 2 resolution, 7 steps):**
1. Evasion check
2. Distance falloff
3. Conditionals (attacker's "if target HP < X" type modifiers)
4. Block check
5. Resistance & penetration
6. HP application
7. Thorns reactive proc

## Proposed Resolution

### The Complete Modifier Pipeline

Expand the existing 7-step `apply_combat_math` into a complete pipeline that accounts for all modifier categories. The pipeline runs once per incoming hit — each hit resolves fully before the next one starts (sequential, not snapshot).

```
PHASE 2: apply_combat_math(victim, attacker_id, context)
│
├─ 1. EVASION CHECK
│     Compute effective evasion: base + flat defense mods + mult defense mods
│     Roll against effective evasion rating
│     If dodged → emit "DODGED", exit (no further processing)
│
├─ 2. DISTANCE FALLOFF
│     Apply calculate_falloff(distance) to base_damage
│     (See T1-02 for falloff formula)
│
├─ 3. ATTACKER CONDITIONALS (carried in CombatContext)
│     Evaluate against victim's CURRENT state (not snapshot)
│     e.g., "50% bonus if target HP < 30%" checks victim.hp NOW
│     This means prior hits in the same tick CAN trigger conditionals
│
├─ 4. BLOCK CHECK
│     Compute effective block chance: base + flat defense mods + mult defense mods
│     Roll against effective block chance
│     If blocked → apply block effectiveness multiplier (default 50% reduction)
│     On-block procs trigger here (pushed to internal_inbox, proc_depth + 1)
│
├─ 5. VICTIM INCOMING DAMAGE MODIFIERS
│     Evaluate all active modifiers on the victim that affect incoming damage:
│       a. Flat incoming damage adjustment (e.g., "take 10 less damage per hit")
│       b. Percentage vulnerability/reduction (e.g., "take 20% more fire damage")
│     Order: flat adjustments first, then percentage multipliers
│     Same flat-then-multiplicative convention as buff evaluation
│
├─ 6. RESISTANCE & PENETRATION
│     (Unchanged from current spec)
│     effective_resistance = base - flat_pen, then * (1 - pct_pen)
│     Clamp to [-100, 85]
│     Apply mitigation: damage * (1 - resistance/100) or amplification if negative
│
├─ 7. FINAL HP APPLICATION
│     victim.hp -= incoming_damage (truncated to i32 per T0-01 rounding rules)
│     If victim.hp <= 0 → mark is_dead, emit PlayerDied/MonsterDied HardEvent
│
├─ 8. ON-HIT PROCS
│     Evaluate attacker's on-hit effects (carried in CombatContext or on ActiveStatusEffects)
│     Only fires if damage was actually applied (not dodged, not fully absorbed)
│     e.g., "on hit: apply Burning for 5 seconds"
│     Status effect application is immediate on the victim
│     proc_depth carries forward from context
│
├─ 9. ON-CRIT PROCS (if context.is_critical_strike)
│     Evaluate attacker's on-crit effects
│     e.g., "on crit: 30% chance to apply Stun for 1 second"
│     Same rules as on-hit: status effect applied immediately, proc_depth carries
│
├─ 10. ON-KILL PROCS (if victim.is_dead)
│      Evaluate attacker's on-kill effects
│      e.g., "on kill: heal for 5% of max HP"
│      Heal is applied to attacker immediately (or via InternalPreparedHit if cross-boundary)
│
├─ 11. REACTIVE PROCS (victim-side)
│      Thorns: if victim has thorns_damage > 0
│              AND damage_origin == DirectCast
│              AND proc_depth == 0
│              → push counter-damage to internal_inbox with proc_depth + 1
│      On-block counter: if is_blocked AND victim has on-block proc
│              → same pattern (push to internal_inbox, proc_depth + 1)
│
└─ END
```

### Key Design Decisions

**Sequential, not snapshot.** Each hit resolves fully (including HP change and death check) before the next hit processes. This means:
- Hit 2 sees the HP left by Hit 1
- Conditionals ("if target below 30% HP") can trigger based on prior hits in the same tick
- If Hit 1 kills the target, Hit 2 still resolves (target is dead but damage is applied — important for on-kill procs and kill attribution in multi-attacker scenarios)

**Why sequential?** Snapshot evaluation (all hits see pre-tick state) would mean damage doesn't "count" until the next tick, creating a one-tick invulnerability window. It would also break conditionals — "if target below 30% HP" would never trigger from burst damage in the same tick. Sequential is simpler, more intuitive, and matches player expectations from ARPGs.

**Dead targets still receive hits.** If an entity dies from Hit 1, subsequent hits in the same tick still resolve against it. The damage is applied (HP goes further negative), procs fire, and kill attribution tracks all contributors. This prevents race conditions where "who gets the kill" depends on processing order. The `is_dead` flag prevents the dead entity from *acting* (no movement, no casting), but it can still be hit.

**Reactive procs are deferred.** Thorns, on-block counters, and similar reactive effects push to `internal_inbox` rather than resolving inline. This prevents recursive explosion within a single `apply_combat_math` call. They resolve on the next pass of the inbox drain (same tick, but after the current event finishes). `proc_depth` prevents infinite chains (see T1-06).

**Proc depth is per-chain, not per-tick.** `proc_depth` tracks how many reactive hops have occurred in a single cause-effect chain, not how many procs have fired this tick globally. Multiple independent chains can proc in the same tick without interfering.

### Where New Proc Types Plug In

The pipeline has explicit extension points:

| Trigger | Step | Condition | Examples |
|---------|------|-----------|----------|
| **On-hit** | 8 | Damage applied (not dodged) | Apply DoT, apply slow, lifesteal |
| **On-crit** | 9 | `is_critical_strike == true` | Bonus damage proc, stun, resource gain |
| **On-kill** | 10 | `victim.is_dead == true` | Heal on kill, soul harvest, XP bonus |
| **On-block** | 4/11 | Block check succeeded | Shield bash counter, thorns variant |
| **Reactive (thorns)** | 11 | `damage_origin == DirectCast && proc_depth == 0` | Reflect damage |

Adding a new proc type means: define the trigger condition, the effect, and which step it plugs into. The pipeline itself doesn't change.

### Tick-Level Event Ordering (Resolved by T0-01)

The original question about "what order are events processed in the same tick" is already answered by T0-01:
- Status effect ticks (`tick_status_effects`) run before inbox drain → DoTs/HoTs always resolve before incoming combat events
- Internal inbox drains sequentially → events process one at a time, each seeing the result of the previous
- External proposals drain in EntityID order (BTreeMap) after coalescing
- Within each event, the modifier pipeline above defines the exact resolution order

No additional ordering specification is needed beyond what T0-01 and this pipeline provide.

## Summary of Decisions

| Question | Decision |
|----------|----------|
| Modifier pipeline | 11-step expansion of `apply_combat_math` with explicit proc trigger points |
| Hit evaluation | Sequential (each hit sees results of prior hits, not snapshot) |
| Dead targets | Still receive hits (damage applied, procs fire, kill attribution tracks all contributors) |
| Reactive procs | Deferred to internal_inbox (same tick, next drain pass), proc_depth prevents recursion |
| Incoming damage modifiers | Step 5: flat adjustment first, then percentage (flat-then-mult convention) |
| Proc depth | Per-chain, not per-tick |
| Tick-level ordering | Resolved by T0-01 (BTreeMap iteration, phase ordering in tick loop) |

## Open Questions

- [ ] Should on-hit procs fire on blocked hits (reduced damage but not zero)?
- [ ] Should lifesteal be an on-hit proc (step 8) or a separate step after HP application (step 7.5)?
- [ ] Maximum number of on-hit/on-crit/on-kill procs per entity? (Cap to prevent proc spam from stacked items?)

## References

- `docs/3-gameplay-systems/01-rpg-mechanics.md` — Phase 1/Phase 2 pipeline, `apply_combat_math`, buff evaluation
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` — CombatContext, StatModifier, OffensiveCondition
- `docs/6-spec-drafts/_archived/01-determinism-strategy.md` — BTreeMap iteration order, WAL self-containment
