# SK-72: Nydus Network

## Designer Intent

I place Nydus Worms around the map. Any ally can enter one worm, choose any other living worm in
the same network, and emerge there after a short enter channel. Worms persist as visible
destructible structures until destroyed or otherwise removed.

## Primitive Composition

P-32 (Actor Spawning) → P-59 (N-Way Portal Network) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Ground-targeted worm placement position
- Placement cast time / emergence delay
- Worm archetype stats (HP, visibility, collision, observer presentation)
- Worm interaction choice: source worm entered, destination worm selected

## Observable Behavior

1. Cast to place Worm A at the requested ground position after the authored emerge time
2. Later casts place additional worms that join the same owner-scoped network
3. Any allied user interacting with a worm sees the currently valid destination worms in that
   network and chooses one
4. After the short enter channel, the user is teleported to the chosen destination worm
5. Each worm is a visible destructible structure with its own HP and can be killed by enemies
6. Destroying one worm removes only that worm; the remaining worms stay in the network
7. If fewer than two worms remain, the surviving worm is still a valid network member but has no
   current exit options
8. For the canonical profile, network size is bounded by the baseline `P-59` caps rather than
   being literally unbounded
9. Visual: emerge animation on placement, obvious entry/exit interaction, and tunnel travel cue on
   successful use

## Engine Primitives Required

Nydus Network is now a canonical owner-scoped `portal_anchor` pattern on ordinary spawned actors.
It does not need a separate network registry subsystem beyond `P-59`.

### Canonical Worm Authoring Shape

Each placement cast lowers to one `spawn_actor` that emits an ordinary destructible worm actor with
portal metadata:

- `portal_anchor.network_mode = owner_scoped`
- `portal_anchor.interaction_range = ...`
- `portal_anchor.allowed_filter = ally_alive`
- `portal_anchor.destination_mode = player_choice`
- `portal_anchor.per_user_cooldown_ticks = ...`
- `portal_anchor.channel_ticks = 30` for the 0.5 second enter channel
- `portal_anchor.destroy_network_on_removed = false`

The network key is `(owner, public_ability_id)`. That means every live worm from the same owner and
ability automatically joins the same `P-59` network.

### Destination Choice

Destination choice is engine-owned once the network exists.

1. the source-anchor owner already has the replicated `P-59` network membership
2. it presents only currently valid destination anchors to the user
3. the chosen destination resolves through the ordinary `P-01` instant-translation + handoff path

No sketch-local peer-to-peer registry or special UI protocol is required.

### Structure / Lifetime Semantics

The worms are ordinary spawned actors:

- they use normal entity HP and targetability rules
- they are visible to enemies through ordinary observer presentation
- enemies may attack and destroy them like other spawned structures
- they remain until destroyed, explicit removal, or expiry of whatever long-lived spawn duration the
  game authors for the worm archetype

## Cross-Boundary Concerns

Nydus Network follows the canonical `P-59` cross-Arbiter model.

1. When worms on the same network live on different Arbiters, the Mesh Controller replicates the
   portal-network registry to all participating anchor owners
2. A user entering Worm A only talks to Worm A's owner; that Arbiter validates range, filter, per-
   user cooldown, and destination choice against the replicated registry
3. If the chosen destination worm is remote, teleport uses the ordinary cross-Arbiter instant-
   translation + destination handoff contract
4. When a worm is destroyed or hands off because topology changes, the current owner updates the
   shared `P-59` registry; other worms do not maintain a bespoke peer list
5. Simultaneous users are independent. The network does not serialize all travel beyond each user's
   own channel and cooldown gates

## Compiler Requirements

Designer specifies:

- worm placement position and placement cast / emerge timing
- worm archetype, HP, and presentation
- interaction range
- ally-only usage filter
- enter channel duration
- per-user reuse cooldown

Compiler emits:

- one ordinary spawned worm actor per placement cast
- one owner-scoped `portal_anchor` block on that spawn
- one shared owner-scoped `P-59` network keyed by owner + public ability identity
- ordinary player-choice portal interaction with no sketch-local network manager

Compiler validates:

1. `portal_anchor.network_mode = owner_scoped`
2. `portal_anchor.destination_mode = player_choice`
3. `interaction_range > 0`
4. `channel_ticks >= 0`
5. `per_user_cooldown_ticks >= 0`
6. the authored worm count cannot exceed the core `max_portal_anchors_per_network` bound; extra
   placements beyond the live cap fail deterministically rather than widening the baseline profile

## Resolved Notes

- Enemies cannot use the network in this sketch because `allowed_filter = ally_alive`
- The network is not literally unlimited; the canonical bound is the baseline `P-59`
  `max_portal_anchors_per_network`
- Entering a worm is interruptible if the authored `channel_ticks` channel is interrupted before
  completion
- Worms may be placed in combat unless a separate placement guard forbids it; `P-59` itself does
  not require an out-of-combat restriction
- Destroying a worm is the intended counterplay. The network degrades naturally as anchors are
  removed instead of collapsing automatically on the first loss
