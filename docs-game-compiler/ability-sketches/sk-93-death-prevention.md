# SK-93: Death Prevention

## Designer Intent

I place a protective buff on an ally. If that ally would die within the next 3 seconds, instead of dying they are healed to full HP. The buff is consumed on activation. If the ally doesn't take lethal damage within 3 seconds, the buff expires unused.

## Primitive Composition

P-39 (On-Death Hook) → P-23 (Floor Clamping) → P-15 (Value Modification)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (must be in range)

## Observable Behavior

1. Cast on ally — they receive the "Divine Palm" buff for 3 seconds
2. If the ally's HP would reach 0 during the buff: death is PREVENTED
3. The ally is healed to 100% of their max HP instantly
4. The buff is consumed (one-time use)
5. If the buff expires without triggering: nothing happens, cooldown was spent
6. The prevention is absolute — no damage amount can overcome it (even 50,000 damage)
7. Visual: golden palm icon on the ally, dramatic full-heal burst if triggered

## Engine Primitives Required

Death Prevention is now a canonical status-owned `death_prevention` reference.

The recommended lowering is:

1. apply one positive protection status to the ally for 180 ticks
2. author on that status:
   - `death_prevention = {`
     `restore_hp_ratio = 1.0,`
     `consume_on_trigger = true,`
     `bypass_anti_heal = true`
     `}`
3. let ordinary status expiry remove the protection with no payoff if no lethal event arrives in
   the window

This keeps the mechanic inside existing surfaces:

- lethal interception is the canonical `death_prevention` block
- full restore is just `restore_hp_ratio = 1.0`
- anti-heal bypass is already an authored flag on the same block
- no bespoke death-hook API is needed

## Cross-Boundary Concerns

Death Prevention is target-owner authoritative after admission.

1. If the caster and ally are on different Arbiters, the positive status is admitted through the
   ordinary ally-target relay path.
2. Later lethal checks happen only on the protected ally's current owner, after damage and any
   active `hp_floor` effects have already resolved there.
3. If `death_prevention` triggers, the same owner rewrites HP locally and consumes the status before
   terminal death is declared, so no `PlayerDied` or Meta respawn path opens.
4. If the protected ally hands off while the buff is active, the status simply transfers with them
   as ordinary SoftState.

## Compiler Requirements

Designer specifies:

- allied target
- buff duration
- restored HP ratio
- whether the protection is consumed on trigger
- whether the restore bypasses anti-heal

Compiler emits:

- one positive status definition with canonical `death_prevention`
- one ordinary ally-target application effect for that status

Compiler validates:

1. `restore_hp_ratio` is in `(0, 1]`
2. the mechanic is authored through canonical `death_prevention`, not through a bespoke death
   callback or a hidden respawn path
3. if the designer wants anti-heal to matter, they must explicitly set `bypass_anti_heal = false`

## Resolved Interaction Notes

- `hp_floor` resolves before `death_prevention`, so HP-floor effects like `SK-73` prevent this
  status from triggering if they already keep the entity alive.
- Overkill damage still triggers the protection if the entity remains lethal after ordinary
  mitigation and floor checks.
- This reference uses `bypass_anti_heal = true`, so the restore is not countered by `SK-92`.
- If enemies purge the protection before lethal damage arrives, nothing special happens; the later
  lethal event follows the ordinary death path.
