# Game Adapter Interface

## 1. Purpose

The game adapter provides all game-specific meaning while the engine provides deterministic spatial runtime behavior.

Normative requirements are defined in:
1. `04-1-game-adapter-contract.md` (behavior contract)
2. `04-2-game-adapter-api-contract.md` (strict API and negotiation contract)
3. `04-3-version-line-transition-contract.md` (rollout/rollback contract)

## 2. Engine-Owned vs Game-Owned

Engine-owned:
- time, space, authority, topology, transport safety
- deterministic execution constraints
- handoff and replay safety mechanisms

Game-owned:
- action taxonomy and validation semantics
- resolution logic and mutation meaning
- content schemas and balancing data
- progression/economy/social/NPC behavior semantics

## 3. Minimum Adapter Surface

The game adapter must provide:
1. Intent validation hook.
2. External action resolution hook.
3. Internal event resolution hook.
4. Entity extension schema definitions.
5. Serialization compatibility for game-owned payloads.

The engine must provide:
1. Stable call order for adapter hooks.
2. Deterministic RNG and numeric primitives.
3. Transport and routing guarantees.
4. Mutation application and event publication pipeline.
5. Versioned game content distribution: the engine distributes content artifacts to runtime nodes, manages data-epoch versioning, and ensures nodes activate content atomically at frame boundaries before accepting entity authority.

## 4. Data Contract

1. Engine core entity fields are fixed and always present.
2. Game extension fields are opaque to engine logic except serialization/transport.
3. Game data assets are versioned and distributed through engine data-epoch mechanisms.

## 5. Compatibility Contract

1. Game adapter changes must obey wire/data compatibility strategy.
2. Engine and game versions must negotiate compatibility explicitly.
3. Mixed-game runtime meshes are out of scope; one deployed stack hosts one game adapter.
