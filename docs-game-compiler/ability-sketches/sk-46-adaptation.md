# SK-46: Adaptation

## Designer Intent

I activate this ability and a 4-second window begins. At the end of the window, I am healed for 100% of all damage I took during those 4 seconds. The more damage I take, the bigger the heal. If I take no damage, I get no heal.

## Primitive Composition

P-36 (On-Damage-Received Hook) → P-42 (Stacking Counters w/ Decay) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (self-only)

## Observable Behavior

1. Activate — a 4-second tracking window begins
2. During the window: every point of damage I take is accumulated in a counter
3. All damage types count: direct hits, DoTs, reflected damage, AoE, everything
4. Damage is still applied normally — I take full damage during the window (not reduced)
5. After 4 seconds: I am healed for 100% of the accumulated damage total
6. The heal is a single burst heal at the end, not a heal-over-time
7. If I die during the 4-second window: the heal never fires (I'm dead)
8. If I take 0 damage during the window: I am healed for 0 (ability was wasted)
9. Visual: glowing adaptive carapace effect, damage counter visible to the player, burst heal on completion

## Engine Primitives Required

Adaptation is now a canonical status-owned damage-accumulator window.

The recommended lowering is:

1. apply one positive `adaptation_window` status to the caster for 240 ticks
2. that status authors:
   - `damage_accumulator = { bind_total_as = adaptation_damage, include_absorbed_damage = false }`
   - `on_expire_effects = [heal(target = caster, amount = 0, scaling = { binding = adaptation_damage, coefficient = 1.0 })]`
   - optional presentation-only status visuals for the player-facing counter

This keeps the mechanic entirely inside the canonical `damage_accumulator` surface:

- damage is still taken normally during the window
- the accumulator records the final post-mitigation HP lost while the status is active
- expiry resolves one burst heal from the bound accumulated value
- cleanse/remove does not fire the expiry heal because the binding is only exposed to
  `on_expire_effects`, not arbitrary remove hooks

## Cross-Boundary Concerns

Adaptation is local to the defended entity's owner.

1. All qualifying damage, including cross-boundary prepared-hit relays, is resolved on the target's
   current authoritative owner. The accumulator therefore records damage locally with no extra relay
   path.
2. If the entity hands off during the 4-second window, the active status and its accumulated total
   transfer as ordinary SoftState.
3. The expiry heal is just one local reactive heal on the entity's current owner. No special
   cross-boundary routing is required beyond the ordinary handoff/stage ordering already defined for
   status lifecycle effects.

## Compiler Requirements

Designer specifies:

- tracking duration
- whether shield-absorbed damage counts
- heal multiplier on expiry
- whether the status is cleansable/purgeable

Compiler emits:

- one positive tracking status
- one canonical `damage_accumulator` block bound to `adaptation_damage`
- one expiry heal that reads the bound accumulated value

Compiler validates:

1. the ability is self-only
2. `duration_ticks > 0`
3. the heal is authored through `on_expire_effects`, not through an on-remove hook
4. the accumulator reads resolved HP loss, with shield-absorbed damage included only when the
   designer explicitly flips `include_absorbed_damage = true`

## Resolved Interaction Notes

- This reference tracks post-mitigation HP actually lost. Shield-absorbed damage is excluded because
  `include_absorbed_damage = false`.
- Damage redirected away before it ever reaches the adapting entity does not count. Damage redirected
  onto the adapting entity does count because it becomes resolved HP loss there.
- Enemies may purge the beneficial status if the design leaves it cleansable; purge removes the
  window and prevents the expiry heal because the heal is not authored on remove.
- The expiry heal is an ordinary heal event. It may participate in ordinary heal-side consumers such
  as healing mirrors or modifiers, but it is not a crit-capable damage event.
- Kinematic Dilation does not change the authored tick window. The status lasts 240 simulation ticks
  just like other timed statuses.
- Entering Burrow during the window simply means the accumulator stops growing while invulnerability
  is active. The Adaptation timer itself keeps running in this reference because Burrow does not
  pause status timers.
- This reference is non-stacking. Reapplying it refreshes/replaces the active window instead of
  keeping multiple accumulators alive.
