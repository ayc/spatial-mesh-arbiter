# 11. Systemic Interactions

*Primitives for cross-entity and cross-player emergent mechanics not covered by the core 62.*

These three primitives emerged from the final 18 ability sketches (SK-108 through SK-125) and cover systemic patterns where the interaction between entities or between game systems produces effects that are not reducible to simpler primitives.

---

### P-63: Movement-Damage Scalar

**Description:** Damage proportional to an entity's per-tick displacement — standing still deals zero damage; moving deals damage scaled by distance traveled.

**Sketches:** SK-109 (Movement Damage / Bloodseeker Rupture)

**Engine layer:** `game-adapter`

**Dependencies:** P-15 (Value Modification) — the calculated damage is applied through standard resolution.

**Key constraints:** The primitive attaches a debuff that stores `previous_position` and `damage_per_unit`. Each tick, after all movement resolution (voluntary, forced, teleport), displacement is calculated as `distance(current_position, previous_position)`. Damage = displacement &times; scalar. The damage is proportional to DISPLACEMENT (straight-line), not path length. Teleports (P-01) produce large single-tick displacements and correspondingly large damage. Forced displacement (P-02) also triggers the damage — the debuff does not distinguish voluntary from involuntary movement. An optional per-tick damage cap may be defined to prevent one-shot from global teleports. All arithmetic uses `I32F32`. The engine already exposes entity position each tick in kinematic state; the adapter reads position delta and applies damage through standard resolution hooks.

---

### P-64: Combo Field &times; Finisher Matrix

**Description:** A game-data-defined lookup table where zone element types crossed with ability finisher types produce emergent combo effects, enabling cross-player synergies.

**Sketches:** SK-120 (GW2 Combo System), SK-59 (Oil-Ignite — element combination), SK-95 (Mass Effect Detonation — primer/detonator pattern)

**Engine layer:** `game-adapter`

**Dependencies:** P-14 (Continuous Proximity Monitor) — detecting when a finisher enters a field. P-32 (Actor Spawning) — fields are spawned zone actors. P-09 (Shape Overlap Query) — finisher position checked against field geometry.

**Key constraints:** The matrix is defined entirely in game data (SpellData), not hardcoded in the engine. The engine provides the DETECTION mechanism; the game defines the CONTENT. Each zone carries an optional `combo_field_type` tag. Each ability carries an optional `combo_finisher_type` tag. When a finisher interacts with a field (projectile passes through, blast lands inside, leap traverses, whirl channels inside), the engine looks up `(field_type, finisher_type)` in the matrix and applies the result.

Combo detection rules:
- **Projectile finisher:** checked per-tick during flight — first field intersection triggers.
- **Blast finisher:** checked at resolution — is the AoE center inside a field?
- **Leap finisher:** checked on completion — did the path cross a field?
- **Whirl finisher:** checked per-tick during channel — once per field.

Each finisher can combo with each field only once (dedup via `comboed_fields` set). Cross-player combos are the default (any player's field + any player's finisher). Combos are detected only when finisher and field are on the same Arbiter.

---

### P-65: Vulnerability Window Broadcast

**Description:** An entity broadcasts a timed "counterable" state during a specific animation. Correctly-classified abilities landing during the window trigger a special interrupt and bonus effect.

**Sketches:** SK-119 (Lost Ark Counter System)

**Engine layer:** `game-adapter`

**Dependencies:** P-26 (Capability Bitmask) — the counter-stagger disables the target's actions. P-40 (On-Cast Intercept) — the counter interrupts the target's current cast.

**Key constraints:** The vulnerability window is defined as part of the broadcasting entity's ability definition: `window_start_offset_ticks`, `window_duration_ticks`, `bonus_damage`, `stagger_duration_ticks`. The window is opened when the entity begins a specific attack animation and closed when the window duration elapses or a counter lands.

Player abilities are tagged `can_counter_vulnerability_window: bool` at compile time. When an ability with that tag hits an entity during its vulnerability window:
1. The target's current ability is cancelled (mid-cast interruption).
2. Bonus damage is applied.
3. The target enters a brief stagger (stun + damage vulnerability).
4. The window is consumed (one counter per window — first hit wins).

If no counter lands, the target completes its attack normally. The window is primarily a PvE mechanic (boss attacks) but the primitive is entity-agnostic. Counter detection happens on the target's Arbiter where the window state is authoritative. Cross-boundary counter timing is subject to relay latency — for PvE, boss and players are typically co-located on the same Arbiter.
