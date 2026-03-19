# 9. Spatial & Instance Manipulation Primitives

*How the engine creates, reshapes, and connects spatial regions.*

---

### P-56: Spatial Instance Forking

**Description:** Dynamically spawning a "Pocket Arena" — a private R-Tree node — and migrating a subset of entities into it for isolated resolution.

**Sketches:** SK-105 (Pocket Arena), SK-61 (Spirit Split — instanced duel space)

**Engine layer:** `docs-core/`

**Dependencies:** None.

**Key constraints:** The forked instance is a new spatial partition with its own R-Tree. Entities migrated into it are removed from the parent R-Tree and are invisible/untargetable from outside. The instance has a bounded lifetime and bounded entity count. On expiry, entities are migrated back to their original positions (or a designated exit point) in the parent R-Tree. Instance creation is a heavy operation — bounded to N concurrent instances per Arbiter.

---

### P-57: Polyline Collision Generator

**Description:** Building damage or collision geometry from a sequence of points (a recorded path) rather than from a static shape definition.

**Sketches:** SK-30 (Trail of Fire — path traced by movement), SK-90 (Orbital Sweep — circular path geometry)

**Engine layer:** `docs-core/`

**Dependencies:** P-09 (Shape Overlap Query) — the generated geometry participates in overlap queries.

**Key constraints:** The polyline is built incrementally as points are added (one per tick during movement). Each segment has a width (creating a swept corridor). The total point count is bounded to cap memory and collision cost. The geometry is inserted into the spatial index and queried like any other zone. Old segments can expire individually (FIFO decay) to create a trail effect.

---

### P-58: Container/Vehicle Logic

**Description:** Locking N entities to a "parent" entity's transform, suppressing their direct spatial input, and routing the parent's movement to all contained entities.

**Sketches:** SK-60 (Bunker — entities inside the structure), SK-98 (Mobile Transport — entities riding a vehicle)

**Engine layer:** `docs-core/`

**Dependencies:** P-06 (Attached Kinematics) — contained entities follow the parent's transform. P-26 (Capability Bitmask) — contained entities have movement suppressed.

**Key constraints:** Contained entities lose autonomous movement but may retain ability usage (design choice). The container has a max capacity. Entering/exiting the container is an explicit action with a cast time. While contained, entities are at the container's position for targeting purposes. If the container is destroyed, all contained entities are ejected at the container's position.

---

### P-59: N-Way Portal Network

**Description:** A registry of spatial anchors that enables any-to-any instant translation across the mesh, including cross-Arbiter teleportation.

**Sketches:** SK-69 (Portal Pair), SK-72 (Nydus Network — multi-exit network)

**Engine layer:** `docs-core/`

**Dependencies:** P-01 (Instant Translation) — the actual teleport uses the same position-update path.

**Key constraints:** Each portal anchor has a position, an Arbiter ID, and a network ID. Anchors in the same network can teleport to each other. The registry is replicated to all Arbiters hosting anchors in the network (via Controller if cross-Arbiter). Portal usage triggers a handoff if the destination is on a different Arbiter. Anchor creation and destruction are bounded events. Travel through portals is subject to P-63 (Movement-Damage Scalar) displacement.
