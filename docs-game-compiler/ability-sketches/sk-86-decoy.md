# SK-86: Decoy

## Designer Intent

I spawn an illusory copy of myself. The decoy looks identical to me from the enemy's perspective — same model, same health bar, same name. The decoy mimics my recent movement pattern and can even fake-cast abilities (visual only, no damage). Enemies can't tell which is real until they attack — the decoy dies in one hit. I can use this to bait abilities, confuse targeting, and escape.

## Primitive Composition

P-32 (Actor Spawning) → P-52 (Asymmetric Team-Rendering) → P-27 (Targetability Overrides)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- No target (spawns at caster position, or at a target position)

## Observable Behavior

1. Activate — decoy spawns at caster position (or mirrored position)
2. The decoy looks IDENTICAL to the caster from the enemy's perspective
3. The decoy's health bar appears full (fake — it actually has 1 HP)
4. The decoy moves in a pattern (continues last movement direction, or mirrors caster movement)
5. The decoy can perform fake ability animations (visual only, no gameplay effect)
6. Any damage dealt to the decoy kills it instantly (reveals it was fake)
7. The decoy persists for 5 seconds or until killed
8. Allies can see which is the real one (slight visual indicator for friendlies)
9. Visual: identical to caster for enemies, subtle shimmer for allies

## Engine Primitives Required

Decoy is now a canonical spawned actor plus downstream-only observer-presentation reference.

The recommended lowering is:

1. spawn one short-lived decoy actor with:
   - low actual HP (the reference uses 1 HP)
   - ordinary targetability / collision
   - simple deterministic autonomy or follow behavior
2. author `observer_presentation` on that spawned actor with:
   - `appearance_source = mirror_entity`
   - `source_entity = caster`
   - `enemy_hp_presentation = mirror_source_percent` (or `full` if the design wants that lie)
   - `ally_marker = decoy_indicator`
3. keep fake cast animations and flourish behavior presentation-only; they do not author real combat
   effects

This keeps the mechanic inside existing canonical surfaces:

- the decoy is a normal spawned targetable body
- the deception is downstream-only presentation aliasing
- ally recognition uses the existing `decoy_indicator` marker rather than a bespoke team-UI rule

## Cross-Boundary Concerns

Decoy follows the ordinary spawned-actor and observer-presentation contracts.

1. The decoy itself is just another spawned actor and therefore handoffs / Ghost replication work the
   same way they do for other spawned entities.
2. Observer presentation is evaluated per recipient team when downstream payloads are built, so
   enemy observers can see the mirrored appearance / fake HP while allies receive the decoy marker.
3. Those per-team payload aliases do not change authoritative targeting or damage resolution. Remote
   Arbiters and Edge Nodes still agree on the same underlying decoy entity ID and gameplay state.

## Compiler Requirements

Designer specifies:

- decoy lifetime
- actual HP
- movement/autonomy pattern
- whether enemy HP lies use `full` or `mirror_source_percent`
- whether allies get the decoy indicator

Compiler emits:

- one spawned decoy actor
- ordinary spawned-actor autonomy metadata if the decoy should move
- one `observer_presentation` block mirroring the caster to enemies

Compiler validates:

1. `appearance_source = mirror_entity` always has `source_entity = caster`
2. presentation-only fake HP / model aliases remain in `observer_presentation`, not in
   authoritative stat or HP mutation
3. the decoy remains an ordinary targetable entity unless some other canonical targetability policy
   is also authored

## Resolved Interaction Notes

- Enemies may target, damage, CC, and destroy the decoy normally. The deception is visual, not an
  exemption from gameplay systems.
- Auto-targeting and nearest-target helpers treat the decoy as a valid target if its ordinary
  relation/targetability filters admit it.
- Fake cast behavior in this reference is downstream-only presentation and does not create combat
  payloads, cooldown changes, or threat.
- Because the decoy is an ordinary spawned actor, it may still trigger mines, block pathing, or be
  hit by AoE exactly as its authored targetability/collision policy allows.
