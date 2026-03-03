## 3. Layer 2: The Mesh Arbiter (Spatial Actor)

The Spatial Actor is a single-threaded, lock-free, 60Hz deterministic simulation loop. 

### 3.1 Interface
```rust
// Defines how long the engine remembers events (60 ticks = 1.0 second).
const MAX_EVENT_AGE_TICKS: u64 = 60;

// Configuration structs replacing hardcoded magic numbers
// (See ../../4-infrastructure/02-configuration-registry.md for detailed definitions)
struct BootConfig {
    proposal_bucket_capacity: u16,
    proposal_bucket_refill_per_tick: u16,
    max_event_age_ticks: u64,
}

struct LiveConfig {
    combat_radius: SimFixed,
    visible_radius: SimFixed,
    keyframe_interval_ticks: u64,
    ghost_anomaly_margin: SimFixed,
    ghost_degraded_ttl_ticks: u64,
    ghost_render_ttl_ticks: u64,
    dilation: DilationConfig,
}

// --- Utility Types ---

// Capacity-limited FIFO queue. Prevents OOM during blackhole density events
// by dropping excess items rather than growing unbounded.
struct BoundedQueue<T> {
    buffer: VecDeque<T>,
    capacity: usize,
}

impl<T> BoundedQueue<T> {
    fn new(capacity: usize) -> Self {
        Self { buffer: VecDeque::with_capacity(capacity), capacity }
    }
    fn push_back(&mut self, item: T) -> bool {
        if self.buffer.len() >= self.capacity { return false; } // Drop on overflow
        self.buffer.push_back(item);
        true
    }
    fn drain(&mut self) -> impl Iterator<Item = T> + '_ { self.buffer.drain(..) }
    fn is_full(&self) -> bool { self.buffer.len() >= self.capacity }
    fn len(&self) -> usize { self.buffer.len() }
    fn is_empty(&self) -> bool { self.buffer.is_empty() }
}

// Thin wrapper over an R-Tree (rstar crate) for O(log n) spatial queries on entity positions.
// Kept in sync with the corresponding HashMap (e.g., ghost_entities) on every insert/remove/move.
struct SpatialIndex<T: Copy> {
    tree: RTree<SpatialEntry<T>>, // rstar::RTree
}

struct SpatialEntry<T: Copy> {
    position: Vec2F,
    value: T,
}

impl<T: Copy> SpatialIndex<T> {
    fn new() -> Self { Self { tree: RTree::new() } }
    fn insert(&mut self, position: Vec2F, value: T);
    fn remove(&mut self, position: Vec2F, value: T);
    fn update(&mut self, old_pos: Vec2F, new_pos: Vec2F, value: T);
    fn query_radius(&self, center: Vec2F, radius: SimFixed) -> Vec<T>;
    fn query_rect(&self, region: &Rect) -> Vec<T>;
}

// --- Ghost Types ---

enum GhostMovementClass {
    Normal,
    HighSpeed, // Dash/leap style displacement
    Teleport,  // Instant large displacement
}

enum GhostQuality {
    Healthy,
    Degraded, // Frozen/clamped until reliable correction arrives or TTL expires
}

struct GhostState2D {
    entity_id: EntityID,
    authoritative_arbiter_id: u32,
    position: Vec2F,
    velocity: Vec2F,
    last_valid_position: Vec2F,
    last_update_tick: u64,
    movement_class: GhostMovementClass,
    quality: GhostQuality,
    degraded_until_tick: u64,
}

struct GhostUpdate {
    entity_id: EntityID,
    source_arbiter_id: u32,
    source_tick: u64,
    position: Vec2F,
    velocity: Vec2F,
    movement_class: GhostMovementClass,
    is_keyframe: bool,
}

struct TokenBucket {
    tokens: u16,
    last_refill_tick: u64,
}

impl TokenBucket {
    fn new(now_tick: u64) -> Self {
        Self {
            tokens: PROPOSAL_BUCKET_CAPACITY,
            last_refill_tick: now_tick,
        }
    }

    fn try_consume(&mut self, now_tick: u64, cost: u16) -> bool {
        let elapsed = now_tick.saturating_sub(self.last_refill_tick);
        if elapsed > 0 {
            let refill = (elapsed as u128) * (PROPOSAL_BUCKET_REFILL_PER_TICK as u128);
            let replenished = (self.tokens as u128 + refill).min(PROPOSAL_BUCKET_CAPACITY as u128);
            self.tokens = replenished as u16;
            self.last_refill_tick = now_tick;
        }

        if self.tokens < cost { return false; }
        self.tokens -= cost;
        true
    }
}

enum MergeRole {
    Winner,
    Loser,
}

enum MergePhase {
    Streaming,
    Catchup,
    AwaitingCommit,
    ForwardingOnly,
}

struct MergeState {
    merge_id: UUID,
    role: MergeRole,
    peer_arbiter_id: u32,
    cutover_tick: u64,
    target_epoch: u32,
    phase: MergePhase,
    forwarding_until_tick: u64,
}

struct SpatialActor {
    arbiter_id: u32,
    topology_epoch: u32,
    current_data_epoch: u32, // The version of the SpellData dictionary currently loaded in memory
    rtree_depth: u8,
    region_bounds: Rect,
    current_tick: u64,
    
    // The "Temporal Swamp" Factor (0.0 to 1.0)
    // 1.0 = Full speed (60Hz resolution)
    // 0.2 = 1/5th speed (Physics resolution every 5th tick)
    dilation_factor: SimFixed, 
    
    // Bounded Queues (Network layer pushes here. Must have explicit capacity limits 
    // to prevent OOM failure modes during blackhole density events).
    external_inbox: BoundedQueue<ActionProposal>,
    internal_inbox: BoundedQueue<MeshInternalEvent>,
    controller_inbox: BoundedQueue<ControllerCommand>,
    
    // Future Event Scheduler
    pending_global_events: HashMap<UUID, ControllerCommand>,
    
    // Stale Buffer: Holds (Proposal, local_arrival_tick) to measure timeout safely.
    // Must be a BoundedQueue to prevent OOM vulnerabilities during prolonged Mesh Controller 
    // outages. Sized to handle spikes based on a ~400 entity capacity limit.
    stale_proposals_buffer: BoundedQueue<(ActionProposal, u64)>,

    // Runtime storage splits SoftState and OffensiveStats into separate maps for cache locality.
    // During split/merge serialization, these are joined into Vec<(EntityID, EntityRecord)>
    // as defined in 01-core-primitives.md (SplitSnapshot / MergeSnapshot).
    entities: HashMap<EntityID, SoftState>,
    offense_by_entity: HashMap<EntityID, OffensiveStats>,
    ghost_entities: HashMap<EntityID, GhostState2D>, 
    ghost_grid: SpatialIndex<EntityID>, // Mirrors ghost positions for cheap downstream visibility queries
    proposal_buckets: HashMap<EntityID, TokenBucket>, // Per-entity fairness guard on ingress
    merge_state: Option<MergeState>,
    processed_proposals: LruCache<UUID, bool>, 
    
    // Event Idempotency Ledger: Prevents double-damage from delayed or duplicate relays.
    // Dynamically sized to the max event age to survive delayed packets and Hitless Handoffs.
    event_idempotency_ledger: [HashSet<(UUID, EntityID)>; MAX_EVENT_AGE_TICKS as usize], 
}

impl SpatialActor {
    fn verify_mesh_auth<T>(&self, header: &MeshAuthHeader, payload: &T) -> bool {
        // Pseudocode:
        // 1) validate auth_epoch/key-id is currently accepted
        // 2) reject nonce replay for this sender
        // 3) recompute HMAC over canonical payload bytes and compare constant-time
        verify_hmac_and_nonce(header, payload)
    }

    // Called by the RUDP network layer for authenticated intra-mesh events.
    fn on_internal_event_rudp(&mut self, header: MeshAuthHeader, event: MeshInternalEvent) {
        if !self.verify_mesh_auth(&header, &event) { return; }
        self.internal_inbox.push_back(event);
    }

    // Called by the network ingress layer for each proposal packet before queueing.
    fn on_external_proposal_received(&mut self, proposal: ActionProposal) {
        // Zero-trust ingress: only intent-level payloads are valid from Edge Nodes.
        if !matches!(
            &proposal.payload,
            ActionPayload::Movement { .. }
                | ActionPayload::TargetedAbility { .. }
                | ActionPayload::GroundTargetedAbility { .. }
                | ActionPayload::SpawnProjectile { .. }
                | ActionPayload::UseConsumable { .. }
                | ActionPayload::Interact { .. }
        ) {
            self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                proposal_id: proposal.proposal_id,
                reason: "Invalid Payload Type".to_string(),
            });
            return;
        }

        let cost = if matches!(&proposal.payload, ActionPayload::Movement { .. }) {
            PROPOSAL_COST_MOVEMENT
        } else {
            PROPOSAL_COST_DISCRETE
        };

        let bucket = self.proposal_buckets
            .entry(proposal.actor_id)
            .or_insert(TokenBucket::new(self.current_tick));

        if !bucket.try_consume(self.current_tick, cost) {
            if !matches!(&proposal.payload, ActionPayload::Movement { .. }) {
                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                    proposal_id: proposal.proposal_id,
                    reason: "Rate Limited".to_string(),
                });
            }
            return;
        }

        if self.external_inbox.is_full() {
            if !matches!(&proposal.payload, ActionPayload::Movement { .. }) {
                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                    proposal_id: proposal.proposal_id,
                    reason: "Arbiter Queue Saturated".to_string(),
                });
            }
            return;
        }

        self.external_inbox.push_back(proposal);
    }

    // Core Loop: Runs strictly every 16.6ms (60Hz)
    fn tick(&mut self) {
        self.current_tick += 1;
        
        // 0. O(1) Ledger Cleanup
        let current_bucket = (self.current_tick % MAX_EVENT_AGE_TICKS) as usize;
        self.event_idempotency_ledger[current_bucket].clear();

        // 1. Buffer incoming top-down commands into the persistent scheduler
        for command in self.controller_inbox.drain(..) {
            if let ControllerCommand::ExecuteGlobalEvent { event_id, .. } = command {
                self.pending_global_events.insert(event_id, command);
            } else {
                self.process_controller_command(command);
            }
        }

        // 2. Priority Check: Do we have a Nuke scheduled for RIGHT NOW (or earlier)?
        let mut has_priority_event = false;
        for cmd in self.pending_global_events.values() {
            if let ControllerCommand::ExecuteGlobalEvent { execute_at_tick, .. } = cmd {
                if self.current_tick >= *execute_at_tick { has_priority_event = true; }
            }
        }

        // Heavy frames occur more frequently as dilation_factor approaches 1.0.
        // Formula: is_heavy if (current_tick % (1.0 / dilation_factor) == 0)
        let frame_interval = (SimFixed::from_num(1) / self.dilation_factor).to_num::<u64>();
        let is_heavy_frame = (self.current_tick % frame_interval == 0) || has_priority_event;

        if is_heavy_frame {
            self.simulate_physics_step(); 

            // 3. Execute Scheduled Controller Commands
            self.pending_global_events.retain(|_, cmd| {
                if let ControllerCommand::ExecuteGlobalEvent {
                    epicenter,
                    event_id,
                    geometry,
                    target_filters,
                    pulse_interval_ticks,
                    duration_ticks,
                    execute_at_tick,
                    caster_id,
                    ability_id,
                    data_epoch,
                    context,
                } = cmd {
                    // Ideal execution is `==`. `>=` acts as an emergency fallback if the 
                    // reliable TCP packet was severely delayed due to a datacenter outage.
                    if self.current_tick >= *execute_at_tick {
                        // Deterministic Epoch Pinning:
                        // Execute only under the same data dictionary used during pre-roll.
                        if *data_epoch != self.current_data_epoch {
                            if !self.try_activate_data_epoch(*data_epoch) {
                                // Keep queued and retry next frame rather than detonating under the wrong balance set.
                                return true;
                            }
                        }
                        
                        self.resolve_global_event_effect(
                            *epicenter,
                            geometry.clone(),
                            target_filters.clone(),
                            *pulse_interval_ticks,
                            *duration_ticks,
                            *event_id,
                            *caster_id,
                            *ability_id,
                            *data_epoch,
                            context.clone(),
                        );
                        
                        // Pulse Lifecycle Management
                        if let (Some(interval), Some(duration)) = (pulse_interval_ticks, duration_ticks) {
                            if *duration > *interval {
                                *duration -= *interval;
                                *execute_at_tick += *interval as u64;
                                return true; // Keep in queue for the next pulse
                            }
                        }
                        return false; // Final execution, remove from queue
                    }
                }
                true // Keep in queue for the future
            });

            // 4. Process Internal Mesh Events (Draining the persistent queue)
            for event in self.internal_inbox.drain(..) {
                // Internal Relay Deduplication
                if self.processed_proposals.contains(&event.event_id) { continue; }
                self.processed_proposals.insert(event.event_id, true);
                
                self.resolve_action(event.payload, event.actor_id, event.origin_tick, None, event.data_epoch);
            }

            // 5. Process External Proposals (Draining both persistent queue and stale buffer)
            let mut next_tick_stale_buffer = BoundedQueue::new(1000); // 1,000 capacity protects a 400-player Arbiter
            let mut latest_movement_by_actor: HashMap<EntityID, (ActionProposal, u64)> = HashMap::new();
            
            // We combine new arrivals with anything we held over from the previous tick.
            // Movement packets are coalesced to latest-per-actor before validation to reduce pressure.
            let all_proposals = self.external_inbox.drain(..).map(|p| (p, self.current_tick))
                .chain(self.stale_proposals_buffer.drain(..));

            for (proposal, local_arrival_tick) in all_proposals {
                if matches!(&proposal.payload, ActionPayload::Movement { .. }) {
                    latest_movement_by_actor.insert(proposal.actor_id, (proposal, local_arrival_tick));
                    continue;
                }

                // --- Data Epoch Handshake Validation ---
                if proposal.data_epoch < self.current_data_epoch {
                    self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                        proposal_id: proposal.proposal_id,
                        reason: "Data Epoch Mismatch".to_string()
                    });
                    continue;
                } else if proposal.data_epoch > self.current_data_epoch {
                    if !self.try_activate_data_epoch(proposal.data_epoch) {
                        if self.current_tick.saturating_sub(local_arrival_tick) >= MAX_EVENT_AGE_TICKS {
                            self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: proposal.proposal_id,
                                reason: "Data Epoch Sync Timeout".to_string()
                            });
                        } else {
                            if next_tick_stale_buffer.is_full() {
                                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                                    proposal_id: proposal.proposal_id,
                                    reason: "Arbiter Queue Saturated".to_string()
                                });
                            } else {
                                next_tick_stale_buffer.push_back((proposal, local_arrival_tick));
                            }
                        }
                        continue;
                    }
                }

                // --- Topology Epoch Handshake Validation ---
                if proposal.topology_epoch < self.topology_epoch {
                    self.forward_to_correct_arbiter(proposal); // Proxy is stale
                    continue;
                } else if proposal.topology_epoch > self.topology_epoch {
                    // Arbiter is stale. Buffer until the Controller's topology update arrives.
                    // Timeout is based purely on the Arbiter's local clock, avoiding drift false-positives.
                    // We use MAX_EVENT_AGE_TICKS (60 ticks / 1.0s) to unify the engine's latency budget,
                    // allowing TCP up to 3 retransmissions to deliver the map update before we refund the player.
                    if self.current_tick.saturating_sub(local_arrival_tick) >= MAX_EVENT_AGE_TICKS {
                        self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                            proposal_id: proposal.proposal_id,
                            reason: "Topology Sync Timeout (Arbiter Stale)".to_string()
                        });
                    } else {
                        // Explicit rejection on saturation (never silent drop).
                        if next_tick_stale_buffer.is_full() {
                            self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: proposal.proposal_id,
                                reason: "Arbiter Queue Saturated".to_string()
                            });
                        } else {
                            next_tick_stale_buffer.push_back((proposal, local_arrival_tick));
                        }
                    }
                    continue;
                }

                if self.processed_proposals.contains(&proposal.proposal_id) { continue; }
                self.processed_proposals.insert(proposal.proposal_id, true);
                
                if self.is_in_overlap_buffer(proposal.actor_id) {
                    self.relay_to_neighbors(MeshInternalEvent {
                        event_id: proposal.proposal_id,
                        source_arbiter_id: self.arbiter_id,
                        actor_id: Some(proposal.actor_id),
                        origin_tick: proposal.origin_tick,
                        data_epoch: proposal.data_epoch,
                        payload: proposal.payload.clone()
                    });
                }

                self.resolve_action(proposal.payload, Some(proposal.actor_id), proposal.origin_tick, Some(proposal.proposal_id), proposal.data_epoch);
            }

            // Process latest movement per actor after coalescing (no per-proposal terminal acks).
            for (_, (proposal, local_arrival_tick)) in latest_movement_by_actor {
                if proposal.data_epoch > self.current_data_epoch {
                    if !self.try_activate_data_epoch(proposal.data_epoch)
                        && self.current_tick.saturating_sub(local_arrival_tick) < MAX_EVENT_AGE_TICKS
                    {
                        let _ = next_tick_stale_buffer.try_push_back((proposal, local_arrival_tick));
                        continue;
                    }
                } else if proposal.data_epoch < self.current_data_epoch {
                    // Movement has no terminal ack; stale movement is dropped/coalesced.
                    continue;
                }

                if proposal.topology_epoch < self.topology_epoch {
                    self.forward_to_correct_arbiter(proposal);
                    continue;
                } else if proposal.topology_epoch > self.topology_epoch {
                    if self.current_tick.saturating_sub(local_arrival_tick) < MAX_EVENT_AGE_TICKS {
                        let _ = next_tick_stale_buffer.try_push_back((proposal, local_arrival_tick));
                    }
                    continue;
                }
                self.resolve_action(proposal.payload, Some(proposal.actor_id), proposal.origin_tick, None, proposal.data_epoch);
            }
            
            // Save the held-over proposals for the next simulation tick
            self.stale_proposals_buffer = next_tick_stale_buffer;
        } else {
            // Light Frame: External/Internal inboxes are NOT drained. They accumulate safely.
            self.simulate_light_physics();
        }

        // Integrate dead-reckoned Ghosts with low-cost anomaly guards.
        self.integrate_ghosts_lightweight();
        self.broadcast_ghosts_to_neighbors();
        self.broadcast_with_interest_management(); 
        self.tick_merge_forwarding();
    }

    // --- Ghost Integration (Low-Cost / Anomaly-Gated) ---
    fn integrate_ghosts_lightweight(&mut self) {
        let mut expired = Vec::new();
        for (ghost_id, ghost) in self.ghost_entities.iter_mut() {
            // Expire stale ghosts so downstream rendering never drifts indefinitely.
            if self.current_tick.saturating_sub(ghost.last_update_tick) > GHOST_RENDER_TTL_TICKS {
                expired.push(*ghost_id);
                continue;
            }

            // Degraded ghosts stay frozen briefly to avoid tunneling artifacts until correction arrives.
            if matches!(ghost.quality, GhostQuality::Degraded) && self.current_tick < ghost.degraded_until_tick {
                self.ghost_grid.upsert(*ghost_id, ghost.position);
                continue;
            }
            ghost.position += ghost.velocity;
            self.ghost_grid.upsert(*ghost_id, ghost.position);
        }

        for ghost_id in expired {
            self.ghost_entities.remove(&ghost_id);
            self.ghost_grid.remove(ghost_id);
        }
    }

    // Called by the network layer when an unreliable UDP GhostUpdate arrives.
    fn on_ghost_update_unreliable(&mut self, update: GhostUpdate) {
        if update.source_tick + MAX_EVENT_AGE_TICKS < self.current_tick { return; }

        let ghost = self.ghost_entities.entry(update.entity_id).or_insert(GhostState2D {
            entity_id: update.entity_id,
            authoritative_arbiter_id: update.source_arbiter_id,
            position: update.position,
            velocity: update.velocity,
            last_valid_position: update.position,
            last_update_tick: update.source_tick,
            movement_class: update.movement_class,
            quality: GhostQuality::Healthy,
            degraded_until_tick: 0,
        });

        let dt = self.current_tick.saturating_sub(ghost.last_update_tick);
        let expected_max = max_allowed_displacement(ghost.movement_class, dt) + GHOST_ANOMALY_MARGIN;
        let observed = ghost.position.distance_to(update.position);
        let anomaly = observed > expected_max
            || matches!(update.movement_class, GhostMovementClass::HighSpeed | GhostMovementClass::Teleport);

        if anomaly {
            // Cost control: sweep only against nearby static cells (broadphase), never full-map geometry.
            let candidates = self.static_grid.query_segment_aabb(ghost.position, update.position);
            if segment_hits_static(ghost.position, update.position, &candidates) {
                ghost.position = first_valid_contact_or(ghost.last_valid_position);
                ghost.velocity = Vec2F::ZERO;
                ghost.quality = GhostQuality::Degraded;
                ghost.degraded_until_tick = self.current_tick + GHOST_DEGRADED_TTL_TICKS;
                self.request_ghost_correction_rudp(update.entity_id, update.source_arbiter_id);
                return;
            }
        }

        ghost.position = update.position;
        ghost.velocity = update.velocity;
        ghost.last_valid_position = update.position;
        ghost.last_update_tick = update.source_tick;
        ghost.authoritative_arbiter_id = update.source_arbiter_id;
        ghost.movement_class = update.movement_class;
        ghost.quality = GhostQuality::Healthy;
        self.ghost_grid.upsert(update.entity_id, ghost.position);
    }

    // Reliable correction path reuses the same integration logic but arrives over authenticated RUDP.
    fn on_ghost_update_reliable(&mut self, auth: MeshAuthHeader, update: GhostUpdate) {
        if !self.verify_mesh_auth(&auth, &update) { return; }
        self.on_ghost_update_unreliable(update);
    }

    fn request_ghost_correction_rudp(&mut self, entity_id: EntityID, owner_arbiter_id: u32) {
        self.send_to_arbiter(owner_arbiter_id, MeshInternalEvent {
            event_id: generate_uuid(),
            source_arbiter_id: self.arbiter_id,
            actor_id: None,
            origin_tick: self.current_tick,
            data_epoch: self.current_data_epoch,
            payload: ActionPayload::RequestGhostCorrection {
                entity_id,
                requester_arbiter_id: self.arbiter_id,
            },
        });
    }

    fn send_ghost_update_rudp(&mut self, target_arbiter_id: u32, update: GhostUpdate) {
        self.network.send_rudp(target_arbiter_id, update);
    }

    // --- Intra-Mesh Ghost Propagation (Geometric) ---
    fn broadcast_ghosts_to_neighbors(&mut self) {
        // Purely stateless geometric calculation: No pub/sub tracking needed.
        for entity in self.entities.values() {
            // Find all sibling Arbiters whose AABB intersects the entity's visibility radius
            let overlapping_neighbors = self.local_grid.get_neighbors_intersecting_radius(entity.position, VISIBLE_RADIUS);
            
            for neighbor_id in overlapping_neighbors {
                // Delta-compression: Only send if velocity changed or it's a keyframe
                if entity.kinematics_changed() || self.current_tick % KEYFRAME_INTERVAL == 0 {
                    // Include movement class so receivers can anomaly-gate expensive validation.
                    let ghost_update = entity.get_ghost_update(self.current_tick);
                    // Sent via Unreliable UDP (it is fine if it drops, dead-reckoning covers it)
                    self.send_to_arbiter_unreliable(neighbor_id, ghost_update);
                }
            }
        }
    }

    fn resolve_action(&mut self, payload: ActionPayload, source_actor_id: Option<EntityID>, origin_tick: u64, original_proposal_id: Option<UUID>, data_epoch: u32) {
        match payload {
            ActionPayload::TargetedAbility { target_id, ability_id } => {
                let actor_id = source_actor_id.expect("TargetedAbility requires a source actor");
                
                let local_target_pos = self.entities.get(&target_id).and_then(|target| {
                    if self.has_jurisdiction_over(target.position) { Some(target.position) } else { None }
                });
                let ghost_target_owner = self.ghost_entities.get(&target_id).map(|ghost| ghost.authoritative_arbiter_id);
                let ghost_target_pos = self.ghost_entities.get(&target_id).map(|ghost| ghost.position);

                let target_pos = if let Some(pos) = local_target_pos {
                    pos
                } else if let Some(pos) = ghost_target_pos {
                    pos
                } else {
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                            proposal_id: prop_id,
                            reason: "Invalid Target".to_string()
                        });
                    }
                    return;
                };

                // Safe Actor Lookup: The attacker might be a Real entity or a Ghost (if relayed)
                let actor_pos = match self.get_entity_or_ghost_position(actor_id) {
                    Some(pos) => pos,
                    None => {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: prop_id,
                                reason: "Unknown Attacker".to_string()
                            });
                        }
                        return; // Attacker is completely unknown due to dropped packets; safely abort.
                    },
                };

                let ability = get_ability_data(ability_id, data_epoch);
                
                // --- Phase 1: The Pre-Roll (Originating Server Authority) ---
                // The Arbiter securely calculates the offensive math using its authoritative state,
                // completely ignoring any math the client/Edge Node might have attempted to claim.
                let context = self.generate_combat_context(actor_id, &ability);

                // --- Global Event Escalation ---
                if ability.geometry.get_max_extent() > MAX_SPELL_RANGE {
                    if self.mesh_controller_client.is_offline() {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed { 
                                proposal_id: prop_id,
                                reason: "Mesh Controller Unreachable".to_string() 
                            });
                        }
                        return;
                    }
                    // Pass the full combat identity up to the Controller so it can construct the downstream command
                    self.mesh_controller_client.escalate_event(
                        actor_id,
                        ability_id, 
                        data_epoch,
                        context.clone(),
                        target_pos,
                        ability.geometry.clone(),
                        ability.target_filters.clone(),
                        ability.pulse_interval_ticks,
                        ability.duration_ticks,
                    );
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                    return;
                }

                let distance = actor_pos.distance_to(target_pos);
                let prediction_tolerance = calculate_prediction_drift(origin_tick, self.current_tick);
                let effective_range = ability.max_range + prediction_tolerance;

                if distance <= effective_range {
                    if local_target_pos.is_some() {
                        self.apply_combat_math(target_id, Some(actor_id), context.clone(), distance);
                    } else if let Some(owner_arbiter_id) = ghost_target_owner {
                        // Border-targeted cast: actor-owner pre-rolls context, target-owner applies mutation.
                        self.send_to_arbiter(owner_arbiter_id, MeshInternalEvent {
                            event_id: generate_uuid(),
                            source_arbiter_id: self.arbiter_id,
                            actor_id: Some(actor_id),
                            origin_tick,
                            data_epoch,
                            payload: ActionPayload::InternalPreparedHit {
                                target_id,
                                context: context.clone(),
                            },
                        });
                    }
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                } else if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                        proposal_id: prop_id,
                        reason: "Out of Range".to_string()
                    });
                }
            },
            ActionPayload::InternalPreparedHit { target_id, context } => {
                // Internal-only path: context is already authoritative and must not be recomputed.
                let target_pos = match self.entities.get(&target_id) {
                    Some(target) if self.has_jurisdiction_over(target.position) => target.position,
                    _ => return, // Internal relay may race ownership during boundary transitions; intentional safe drop.
                };

                let distance = match source_actor_id.and_then(|id| self.get_entity_or_ghost_position(id)) {
                    Some(attacker_pos) => attacker_pos.distance_to(target_pos),
                    None => SimFixed::from_num(0),
                };

                self.apply_combat_math(target_id, source_actor_id, context, distance);
            },
            ActionPayload::GroundTargetedAbility { destination, ability_id } => {
                let actor_id = source_actor_id.expect("GroundTargetedAbility requires a source actor");
                
                let actor_pos = match self.get_entity_or_ghost_position(actor_id) {
                    Some(pos) => pos,
                    None => {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: prop_id,
                                reason: "Unknown Attacker".to_string()
                            });
                        }
                        return;
                    },
                };

                let ability = get_ability_data(ability_id, data_epoch);
                let context = self.generate_combat_context(actor_id, &ability);

                // --- Global Event Escalation (Ground-Targeted) ---
                if ability.geometry.get_max_extent() > MAX_SPELL_RANGE {
                    if self.mesh_controller_client.is_offline() {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed { 
                                proposal_id: prop_id,
                                reason: "Mesh Controller Unreachable".to_string() 
                            });
                        }
                        return;
                    }
                    
                    // Escalate using the raw ground coordinate (destination) as the epicenter
                    self.mesh_controller_client.escalate_event(
                        actor_id,
                        ability_id, 
                        data_epoch,
                        context.clone(),
                        destination, // Ground Coordinate
                        ability.geometry.clone(),
                        ability.target_filters.clone(),
                        ability.pulse_interval_ticks,
                        ability.duration_ticks,
                    );
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                    return;
                }

                // Standard Local Resolution
                let distance_to_cast = actor_pos.distance_to(destination);
                let prediction_tolerance = calculate_prediction_drift(origin_tick, self.current_tick);
                let effective_cast_range = ability.max_range + prediction_tolerance;

                if distance_to_cast <= effective_cast_range {
                    // Because it is ground-targeted, the Arbiter spawns an ephemeral ZoneActor or 
                    // instantly applies an AoE blast at that specific [x, y] coordinate.
                    // CRITICAL FIX: We MUST use the original_proposal_id to guarantee that if this 
                    // proposal was relayed to neighboring Arbiters, they all generate the exact same 
                    // UUID for the resulting ImpactEvent, allowing the Ledger to prevent double-damage.
                    let event_uuid = original_proposal_id.unwrap_or_else(|| generate_uuid());
                    self.resolve_aoe_effect(destination, ability.radius, event_uuid, actor_id, ability_id, data_epoch, context);
                    if let Some(prop_id) = original_proposal_id {
                        self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                    }
                } else if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                        proposal_id: prop_id,
                        reason: "Out of Range".to_string()
                    });
                }
            },
            ActionPayload::RequestGhostCorrection { entity_id, requester_arbiter_id } => {
                // Owner-side reliable repair response for degraded ghost correction requests.
                if let Some(entity) = self.entities.get(&entity_id) {
                    if !self.has_jurisdiction_over(entity.position) { return; }
                    let mut keyframe = entity.get_ghost_update(self.current_tick);
                    keyframe.is_keyframe = true; // Force full state correction semantics.
                    self.send_ghost_update_rudp(requester_arbiter_id, keyframe); // Reliable RUDP path.
                }
            },
            ActionPayload::ImpactEvent { impact_id, target_ids, epicenter, geometry, impact_tick, context } => {
                // Network Discard Window: Drop packets that are older than our ledger's memory capacity.
                // Using `>=` ensures we don't accidentally write to the bucket currently being cleared.
                if self.current_tick.saturating_sub(impact_tick) >= MAX_EVENT_AGE_TICKS { return; }

                for target_id in target_ids {
                    let ledger_key = (impact_id, target_id);
                    let bucket_index = (impact_tick % MAX_EVENT_AGE_TICKS) as usize;
                    if self.event_idempotency_ledger[bucket_index].contains(&ledger_key) { continue; }

                    // SCENARIO A: Target is a REAL entity owned by this Arbiter
                    if let Some(target) = self.entities.get(&target_id) {
                        if self.has_jurisdiction_over(target.position) {
                            // --- Final Mathematical Validation (Ghost Drift Check) ---
                            // Because the reporting Arbiter may have been aiming at a dead-reckoned Ghost,
                            // their coordinates for the explosion might slightly miss the true entity.
                            // We allow a small 'ghost_drift_tolerance' to favor the shooter and prevent phantom dodges,
                            // while strictly preserving the geometric integrity of Cones and Boxes.
                            let distance_to_impact = target.position.distance_to(epicenter);
                            let ghost_drift_tolerance = calculate_ghost_drift(impact_tick, self.current_tick);
                            
                            if geometry.is_inside_with_tolerance(target.position, epicenter, ghost_drift_tolerance) {
                                self.event_idempotency_ledger[bucket_index].insert(ledger_key);
                                self.apply_combat_math(target_id, source_actor_id, context.clone(), distance_to_impact);
                            }
                        }
                        continue;
                    }

                    // SCENARIO B: Target is a GHOST entity owned by a neighboring Arbiter
                    if let Some(ghost) = self.ghost_entities.get(&target_id) {
                        if ghost.position.is_inside_geometry(epicenter, &geometry) {
                            self.event_idempotency_ledger[bucket_index].insert(ledger_key);
                            
                            // Package the ImpactEvent and relay it to the Ghost's true owner
                            let relay_payload = MeshInternalEvent {
                                event_id: generate_uuid(), // Unique envelope ID for this relay hop
                                source_arbiter_id: self.arbiter_id,
                                actor_id: source_actor_id,
                                origin_tick: impact_tick,
                                data_epoch, // CRITICAL FIX: Pass the data_epoch forward so the receiving Arbiter uses the correct dictionary
                                // Preserve original impact_id for destination ledger deduplication
                                payload: ActionPayload::ImpactEvent {
                                    impact_id, 
                                    target_ids: vec![target_id], 
                                    epicenter,
                                    geometry: geometry.clone(),
                                    impact_tick,
                                    context: context.clone(),
                                }
                            };
                            
                            // Dispatched via Reliable-UDP (RUDP). If dropped, the network layer will retry.
                            // The receiving Arbiter's Idempotency Ledger will deduplicate any retries.
                            self.send_to_arbiter(ghost.authoritative_arbiter_id, relay_payload);
                        }
                    }
                }
            },
            ActionPayload::SpawnProjectile { direction, target_id, spell_id } => {
                let actor_id = source_actor_id.expect("SpawnProjectile requires a source actor");
                let actor_pos = match self.get_entity_or_ghost_position(actor_id) {
                    Some(pos) => pos,
                    None => {
                        if let Some(prop_id) = original_proposal_id {
                            self.send_downstream(actor_id, DownstreamPayload::ActionFailed {
                                proposal_id: prop_id,
                                reason: "Unknown Attacker".to_string()
                            });
                        }
                        return;
                    }
                };

                let ability = get_ability_data(spell_id, data_epoch);
                // Validate cooldowns, resources, and CC states here (omitted for brevity)
                let context = self.generate_combat_context(actor_id, &ability);

                let projectile = ProjectileActor {
                    projectile_id: original_proposal_id.unwrap_or_else(|| generate_uuid()),
                    owner_id: actor_id,
                    target_id,
                    position: actor_pos,
                    // Fixed-point vector math
                    velocity: direction.normalize() * ability.projectile_speed, 
                    remaining_lifetime_ticks: ability.duration_ticks.unwrap_or(120),
                    fuse_remaining_ticks: ability.fuse_timer_ticks.unwrap_or(0),
                    pierce_remaining: ability.pierce_count.unwrap_or(0),
                    data_epoch,
                    damage_origin: DamageOrigin::DirectCast,
                    proc_depth: 0,
                    authoritative_arbiter_id: self.arbiter_id,
                    handoff_topology_epoch: self.topology_epoch,
                    handoff_cutover_tick: self.current_tick,
                    handoff_seq: 0,
                    handoff_state: ProjectileHandoffState::Owned,
                    impact_sequence: 0,
                    spell_data: ability,
                };
                
                self.projectiles.insert(projectile.projectile_id, projectile);

                if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                }
            },
            ActionPayload::Movement { position, velocity, rotation } => {
                let actor_id = source_actor_id.expect("Movement requires a source actor");
                if let Some(entity) = self.entities.get_mut(&actor_id) {
                    if !self.has_jurisdiction_over(entity.position) { return; }
                    
                    // Anti-Cheat: Validate displacement against max theoretical speed
                    let dt = self.current_tick.saturating_sub(entity.last_movement_tick);
                    let max_displacement = (entity.stats.move_speed * SimFixed::from_num(dt)) + GHOST_ANOMALY_MARGIN;
                    
                    if entity.position.distance_to(position) <= max_displacement {
                        // Validate against static geometry (Navmesh)
                        if !self.static_grid.is_colliding(position) {
                            entity.position = position;
                            entity.velocity = velocity;
                            entity.rotation = rotation;
                            entity.last_movement_tick = self.current_tick;
                            self.local_grid.upsert(actor_id, position);
                        } else {
                            // Hit a wall, rubber-band back to last valid
                            self.trigger_client_rollback(actor_id);
                        }
                    } else {
                        // Speed hack detected, rubber-band back
                        self.trigger_client_rollback(actor_id);
                    }
                }
            },
            ActionPayload::UseConsumable { item_id } => {
                let actor_id = source_actor_id.unwrap();
                // 1. Verify inventory via asynchronous Meta Service check (or pre-synced local SoftState)
                // 2. Apply soft state changes (e.g., add HP, start potion cooldown)
                if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                }
            },
            ActionPayload::Interact { target_entity } => {
                let actor_id = source_actor_id.unwrap();
                // Logic: distance check, type check (NPC, Loot, Resource), trigger UI/Quest event via Meta Services
                if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                }
            }
        }
    }

    // --- Deep RPG Combat Engine ---
    // This centralizes all complex ARPG/MOBA math (Armor, Resistance, Weight, Falloff)
    // ensuring it only runs on the true authoritative owner of the target.
    // (See ../2-gameplay-and-design/01-rpg-mechanics-and-state.md for the full mitigation formula including Evasion and Block).
    // 
    // RUST BORROW CHECKER NOTE: This function takes a mutable borrow of the `victim`. 
    // You cannot simultaneously take a mutable borrow of the `attacker` from `self.entities` 
    // (e.g., to apply Lifesteal or Thorns damage) without triggering a compiler error. 
    // Instead, "reflection" mechanics must push a new `MeshInternalEvent` with
    // `ActionPayload::InternalPreparedHit` to the `internal_inbox`.
    fn apply_combat_math(&mut self, target_id: EntityID, attacker_id: Option<EntityID>, context: CombatContext, distance: SimFixed) {
        let mut victim = self.entities.get_mut(&target_id).unwrap();
        
        if victim.is_invulnerable { return; }

        // --- Healing vs Damage Branch ---
        if context.damage_type == 100 { // 100 = HEALING
            victim.hp = std::cmp::min(victim.max_hp, victim.hp + context.base_damage as i32);
            return; 
        }

        // 1. Distance Falloff
        let distance_multiplier = calculate_falloff(distance);
        let mut incoming_damage = context.base_damage as SimFixed * distance_multiplier;

        // 2. Resistance & Penetration Mitigation
        // Note: For brevity, Evasion and Block checks are omitted here. See ../2-gameplay-and-design/01-rpg-mechanics-and-state.md.
        if context.damage_type != 99 {
            let mut effective_resistance = victim.defense.resistances[context.damage_type as usize];
            
            // Fixed-point deterministic math using F32 literal macros/conversions
            effective_resistance *= (SimFixed::from_num(1) - context.armor_penetration_pct);
            effective_resistance -= context.armor_penetration_flat;
            
            effective_resistance = effective_resistance.clamp(SimFixed::from_num(-100), SimFixed::from_num(85));
            
            let one_hundred = SimFixed::from_num(100);
            if effective_resistance > SimFixed::from_num(0) {
                incoming_damage *= (SimFixed::from_num(1) - (effective_resistance / one_hundred));
            } else {
                incoming_damage *= (SimFixed::from_num(1) + (effective_resistance.abs() / one_hundred));
            }
        }

        // 3. Application
        victim.hp -= incoming_damage as i32;

        // 4. Physics Engine (Knockback vs Weight)
        if context.knockback_force > 0 {
            victim.velocity.x += calculate_knockback(context.knockback_force, victim.stats.weight);
        }

        // 5. Hard State Trigger
        if victim.hp <= 0 {
            self.emit_hard_state(HardEvent::PlayerDied { killer: attacker_id, victim: target_id });
        }
        
        // 6. Reactive Procs (Lifesteal / Thorns)
        // We push to the internal inbox to be processed sequentially, safely bypassing the borrow checker.
        // Safety Rule: Reactive effects only trigger from DIRECT hits and only at depth 0.
        // This prevents infinite loops (e.g., Thorns-vs-Thorns ping-pong).
        if let Some(atk_id) = attacker_id {
            if victim.has_thorns_buff()
                && matches!(context.damage_origin, DamageOrigin::DirectCast)
                && context.proc_depth == 0
            {
                self.internal_inbox.push_back(MeshInternalEvent {
                    event_id: generate_uuid(),
                    source_arbiter_id: self.arbiter_id,
                    actor_id: Some(target_id),
                    origin_tick: self.current_tick,
                    data_epoch: self.current_data_epoch, // CRITICAL FIX: Use the data epoch, not the topology map version!
                    payload: ActionPayload::InternalPreparedHit {
                        target_id: atk_id,
                        context: CombatContext { 
                            base_damage: 15, 
                            damage_type: 99, // TRUE DAMAGE
                            knockback_force: SimFixed::from_num(0), 
                            armor_penetration_pct: SimFixed::from_num(0),
                            armor_penetration_flat: SimFixed::from_num(0),
                            is_critical_strike: false,
                            status_effect_id: None,
                            damage_origin: DamageOrigin::ReactiveProc,
                            proc_depth: context.proc_depth.saturating_add(1),
                        }
                    }
                });
            }
        }
    }

    // Safely retrieves coordinates for an entity, checking both local ownership and Ghost memory
    fn get_entity_or_ghost_position(&self, id: EntityID) -> Option<Vec2F> {
        if let Some(entity) = self.entities.get(&id) { return Some(entity.position); }
        if let Some(ghost) = self.ghost_entities.get(&id) { return Some(ghost.position); }
        None
    }

    fn process_controller_command(&mut self, command: ControllerCommand) {
        match command {
            ControllerCommand::UpdateTopology { .. } => { /* ... */ }
            ControllerCommand::BeginMerge { merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch, .. } => {
                self.on_begin_merge_command(merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch);
            }
            ControllerCommand::CommitMerge { merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch } => {
                self.on_commit_merge_command(merge_id, winner_arbiter_id, loser_arbiter_id, cutover_tick, new_epoch);
            }
            ControllerCommand::FinalizeMerge { merge_id, winner_arbiter_id, loser_arbiter_id, new_epoch } => {
                self.on_finalize_merge_command(merge_id, winner_arbiter_id, loser_arbiter_id, new_epoch);
            }
            ControllerCommand::SyncHeartbeat { controller_shard_tick } => {
                // The Metronome Corrector
                let diff = (controller_shard_tick as i64) - (self.current_tick as i64);
                // Adjust our frame sleep target (e.g., +/- 100 microseconds per frame) to smoothly catch up 
                // or slow down without causing a massive temporal snap that would break ghost extrapolation.
                self.frame_pacing_offset_micros = (diff * 50).clamp(-1000, 1000); 
            }
            ControllerCommand::PrepareDataEpoch { new_epoch, asset_uri, checksum } => {
                // Offload the I/O to a background thread so the 60Hz loop never stalls.
                // The background thread will download, parse, and push the new dictionary 
                // into a lock-free queue that the Arbiter reads from at the top of tick().
                self.asset_loader.async_fetch_and_parse(new_epoch, asset_uri, checksum);
            }
            _ => { /* ExecuteGlobalEvent and Splits handled in scheduler block */ }
        }
    }

    fn simulate_physics_step(&mut self) {
        // 1. Resolve discrete physics steps (Movement integration, knockback decay)
        self.apply_kinematics();
        
        // 2. Process all active Status Effects (DoTs, HoTs, CC)
        self.tick_status_effects();
    }

    fn tick_status_effects(&mut self) {
        for (entity_id, entity) in self.entities.iter_mut() {
            let mut expired = Vec::new();
            
            for (i, effect) in entity.active_status_effects.iter_mut().enumerate() {
                if self.current_tick >= effect.next_pulse_tick {
                    // Trigger the damage/healing payload
                    if let Some(context) = &effect.pulse_context {
                        // We push to the internal inbox to bypass the borrow checker
                        // and ensure the mitigation math runs cleanly in sequence.
                        self.internal_inbox.push_back(MeshInternalEvent {
                            event_id: generate_uuid(),
                            source_arbiter_id: self.arbiter_id,
                            actor_id: Some(effect.caster_id),
                            origin_tick: self.current_tick,
                            data_epoch: effect.data_epoch,
                            payload: ActionPayload::InternalPreparedHit {
                                target_id: *entity_id,
                                context: context.clone(),
                            }
                        });
                    }
                    
                    // Reset the pulse timer based on the SpellData (e.g., 60 ticks for a 1-second DoT)
                    let spell_data = get_ability_data(effect.effect_id, effect.data_epoch);
                    effect.next_pulse_tick = self.current_tick + spell_data.pulse_interval_ticks.unwrap_or(60) as u64;
                }
                
                effect.remaining_ticks = effect.remaining_ticks.saturating_sub(1);
                if effect.remaining_ticks == 0 {
                    expired.push(i);
                }
            }
            
            // Remove expired buffs (iterate in reverse to avoid index shifting)
            for i in expired.into_iter().rev() {
                entity.active_status_effects.remove(i);
            }
        }
    }

    // Lock-Free Ownership check
    fn has_jurisdiction_over(&self, target_point: Vec2F) -> bool {
        for sibling in self.get_overlapping_siblings(target_point) {
            if sibling.rtree_depth > self.rtree_depth { return false; }
            if sibling.rtree_depth == self.rtree_depth && sibling.arbiter_id < self.arbiter_id { return false; }
        }
        true
    }

    // --- Interest Management (Downstream Bandwidth Control) ---
    fn broadcast_with_interest_management(&mut self, live_config: &LiveConfig) {
        for proxy_id in self.connected_proxies() {
            let proxy_pos = self.get_proxy_position(proxy_id);
            let mut proxy_payload = Vec::new();
            let mut seen = HashSet::new();

            let close_entities = self.local_grid.query_radius(proxy_pos, live_config.combat_radius);
            for entity in close_entities {
                seen.insert(entity.id);
                proxy_payload.push(entity.get_full_update()); // is_authoritative_owner = true
            }

            // Include border-neighbor ghosts for rendering/raycast consistency at Arbiter seams.
            let close_ghost_ids = self.ghost_grid.query_radius(proxy_pos, live_config.combat_radius);
            for ghost_id in close_ghost_ids {
                if seen.contains(&ghost_id) { continue; } // Prefer local owner update if both exist.
                if let Some(ghost) = self.ghost_entities.get(&ghost_id) {
                    proxy_payload.push(ghost.get_full_update()); // is_ghost = true
                    seen.insert(ghost_id);
                }
            }

            if self.current_tick % live_config.keyframe_interval_ticks == 0 {
                let far_entities = self.local_grid.query_donut(proxy_pos, live_config.combat_radius, live_config.visible_radius);
                for entity in far_entities {
                    if seen.insert(entity.id) {
                        proxy_payload.push(entity.get_keyframe_update());
                    }
                }

                let far_ghost_ids = self.ghost_grid.query_donut(proxy_pos, live_config.combat_radius, live_config.visible_radius);
                for ghost_id in far_ghost_ids {
                    if !seen.insert(ghost_id) { continue; }
                    if let Some(ghost) = self.ghost_entities.get(&ghost_id) {
                        proxy_payload.push(ghost.get_keyframe_update()); // is_ghost = true
                    }
                }
            }
            self.network.send_to(proxy_id, proxy_payload);
        }
    }
}

---

### 3.3 Ephemeral Actors (Projectiles)

To support lock-free cross-boundary combat and complex multi-hit spells, projectiles are not treated as raw spatial vectors. They are instantiated as independent "Thinker" Actors hosted by the Spatial Arbiter. 

The Projectile Actor is the sole authority on *who it hits*, generating a globally unique `UUID` for every explosion/impact. This allows the Spatial Arbiter to flawlessly deduplicate boundary overlaps using the Idempotency Ledger.

```rust
enum ProjectileHandoffState {
    Owned,
    TransferPending {
        to_arbiter_id: u32,
        handoff_seq: u64,
        commit_tick: u64,
        acked: bool,
    },
    Shadow, // Replica kept briefly after commit; never simulates
}

