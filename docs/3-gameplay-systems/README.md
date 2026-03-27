# ARPG Template — Reference Game Layer Implementation

The documents in this directory are the **reference implementation** of the Spatial Mesh Engine's game layer traits, not engine specification.

They define the game-specific logic for a Diablo/Path of Exile-style ARPG MMO: stat systems, combat formulas, ability framework, NPC behavior, and world interaction. A different game genre (MOBA, survival, RTS) would provide different implementations of the same engine traits.

For the engine/game boundary and trait interfaces, see [Framework Boundary](../1-architecture/07-framework-boundary.md).

## Contents

| Document | Implements |
|:---------|:-----------|
| `01-rpg-mechanics.md` | `GameEntity::SoftExt`, `GameEntity::OffenseExt`, stat compilation, combat formulas |
| `02-ability-framework.md` | `GameActions::Action` variants plus the game-layer logic surfaced through `GameAdapter::validate_intent()` and `GameAdapter::dispatch_stage()` |
| `03-global-events.md` | Global event escalation and resolution patterns |
| `04-npc-and-world-interaction.md` | `GameNpcArchetype` implementations, interaction validation |
