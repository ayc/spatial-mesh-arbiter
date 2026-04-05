# Architecture Decision Log

> Reverse-chronological. Records the "why" behind choices that aren't self-evident from specs or code.
> This file is now the working decision index. Durable decisions should be promoted into
> `../adr/compiler/` or `../adr/engine/` once they are stable enough to stand alone. Not all
> historical entries are backfilled yet.

## Promoted ADRs

- [ADR-0001: Bounded Projectile Carry Roster](../adr/compiler/ADR-0001-bounded-projectile-carry-roster.md)
- [ADR-0002: Shield Absorb to Resource to Offense Loop](../adr/compiler/ADR-0002-shield-absorb-resource-offense-loop.md)
- [ADR-0003: Category-Scoped Cleanse](../adr/compiler/ADR-0003-category-scoped-cleanse.md)
- [ADR-0004: Late-Bound Actor Transit](../adr/compiler/ADR-0004-late-bound-actor-transit.md)
- [ADR-0005: Combo-Field Replacement via Explicit Context and Ordinary Sequencing](../adr/compiler/ADR-0005-combo-field-replacement-sequencing.md)
- [ADR-0006: Control-Projection Teardown Callbacks](../adr/compiler/ADR-0006-control-projection-teardown-callbacks.md)
- [ADR-0007: Target-Side Status Consumption for Mass Detonation](../adr/compiler/ADR-0007-target-side-status-consumption-for-mass-detonation.md)

---

## 2026-04 — Rolling snowball multi-carry uses a bounded projectile-local roster, not containers or a widening of `P-06`

Promoted to [ADR-0001](../adr/compiler/ADR-0001-bounded-projectile-carry-roster.md).
Projectile multi-carry is now a bounded projectile-local roster; `P-06` remains entity-to-entity
only.

## 2026-04 — Energy-shield offense loops use per-absorb shield callbacks plus ordinary resources, not bespoke shield-owned state

Promoted to [ADR-0002](../adr/compiler/ADR-0002-shield-absorb-resource-offense-loop.md).
Shield absorb -> resource mutation -> live offense scaling is now a canonical compositional path,
not a bespoke Energy subsystem.

## 2026-04 — Devour-style removal uses `P-58 off_world_stored` containment, not bespoke entity serialization

**Context:** Closing `SK-54 Entity Consumption` exposed that the original sketch still framed the
mechanic as "remove the entity from existence, serialize it somewhere, then restore it later."
That made the mechanic sound like a special lifecycle or persistence feature even though the
canonical compiler/docs layer already has a bounded devour-style containment path.

**Decision:** Treat devour mechanics as ordinary `container_profile` + `enter_container` /
`exit_container` authoring with `occupant_storage_mode = off_world_stored`. The swallowed target is
carried as container-owned preserved state, exits through ordinary eject logic, and uses
`eject_on_removed` for emergency release if the carrier dies.

**Alternatives:** Keep a bespoke "serialize entity / deserialize entity" mechanic; treat devour as
hard dormancy plus manual restore; or model it as pseudo-death plus later revive.

**Rationale:** The missing piece was not a new entity-lifecycle subsystem. `off_world_stored`
already expresses exactly the required gameplay boundaries: removed from the spatial world, no
queries/payloads while stored, carried through handoff with the container owner, and restored only
through ordinary exit/eject rules. Reusing that contract keeps devour aligned with bunker and
transport containment instead of inventing a parallel removal model.

## 2026-04 — Unstoppable-style CC strip uses category-scoped `cleanse`, not broad negative purge

Promoted to [ADR-0003](../adr/compiler/ADR-0003-category-scoped-cleanse.md).
Unstoppable-style activation now strips active CC through category-scoped cleanse rather than broad
negative-status purge.

## 2026-04 — Moving transport shells use late-bound `start_actor_transit`, not spawn-local vehicle phases

Promoted to [ADR-0004](../adr/compiler/ADR-0004-late-bound-actor-transit.md).
Late-launch transport motion is now modeled through one narrow transit effect rather than spawn
phases or a vehicle subsystem.

## 2026-04 — Multi-spawn projectile salvos use placement-authored heading vectors, not implicit aim or facing rotation

**Context:** Closing `SK-62 Boomerang` exposed a thin missing piece in the otherwise-mature
projectile surface. `spawn_actor.placement` could already expand one anchor into multiple derived
spawn points, and `projectile.return_policy` already covered the outbound/return lifecycle, but the
docs still lacked a canonical way to say "these no-target spawned projectiles launch in these fixed
radial directions" without relying on player aim or inferred facing rotation.

**Decision:** Extend `SpawnPlacementBlock` so each `SpawnOffsetDef` may optionally carry an explicit
world-space heading vector. When present on projectile spawns, that normalized heading becomes the
initial outbound launch direction for that derived spawn only. The spawn point and the launch
heading stay as separate explicit data.

**Alternatives:** Infer heading from placement offsets; rotate a fixed pattern from current facing;
force all radial salvos to use player aim/cursor; or add a separate projectile-launch-pattern
subsystem.

**Rationale:** The missing piece was a deterministic initial heading override, not a new projectile
actor model. Keeping it inside `placement` preserves the existing ability-local spawn metadata
shape, supports no-target salvos like `SK-62`, and avoids non-explicit rotation/facing inference.