struct ProjectileActor {
    projectile_id: UUID,
    owner_id: EntityID,
    target_id: Option<EntityID>,
    position: Vec2F,
    velocity: Vec2F,
    remaining_lifetime_ticks: u32,
    fuse_remaining_ticks: u32,
    pierce_remaining: u8,
    data_epoch: u32,
    damage_origin: DamageOrigin, // Inherited from the launch context
    proc_depth: u8,              // Propagated for deterministic proc recursion limits
    authoritative_arbiter_id: u32, // The only Arbiter allowed to advance this projectile
    handoff_topology_epoch: u32,    // Topology version where authority was last assigned
    handoff_cutover_tick: u64,      // Tick where current authority became active
    handoff_seq: u64,               // Monotonic ownership transfer sequence
    handoff_state: ProjectileHandoffState,
    impact_sequence: u32,           // Monotonic owner-local sequence for deterministic impact UUID derivation
    spell_data: SpellData,
}

impl ProjectileActor {
    // Projectiles run their own tick within the Host Arbiter's simulation loop.
    // The Arbiter passes in the current_target_pos (resolved from Real entities or dead-reckoned Ghosts).
    fn tick(&mut self, local_hitboxes: &Vec<Hitbox>, current_target_pos: Option<Vec2F>) -> Option<MeshInternalEvent> {
        // Split/Handoff safety: shadow replicas must never simulate or emit impacts.
        if self.authoritative_arbiter_id != current_arbiter_id() { return None; }

        // Runtime cross-boundary transfer: lightweight RUDP Prepare/Ack/Commit.
        if let ProjectileHandoffState::TransferPending { to_arbiter_id, handoff_seq, commit_tick, acked } = self.handoff_state {
            if acked && current_shard_tick() >= commit_tick {
                self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Commit {
                    projectile_id: self.projectile_id,
                    handoff_seq,
                    new_owner_arbiter_id: to_arbiter_id,
                    commit_tick,
                });
                self.authoritative_arbiter_id = to_arbiter_id;
                self.handoff_cutover_tick = commit_tick;
                self.handoff_state = ProjectileHandoffState::Shadow;
                return None;
            }
            // Still authoritative until commit; continue simulation and retry Prepare via network layer if needed.
        } else if self.will_cross_neighbor_boundary_next_step() {
            self.handoff_seq = self.handoff_seq.saturating_add(1);
            let destination = choose_neighbor_by_depth_then_id(self.position, self.velocity);
            let commit_tick = current_shard_tick() + 2; // deterministic small future window
            self.handoff_state = ProjectileHandoffState::TransferPending {
                to_arbiter_id: destination,
                handoff_seq: self.handoff_seq,
                commit_tick,
                acked: false,
            };
            self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Prepare {
                projectile_id: self.projectile_id,
                handoff_seq: self.handoff_seq,
                from_arbiter_id: current_arbiter_id(),
                to_arbiter_id: destination,
                topology_epoch: current_topology_epoch(),
                source_tick: current_shard_tick(),
                commit_tick,
                snapshot: self.to_snapshot(),
            });
        }

        // --- Homing "Dumb NPC" Steering Logic ---
        if let Some(pos) = current_target_pos {
            let desired_dir = (pos - self.position).normalize();
            // In a full implementation, apply a max `turn_rate` here to prevent instant 180-degree snaps.
            // If target is lost (current_target_pos is None), the projectile maintains its current velocity.
            self.velocity = desired_dir * self.spell_data.projectile_speed;
        }

        self.position.x += self.velocity.x;
        self.position.y += self.velocity.y;
        self.remaining_lifetime_ticks = self.remaining_lifetime_ticks.saturating_sub(1);
        self.fuse_remaining_ticks = self.fuse_remaining_ticks.saturating_sub(1);

        // The Projectile determines who it hits (Real players AND Ghosts).
        let victims = self.calculate_collisions(local_hitboxes);
        
        if !victims.is_empty() {
            // Generate a universally unique ID for this specific interaction/explosion.
            // This guarantees the Idempotency Ledger prevents double-damage, even for 
            // pulsing AoEs or returning boomerangs.
            let impact_uuid = deterministic_impact_uuid(self.projectile_id, self.impact_sequence, current_shard_tick());
            self.impact_sequence = self.impact_sequence.saturating_add(1);
            
            // The Projectile hands the authoritative ImpactEvent back to its Host Arbiter.
            // The Host Arbiter will apply damage to Real victims, and relay the impact to Ghost owners.
            return Some(MeshInternalEvent {
                event_id: generate_uuid(),
                source_arbiter_id: current_arbiter_id(),
                actor_id: Some(self.owner_id),
                origin_tick: current_shard_tick(), // Projectile actions are anchored to their current simulation frame
                data_epoch: self.data_epoch, // CRITICAL: Ensures receiving Arbiters use the correct dictionary version
                payload: ActionPayload::ImpactEvent { 
                    impact_id: impact_uuid, 
                    target_ids: victims,
                    epicenter: self.position, // Provides absolute center for Ghost drift checks and distance falloff
                    geometry: self.spell_data.collision_geometry,
                    impact_tick: current_shard_tick(),
                    context: CombatContext {
                        base_damage: self.spell_data.base_damage,
                        damage_type: self.spell_data.damage_type,
                        knockback_force: self.spell_data.knockback_force,
                        armor_penetration_pct: self.spell_data.armor_penetration_pct, // Passed from Pre-Roll
                        armor_penetration_flat: self.spell_data.armor_penetration_flat, // Passed from Pre-Roll
                        is_critical_strike: self.spell_data.is_critical_strike, // Ensures clients render Crits
                        status_effect_id: self.spell_data.status_effect_id,
                        damage_origin: self.damage_origin,
                        proc_depth: self.proc_depth,
                    }
                }
            });
        }
        None
    }

    fn to_snapshot(&self) -> ProjectileSnapshot {
        ProjectileSnapshot {
            projectile_id: self.projectile_id,
            owner_id: self.owner_id,
            target_id: self.target_id,
            position: self.position,
            velocity: self.velocity,
            remaining_lifetime_ticks: self.remaining_lifetime_ticks,
            fuse_remaining_ticks: self.fuse_remaining_ticks,
            pierce_remaining: self.pierce_remaining,
            impact_sequence: self.impact_sequence,
            data_epoch: self.data_epoch,
            damage_origin: self.damage_origin as u8,
            proc_depth: self.proc_depth,
        }
    }
}
```

#### 3.3.1 Projectile Ownership Transfer (Split/Handoff Safety)
```rust
// Called by the surrogate Arbiter during split planning.
fn assign_projectile_owner_at_cutover(
    projectile: &ProjectileActor,
    child_b: ArbiterRegion,
    child_c: ArbiterRegion,
    cutover_tick: u64,
    topology_epoch: u32,
) -> u32 {
    // Predict position at cutover using deterministic fixed-point integration.
    let dt = cutover_tick.saturating_sub(current_shard_tick());
    let predicted = projectile.position + (projectile.velocity * SimFixed::from_num(dt));

    // Reuse the same jurisdiction rule as entities: depth, then lowest Arbiter_ID.
    let owner_child_id = choose_owner_by_depth_then_id(predicted, child_b, child_c);

    serialize_handoff_record(HandoffProjectileRecord {
        projectile_id: projectile.projectile_id,
        owner_child_id,
        cutover_tick,
        topology_epoch,
    });

    owner_child_id
}

