# 6. Temporal & Accumulator Primitives

*How abilities scale with time or repetition.*

---

### P-41: Diminishing Returns (DR) Tracker

**Description:** A historical registry of CC applied to an entity that reduces the duration of subsequent CC applications of the same category.

**Sketches:** SK-28 (Slow Diminishing Returns)

**Engine layer:** `game-adapter`

**Dependencies:** P-62 (Categorized CC Immunity) — DR categories align with CC immunity categories.

**Key constraints:** The tracker stores `(cc_category, applied_at_tick, dr_tier)` entries per entity. Each successive application of the same CC category within a decay window reduces the effective duration (e.g., 100% &rarr; 65% &rarr; 35% &rarr; immune). DR tiers decay over time — after N seconds without that CC category, the tier resets. The DR formula and tier thresholds are game-defined (compiler-configured), not hardcoded. The engine provides the CC application hook; the game adapter tracks DR history internally.

---

### P-42: Stacking Counters with Decay

**Description:** A per-entity counter that accumulates stacks from repeated actions, scales effects based on stack count, and decays over time.

**Sketches:** SK-42 (Withering Fire — charge stacks), SK-52 (Combo Strike — sequential hit counter), SK-97 (Escalating Cost — cost stacks), SK-116 (Charge-Finisher — typed charge accumulation)

**Engine layer:** `game-adapter`

**Dependencies:** None.

**Key constraints:** Each stack has an optional type tag (for P-50 Typed Multi-Charge Pool). Stacks can decay individually (oldest first) or all-at-once (binary timeout). The max stack count is bounded. Stack count feeds into ability resolution as a multiplier or branch condition. The decay timer resets on each new stack addition.

---

### P-43: Charge-Up State

**Description:** A multiplier driven by the time delta between `Intent::Start` and `Intent::Release` — holding the button longer produces a stronger effect.

**Sketches:** SK-79 (Charge-Up Shot)

**Engine layer:** `game-adapter`

**Dependencies:** None.

**Key constraints:** The charge duration is capped (max charge time). The multiplier interpolates linearly (or via a configurable curve) between min and max values. The entity may be movement-locked or slowed during charge-up (via P-26 Capability Bitmask). Releasing early produces a weaker effect. The charge state is local to the caster's Arbiter — no cross-boundary concern.

---

### P-44: Pulse Timer

**Description:** An internal clock on a zone or entity that triggers a secondary primitive on a fixed interval.

**Sketches:** SK-08 (Aura — pulse every N ticks), SK-29 (Blizzard — damage pulse), SK-30 (Trail of Fire — damage tick), SK-38 (Contagion — spread pulse)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The pulse interval is defined in ticks (must be a positive integer). Each pulse triggers an associated primitive chain (typically P-09 Shape Overlap &rarr; P-15 Value Modification for damage zones). The pulse count may be bounded (N pulses then expire) or unbounded (until zone despawns). Pulse timing is deterministic — same tick offset on every Arbiter.

---

### P-45: Delay Timer

**Description:** A scheduled trigger that fires a primitive chain after a fixed number of ticks.

**Sketches:** SK-41 (Detonation Arrow — delayed explosion), SK-71 (Sticky Bomb), SK-84 (Temporal Trap)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The timer is created with a target tick and a primitive chain to execute. On the target tick, the chain fires unconditionally (the delay is committed). The timer is attached to an entity or zone — if the entity is destroyed before the timer fires, the timer may be cancelled (design choice) or fire anyway (fire-and-forget). Delay timers are SoftState and transfer on handoff.

---

### P-46: Global Event Scheduler

**Description:** Escalating a local event to the Mesh Controller for deterministic map-wide execution at a coordinated tick.

**Sketches:** SK-05 (Global Strike), SK-95 (Mass Effect Detonation — if map-wide)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The local Arbiter sends a "schedule global event at tick T" request to the Mesh Controller. The Controller broadcasts the event to all Arbiters for simultaneous execution. The scheduled tick must be far enough in the future to account for Controller round-trip latency. Global events are rare (design constraint) and bounded in frequency to prevent Controller overload.
