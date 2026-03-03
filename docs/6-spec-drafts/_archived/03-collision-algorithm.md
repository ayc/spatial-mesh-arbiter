# T0-03: Collision Algorithm

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/01-core-concepts-and-mesh.md`

## Audit Notes

**The original draft overstated the gap.** Several aspects ARE specified:

| Aspect | Status | Source |
|--------|--------|--------|
| Movement integration | **Specified** — Euler: `pos += vel * dilation` | `03-mesh-arbiter-state.md` line 1491 |
| Entity-entity collision | **Specified** — Soft collision (separation steering), NOT rigid body. Entities can overlap but are pushed apart ("incompressible fluid"). | `01-core-concepts-and-mesh.md` §8.1 |
| CCD for projectiles | **Specified** — Swept-volume raycasts for fast projectiles | `01-core-concepts-and-mesh.md` §8.2.2 |
| Ability hit detection | **Specified** — `CollisionGeometry.is_inside_with_tolerance()` with Circle/Cone/Box and tolerance margin | `01-core-primitives.md` lines 939-980 |
| Ghost anomaly detection | **Specified** — Swept-segment AABB against static geometry, triggered only on abnormal displacement | `01-core-concepts-and-mesh.md` §2.4 |
| Movement validation | **Specified** — Client proposes position, Arbiter validates displacement ≤ `move_speed * dt + margin`, checks `static_grid.is_colliding()`, accepts or rejects | `03-mesh-arbiter-state.md` lines 997-1017 |

## Proposed Resolution

### 1. `apply_kinematics()` — Server-Side Physics Step

This method runs every tick. It handles three things, all dilated per-entity via `effective_time`:

```rust
fn apply_kinematics(&mut self) {
    for (entity_id, entity) in self.entities.iter_mut() {
        // Per-entity effective time: zone dilation * entity time_scale (Haste/Slow buffs)
        let effective_time = self.dilation_factor
            .saturating_mul(entity.stats.time_scale);

        // 1. SERVER-AUTHORITATIVE MOVEMENT (NPCs only)
        // Player movement is client-proposed (validated on arrival).
        // NPC movement is server-driven: apply velocity from FSM/AI decisions.
        if entity.is_npc {
            let new_pos = entity.position
                + entity.velocity.saturating_mul(effective_time);
            if !self.static_grid.is_colliding(new_pos) {
                entity.position = new_pos;
            } else {
                entity.velocity = Vec2F::ZERO; // NPC stops at wall
            }
        }

        // 2. KNOCKBACK DECAY (dilated — knockback fades slower in the swamp)
        if entity.knockback_velocity != Vec2F::ZERO {
            // Decay is dilated: in a 0.2 zone, knockback persists longer
            // because the entity experiences time slower.
            let decay_this_tick = SimFixed::from_num(1)
                - (SimFixed::from_num(1) - self.live_config.knockback_decay_rate)
                    .saturating_mul(effective_time);
            entity.knockback_velocity = entity.knockback_velocity
                .saturating_mul(decay_this_tick);

            let kb_displacement = entity.knockback_velocity
                .saturating_mul(effective_time);
            let new_pos = entity.position + kb_displacement;
            if !self.static_grid.is_colliding(new_pos) {
                entity.position = new_pos;
            }

            // Zero out if below threshold to avoid infinite tiny movements
            if entity.knockback_velocity.magnitude() < SimFixed::from_num(0.01) {
                entity.knockback_velocity = Vec2F::ZERO;
            }
        }
    }

    // 3. SOFT COLLISION PUSH-OUT (see §3 below)
    self.apply_soft_collision_separation();
}
```

**Key design decisions:**
- **Player movement is NOT integrated server-side.** Players propose positions (client-authoritative with server validation). The server only integrates movement for NPCs and knockback effects.
- **`effective_time` is per-entity.** Each entity may have a different `time_scale` from gameplay buffs (Haste, Slow), which stacks multiplicatively with zone `dilation_factor`. See `06-kinematic-dilation.md` §2.3.
- **Knockback decay is dilated.** In a Temporal Swamp, knockback fades slower because the entity experiences time slower. The decay rate is interpolated toward 1.0 (no decay) as `effective_time` approaches 0.
- **`knockback_velocity` is a field on `SoftState`.** It's per-entity ephemeral state that must serialize during handoffs, same as position and velocity.

### 2. `static_grid` — Uniform Grid of AABB Cells

**Type:** A uniform spatial grid where each cell stores a list of static AABB obstacles.

```rust
struct StaticGrid {
    cell_size: SimFixed,          // e.g., 2.0 meters per cell
    cells: HashMap<(i32, i32), Vec<StaticAABB>>,
}