// Child boot behavior:
// - Winner child sets authoritative_arbiter_id = self.arbiter_id and continues tick().
// - Loser child keeps an optional shadow copy for one grace window but never advances it.
```

#### 3.3.2 Runtime Projectile Boundary Handoff (Low-Cost)
```rust
// Receiver-side handler for RUDP projectile handoffs.
fn on_projectile_handoff_rudp(&mut self, auth: MeshAuthHeader, msg: ProjectileHandoffMessage) {
    if !self.verify_mesh_auth(&auth, &msg) { return; }
    match msg {
        ProjectileHandoffMessage::Prepare {
            projectile_id, handoff_seq, from_arbiter_id, to_arbiter_id,
            topology_epoch, source_tick, commit_tick, snapshot
        } => {
            if to_arbiter_id != self.arbiter_id { return; }

            // Epoch safety mirrors proposal-epoch rules.
            if topology_epoch < self.topology_epoch {
                self.forward_handoff_surrogate(msg);
                return;
            }
            if topology_epoch > self.topology_epoch {
                self.buffer_handoff_until_epoch(msg);
                return;
            }

            // Single-simulator safety: only accept newer sequence.
            let last_seq = self.last_projectile_handoff_seq(projectile_id);
            if handoff_seq <= last_seq {
                self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Reject {
                    projectile_id, handoff_seq, reason: "StaleSequence".to_string()
                });
                return;
            }

            // Reconstruct full mid-flight state from snapshot.
            let mut p = ProjectileActor::from_snapshot(snapshot);
            p.authoritative_arbiter_id = from_arbiter_id; // Owner flips at commit_tick only.
            p.handoff_state = ProjectileHandoffState::Shadow;
            p.handoff_seq = handoff_seq;
            p.handoff_topology_epoch = topology_epoch;
            p.handoff_cutover_tick = commit_tick;
            self.projectiles.insert(projectile_id, p);

            self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Ack {
                projectile_id, handoff_seq, from_arbiter_id, to_arbiter_id, commit_tick
            });
        }
        ProjectileHandoffMessage::Ack { projectile_id, handoff_seq, commit_tick, .. } => {
            if let Some(p) = self.projectiles.get_mut(&projectile_id) {
                if let ProjectileHandoffState::TransferPending { handoff_seq: seq, commit_tick: ct, acked, .. } = &mut p.handoff_state {
                    if *seq == handoff_seq && *ct == commit_tick { *acked = true; }
                }
            }
        }
        ProjectileHandoffMessage::Commit { projectile_id, handoff_seq, new_owner_arbiter_id, commit_tick } => {
            if let Some(p) = self.projectiles.get_mut(&projectile_id) {
                if handoff_seq >= p.handoff_seq && current_shard_tick() >= commit_tick {
                    p.authoritative_arbiter_id = new_owner_arbiter_id;
                    p.handoff_state = if new_owner_arbiter_id == self.arbiter_id {
                        ProjectileHandoffState::Owned
                    } else {
                        ProjectileHandoffState::Shadow
                    };
                }
            }
        }
        ProjectileHandoffMessage::Reject { .. } => {
            // Sender remains authoritative and retries with updated destination/epoch.
        }
    }
}
```

#### 3.3.3 Sibling Merge Protocol (Prepare -> Stream -> Controller Commit -> Drain)
Commit-phase routing contract:
- At `CommitMerge`, the loser must emit a final downstream `TopologyUpdate` (`new_epoch`) with `redirect_arbiter_id = winner_arbiter_id` before entering `ForwardingOnly`.
- During the forwarding drain window, the loser must still serve or proxy `RequestRoutingDelta` so stale Edge Nodes can converge to winner routing.

```rust
fn on_begin_merge_command(
    &mut self,
    merge_id: UUID,
    winner_arbiter_id: u32,
    loser_arbiter_id: u32,
    cutover_tick: u64,
    new_epoch: u32,
) {
    let role = if self.arbiter_id == winner_arbiter_id {
        Some(MergeRole::Winner)
    } else if self.arbiter_id == loser_arbiter_id {
        Some(MergeRole::Loser)
    } else {
        None
    };
    if role.is_none() { return; }

    self.merge_state = Some(MergeState {
        merge_id,
        role: role.unwrap(),
        peer_arbiter_id: if self.arbiter_id == winner_arbiter_id { loser_arbiter_id } else { winner_arbiter_id },
        cutover_tick,
        target_epoch: new_epoch,
        phase: MergePhase::Streaming,
        forwarding_until_tick: 0,
    });

    if matches!(self.merge_state.as_ref().unwrap().role, MergeRole::Loser) {
        self.send_merge_handoff_rudp(MergeHandoffMessage::Prepare {
            merge_id,
            winner_arbiter_id,
            loser_arbiter_id,
            cutover_tick,
            topology_epoch: self.topology_epoch,
        });
        self.stream_merge_snapshot_and_wal(winner_arbiter_id, merge_id, new_epoch);
    }
}

