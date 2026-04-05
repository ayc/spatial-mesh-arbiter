# SK-69: Portal Pair

## Designer Intent

I place Portal A, then place Portal B shortly afterward. The two portals are linked for 9 seconds.
Any ally who interacts with either portal is instantly teleported to the other. The portals are
bidirectional, visible to enemies, and unusable by enemies.

## Primitive Composition

P-32 (Actor Spawning) → P-59 (N-Way Portal Network) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- First portal position
- Second portal position

## Observable Behavior

1. First use places Portal A
2. Second use places Portal B and links it to Portal A
3. Once both portals exist, allies may interact with either portal to teleport to the other
4. Teleportation is instant
5. Each user has an individual short reuse cooldown before they can use the pair again
6. Enemies can see the portals but cannot use them
7. The linked pair lasts 9 seconds unless removed earlier
8. For this sketch, removing either portal collapses the pair

## Engine Primitives Required

Portal Pair is now a canonical `spawn_actor.portal_anchor` pattern built as a two-step reactivation.

The recommended lowering is:

1. First cast:
   - `spawn_actor {`
     `output_binding = portal_a,`
     `portal_anchor = {`
       `network_mode = new_pair_leader,`
       `interaction_range = ... ,`
       `allowed_filter = ally_alive,`
       `destination_mode = paired_other,`
       `per_user_cooldown_ticks = 60,`
       `channel_ticks = 0,`
       `destroy_network_on_removed = true`
     `}`
   - write `portal_a` into a runtime-state bookmark
2. Second cast while that bookmark is present:
   - hidden reactivation variant
   - `spawn_actor {`
     `portal_anchor = {`
       `network_mode = pair_follower,`
       `paired_anchor_state = first_portal_bookmark,`
       `interaction_range = ... ,`
       `allowed_filter = ally_alive,`
       `destination_mode = paired_other,`
       `per_user_cooldown_ticks = 60,`
       `channel_ticks = 0,`
       `destroy_network_on_removed = true`
     `}`

This keeps the portal pair inside the canonical portal-network contract. The anchors are ordinary
spawned actors with portal metadata; they are not a bespoke actor class.

For this sketch, the portals are visible to enemies through ordinary `observer_presentation`, but
enemy interaction is rejected by `allowed_filter = ally_alive`. The portals are not designed as
enemy-destructible structures here; enemy hostility is visual counterplay / information only, not
an attack interaction.

## Cross-Boundary Concerns

Portal Pair is designed to work cleanly across Arbiters.

1. If both portals are local, use is a local `P-01` instant translation
2. If the paired anchor is remote, `P-59` already replicates the network registry across the
   Arbiters that host anchors in that network
3. The source-anchor owner validates interaction range, team filter, and per-user cooldown, then
   teleports the user to the paired anchor through the ordinary instant-translation + destination
   handoff rules
4. Topology changes do not break the pair. If an anchor hands off, the portal-network registry
   updates with the new authoritative Arbiter for that anchor
5. Simultaneous ally uses are ordinary independent portal uses. The pair does not serialize users
   beyond each user's own cooldown gate

## Compiler Requirements

Designer specifies:

- first and second anchor placement positions
- portal lifetime
- interaction range
- ally-only usage filter
- per-user reuse cooldown
- observer presentation

Compiler emits:

- one reactivation/bookmark-based two-step portal placement flow
- one `new_pair_leader` portal anchor on the first cast
- one `pair_follower` portal anchor on the second cast
- one owner-local bookmark that remembers the first anchor between casts
- ordinary `P-59` interaction and `P-01` teleport routing

Compiler validates:

1. the follower variant references a valid `RuntimeStateDefinition` of kind `bookmark(entity_ref)`
2. `interaction_range > 0`
3. `per_user_cooldown_ticks >= 0`
4. `channel_ticks >= 0`
5. `destination_mode = paired_other` for pair-style anchors

## Resolved Interaction Notes

- Bidirectionality is automatic once both anchors exist in the same `P-59` network; there is no
  second explicit "reverse link" mechanic.
- Teleport destination effects, traps, or leash checks at the destination follow the ordinary
  `P-01` instant-translation rules after arrival.
- Placing both portals at the same coordinates is legal but strategically useless; it still creates
  a valid pair under the canonical portal contract.
- Because `destroy_network_on_removed = true` is authored for this sketch, expiry or manual removal
  of either anchor collapses the pair instead of leaving behind a useless singleton portal.
