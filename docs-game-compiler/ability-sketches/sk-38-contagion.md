# SK-38: Contagion

## Designer Intent

I throw a cursed dagger at an enemy. It deals initial damage and applies a spreading debuff. After 2 seconds, the debuff jumps to all enemies within range of the infected target. Each newly infected enemy can spread it again after another 2 seconds. The spread continues until no new targets are in range or a maximum generation is reached.

## Primitive Composition

P-44 (Pulse Timer) → P-09 (Shape Overlap Query) → P-35 (On-Hit Hook)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target enemy entity (must be in range)

## Observable Behavior

1. Dagger hits target — initial damage + Contagion debuff applied
2. Contagion debuff deals damage over time while active (4 seconds per application)
3. After 2 seconds: the debuff autonomously spreads to all enemies within spread radius of the carrier
4. Newly infected enemies get their own Contagion debuff (fresh 4-second duration)
5. After 2 seconds on each new carrier: it spreads again to nearby uninfected enemies
6. An entity can only be infected once per cast (no re-infection from the same contagion chain)
7. Maximum 4 generations of spreading (initial target = gen 0, their spread = gen 1, etc.)
8. Visual: sickly green glow on infected targets, visible spread wave when it jumps

## Engine Primitives Required

Contagion is now a canonical status-owned spread pattern built from one hostile status application
plus one `SpreadBlock`.

The recommended lowering is:

1. The initial dagger hit resolves its ordinary damage and applies one hostile status
   `contagion_status`.
2. `contagion_status` carries:
   - the authored DoT payload for the 4-second infection window
   - `spread = {`
     `delay_ticks = 120,`
     `query_radius = ... ,`
     `max_generations = 4,`
     `max_targets_per_spread = ... ,`
     `filter = enemy_alive,`
     `apply_status_id = contagion_status,`
     `dedup_scope = entity_once_per_chain,`
     `allow_spread_from_corpse = false`
     `}`
3. Each admitted infection instance stores compiler-owned `chain_id`, current `generation`, and
   next `spread_at_tick`.
4. When `spread_at_tick` arrives and `generation < max_generations`, the carrier's current owner
   performs the local spread query and applies child `contagion_status` instances as generation
   `+1`.

This keeps the mechanic inside existing canonical surfaces:

- the spreading logic lives in status metadata, not a bespoke autonomous actor
- per-chain dedup is the built-in `dedup_scope = entity_once_per_chain` path
- generation bounds are the ordinary `max_generations` cap
- child infections inherit the original caster / credit owner instead of inventing a new local
  source identity

## Cross-Boundary Concerns

Contagion follows the ordinary carrier-owner status relay model.

1. The spread query always runs on the current authoritative owner of the infected carrier.
2. Locally owned targets receive child status applications directly; Ghost/remote targets are
   relayed to their authoritative owner with the same `chain_id` and incremented `generation`.
3. The receiving owner inserts the child status locally, preserves the original caster / credit
   owner, and schedules that child instance's own later spread from the new carrier.
4. If an infected carrier hands off before its `spread_at_tick`, the status transfers with its
   `chain_id`, `generation`, and next spread schedule as ordinary SoftState, so the next owner runs
   the spread exactly once.
5. Cross-Arbiter back-spread does not reopen prior targets because the visited-set semantics are
   keyed by `chain_id`, not by local-owner identity.

## Compiler Requirements

Designer specifies:

- initial hit damage / delivery
- infection DoT magnitude and duration
- spread delay
- spread radius
- maximum generation count
- bounded `max_targets_per_spread`
- hostile filter for valid spread targets

Compiler emits:

- one initial hostile status application
- one `StatusEffectDefinition` carrying the authored DoT plus canonical `spread`
- compiler-owned `chain_id` / `generation` / `spread_at_tick` metadata on each status instance
- target-owner relay payloads that preserve original caster / credit owner across child infections

Compiler validates:

1. `delay_ticks > 0`
2. `query_radius > 0`
3. `max_generations > 0`
4. `max_targets_per_spread > 0` and remains bounded for the intended density envelope
5. `apply_status_id` resolves to a valid status definition
6. self-propagating spread remains finite through the authored generation cap

## Resolved Interaction Notes

- Spread infections keep the original caster / credit owner for kill credit and downstream source
  identity. The carrier only hosts the query execution.
- `SK-15 Purify` removes the current contagion instance, but `entity_once_per_chain` still prevents
  the same chain from re-infecting that entity later.
- Because this reference leaves `allow_spread_from_corpse = false`, dead carriers do not emit a
  final spread from corpse position.
- Separate casts mint separate `chain_id` values, so different contagion casts may infect the same
  entity independently.
- Hostility / visibility / line-of-sight behavior comes from the authored spread filter and
  ordinary target admission. This reference uses an ordinary hostile spread query and does not add a
  bespoke through-wall exception.
