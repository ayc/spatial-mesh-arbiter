# 10. Advanced Resolution Primitives

*Exotic combat pipeline behaviors that modify how resolution itself works.*

---

### P-60: Event Cloning (Mirroring)

**Description:** Forcing all damage, healing, or ability resolutions applied to Entity A to be immediately duplicated and applied to Entity B.

**Sketches:** SK-111 (Soulbind — single-target ability duplication), SK-66 (Symbiote — shared damage)

**Engine layer:** `docs-core/`

**Dependencies:** P-34 (Persistent Linkage) — the mirror relationship is a binding between two entities.

**Key constraints:** The cloned event is a NEW resolution against Entity B using Entity B's own defensive stats — not a copy of Entity A's resolution result. The clone is flagged as "mirrored" to prevent infinite loops (mirrored events do not trigger further mirroring). For SK-111 (Soulbind), only single-target abilities are cloned; AoE is excluded. The clone relay is cross-boundary if A and B are on different Arbiters.

---

### P-61: Projectile Ownership Hijacking

**Description:** Dynamically swapping the `OwnerID` and `Velocity` vector of an active projectile in flight.

**Sketches:** SK-82 (Projectile Deflect)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The hijack is an atomic operation within a single tick: the projectile's owner becomes the deflecting entity, and its velocity is reversed (or redirected toward a new target). The projectile's damage now credits the new owner. The hijack can only target projectiles within a spatial query range of the deflecting entity. Only one hijack per projectile (prevent ping-pong). The projectile's remaining lifetime is preserved or reset (design choice).

---

### P-62: Categorized CC Immunity

**Description:** Granular immunity flags organized by CC category — displacement immunity, hard-disable immunity, soft-disable immunity — rather than a blanket "unstoppable" flag.

**Sketches:** SK-118 (Partial CC Immunity — push immune during cast), SK-51 (Unstoppable — all categories immune)

**Engine layer:** `docs-core/`

**Dependencies:** P-41 (Diminishing Returns Tracker) — DR categories should align with immunity categories.

**Key constraints:** CC categories: `Displacement`, `HardDisable`, `SoftDisable`, `ForcedMovement`, `TargetOverride`, `Mute`. Every CC effect is tagged with exactly one category at compile time. Immunity is checked per-category before CC application. Multiple immunity sources stack (any source granting immunity for a category is sufficient). Immunity flags are temporary status effects with duration — typically tied to ability cast animations. Full "Unstoppable" is all flags set to true.
