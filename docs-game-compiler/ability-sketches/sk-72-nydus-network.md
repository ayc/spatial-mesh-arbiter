# SK-72: Nydus Network

## Designer Intent

I place Nydus Worms at various positions around the map. I can enter any worm and choose which other worm to exit from. The worms persist until destroyed by enemies. I can place more worms over time, expanding the network. Any ally can use the network.

## Primitive Composition

P-32 (Actor Spawning) → P-59 (N-Way Portal Network) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target position for each worm (ground-targeted)
- Worm selection input (choose which worm to exit from)

## Observable Behavior

1. First cast — Nydus Worm A spawns at target position (takes 2 seconds to emerge)
2. Subsequent casts — additional worms (B, C, D...) spawn at target positions
3. Any ally interacts with a worm: UI shows all other worms in the network, ally chooses destination
4. Teleport to chosen worm is instant (after a brief channel/enter animation, 0.5s)
5. Each worm has HP and can be destroyed by enemies
6. Destroying a worm removes it from the network — other worms still function
7. No limit on worm count (bounded by cooldown and game duration)
8. Worms persist indefinitely until destroyed
9. Worms are visible to enemies (can be scouted and killed)
10. Visual: organic worm structures, entry/exit animation, tunnel effect during travel

## Engine Primitives Required

### N-Way Portal Network

SK-69 Portal Pair links exactly two portals bidirectionally. Nydus extends this to **N portals with any-to-any routing**:

```
struct NydusNetwork {
    network_id: UUID,
    owner_team: TeamId,
    worm_ids: Vec<EntityID>,   // All living worms in the network
}

struct NydusWorm {
    worm_id: EntityID,
    network_id: UUID,
    position: Vec2F,
    hp: SimFixed,
    max_hp: SimFixed,
    is_alive: bool,
}
```

When an ally enters a worm:
1. Present a selection UI showing all other living worms in the network
2. Ally chooses a destination worm
3. Brief channel (0.5s, interruptible)
4. Instant teleport to the destination worm's position

### Dynamic Network Membership

Unlike SK-69 (two portals placed together, fixed), the Nydus Network grows over time:
- New worms are added to the network as the caster places them
- Destroyed worms are removed from the network
- The network is valid as long as at least 2 worms exist (need entry + exit)
- If only 1 worm remains, it's usable only for entry to future worms

The Arbiter (or Meta service?) must maintain the network's worm registry. When a new worm is placed, all existing worms learn about the new member. When a worm dies, it's removed from the registry.

### Destination Selection UI

This is the first ability requiring a **player selection from a dynamic list at runtime**. The ally enters a worm and must CHOOSE where to go. The Edge Node presents a selection UI showing available worms (positions, names/identifiers). The ally picks one, and the selection is sent as part of the teleport proposal.

This is different from SK-69 Portal Pair (bidirectional, no choice needed — only one destination) and from any other ability (where the target is chosen at cast time, not during an interaction).

### Persistent Destructible Structures

Nydus Worms are permanent placed structures with HP:
- They persist across fights, topology changes, player deaths
- Enemies can discover and destroy them (counterplay)
- They have a position in the entity map and participate in pathing/collision
- They survive Arbiter splits/merges (transferring to whichever child inherits their position)

## Cross-Boundary Concerns

TODO: Nydus Worms can be placed anywhere on the map — they WILL be on different Arbiters. The network is inherently cross-boundary:

1. **Network registry:** Which Arbiter owns the network state? Options: Controller tracks it centrally, or each worm knows about the others peer-to-peer. Central is simpler but adds Controller dependency. Peer-to-peer requires broadcast on worm creation/destruction.

2. **Cross-boundary teleport:** Ally enters Worm A on Arbiter X, exits Worm C on Arbiter Z. Same instant handoff pattern as SK-69, but the destination is chosen from a dynamic list, not fixed.

3. **Worm destruction notification:** When Worm B is destroyed on Arbiter Y, all other worms must learn about it (remove from selection UI). Cross-boundary state update.

4. **Topology changes:** A worm placed before a split/merge persists. It transfers to the new Arbiter owning its position. The network registry must update.

## Compiler Requirements

TODO: Designer specifies: worm placement (ground-targeted, channeled spawn), worm HP, network membership (dynamic, any-to-any), ally interaction (enter + choose destination + teleport), worm lifetime (permanent until destroyed), network valid with 2+ worms. Compiler produces:
- NydusWorm entity definition (HP, position, network_id)
- NydusNetwork registry (dynamic membership, worm creation/destruction)
- Interaction definition: enter → selection UI → choose destination → channel → teleport
- Cross-boundary network state synchronization
- Worm destruction hook: remove from network, notify all members

## Open Questions

- Can enemies use the Nydus Network (enter an enemy worm)?
- Is there a maximum number of worms in one network?
- Can the caster place a worm inside SK-60 Bunker (worm inside a structure)?
- Does entering/exiting a worm trigger SK-32 Minefield?
- Can a worm be placed on an Arbiter boundary?
- How does the selection UI work — does the ally see a minimap with worm positions?
- Can the caster destroy their own worms (to deny enemy use/clean up)?
- Does the 0.5s enter channel make the user vulnerable to interrupts?
- How does the network registry persist across Arbiter crashes (worms are soft state)?
- Can worms be placed in combat, or only out of combat?
