# SK-42: Withering Fire

## Designer Intent

I have 5 charges of a rapid-fire arrow attack. Each press fires one arrow at the nearest enemy hero (auto-targeted). Charges recharge independently — one charge every 8 seconds. I can dump all 5 rapidly for burst damage, then wait for them to recharge.

## Primitive Composition

P-42 (Stacking Counters w/ Decay) → P-11 (N-Nearest Neighbor)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target required (auto-targets nearest enemy hero within range)

## Observable Behavior

1. Press ability — one arrow fires at the nearest enemy hero within range
2. Arrow is instant (hitscan or very fast projectile — no meaningful travel time)
3. Arrow deals X damage to the target
4. One charge is consumed (5 max charges)
5. Can be pressed rapidly — fire all 5 in quick succession (no cooldown between charges, just a minimum interval like 0.15s)
6. Charges recharge independently: one charge every 8 seconds
7. Charge recharge timer starts when a charge is consumed, not when all charges are spent
8. If no enemy hero is in range: ability fails / fires at nearest non-hero enemy
9. Visual: rapid arrow shots, charge counter UI element

## Engine Primitives Required

Withering Fire is now a canonical count-only `charge_pool` plus nearest-neighbor auto-target helper.

The recommended lowering is:

1. one `RuntimeStateDefinition(kind = charge_pool)` with:
   - `capacity = 5`
   - `recharge_mode = independent`
   - `recharge_interval_ticks = 480`
   - `min_use_interval_ticks = 9`
2. one cast-time guard requiring at least one available charge in that pool
3. one nearest-neighbor helper query in TargetResolution:
   - primary query: nearest enemy hero within range
   - optional fallback query: nearest non-hero enemy within range
4. one ordinary hostile single-target damage payload against the selected target
5. one `modify_charge_pool(state_id = withering_fire_charges, action = consume)` emitted only if
   the cast commits successfully

This means the mechanic does NOT need a separate "charge cost type" outside the existing runtime-
state surface. Self-recharging charges are already the count-only form of `charge_pool`, and the
minimum use interval is already part of `ChargePoolStateDef`.

The auto-targeting portion is a bounded deterministic `P-11` query. The helper query sorts by
`(distance, entity_id)`, so ties are stable across replay.

## Cross-Boundary Concerns

Withering Fire follows the ordinary target-selection / target-owner authority split.

1. The caster's current owner runs the nearest-neighbor query using local entities plus Ghost data.
2. If the selected target is remote/Ghost, the cast still commits normally; the current owner emits
   the ordinary hostile payload toward the selected target's authoritative owner.
3. Because this sketch is authored as an instant / effectively hitscan shot, there is no later
   in-flight retarget. The selected target snapshot at commit time is the one used.
4. Rapid dumping of charges does not create a new transport pattern. It is just repeated ordinary
   casts, so each committed shot still consumes a normal ingress token and may still relay cross-
   boundary once if the chosen target is remote.
5. Ghost staleness is handled the same way it is for other nearest-target helpers: the local owner
   selects from the best current local-or-Ghost view, and the authoritative target owner still
   resolves defense on the real target state once the shot arrives.

## Compiler Requirements

Designer specifies:

- charge capacity
- recharge interval
- minimum use interval
- hostile auto-target priority (hero first, optional non-hero fallback)
- range
- per-shot damage payload

Compiler emits:

- one count-only `charge_pool` runtime state definition
- one cast-time availability guard against that pool
- one bounded nearest-neighbor helper query (plus optional fallback query)
- one ordinary single-target shot payload
- one post-commit `modify_charge_pool(..., action = consume)` mutation

Compiler validates:

1. `capacity > 0`
2. `recharge_mode = independent` when this sketch wants per-charge refill timers
3. `recharge_interval_ticks > 0`
4. `min_use_interval_ticks >= 0`
5. the auto-target helper remains bounded to one selected target per cast with deterministic
   `(distance, entity_id)` ordering

## Resolved Interaction Notes

- Charges live in ordinary per-entity runtime state, so they survive handoff exactly like other
  runtime states. Terminal death / respawn resets them through the game's normal respawn-state
  initialization path rather than through Withering Fire-specific logic.
- Recharge timers continue during ordinary CC. Only canonical timer-pause states such as `stasis`
  pause them.
- Each committed shot is a separate ordinary cast, so crit rolls, on-hit hooks, and proc windows
  are evaluated per shot.
- Because the shot is effectively instant in this reference, there is no late retarget after commit.
- The minimum use interval is ability-local rate limiting. It does not automatically scale from
  attack speed unless the game explicitly authors that coupling elsewhere.
