# Spatial Mesh Arbiter - LLM Orientation

Welcome to the Spatial Mesh Arbiter codebase. You are an AI assistant and senior system architect helping to build a lock-free, 60Hz deterministic distributed game engine in Rust, designed for massive scale (4k+ players) MMO-ARPG environments. 

This is a multi-million dollar architecture. Accuracy and strict adherence to the specs are non-negotiable.

## 🚨 CRITICAL RULES FOR LLMs (READ FIRST) 🚨

1. **DO NOT SKIM OR HALLUCINATE ARCHITECTURE:** The high-level markdown files (e.g., `docs/README.md`) contain idealized summaries. **The absolute source of truth is the Rust code and the internal contracts.**
2. **VERIFY WITH STRUCTS:** Before explaining how a system works, proposing a solution, or writing code, you MUST read the exact Rust structs in `docs/2-contracts-and-interfaces/internal-mesh-types/`. If you do not read the structs, you will misunderstand the system.
3. **READ WHOLE FILES:** If you use a tool to read a file and it truncates, you MUST paginate through the rest of the file using `start_line` and `end_line` before drawing conclusions.
4. **CITE YOUR SOURCES:** When answering architectural questions, cite the specific Rust struct names (e.g., `ActionProposal`, `CombatContext`, `SoftState`) and the markdown files where they are defined.

---

## 1. Core Components & Trust Boundaries

The engine operates on a strict Spatial Actor Model.

*   **Client (Zero-Trust):** A "dumb terminal" tasked solely with rendering visuals and capturing raw inputs. It sends structured **Client Intents** (e.g., `DiscreteIntent::TargetedAbility`), *never* raw WASD streams for server integration, and *never* authoritative outcomes (e.g., "I hit X for 10 damage").
*   **Edge Node / Proxy Actor (Gateway):** A Trusted Headless Client deployed at the network edge. It performs anti-cheat validation, translates intents into formal **`ActionProposals`**, and provides immediate client-side prediction (`EdgeAck`). It **does not** perform final combat mitigation math.
*   **Mesh Arbiter / Spatial Actor (Authority):** The core of the engine. A lock-free, single-threaded deterministic physics loop running strictly at 60Hz. It owns a specific 2D spatial region (R-Tree node) and exclusively mutates the `SoftState` of entities within that region. 
*   **Mesh Controller (Control Plane):** A highly consistent (Raft) cluster that dictates the R-Tree topology (splits/merges), synchronizes the global shard tick ("The Metronome"), and routes high-radius Global Events.
*   **Meta Services:** Eventual-consistency services (Inventory, Social, Persistence). The Arbiter communicates with Meta asynchronously via a Redis Streams Event Bus (emitting `HardEvent`s like `PlayerDied` or `LootSpawned`).

---

## 2. Data Flow & The Two-Phase Combat Pipeline

Because an attacker and defender might exist on two completely different physical server nodes (Arbiters), combat is strictly asynchronous and divided:

1.  **The Intent:** Client sends `DiscreteIntent` to the Edge.
2.  **The Proposal:** Edge validates and sends `ActionProposal` to the attacker's Host Arbiter.
3.  **Phase 1 (Pre-Roll / Offense):** The attacker's Arbiter evaluates the proposal against the attacker's `OffensiveStats` and generates a `CombatContext` (rolling crits, calculating base damage, armor penetration). 
4.  **The Relay:** If the target is a "Ghost" (owned by a neighboring Arbiter), the attacker's Arbiter wraps the `CombatContext` in an internal envelope (`MeshInternalEvent::InternalPreparedHit`) and sends it over RUDP to the target's owner.
5.  **Phase 2 (Resolution / Defense):** The target's Arbiter evaluates the `CombatContext` against the target's `DefensiveStats` (applying resistances, block, evasion, weight vs. knockback) and finally mutates the target's `SoftState` (HP).

---

## 3. Strict Engineering Constraints

If you write code for this engine, you must adhere to these absolute rules:

*   **NO FLOATING POINT MATH:** `f32` and `f64` are strictly forbidden in the simulation loop. Because Arbiters use WAL-streaming to "fast-forward" state during splits/merges, math must be perfectly deterministic across different CPU architectures. **You must use the `SimFixed` type (`I32F32` via the `fixed` crate).**
*   **Saturating Arithmetic:** All fixed-point math must use saturating variants (`saturating_mul`, `saturating_add`) to prevent panics or silent wrapping overflows.
*   **The 60Hz Metronome:** The Arbiter's `tick()` loop runs at 60Hz, period. It does not skip frames or slow its tick rate under load.
*   **Lock-Free Mutability:** Actors share no memory. Concurrency is achieved through spatial jurisdiction, not mutexes. 
*   **Token-Bucket Ingress:** Every `ActionProposal` hitting the Arbiter is gated by a per-entity token bucket to isolate spammy/malicious sessions and prevent queue saturation.

---

## 4. Core Engine Mechanics

*   **Ghost Entities:** Lightweight, read-only 2D projections of entities that exist near the Arbiter's borders but are owned by neighboring Arbiters. They are synchronized via UDP dead-reckoning and are used strictly for local raycasting and collision. They do not receive direct damage (they trigger the `ImpactEvent` relay).
*   **Ephemeral Actors (Projectiles):** Projectiles are *not* zero-width hitscan raycasts. They are independent structs (`ProjectileActor`) with their own `tick()` loop. If a projectile crosses a server boundary, it executes a rigorous 3-phase handoff protocol (`Prepare` -> `Ack` -> `Commit`) over Reliable-UDP.
*   **Kinematic Dilation (KiDi):** The engine's defense against "Blackhole" density events (e.g., 4,000 players in one room). Instead of dropping server ticks, the Arbiter calculates a `dilation_factor` (e.g., 0.2x). The server still runs at 60Hz, but entities move, cast, and recover slower—like wading through a "Temporal Swamp."

---
*End of Orientation*