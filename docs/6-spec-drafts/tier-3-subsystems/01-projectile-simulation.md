# T3-01: Projectile Simulation

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `3-gameplay-systems/02-ability-framework.md`

## Audit Notes

**Core projectile mechanics ARE specified** in `03-mesh-arbiter-state.md` (ProjectileActor tick pseudocode, lines 1425-1534):

| Aspect | Status | Source |
|--------|--------|--------|
| Integration | **Specified** — Euler: `pos += vel * step_dilation` | line 1491 |
| Homing steering | **Specified** — bounded turn-rate via `projectile_turn_rate` and P-03 integration (see §1 below) | `01-core-primitives.md` |
| Pierce field | **Specified** — `pierce_remaining` tracked on ProjectileActor | `01-core-primitives.md` |
| Arming decrement | **Specified** — `arming_remaining_ticks.saturating_sub(1)` | `03-mesh-arbiter-state.md` |
| Collision call | **Specified** — `calculate_collisions(&entities, &ghosts)` with capsule broadphase (see §4 below) | `03-mesh-arbiter-state.md` |
| Cross-boundary dilation | **Specified** — `compute_projectile_step_dilation()` with blend equation | lines 1561-1578 |
| Handoff protocol | **Specified** — 3-phase Prepare/Ack/Commit | `01-core-primitives.md` |

## Resolved Gaps

All four original gaps have been resolved in this draft:

1. **Turn Rate Limiting** — Bounded steering via `projectile_turn_rate` and P-03 integration (§1 below).
2. **Detonation Policy** — Composable `ProjectileDetonationPolicy` with arming, impact, command, proximity, and expiry dimensions (§2 below).
3. **Pierce Decrement** — Per-unique-target consumption with hit exclusion list (§3 below).
4. **`calculate_collisions()` Body** — Capsule broadphase, distance+EntityID sort, narrowphase with pierce limit (§4 below).

## Questions to Resolve

- [x] Turn rate formula and config value
- [x] Detonation policy dimensions (arming, impact, command, proximity, expiry)
- [x] Pierce decrement: per-target or per-frame? Damage reduction per pierce?
- [x] `calculate_collisions()` implementation

## Proposed Resolution

### 1. Turn Rate Formula (P-03 Integration)
Homing projectiles (`homing == true`) MUST use the `projectile_turn_rate` field from the `AbilityEntry` as the `max_steer_rate` for the `P-03: Trajectory Steering` primitive.

**Validation Rule:**
- If `homing == true`, `projectile_turn_rate` MUST be present and MUST be greater than zero.
- If `homing == false`, `projectile_turn_rate` MAY be omitted. If present, it is ignored.
- The engine MUST NOT synthesize an implicit default turn rate for homing projectiles.

**Algorithm:**
1.  Compute `desired_dir = (target_pos - current_pos).normalize()`.
2.  Compute `current_dir = velocity.normalize()`.
3.  Compute `angle_to_target = acos(dot(current_dir, desired_dir))`.
4.  `step_angle = min(angle_to_target, projectile_turn_rate * effective_dilation)`.
5.  `new_dir = rotate(current_dir, step_angle, sign(cross(current_dir, desired_dir)))`.
6.  `velocity = new_dir * projectile_speed`.

All steering math MUST use `SimFixed` arithmetic to preserve determinism.

### 2. Detonation Policy Logic
The engine MUST evaluate `arming_delay_ticks` and `detonation_policy` (defined in `AbilityEntry`) during the ProjectileActor `tick()`:

#### 2.1 Arming Gate
- While `arming_remaining_ticks > 0`, the projectile/trap is unarmed.
- Unarmed explosives MUST NOT detonate from entity impact or proximity triggers.
- Non-detonating world responses such as `Bounce` or `Stop` MAY still apply while unarmed.

#### 2.2 Manual Command Trigger
- If `detonation_policy.manual_trigger_enabled == true`, the owner MAY issue a `DetonateOwnedProjectile { projectile_id }` intent.
- If the projectile is armed and still alive, the engine detonates it at its current authoritative position.

#### 2.3 Entity Impact Behavior
- **`Ignore`**: Pass through entities.
- **`Stop`**: Stop on first valid entity hit but do not detonate.
- **`Detonate`**: Detonate immediately on first valid entity hit.
- **`DetonateAfterPierceExhausted`**: Apply hits, decrement `pierce_remaining` per valid target, and detonate once `pierce_remaining == 0`.

#### 2.4 World Impact Behavior
- **`Ignore`**: No world-collision response.
- **`Bounce`**: Reflect/roll using the projectile's movement model.
- **`Stop`**: Stop on world collision without detonating.
- **`Detonate`**: Detonate on world collision.

