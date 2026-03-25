# SK-52: Combo Strike

## Designer Intent

I press Q three times in quick succession to perform a three-hit combo. Each press is a different attack: the first two are quick slashes dealing damage, the third is a heavy slash that deals damage AND heals me. If I don't press Q again within 2 seconds of the previous press, the combo resets to the first hit.

## Primitive Composition

P-42 (Stacking Counters w/ Decay)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Same ability key pressed repeatedly (Q, Q, Q)
- Combo window between presses (2 seconds)

## Observable Behavior

1. First Q press: quick slash dealing X damage to target
2. Within 2 seconds, second Q press: quick slash dealing X damage to target
3. Within 2 seconds, third Q press: heavy slash dealing 1.5X damage AND healing caster for Y HP
4. After the third press: combo resets to first hit. Full cooldown begins.
5. If 2 seconds pass between any press: combo resets to first hit. Short cooldown.
6. Each press can target a different enemy (not locked to the first target)
7. Visual: escalating slash animations, third hit has a pronounced wind-up and green heal effect

## Engine Primitives Required

### Combo State Machine

The ability maintains a per-entity combo state:

```
struct ComboState {
    current_step: u8,        // 0 = ready for first hit, 1 = ready for second, 2 = ready for third
    combo_window_expires: u64, // Tick at which the combo resets if not advanced
}
```

Each press of the ability:
1. Read `current_step`
2. Resolve the effect for that step (step 0: damage, step 1: damage, step 2: damage + heal)
3. Advance `current_step` to the next step
4. Set `combo_window_expires = current_tick + window_ticks`
5. If `current_step` wraps past the final step: reset to 0, apply full cooldown

If `combo_window_expires` passes without advancement: reset `current_step` to 0, apply short cooldown.

### Multi-Phase Ability (Different From SK-36)

SK-36 Shadow Step has two phases (blink out, blink back) determined by whether a status effect is active. Combo Strike has N phases (3 hits) determined by an incrementing counter with a timeout. The differences:
- SK-36: binary (phase 1 or phase 2), determined by presence of a buff
- SK-52: sequential (step 0 → 1 → 2 → reset), determined by a counter with decay
- Each step has different resolution logic (step 2 heals, others don't)
- The combo can be interrupted at any step by the timeout

### Validate Hook Branching

The `validate_intent` hook must read the combo state to determine which validation rules apply:
- Step 0: standard cooldown/range check
- Step 1: no cooldown check (mid-combo), range check, combo window check
- Step 2: no cooldown check, range check, combo window check

The stage-execution path must read the combo state to determine the effect:
- Step 0/1: damage only
- Step 2: damage + heal

## Cross-Boundary Concerns

TODO: Each combo press can target a different entity. If the first hit targets a local entity and the second targets a Ghost, the second hit's damage relays cross-boundary. The combo state lives on the caster's entity (SoftState), so it's always local to the caster's Arbiter. If the caster crosses a boundary mid-combo, the combo state transfers with the handoff.

## Compiler Requirements

TODO: Designer specifies: combo steps (3), per-step effects (step 0: X damage, step 1: X damage, step 2: 1.5X damage + Y heal), combo window (2s), full cooldown after complete combo, short cooldown on timeout reset. Compiler produces:
- Ability definition with combo state machine (step count, window duration)
- Per-step resolution logic (branching in stage execution based on `current_step`)
- Per-step validation rules (skip cooldown check mid-combo)
- Combo reset logic (timeout → reset, completion → reset + full cooldown)

The compiler needs to support **sequential multi-step abilities** as a first-class pattern.

## Open Questions

- Can on-hit procs (SK-09 Chain Lightning) trigger on each combo hit independently?
- Does the third hit's heal benefit from healing bonuses?
- Can the combo be interrupted by CC (stun resets combo? or pauses it?)
- Does SK-12 Spell Echo interact with combo — if step 1 echoes, does it produce another step 1, or advance to step 2?
- Can the combo window be affected by attack speed buffs (SK-20 Battle Cry)?
- Does each step consume a token from the per-entity token bucket, or is the entire combo one token?
- Can the third hit be used with SK-42 Withering Fire's auto-targeting, or must combos be manually targeted?
- If the caster is silenced (SK-26) between step 1 and step 2, does the combo reset?
- Can combo state be represented as a status effect (hidden buff with step counter) rather than a separate state machine?
