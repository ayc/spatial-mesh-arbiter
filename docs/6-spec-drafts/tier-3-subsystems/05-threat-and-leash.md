# T3-05: Threat Table & Leash Mechanics

> **Status:** OPEN
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/04-npc-and-world-interaction.md`

## Problem Statement

NPC archetypes reference aggro, threat tables, and leash mechanics but no formulas are provided:

1. **Threat formula:** How does damage/healing translate to threat? (1:1? Multiplied by role? Flat threat from taunts?)
2. **Threat decay:** Does threat decay over time? Per tick? Only out of combat?
3. **Recent damage window:** "Recent damage/heal aggro rules" — what is "recent"? (ticks? seconds?)
4. **Leash boundary:** How is leash range calculated? From spawn point? From patrol path?
5. **Leash restoration:** When a leashed NPC returns, does HP reset? Threat table clear? Evade state duration?
6. **Boss tie-breakers:** For boss encounters with multiple threat targets, what breaks ties?

## Questions to Resolve

- [ ] Threat formula: `threat = damage * threat_multiplier + flat_threat`?
- [ ] Healing threat multiplier
- [ ] Threat decay rate
- [ ] Leash distance (from spawn? From patrol waypoint?)
- [ ] Leash return behavior (HP reset? Invulnerable during return?)
- [ ] Boss aggro table: sorted by threat? With swap threshold (e.g., must exceed current target by 10%)?

## Proposed Resolution

_To be drafted._

## References

- `docs/3-gameplay-systems/04-npc-and-world-interaction.md` — NPC archetypes, state machines
- `docs/1-architecture/02-npc-architecture.md` — Runtime tiers, AI Node archetypes
