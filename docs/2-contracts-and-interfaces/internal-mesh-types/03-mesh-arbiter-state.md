# Internal Mesh Types: Mesh Arbiter State

**API v2 Note:** The `tick()` execution loop below reflects the normative 12-stage pipeline and `dispatch_stage` mechanism defined in `docs-core/04-2-game-adapter-api-contract.md`. Utility functions outside the tick loop (ghost integration, physics helpers, ARPG combat math) predate the API v2 migration and will be reconciled during the `docs/` extraction workstream (`docs-core/06-architecture-section-mapping.md`).

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
    idempotency_bucket_capacity: u32, // Max dedupe keys per tick-bucket (memory guardrail)
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

enum LedgerInsertResult {
    Inserted,
    Duplicate,
    Overflow,
}

// Capacity-limited idempotency bucket (one slot in the MAX_EVENT_AGE_TICKS ring).
// Keeps dedupe memory bounded under spikes.
struct BoundedLedgerBucket {
    entries: HashSet<(UUID, EntityID)>,
    capacity: usize,
    overflowed_this_tick: bool,
}

impl BoundedLedgerBucket {
    fn new(capacity: usize) -> Self {
        Self {
            entries: HashSet::with_capacity(capacity),
            capacity,
            overflowed_this_tick: false,
        }
    }

    fn clear(&mut self) {
        self.entries.clear();
        self.overflowed_this_tick = false;
    }

    fn try_insert(&mut self, key: (UUID, EntityID)) -> LedgerInsertResult {
        if self.entries.contains(&key) {
            return LedgerInsertResult::Duplicate;
        }
        if self.entries.len() >= self.capacity {
            self.overflowed_this_tick = true;
            return LedgerInsertResult::Overflow;
        }
        self.entries.insert(key);
        LedgerInsertResult::Inserted
    }
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

struct SpatialActor<G: GameAdapter> {
    arbiter_id: u32,
    topology_epoch: u32,
    current_data_epoch: u32, // The version of the SpellData dictionary currently loaded in memory
    rtree_depth: u8,
    region_bounds: Rect,
    current_tick: u64,
    frame_pacing_offset_micros: i64,        // Applied to sleep budget each frame
    target_frame_pacing_offset_micros: i64, // Set by SyncHeartbeat correction target
    last_sync_heartbeat_tick: u64,          // current_tick at last accepted SyncHeartbeat
    metronome_outlier_count: u64,           // Diagnostics only
    metronome_degraded: bool,               // True after prolonged heartbeat loss warning emitted
    
    // The "Temporal Swamp" Factor (0.0 to 1.0)
    // Per-entity time multiplier for this zone. Entities move, cast, and recover at
    // (dilation_factor * entity.time_scale) rate. The Arbiter always runs at full 60Hz;
    // every tick is a full simulation tick. See docs/1-architecture/06-kinematic-dilation.md.
    // 1.0 = Full speed, 0.2 = entities at 1/5th speed
    dilation_factor: SimFixed,
    
    // Bounded Queues (Network layer pushes here. Must have explicit capacity limits 
    // to prevent OOM failure modes during blackhole density events).
    external_inbox: BoundedQueue<ActionProposal<G>>,
    internal_inbox: BoundedQueue<MeshInternalEvent<G>>,
    controller_inbox: BoundedQueue<ControllerCommand>,
    
    // Future Event Scheduler
    pending_global_events: HashMap<UUID, ControllerCommand>,

    // Deferred ingress normalized for the API v2 stage scheduler.
    // `incoming_deferred_events` is the batch eligible for the current tick.
    // `next_tick_deferred_events` accumulates Stage 9/11 outputs and ready controller timers
    // for deterministic re-entry on the next authoritative tick.
    incoming_deferred_events: Vec<DeferredEvent>,
    next_tick_deferred_events: Vec<DeferredEvent>,
    
    // Stale Buffer: Holds (Proposal, local_arrival_tick) to measure timeout safely.
    // Must be a BoundedQueue to prevent OOM vulnerabilities during prolonged Mesh Controller 
    // outages. Sized to handle spikes based on a ~400 entity capacity limit.
    stale_proposals_buffer: BoundedQueue<(ActionProposal<G>, u64)>,

