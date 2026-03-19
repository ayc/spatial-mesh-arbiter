# SK-119: Counter Window

## Designer Intent

During certain boss attack animations, the boss glows blue — signaling a COUNTER WINDOW. If a player hits the boss with a "counter" classified ability during this window, the attack is interrupted, the boss takes bonus damage, and the boss is briefly staggered. If no one counters, the boss completes its powerful attack. Timing the counter is a core skill check in raid encounters.

## Primitive Composition

P-65 (Vulnerability Window Broadcast) → P-40 (On-Cast Intercept)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Boss entity (broadcasts the counter window)
- Player entity (must use an ability that can counter a vulnerability window during the window)

## Observable Behavior

1. Boss begins a specific attack animation — blue glow appears (counter window opens)
2. Counter window lasts 1-2 seconds (tight timing)
3. If a player hits the boss with an ability that can counter a vulnerability window during the window:
   - Boss attack is INTERRUPTED (cancelled — doesn't deal damage)
   - Boss takes bonus damage from the counter hit
   - Boss enters a brief stagger (1.5 seconds — stunned + vulnerable)
   - Counter window closes
4. If NO counter lands during the window:
   - Boss completes the attack (potentially devastating damage/AoE)
   - Counter window closes
5. Only the FIRST counter that lands counts (no double-countering)
6. Visual: blue flash on boss during window, dramatic parry effect on successful counter

## Engine Primitives Required

### Entity Vulnerability State

The boss entity broadcasts a vulnerability-window-active state during specific attack animations:

```
struct CounterWindowState {
    is_vulnerability_window_active: bool,
    window_start_tick: u64,
    window_end_tick: u64,
    counter_bonus_damage: SimFixed,
    counter_stagger_ticks: u64,
    attack_to_cancel: AbilityId,  // Which boss attack to interrupt on counter
    countered_by: Option<EntityID>,  // First player to counter (one-shot)
}
```

The boss's Arbiter sets `is_vulnerability_window_active = true` at the start of specific attack animations and `false` at the end. This is driven by the boss's ability definitions and animation timing.

### Counter-Classified Abilities

Players have some abilities tagged to counter vulnerability windows:
```
struct AbilityDef {
    // ... existing fields
    can_counter_vulnerability_window: bool,  // This ability can counter during a vulnerability window
}
```

When an ability with `can_counter_vulnerability_window = true` hits an entity with `is_vulnerability_window_active = true`:
1. Check: is the target in a counter window? (`is_vulnerability_window_active && current_tick <= window_end_tick`)
2. Check: has the window already been countered? (`countered_by.is_none()`)
3. If both: COUNTER SUCCEEDS
   - Interrupt the boss's current attack (`attack_to_cancel`)
   - Apply bonus damage from the counter
   - Apply stagger (brief stun + vulnerability)
   - Set `countered_by = Some(player_entity_id)` (prevent double-counter)
4. If not: ability resolves normally (no counter bonus)

### Boss Attack Interruption

On successful counter, the boss's current attack is CANCELLED:
- The attack's damage/effects DO NOT apply
- The boss's ability goes on cooldown (or enters a recovery state)
- The boss enters a stagger state (similar to SK-117 Stagger Bar depletion but triggered by counter, not cumulative stagger damage)

The engine needs to support **mid-cast ability cancellation** on an entity — stopping an ability that's currently being resolved/animated. This is different from CC interrupting a channel (SK-64 Mosh Pit) — the boss isn't channeling, it's mid-cast of a specific attack.

### Timing Window as a Skill Check

The counter window is short (1-2 seconds). The tight timing creates a SKILL CHECK — players must:
1. Recognize the blue glow (visual cue)
2. React within the window (timing)
3. Use an ability that can counter a vulnerability window (correct ability choice)
4. Hit the boss (accuracy — counter abilities might be skillshots)

This is fundamentally a PvE mechanic designed to reward player skill and reaction time.

### Integration With Boss AI / Ability Scripting

The counter window is part of the boss's ABILITY DEFINITION — specific boss attacks open counter windows:
```
boss_ability: GroundSlam {
    damage: 5000,
    aoe_radius: 8,
    cast_time_ticks: 120,  // 2 seconds
    counter_window: Some(CounterWindow {
        start_at_tick_offset: 30,   // Window opens 0.5s into cast
        duration_ticks: 90,          // Window is open for 1.5s
        bonus_damage: 2000,
        stagger_ticks: 90,
    }),
}
```

The compiler defines counter windows as part of boss ability definitions in SpellData. The designer specifies which boss attacks are counterable, when the window opens/closes, and what happens on successful counter.

## Cross-Boundary Concerns

TODO: The boss is on one Arbiter. Players attacking the boss might be on the same Arbiter or relaying cross-boundary.

1. **Local player counters**: Player hits boss with counter ability on the same Arbiter. Counter check is local and immediate.
2. **Cross-boundary player counters**: Player on Arbiter B sends a counter attack that relays to the boss's Arbiter A. The relay arrives and the boss's Arbiter checks: is the counter window still open? Due to relay latency, the player might have acted within their local window but the relay arrives after the window closed on the boss's Arbiter.

This creates a LATENCY FAIRNESS issue: players closer (same Arbiter) have a slight advantage on counter timing vs cross-boundary players. For PvE content, the boss is likely on the same Arbiter as nearby players (they're all in the same spatial region). Cross-boundary countering should be rare.

## Compiler Requirements

TODO: Designer specifies: per-boss-ability counter window definition (timing, bonus, stagger), player abilities tagged as `can_counter_vulnerability_window: true`, counter check during damage resolution, one-shot per window (first counter wins), attack interruption on success. Compiler produces:
- CounterWindowState as boss entity component
- Per-boss-ability counter window timing in SpellData
- `can_counter_vulnerability_window: bool` flag on player ability definitions
- Damage resolution hook: if attacker's ability `can_counter_vulnerability_window` AND target `is_vulnerability_window_active` → counter resolution
- Attack interruption (cancel current boss ability)
- One-shot flag (first counter consumes the window)

The compiler adds counter windows to the boss ability definition format and counter classification to player ability definitions.

## Open Questions

- Can multiple players attempt to counter simultaneously? (First hit wins — but what if two hits arrive on the same tick?)
- Does the counter ability need to deal damage to trigger the counter, or just hit?
- Can counter windows appear on player entities in PvP?
- Does the counter bonus damage go through normal damage resolution (shields, mitigation)?
- Can the counter stagger be affected by SK-51 Unstoppable (boss has super armor — counter still works)?
- Does a successful counter contribute to the SK-117 Stagger Bar?
- Can counter windows be extended or shortened by abilities (slow the boss → longer window)?
- Does Kinematic Dilation affect counter window timing?
- Can the boss attack be "partially countered" (counter lands late in the window → reduced bonus)?
- Should the counter window timing account for network latency (grace period for cross-boundary players)?