## 2026-04 — `link` may bind two resolved non-caster endpoints through `source_entity`

**Context:** Closing `SK-111 Soulbind` exposed that the canonical `link` surface already modeled
the right runtime behavior (`event_clone`, anti-recursion, symmetric cleanup), but the schema still
assumed the binding source endpoint was always the current caster.

**Decision:** Extend `link` with optional `source_entity`, defaulting to `caster`. The compiler may
now emit one symmetric binding between any two resolved entity refs, including two non-caster
targets, while still using the same canonical `P-34` binding record and `event_clone` behavior.

**Alternatives:** Treat Soulbind as a bespoke replay subsystem; add a second target-to-target link
effect distinct from `link`; or keep non-caster endpoint binding as undocumented compiler magic.

**Rationale:** The runtime already wants a `(source_entity_id, target_entity_id)` binding pair.
Making the source endpoint explicit keeps the linkage model compositional, closes Soulbind cleanly,
and avoids a special one-off "enemy pair mirror" mechanic outside the normal link/event-clone
contract.

## 2026-04 — Combo-field replacement uses explicit field context plus ordinary effect sequencing

Promoted to [ADR-0005](../adr/compiler/ADR-0005-combo-field-replacement-sequencing.md).
Combo-field replacement now relies on explicit callback context plus ordinary authored sequencing
instead of a bespoke field-transform primitive.

## 2026-04 — Remote-controlled shell detonation is callback-driven `control_projection`, not bespoke bomb logic

Promoted to [ADR-0006](../adr/compiler/ADR-0006-control-projection-teardown-callbacks.md).
Remote-controlled shell detonation is now a bounded callback-driven extension on
`control_projection`, not a separate bomb subsystem.

## 2026-04 — `SK-95` detonates via target-side status consumption, not a source-side effect registry

Promoted to [ADR-0007](../adr/compiler/ADR-0007-target-side-status-consumption-for-mass-detonation.md).
Mass detonation is target-side authoritative through exact-match status consumption, not a
source-side effect registry.

## 2026-04 — `SK-89 Respawn Anchor` is a narrow revocable rebirth route, not a generic respawn-policy system

**Context:** After `SK-96` was reframed as a pre-terminal `ghost_phase`, the only remaining
blocked sketch was `SK-89 Respawn Anchor`. The mechanic needed post-terminal respawn rerouting, but
the user clarified two key constraints: the egg remains destructible after death during the
5-second rebirth window, and successful respawn should consume the egg because the player has
"hatched."

**Decision:** Add one narrow canonical path instead of a generic respawn-policy framework:
`spawn_actor.respawn_anchor` on the compiler side, `PlayerDied.respawn_override =
RespawnAnchor { ... }` plus `HardEvent::RespawnOverrideRevoked` on the HardEvent side, and
`MetaCommand::SpawnEntity.respawn_context = RespawnAnchor { anchor_entity_id }` on the Meta →
Mesh side. Meta stores both the base respawn schedule and the shorter anchor schedule. If the egg
is destroyed before respawn commit, the override is revoked and Meta falls back to the base
schedule measured from the original death time. On successful anchor-respawn, the target Arbiter
validates the anchor, consumes it atomically, and materializes the player at the anchor position in
ordinary spawn state.

**Alternatives:** Lock the rebirth in at death time; consume the egg immediately on death; make the
egg invulnerable once the owner dies; or build a broad free-form respawn-policy system covering
arbitrary location / HP / cooldown / state-reset overrides.

**Rationale:** The user explicitly wanted enemy counterplay during the 5-second rebirth window, so
death-time finalization was wrong. The minimal revocable route keeps Meta relatively dumb, keeps
the final race-free validation on the target Arbiter, closes `SK-89`, and avoids widening the
project into a generic "custom respawn framework" before there is evidence that broader policy
replacement is needed.

## 2026-04 — `SK-96 Death Ghost` is a pre-terminal ghost phase, not a post-terminal active shell

**Context:** `SK-96` was originally written as "death is already committed, Meta respawn timing is
already running, but the entity stays in-world and can still cast heals for 8 seconds." That
pattern conflicted directly with the current lifecycle contract and was one half of the last
remaining `CG-13` blocker.

**Decision:** Reframe `SK-96` as an ordinary non-terminal `P-25` phase named `ghost_phase`. On
lethal HP, the entity transitions into that phase instead of terminal death. Kill credit and
`PlayerDied` are delayed until phase expiry. While active, the phase forces immobility, denies all
incoming targeting/AoE/pathing collision, clears existing status effects, disables attacks/items
and passives, and exposes only a heal/support whitelist. On expiry, Stage 10 commits terminal
death and emits `PlayerDied` with a bounded `respawn_delay_credit_ticks` so Meta subtracts the
ghost linger time from the resolved base respawn delay.

**Alternatives:** Keep the original "dead but still acting" design; delay the ghost as pure visual
only with no casting; treat the 8-second ghost as post-terminal and expand the engine to support
active shells after `PlayerDied`.

**Rationale:** The pre-terminal phase model fits the existing lifecycle contract cleanly, avoids
inventing a paradoxical "dead but still active" entity state, preserves deterministic Stage 10
ownership, and still captures the intended gameplay. It also narrows the remaining open lifecycle
gap to `SK-89`'s post-terminal respawn-location override instead of keeping `SK-96` blocked on a
much larger engine/Meta expansion.