    // Runtime storage splits SoftState and OffensiveStats into separate maps for cache locality.
    // During split/merge serialization, these are joined into Vec<(EntityID, EntityRecord)>
    // as defined in 01-core-primitives.md (SplitSnapshot / MergeSnapshot).
    entities: HashMap<EntityID, (EntityCore, <G::Entity as GameEntity>::SoftExt)>,
    offense_by_entity: HashMap<EntityID, <G::Entity as GameEntity>::OffenseExt>,
    ghost_entities: HashMap<EntityID, GhostState2D>, 
    ghost_grid: SpatialIndex<EntityID>, // Mirrors ghost positions for cheap downstream visibility queries
    proposal_buckets: HashMap<EntityID, TokenBucket>, // Per-entity fairness guard on ingress
    commander_bindings: HashMap<EntityID, CommanderBinding>, // commander_entity_id -> binding metadata
    creep_overrides: HashMap<EntityID, (CreepDirective, u64)>, // creep_id -> (directive, expires_at_tick)
    ai_controlled_entities: HashSet<EntityID>, // Named NPCs currently controlled by an AI Node
    merge_state: Option<MergeState>,
    processed_proposals: LruCache<UUID, bool>,

    // Crash Fencing: arbiter_ids declared dead by the Controller.
    // Populated on AbortPendingHandoffs (crash cleanup). Internal mesh messages
    // and ghost updates from fenced sources are silently dropped.
    // Entries are cleared when the Arbiter processes a topology update that
    // removes the dead arbiter from its neighbor set.
    fenced_arbiter_ids: HashSet<u32>,
    
    // Event Idempotency Ledger: Prevents double-damage from delayed or duplicate relays.
    // Memory-bounded ring: max keys ~= idempotency_bucket_capacity * MAX_EVENT_AGE_TICKS.
    event_idempotency_ledger: [BoundedLedgerBucket; MAX_EVENT_AGE_TICKS as usize], // each bucket initialized with boot_config.idempotency_bucket_capacity
    idempotency_overflow_drop_count: u64, // Impacts dropped fail-closed due to dedupe cap
    idempotency_merge_overflow_drop_count: u64, // Imported merge dedupe keys dropped due to cap
    adapter: G,
}

impl<G: GameAdapter> SpatialActor<G> {
    const FRAME_BUDGET_US: i64 = 16_666;
    const METRONOME_GAIN_US_PER_TICK: i64 = 50;
    const METRONOME_OFFSET_CLAMP_US: i64 = 1000;
    const METRONOME_SLEW_CLAMP_US_PER_FRAME: i64 = 50;
    const METRONOME_DECAY_US_PER_FRAME: i64 = 10;
    const METRONOME_DIFF_OUTLIER_TICKS: i64 = 300;
    const METRONOME_HEARTBEAT_STALE_TICKS: u64 = 180;    // 3 seconds @ 60Hz
    const METRONOME_HEARTBEAT_DEGRADED_TICKS: u64 = 600; // 10 seconds @ 60Hz

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
        if self.fenced_arbiter_ids.contains(&event.source_arbiter_id) { return; }
        self.internal_inbox.push_back(event);
    }

