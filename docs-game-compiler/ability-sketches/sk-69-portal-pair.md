# SK-69: Portal Pair

## Designer Intent

I place a portal at my current position. After a short delay, I place a second portal at my new position (or target location). The two portals are linked — any ally who clicks one is instantly teleported to the other. Portals persist for 9 seconds. Bidirectional — allies can go either way.

## Primitive Composition

P-32 (Actor Spawning) → P-59 (N-Way Portal Network) → P-01 (Instant Translation)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- First portal: placed at caster's position (or ground-targeted)
- Second portal: placed at caster's position after delay (or second ground target)

## Observable Behavior

1. First cast — Portal A appears at the caster's position
2. Short delay (1-2 seconds), then second cast — Portal B appears at the caster's new position
3. Both portals are linked and active for 9 seconds
4. Any ally (including the caster) can right-click either portal to teleport to the other
5. Teleportation is instant — same as SK-35 Blink Strike (position snap)
6. Portals are bidirectional — A→B and B→A
7. Brief cooldown per user after teleporting (1 second — can't spam back and forth)
8. Enemies cannot use the portals
9. Portals are visible to enemies but not interactable by them
10. Visual: swirling magical doorways, whoosh effect on teleport

## Engine Primitives Required

### Linked Placed Structures

Two portal entities are placed in the world, linked to each other:

```
struct PortalActor {
    portal_id: EntityID,
    linked_portal_id: EntityID,
    linked_portal_position: Vec2F,
    linked_portal_arbiter_id: u32,
    owner_team: TeamId,
    expires_at_tick: u64,
    use_cooldown_ticks: u64,
    recent_users: HashMap<EntityID, u64>,  // entity → last_use_tick (for per-user cooldown)
}
```

Each portal knows where its partner is. When an ally interacts with Portal A, the Arbiter:
1. Validates: is the user on the correct team? Is the per-user cooldown expired?
2. Reads `linked_portal_position`
3. Snaps the user's position to the linked portal's position (instant teleport)
4. Records the use for per-user cooldown

### Interaction Model

Portals are interact-able entities — allies can "use" them, similar to SK-45 Essence Collection's pickup mechanic but with a teleportation outcome. The interaction is:
- Proximity-based: ally must be within interact range of the portal
- Team-restricted: only the caster's team
- Cooldown-restricted: per-user, not per-portal

### Instant Cross-Boundary Teleportation

If Portal A is on Arbiter X and Portal B is on Arbiter Y, using Portal A teleports the ally from Arbiter X to Arbiter Y. This is an **instant cross-boundary handoff** — same as SK-35 Blink Strike but triggered by interacting with a placed structure rather than casting an ability.

The portal entity on Arbiter X must know the linked portal's Arbiter and position to route the handoff correctly.

### Portal Placement Across Boundaries

The caster places Portal A, walks to a new location, and places Portal B. If the caster crossed a boundary between placements, the two portals are on different Arbiters. The portals must maintain a cross-boundary link:
- Portal A on Arbiter X has `linked_portal_arbiter_id = Y`
- Portal B on Arbiter Y has `linked_portal_arbiter_id = X`
- Position updates are needed if either portal could move (they're stationary, so position is fixed at placement)

### Linked Lifecycle

If one portal is destroyed or expires:
- The other portal also despawns (portals are useless alone)
- Or: the other portal persists but becomes non-functional (design choice)

## Cross-Boundary Concerns

TODO: Portals are designed for cross-boundary use — the whole point is moving allies across distances:

1. **Both portals on same Arbiter:** Simple. Teleport is a local position snap.
2. **Portals on different Arbiters:** Portal A (Arbiter X) knows Portal B is at position P on Arbiter Y. On use: ally is removed from Arbiter X and inserted at position P on Arbiter Y. Instant handoff.
3. **Topology change:** If a split/merge changes which Arbiter owns a portal's position, the portal must update its linked_portal_arbiter_id. Or: portals don't survive topology changes (simpler).
4. **Multiple allies using simultaneously:** Two allies use Portal A in the same tick. Both are teleported to Portal B's position on Arbiter Y. Two simultaneous handoffs to the same destination.

## Compiler Requirements

TODO: Designer specifies: two-part placement (Portal A, then Portal B), link between portals, ally-only interaction, instant teleport to linked position, per-user cooldown (1s), portal duration (9s), bidirectional. Compiler produces:
- PortalActor entity definition (position, link, team, lifetime, cooldown tracking)
- Two-phase placement ability (place A, then place B with linking)
- Interact action definition (proximity, team check, cooldown check)
- Teleport resolution: instant position snap to linked portal position
- Linked lifecycle: despawn partner on expiry/destruction

## Open Questions

- Can portals be placed inside buildings/structures?
- Can portals be destroyed by enemies (do they have HP)?
- Does teleporting through a portal trigger SK-32 Minefield at the destination?
- Can enemies see which direction allies teleported (from A→B or B→A)?
- Does teleporting through a portal break SK-04 Tether if it exceeds break distance?
- Can SK-01 Toss throw an enemy INTO a portal (forced portal use)?
- Can the caster place both portals at the same location (degenerate case)?
- Does the portal interaction interrupt movement, or is it seamless?
- Can SK-55 Growing Projectile or SK-62 Boomerang pass through portals?
- How does the portal interact with SK-44 Burrow — can a burrowed entity use a portal?
