# Local Development & Testing Strategy (The "Mini-Mesh")

Testing a dynamically scaling, geographically partitioned server mesh on a single local development machine is notoriously difficult. A modern CPU can easily simulate thousands of entities on a single core, meaning a local developer will rarely, if ever, trigger the R-Tree splitting, Hitless Handoffs, or Ghost Propagation logic organically.

To ensure engineers can actively debug and observe the distributed systems logic without needing a massive cloud deployment, the engine utilizes a **"Mini-Mesh" Configuration Profile**.

---

## 1. The "Sandbox" Configuration Profile

The core of local testing is artificially shrinking the engine's capacity limits so that standard developer tests immediately trigger structural mesh events.

Developers should run the engine using a specific `config.dev.yaml` that aggressively overrides the production thresholds:

```yaml
# config.dev.yaml

mesh_controller:
  # Artificially force the R-Tree to split when as few as 10 entities gather
  max_entities_per_arbiter: 10
  
  # Prevent the R-Tree from slicing the map into microscopic 1-meter boxes
  # This forces the engine to test Kinematic Dilation (Blackhole events) locally
  min_cell_size_meters: 20.0 

spatial_arbiter:
  # Force high-frequency Ghost updates to easily monitor UDP traffic
  keyframe_interval_ticks: 10 
```

---

## 2. The Headless Swarm Tester

Running 30 full 3D game clients on a local machine to trigger a 10-player split is inefficient and resource-heavy. 

Engineers should utilize a **Headless Swarm Tester**—a lightweight Rust script that bypasses the graphical rendering engine and communicates directly with the local Edge Node (Proxy Actor) via UDP/WebSockets.

The Swarm Tester acts as an army of automated bots. It constructs raw `ActionProposals` (defined in `ActionPayloadTypes.md`) and spams them at the server to simulate real player behavior.

### Recommended Test Scenarios

#### Scenario A: The Organic Split (Testing Hitless Handoffs)
1. **Action:** The Swarm Tester spawns 15 bots and commands them to walk toward coordinate `[0,0]`.
2. **Observation:** As the 11th bot enters the bounding box, developers can observe the Mesh Controller instantly provision a secondary Arbiter process on `localhost`.
3. **Debugging:** Engineers can attach a debugger to verify the state serialization, fast-forward catch-up, and Edge Node routing flips occur without dropping the bots' movement packets.

#### Scenario B: Cross-Border Combat (Testing Ghost Relays)
1. **Action:** The Swarm Tester spawns 5 bots at `[-50, 0]` (Arbiter West) and 5 bots at `[50, 0]` (Arbiter East), commanding them to fire `SpawnProjectile` rockets at each other.
2. **Observation:** Developers can monitor the `Unreliable UDP` channel to ensure `GhostUpdates` are flowing across the border.
3. **Debugging:** When a rocket intersects a Ghost, engineers can trace the `MeshInternalEvent` via the `RUDP` channel to guarantee the Idempotency Ledger on the receiving Arbiter correctly applies the damage exactly once.

#### Scenario C: The Blackhole (Testing Kinematic Dilation)
1. **Action:** The Swarm Tester spawns 30 bots and forces them all to stand on the exact same `[0,0]` coordinate.
2. **Observation:** The Mesh Controller attempts to split the node but hits the `min_cell_size_meters: 20.0` limit. Unable to split geographically, the Arbiter is forced to handle 30 entities (3x its capacity).
3. **Debugging:** Developers will see the Arbiter automatically trigger **Kinematic Dilation**. The physical speed of the bots will slow down, and the Arbiter will begin interleaving its collision checks to survive the artificial load.

---

## 3. Visualizing the Mesh

Because the Headless Swarm Tester has no graphical client, it is highly recommended to build a simple **2D Debug Canvas** (using a lightweight framework like `macroquad` or an HTML5 Canvas hooked to a local WebSocket).

This Debug Canvas should connect directly to the Mesh Controller to visualize:
1. The dynamic Axis-Aligned Bounding Boxes (AABBs) of the active Arbiters (drawn as colored rectangles).
2. The `EntityIDs` (drawn as dots).
3. The `Ghost Entities` (drawn as hollow circles to prove propagation is working).

By watching the rectangles dynamically split, merge, and slide over the dots in real-time on the 2D canvas, engineers can visually confirm that the R-Tree is load-balancing the mesh correctly.