#### 2.5 Expiry Behavior
- **`Despawn`**: When `remaining_lifetime_ticks == 0`, remove the projectile silently.
- **`Detonate`**: When `remaining_lifetime_ticks == 0`, detonate at the projectile's final position.

#### 2.6 Proximity Trigger
- If `detonation_policy.proximity_trigger_radius` is present, the engine checks for valid targets entering that radius after arming completes.
- Mines and pressure traps use this path; a contact-style trap uses a contact-sized radius.

#### 2.7 Example Mappings
- **Remote mine**: `manual_trigger_enabled = true`, `entity_impact_behavior = Ignore`, `world_impact_behavior = Stop`, `expiry_behavior = Despawn` or `Detonate`.
- **Bouncing grenade**: `manual_trigger_enabled = false`, `entity_impact_behavior = Detonate`, `world_impact_behavior = Bounce`, `expiry_behavior = Detonate`.
- **Pressure mine**: `manual_trigger_enabled = false`, `proximity_trigger_radius = Some(r)`, `entity_impact_behavior = Ignore`, `world_impact_behavior = Stop`, `expiry_behavior = Despawn` or `Detonate`.

### 3. Pierce Logic
`pierce` in `AbilityEntry` means **additional unique valid targets after the first**. `pierce_remaining` is initialized from that value when the projectile spawns.

1.  `calculate_collisions()` returns entity hits in deterministic contact order.
2.  Each candidate whose `entity_id` is NOT already in the projectile's `hit_exclusion_list` is eligible to consume pierce.
3.  For each accepted hit:
    -   Generate the hit payload.
    -   Add `target_id` to `hit_exclusion_list`.
    -   If `pierce_remaining > 0`, decrement it and continue evaluating later hits.
    -   If `pierce_remaining == 0`, this is the terminal hit for `DetonateAfterPierceExhausted`.
4.  Pierce is **never** decremented per frame and **never** decremented for rejected candidates.
5.  There is **no implicit per-pierce damage falloff**. If a design wants diminishing damage across pierces, that must be an explicit authored mechanic separate from `pierce`.

### 4. `calculate_collisions()` Implementation
The engine MUST resolve projectile collisions into an ordered batch that captures both entity hits and the earliest world contact:

```rust
struct ProjectileEntityHit {
    entity_id: EntityID,
    contact_t: SimFixed,
    is_ghost: bool,
}

struct WorldContact {
    contact_t: SimFixed,
    point: Vec2F,
    normal: Vec2F,
}

struct ProjectileCollisionBatch {
    entity_hits: Vec<ProjectileEntityHit>,
    first_world_hit: Option<WorldContact>,
}

fn calculate_collisions(&self, entities: &SpatialIndex, ghosts: &SpatialIndex) -> ProjectileCollisionBatch {
    let mut entity_hits = Vec::new();
    
    // 1. Broadphase: query spatial indexes for entities/ghosts within the sweep capsule
    // (segment from prev_pos to current_pos with projectile radius).
    let mut candidates = entities.query_capsule(self.prev_pos, self.pos, self.radius);
    candidates.extend(ghosts.query_capsule(self.prev_pos, self.pos, self.radius));
    let first_world_hit = static_grid.first_segment_contact(self.prev_pos, self.pos, self.radius);

    // 2. Deterministic Sort: all entity candidates (local + ghost) are normalized into one
    // total order. Ghost hash iteration order must not affect outcomes.
    candidates.sort_by(|a, b| {
        a.contact_t.cmp(&b.contact_t).then_with(|| a.id.cmp(&b.id))
    });

    // 3. Narrowphase: test exact intersection and filters
    for entity in candidates {
        if self.hit_exclusion_list.contains(&entity.id) { continue; }
        if self.geometry.intersects(&entity.hitbox) {
            entity_hits.push(ProjectileEntityHit {
                entity_id: entity.id,
                contact_t: entity.contact_t,
                is_ghost: entity.is_ghost,
            });
        }
    }

    ProjectileCollisionBatch {
        entity_hits,
        first_world_hit,
    }
}
```

Deterministic ordering rules:
1.  Sort entity hits by `contact_t` ascending.
2.  Break equal-`contact_t` ties by `entity_id` ascending.
3.  When comparing the earliest entity hit against `first_world_hit`, use `contact_t` ascending.
4.  If an entity hit and world contact have identical `contact_t`, the engine MUST resolve the entity hit first.

## References

- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` lines 1425-1534 — ProjectileActor tick
- `docs/3-gameplay-systems/02-ability-framework.md` — Homing Missile example
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` — ProjectileDetonationPolicy
