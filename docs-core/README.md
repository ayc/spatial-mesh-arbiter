# Core Framework Abstract

This directory is a clean, engine-first abstraction of the project.

It intentionally excludes game-specific systems (economy, loot, classes, quests, etc.) and defines only reusable runtime concepts for massively multiplayer 2D spatial simulation.

## Purpose

- Define the reusable engine contract.
- Isolate spatial runtime rules from game semantics.
- Provide a stable target for multi-game reuse.

## Scope

Included:
- Spatial authority and topology model
- Deterministic runtime loop constraints
- Spatial messaging and routing contracts
- Durability bridge contracts
- Game adapter/plugin boundary
- Core conformance invariants

Excluded:
- ARPG-specific combat formulas and stat models
- Game economy, progression, social systems
- Game-specific NPC archetypes or content schemas

## Document Index

1. [00-scope-and-principles.md](00-scope-and-principles.md)
2. [00-1-core-baseline-profile.md](00-1-core-baseline-profile.md)
3. [01-spatial-runtime-kernel.md](01-spatial-runtime-kernel.md)
4. [01-1-spatial-primitive-catalog.md](01-1-spatial-primitive-catalog.md)
5. [01-2-entity-lifecycle-contract.md](01-2-entity-lifecycle-contract.md)
6. [01-3-entity-relationship-contract.md](01-3-entity-relationship-contract.md)
7. [01-4-dynamic-topology-contract.md](01-4-dynamic-topology-contract.md)
8. [02-spatial-messaging-plane.md](02-spatial-messaging-plane.md)
9. [03-durability-bridge.md](03-durability-bridge.md)
10. [04-0-game-adapter-interface.md](04-0-game-adapter-interface.md)
11. [04-1-game-adapter-contract.md](04-1-game-adapter-contract.md)
12. [04-2-game-adapter-api-contract.md](04-2-game-adapter-api-contract.md)
13. [04-3-version-line-transition-contract.md](04-3-version-line-transition-contract.md)
14. [05-conformance-invariants.md](05-conformance-invariants.md)
15. [05-1-conformance-test-matrix.md](05-1-conformance-test-matrix.md)
16. [05-2-core-conformance-scenario-catalog.md](05-2-core-conformance-scenario-catalog.md)
17. [06-architecture-section-mapping.md](06-architecture-section-mapping.md)
