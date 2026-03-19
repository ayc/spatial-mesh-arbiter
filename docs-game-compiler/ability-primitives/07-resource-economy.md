# 7. Resource & Economy Primitives

*Advanced resource systems beyond HP and mana.*

---

### P-47: Spatial Corpse Registry

**Description:** Tracking the location and "stat-ghost" of dead entities as consumable spatial resources.

**Sketches:** SK-54 (Entity Consumption), SK-107 (Corpse Possession), SK-115 (Corpse Economy)

**Engine layer:** `game-adapter`

**Dependencies:** P-39 (On-Death Hook) — corpses are spawned by the death hook. P-11 (N-Nearest Neighbor) — abilities query for nearest corpses.

**Key constraints:** Corpse entities are lightweight — they carry position, source entity stats (max HP, level), creation tick, and expiry tick. They do not participate in the 60Hz evaluation loop. Corpse consumption is atomic (first-claim-wins) to resolve contention between multiple consumers. The corpse count per Arbiter is bounded. Corpses are local to the Arbiter where the entity died — cross-boundary corpse consumption is not supported.

---

### P-48: Secondary "Stagger" Bar

**Description:** A parallel health track that accumulates specialized damage and triggers a vulnerability state on depletion.

**Sketches:** SK-117 (Stagger Bar)

**Engine layer:** `game-adapter`

**Dependencies:** P-26 (Capability Bitmask) — the stagger state disables actions. P-16 (Stat Layering) — the vulnerability bonus is a damage-taken modifier.

**Key constraints:** The stagger bar is an optional entity component (typically bosses/elites only). Every ability carries a `stagger_damage` value alongside its `hp_damage`. Stagger damage is resolved in parallel with HP damage but through a separate pipeline (may have its own mitigation rules). On depletion: entity enters a timed stagger state (stun + damage vulnerability). The bar regenerates after a delay if not depleted. Regeneration rate and delay are per-entity configuration.

---

### P-49: Resource Destruction-to-Damage Scalar

**Description:** A combat modifier that converts the amount of a secondary resource destroyed into bonus damage.

**Sketches:** SK-108 (Mana Burn — mana destroyed = bonus damage)

**Engine layer:** `game-adapter`

**Dependencies:** P-21 (Value Conversion) — the conversion mechanic. P-15 (Value Modification) — the bonus damage application.

**Key constraints:** The resource being targeted (mana, energy, etc.) must be part of entity state and externally modifiable. The scalar is a `I32F32` ratio (e.g., 1.0 = 1 damage per 1 mana destroyed). The resource destruction is resolved on the target's Arbiter (where the resource is authoritative). The bonus damage flows through standard damage resolution (shields, mitigation apply).

---

### P-50: Typed Multi-Charge Pool

**Description:** An accumulator that tracks the sequence and type of charges rather than just a count, enabling composition-based finisher logic.

**Sketches:** SK-116 (Charge-Finisher — Fire/Lightning/Cold charges), SK-59 (Oil-Ignite — element type interaction)

**Engine layer:** `game-adapter`

**Dependencies:** P-42 (Stacking Counters) — the charge pool is a specialized form of stacking counter with type tags.

**Key constraints:** The pool stores an ordered list of `(charge_type, added_at_tick)` entries up to a max count. Finisher abilities read the charge composition (not just count) to determine their effect. The charge types are an enum defined at compile time. The pool decays as a unit (all charges lost on timeout, not one at a time). The pool is per-entity SoftState and transfers on handoff.

---

### P-51: Desperation Cost Modifiers

**Description:** Stacking multipliers on an ability's base resource cost that accumulate with repeated use and decay over time.

**Sketches:** SK-97 (Escalating Cost)

**Engine layer:** `game-adapter`

**Dependencies:** P-42 (Stacking Counters) — the cost multiplier is a stack-based counter.

**Key constraints:** Each cast of the ability increments the cost multiplier stack. The multiplier scales the base cost (e.g., base 10 mana &times; 1.5^stacks). Stacks decay individually over time (e.g., one stack removed every 8 seconds). If the entity cannot afford the escalated cost, the ability is unavailable. The cost check happens in `validate_intent` (Phase 1) using the current stack count.
