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

### Illusory Entity

The decoy is an entity that **appears identical to the caster for enemy clients** but is functionally minimal:

```
struct DecoyEntity {
    decoy_id: EntityID,
    source_entity_id: EntityID,  // Who the decoy looks like
    hp: SimFixed,                // 1 HP (dies instantly)
    movement_pattern: DecoyAI,
    expires_at_tick: u64,
    fake_ability_timer: u64,     // Periodically play fake cast animations
}
```

The decoy needs:
- Same visual model as the source entity
- Same apparent HP bar (shown as full to enemies, regardless of actual 1 HP)
- Movement AI (simple pattern — continue moving, mirror caster, or patrol)
- Fake ability animations (client-side visual effects that deal no damage)

### Per-Team Visual Deception

This is the first ability requiring **different downstream payloads per team**:
- **Enemy Edge Nodes** receive: entity with source entity's model, fake full HP bar, normal entity data
- **Ally Edge Nodes** receive: entity with a "decoy" flag, allowing the client to render a subtle indicator

The Arbiter must generate DIFFERENT state updates for the same entity based on the recipient's team. This is a new capability — all existing downstream payloads are the same for all recipients.

Or alternatively: the decoy looks identical to everyone, and only the CASTER's client knows which is real (simplifies the Arbiter, but allies can't distinguish either).

### Fake HP Bar

The decoy's apparent HP must differ from its actual HP:
- Actual HP: 1 (dies on any damage)
- Displayed HP: matches the caster's current HP percentage (or always full)

The downstream payload for the decoy entity must carry a "display HP" that differs from the actual HP. This is a form of server-side visual deception. Currently, entity HP in downstream payloads is authoritative — clients display what the server sends. The decoy requires the server to lie about HP to enemies.

### Targeting Confusion

The goal of the decoy is to make enemies waste abilities on it. For this to work:
- Auto-targeting (SK-42 Withering Fire) should not be able to distinguish the decoy from the real entity
- Tab-targeting/nearest-hero selection should treat the decoy as a valid hero target
- The decoy must appear in enemy spatial queries as a valid target

The decoy IS a valid target — it just dies in one hit. The deception is visual (looks identical), not mechanical (it can be targeted and hit normally).

## Cross-Boundary Concerns

TODO: The decoy is a standard entity on the caster's Arbiter. Cross-boundary concerns are minimal:
- Ghost updates for the decoy carry its visual data (same model as caster)
- Enemies on neighboring Arbiters see the decoy as a Ghost — same deception applies
- The fake HP bar in Ghost updates or downstream payloads must be team-aware

The unique concern: per-team downstream payloads. If the Arbiter sends state updates to Edge Nodes, and an enemy Edge Node and ally Edge Node are on the same Arbiter (both seeing the decoy as a Ghost), the Arbiter must generate different data for each. This is new — current downstream payloads are entity-centric, not recipient-centric.

## Compiler Requirements

TODO: Designer specifies: spawn decoy (identical appearance to caster), decoy HP (1, displayed as full), movement AI (pattern), fake ability animations, duration (5s), dies on any hit, allies can identify (subtle indicator). Compiler produces:
- Decoy entity definition (1 HP, source_entity_id for visual copying)
- Movement AI definition (simple pattern)
- Fake ability animation schedule
- Per-team visual deception rules (display HP, decoy indicator for allies)
- Expiry timer + instant death on any damage

The compiler needs to support **per-team entity presentation** — different visual/data representations of the same entity based on the viewer's team affiliation.

## Open Questions

- Does the decoy inherit the caster's current buffs/debuffs visually (enemies see buff icons)?
- Can the decoy trigger SK-32 Minefield (walks over a mine, mine detonates on the 1-HP decoy)?
- Does the decoy benefit from SK-08 Aura (caster's aura applies from the decoy's position)?
- Can SK-42 Withering Fire's auto-target distinguish the decoy from the real entity?
- If the caster has SK-04 Tether active, does the tether visual connect to the decoy or the real caster?
- Can the decoy be healed by allies (healing a 1-HP entity)?
- Can the decoy use SK-69 Portal Pair (enter a portal)?
- Does the decoy block pathing (enemies walk around it)?
- Can the decoy be CC'd (stun the decoy — wastes the stun)?
- How does the fake HP bar interact with SK-14 Execute Threshold (enemy sees "full HP" but the decoy is actually at 1 HP)?
