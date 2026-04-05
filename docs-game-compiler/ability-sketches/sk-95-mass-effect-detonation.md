# SK-95: Mass Effect Detonation

## Designer Intent

I apply persistent effects to multiple allies and enemies. When I activate my detonation trait, all
matching active instances of those effects that I own burst simultaneously across the battlefield:
healing primers burst-heal, offensive primers burst-damage and root, then the consumed primers are
removed.

## Primitive Composition

P-46 (Global Event Scheduler) → P-66 (Status Effect Filter Mutation) → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No direct target; the detonate cast is a global self activation
- One or more status IDs that this ability detonates
- Per-status consume payloads (heal burst, damage burst, root, etc.)

## Observable Behavior

1. Over time, the caster applies `Healing Pathogen` to allies and `Weighted Pustule` to enemies
2. When the caster presses the detonate ability, one coordinated global detonation tick is
   scheduled
3. At that execute tick, every Arbiter checks its OWN authoritative targets for matching status
   instances from THIS caster and consumes them atomically
4. On the immediately following simulation tick, each consumed `Healing Pathogen` instance resolves
   its authored burst heal
5. On the immediately following simulation tick, each consumed `Weighted Pustule` instance resolves
   its authored burst damage + root
6. Targets without matching status instances from this caster are unaffected
7. After detonation, the consumed primer statuses are gone
8. Visual: all qualifying targets burst in one coordinated battlefield-wide resolution window

## Engine Primitives Required

Mass Effect Detonation is now a canonical mesh-wide status-consumption pattern. It does not need a
source-side "caster effect registry."

### Canonical Authoring Shape

The detonate ability should lower to:

- one `global_event` block with:
  - `schedule_lead_ticks = 1`
  - `geometry = whole_mesh`
  - `target_class` and `filter` authored to include every entity type that may legally host the
    relevant primer statuses
- one `consume_status` effect per detonatable primer status, for example:
  - `consume_status(target = target, status_id = healing_pathogen, source_entity = caster, on_consume_effects = [burst_heal ...])`
  - `consume_status(target = target, status_id = weighted_pustule, source_entity = caster, on_consume_effects = [burst_damage ..., apply_cc root ...])`

This keeps the mechanic target-side authoritative:

1. the target owner already has the active status registry
2. each status instance already stores the original source/applier identity
3. exact-match source filtering happens where the status actually lives

### Why No Caster-Owned Registry Is Needed

The older sketch assumed the caster needed to track every active status instance across the mesh.
That is no longer the preferred model.

Instead:

1. the detonate cast schedules one coordinated `P-46` execute tick
2. every Arbiter evaluates its local authoritative targets at that tick
3. `consume_status` removes exact `(status_id, source_entity)` matches from the target's registry
4. if any match was consumed, the authored consume payload is queued for the NEXT tick in that same
   target context

This avoids stale source-side membership tracking when targets hand off between Arbiters.

## Cross-Boundary Concerns

The cross-boundary story is the ordinary `P-46` plus target-side status-ownership contract.

1. The caster's owner does NOT fan out bespoke "detonate target X" relays to every Arbiter
2. The detonate cast escalates once through `global_event`
3. At execute time, each Arbiter evaluates only its OWN authoritative targets
4. Handoffs before the execute tick are naturally handled because the status registry lives with the
   target's current owner
5. Source ownership still filters correctly because status instances preserve their original
   source/applier identity even after handoff

## Compiler Requirements

Designer specifies:

- the detonate ability activation
- which status IDs are detonatable by this ability
- the consume payload for each detonated status family
- the execute scope/filter for the global event

Compiler emits:

- one controller-escalated `global_event` for the detonate cast
- one exact-match `consume_status` mutation per detonatable status family
- status-consumption follow-up payloads in ordinary authored effect form
- no sketch-local status registry or one-off relay subsystem

Compiler validates:

1. every referenced `status_id` exists
2. duplicate `consume_status` entries against the same `(status_id, source_entity)` pair in one
   ability are rejected
3. the detonate ability's `global_event` target filter is compatible with the entity types expected
   to carry the referenced statuses
4. every consume payload is expressible as ordinary authored effects under the existing compiler
   surface

## Resolved Notes

- Detonation only affects statuses applied by THIS caster because `consume_status` matches both
  `status_id` and stored source identity
- Detonation is not selective in this sketch. Activating the trait consumes every authored primer
  family on every qualifying target
- The burst heal and burst damage/root follow ordinary healing, damage, anti-heal, CC-immunity,
  DR, kill-credit, and proc-attribution rules because they are just normal authored effects
- Because `consume_status` is a Stage 11 registry mutation, the primer removal is committed on the
  execute tick and the burst payload lands on the immediately following simulation tick
- If a target dies or loses the relevant status before the execute tick, nothing detonates on that
  target
- This sketch's map-wide profile is why `P-46` is part of the canonical primitive chain here; a
  local-radius variant could be authored differently, but this reference is explicitly whole-mesh
