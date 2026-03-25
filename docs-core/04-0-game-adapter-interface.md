# Game Adapter Interface

This document is **conceptual and explanatory**. It introduces the engine/game adapter boundary at a high level. For normative requirements, see:

1. `04-1-game-adapter-contract.md` (behavior contract — 12-stage pipeline, ownership rules, failure handling)
2. `04-2-game-adapter-api-contract.md` (strict API shapes — hook envelopes, payload types, startup negotiation)
3. `04-3-version-line-transition-contract.md` (rollout/rollback contract)

## 1. Purpose

The game adapter provides all game-specific meaning. The engine provides deterministic spatial runtime behavior. Neither side reaches into the other's domain.

The adapter is not a plugin with arbitrary access to engine internals. It is a **declarative responder**: the engine calls the adapter at defined points in the tick lifecycle, the adapter returns structured outcomes (mutations, events, deferred events), and the engine applies those outcomes through its own pipeline.

## 2. Engine-Owned vs Game-Owned

**Engine-owned** (adapter MUST NOT mutate directly):
- Time, space, authority, topology, transport safety
- Deterministic execution constraints and tick scheduling
- Entity identity allocation and R-Tree spatial placement
- Handoff, replay, and idempotency mechanisms
- Input routing commitment (Stage 1 outcomes are committed by the engine)
- Downstream payload serialization (Stage 12 outcomes are serialized by the engine)

**Game-owned** (adapter defines and controls via declarative outcomes):
- Action taxonomy and validation semantics
- Combat resolution logic and mutation meaning
- Content schemas, balancing data, and formula registries
- Progression, economy, social, and NPC behavior semantics
- Entity life-phase definitions (downed state, form transformation)
- Reactive hook behavior (on-hit, on-death, on-cast intercept)

## 3. Adapter Hook Surface (API v2)

The adapter implements four hooks. Two are called each tick (`validate_intent`, `dispatch_stage`), one is called at spawn time (`initialize_spawn_configuration`), and one at startup (`describe_compatibility`).

| Hook | When Called | Purpose |
|------|-----------|---------|
| `validate_intent` | Stage 2 of each tick, once per incoming intent | Determine whether a player/AI intent is legal. Returns accept or reject. |
| `dispatch_stage` | Stages 1 and 3-12 of each tick | Unified entry point for all non-validation game logic. Called once per active stage with a batch of entities that have work for that stage. |
| `initialize_spawn_configuration` | When a P-32 Actor Spawning directive fires | Provide game-specific initial state for a newly spawned entity. The engine allocates the entity ID; the adapter returns configuration. |
| `describe_compatibility` | At startup, during admission negotiation | Report the adapter's identity, version, and supported schema descriptors so the engine can validate compatibility. |

The legacy v1 hooks (`resolve_external`, `resolve_internal`) are deprecated.

## 4. The 12-Stage Tick Lifecycle

The engine executes each authoritative tick as a strictly ordered 12-stage pipeline. The adapter participates in 11 of these stages (Stage 2 via `validate_intent`, the rest via `dispatch_stage`).

```
 1. ControlAuthorityAndInputRouting  — who controls whom
 2. IntentValidation                 — is this action legal? (via validate_intent)
 3. TargetResolution                 — who does this affect?
 4. PreKinematic                     — movement modifiers (roots, slows, steering)
 5. KinematicResolution              — execute movement
 6. PostKinematic                    — position consequences (proximity, clamping)
 7. PreMitigation                    — combat interception (shields, immunity)
 8. DamageResolution                 — combat math
 9. PostDamage                       — reactive hooks (on-hit, on-damage-received)
10. DeathCheck                       — life-phase transitions
11. StateUpdate                      — timers, counters, accumulators
12. ObserverScopedPayloadEmission    — downstream payload filtering
```

The engine owns the stage scheduler. It calls the adapter for each stage, collects declarative outcomes, and applies them before advancing to the next stage. Four stages have **engine commit boundaries** where the engine applies adapter outcomes to its own state: after Stage 1 (input routing), after Stage 5 (spatial positions), after Stage 10 (entity removal/respawn), and after Stage 12 (downstream payload serialization).

## 5. Declarative Outcome Model

The adapter never mutates engine state directly. Every hook returns a structured outcome object:

- **`StageOutcome`** — mutations to apply, events to emit immediately, events to defer to the next tick, and non-fatal faults to log.
- **`TerminalOutcome`** — accept or reject disposition for an intent, with optional game payload.
- **`SpawnConfiguration`** — initial entity state, replication cadence, and lifetime for a new entity.

All game-defined payloads crossing the boundary use `SchemaTypedPayload` wrappers with negotiated `(payload_type_id, schema_version)` pairs, ensuring both sides agree on the data format.

## 6. Data Contract

1. Engine core entity fields (position, velocity, entity ID, team ID) are fixed and always present.
2. Game extension state is opaque to the engine except for serialization/transport — the engine carries it but does not interpret it.
3. Game data assets (compiled game images) are versioned and distributed through engine data-epoch mechanisms. Activation is atomic at frame boundaries.

## 7. Compatibility Contract

1. Game adapter changes must obey wire/data compatibility strategy.
2. Engine and adapter versions negotiate compatibility explicitly at startup via the `describe_compatibility` / `ENGINE_HELLO` / `ADAPTER_HELLO` handshake.
3. Mixed-game runtime meshes are out of scope; one deployed stack hosts one game adapter.
4. Version-line transitions (upgrades, rollbacks) follow `04-3-version-line-transition-contract.md`.