    // Called by the network ingress layer for each proposal packet before queueing.
    fn on_external_proposal_received(&mut self, proposal: ActionProposal<G>) {
        // Zero-trust ingress: only intent-level payloads are valid from Edge Nodes.
        // Game-semantic legality is evaluated later in Stage 2 via `validate_intent`.
        if !proposal.payload.is_edge_admissible() {
            self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                proposal_id: proposal.proposal_id,
                reason: "Invalid Payload Type".to_string(),
            });
            return;
        }

        let cost = if matches!(&proposal.payload, ActionPayload::Engine(EngineAction::Movement { .. })) {
            PROPOSAL_COST_MOVEMENT
        } else {
            PROPOSAL_COST_DISCRETE
        };

        let bucket = self.proposal_buckets
            .entry(proposal.actor_id)
            .or_insert(TokenBucket::new(self.current_tick));

        if !bucket.try_consume(self.current_tick, cost) {
            if !matches!(&proposal.payload, ActionPayload::Engine(EngineAction::Movement { .. })) {
                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                    proposal_id: proposal.proposal_id,
                    reason: "Rate Limited".to_string(),
                });
            }
            return;
        }

        if self.external_inbox.is_full() {
            if !matches!(&proposal.payload, ActionPayload::Engine(EngineAction::Movement { .. })) {
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
        let frame_start = monotonic_now();
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

        // 2. Metronome & Kinematic Dilation
        self.recalculate_dilation();

        // Normalize engine-owned ingress into API v2 stage inputs.
        // This preparation step:
        // - merges `external_inbox` with `stale_proposals_buffer`
        // - applies topology/data-epoch gating and bounded stale buffering
        // - coalesces continuous movement intents
        // - drains `internal_inbox` and ready `pending_global_events` into typed DeferredEvents
        // - deduplicates relay traffic before it enters Stage 2 or deferred stage ingress
        let stage2_candidates = self.prepare_stage2_intents();
        self.promote_ready_deferred_ingress();
        
        // --- STAGE 1: ControlAuthorityAndInputRouting ---
        // (API v2) Engine resolves routing changes before validation
        let stage1_outcome = self.adapter.dispatch_stage(1, self.build_stage_context());
        self.apply_stage_outcome(stage1_outcome);
        self.commit_routing_state();

        // Drain normalized Stage 2 candidates into intent validation
        let mut valid_intents = Vec::new();
        for proposal in stage2_candidates {
            let outcome = self.adapter.validate_intent(proposal.clone(), self.build_entity_snapshot(proposal.actor_id));
            if outcome.status == Status::OK {
                valid_intents.push(proposal);
                if let Some(stage_outcome) = outcome.stage_outcome {
                    self.apply_stage_outcome(stage_outcome); // Handle P-40 intercepts
                }
            } else {
                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                    proposal_id: proposal.proposal_id,
                    reason: outcome.reject_code.unwrap_or_default(),
                });
            }
        }
        
        // Inject Deferred Events (Sorted)
        self.incoming_deferred_events.sort_by_key(|e| (e.ready_tick, e.target_stage, e.sort_key));

        // --- STAGES 3 through 12 ---
        // (API v2) The engine drives the global pipeline
        for stage_id in 3..=12 {
            let mut stage_batch = self.build_stage_batch(stage_id, &valid_intents);
            
            // Inject deferred events for this stage
            self.inject_deferred_events(&mut stage_batch, stage_id);

            let stage_outcome = self.adapter.dispatch_stage(stage_id, stage_batch);
            self.apply_stage_outcome(stage_outcome);

            // Engine-owned Commit Boundaries
            match stage_id {
                5 => self.commit_kinematic_positions(), // Post-KinematicResolution
                10 => self.commit_death_and_respawn(),  // Post-DeathCheck
                12 => self.serialize_downstream_payloads(), // Post-Emission
                _ => {}
            }
        }

        // Stage 9/11 outputs and ready controller timers are now accumulated in
        // `next_tick_deferred_events` and become the ingress source for the next tick.
        self.roll_deferred_event_queues();

        // Integrate dead-reckoned Ghosts
        self.integrate_ghosts_lightweight();
        self.broadcast_ghosts_to_neighbors();
        self.tick_merge_forwarding();
        self.gc_expired_projectile_prepares();
        self.update_metronome_correction();

        let sim_elapsed_us = monotonic_elapsed_micros(frame_start);
        let sleep_us = self.compute_frame_sleep_micros(sim_elapsed_us);
        sleep_micros(sleep_us as u64);
    }

    // Normalize current external proposals plus any stale-buffered proposals into the
    // bounded Stage 2 candidate set. This is where the old pre-API-v2 ingress logic now lives.
    fn prepare_stage2_intents(&mut self) -> Vec<ActionProposal<G>> {
        let mut stage2_candidates = Vec::new();
        let mut next_tick_stale_buffer = BoundedQueue::new(1000);
        let mut latest_movement_by_actor: HashMap<EntityID, (ActionProposal<G>, u64)> = HashMap::new();

        // Merge new arrivals with anything we held over while waiting on topology/data sync.
        let all_proposals = self.external_inbox.drain(..).map(|p| (p, self.current_tick))
            .chain(self.stale_proposals_buffer.drain(..));

        for (proposal, local_arrival_tick) in all_proposals {
            // Continuous movement is coalesced to latest-per-actor before validation.
            if matches!(&proposal.payload, ActionPayload::Engine(EngineAction::Movement { .. })) {
                latest_movement_by_actor.insert(proposal.actor_id, (proposal, local_arrival_tick));
                continue;
            }

            // Data/topology mismatches are engine-owned admission concerns. The engine either:
            // - retries under bounded buffering,
            // - forwards to the correct Arbiter, or
            // - fails closed with a deterministic rejection.
            if !self.is_current_data_epoch_or_bufferable(&proposal, local_arrival_tick, &mut next_tick_stale_buffer) {
                continue;
            }
            if !self.is_current_topology_epoch_or_bufferable(&proposal, local_arrival_tick, &mut next_tick_stale_buffer) {
                continue;
            }

            if self.processed_proposals.contains(&proposal.proposal_id) { continue; }
            self.processed_proposals.insert(proposal.proposal_id, true);

            // Overlap-buffer relays remain engine-owned. The adapter only sees the normalized intent.
            if self.is_in_overlap_buffer(proposal.actor_id) {
                self.relay_to_neighbors(self.build_relay_event(&proposal));
            }

            stage2_candidates.push(proposal);
        }

        // Re-apply bounded epoch/topology checks to coalesced movement after latest-per-actor collapse.
        for (_, (proposal, local_arrival_tick)) in latest_movement_by_actor {
            if !self.is_current_data_epoch_or_bufferable(&proposal, local_arrival_tick, &mut next_tick_stale_buffer) {
                continue;
            }
            if !self.is_current_topology_epoch_or_bufferable(&proposal, local_arrival_tick, &mut next_tick_stale_buffer) {
                continue;
            }
            stage2_candidates.push(proposal);
        }

        self.stale_proposals_buffer = next_tick_stale_buffer;
        stage2_candidates
    }

    // Promote all deferred work that is eligible to enter THIS authoritative tick.
    // This includes:
    // - next-tick deferred events emitted by prior Stage 9/11 execution
    // - legacy `internal_inbox` payloads normalized into DeferredEvents
    // - ready controller/global-event timers normalized into DeferredEvents
    fn promote_ready_deferred_ingress(&mut self) {
        self.incoming_deferred_events.clear();
        self.incoming_deferred_events.extend(self.next_tick_deferred_events.drain(..));

        for event in self.internal_inbox.drain(..) {
            if self.processed_proposals.contains(&event.event_id) { continue; }
            self.processed_proposals.insert(event.event_id, true);
            self.incoming_deferred_events.push(self.normalize_internal_event(event));
        }

        self.pending_global_events.retain(|_, cmd| {
            if !cmd.is_ready_at(self.current_tick) {
                return true;
            }
            self.incoming_deferred_events.push(self.normalize_controller_command(cmd));
            false
        });
    }

    // Build the adapter-facing batch for a single stage.
    // Stage 1 uses relationship/control directives only; Stages 3-12 project the validated
    // intents plus currently active IR work into per-entity stage contexts.
    fn build_stage_batch(&self, stage_id: u8, valid_intents: &Vec<ActionProposal<G>>) -> DispatchStageRequest {
        let entity_batch = match stage_id {
            1 => self.collect_stage1_entities(),
            _ => self.collect_stage_entities_from_intents(stage_id, valid_intents),
        };

        DispatchStageRequest {
            stage_id,
            entity_batch,
            global_context: GlobalStageContext {
                tick: self.current_tick,
                topology_epoch: self.topology_epoch as u64,
                data_epoch: self.current_data_epoch as u64,
                incoming_deferred_events: Vec::new(),
            },
        }
    }

    // Inject only the deferred events that are scheduled to re-enter at this stage.
    // Events for later stages remain in the current tick ingress batch until their turn.
    fn inject_deferred_events(&mut self, stage_batch: &mut DispatchStageRequest, stage_id: u8) {
        let mut remaining = Vec::new();
        for event in self.incoming_deferred_events.drain(..) {
            if event.target_stage == stage_id {
                stage_batch.global_context.incoming_deferred_events.push(event);
            } else {
                remaining.push(event);
            }
        }
        self.incoming_deferred_events = remaining;
    }

    // Seal the tick's deferred outputs. Stage 9/11 outcomes emitted during this tick land in
    // `next_tick_deferred_events` and MUST NOT re-enter until the next authoritative tick.
    fn roll_deferred_event_queues(&mut self) {
        self.incoming_deferred_events.clear();
        self.next_tick_deferred_events.sort_by_key(|e| (e.ready_tick, e.target_stage, e.sort_key));
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
        if self.fenced_arbiter_ids.contains(&update.source_arbiter_id) { return; }
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
            payload: ActionPayload::Engine(EngineAction::RequestGhostCorrection {
                entity_id,
                requester_arbiter_id: self.arbiter_id,
            })
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

        // --- ARPG Template Reference Implementation ---
    // This centralizes all complex ARPG/MOBA math (Armor, Resistance, Weight, Falloff)
    // ensuring it only runs on the true authoritative owner of the target.
    // (See ../../3-gameplay-systems/01-rpg-mechanics.md for the full mitigation formula including Evasion and Block).
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
        // Note: For brevity, Evasion and Block checks are omitted here. See ../../3-gameplay-systems/01-rpg-mechanics.md.
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
            self.emit_hard_state(HardEvent::PlayerDied {
                killer: attacker_id,
                victim: target_id,
                respawn_delay_credit_ticks: 0,
                respawn_override: None,
            });
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
                    payload: ActionPayload::Game(ArpgAction::InternalPreparedHit {
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
                    })
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
                let diff = (controller_shard_tick as i64) - (self.current_tick as i64);

                // Outlier guard: ignore improbable one-off samples.
                if diff.abs() > Self::METRONOME_DIFF_OUTLIER_TICKS {
                    self.metronome_outlier_count = self.metronome_outlier_count.saturating_add(1);
                    return;
                }

                self.last_sync_heartbeat_tick = self.current_tick;
                self.metronome_degraded = false;
                self.target_frame_pacing_offset_micros = (diff * Self::METRONOME_GAIN_US_PER_TICK)
                    .clamp(-Self::METRONOME_OFFSET_CLAMP_US, Self::METRONOME_OFFSET_CLAMP_US);
            }
            ControllerCommand::PrepareDataEpoch { new_epoch, asset_uri, checksum } => {
                // Offload the I/O to a background thread so the 60Hz loop never stalls.
                // The background thread will download, parse, and push the new dictionary 
                // into a lock-free queue that the Arbiter reads from at the top of tick().
                self.asset_loader.async_fetch_and_parse(new_epoch, asset_uri, checksum);
            }
            ControllerCommand::AbortPendingHandoffs { crashed_arbiter_id } => {
                self.fenced_arbiter_ids.insert(crashed_arbiter_id);
                self.abort_pending_projectile_handoffs_from(crashed_arbiter_id);
            }
            _ => { /* ExecuteGlobalEvent and Splits handled in scheduler block */ }
        }
    }

    // Called once per frame before sleeping.
    fn update_metronome_correction(&mut self) {
        let since_last = self.current_tick.saturating_sub(self.last_sync_heartbeat_tick);

        if since_last > Self::METRONOME_HEARTBEAT_STALE_TICKS {
            // Heartbeat stale: freeze target updates and decay toward zero.
            self.target_frame_pacing_offset_micros = 0;
            let step = self.frame_pacing_offset_micros
                .abs()
                .min(Self::METRONOME_DECAY_US_PER_FRAME);
            self.frame_pacing_offset_micros -= self.frame_pacing_offset_micros.signum() * step;
        } else {
            // Normal correction: slew-limited convergence.
            let delta = self.target_frame_pacing_offset_micros - self.frame_pacing_offset_micros;
            self.frame_pacing_offset_micros += delta
                .clamp(-Self::METRONOME_SLEW_CLAMP_US_PER_FRAME, Self::METRONOME_SLEW_CLAMP_US_PER_FRAME);
        }

        if since_last > Self::METRONOME_HEARTBEAT_DEGRADED_TICKS && !self.metronome_degraded {
            self.emit_control_plane_warning("SyncHeartbeat missing >10s".to_string());
            self.metronome_degraded = true;
        }
    }

    // Sleep budget contract for the 60Hz loop:
    // sleep_us = max(0, 16_666 - sim_elapsed_us + frame_pacing_offset_micros)
    fn compute_frame_sleep_micros(&self, sim_elapsed_us: i64) -> i64 {
        (Self::FRAME_BUDGET_US - sim_elapsed_us + self.frame_pacing_offset_micros).max(0)
    }

    fn try_insert_idempotency_key(&mut self, bucket_index: usize, key: (UUID, EntityID)) -> LedgerInsertResult {
        if bucket_index >= self.event_idempotency_ledger.len() {
            return LedgerInsertResult::Overflow;
        }
        self.event_idempotency_ledger[bucket_index].try_insert(key)
    }

    fn simulate_physics_step(&mut self) {
        // 1. Resolve discrete physics steps (NPC movement, knockback decay, soft collision)
        self.apply_kinematics();

        // 2. Process all active Status Effects (DoTs, HoTs, CC)
        self.tick_status_effects();
    }

    // --- Physics Implementation (see T0-03 Collision Algorithm) ---
    //
    // apply_kinematics() runs every tick and handles:
    //   1. NPC movement: position += velocity * effective_time (where effective_time =
    //      dilation_factor * entity.core_stats.time_scale). Player movement is client-proposed
    //      and validated on arrival, NOT integrated server-side.
    //   2. Knockback decay: dilated per-entity. Knockback fades slower in the Temporal Swamp.
    //      knockback_velocity is a field on SoftState (serialized during handoffs).
    //   3. Soft collision push-out: Boids-style separation steering ("incompressible fluid").
    //      Push displacement is dilated. O(n²) is acceptable for n ≤ 400.
    //      Config: separation_radius (1.5m), max_push_per_tick (0.3m) — live-configurable.
    //
    // static_grid is a uniform grid of AABB cells loaded from map asset at boot.
    //   - is_colliding(position) -> bool: point-in-obstacle test
    //   - query_segment_aabb(a, b) -> Vec<AABB>: swept-segment test (CCD, ghost anomaly, LOS)
    //
    // calculate_collisions() normalizes local entities and ghosts into one deterministic
    // contact-ordered batch. HashMap iteration order for ghosts MUST NOT leak into
    // authoritative pierce results.
    // Arming guard: unarmed projectiles (arming_remaining_ticks > 0) don't register detonation-capable hits.
    // Pierce decrements per unique valid target hit. The projectile carries a
    // hit_exclusion_list so one target cannot consume pierce more than once.
    //
    // Wall rejection is intentional: server validates position legality, client handles sliding.
    // See docs/6-spec-drafts/tier-0-foundations/03-collision-algorithm.md for full pseudocode.

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
                            payload: ActionPayload::Game(ArpgAction::InternalPreparedHit {
                                target_id: *entity_id,
                                context: context.clone(),
                            })
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
        prepare_expiry_tick: u64,
        acked: bool,
    },
    ShadowPendingCommit {
        from_arbiter_id: u32,
        handoff_seq: u64,
        commit_tick: u64,
        prepare_expiry_tick: u64,
    }, // Replica staged from Prepare; never simulates unless Commit promotes ownership
    Shadow, // Replica kept briefly after commit; never simulates
}

