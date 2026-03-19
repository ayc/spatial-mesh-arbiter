# 5. Hooks & Reactive Triggers

*The event listener system for abilities that watch other actions.*

---

### P-35: On-Damage-Dealt / On-Hit Hook

**Description:** A callback invoked after an entity successfully deals damage or lands a hit, enabling secondary effects to trigger from the damage event.

**Sketches:** SK-02 (Poison Shot — on-hit DoT), SK-09 (Chain Lightning — on-hit chain), SK-10 (Crit Explosion — on-hit AoE), SK-52 (Combo Strike — on-hit advance combo), SK-83 (Next-Cast Empowerment — on-hit bonus), SK-108 (Mana Burn — on-hit mana destruction)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The hook fires AFTER the primary damage is resolved and applied. The hook receives the full `CombatContext` (attacker, target, damage dealt, damage type, was-crit). Multiple on-hit hooks on the same entity fire in registration order. On-hit effects from hooks go through their own resolution (can be shielded, mitigated, etc.) but are flagged as "secondary" to prevent infinite on-hit chains.

---

### P-36: On-Damage-Received Hook

**Description:** A callback invoked when an entity takes damage, enabling reactive effects like reflection, adaptation, or concentration checks.

**Sketches:** SK-22 (Damage Reflection), SK-23 (Thorns Aura), SK-46 (Adaptation — ramp resistance), SK-87 (Conditional Counter), SK-123 (Concentration check on damage)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The hook fires AFTER damage is applied to HP (post-mitigation, post-shield). The hook receives: damage source, damage amount (pre- and post-mitigation), damage type. Thorns/reflection effects triggered by this hook are flagged as "reactive" and do NOT trigger the attacker's own P-36 hooks (prevents infinite ping-pong).

---

### P-37: On-Crit Hook

**Description:** A callback invoked specifically when a damage event is a critical hit, enabling crit-specific secondary effects.

**Sketches:** SK-10 (Crit Explosion)

**Engine layer:** `game-adapter`

**Dependencies:** P-35 (On-Hit Hook) — the crit hook is a specialization of the on-hit hook, filtered by the `was_crit` flag.

**Key constraints:** Fires only when `CombatContext.was_crit == true`. The hook receives the same context as P-35 plus the crit multiplier. This is logically a filtered subset of P-35 but is separated for clarity and to avoid unnecessary hook evaluations on non-crit hits.

---

### P-38: On-Block / On-Defend Hook

**Description:** A callback invoked when an entity successfully blocks, parries, or defends against an incoming attack.

**Sketches:** SK-21 (Block — on-block damage reduction), SK-87 (Conditional Counter — on-block riposte)

**Engine layer:** `game-adapter`

**Dependencies:** None.

**Key constraints:** The definition of "block" is game-specific (RNG roll, facing check, active ability). The hook fires when the block check succeeds, before damage mitigation. The hook receives: attacker, original damage, block percentage. Effects triggered by this hook (riposte damage, block buff) go through standard resolution.

---

### P-39: On-Death Hook

**Description:** A callback invoked when an entity's HP reaches zero (or transitions to a death-like state), enabling death-triggered effects.

**Sketches:** SK-11 (On-Kill Cascade), SK-96 (Death Ghost), SK-115 (Corpse Economy — spawn corpse on death), SK-121 (Downed State — intercept death transition)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The hook fires at the point of death, BEFORE the entity is removed from the R-Tree. This allows the hook to spawn entities at the death position (corpses, ghosts), modify the death outcome (transition to downed state), or trigger effects on the killer. The hook has access to the killer's entity ID for on-kill attribution. Death hooks run in priority order — P-25 (Multi-Phase Vitals) transitions take precedence over corpse spawning.

---

### P-40: On-Cast Intercept

**Description:** Reading an ability intent BEFORE it resolves, with the option to cancel, duplicate, or modify it.

**Sketches:** SK-07 (Ability Steal), SK-12 (Spell Echo — duplicate the cast), SK-122 (Counterspell — cancel the cast)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The intercept fires during Phase 1 (`validate_intent`), after the caster's intent is confirmed but before Phase 2 resolution begins. The interceptor can: (a) cancel the cast entirely (Counterspell), (b) duplicate the cast as an additional resolution (Spell Echo), or (c) copy the ability definition for the interceptor's own use (Ability Steal). The intercepted entity's cast state (ability ID, cast tick) must be visible to nearby entities for reaction-based intercepts. Only abilities with `cast_time > 0` are interceptable by default.
