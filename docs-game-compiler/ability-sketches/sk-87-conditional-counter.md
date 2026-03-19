# SK-87: Conditional Counter

## Designer Intent

I enter a defensive stance for 1 second. If any enemy hits me during that window, the stance activates — I become Protected (invulnerable) and deal AoE damage around me. If nobody attacks me during the window, nothing happens and the ability goes on full cooldown. High risk, high reward — I'm gambling that the enemy will attack.

## Primitive Composition

P-36 (On-Damage-Received Hook) → P-17 (Conditional Thresholds) → P-09 (Shape Overlap Query)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only defensive activation)

## Observable Behavior

1. Activate — enter counter stance for 1 second
2. During the stance: caster can't move or act (locked in place, vulnerable)
3. If hit by ANY damage during the stance: counter TRIGGERS
4. On trigger: caster becomes Protected for 0.75 seconds, AoE damage to all nearby enemies
5. If NOT hit during the 1-second window: stance expires, nothing happens, full cooldown
6. The trigger check is binary — any damage source triggers it (melee, ranged, DoT tick, AoE)
7. Visual: defensive pose during stance, flash of energy on trigger, underwhelming fizzle on expiry

## Engine Primitives Required

### Window-Gated Conditional Activation

This is the first ability with a **"wait for external event, then activate" pattern** within a time window:

```
status_effect: CounterStance {
    window_expires_at_tick: u64,
    triggered: bool,
    aoe_damage: SimFixed,
    aoe_radius: SimFixed,
    protected_duration_ticks: u64,
    combat_context: CombatContext,
}
```

The stance effect registers a **damage-received hook**:
- Each tick: check if the entity took damage
- If yes AND `!triggered`: set `triggered = true`, apply Protected status, perform AoE damage
- If window expires AND `!triggered`: remove stance, nothing happens

This is similar to SK-27 Sleep's break-on-damage check, but REVERSED — Sleep breaks (bad) on damage, Counter activates (good) on damage. The trigger check is the same engine primitive: "did this entity receive damage this tick?"

### Damage-Gated Activation vs Break-On-Damage

Both SK-27 Sleep and SK-87 Counter Stance use the same hook: "on damage received during a status effect window." The difference is the response:
- Sleep: remove the effect (negative outcome for the target)
- Counter: activate a payoff (positive outcome for the target)

The engine primitive is: **status effect with a damage-received trigger that fires a callback**. The callback can do anything — remove the effect, spawn AoE, grant invulnerability, etc.

### Stance Vulnerability

During the stance, the caster is locked in place and can't act — but is NOT invulnerable. They MUST be hit for the counter to work. This creates a window where:
- The caster is a sitting duck (can be CC'd, which might prevent the counter from resolving)
- Enemies can choose NOT to attack (denying the counter)
- The caster is gambling on being attacked

If the caster is stunned during the stance, does the stance persist (stun + stance coexist) or does the stun cancel the stance?

## Cross-Boundary Concerns

TODO: The stance is local to the caster's Arbiter. Damage arriving via relay (cross-boundary attack) triggers the counter locally. The AoE damage from the counter is also local + Ghost relays. No special cross-boundary handling needed.

One timing concern: if damage arrives from a relay just as the stance window expires (same tick), the ordering matters. Does damage resolution happen before or after effect expiry checks?

## Compiler Requirements

TODO: Designer specifies: stance duration (1s), caster locked + vulnerable during stance, trigger (any damage received), on-trigger (Protected + AoE damage), on-expiry-without-trigger (nothing, full cooldown), cannot be cancelled voluntarily. Compiler produces:
- CounterStance status effect with damage-received hook
- On-trigger callback: apply Protected + snapshot AoE damage
- On-expiry callback: remove stance, nothing else
- Caster lockdown during stance (can't move, can't cast, can't attack)

The compiler needs to support **damage-received callbacks on status effects** — a general mechanism for "when this entity takes damage while this effect is active, execute this action."

## Open Questions

- Does the counter trigger on ANY damage (including DoT ticks from SK-02 Poison)?
- Does the counter trigger on damage absorbed by shields (SK-17)?
- If the caster is stunned (SK-24) during the stance, does the stance persist or cancel?
- Can the counter trigger multiple times if hit by multiple sources in the same tick? (Should be once only)
- Does the AoE damage from the counter trigger on-hit procs (SK-09 Chain Lightning)?
- Can SK-51 Unstoppable be used during the stance (remain mobile while waiting for the counter)?
- Does the counter trigger on self-damage (SK-17 Sacrifice Shield self-cost)?
- Is the Protected duration from the counter subject to Tenacity/DR? (It's a buff, not CC)
- Can enemies bait the counter with a low-damage ability and then burst after the Protected expires?
