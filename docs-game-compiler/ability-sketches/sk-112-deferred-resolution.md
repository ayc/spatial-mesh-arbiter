# SK-112: Deferred Resolution

## Designer Intent

I buff an ally with a false promise. For 8 seconds, they appear to take no damage and receive no healing — their HP bar doesn't move. In reality, all damage and healing is secretly accumulated in a hidden ledger. When the buff expires, the NET result is applied: if more healing than damage occurred, they're fine. If more damage than healing, they take the difference and might die.

## Primitive Composition

P-22 (Deferred Ledger)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity

## Observable Behavior

1. Cast on ally — False Promise buff applied for 8 seconds
2. For the duration: ally's HP bar DOES NOT CHANGE regardless of damage/healing
3. Ally appears immortal (no visible HP loss) — but they're NOT invulnerable (damage is accumulating)
4. All healing also accumulates (not visible on HP bar)
5. On expiry: calculate NET = total_healing - total_damage
6. If NET >= 0: ally's HP is adjusted upward (effective healing received)
7. If NET < 0: ally's HP drops by |NET| (potentially killing them instantly)
8. If the ally would have died during the buff (accumulated damage > max HP + accumulated healing): they die on expiry
9. Visual: golden shield effect during buff, dramatic HP bar resolution on expiry (jumps up or drops)

## Engine Primitives Required

Deferred Resolution is now a canonical positive status carrying `deferred_ledger`.

The recommended lowering is:

1. apply one positive ally buff with:
   - `deferred_ledger = {`
     `freeze_observer_hp = true,`
     `remove_policy = resolve_immediately`
     `}`
   - authored duration and ordinary buff metadata
2. let the runtime intercept all HP damage/healing that would otherwise reach the target while the
   buff is active
3. let the ledger accumulate damage and healing separately, then cash out one net HP mutation when
   the status expires or is removed early

This keeps the mechanic entirely inside the canonical combat-state surface:

- the visible HP freeze is the authored `freeze_observer_hp = true`, not a bespoke client trick
- the hidden ledger is a status-owned accumulator, not a second shadow HP pool
- expiry/removal release is one committed HP mutation without re-running mitigation or anti-heal
- early removal/cancel uses the same canonical `remove_policy = resolve_immediately` path rather
  than inventing a separate "cleanse false promise" rule

## Cross-Boundary Concerns

Deferred Resolution is target-owner authoritative.

1. The positive status lives on the ally's current owner, and that owner intercepts all incoming HP
   damage/healing that would otherwise modify the ally.
2. Remote damage relays and remote heals still resolve through the ordinary target-owner path. The
   source does not need a second protocol to know the result was deferred.
3. If the buffed ally hands off, the status and its current damage/healing ledger transfer as
   ordinary SoftState to the new owner.
4. Because observer HP freezing is canonical status metadata, downstream UI remains frozen without a
   bespoke cross-service deception path.

## Compiler Requirements

Designer specifies:

- buff duration
- whether observer HP is frozen
- whether early removal resolves or discards the current ledger

Compiler emits:

- one positive status carrying canonical `deferred_ledger`
- runtime state for accumulated damage and accumulated healing
- one release-time net HP mutation when the status expires or is removed

Compiler validates:

1. the mechanic uses canonical `deferred_ledger`, not a bespoke HP shadow-copy system
2. `remove_policy` is explicit if the design wants anything other than the canonical immediate
   cash-out
3. the visible HP freeze comes from `freeze_observer_hp`, not from suppressing unrelated entity
   replication

## Resolved Interaction Notes

- Shield-absorbed damage does not enter the ledger, because `P-18` / `P-19` resolve before HP
  damage would reach the deferred ledger.
- Anti-heal reduces accumulated healing normally, because healing modifiers are applied when each
  healing sub-event is recorded, not at final release.
- If the status is removed early and `remove_policy = resolve_immediately`, the current net is
  applied immediately as one committed HP mutation.
- The release mutation can still interact with other active terminal-survival policies on the
  target. `hp_floor` checks first, then `death_prevention`, against that one released net result.
- `P-24` bypass-marked kills such as a bypass-prevention execute skip the ledger entirely.
- Stasis pauses the buff timer through the canonical suspension contract, so the ledger persists
  until the status timer resumes and ends or the buff is removed another way.
