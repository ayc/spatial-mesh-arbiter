# SK-70: Energy Shield

## Designer Intent

I shield myself (or an ally). The shield absorbs incoming damage as normal. BUT: every point of damage the shield absorbs is converted into Energy — a secondary resource that increases my weapon damage. More damage absorbed = more Energy = stronger attacks. Energy decays over time if not refreshed.

## Primitive Composition

P-18 (Absorption Barrier) → `apply_shield.on_absorb_effects` → `modify_resource` → passive
`resource_stat_links` + periodic decay → P-16 (Stat Layering)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target: self or ally entity

## Observable Behavior

1. Cast — shield is applied to the target (e.g., 400 HP shield, 3 second duration)
2. Shield absorbs incoming damage normally
3. For each point of damage absorbed: the CASTER gains 1 Energy (secondary resource, max 100)
4. Energy increases the caster's damage output: each point of Energy = +0.5% damage bonus
5. At max Energy (100): caster deals +50% bonus damage
6. Energy decays over time (e.g., 3 Energy per second) if no new damage is absorbed
7. Shield on ally: damage absorbed by the ALLY's shield gives Energy to the CASTER
8. Visual: blue-white shield, caster's weapon glows brighter as Energy increases

## Engine Primitives Required

### Shield-to-Resource Conversion Pipeline

The canonical contract is:

1. `apply_shield` authors `bind_absorbed_value_as = absorbed_damage`.
2. `apply_shield.on_absorb_effects` emits `modify_resource(target = caster, pool_id = energy, ...)`.
3. The callback reads `absorbed_damage` through `ScalingExpr(binding = absorbed_damage)`.
4. The credited amount is the authoritative damage prevented by that specific shield instance on
   that hit, after shield-priority ordering is already resolved.
5. Shield break and shield expiry stay on the ordinary `on_break_effects` / `on_expire_effects`
   path; they are not required for Energy credit.

### Cross-Entity Resource Credit

Energy is an ordinary resource pool on the caster:

```yaml
max_resource:
  energy: 100
```

Every shield absorb event mutates that pool through canonical `modify_resource`. For example:

```yaml
type: modify_resource
target: caster
pool_id: energy
mode: add
amount: 0
scaling:
  binding: absorbed_damage
  coefficient: 1.0
```

When the shield is on an ally, the shield bearer computes the authoritative absorbed amount on
their current owner. If the caster is remote, the resulting `modify_resource(target = caster, ...)`
uses the ordinary target-owner relay path. No bespoke "Energy credit" protocol is required.

### Secondary Resource With Decay

Energy decay and the outgoing damage bonus are both status-owned, not shield-owned:

```yaml
status_id: energy_attunement
is_passive: true
resource_stat_links:
  - pool_id: energy
    stat_id: physical_damage_multiplier
    operation: add_percent
    coefficient: 0.005
periodic_effects:
  interval_ticks: 20
  effects:
    - type: modify_resource
      target: caster
      pool_id: energy
      mode: remove
      amount: 1
```

This yields:

- 1 Energy = +0.5% weapon-damage bonus through `physical_damage_multiplier`
- 100 Energy = +50% weapon-damage bonus
- deterministic decay through ordinary periodic resource mutation
- no bespoke per-shield Energy state object

### Feedback Loop

This creates a positive feedback loop:
1. Shield absorbs damage → gain Energy → deal more damage
2. Deal more damage → enemies try to focus you → shield absorbs more → gain more Energy

The loop is bounded by:
- Energy max cap (100)
- Shield HP limit (shield is consumed)
- Energy decay (fades without fresh shield absorption)
- Shield cooldown (can't have 100% shield uptime)

## Cross-Boundary Concerns

1. **Self-shield:** Caster shields themselves. All absorption and Energy credit are local. No cross-boundary concern.

2. **Ally shield:** Caster on Arbiter A shields an ally on Arbiter B. The shield is applied on
   Arbiter B. When the ally takes damage, Arbiter B calculates the authoritative absorbed amount,
   then the deferred `modify_resource(target = caster, pool_id = energy)` mutation routes to
   Arbiter A if the caster is remote.

This can generate one relay per absorb event, but it is bounded by shield HP, shield duration, and
incoming hit cadence. If the shield is removed, cleansed, or expires, future credits stop
immediately. Energy already gained remains because it is ordinary resource state on the caster.

## Compiler Requirements

Designer authors:

- shield amount and duration
- Energy conversion coefficient
- Energy pool max
- Energy decay cadence
- Energy-to-weapon-damage coefficient
- self-target and ally-target variants

Compiler produces:

- a canonical `apply_shield` with `bind_absorbed_value_as` and `on_absorb_effects`
- canonical `modify_resource` mutations against the caster's `energy` pool
- a passive status with `resource_stat_links` so current Energy continuously affects present
  offense
- periodic `modify_resource(mode = remove)` decay on that passive status
- ordinary cross-boundary target-owner relay when an ally shield credits a remote caster

## Resolved Notes

- The outgoing damage bonus is modeled as weapon damage by linking Energy to
  `physical_damage_multiplier`.
- Multiple simultaneous qualifying shields may all feed the same `energy` pool; ordinary
  `max_resource.energy` clamping bounds the result.
- Energy already gained is retained if the shield is cleansed or removed early; only future absorb
  callbacks stop.
- Energy persistence through death follows the ordinary lifecycle for authored resource pools. This
  sketch does not add a bespoke exception.
