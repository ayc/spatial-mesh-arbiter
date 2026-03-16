# Spatial Mesh Arbiter Documentation

This project is a large-scale, lock-free, 2D distributed multiplayer game engine designed to solve the "Blackhole" density problem without relying on generic distributed locks or heavy time-travel buffers.

## Documentation Structure

The documentation is split into two distinct layers to maintain a clean separation between the reusable engine and game-specific logic.

### 1. [Core Framework (docs-core/)](../docs-core/README.md)
The **authoritative engine contract**. This directory contains the distilled, game-agnostic specs for the Spatial Mesh framework. It defines the rules for time, space, topology, and transport that remain constant regardless of the game being built.
*   **Spatial Runtime Kernel:** Authority, ticks, and R-Tree topology.
*   **Messaging Plane:** Wire envelopes, routing, and idempotency.
*   **Durability Bridge:** Hard vs. Soft state and persistence reconciliation.
*   **Game Adapter Interface:** The trait-based boundary for plugging in game logic.
*   **Conformance Matrix:** The non-negotiable invariants and test scenarios.

### 2. [ARPG Reference Implementation (docs/)](README.md)
The **first concrete implementation** built on top of the framework. These documents describe a Diablo-style ARPG MMO, serving as both a production spec and a reference template for how to implement the Core Framework traits.

#### [Architecture](1-architecture/)
* [01. Core Concepts and Mesh](1-architecture/01-core-concepts-and-mesh.md)
* [02. NPC Architecture](1-architecture/02-npc-architecture.md)
* [03. Mesh Controller](1-architecture/03-mesh-controller.md)
* [04. Meta Services](1-architecture/04-meta-services.md)
* [05. AI Node Protocol](1-architecture/05-ai-node-protocol.md)

#### [Gameplay Systems](3-gameplay-systems/)
* [01. RPG Mechanics](3-gameplay-systems/01-rpg-mechanics.md)
* [02. Ability Framework](3-gameplay-systems/02-ability-framework.md)
* [03. Global Events](3-gameplay-systems/03-global-events.md)
* [04. NPC and World Interaction](3-gameplay-systems/04-npc-and-world-interaction.md)

---

## Developer Quick Start
* [Local Environment Setup](0-getting-started/01-quick-start.md)
* [Implementation Roadmap](0-getting-started/02-implementation-phases.md)
* [Mini-Mesh Failure Drills](5-testing-and-conformance/01-mini-mesh-conformance.md)
