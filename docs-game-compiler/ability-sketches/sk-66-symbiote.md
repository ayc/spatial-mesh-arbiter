# SK-66: Symbiote

## Designer Intent

I attach to an allied hero from anywhere on the map. While attached, my abilities fire from their position — I can shoot spikes at nearby enemies, shield my host, and spawn a locust. My actual body stays where it was, vulnerable and immobile. I can detach at any time to return to controlling my body.

## Primitive Composition

P-06 (Attached Kinematics) → P-34 (Persistent Linkage) → P-60 (Event Cloning)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity (global range — anywhere on the map)
- Detach input (same ability key to end symbiote)

## Observable Behavior

1. Cast on ally — caster attaches to the host (global range, no distance limit)
2. Caster's body becomes immobile and vulnerable at its current position
3. While attached: caster's ability bar changes to symbiote abilities (Spike Burst, Carapace, Stab)
4. All symbiote abilities fire FROM the host's position, not the caster's position
5. The host can act normally — the symbiote doesn't restrict them
6. The caster sees the host's surroundings (camera follows the host)
7. Detach: caster returns to controlling their body at its original position
8. If the host dies: caster is forcibly detached
9. If the caster's body is killed while symbioted: caster dies (body is vulnerable)
10. Visual: symbiote hat on the host, spike effects emanating from the host

## Engine Primitives Required

### Remote Ability Origin

This is the first ability where the **caster's abilities use a different entity's position as their origin point**. All existing abilities originate from the caster's position. Symbiote breaks this:

```
struct SymbioteState {
    host_id: EntityID,
    caster_body_position: Vec2F,  // Where the body stays
    ability_set: AbilitySetId,    // Symbiote-specific abilities
}
```

When the caster uses an ability while symbioted:
1. The ActionProposal originates from the caster's Edge Node
2. The Arbiter resolves the ability with `origin_position = host.position` instead of `caster.position`
3. Spatial queries (who's in range of Spike Burst) use the host's position
4. Projectiles (Stab) launch from the host's position

The engine needs to support **ability origin override** — a modifier that says "this entity's abilities use entity X's position."

### Body Vulnerability

The caster's body remains in the entity map at its original position. It:
- Cannot move (immobile)
- Cannot attack or cast (all input routed to symbiote)
- CAN be targeted and damaged by enemies
- CAN die — which kills the caster even though they're "somewhere else"

The caster exists as two things simultaneously: a vulnerable body and a remote ability source. The body is like a channeling entity (immobile, vulnerable) but the "channel" produces abilities at a remote location.

### Global Range Attachment

The symbiote can attach to any ally anywhere on the map. This means:
- The host is almost certainly on a different Arbiter than the caster
- All symbiote abilities resolve at the host's position, on the host's Arbiter
- The caster's Edge Node sends input, which the caster's Arbiter translates into ability commands and relays to the host's Arbiter

This is a persistent cross-boundary ability connection — not a one-time relay like damage, but a continuous stream of ability commands from Arbiter A (caster) to Arbiter B (host) for the duration of the symbiote.

### Camera / Vision

The caster's client needs to see the host's surroundings. The Edge Node must receive downstream state updates for the host's area, not the caster's body's area. This is a **vision redirect** — the Arbiter that owns the host must send state updates to the caster's Edge Node as if the caster were there.

## Cross-Boundary Concerns

TODO: This ability is inherently cross-boundary by design. The caster is on Arbiter A, the host is on Arbiter B.

1. **Ability relay:** Every symbiote ability the caster uses must be relayed from A to B. Arbiter B resolves the ability at the host's position using the caster's offensive stats (carried in the relay). This is a per-action cross-boundary relay, not per-tick — only fires when the caster presses an ability.

2. **Vision relay:** The caster's Edge Node needs state updates from Arbiter B's area. Does B send downstream payloads to the caster's Edge Node directly? Or does A proxy them? This is a new data flow — an Edge Node receiving state from an Arbiter it's not spatially associated with.

3. **Body vulnerability:** The caster's body on Arbiter A can be attacked. If the body dies, the symbiote must terminate — Arbiter A sends a death notification to Arbiter B, which terminates the symbiote session.

4. **Host handoff:** If the host crosses a boundary (from B to C), the symbiote must follow. The ability relay destination changes from B to C. The vision source changes from B to C.

## Compiler Requirements

TODO: Designer specifies: global range ally target, attach (caster immobile + vulnerable), symbiote ability set (3 abilities that fire from host position), detach on command or host death or caster death, camera follows host. Compiler produces:
- SymbioteState status effect on caster (host reference, body position, ability set swap)
- Ability origin override: all caster abilities use host.position
- Input routing: caster's Edge Node → caster's Arbiter → relay to host's Arbiter
- Vision redirect: host's Arbiter → caster's Edge Node
- Detach/death hooks: terminate symbiote on detach, host death, or caster body death

## Open Questions

- Can the symbiote abilities trigger on-hit procs using the caster's proc effects?
- Does the symbiote use the caster's offensive stats or the host's?
- Can the host see the symbiote abilities being used (UI indicator)?
- Can enemies see who is symbioted to a host (targeting the body as counter-play)?
- Can multiple symbiotes attach to the same host?
- Does the symbiote persist through SK-44 Burrow on the host (host burrows, symbiote stays)?
- If the host enters SK-60 Bunker, does the symbiote stay attached?
- Can the caster's body be consumed by SK-54 Entity Consumption while symbioted?
- How does the ability relay interact with latency — symbiote abilities at global range have higher latency than local abilities?
- Performance: persistent cross-boundary ability relay + vision redirect for the duration — how much bandwidth?