## 2026-04 — Single-actor spawned loadout/control projection stays ability-local on `spawn_actor`

**Context:** The remaining `CG-09` sketches split into two classes. `Entity Clone` and
`Remote Control Summon` both needed a spawned actor to temporarily receive a runtime loadout
snapshot and/or a controller's input stream, plus a bounded rule for what happens to the owner's
body when that projected actor expires or is removed. `Spirit Split` is harder because it needs a
dynamic multi-member control/reform group.

**Decision:** Add `spawn_actor.loadout_projection` and `spawn_actor.control_projection` as
ability-local spawn metadata in `AbilityIREntry.ParamData`. They snapshot one runtime loadout
source at spawn commit and install one single-actor control/body-return overlay using the existing
Stage 1 routing contract. They do NOT attempt to encode multi-member split/reform groups.

**Alternatives:** Bake clone/control policy into `EntityDefinition`; keep clone-shell and
remote-controlled bomb behavior sketch-local; try to force both single-actor projection and
multi-member split forms through one overloaded control-group surface immediately.

**Rationale:** The missing surface for `SK-67` and `SK-81` was local to the spawning ability, not
to the archetype. Keeping it on `spawn_actor` lets the same shell archetype be reused with or
without runtime loadout snapshots, routed input, body suspension, or restore-on-expire policy.
Separating this from the still-open multi-member group problem keeps the contract bounded and
auditable.

---

## 2026-04 — Multi-member split forms reuse `P-30` and stay ability-local

**Context:** `SK-61 Spirit Split` was the last remaining `CG-09` holdout after single-actor clone
and bomb projection were solved. The engine already had a bounded cross-boundary `P-30`
coordinator model and a `max_multiplex_group_size` of 4 in `docs-core/`, so the missing piece was
not a new engine primitive; it was compiler surface for grouping multiple spawned members, rotating
the active body, and reforming the stored owner.

**Decision:** Add `split_form` as ability-level metadata referencing prior `spawn_actor`
`output_binding`s, plus `cycle_split_form` as the bounded swap-command helper. The contract stores
and suspends the original owner body, routes direct input to exactly one active spawned member at a
time through existing `P-30` rules, optionally drives inactive members with a bounded follow-active
loop, and restores or kills the stored owner according to explicit authored end policies.

**Alternatives:** Extend `control_projection` to overloaded multi-member semantics; invent a new
engine primitive for split bodies; keep spirit-form rotation and reform behavior sketch-local.

**Rationale:** The group is still just a bounded `OneToMany + AdapterRouted` routing problem plus
explicit restore policy. Keeping it ability-local preserves archetype reuse, keeps the cross-boundary
story aligned with the existing `P-30` coordinator model, and avoids embedding Spirit Split specific
logic into `EntityDefinition` or the engine core.

---

## 2026-04 — `CG-12` closes by extending existing `P-56` / `P-58` contracts rather than adding new primitives

**Context:** After portal anchors, container profiles, and local instance forking were documented,
two edge cases remained: `Entity Consumption` needed a target carried completely out of the spatial
world, and `Pocket Arena` needed a remote target admitted into the caster's local private instance.

**Decision:** Extend `P-58` with `occupant_storage_mode = off_world_stored` for devour-style carried
occupants, and extend `P-56` with a one-time controller-coordinated remote-admission step before a
single-host instance starts. Live containers and live instances still remain single-owner /
single-host once active.

**Alternatives:** Leave both sketches permanently deferred; invent new bespoke primitives for
off-world carrying and cross-Arbiter arena extraction; overload suspension or general handoff with
special sketch-local semantics.

**Rationale:** Both mechanics were still topology/lifecycle variants of primitives the engine
already had. Extending the existing contracts preserved single authority, kept the live runtime
objects bounded and local after admission, and avoided growing the primitive catalog for what are
really specialized `P-56` / `P-58` policies.

---

## 2026-04 — `CG-13` splits into supported local corpse/downed flows vs unsupported post-terminal lifecycle overrides

**Context:** The remaining corpse/death sketches were mixing two different problems. Some only
needed a canonical compiler contract for corpse-targeted revive, corpse consumption, corpse-snapshot
loadout projection, and downed/rally lifecycle. Others (`Respawn Anchor`, `Death Ghost`) required
behavior after terminal death that touches Meta respawn timing and engine death semantics more
deeply.

**Decision:** Treat local corpse/downed flows as supported in the current compiler/core profile, and
explicitly treat two post-terminal patterns as outside the current profile:
1. an entity that is terminally dead for HardEvent/Meta timing yet still remains actively castable
   in-world
2. ability-authored override of Meta respawn timer/location after terminal death

**Alternatives:** Keep all corpse/death sketches grouped as one broad open compiler gap; force
sketch-local behavior for revive/corpse economy/possession/downed rally; implicitly assume the core
lifecycle already supported post-terminal active ghosts or respawn overrides.

**Rationale:** `docs-core/01-2-entity-lifecycle-contract.md` already supports intermediate
non-terminal phases through `P-25`, and the compiler can safely surface local corpse records through
`P-47`. The remaining blocked cases are qualitatively different because they cross the engine/Meta
death boundary rather than just needing better compiler authoring.

---

## 2026-04 — Multi-point spawned-actor placement stays ability-local and explicit

