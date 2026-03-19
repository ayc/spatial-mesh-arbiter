# 8. Visibility & UI Primitives

*How the engine controls what players see and interact with beyond combat.*

---

### P-52: Asymmetric Team-Rendering

**Description:** A flag system that makes an entity invisible or differently-rendered based on the observer's team affiliation.

**Sketches:** SK-86 (Decoy — real entity hidden, decoy visible to enemies), SK-36 (Shadow Step — invisible during dash)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The per-entity visibility flags are a bitmask indexed by team ID: `visible_to_team[team_id] = bool`. The Arbiter evaluates these flags when building downstream payloads — an entity invisible to a team is excluded from that team's Edge Node updates. This is distinct from P-27 (Targetability) — an invisible entity may still be targetable by AoE (or not, design choice). The flags are SoftState and have bounded lifetime.

---

### P-53: Entity Suspension

**Description:** Removing an entity from all spatial, targeting, and rendering systems while preserving its existence in memory.

**Sketches:** SK-58 (Cocoon — swallowed entity), SK-91 (Team-Agnostic Stasis — frozen entity)

**Engine layer:** `docs-core/`

**Dependencies:** P-33 (Entity Dormancy) — suspension is dormancy plus rendering removal.

**Key constraints:** A suspended entity is not in the R-Tree, not in downstream payloads, not targetable, and not evaluated. It exists only as a state blob in memory. On un-suspension, the entity is re-inserted into the R-Tree at its preserved position. Status effect timers may pause during suspension (stasis) or continue (design choice). The suspension is bounded in duration.

---

### P-54: Group Choice Aggregator

**Description:** A synchronized UI mechanism that collects inputs from N players and pattern-matches them to a combined result.

**Sketches:** SK-124 (Group Sequential Combo), SK-125 (Group Simultaneous Input)

**Engine layer:** `game-adapter`

**Dependencies:** P-46 (Global Event Scheduler) — if the group spans Arbiters, coordination requires Controller involvement.

**Key constraints:** The aggregator has a deadline tick and a set of expected participants (by entity ID). Each participant submits one input (from a bounded option set). Missing inputs at deadline are filled with a default. The combination is evaluated via a game-defined lookup table: ordered patterns (specific sequence = special result) checked first, then unordered count distribution (generic result). The result is a group-wide effect applied to all participants. The aggregator state lives on one Arbiter; cross-Arbiter participant inputs are relayed.

---

### P-55: Concentration Intercept

**Description:** A combat-pipeline hook that forces a deterministic RNG check on the maintaining entity whenever it takes damage, potentially breaking a maintained effect.

**Sketches:** SK-123 (Concentration)

**Engine layer:** `game-adapter`

**Dependencies:** P-36 (On-Damage-Received Hook) — the concentration check is triggered by the damage-received hook.

**Key constraints:** The RNG is deterministic (seeded by entity ID + tick + "concentration" salt). The difficulty scales with damage taken (e.g., DC = max(10, damage / 2)). On failure, the concentrated effect is removed — this may require a cross-boundary relay if the effect is on a different entity/Arbiter. Only one concentration effect per entity at a time (mutual exclusion enforced at cast time). Concentration is distinct from channeling: the entity can move and use non-concentration abilities freely.
