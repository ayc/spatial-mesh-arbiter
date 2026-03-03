# T3-06: NPC Data Asset Format

> **Status:** OPEN (narrowed after audit)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/02-npc-architecture.md`

## Audit Notes

**Tier assignment and archetype binding ARE specified:**

| Aspect | Status | Source |
|--------|--------|--------|
| Design-time classification mandate | **Specified** — "MUST be declared in the game data asset at design time" | `02-npc-architecture.md` §2.1 |
| Tier defaults per archetype | **Specified** — Full table (LaneCreep→T1, NeutralMonster→T0/T1, BossEncounter→T0, etc.) | `02-npc-architecture.md` §3.1-3.2 |
| Named NPC UUID | **Specified** — `character_id` is persistent UUID assigned at design time | `02-npc-architecture.md` §2.4 |
| Per-archetype orphan TTL | **Specified** — Configurable per NPC archetype in game data asset | `02-npc-architecture.md` §2.5 |
| Stats compilation | **Specified** — `compiled_state` and `compiled_offense` populated from data asset by Meta | `02-npc-architecture.md` §2.4 |

## Remaining Gap (Narrowed)

### 1. Asset File Format
No JSON/binary schema for NPC definitions. What fields? What file extension? What directory?

### 2. Spawn Rules
Wave composition, respawn timing, spawn point assignment, patrol paths — none specified.

### 3. Compilation Pipeline
How does Meta Services convert raw NPC definition files into `compiled_state` and `compiled_offense`?

## Questions to Resolve

- [ ] Schema for NPC definition assets (JSON? Protobuf? Fields?)
- [ ] Spawn rule definition format (location, count, respawn timer, conditions)
- [ ] Patrol path / waypoint format
- [ ] Meta compilation pipeline for NPC stats

## Proposed Resolution

_To be drafted._

## References

- `docs/1-architecture/02-npc-architecture.md` §2.1 — Classification mandate
- `docs/1-architecture/02-npc-architecture.md` §3.1-3.2 — Tier defaults
- `docs/3-gameplay-systems/04-npc-and-world-interaction.md` — Archetype taxonomy
