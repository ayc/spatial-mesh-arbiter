# Spatial Mesh Arbiter Documentation

Welcome to the Spatial Mesh Arbiter engine documentation. This project is a large-scale, lock-free, 2D distributed multiplayer game engine designed to solve the "Blackhole" density problem without relying on generic distributed locks or heavy time-travel buffers.

## Developer-First Organization

The documentation is organized to support the lifecycle of developers and systems engineers working on the engine:

### [0. Getting Started](0-getting-started/)
Start here to set up your environment, understand the development lifecycle, and read the implementation blueprints.
* [01. Quick Start & Local Environment](0-getting-started/01-quick-start.md)
* [02. Implementation Phases & Mandates](0-getting-started/02-implementation-phases.md)

### [1. Architecture](1-architecture/)
Core theoretical foundation and engine design for the Spatial Actor Model.
* [01. Core Concepts and Mesh](1-architecture/01-core-concepts-and-mesh.md)
* [02. NPC Architecture](1-architecture/02-npc-architecture.md)

### [2. Contracts & Interfaces](2-contracts-and-interfaces/)
The API and definitive "Source of Truth" for wire protocols and message types.
* [01. Client-Edge Wire Protocol](2-contracts-and-interfaces/01-client-edge-wire-protocol.md)
* [02. Intent Taxonomy](2-contracts-and-interfaces/02-intent-taxonomy.md)
* [Internal Mesh Types](2-contracts-and-interfaces/internal-mesh-types/) (Core primitives, envelopes, state)

### [3. Gameplay Systems](3-gameplay-systems/)
Data-driven systems used to build spells, abilities, and RPG stats.
* [01. RPG Mechanics](3-gameplay-systems/01-rpg-mechanics.md)
* [02. Ability Framework](3-gameplay-systems/02-ability-framework.md)
* [03. Global Events](3-gameplay-systems/03-global-events.md)
* [04. NPC and World Interaction](3-gameplay-systems/04-npc-and-world-interaction.md)

### [4. Infrastructure](4-infrastructure/)
Guides on how the engine is containerized, scaled, and configured.
* [01. Deployment & Orchestration](4-infrastructure/01-deployment-and-orchestration.md)
* [02. Configuration Registry](4-infrastructure/02-configuration-registry.md)

### [5. Testing & Conformance](5-testing-and-conformance/)
Scenarios for proving the distributed mesh behaviors locally.
* [01. Mini-Mesh Conformance](5-testing-and-conformance/01-mini-mesh-conformance.md)