**Context:** Closing `SK-32 Minefield` exposed a hidden gap in the compiler surface. `spawn_actor`
already had `count`, but it did not yet have a canonical way to expand one anchor position into a
deterministic set of multiple spawn points for formations like mine patterns or summon circles.

**Decision:** Add `spawn_actor.placement` as ability-local metadata in `AbilityIREntry.ParamData`.
The surface is explicit ordered `(x, y)` offsets relative to the resolved anchor position; it does
not infer rotation from facing, and it does not inject runtime randomness.

**Alternatives:** Keep multi-point placement sketch-local; infer ring/line layouts procedurally;
bake formation data into `EntityDefinition`.

**Rationale:** The missing surface was placement authoring, not a new engine primitive. Keeping
placement offsets ability-local allows different abilities to spawn the same archetype with
different formations while preserving deterministic replay and avoiding archetype bloat.

---

## 2026-04 — Spawned-actor autonomy, proximity interaction, coverage, and live limits stay ability-local

**Context:** The remaining `CG-09` sketches (`Summon Swarm`, `Minefield`, `Build Zone`,
`Placed Potion`, plus the still-open split/clone/remote-control cases) all needed more behavior
than bare `P-32` spawning, but not all spawned actors of one archetype should necessarily share the
same follow AI, pickup payload, pylon-network tag, or per-owner live cap.

**Decision:** Keep `spawn_actor.autonomy`, `spawn_actor.interaction`, `spawn_actor.coverage`, and
`spawn_actor.instance_limit` as ability-local spawn metadata in `AbilityIREntry.ParamData` rather
than static `EntityDefinition` fields. The entity archetype still owns HP, movement, abilities,
targetability, and presentation, while the spawning ability supplies the bounded runtime behavior
profile for that particular spawned instance.

**Alternatives:** Bake summon/pickup/coverage behavior into every entity archetype; invent new
special actor classes for minions, mines, potions, pylons, and turrets; keep these behaviors
sketch-local.

**Rationale:** The repeated gap was not missing engine primitives. It was missing one bounded
compiler surface for actor-local behavior overlays. Keeping the behavior local to `spawn_actor`
allows the same archetype to be reused by different abilities with different trigger payloads,
network IDs, or live-count limits without turning `EntityDefinition` into a bloated catch-all.

---

## 2026-04 — Mesh-wide abilities schedule once through `P-46`; target owners resolve defense locally

**Context:** `Global Strike` still lacked a canonical compiler contract even after channels and
interrupts were resolved. The engine already had `P-46 (Global Event Scheduler)` and the
controller-to-Arbiter `ExecuteGlobalEvent` envelope, but the compiler docs did not say how an
authored ability opts into that path or when offense context versus target admission is frozen.

**Decision:** Add `global_event` as the canonical ability-level schedule policy for controller-
escalated execution. The caster's authoritative Arbiter bakes offense-side context once at schedule
time and asks the Mesh Controller to fan the event out for a coordinated future tick. At execute
time, each target owner re-runs the authored geometry/filter against its CURRENT local entities and
resolves the root `effects` list locally for admitted targets.

**Alternatives:** Keep mesh-wide abilities sketch-local; special-case `Global Strike`; snapshot the
entire target list at schedule time; let the origin owner directly compute outcomes for remote
targets from stale global state.

**Rationale:** The missing piece was scheduling policy, not new combat math. Baking offense once
preserves determinism and keeps the controller payload bounded. Re-running target admission and
defense locally at execute time preserves single authority and answers the schedule-time versus
execute-time membership question cleanly.

---

## 2026-04 — Containment stays local to existing `P-58` / `P-56` limits; portal networks are spawn-local metadata

**Context:** `Bunker`, `Portal Pair`, `Nydus Network`, `Mobile Transport`, `Entity Consumption`,
and `Pocket Arena` all reused the same remaining `CG-12` gap family, but they did not need the
same scope of engine support. The compiler lacked one canonical surface for container entry/exit,
portal anchor registration, and bounded instance forking.

**Decision:** Treat container rules as static entity/archetype capacity/cast policy plus dynamic
`P-58` entry/exit mutations; treat portal anchors as ordinary spawned actors with ability-local
`portal_anchor` metadata; and keep `fork_instance` local-only under the current `docs-core` `P-56`
contract. This means local bunkers, portal pairs, owner-scoped portal networks, and same-Arbiter
transport/arena cases are canonical now, while full off-world carried-entity lifecycle and remote
target extraction into a pocket instance remain outside the current compiler/core contract.

**Alternatives:** Keep containment and portal behavior sketch-local; invent dedicated actor classes
for portals or vehicles; silently widen `P-56` to allow remote extraction; treat consumed entities
as a separate hidden world instead of the existing attachment/container model.

**Rationale:** The repeated resolved cases did not need new engine primitives. They needed one
compiler contract that reused existing `P-58` and `P-59` semantics without implying unsupported
remote extraction or off-world persistence. Narrowing the remaining edge cases is more accurate
than pretending the current core contract already covers them.

---

## 2026-04 — Temporary geometry, body sweeps, and leashes share one spatial contract

**Context:** `Terrain Wall`, `Trail of Fire`, `Charge`, `Hit-Confirmed Dash`, `Build Zone`,
`Positional Leash`, and `Orbital Sweep` all reused the same missing compiler surface: the primitive
layer already covered `P-08`, `P-57`, `P-07`, and `P-04`, but the compiler docs did not define one
bounded authoring/lowering contract that tied those spatial primitives together.