fn on_finalize_merge_command(
    &mut self,
    merge_id: UUID,
    winner_arbiter_id: u32,
    loser_arbiter_id: u32,
    _new_epoch: u32,
) {
    if self.arbiter_id == winner_arbiter_id {
        self.mark_merge_complete(merge_id);
    } else if self.arbiter_id == loser_arbiter_id {
        self.mark_merge_complete(merge_id);
        self.shutdown_or_return_to_pool();
    }
}

fn on_commit_merge_command(
    &mut self,
    merge_id: UUID,
    winner_arbiter_id: u32,
    loser_arbiter_id: u32,
    cutover_tick: u64,
    new_epoch: u32,
) {
    // Commit is idempotent and may arrive before cutover; requeue until effective tick.
    if self.current_tick < cutover_tick {
        self.controller_inbox.push_back(ControllerCommand::CommitMerge {
            merge_id,
            winner_arbiter_id,
            loser_arbiter_id,
            cutover_tick,
            new_epoch,
        });
        return;
    }

    if self.already_committed_merge(merge_id) { return; }

    if self.arbiter_id == winner_arbiter_id {
        self.apply_merge_snapshot_atomic(merge_id, new_epoch);
        self.topology_epoch = new_epoch;
        self.promote_merged_region_ownership();
        self.mark_merge_committed(merge_id);
    } else if self.arbiter_id == loser_arbiter_id {
        self.topology_epoch = new_epoch;
        self.broadcast_topology_redirect_to_connected_edges(
            new_epoch,
            winner_arbiter_id,
            self.current_data_epoch,
        );
        if let Some(state) = self.merge_state.as_mut() {
            state.phase = MergePhase::ForwardingOnly;
            state.forwarding_until_tick = self.current_tick + MAX_EVENT_AGE_TICKS;
        }
        self.mark_merge_committed(merge_id);
    }
}

