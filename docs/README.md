# Spatial Mesh Arbiter Documentation

Welcome to the Spatial Mesh Arbiter engine documentation. This project is a large-scale, lock-free, 2D distributed multiplayer game engine designed to solve the "Blackhole" density problem without relying on generic distributed locks or heavy time-travel buffers.

Because this is a complex system involving multiple disciplines, the documentation is organized by **Audience and Domain** to help you find what you need quickly.

---

## 1. Architecture & Engine
*Target Audience: Core Engine / Systems / Network Engineers*

Contains the core theoretical foundation, network interfaces, messaging envelopes, and low-level engine design.
*   [01. Core Architecture](1-architecture-and-engine/01-core-architecture.md)
*   [02. Network Interfaces](1-architecture-and-engine/02-network-interfaces.md)

## 2. Gameplay & Design
*Target Audience: Game Designers / Gameplay Engineers*

Covers the data-driven systems used to build spells, abilities, and RPG stats.
*   [01. RPG Mechanics & State](2-gameplay-and-design/01-rpg-mechanics-and-state.md)
*   [02. Ability Framework (Action Payloads)](2-gameplay-and-design/02-ability-framework.md)
*   [03. Global Events (Map-Wide Mechanics)](2-gameplay-and-design/03-global-events.md)

## 3. Infrastructure
*Target Audience: DevOps / Platform / Site Reliability Engineers*

Guides on how the engine is containerized, scaled via Hitless Handoffs, and orchestrated safely in production.
*   [01. Deployment & Orchestration](3-infrastructure/01-deployment-and-orchestration.md)
*   [02. Engine Configuration Registry](3-infrastructure/02-configuration-registry.md)

## 4. Development
*Target Audience: All Developers & QA*

Guides for running and testing the distributed mesh behavior locally.
*   [01. Local Testing Strategy (The "Mini-Mesh")](4-development/01-local-testing-strategy.md)