struct StaticAABB {
    min: Vec2F,
    max: Vec2F,
}

impl StaticGrid {
    /// Point-in-obstacle test. Returns true if position overlaps any static obstacle.
    fn is_colliding(&self, position: Vec2F) -> bool;

    /// Swept-segment test. Returns all AABBs intersecting the line segment from `a` to `b`.
    /// Used for ghost anomaly detection, CCD, and line-of-sight checks (T3-04).
    fn query_segment_aabb(&self, a: Vec2F, b: Vec2F) -> Vec<&StaticAABB>;
}
```

**Loading:** Static geometry is loaded from a map asset file at Arbiter boot. The format is a flat list of AABBs (walls, obstacles, terrain blockers) serialized as bincode. The map asset is versioned by `data_epoch` alongside SpellData. Format can be evolved later (named regions, zone metadata) without changing the query interface.

**Rationale:** A uniform grid is the simplest spatial structure that supports both point queries and segment queries efficiently. At 2m cell size, a 1000m x 1000m map is 250K cells — trivially fits in memory. No dynamic updates needed since static geometry doesn't change during gameplay.

**Note on HashMap:** `cells` uses `HashMap` for sparse storage (empty cells don't exist in memory). Iteration order doesn't matter — `static_grid` is only accessed via point and segment queries, never iterated in entity-order-sensitive loops.

**LOS reuse (resolves T3-04):** `query_segment_aabb` is a raycast against static geometry — exactly what line-of-sight checks need. If the segment from entity A to entity B intersects any static AABB, LOS is blocked. This resolves T3-04 (Line of Sight Calculation) with no additional data structure.

### 3. Soft Collision Push-Out — Separation Steering

The "incompressible fluid" behavior from §8.1 is implemented as a Boids-style separation force, **dilated to match zone time:**

```rust
fn apply_soft_collision_separation(&mut self) {
    let separation_radius = self.live_config.separation_radius;   // e.g., 1.5 meters
    let max_push_per_tick = self.live_config.max_push_per_tick;   // e.g., 0.3 meters

    // Collect push vectors (can't mutate entities while iterating)
    let mut pushes: BTreeMap<EntityID, Vec2F> = BTreeMap::new();

    let entity_positions: Vec<(EntityID, Vec2F)> = self.entities.iter()
        .map(|(id, e)| (*id, e.position))
        .collect();

    for i in 0..entity_positions.len() {
        let (id_a, pos_a) = entity_positions[i];
        let mut push = Vec2F::ZERO;

        for j in 0..entity_positions.len() {
            if i == j { continue; }
            let (_, pos_b) = entity_positions[j];
            let diff = pos_a - pos_b;
            let dist = diff.magnitude();

            if dist < separation_radius && dist > SimFixed::from_num(0.001) {
                // Push strength inversely proportional to distance
                let strength = (separation_radius - dist)
                    .saturating_div(separation_radius);
                let direction = diff.normalize();
                push = push + direction.saturating_mul(strength);
            }
        }

        if push != Vec2F::ZERO {
            // Dilate push: in the Temporal Swamp, even the fluid pushes slower
            let dilated_max = max_push_per_tick
                .saturating_mul(self.dilation_factor);
            let mag = push.magnitude();
            if mag > dilated_max {
                push = push.normalize().saturating_mul(dilated_max);
            }
            pushes.insert(id_a, push);
        }
    }

    // Apply pushes (with static geometry validation)
    for (entity_id, push) in pushes {
        if let Some(entity) = self.entities.get_mut(&entity_id) {
            let new_pos = entity.position + push;
            if !self.static_grid.is_colliding(new_pos) {
                entity.position = new_pos;
            }
            // If push would go into a wall, just don't move (entities compress against walls)
        }
    }
}
```

**Configuration values** (live-configurable via SpellData / Data Epoch hot-patches):

| Key | Default | Description |
|-----|---------|-------------|
| `separation_radius` | `1.5` meters | Personal space radius for push-out |
| `max_push_per_tick` | `0.3` meters | Max separation displacement per tick (before dilation) |

**Performance:** The naive O(n²) loop is acceptable for n ≤ 400 (max entities per Arbiter before split). At 400 entities, that's 160K distance checks per tick — well within budget at 60Hz. If profiling shows this is hot, upgrade to a spatial hash for the entity positions.

### 4. `calculate_collisions()` — Projectile Hit Detection

```rust
fn calculate_collisions(
    &self,
    projectile: &ProjectileActor,
    entities: &BTreeMap<EntityID, SoftState>,
    ghosts: &HashMap<EntityID, GhostState2D>,
) -> Vec<EntityID> {
    // Unarmed projectiles (fuse still counting down) don't register hits
    if projectile.fuse_remaining_ticks > 0 {
        return Vec::new();
    }

    let mut victims = Vec::new();

    // Check local entities
    for (entity_id, entity) in entities {
        if *entity_id == projectile.caster_id { continue; } // Can't hit self
        if entity.is_dead { continue; }
        if entity.is_invulnerable { continue; }

        if projectile.geometry.is_inside_with_tolerance(
            entity.position,
            projectile.position,
            self.live_config.ghost_anomaly_margin, // Tolerance for network jitter
        ) {
            victims.push(*entity_id);
        }
    }

    // Check ghosts (cross-boundary targets)
    for (ghost_id, ghost) in ghosts {
        if *ghost_id == projectile.caster_id { continue; }
        if ghost.is_dead { continue; }

        if projectile.geometry.is_inside_with_tolerance(
            ghost.position,
            projectile.position,
            self.live_config.ghost_anomaly_margin,
        ) {
            victims.push(*ghost_id);
        }
    }

    victims
}
```

**Multi-victim handling:** All victims are collected. Each gets an independent `ImpactEvent` (or `InternalPreparedHit` for ghosts). There is no ordering among victims — each hit is processed independently. Pierce decrements `pierce_remaining` per victim hit; when exhausted, the projectile stops.

**Fuse guard:** Projectiles with `fuse_remaining_ticks > 0` are unarmed (still in their fuse period) and cannot register hits. The fuse timer decrements by `effective_time` per tick per the KiDi model — in a dilated zone, the fuse takes longer to arm.

**Determinism:** Local entities are iterated from `BTreeMap` (sorted by EntityID). Ghosts are iterated from `HashMap` (non-deterministic), but ghost hits produce `InternalPreparedHit` messages that are processed on the ghost's home Arbiter — the iteration order here doesn't affect authoritative state. Only the *existence* of a hit matters, not the order.

### 5. Wall Rejection — Intentional (No Wall Sliding)

**Decision:** Hard rejection is intentional. The current spec shows:

```rust
if !self.static_grid.is_colliding(position) {
    entity.position = position;
} else {
    self.trigger_client_rollback(actor_id);
}
```

**Rationale:** Player movement is client-authoritative with server validation. The client already implements wall sliding locally (the game client handles smooth movement against obstacles). The server's job is only to validate: "is this position legal?" If the client sends a position inside a wall, it's either a bug or a cheat — rollback is correct.

NPC movement (in `apply_kinematics`) also uses hard rejection (`entity.velocity = Vec2F::ZERO`), which means NPCs stop at walls rather than slide. This is acceptable for Arbiter-local NPCs; AI Node NPCs with more complex pathfinding would handle wall avoidance in their decision logic before submitting movement proposals.

## Summary of Decisions

| Question | Decision |
|----------|----------|
| `apply_kinematics()` | NPC movement integration + knockback decay + soft collision push-out. All dilated per-entity via `effective_time`. |
| `effective_time` | `dilation_factor * entity.core_stats.time_scale` — per-entity, accounts for Haste/Slow buffs |
| `knockback_velocity` | Field on `SoftState`. Decay is dilated. |
| `static_grid` | Uniform grid of AABB cells, loaded from map asset at boot. Also used for LOS (resolves T3-04). |
| Soft collision | Boids-style separation steering, O(n²), dilated push displacement. Live-configurable radius and max push. |
| `calculate_collisions()` | Geometry overlap test against local entities + ghosts. Fuse guard prevents unarmed hits. All victims collected independently. |
| Wall behavior | Hard rejection (intentional — client handles sliding, server validates) |

## Closed Questions

- **`separation_radius` / `max_push_per_tick` configurability:** Live-configurable via SpellData. They're gameplay-feel parameters designers will want to tune without restarts.
- **`knockback_velocity` storage:** Field on `SoftState`. Per-entity ephemeral state that serializes during handoffs.
- **Map asset format:** Bincode list of AABBs as starting point. Format can evolve (named regions, zone metadata) without changing the query interface.
- **LOS reuse of `static_grid`:** Yes — `query_segment_aabb` is a raycast against static geometry, which is exactly what LOS needs. Resolves T3-04.

## References

- `docs/1-architecture/01-core-concepts-and-mesh.md` §8.1 — Soft Collision, §8.2.2 — CCD, §2.4 — Ghost swept checks
- `docs/1-architecture/06-kinematic-dilation.md` §2.3 — Effective time multiplier, §3.1 — Dilated systems, §10.1 — Correct patterns
- `docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md` — CollisionGeometry with tolerance matching
- `docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md` — Movement validation, tick loop
