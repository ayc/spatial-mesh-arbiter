# 3. Combat Resolution Primitives

*How numbers go up and down in Phase 2.*

---

### P-15: Value Modification

**Description:** Flat or percentage application of damage or healing to an entity's HP.

**Sketches:** SK-01 (Toss), SK-02 (Poison Shot), SK-05 (Global Strike), SK-09 (Chain Lightning), SK-15 (Purify), SK-16 (Holy Ground), SK-20 (Battle Cry), SK-29 (Blizzard), SK-48 (Death Coil), SK-108 (Mana Burn bonus damage), SK-109 (Movement Damage)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The fundamental building block of combat. All damage/healing flows through this primitive and is subject to the Phase 2 resolution pipeline (mitigation, shields, hooks). Values use `I32F32`. Negative values are damage; positive values are healing (or vice versa per convention — the sign is explicit in the CombatContext).

---

### P-16: Stat Layering

**Description:** Applying additive or multiplicative modifiers to an entity's base stats, with defined stacking rules and layer priorities.

**Sketches:** SK-16 (Holy Ground stat buffs), SK-20 (Battle Cry), SK-46 (Adaptation), SK-92 (Anti-Heal as negative healing modifier)

**Engine layer:** `game-adapter`

**Dependencies:** None.

**Key constraints:** Modifiers are layered: base stat &rarr; flat additive &rarr; percentage multiplicative &rarr; final value. Each modifier has a source ID for removal. Stacking rules (does the same buff stack? up to N times?) are defined per modifier at compile time. Modifiers are recalculated when buffs are added or removed, not every tick.

---

### P-17: Conditional Thresholds

**Description:** Branching ability resolution based on a numeric condition — "if target HP < X" or "if caster has Y stacks."

**Sketches:** SK-14 (Execute Threshold), SK-48 (Death Coil — conditional friend/foe), SK-114 (Piercing Execute)

**Engine layer:** `game-adapter`

**Dependencies:** None.

**Key constraints:** The condition is evaluated at resolution time using authoritative state. For cross-boundary targets (Ghosts), the condition check must happen on the target's Arbiter where the value is authoritative. The threshold value can be a flat number or a percentage of a stat (e.g., "below 25% max HP").

---

### P-18: Absorption Barrier

**Description:** A secondary HP pool (shield) that absorbs incoming damage before the entity's actual HP is reduced.

**Sketches:** SK-17 (Sacrifice Shield), SK-47 (Shield Burst), SK-70 (Energy Shield)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Multiple shields can stack — damage is absorbed from shields in priority order before reaching HP. Each shield has a remaining value, a source, and an expiry tick. When a shield's remaining value reaches zero, it is removed. Shield overflow (damage exceeding shield remaining) passes through to the next shield or HP.

---

### P-19: Instance Barrier

**Description:** A shield that tracks number of hits absorbed rather than damage amount — each hit consumes one charge regardless of damage value.

**Sketches:** SK-113 (Hit-Count Shield)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** Instance barriers are checked BEFORE absorption barriers (P-18) in the damage pipeline. Each incoming damage event consumes one charge and is fully negated. When charges reach zero, the barrier is removed. DoT ticks each count as separate hits (intended counterplay). A "hit" is defined as one damage event in the resolution pipeline.

---

### P-20: Damage Redirection

**Description:** Siphoning a percentage of damage dealt to Entity A and applying it instead to Entity B.

**Sketches:** SK-60 (Bunker — damage redirected to the bunker structure), SK-17 (Sacrifice Shield — ally damage redirected to shield caster)

**Engine layer:** `docs-core/`

**Dependencies:** P-34 (Persistent Linkage) — the redirection binding between A and B must survive handoffs.

**Key constraints:** The redirection percentage is configurable (25%, 50%, 100%). Redirected damage goes through Entity B's own damage resolution pipeline (B's shields and mitigation apply). Circular redirections (A redirects to B, B redirects to A) must be detected and broken at compile time or capped at one hop at runtime.

---

### P-21: Value Conversion

**Description:** Converting one value type into another during combat resolution — dealt damage into healing (lifesteal), or resource destruction into damage.

**Sketches:** SK-48 (Death Coil — self-damage to heal ally), SK-108 (Mana Burn — mana destroyed &rarr; bonus damage), SK-45 (Essence Collection — pickups &rarr; healing)

**Engine layer:** `game-adapter`

**Dependencies:** P-15 (Value Modification) — the converted value is applied through standard value modification.

**Key constraints:** The conversion ratio is a `I32F32` scalar (e.g., 0.15 for 15% lifesteal). The input and output value types must be explicit (HP &rarr; HP, Mana &rarr; HP, etc.). Conversion happens after the source value is finalized (post-mitigation for lifesteal).

---

### P-22: Deferred Ledger

**Description:** Suppressing all HP changes on an entity for a duration, accumulating them in a hidden ledger, and applying the net result on expiry.

**Sketches:** SK-112 (Deferred Resolution / False Promise)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** While active, the entity's HP does not change in downstream payloads (frozen HP bar). The ledger tracks accumulated damage and accumulated healing separately. On expiry: `net = healing - damage`, applied as a single HP modification. If net is negative and exceeds remaining HP, the entity dies. The ledger intercepts ALL damage/healing sources — no bypass except P-24 (Resolution Bypass).

---

### P-23: Floor Clamping

**Description:** Preventing an entity's HP from dropping below a minimum value (typically 1 HP).

**Sketches:** SK-73 (Death Immunity), SK-93 (Death Prevention), SK-121 (Downed State — HP floored at transition)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The floor is checked after all damage resolution. If HP would drop to or below zero, it is set to the floor value instead. The floor can be 1 (death immunity) or 0 (transitions to a different life phase via P-25). Floor clamping is bypassed by P-24 (Resolution Bypass).

---

### P-24: Resolution Bypass

**Description:** Marking a damage event or kill command as "true execution" that ignores all shields, immunities, floor clamps, and death-prevention hooks.

**Sketches:** SK-114 (Piercing Execute)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** A `bypass_prevention: true` flag on the death trigger skips P-18 (shields), P-19 (instance barriers), P-22 (deferred ledger), P-23 (floor clamping), and P-25 (multi-phase vital transition). This flag is only available through authorized ability definitions validated at compile time — it cannot be set by arbitrary runtime logic. Use sparingly in game design.

---

### P-25: Multi-Phase Vitals

**Description:** Allowing an entity to hit 0 HP but transition to a secondary vital pool and life phase instead of dying.

**Sketches:** SK-121 (Downed State)

**Engine layer:** `docs-core/`

**Dependencies:** P-23 (Floor Clamping) — the transition intercepts the death check. P-31 (Identity/Loadout Swap) — the phase transition typically swaps abilities.

**Key constraints:** The entity lifecycle becomes: Alive (main HP) &rarr; Downed (secondary HP) &rarr; Dead. Each phase has its own HP pool, ability set, and movement speed. Damage while in a secondary phase targets that phase's HP pool. The number of phases is bounded (typically 2-3). Bypassed by P-24 (Resolution Bypass).
