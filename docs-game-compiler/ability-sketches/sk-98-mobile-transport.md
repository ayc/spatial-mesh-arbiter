# SK-98: Mobile Transport

## Designer Intent

I summon a dropship at my position. Allies can enter the dropship (up to 4 passengers). Once loaded, I select a destination on the map and the dropship flies there. On arrival, all passengers exit at the destination. The dropship can be shot down during flight — if destroyed, passengers crash-land at the current position.

## Primitive Composition

P-32 (Actor Spawning) → P-58 (Container/Vehicle Logic) → P-06 (Attached Kinematics)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity (summons the transport)
- Allies interact to enter
- Caster selects destination (ground-targeted, potentially global range)

## Observable Behavior

1. Summon dropship at caster's position — dropship entity appears
2. Allies walk near the dropship and interact to enter (like SK-60 Bunker entry)
3. Up to 4 allies can enter (+ caster = 5 total occupants)
4. Caster selects a destination on the map
5. Dropship lifts off and flies to the destination (travel time proportional to distance)
6. During flight: dropship is visible and targetable. It has HP.
7. During flight: occupants are untargetable and cannot act
8. On arrival: dropship lands, all occupants exit at the destination position
9. If dropship is destroyed mid-flight: all occupants are ejected at the crash position with a brief stun
10. Visual: military dropship, flight path line on minimap, landing effect

## Engine Primitives Required

### Moving Enterable Vehicle

SK-60 Bunker is a STATIONARY enterable structure. Mobile Transport adds MOVEMENT:

```
struct TransportActor {
    transport_id: EntityID,
    hp: SimFixed,
    max_hp: SimFixed,
    occupants: Vec<EntityID>,
    max_occupants: u8,
    owner_team: TeamId,
    phase: TransportPhase,
}

enum TransportPhase {
    Loading { expires_at_tick: u64 },            // On ground, allies entering
    InFlight { destination: Vec2F, speed: SimFixed }, // Moving to destination
    Landing,                                      // Arriving, occupants exiting
    Destroyed { crash_position: Vec2F },          // Shot down
}
```

### Flight Path

The transport moves from origin to destination at a fixed speed:
- Each tick: `transport.position += normalize(destination - position) * speed`
- The transport traverses the map in a straight line
- Travel time = distance / speed

During flight, the transport is an entity moving at high speed. Unlike normal entity movement (bounded by movement speed caps), the transport can move at arbitrary speed (it's a vehicle, not a character).

### Occupant State During Flight

While in flight, occupants are:
- Untargetable (like SK-60 Bunker occupants)
- Cannot act (unlike SK-60 Bunker where occupants can shoot)
- Position is tied to the transport (they're inside it)
- Not individually visible on the map (only the transport is visible)

### Landing and Ejection

On arrival:
1. Transport lands at destination
2. All occupants are removed from the transport
3. Occupants are placed at positions around the landing point
4. Occupants resume normal entity state (targetable, can act)
5. Transport despawns

On destruction mid-flight:
1. Transport is destroyed at its current position
2. All occupants are ejected at the crash position
3. Occupants take a brief stun (0.5s crash recovery)
4. No damage from the crash (or minor damage — design choice)

### Global Range Movement

The transport can fly to any point on the map. This means it will cross MANY Arbiter boundaries during flight. The transport entity must be handed off repeatedly as it traverses the map — potentially crossing 5-10 Arbiter boundaries in a single flight.

Each handoff carries the transport entity AND all its occupant data. The occupants themselves are not in the entity map during flight — they're serialized inside the transport.

## Cross-Boundary Concerns

TODO: This is the most boundary-intensive sketch yet (alongside SK-68 Multi-Entity):

1. **Multi-boundary traversal:** The transport flies across the entire map. It crosses every Arbiter boundary in its path. Each crossing is an entity handoff for the transport.

2. **Occupants during handoff:** Occupants are stored inside the transport (like SK-54 Entity Consumption). They transfer with the transport. No individual occupant handoffs during flight.

3. **Destination on different Arbiter:** The flight origin and destination are almost certainly on different Arbiters. The transport starts on Arbiter A, flies across B, C, D, and lands on Arbiter E. On landing, occupants materialize on Arbiter E.

4. **Occupant session routing:** Occupants' Edge Nodes need to know they're in transit. They don't receive game state updates during flight (untargetable, can't act). On landing, their Edge Nodes must be redirected to Arbiter E.

5. **Transport shot down:** If destroyed mid-flight on Arbiter C, occupants materialize on Arbiter C. Their Edge Nodes redirect to C.

6. **Flight path and R-Tree:** The transport moves in a straight line through potentially many R-Tree cells. The Controller doesn't manage the transport's flight (it's not a topology operation). The transport uses standard entity handoff at each boundary.

## Compiler Requirements

TODO: Designer specifies: summon transport at caster position, allies enter (max 4 + caster), caster selects global destination, transport flies at speed X, occupants untargetable + can't act during flight, transport has HP (destructible), on arrival eject all, on destruction eject + stun. Compiler produces:
- TransportActor entity with state machine (Loading → InFlight → Landing / Destroyed)
- Occupant storage (serialized entity list, like SK-54)
- Entry interaction (like SK-60 Bunker)
- Flight movement (per-tick position update toward destination)
- Landing action: deserialize occupants, place at destination
- Destruction action: deserialize occupants, place at crash position + stun
- Global destination selection input

The most complex entity lifecycle in the sketch set — it combines: enterable structure (SK-60) + entity consumption/storage (SK-54) + global movement + multi-boundary traversal + conditional ejection.

## Open Questions

- Can the transport be healed by allies during flight?
- Can enemies see the transport's destination (flight path indicator)?
- Is the transport affected by CC (stunned mid-flight = stops moving)?
- Can the caster cancel the flight and land early?
- Can allies exit voluntarily during flight?
- Does the transport interact with SK-03 Terrain Wall (blocked or flies over)?
- If the transport lands on SK-32 Minefield, do mines detonate on the occupants?
- Can the transport carry non-player entities (SK-06 summons)?
- Does the transport count as one entity or N+1 entities for entity_count?
- Performance: rapid boundary crossings during flight — how many handoffs per second at max speed?
- How does the transport interact with the Warm Pool / Arbiter split triggers as it passes through regions?
- Can two transports collide in flight?