fn on_merge_handoff_rudp(&mut self, auth: MeshAuthHeader, msg: MergeHandoffMessage) {
    if !self.verify_mesh_auth(&auth, &msg) { return; }
    match msg {
        MergeHandoffMessage::Prepare { merge_id, winner_arbiter_id, topology_epoch, .. } => {
            if self.arbiter_id != winner_arbiter_id { return; }
            if topology_epoch != self.topology_epoch {
                self.send_merge_handoff_rudp(MergeHandoffMessage::Reject {
                    merge_id,
                    reason: "EpochMismatch".to_string(),
                });
                return;
            }
            self.init_merge_staging(merge_id);
        }
        MergeHandoffMessage::SnapshotChunk { merge_id, snapshot_chunk, is_last, .. } => {
            if !self.is_merge_winner(merge_id) { return; }
            self.stage_merge_snapshot_chunk(merge_id, snapshot_chunk);
            if is_last {
                if let Some(state) = self.merge_state.as_mut() {
                    if state.merge_id == merge_id { state.phase = MergePhase::Catchup; }
                }
            }
        }
        MergeHandoffMessage::WalDelta(delta) => {
            if !self.is_merge_winner(delta.merge_id) { return; }
            self.replay_merge_wal(delta);
            let awaiting_ack = self.merge_state.as_ref()
                .map(|s| s.merge_id == delta.merge_id && matches!(s.phase, MergePhase::Catchup))
                .unwrap_or(false);
            if awaiting_ack && self.merge_staging_synced_to(delta.merge_id) >= self.current_tick {
                self.send_merge_handoff_rudp(MergeHandoffMessage::CatchupAck {
                    merge_id: delta.merge_id,
                    winner_arbiter_id: self.arbiter_id,
                    loser_arbiter_id: self.merge_peer(delta.merge_id),
                    synced_to_tick: self.current_tick,
                });
                if let Some(state) = self.merge_state.as_mut() {
                    if state.merge_id == delta.merge_id { state.phase = MergePhase::AwaitingCommit; }
                }
            }
        }
        MergeHandoffMessage::DrainComplete { merge_id, loser_arbiter_id, winner_arbiter_id } => {
            if self.arbiter_id == winner_arbiter_id {
                self.notify_controller_merge_drained(merge_id, loser_arbiter_id);
            }
        }
        MergeHandoffMessage::CatchupAck { merge_id, winner_arbiter_id, loser_arbiter_id, synced_to_tick } => {
            // Loser forwards winner readiness to controller; controller owns commit orchestration.
            if self.arbiter_id == loser_arbiter_id {
                self.notify_controller_merge_ready(merge_id, winner_arbiter_id, loser_arbiter_id, synced_to_tick);
            }
        }
        MergeHandoffMessage::Reject { .. } => {
            // Omitted: retry/abort policy driven by controller deadlines.
        }
    }
}

