# SK-30: Trail of Fire

## Designer Intent

As I move, I leave a burning trail behind me. The trail persists for 4 seconds after I pass through. Enemies who walk through the trail take fire damage and are ignited (short DoT). The trail follows my exact movement path.

## Primitive Composition

P-57 (Polyline Collision Generator) → P-14 (Continuous Proximity Monitor) → P-44 (Pulse Timer)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (passive or toggled — active while moving)
- Caster's movement path

## Observable Behavior

1. As the caster moves, fire appears along the path they traveled
2. The trail is not a circle — it's a line/path with width following the caster's exact route
3. Each segment of trail persists for 4 seconds from when it was deposited
4. Enemies who touch any trail segment take fire damage
5. Enemies who linger in the trail are ignited (DoT, 2 seconds, refreshed on continued contact)
6. The caster is immune to their own trail
7. Trail segments expire individually (oldest segments fade first)
8. Visual: burning ground along the path, fading from back to front

## Engine Primitives Required

TODO: This is fundamentally different from circular zones. The geometry is a **polyline with width** — a series of connected line segments, each with a timestamp. The Arbiter needs to:
1. Record the caster's position at regular intervals (every N ticks) to build the polyline
2. Create trail segments between consecutive positions
3. Each segment has its own expiry timer
4. Per tick: check if any enemy entity intersects any active trail segment
5. Apply damage/ignite on intersection

How is this represented? A list of `TrailSegment { start: Vec2F, end: Vec2F, width: SimFixed, created_tick: u64 }`? Is collision detection a series of capsule checks (line segment + radius)?

## Cross-Boundary Concerns

TODO: If the caster moves along an Arbiter boundary, the trail is deposited in one Arbiter's region but may need to be visible/collidable in the neighbor's. Trail segments near a boundary: are they replicated as Ghost-like objects? If the caster crosses a boundary, do trail segments behind them (in the old Arbiter) persist? Who owns them — the caster's current Arbiter or the Arbiter where they were deposited?

## Compiler Requirements

TODO: Designer specifies: trail width, segment lifetime (4s), damage on contact, ignite DoT (2s, fire damage), caster immunity, sampling rate (how often to record positions). Compiler produces: a movement-tracking hook on the caster + trail segment spawning logic + per-segment lifecycle + capsule collision definition + damage/DoT payload. This is unlike any other ability — it's driven by movement, not by casting.

## Open Questions

- How frequently are positions sampled to build the trail — every tick (60Hz) or less? More segments = more collision checks.
- Is the trail one continuous ZoneActor or many independent segment actors?
- What happens if the caster stands still — no new trail deposited, existing trail fades normally?
- Can the trail go through walls, or does it respect static geometry?
- Does the trail interact with SK-31 Vortex — enemies pulled through a trail take damage?
- Performance: a fast-moving caster in a 4-second window could create hundreds of trail segments. Is there a segment cap?
- If the caster is displaced (SK-01 Toss), does the trail appear along the arc?
- Can enemies destroy trail segments?
- Does the trail block projectile pathing like SK-03 Terrain Wall, or is it passable (damage only)?
