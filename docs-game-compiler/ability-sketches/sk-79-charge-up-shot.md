# SK-79: Charge-Up Shot

## Designer Intent

I hold down the ability button to charge my bow. The longer I hold, the more damage and range the shot has. When I release, the arrow fires. Minimum charge fires a weak short-range shot. Maximum charge (after 2 seconds) fires a powerful long-range shot. I can move slowly while charging.

## Primitive Composition

P-43 (Charge-Up State) → P-32 (Actor Spawning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Button HOLD duration (continuous input, not discrete press)
- Release timing (player-controlled)
- Aim direction (requested aim direction at release time)

## Observable Behavior

1. Press and hold ability button — charging begins
2. Charge bar fills over 2 seconds
3. While charging: caster moves at 50% speed, cannot use other abilities
4. At any point: release to fire at current charge level
5. Minimum charge (instant release): low damage, short range
6. Maximum charge (2 seconds): high damage, long range
7. Charge level scales linearly: damage and range interpolate between min and max
8. If held beyond max charge: stays at max, doesn't overcharge
9. Visual: bow draw animation intensifies, glowing effect increases with charge

## Engine Primitives Required

### Hold-to-Charge Input Model

All existing abilities use discrete input: press button → ability fires. Charge-Up introduces **continuous input with a duration component**:

```
enum AbilityInputMode {
    Instant,              // Press → fire (all existing abilities)
    HoldRelease {         // Hold → charge → release → fire (SK-79)
        max_charge_ticks: u64,
        min_charge_ticks: u64,   // Minimum hold before firing
    },
}
```

The Edge Node must:
1. Detect button-down event → start charging
2. Track hold duration in ticks
3. Detect button-up event → send "fire with charge_ticks=N" proposal
4. The proposal carries the charge duration, not just "cast ability"

The Arbiter validates:
1. Was the entity in a valid charging state? (Not CC'd, not dead)
2. Is the charge_ticks value within bounds?
3. Calculate damage/range from charge_ticks using the ability's scaling formula

### Charge State on Entity

While charging, the entity is in a special state:

```
struct ChargeState {
    ability_id: AbilityId,
    charge_start_tick: u64,
    max_charge_ticks: u64,
}
```

This state:
- Restricts movement to 50% speed (movement modifier while charging)
- Blocks other ability usage (can't cast while charging)
- Can be interrupted by CC (stun cancels the charge, nothing fires)
- Is visible to enemies (the entity is "winding up")

### Scaling Formula

The ability's damage and range are functions of charge duration:
```
let charge_pct = clamp(charge_ticks / max_charge_ticks, 0.0, 1.0);
let damage = min_damage + (max_damage - min_damage) * charge_pct;
let range = min_range + (max_range - min_range) * charge_pct;
```

This must be deterministic (fixed-point) and the formula must be compiled into the ability definition.

## Cross-Boundary Concerns

TODO: Minimal cross-boundary concerns. The charge state is local to the caster's Arbiter. The fire event (on release) produces a standard projectile. The charge duration is determined client-side (Edge Node) and sent in the proposal — the Arbiter validates it.

The only concern: if the caster crosses a boundary mid-charge, the charge state must transfer with the handoff. The new Arbiter continues the charge from the transferred state.

## Compiler Requirements

TODO: Designer specifies: input mode (hold-release), max charge time (2s), min charge time (0s or 0.25s), damage scaling (min → max over charge), range scaling (min → max over charge), movement speed while charging (50%), blocks other abilities while charging, interruptible by CC. Compiler produces:
- Ability definition with `InputMode::HoldRelease`
- Charge state definition (start_tick, max_ticks)
- Scaling formula (charge_pct → damage, range)
- Movement speed modifier during charge
- CC interrupt hook (cancel charge on stun/silence)

The compiler needs to support a new input model alongside Instant, which affects the Edge Node's input handling and the Arbiter's proposal validation.

## Open Questions

- Can the charge be canceled voluntarily without firing (press escape)?
- Does the charge persist through SK-51 Unstoppable (you become unstoppable while charging)?
- If CC'd mid-charge, is the cooldown fully consumed or partially refunded?
- Can SK-12 Spell Echo trigger on a charged shot — does the echo fire at the same charge level?
- Does the charge bar progress account for Kinematic Dilation (slower charging in dilated zones)?
- Can the entity auto-attack while charging (some games allow this)?
- Is the charge visible to enemies (telegraphing the incoming shot)?
- How does the Edge Node predict the charge state for client-side rendering?
- Does the charged projectile gain any special properties beyond damage/range (e.g., pierce at max charge)?