struct ProjectileActor {
    projectile_id: UUID,
    owner_id: EntityID,
    target_id: Option<EntityID>,
    position: Vec2F,
    velocity: Vec2F,
    remaining_lifetime_ticks: u32,
    arming_remaining_ticks: u32,
    pierce_remaining: u8,
    hit_exclusion_list: BTreeSet<EntityID>,
    carried_entities: Vec<EntityID>,   // Ordered currently carried targets; the entities themselves remain authoritative state
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

impl ProjectileActor {
    // Projectiles run their own tick within the Host Arbiter's simulation loop.
    // The Arbiter passes in entity and ghost spatial indexes for collision queries,
    // plus the current_target_pos (resolved from Real entities or dead-reckoned Ghosts).
    fn tick(&mut self, local_entities: &SpatialIndex, ghost_entities: &SpatialIndex, current_target_pos: Option<Vec2F>) -> Option<MeshInternalEvent> {
        // Split/Handoff safety: shadow replicas must never simulate or emit impacts.
        if self.authoritative_arbiter_id != current_arbiter_id() { return None; }

        // Runtime cross-boundary transfer: lightweight RUDP Prepare/Ack/Commit.
        if let ProjectileHandoffState::TransferPending { to_arbiter_id, handoff_seq, commit_tick, prepare_expiry_tick, acked } = self.handoff_state {
            if !acked && current_shard_tick() > prepare_expiry_tick {
                // Fail-closed: unresolved ownership window cancels projectile rather than risking dual simulation.
                self.cancel_due_to_handoff_timeout();
                return None;
            }
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
            let prepare_expiry_tick = commit_tick + MAX_EVENT_AGE_TICKS;
            self.handoff_state = ProjectileHandoffState::TransferPending {
                to_arbiter_id: destination,
                handoff_seq: self.handoff_seq,
                commit_tick,
                prepare_expiry_tick,
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
                prepare_expiry_tick,
                snapshot: self.to_snapshot(),
            });
        }