fn apply_merge_snapshot_atomic(&mut self, merge_id: UUID, new_epoch: u32) {
    let staged = self.take_merge_staging(merge_id);

    // 1) Entity import + Ghost->Real promotion in same frame.
    for (entity_id, incoming) in staged.entities {
        if self.entities.contains_key(&entity_id) {
            self.abort_merge(merge_id, "EntityIdCollision");
            return;
        }
        self.ghost_entities.remove(&entity_id);
        self.ghost_grid.remove(entity_id);
        self.entities.insert(entity_id, incoming.soft_state);
        self.offense_by_entity.insert(entity_id, incoming.offense);
    }

    // 2) Projectile import with UUID-based deduplication.
    for snap in staged.projectiles {
        match self.projectiles.get(&snap.projectile_id) {
            Some(existing) if existing.impact_sequence >= snap.impact_sequence => {}
            _ => { self.projectiles.insert(snap.projectile_id, ProjectileActor::from_snapshot(snap)); }
        }
    }

    // 3) Idempotency ledger union by absolute bucket tick (phase-safe remap).
    for b in staged.ledger_ring {
        let idx = (b.bucket_tick % MAX_EVENT_AGE_TICKS) as usize;
        if idx >= self.event_idempotency_ledger.len() { continue; }
        for entry in b.entries {
            self.event_idempotency_ledger[idx].insert(entry);
        }
    }

    // 4) Merge deterministic schedulers and epoch.
    self.pending_global_events.extend(staged.pending_global_events);
    self.topology_epoch = new_epoch;
}

fn tick_merge_forwarding(&mut self) {
    if let Some(state) = &self.merge_state {
        if matches!(state.role, MergeRole::Loser) && matches!(state.phase, MergePhase::ForwardingOnly) {
            self.forward_all_external_and_internal_to(state.peer_arbiter_id);
            self.service_or_proxy_routing_delta_requests(state.peer_arbiter_id);
            if self.current_tick >= state.forwarding_until_tick && self.external_inbox.is_empty() && self.internal_inbox.is_empty() {
                self.send_merge_handoff_rudp(MergeHandoffMessage::DrainComplete {
                    merge_id: state.merge_id,
                    loser_arbiter_id: self.arbiter_id,
                    winner_arbiter_id: state.peer_arbiter_id,
                });
                self.shutdown_or_return_to_pool();
            }
        }
    }
}
```

---