**Decision:** Add `inject_geometry`, `polyline_zone`, `kinematic_sweep`, and status-owned
`movement_constraint` as the canonical compiler surface for temporary walls, recorded path
corridors, body-based sweep/capture motion, orbit-derived sweeps, and bookmark-driven leash rules.
Arbitrarily oriented walls lower through single-segment `P-57` corridors rather than rotated
`P-08` boxes, capture-first sweeps become temporary `P-06` attachment instead of shared authority,
and leash anchors come from runtime bookmarks so the same status surface supports fixed positions
and moving entity anchors.

**Alternatives:** Keep walls, trails, charges, leashes, and orbit sweeps sketch-local; invent
separate one-off movement logic per sketch; model carried targets as shared authority; add a second
client intent path for orbit/detach behavior.

**Rationale:** The repeated gap was not primitive absence. It was missing compiler surface that
connected existing spatial primitives coherently. One shared contract keeps geometry insertion,
path sampling, sweep hit dedup, capture handoff, and leash-anchor resolution deterministic without
turning the compiler layer into a collection of bespoke per-skill exceptions.

---

## 2026-04 — Zones are live actors with explicit mobility, persistence, and relation gates

**Context:** `Blizzard`, `Vortex`, `Shifting Sands`, `Oil-Ignite`, `Self-Sustaining Zone`,
`Target-Tracking Zone`, and `Zone-Conditional Invulnerability` all reused the same missing
compiler surface: zone actors already existed conceptually, but the docs did not define one
canonical contract for moving zones, occupant tracking, conditional persistence, or live
zone-conditioned hostile admission.

**Decision:** Treat zones as spawned actors with explicit `ZoneMobilityBlock`,
`ZonePersistenceBlock`, `ZoneForceBlock`, `zone.output_binding`, and status-owned
`zone_relation_gate`. `duration_ticks` is always a hard cap, moving-zone membership is computed
from the committed current zone position, and hostile admission gates resolve against the CURRENT
live zone instance rather than a cast-time snapshot.

**Alternatives:** Keep moving/tracking zones sketch-local; special-case vortex pull, tracking beams,
self-sustaining zones, and mist barriers separately; treat zone-conditioned immunity as an ad hoc
combat exception without a live zone reference.

**Rationale:** The repeated gap was zone lifecycle policy, not missing spawning or pulse primitives.
One shared zone-actor contract keeps mobility, membership, early-end rules, and defensive relation
checks deterministic across multiple sketches without creating bespoke one-off logic per zone type.

---

## 2026-04 — Advanced projectile behavior is one shared lifecycle contract, not seven one-offs

**Context:** `Spectral Dash`, `Growing Projectile`, `Knockback Projectile`, `Boomerang`,
`Sticky Bomb`, `Wall Bounce`, and `Projectile Deflect` all reused the same missing compiler
surface: advanced projectile behavior existed in the primitive layer, but not as one bounded
authoring/lowering contract.

**Decision:** Treat advanced projectile behavior as a shared family spanning archetype-owned
travel scalars, return-flight phases, bounce counters, attached delayed detonation, ability-local
`displacement.flight_policy`, and status-owned `projectile_intercept`. Live projectile IDs may be
bound only for single-spawn cases, return legs preserve one projectile identity with per-leg hit
ledgers, and deflect-style redirects use bounded `P-61` redirect generations instead of ad hoc
projectile cloning.

**Alternatives:** Keep projectile special cases sketch-local; model boomerang, sticky bomb, wall
bounce, and deflect as unrelated exceptions; create new actor types for every mutated projectile
shape.

**Rationale:** The recurring gap was lifecycle policy, not primitive absence. One shared contract
keeps handoff, phase changes, redirect bounds, and runtime-state references deterministic across
multiple projectile-heavy sketches without turning the compiler surface into a bag of bespoke
one-off mechanics.

---

## 2026-04 — Visibility is relation-scoped, presentation is downstream-only, and stasis pauses by shifting expiry

**Context:** `Minefield`, `Burrow`, `Cocoon`, `Decoy`, `Team-Agnostic Stasis`, `Ally Untargetable`,
and `Zone-Conditional Invuln.` all depended on the same missing compiler contract: one bounded way
to express who can target an entity, who can see it, and what suspension or dormancy actually does
to timers and payload admission.

**Decision:** Model targetability through relation-scoped `TargetabilityPolicyBlock` rules, model
appearance and false HP bars through downstream-only `ObserverPresentationBlock` rules, and model
nonstandard inactivity through `SuspensionBlock` with canonical `suspended`, `dormant`, and
`stasis` modes. Permanent entity policies and temporary status overlays stack by restriction, and
timer pausing in `stasis` resumes by shifting expiry ticks forward rather than mutating elapsed
history.

**Alternatives:** Keep stealth, deception, untargetability, and stasis sketch-local; treat
visibility as a client-only concern; use one generic boolean for untargetable/invisible/suspended;
pause timers by rewinding state at resume time.

**Rationale:** These mechanics recur across multiple sketches, but they are not the same policy.
Relation-scoped targetability preserves authoritative admission checks, downstream-only presentation
keeps deception from mutating gameplay state, and explicit suspension modes keep dormancy and stasis
bounded without leaking ad hoc timer semantics into later sketches.

