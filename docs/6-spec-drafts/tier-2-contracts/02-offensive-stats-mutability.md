# T2-02: OffensiveStats Mutability

> **Status:** RESOLVED (not a gap)
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)

## Audit Result

**This was not a gap.** The spec is explicit and consistent across three documents:

1. **Core Primitives** (`01-core-primitives.md` lines 392-430): "The Arbiter never mutates this struct during gameplay; temporary buffs are layered on top via StatModifier entries on ActiveStatusEffect at cast time."

2. **StatModifier system** (`01-core-primitives.md` lines 326-345): "Modifiers are carried on ActiveStatusEffect and layered on top of the immutable base OffensiveStats/DefensiveStats at evaluation time (Pre-Roll for offense, Resolution for defense). The stored base structs are never mutated."

3. **UpdateEntityStats** (`01-core-primitives.md` lines 553-559): "Pushes updated base stats when equipment or attributes change. The Arbiter atomically overwrites the stored OffensiveStats... Active buff modifiers on ActiveStatusEffect are unaffected — they layer on top of the new base at the next evaluation."

4. **Triggers** (`04-meta-services.md`): Meta pushes UpdateEntityStats on equipment change, level-up, durability threshold crossing, and loot claim.

**The contract is:**
- Base OffensiveStats is immutable *during Arbiter simulation* (never mutated by game logic)
- Meta can *replace* the base atomically via UpdateEntityStats (not a mutation — a wholesale swap)
- Buffs layer on top at evaluation time, never touching the base

This file can be deleted.
