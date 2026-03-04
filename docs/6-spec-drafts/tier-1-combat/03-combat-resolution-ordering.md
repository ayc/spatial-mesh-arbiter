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
├─ 0. MODIFIER CLASSIFICATION GATE
│     Before the pipeline runs, active modifiers on the victim are sorted into
│     their classified pipeline positions. Each modifier carries a classification
│     that determines WHERE in the pipeline it evaluates — not IF, but WHEN.
│     See "Modifier Classifications" below.
│
├─ 1. IMMUNITY CHECK (Classification: Immunity)
│     If victim has any active Immunity modifier matching this damage type:
│       → short-circuit entire pipeline, emit "IMMUNE", exit
│     Examples: Invulnerability, Divine Shield, phase-shift
│     Immunity modifiers always evaluate first regardless of when they were applied.
│
├─ 2. EVASION CHECK
│     Compute effective evasion: base + flat defense mods + mult defense mods
│     Roll against effective evasion rating
│     If dodged → emit "DODGED", exit (no further processing)
│
├─ 3. ABSORPTION (Classification: Absorption)
│     If victim has active Absorption modifiers (shields, barriers):
│       → subtract damage from shield HP first
│       → if shield absorbs all damage, emit "ABSORBED", skip to step 10 (procs may still fire)
│       → if shield breaks, remainder continues through pipeline
│     Examples: Mana Shield (absorb up to X using resource), Damage Barrier (flat HP shield)
│
├─ 4. DISTANCE FALLOFF
│     Apply calculate_falloff(distance) to remaining base_damage
│     (See T1-02 for falloff formula)
│
├─ 5. ATTACKER CONDITIONALS (carried in CombatContext)
│     Evaluate against victim's CURRENT state (not snapshot)
│     e.g., "50% bonus if target HP < 30%" checks victim.hp NOW
│     This means prior hits in the same tick CAN trigger conditionals
│
├─ 6. BLOCK CHECK
│     Compute effective block chance: base + flat defense mods + mult defense mods
│     Roll against effective block chance
│     If blocked → apply block effectiveness multiplier (default 50% reduction)
│     On-block procs trigger here (pushed to internal_inbox, proc_depth + 1)
│
├─ 7. INCOMING DAMAGE MODIFIERS (Classifications: Amplification, Reduction)
│     Evaluate all active modifiers on the victim that affect incoming damage:
│       a. Flat incoming damage adjustment — Reduction class (e.g., "take 10 less per hit")
│       b. Percentage amplification — Amplification class (e.g., "take 20% more fire damage")
│       c. Percentage reduction — Reduction class (e.g., "reduce incoming damage by 15%")
│     Order: flat adjustments first, then percentage multipliers
│     Same flat-then-multiplicative convention as buff evaluation
│     Amplification and Reduction modifiers both evaluate here, in declaration order
│     within their flat/mult grouping.
│
├─ 8. RESISTANCE & PENETRATION
│     (Unchanged from current spec)
│     effective_resistance = base - flat_pen, then * (1 - pct_pen)
│     Clamp to [-100, 85]
│     Apply mitigation: damage * (1 - resistance/100) or amplification if negative
│
├─ 9. FINAL HP APPLICATION
│     victim.hp -= incoming_damage (truncated to i32 per T0-01 rounding rules)
│     Check Threshold modifiers BEFORE marking death (see below)
│     If victim.hp <= 0 AND no Threshold modifier prevents death:
│       → mark is_dead, emit PlayerDied/MonsterDied HardEvent
│
│     THRESHOLD CHECK (Classification: Threshold)
│     If victim has active Threshold modifier (e.g., "cannot die for 3 seconds",
│     "survive lethal hit with 1 HP once per 60 seconds"):
│       → clamp victim.hp to threshold minimum (e.g., 1)
│       → consume the modifier if it's single-use
│       → do NOT mark is_dead
│     Examples: Last Stand, Undying passive, Cheat Death
│
├─ 10. ON-HIT PROCS
│      Evaluate attacker's on-hit effects (carried in CombatContext or on ActiveStatusEffects)
│      Only fires if damage was actually applied (not immune, not dodged)
│      Fires even if fully absorbed (shield broke or not — the hit "landed")
│      e.g., "on hit: apply Burning for 5 seconds"
│      Status effect application is immediate on the victim
│      proc_depth carries forward from context
│
├─ 11. ON-CRIT PROCS (if context.is_critical_strike)
│      Evaluate attacker's on-crit effects
│      e.g., "on crit: 30% chance to apply Stun for 1 second"
│      Same rules as on-hit: status effect applied immediately, proc_depth carries
│
├─ 12. ON-KILL PROCS (if victim.is_dead)
│      Evaluate attacker's on-kill effects
│      e.g., "on kill: heal for 5% of max HP"
│      Heal is applied to attacker immediately (or via InternalPreparedHit if cross-boundary)
│      NOTE: does NOT fire if Threshold modifier prevented death
│
├─ 13. REACTIVE PROCS (victim-side)
│      Thorns: if victim has thorns_damage > 0
│              AND damage_origin == DirectCast
│              AND proc_depth == 0
│              → push counter-damage to internal_inbox with proc_depth + 1
│      On-block counter: if is_blocked AND victim has on-block proc
│              → same pattern (push to internal_inbox, proc_depth + 1)
│
└─ END
```

### Modifier Classifications

Each modifier on an entity carries a **classification** that determines its guaranteed evaluation position in the pipeline. The classification is defined on the modifier's data definition (in SpellData/affix data), not at runtime. Designers tag each modifier; the pipeline routes it.

| Classification | Pipeline Step | Behavior | Examples |
|---------------|--------------|----------|----------|
| **Immunity** | Step 1 | Short-circuits entire pipeline. Checked first, always. | Invulnerability, Divine Shield, Ice Block |
| **Absorption** | Step 3 | Subtracts damage from shield HP before other mitigation. Can fully absorb. | Mana Shield, Barrier, Energy Shield |
| **Amplification** | Step 7 | Increases incoming damage (percentage). Evaluated with other incoming modifiers. | Vulnerability curse, "take 20% more fire damage" |
| **Reduction** | Step 7 | Decreases incoming damage (flat or percentage). Evaluated with other incoming modifiers. | Damage reduction buff, armor active ability |
| **Threshold** | Step 9 | Overrides death. Clamps HP to minimum after damage application. | Last Stand, Cheat Death, "cannot die while channeling" |

**Why classify?** Without classification, a designer adding a "Mana Shield" modifier would need to know the exact pipeline step number and manually position it. With classification, they tag it as `Absorption` and the pipeline handles placement. This is the extension mechanism — new modifier types are added by defining new classifications with specified pipeline positions, not by rewriting the pipeline.

**Interaction rules:**
- **Immunity beats everything.** If active, nothing else in the pipeline runs.
- **Absorption runs before mitigation.** A 100-damage hit against a 60-HP shield + 50% resistance: shield absorbs 60, remaining 40 goes through resistance → 20 actual HP loss. (Not: 100 → 50 after resistance → shield absorbs 50.)
- **Threshold runs after HP application.** Damage is fully calculated and applied, THEN the threshold check prevents death. This means on-hit procs fire (the hit landed), but on-kill procs don't (the target didn't actually die).
- **Amplification and Reduction coexist at step 7.** Both evaluate in the same flat-then-mult pass. A target with both "+20% vulnerability" and "-15% reduction" gets: `damage * 1.20 * 0.85 = damage * 1.02`.

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
| **On-hit** | 10 | Damage applied (not immune, not dodged) | Apply DoT, apply slow, lifesteal |
| **On-crit** | 11 | `is_critical_strike == true` | Bonus damage proc, stun, resource gain |
| **On-kill** | 12 | `victim.is_dead == true` (not prevented by Threshold) | Heal on kill, soul harvest, XP bonus |
| **On-block** | 6/13 | Block check succeeded | Shield bash counter, thorns variant |
| **Reactive (thorns)** | 13 | `damage_origin == DirectCast && proc_depth == 0` | Reflect damage |

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
| Modifier pipeline | 13-step expansion of `apply_combat_math` with classified modifier positions and explicit proc trigger points |
| Modifier classification | 5 classes (Immunity, Absorption, Amplification, Reduction, Threshold) each with a guaranteed pipeline position |
| Hit evaluation | Sequential (each hit sees results of prior hits, not snapshot) |
| Dead targets | Still receive hits (damage applied, procs fire, kill attribution tracks all contributors) |
| Threshold modifiers | Override death after HP application. On-hit procs fire, on-kill procs don't. |
| Reactive procs | Deferred to internal_inbox (same tick, next drain pass), proc_depth prevents recursion |
| Incoming damage modifiers | Step 7: flat adjustment first, then percentage (flat-then-mult convention) |
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