---

## 2026-04 — Recursive proc chains use compiler-owned propagation state, not sketch-local logic

**Context:** `Chain Lightning`, `Crit Explosion`, `On-Kill Cascade`, `Spell Echo`, and
`Contagion` all reused the same missing contract: bounded multi-generation child emission with
deterministic replay, dedup, and cross-boundary relay semantics.

**Decision:** Represent these mechanics through compiler-owned `PropagationBlock` and `SpreadBlock`
metadata carrying `chain_id`, `generation`, `max_generations`, optional visited-target sets, and
optional replay snapshots. Use one shared generation-scaling rule for chance/effect decay, seed the
root target/carrier into dedup state before the first child query, and keep status spread on the
carrier's owner while preserving original caster credit.

**Alternatives:** Keep recursive proc logic sketch-local; rely only on `reactive_depth`; add
bespoke one-off rules for chain lightning, crit explosions, echoes, and spread effects separately.

**Rationale:** `reactive_depth` alone bounds within-tick hook cascades, not multi-tick or
cross-Arbiter trees. One propagation-state model keeps recursion finite, cross-boundary-safe, and
deterministic without forcing each sketch to redefine generation counters, dedup keys, or replay
snapshots.

---

## 2026-04 — Persistent links are one `P-34` binding record consumed across stages

**Context:** `Tether`, `Guardian Angel`, `Drag`, `Symbiote`, and `Soulbind` were all primitive-covered,
but the compiler docs still lacked one bounded runtime contract for break-distance checks, damage
redirect branches, heal mirroring, single-target replay, and remote origin anchoring.

**Decision:** Treat authored `link` as one compiler-owned `P-34` binding record with optional
Stage 6 break checks, Stage 8 redirect splitting, Stage 9 heal/event mirroring, and Stage 12
observer-anchor behavior. Make damage redirection a pre-mitigation packet split with partner-side
defensive resolution, and treat origin override as a spatial-origin/camera rule only rather than an
authority or stat transfer.

**Alternatives:** Keep link behavior sketch-local; model Tether, Guardian Angel, Symbiote, and
Soulbind as unrelated exceptions; copy outcomes between partners instead of resolving partner
branches against partner state.

**Rationale:** The repeated gap was not missing primitives. It was missing one shared binding
contract. A single `P-34` record keeps cleanup, handoff, relay semantics, and anti-recursion rules
consistent across multiple mechanics and prevents stage-order contradictions like post-mitigation
versus pre-mitigation redirect behavior.

---

## 2026-04 — Cross-boundary relays send parameters; authoritative owners recompute results

**Context:** `Blink Strike` and `Mana Burn` exposed the same missing rule. The compiler docs already
described Ghost-aware queries and target-side authoritative reads, but they did not state one
explicit policy for instant cross-boundary snaps or for resource reads that depend on remote
authoritative pools.

**Decision:** Treat Ghost data as advisory for admission only. When an effect depends on authoritative
remote state, the origin owner relays PARAMETERS, and the owner that already holds that state
recomputes the result. Destination-based instant snaps (`Blink Strike`) are committed by the
destination owner in the same tick, and target-side resource reads (`Mana Burn` / `resource_burn`)
are committed by the target owner.

**Alternatives:** Let origin owners commit outcomes from Ghost data; relay guessed destination
coordinates or computed burn amounts; special-case Blink Strike and Mana Burn separately.

**Rationale:** The repeated issue was authority ambiguity, not primitive availability. One shared
rule keeps single authority intact for both instant teleports and target-side resource reads,
prevents Ghost data from silently becoming authoritative, and gives future edge cases one clear
relay model instead of ad hoc exceptions.

---

## 2026-04 — Channels and concentration share one maintained-effect lifecycle model

**Context:** The sketch audit showed that channels, counterspell, cast bars, and concentration all
depended on the same missing compiler contract: one bounded lifecycle for visible cast state,
mid-cast cancellation, per-tick maintained execution, and teardown of persistent outputs.

**Decision:** Represent interruptible maintained casts through `ChannelBlock`, and represent
post-resolution maintained effects through `requires_concentration` plus `ConcentrationBlock`.
Publish visible cast state for all non-zero `cast_time` abilities, let `P-40` cancel those casts
deterministically, let `P-55` evaluate concentration on damage, and treat persistent outputs from a
channel/concentration cast instance as instance-owned artifacts torn down at Stage 11.

**Alternatives:** Keep channel/counterspell/concentration sketch-local; create separate bespoke
lifecycles for channeling and concentration; widen the external input/intent model just to support
steering during maintained casts.

**Rationale:** The repeated problem was not primitive availability. It was missing lifecycle
policy. One maintained-effect model keeps cast bars, interrupt rules, per-tick channels,
concentration ownership, and teardown behavior consistent across combat mechanics without adding new
trust-boundary complexity or special-case cleanup rules per sketch.

---

## 2026-04 — Control topology and loadout projection are compiler-owned contracts

**Context:** The sketch audit showed that multi-entity control, mind control, form swaps, borrowed
abilities, and dual-owner entities were already primitive-covered by `P-29`, `P-30`, and `P-31`,
but the compiler docs still lacked a stable authoring and lowering contract for those mechanics.

