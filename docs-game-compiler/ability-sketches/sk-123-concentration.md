# SK-123: Concentration

## Designer Intent

Some of my most powerful spells require CONCENTRATION to maintain. While concentrating, I can move, attack, and use non-concentration abilities freely. But I can only concentrate on ONE spell at a time — casting a second concentration spell ends the first. And taking damage risks breaking my concentration — each hit triggers a check, and if I fail, the spell ends prematurely.

## Primitive Composition

P-55 (Concentration Intercept) → P-36 (On-Damage-Received Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Concentration ability (cast normally, then maintained)
- Damage events on the caster (trigger concentration checks)

## Observable Behavior

1. Cast a concentration spell (e.g., a persistent buff zone, a summoned creature, an ongoing debuff on an enemy)
2. The spell takes effect normally and PERSISTS as long as concentration is maintained
3. While concentrating: caster can move, auto-attack, and use non-concentration abilities freely
4. Casting ANOTHER concentration spell: the first one ENDS immediately (mutual exclusion)
5. Taking damage: CONCENTRATION CHECK — roll against a threshold
   - Pass: concentration maintained, spell persists
   - Fail: concentration broken, spell ends immediately
6. The check difficulty scales with damage taken (higher damage = harder to maintain)
7. Concentration indicator visible on the caster (which spell they're concentrating on)
8. Voluntarily ending concentration: caster can choose to stop concentrating at any time
9. Visual: subtle glow indicating active concentration, flash on concentration check, fizzle on break

## Engine Primitives Required

Concentration is now a canonical `requires_concentration = true` plus `concentration` policy
reference.

The recommended lowering is:

1. on the maintained spell, author:
   - `requires_concentration = true`
   - optional `concentration = {`
     `check_formula = standard_half_damage_floor_10,`
     `allow_manual_cancel = true,`
     `replace_existing = true,`
     `max_duration_ticks = ...`
     `}`
2. let the runtime install one concentration instance on the caster after the initial spell
   resolution succeeds
3. let any persistent outputs created by that spell be owned by that concentration instance
4. let the caster keep moving and casting non-concentration abilities normally while the maintained
   outputs persist

This keeps the mechanic entirely inside the canonical concentration surface:

- concentration is not a second channel system
- the caster has exactly one concentration slot
- replacing concentration tears down the previous instance-owned persistent outputs
- damage checks use the canonical deterministic formula unless the policy explicitly overrides it

## Cross-Boundary Concerns

Concentration is caster-owner authoritative.

1. The caster's current owner holds the active concentration slot and runs the damage-triggered
   `P-55` checks on each committed damage event to the caster.
2. Persistent statuses, zones, spawned actors, or other outputs owned by that concentration
   instance may live on other entities or Arbiters, but they are tagged to the same concentration
   instance.
3. On break, replacement, manual cancel, owner removal, or max-duration expiry, Stage 11 teardown
   removes all concentration-owned outputs through the canonical maintained-output cleanup path.
4. No sketch-local per-output relay logic is needed; concentration teardown already owns those
   outputs by cast instance.

## Compiler Requirements

Designer specifies:

- whether the ability requires concentration
- optional concentration policy overrides
- whether a maximum duration exists
- whether manual cancel is allowed
- whether replacing an existing concentration is allowed

Compiler emits:

- `requires_concentration = true`
- optional `concentration` policy metadata
- concentration-owned persistent outputs tagged to that cast instance
- canonical damage-triggered concentration checks on the caster owner

Compiler validates:

1. `concentration` is only present when `requires_concentration = true`
2. `channel` and `requires_concentration` are never both authored on the same ability
3. `max_duration_ticks > 0` when authored

## Resolved Interaction Notes

- Concentration is distinct from channeling: the caster may move and cast non-concentration
  abilities freely once the initial cast resolves.
- Shield-absorbed or fully blocked hits do not trigger a concentration check, because the canonical
  check runs on committed damage events to the owner.
- Burrow/invulnerability indirectly protect concentration by preventing committed damage from
  landing while they are active.
- Stasis pauses concentration timers and also prevents incoming committed damage, so the maintained
  effect simply remains suspended until normal time resumes.
- Mute does not break concentration by itself. Concentration is a maintained cast-instance contract,
  not a passive effect gated by `PASSIVES_ACTIVE`.
