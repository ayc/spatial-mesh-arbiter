# 4. Entity State & Capability Primitives

*How the engine limits what an entity is allowed to do.*

---

### P-26: Capability Bitmask

**Description:** Independent boolean flags controlling what actions an entity is permitted to perform — `CAN_MOVE`, `CAN_CAST`, `CAN_ATTACK`, `CAN_USE_ITEMS`, `PASSIVES_ACTIVE`.

**Sketches:** SK-24 (Stun — all flags false), SK-25 (Root — CAN_MOVE false), SK-26 (Silence — CAN_CAST false), SK-27 (Sleep — all flags false, broken on damage), SK-50 (Blind — CAN_ATTACK miss chance), SK-51 (Unstoppable — immunity to flag changes), SK-102 (Disarm — CAN_ATTACK false), SK-110 (Mute — PASSIVES_ACTIVE false), SK-121 (Downed State — reduced capabilities)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The bitmask is checked in the `validate_intent` phase (Phase 1) before any ability resolution. Multiple sources can set the same flag — the flag remains false until ALL sources expire (reference counting or "most restrictive wins"). The `PASSIVES_ACTIVE` flag suspends (not removes) passive effects; they resume when the flag is restored.

---

### P-27: Targetability Overrides

**Description:** Removing an entity from spatial queries entirely, making it untargetable by abilities and auto-attacks.

**Sketches:** SK-44 (Burrow), SK-86 (Decoy — real entity becomes untargetable), SK-100 (Ally Untargetable)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** An untargetable entity is excluded from P-09 (Shape Overlap Query) and P-11 (N-Nearest Neighbor) results. The entity still exists in the R-Tree but is filtered out of targeting queries via a flag check. Untargetable entities may or may not be visible (separate from P-52 rendering). AoE effects that already resolved do not retroactively miss.

---

### P-28: Hostility Inversion

**Description:** Forcing an entity to treat allies as enemies or enemies as allies for the purpose of targeting and damage resolution.

**Sketches:** SK-106 (Berserk — forced friendly fire)

**Engine layer:** `game-adapter`

**Dependencies:** P-13 (Tag/Allegiance Filtering) — the inversion modifies the filtering rules for the affected entity.

**Key constraints:** The inversion is a status effect with a duration. While active, the entity's auto-attacks and abilities target allies instead of enemies (or both). The inversion does not change the entity's team ID — it only inverts the targeting filter. On expiry, normal targeting resumes.

---

### P-29: Control Authority Swap

**Description:** Disconnecting the Edge Node's input stream from an entity and routing another player's inputs to it.

**Sketches:** SK-40 (Mind Control), SK-67 (Entity Clone), SK-81 (Remote Control Summon)

**Engine layer:** `docs-core/`

**Dependencies:** P-34 (Persistent Linkage) — the control link between controller and controlled entity. P-26 (Capability Bitmask) — the original controller's entity may be locked during the swap.

**Key constraints:** Only ONE entity can control another at a time. The controlled entity's Edge Node receives a "control suspended" signal. The controlling player's Edge Node receives dual input targets. On expiry or break, control reverts. The swap must be atomic within a single tick to prevent split-brain input.

---

### P-30: Input Multiplexing

**Description:** Routing one player's inputs to multiple entities simultaneously, or routing multiple players' inputs to a single entity.

**Sketches:** SK-68 (Multi-Entity Control), SK-77 (Two-Player Entity)

**Engine layer:** `docs-core/`

**Dependencies:** P-29 (Control Authority Swap) — shares the input routing infrastructure.

**Key constraints:** For one-to-many: the player's movement input is applied to all controlled entities. Ability inputs may target from each entity independently (AI-assisted) or mirror the primary. For many-to-one: input conflict resolution is required (e.g., majority vote on movement direction, or role-based split where one player controls movement and another controls abilities).

---

### P-31: Identity/Loadout Swap

**Description:** Replacing an entity's `OffensiveStats`, `DefensiveStats`, and `SpellData` pointers at runtime, effectively transforming it into a different character.

**Sketches:** SK-57 (Form Transformation), SK-121 (Downed State — ability set swap)

**Engine layer:** `game-adapter`

**Dependencies:** None.

**Key constraints:** The swap is atomic within a single tick. The entity's position and entity ID are preserved — only the stat block and ability set change. Cooldowns may or may not transfer (design choice per ability). The swap can be triggered by P-39 (On-Death Hook) for death-form transformations. The original loadout is stored for reversion.

---

### P-32: Actor Spawning

**Description:** Instantiating logic-driven `ProjectileActors` or `ZoneActors` as new entities in the R-Tree.

**Sketches:** SK-06 (Summon Swarm), SK-32 (Minefield), SK-67 (Entity Clone), SK-81 (Remote Control Summon), SK-86 (Decoy)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Each spawned actor has a bounded lifetime and consumes an entity slot on the Arbiter. The spawner's Arbiter is the initial authority. Spawned actors carry an `OwnerID` linking them back to the spawning entity. The total number of actors per owner is bounded (e.g., max 8 summons) to prevent entity explosion. Actors with AI follow the standard 60Hz evaluation loop.

---

### P-33: Entity Dormancy

**Description:** Pausing an entity's 60Hz evaluation loop while preserving its state in memory — the entity exists but does not act or react.

**Sketches:** SK-58 (Cocoon), SK-91 (Team-Agnostic Stasis)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** A dormant entity is skipped during tick evaluation (no movement, no ability resolution, no passive ticks). Status effect timers may or may not pause during dormancy (design choice). The entity remains in the R-Tree but is flagged to skip processing. Dormancy is distinct from P-27 (Targetability) — a dormant entity may or may not be targetable.

---

### P-34: Persistent Linkage (Bindings)

**Description:** Registering a two-way dependency graph between entities that survives Arbiter handoffs and is cleaned up when either entity dies or the link expires.

**Sketches:** SK-04 (Tether), SK-66 (Symbiote), SK-111 (Soulbind), SK-34 (Persistent binding between charge pin entities)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Each binding has a type, two entity IDs, and an optional max-distance. Bindings are stored as SoftState on both entities and replicated during handoff. When one entity hands off to a new Arbiter, the binding is maintained via cross-Arbiter relay. When either entity dies, all its bindings are cleaned up. The binding count per entity is bounded.

---

### P-66: Status Effect Filter Mutation

**Description:** Filtering and mutating an entity's active status registry by compiled metadata,
enabling cleanse, dispel, selective status consumption, and status-application immunity checks.

**Sketches:** SK-15 (Purify), SK-95 (Mass Effect Detonation)

**Engine layer:** `game-adapter`

**Dependencies:** P-16 (Stat Layering), P-26 (Capability Bitmask), P-44 (Pulse Timer) — the registry entries being filtered may carry stat modifiers, capability flags, and periodic payloads.

**Key constraints:** Matching is driven by compiled status metadata (`polarity`, `is_cleansable`,
explicit `status_id`, and optional source/applier identity filters), never by ad hoc runtime string
tags. Bulk removal is atomic on the target's authoritative Arbiter: compute the match set from the
current `active_status_effects`, remove all matches, then apply any follow-up status additions or
deferred consume payloads from the same ability. Crowd control effects emitted via `apply_cc`
participate by compiling to generated negative status entries with their own `is_cleansable` flag.
Admission-time immunity is represented as an active status with `status_application_immunity`;
before any new status is inserted, the runtime checks active immunities and rejects blocked matches
deterministically. Neutral/system statuses are ignored by polarity-targeted cleanse unless the
compiler explicitly emits `polarity = all`.