**Decision:** Surface these mechanics canonically through `loadout_profiles`, `control_topology`,
`swap_identity`, `borrow_ability_slot`, `control_override`, and `LoadoutSource`. Treat persistent
control groups as entity-definition metadata installed at Stage 1, and treat temporary form/slot
projection as Stage 11 `P-31` policies with explicit revert payloads. Use a bounded public
cast-history register for `last_cast_ability`.

**Alternatives:** Keep control/loadout mechanics sketch-local; represent them as arbitrary adapter
logic without compiler validation; add bespoke one-off mechanics for mind control, form swaps, and
ability steal separately.

**Rationale:** The repeated gap was missing compiler contract, not missing engine primitives.
Control routing and loadout projection are cross-cutting mechanics that recur across many sketches.
Making them canonical keeps the compiler surface bounded, reuses the existing Stage 1 and Stage 11
engine contracts, and lets later sketches inherit one deterministic model instead of re-deriving
routing, revert, or borrowed-loadout behavior ad hoc.

---

## 2026-04 — Status-owned combat policies and entity block defense for non-HP resolution rules

**Context:** The sketch compatibility audit showed that the compiler already had the right
primitive taxonomy for mana burn, deferred resolution, death immunity, death prevention, stagger
bars, shield-burst payoffs, block, and counter windows, but those mechanics were still only
"primitive-covered." The missing piece was a canonical compiler contract tying authoring, stage
ordering, and wire/static data together.

**Decision:** Represent these mechanics through explicit schema/runtime policies instead of
sketch-local behavior: `ResourceCost.escalation`, `VulnerabilityWindowBlock`, `resource_burn`,
`swap_hp_percent`, `execute`, `BlockDefenseDef`, shield lifecycle hooks with remaining-value
bindings, and status-owned `damage_accumulator`, `deferred_ledger`, `hp_floor`,
`death_prevention`, and `movement_damage` blocks. Fix the stage ordering so block happens before
shield/mitigation, death prevention resolves after HP-floor policies, and stagger/counter windows
remain mechanical state rather than ordinary DR-scaled CC.

**Alternatives:** Leave the mechanics primitive-only and close sketches one at a time; add bespoke
compiler exceptions per sketch; model everything as custom Lua-side logic instead of stable
compiler-supported policies.

**Rationale:** The repeated gap was not lack of primitives. It was lack of one canonical policy
layer for "combat that is not ordinary HP damage." Making these patterns first-class keeps the
compiler surface bounded, makes validation possible, and prevents future sketch closure from
re-deriving stage ordering or authority rules ad hoc.

---

## 2026-04 — Runtime states plus hidden activation variants for stateful abilities

**Context:** The sketch audit showed a shared compiler gap across reactivation abilities,
rewinds, combo-step routing, charge systems, and "next cast / first hit" windows. The missing piece
was not primitive availability alone; it was the lack of one canonical state model connecting
authoring, IR lowering, runtime storage, and wire format.

**Decision:** Model these mechanics as bounded per-entity runtime states plus ordered
`ActivationModes` that redirect the public ability entry to hidden compiled variants. Keep
hold-release abilities on the existing discrete-cast plus continuous-button-state ingress contract.
Represent rewind recording and one-shot empower/counter windows as status-owned metadata
(`snapshot_recorder_state` and `consumption_window`) instead of bespoke sketch-local behavior.

**Alternatives:** Keep reactivation/combo/charge behavior sketch-local; add one-off special cases
per ability family; introduce new external client intent variants for hold-release abilities.

**Rationale:** This keeps the compiler surface bounded and reusable. Hidden variants let same-key
reactivation and combo routing swap targeting/effects cleanly without mutating one IR block in
place. Runtime-state tables give bookmarks, rewind buffers, sequence windows, and charge pools one
shared authoritative storage model that survives handoff. Preserving the existing intent taxonomy
avoids widening the trust boundary just to support charged abilities.

---

## 2026-04 — Canonical CC behavior profiles and status-immunity contract in compiler docs

**Context:** The full 125-sketch compatibility audit showed that the compiler had baseline `apply_cc`
coverage, but core CC mechanics were still only partially specified. Stun, root, silence, sleep,
blind, taunt, berserk, mute, and partial/full super-armor all depended on implied behavior that
was not yet a canonical compiler/runtime contract.

**Decision:** Treat supported crowd-control types as canonical behavior profiles lowered into
generated status metadata. Add explicit duration-scaling policy, status-authored category immunity,
CC expiry follow-ups, deterministic CC admission/enforcement ordering, and wire-level CC behavior /
immunity fields.

**Alternatives:** Keep CC behavior sketch-local; add one-off special cases per ability; model all
control effects as arbitrary custom status logic instead of stable compiler-supported profiles.

**Rationale:** The repeated gap was not primitive availability; it was missing canonical policy.
Making CC behavior profile-driven keeps the authoring surface compact, lets the runtime enforce
blind/taunt/berserk/mute/fear/charm deterministically without bespoke per-ability code paths, and
gives designers a stable way to express super-armor / immunity windows through ordinary status
authoring instead of undocumented engine flags.

---

## 2026-04 — Engine-first build order

**Context:** The original `02-implementation-phases.md` defined a 5-phase roadmap building the ARPG directly (shared-types → controller → arbiter → edge → swarm-tester). Meanwhile, the engine extraction into `docs-core/` produced a complete, game-agnostic contract layer.

