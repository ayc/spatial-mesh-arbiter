# SK-07: Ability Steal

## Designer Intent

My character steals the last ability used by a target enemy. The stolen ability replaces one of my
ability slots temporarily. I can cast it once using my own stats, then it reverts to my original
ability.

## Primitive Composition

P-40 (On-Cast Intercept) → P-31 (Identity/Loadout Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Cast on enemy and identify the last public ability they used.
2. That ability is copied into one of the caster's ability slots, temporarily replacing the normal
   slot.
3. The caster may cast the stolen ability once, using the caster's own stats and resources.
4. After that one use, or after the timeout expires, the original slot returns automatically.
5. The enemy is not affected and keeps their own ability.
6. Visual presentation may show the stolen ability on the caster.

## Engine Primitives Required

Ability Steal is now a canonical `borrow_ability_slot(source_selector = last_cast_ability)`
reference.

The recommended lowering is:

```yaml
type: borrow_ability_slot
target: caster
source_entity: target
source_selector: last_cast_ability
destination_slot_id: ...
duration_ticks: ...
usage_limit: 1
fallback_if_missing: fail
```

This keeps the mechanic inside the canonical `P-31` slot-override path:

- the target's last accepted public `ability_id` comes from the bounded cast-history register
- the caster receives a temporary slot override on one authored destination slot
- the borrowed slot reverts automatically after one successful use or ordinary timeout expiry
- the target's own loadout is untouched

## Cross-Boundary Concerns

Ability Steal follows the canonical cross-boundary loadout-projection contract.

1. If the target is remote/Ghosted, the target's current owner resolves `last_cast_ability` from
   its bounded public cast-history register.
2. That owner relays the resolved public `ability_id` as immutable slot-override payload data to
   the caster's owner.
3. The caster's owner installs the borrowed slot locally on the caster. Authority does not move to
   the target's Arbiter; only the exposed slot mapping changes.
4. If the caster hands off while the borrowed slot is active, the slot override and its revert
   record transfer with the caster as ordinary SoftState.
5. Later casts by the victim do not live-update the stolen slot. This reference snapshots the
   victim's last accepted public ability at steal time.

## Compiler Requirements

Designer specifies:

- hostile target filter and range
- destination slot to override
- timeout duration
- whether the effect fails or ignores when no last cast exists

Compiler emits:

- one hostile target admit
- one `borrow_ability_slot(target = caster, source_entity = target, source_selector = last_cast_ability, ...)`
- one revert record keyed by `duration_ticks` and `usage_limit = 1`

Compiler validates:

1. the destination slot exists on the stealer's loadout
2. `usage_limit = 1` for this one-cast steal reference
3. only public accepted ability IDs are borrowable from `last_cast_ability`; passive effects and
   hidden activation variants are not valid steal results
4. the mechanic is expressed through canonical `borrow_ability_slot`, not by mutating the target's
   loadout or inventing a second temporary loadout subsystem

## Resolved Interaction Notes

- If the enemy has not used a public ability yet, this reference fails cleanly with no slot change.
- The stolen ability uses the caster's own stats, cooldowns, capability flags, and resource pools,
  because `borrow_ability_slot` only changes the exposed slot mapping.
- If the stolen ability needs a resource pool the caster does not have, the later cast fails
  through ordinary affordability validation; the steal itself still succeeds.
- The stolen cast is the caster's cast, so it may trigger the caster's own on-cast/on-hit proc
  effects normally.
- If the stolen ability summons entities or projectiles, those spawned outputs are owned by the
  caster just like other casts made from the caster's loadout.
- This reference borrows the current live definition of the resolved public `ability_id`; it is not
  a replay of the victim's historical data-epoch version from the moment they cast it.