        // Cross-boundary Temporal Swamp transition:
        // Blend source/destination dilation across the overlap band to avoid velocity snaps.
        let step_dilation = compute_projectile_step_dilation(
            self.position,
            current_arbiter_region(),
            current_arbiter_dilation(),
            current_neighbor_regions(),
            live_config().dilation.cross_boundary_blend_width_meters,
        );

        // --- Homing "Dumb NPC" Steering Logic ---
        if let Some(pos) = current_target_pos {
            let desired_dir = (pos - self.position).normalize();
            let current_dir = self.velocity.normalize();
            let max_step = self.spell_data.projectile_turn_rate
                .expect("validated at content load for homing projectiles");
            let new_dir = rotate_toward_with_max_step(current_dir, desired_dir, max_step * step_dilation);
            // If target is lost (current_target_pos is None), the projectile maintains its current velocity.
            self.velocity = new_dir * self.spell_data.projectile_speed;
        }

        self.position = self.position + (self.velocity * step_dilation);
        self.remaining_lifetime_ticks = self.remaining_lifetime_ticks.saturating_sub(1);
        self.arming_remaining_ticks = self.arming_remaining_ticks.saturating_sub(1);

        // The Projectile determines who it hits (Real players AND Ghosts).
        // A full implementation compares ordered entity hits against `first_world_hit`
        // using `detonation_policy` before choosing bounce/stop/detonate behavior.
        // See T3-01 draft §4 for the canonical collision algorithm.
        let collisions = self.calculate_collisions(&local_entities, &ghost_entities);
        let victims: Vec<EntityID> = collisions.entity_hits.iter().map(|hit| hit.entity_id).collect();
        
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
                payload: ActionPayload::Game(ArpgAction::ImpactEvent { 
                    impact_id: impact_uuid, 
                    target_ids: victims,
                    epicenter: self.position, // Provides absolute center for Ghost drift checks and distance falloff
                    geometry: self.spell_data.geometry,
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
                })
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
            arming_remaining_ticks: self.arming_remaining_ticks,
            pierce_remaining: self.pierce_remaining,
            hit_exclusion_list: self.hit_exclusion_list.iter().copied().collect(),
            impact_sequence: self.impact_sequence,
            data_epoch: self.data_epoch,
            damage_origin: self.damage_origin as u8,
            proc_depth: self.proc_depth,
        }
    }

    fn cancel_due_to_handoff_timeout(&mut self) {
        // Deterministic fail-closed behavior for rare ambiguous ownership windows.
        self.remaining_lifetime_ticks = 0;
        self.authoritative_arbiter_id = u32::MAX; // Sentinel: no owner; prevents further simulation.
        self.handoff_state = ProjectileHandoffState::Shadow;
    }
}

