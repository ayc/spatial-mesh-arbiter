# SK-45: Essence Collection

## Designer Intent

When enemy minions and monsters die near me, they leave essence behind. I can walk over the dropped
orbs to collect that essence into a personal reserve, then activate the trait to consume everything
I have stored and convert it into a self heal-over-time.

## Primitive Composition

P-47 (Spatial Corpse Registry) → P-32 (Actor Spawning) → P-14 (Continuous Proximity Monitor) →
P-42 (Stacking Counters w/ Decay)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Passive component: no input; nearby qualifying deaths are harvested automatically
- Active component: self-cast consume/heal activation

## Observable Behavior

1. While the passive is active, qualifying nearby enemy deaths are converted into visible essence
   orbs at the corpse location.
2. In this reference, each qualifying corpse yields one orb and each orb grants one essence on
   pickup.
3. Orbs are owner-scoped to the harvesting hero: only that hero can collect them.
4. Walking within pickup radius collects the orb immediately and adds one point to the hero's
   bounded `essence_pool`.
5. Orbs persist for 8 seconds if not collected, then despawn.
6. The essence reserve is bounded (for example, `0..50`) and does not regenerate on its own.
7. Activating the trait consumes all currently stored essence and applies a 5-second self
   heal-over-time whose total healing scales linearly with the consumed amount.
8. In this reference, stored essence is cleared by terminal death.
9. Visual: green orbs on the ground, a pull/absorb effect on pickup, and a green self-heal glow
   during the consume window.

## Engine Primitives Required

The clean canonical model is collector-owned harvesting, not a bespoke "broadcast nearby death to
all listeners" subsystem.

1. Qualifying enemy archetypes emit ordinary local `P-47` corpse records on terminal death.
2. The hero's passive periodically runs `consume_corpse(selection = nearest_to_caster, filter =
   enemy_dead, consume = true)` against the CURRENT Arbiter's corpse registry.
3. Each claimed corpse spawns one owner-scoped essence-orb actor at the corpse's death position.
4. The orb uses ordinary `spawn_actor.interaction` with `trigger_filter = self` and
   `resolution_mode = collector_only`.
5. On pickup, the orb adds one count to a bounded count-only `essence_pool`.
6. The active consume ability uses `modify_charge_pool(action = consume, consume_policy = all)` and
   scales a follow-up self HoT from the compiler-emitted consumed-count binding.

This keeps the mechanic inside existing corpse, spawned-actor, pickup, and bounded-pool surfaces.
The reference does not require a second "pickup resource" subsystem distinct from canonical
count-only pools.

## Cross-Boundary Concerns

Corpse harvesting and orb pickup use different authority rules:

1. Corpse claims are local-only under the current canonical `P-47` profile. The passive harvest
   scan only sees corpses in the CURRENT Arbiter's corpse registry.
2. If multiple eligible collectors overlap the same corpse set on one Arbiter, `consume_corpse`
   resolves contention atomically and deterministically. First successful claim wins; one corpse
   cannot feed multiple collectors.
3. Once an orb is spawned, it is an ordinary runtime actor. If the owner is present only as a
   Ghost, the orb owner still detects the overlap and relays the pickup mutation to the owner's
   authoritative Arbiter through the normal `spawn_actor.interaction` path.
4. A corpse on a neighboring Arbiter does not create an orb until the collector is authoritative on
   that Arbiter and the corpse record is still present there. The current canonical profile does not
   relay corpse queries across Arbiter boundaries.
5. Orbs themselves use ordinary spawned-actor ownership and handoff rules if topology changes while
   they are alive.

## Compiler Requirements

Designer specifies:

- passive corpse-harvest radius
- orb pickup radius
- orb lifetime
- `essence_pool` capacity
- consume ability duration and healing-per-essence coefficient
- which enemy archetypes participate in the essence economy for this ruleset

Compiler emits:

- one count-only `charge_pool` runtime state for `essence_pool`
- one passive harvest chain that periodically claims nearby `enemy_dead` corpses and spawns one
  owner-scoped orb per successful claim
- one orb archetype using `spawn_actor.interaction` with `trigger_filter = self`,
  `resolution_mode = collector_only`, and one `modify_charge_pool(action = add, count = 1)` pickup
  payload
- one self-cast consume ability guarded by `charge_count(essence_pool) >= 1`
- one `modify_charge_pool(action = consume, consume_policy = all)` effect plus one follow-up self
  HoT whose total healing scales from the emitted consumed-count binding

Compiler validates:

1. harvest radius, pickup radius, orb lifetime, and HoT duration are all positive
2. the referenced `essence_pool` runtime state exists and is a count-only `charge_pool`
3. `consume_policy = all` is only used on a compatible bounded pool
4. the orb interaction uses `trigger_filter = self`, so only the owning hero may collect it
5. corpse harvesting stays within canonical dead/corpse filters and the CURRENT Arbiter corpse
   registry

## Resolved Interaction Notes

- The reference version uses one essence per qualifying corpse. If a game wants elite enemies to
  yield more, it should author multiple orb spawns or specialized higher-yield variants in data
  rather than inventing a new pickup contract.
- Orbs are visible to all players in this reference but are not targetable, do not block pathing,
  and do not collide with projectiles.
- Because pickup is ordinary overlap-driven interaction, forced movement can pull the owner through
  an orb and collect it.
- The consume activation is instant. The healing-over-time it applies is ordinary healing and can be
  reduced by anti-heal effects.
- Kinematic Dilation does not special-case orb lifetime or pickup checks. All timers remain normal
  tick-based durations.
- Orbs and stored essence are soft state. Arbiter crash/recovery does not guarantee persistence.