**Decision:** Build the engine layer (`docs-core/` contracts) first, then layer the ARPG on top via the game adapter interface.

**Alternatives:** Continue with ARPG-first phases; build both in parallel.

**Rationale:** `docs-core/` is fully mature with zero TODOs — it's the most implementation-ready layer. Building engine-first validates the reusable architecture before committing to game-specific decisions. The game adapter boundary (`docs-core/04-*`) is explicitly designed to allow any game to plug in, so the ARPG becomes just one consumer. Building ARPG-first would have baked game-specific assumptions into engine code that would later need extraction — the same problem the spec already went through.

---

## 2026-04 — Explicit status polarity and cleanse contract in compiler docs

**Context:** The ability sketch set had broad primitive coverage, but `SK-15 Purify` exposed a missing canonical contract. The compiler docs had `apply_buff`, `apply_debuff`, `apply_cc`, and `StatusEffectDefinition`, but no explicit status polarity model, no first-class `cleanse` effect, and no documented way to express a temporary "block new debuffs" immunity window.

**Decision:** Add explicit `polarity` and `status_application_immunity` to `StatusEffectDefinition`, add `is_cleansable` to `apply_cc`, add a first-class `cleanse` effect schema, and introduce `P-66 Status Effect Filter Mutation` in the primitive taxonomy.

**Alternatives:** Keep cleanse semantics sketch-local; infer polarity from `apply_buff`/`apply_debuff` only; treat crowd control as a special case outside the generic status registry.

**Rationale:** Designer-recreatable ability docs require more than primitive chains. Cleanse/dispel behavior depends on canonical metadata that the compiler can validate and the runtime can evaluate deterministically. Making polarity and cleanse policy explicit removes ad hoc tag matching, lets generated CC statuses participate in the same runtime rules as ordinary debuffs, and provides a reusable contract for future dispels, buff strips, and temporary status-immunity windows.

---

## 2026-03 — Redpanda over Redis Streams for event bus

**Context:** The spec originally referenced Redis Streams for the Meta Services event bus. No production traffic existed yet.

**Decision:** Adopt Redpanda (Kafka API) as the day-1 event bus. Redis retained only for Session Manager registry/caching.

**Alternatives:** Redis Streams; dual-write with cutover plan.

**Rationale:** Redpanda provides durability (`acks=all`, idempotent producers), at-least-once delivery with consumer-side idempotency, strict FIFO ordering per partition, and DLQ support — all required by the durability bridge contract. Since there's no live traffic, a dual-write cutover was unnecessary complexity. Redpanda's topic/partition/offset semantics also align directly with the replay/spectator/event-spine architecture planned for phase 2. See `docs/6-spec-drafts/tier-2-contracts/07-redpanda-adoption-adr.md` for the full ADR.

---

## 2026-03 — `no_std` for shared-types crate

**Context:** `shared-types` defines the foundational type vocabulary (stage IDs, deferred events, entity IDs) shared across all engine crates.

**Decision:** Build `shared-types` as `#![no_std]` with `#[cfg(test)] extern crate std`.

**Alternatives:** Standard `std` crate; `no_std` with alloc.

**Rationale:** The Arbiter's 60Hz loop is the most constrained execution context in the system. Keeping the shared type crate `no_std` ensures these types never accidentally pull in allocating or blocking operations. It also keeps the door open for embedded or WASM targets if the engine is ever ported. Test code uses `std` for convenience (Vec in assertions, etc.) without contaminating the library.

---

## 2026-03 — Single-threaded Tokio for Arbiter

**Context:** The Arbiter runs a deterministic 60Hz simulation loop with strict no-shared-mutable-state invariants.

**Decision:** Use single-threaded Tokio runtime for the Arbiter process. Multi-threaded Tokio for Controller and Edge nodes.

**Alternatives:** Multi-threaded Tokio everywhere; custom event loop without Tokio.

**Rationale:** The Arbiter's lock-free invariant means no mutexes or RwLocks inside the tick loop. A multi-threaded runtime would require synchronization primitives that violate this constraint. Single-threaded Tokio gives async I/O (for network ingress/egress between ticks) without introducing shared-state concurrency. Controller and Edge have no determinism requirement, so multi-threaded runtime is fine there. Mandated in `docs/0-getting-started/02-implementation-phases.md` §1.2.

---

## 2026-02 — Layer extraction from monolithic spec

**Context:** `docs/` started as a single ARPG server specification. During development it became clear that a reusable distributed game engine was embedded inside the ARPG-specific design.

**Decision:** Extract the engine contracts into `docs-core/` and the compiler/tooling layer into `docs-game-compiler/`, leaving `docs/` as the ARPG reference implementation.

**Alternatives:** Keep everything in `docs/` with section tags; create a separate repo for the engine.

**Rationale:** The monolithic spec mixed engine invariants (spatial authority, 60Hz tick, determinism) with game-specific design (loot tables, talent trees, quest systems). This made it impossible to reason about which rules were universal vs. ARPG-specific. Extraction into layers with a strict precedence hierarchy (`docs-core/` wins on conflicts) cleanly separates concerns. A separate repo was rejected because the layers are tightly co-evolving during the design phase — the extraction mapping (`docs-core/06-architecture-section-mapping.md`) requires reading both simultaneously.