fn compute_projectile_step_dilation(
    position: Vec2F,
    source_region: Rect,
    source_dilation: SimFixed,
    neighbors: &Vec<NeighborRegion>,
    blend_width_meters: SimFixed,
) -> SimFixed {
    let Some((neighbor, signed_distance)) = find_crossing_neighbor_and_signed_distance(position, source_region, neighbors) else {
        return source_dilation;
    };

    // alpha = clamp((s + w/2) / w, 0, 1)
    // effective = lerp(source, destination, alpha)
    let half = blend_width_meters / SimFixed::from_num(2);
    let alpha = ((signed_distance + half) / blend_width_meters)
        .clamp(SimFixed::from_num(0), SimFixed::from_num(1));
    source_dilation + ((neighbor.dilation_factor - source_dilation) * alpha)
}

// Deterministic requirement:
// - signed_distance must be derived from topology-epoch boundary geometry in fixed-point.
// - both Arbiters and Edge prediction run the same equation; no side-specific variants.
fn find_crossing_neighbor_and_signed_distance(
    position: Vec2F,
    source_region: Rect,
    neighbors: &Vec<NeighborRegion>,
) -> Option<(&NeighborRegion, SimFixed)> {
    // Pseudocode:
    // 1) pick the deterministic destination neighbor (depth then ArbiterID tie-break)
    // 2) compute signed distance to shared boundary plane (source->destination normal)
    // 3) return neighbor + signed distance
    todo!()
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
            topology_epoch, source_tick, commit_tick, prepare_expiry_tick, snapshot
        } => {
            if to_arbiter_id != self.arbiter_id { return; }
            if current_shard_tick() > prepare_expiry_tick {
                self.send_projectile_handoff_rudp(ProjectileHandoffMessage::Reject {
                    projectile_id, handoff_seq, reason: "PrepareExpired".to_string()
                });
                return;
            }

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
            p.handoff_state = ProjectileHandoffState::ShadowPendingCommit {
                from_arbiter_id,
                handoff_seq,
                commit_tick,
                prepare_expiry_tick,
            };
            p.handoff_seq = handoff_seq;
            p.handoff_topology_epoch = topology_epoch;
            p.handoff_cutover_tick = commit_tick;
            // Do not rewrite velocity/position for dilation. Continuity comes from the shared
            // blend-band equation and deterministic topology geometry.
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
            let mut remove_expired_shadow = false;
            if let Some(p) = self.projectiles.get_mut(&projectile_id) {
                let expired_prepare = match p.handoff_state {
                    ProjectileHandoffState::ShadowPendingCommit { prepare_expiry_tick, .. } => {
                        current_shard_tick() > prepare_expiry_tick
                    }
                    _ => false,
                };
                if expired_prepare {
                    remove_expired_shadow = true;
                } else if handoff_seq >= p.handoff_seq && current_shard_tick() >= commit_tick {
                    if matches!(
                        p.handoff_state,
                        ProjectileHandoffState::ShadowPendingCommit { handoff_seq: seq, commit_tick: ct, .. }
                            if seq == handoff_seq && ct == commit_tick
                    ) || matches!(p.handoff_state, ProjectileHandoffState::TransferPending { .. }) {
                        p.authoritative_arbiter_id = new_owner_arbiter_id;
                        p.handoff_state = if new_owner_arbiter_id == self.arbiter_id {
                            ProjectileHandoffState::Owned
                        } else {
                            ProjectileHandoffState::Shadow
                        };
                    }
                }
            }
            if remove_expired_shadow {
                self.projectiles.remove(&projectile_id);
            }
        }
        ProjectileHandoffMessage::Reject { .. } => {
            // Sender remains authoritative and retries with updated destination/epoch.
        }
        ProjectileHandoffMessage::Abort { projectile_id, handoff_seq, from_arbiter_id, to_arbiter_id, .. } => {
            if to_arbiter_id != self.arbiter_id { return; }
            let mut remove_shadow = false;
            if let Some(p) = self.projectiles.get(&projectile_id) {
                if matches!(
                    p.handoff_state,
                    ProjectileHandoffState::ShadowPendingCommit { from_arbiter_id: src, handoff_seq: seq, .. }
                        if src == from_arbiter_id && seq == handoff_seq
                ) {
                    remove_shadow = true;
                }
            }
            if remove_shadow {
                self.projectiles.remove(&projectile_id);
            }
        }
    }
}

fn gc_expired_projectile_prepares(&mut self) {
    let now = self.current_tick;
    self.projectiles.retain(|_, p| {
        !matches!(
            p.handoff_state,
            ProjectileHandoffState::ShadowPendingCommit { prepare_expiry_tick, .. }
                if now > prepare_expiry_tick
        )
    });
}

fn abort_pending_projectile_handoffs_from(&mut self, crashed_arbiter_id: u32) {
    self.projectiles.retain(|_, p| {
        !matches!(
            p.handoff_state,
            ProjectileHandoffState::ShadowPendingCommit { from_arbiter_id, .. }
                if from_arbiter_id == crashed_arbiter_id
        )
    });
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

    // 3) Idempotency ledger union by absolute bucket tick (phase-safe remap, capacity-bounded).
    for b in staged.ledger_ring {
        let idx = (b.bucket_tick % MAX_EVENT_AGE_TICKS) as usize;
        if idx >= self.event_idempotency_ledger.len() { continue; }
        for entry in b.entries {
            if matches!(self.try_insert_idempotency_key(idx, entry), LedgerInsertResult::Overflow) {
                self.idempotency_merge_overflow_drop_count = self.idempotency_merge_overflow_drop_count.saturating_add(1);
            }
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

### 3.2 AI Node + Commander Addendum

The sections above define the core Arbiter runtime. The following minimal addendum pins the integration points for `MetaCommand::BindCommander`, `MetaCommand::EdgeNodeDead`, and AI-node passive mode recovery.

```rust
fn on_meta_command(&mut self, cmd: MetaCommand) {
    match cmd {
        MetaCommand::BindCommander {
            commander_entity_id,
            subordinate_entities,
            command_range,
            override_ttl_ticks,
        } => {
            self.commander_bindings.insert(
                commander_entity_id,
                CommanderBinding {
                    commander_entity_id,
                    subordinate_entities,
                    command_range,
                    override_ttl_ticks,
                },
            );
        }
        MetaCommand::EdgeNodeDead { affected_entities, .. } => {
            for entity_id in affected_entities {
                if self.ai_controlled_entities.contains(&entity_id) {
                    // Named NPC fallback path: passive mode, no logout fuse.
                    self.set_npc_passive_mode(entity_id); // Idle + zero velocity + aggro disabled
                } else {
                    // Player fallback path: existing wilderness logout fuse.
                    self.start_logout_fuse(entity_id);
                }
            }
        }
        _ => {
            // Existing Meta command handlers (SpawnEntity, UpdateEntityStats, etc.) omitted for brevity.
        }
    }
}
```

---
