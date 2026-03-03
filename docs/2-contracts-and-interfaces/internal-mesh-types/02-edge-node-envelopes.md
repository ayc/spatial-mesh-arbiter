## 2. Layer 1: The Edge Node (Proxy Actor)

The Proxy Actor maintains the client connection, manages local prediction (Soft State), and translates client intents into `ActionProposals`.

> **Canonical wire source:** The exact client->edge WebSocket envelope, auth bootstrap/resume payloads, `RawInput` contract, and immediate edge response semantics are defined in [Client-Edge Wire Protocol](../../2-contracts-and-interfaces/01-client-edge-wire-protocol.md). The types below are runtime-focused interface excerpts.
>
> **Canonical NPC runtime source:** NPC cadence tiers, replication budget/ring behavior, and client smoothing contracts are defined in [NPC Runtime and Replication Contract](../../1-architecture/02-npc-architecture.md).

### 2.1 Interface
```rust
// --- Edge Node / Meta Services Dispatch Envelopes ---

// The multiplexed envelope sent from the physical game client to the Edge Node
enum ClientMessage {
    Simulation(RawInput), // `RawInput` is the runtime alias of `SimulationInput` in 01-client-edge-wire-protocol.md
    Meta(MetaRequest),    // Low-frequency chat, inventory, grouping
    Control(ClientControlPayload), // Keepalive + optional non-authoritative telemetry
}

enum ClientControlPayload {
    ClientPing { ping_nonce: u64 },
    Pong { ping_nonce: u64 },
    // Optional raw-device samples for analytics/anti-cheat/debug only.
    // This payload never directly mutates authoritative gameplay state.
    DeviceTelemetry(DeviceTelemetryEnvelope),
}

enum TelemetrySource {
    Mouse,
    Keyboard,
    Gamepad,
    Touch,
}

struct DeviceTelemetryEnvelope {
    sample_seq: u64,
    source: TelemetrySource,
    samples: Vec<DeviceTelemetrySample>,
}

struct DeviceTelemetrySample {
    dt_ms: u16,
    mouse_dx: Option<i16>,
    mouse_dy: Option<i16>,
    raw_buttons_down: Option<u32>,
    raw_buttons_up: Option<u32>,
    raw_key_mask: Option<u64>,
}

// Low-frequency, strongly consistent interactions forwarded to Tier 2
enum MetaRequest {
    SendChatMessage { channel: String, text: String },
    MoveInventoryItem { from_slot: u8, to_slot: u8 },
    InviteToParty { target_character_name: String },
    RequestLogout, // Triggers the Section 9.5 logout handshake
}

// Snapshot of a player's inventory state, sent from Meta Services to the client
// via the Edge Node. Represents the full authoritative slot layout at a point in time.
struct InventorySlot {
    slot: u8,              // Inventory slot index
    item_id: u16,          // Reference to the item definition in the asset dictionary
    quantity: u32,         // Stack count (1 for non-stackable items)
}

struct InventorySnapshot {
    character_id: UUID,
    slots: Vec<InventorySlot>, // Only occupied slots; empty slots are omitted
    capacity: u8,              // Max slot count for this character
}

enum MetaResponse {
    ChatReceived { sender: String, text: String },
    InventorySync(InventorySnapshot),
    PartyInviteReceived { from_name: String },
    SystemAlert { message: String },
}

struct ProxyActor {
    session_id: UUID,        // Secure, unguessable network token for the client connection
    character_id: UUID,      // The persistent DB identity (injected by Auth, trusted by Meta)
    entity_id: EntityID,     // The fast, compact u64 used for physics and mesh routing
    // External client transport is WebSocket for browser compatibility and firewall traversal.
    client_connection: WebSocketStream<TlsOrTcpStream>,
    
    // --- The Dual-Routing Destinations ---
    // 1. Spatial Mesh (60Hz, UDP, Ephemeral)
    authoritative_mesh_node: IPAddress, 
    // 2. Meta Services (Async, gRPC/TCP, Persistent)
    meta_rpc_client: RpcClient, 
    
    // Time Synchronization & Deduplication
    latest_mesh_tick: u64,
    predicted_tick: u64,
    last_known_authoritative_tick: HashMap<EntityID, u64>,
    
    // Spatial Awareness (Temporal Swamp Prediction)
    current_topology_epoch: u32,
    my_region: Rect,
    my_dilation: SimFixed,
    neighbor_regions: Vec<NeighborRegion>, // Used to smoothly predict cross-border deceleration
    
    current_data_epoch: u32,
    
    // Input Buffer
    pending_inputs: Vec<RawInput>,

    // Proposal lifecycle tracking for deterministic rollback under packet loss/saturation.
    pending_proposals: HashMap<UUID, PendingProposal>,
}

enum PendingProposalKind {
    Discrete, // Casts, interactions, consumables
}

struct PendingProposal {
    kind: PendingProposalKind,
    submitted_at_tick: u64,
}

impl ProxyActor {
    const PROPOSAL_TIMEOUT_TICKS: u64 = 18; // ~300ms at 60Hz

    // 1. Asynchronous Network Receiver: Runs as fast as the client sends data
    // Acts as the "API Gateway" routing layer
    fn on_client_message(&mut self, msg: ClientMessage) {
        match msg {
            ClientMessage::Simulation(input) => {
                // Buffer high-frequency physics inputs for the 60Hz tick
                self.pending_inputs.push(input);
            },
            ClientMessage::Meta(request) => {
                // Instantly forward to Meta Services, bypassing the Arbiter.
                // SECURITY: The Edge Node forcibly injects the trusted character_id.
                // The client cannot spoof who is sending the chat or inventory move.
                self.meta_rpc_client.send_async(self.character_id, request);
            }
        }
    }

    // 1.b Asynchronous Meta Response Handler
    fn on_meta_response_received(&mut self, response: MetaResponse) {
        // Forward back to the physical client UI
        self.send_to_client_reliable(response);
    }

    // 2. Local Simulation Loop: Runs strictly at 60Hz to maintain parity with the Mesh Arbiter
    fn tick(&mut self) {
        self.predicted_tick += 1;
        
        // Aggregate all inputs received since the last 16.6ms frame
        let aggregated_input = aggregate_inputs(self.pending_inputs.drain(..).collect());

        let predicted_state = self.run_local_physics(aggregated_input.clone());
        self.send_to_client(predicted_state); 
        
        if aggregated_input.buttons.contains(FIRE) {
            let proposal = ActionProposal {
                proposal_id: generate_uuid(),
                actor_id: self.entity_id, 
                origin_tick: self.predicted_tick, // Now safely synchronized to the 60Hz baseline
                topology_epoch: self.current_topology_epoch,
                data_epoch: self.current_data_epoch,
                payload: ActionPayload::TargetedAbility { 
                    target_id: aggregated_input.target_id, 
                    ability_id: aggregated_input.selected_ability,
                }
            };
            self.pending_proposals.insert(
                proposal.proposal_id,
                PendingProposal { kind: PendingProposalKind::Discrete, submitted_at_tick: self.predicted_tick }
            );
            self.send_to_mesh(&self.authoritative_mesh_node, proposal);
        }

        // Failsafe: do not let client prediction hang forever if no terminal response arrives.
        let mut timed_out = Vec::new();
        for (proposal_id, pending) in &self.pending_proposals {
            if matches!(pending.kind, PendingProposalKind::Discrete)
                && self.predicted_tick.saturating_sub(pending.submitted_at_tick) >= Self::PROPOSAL_TIMEOUT_TICKS
            {
                timed_out.push(*proposal_id);
            }
        }
        for proposal_id in timed_out {
            self.pending_proposals.remove(&proposal_id);
            self.rollback_specific_action(proposal_id);
            self.send_ui_alert_to_client("Action Timeout (No Ack)".to_string());
        }
    }

    fn on_downstream_payload_received(&mut self, payload: DownstreamPayload) {
        match payload {
            DownstreamPayload::StateUpdate { snapshot: mesh_state, data_epoch } => {
                if data_epoch > self.current_data_epoch {
                    self.current_data_epoch = data_epoch;
                }
                self.latest_mesh_tick = cmp::max(self.latest_mesh_tick, mesh_state.tick);
                
                for entity_update in mesh_state.entities {
                    let last_auth_tick = self.last_known_authoritative_tick.get(&entity_update.id).unwrap_or(&0);

                    if entity_update.is_authoritative_owner {
                        if mesh_state.tick > *last_auth_tick {
                            if let Some(effects) = &entity_update.active_effects_detailed {
                                self.rebuild_cooldowns_from_effects(entity_update.id, effects);
                            }
                            self.reconcile_entity(entity_update);
                            self.last_known_authoritative_tick.insert(entity_update.id, mesh_state.tick);
                        }
                    } else if entity_update.is_ghost {
                        if mesh_state.tick > *last_auth_tick {
                            self.reconcile_entity(entity_update);
                        }
                    }
                }
                
                if self.diverges_from_prediction(self.get_my_player_state()) {
                    self.trigger_client_rollback(self.get_my_player_state());
                }
            },
            DownstreamPayload::ActionApplied { proposal_id } => {
                self.pending_proposals.remove(&proposal_id);
            },
            DownstreamPayload::TopologyUpdate { epoch, data_epoch, my_region, my_dilation, neighbors, redirect_arbiter_id } => {
                self.current_topology_epoch = epoch;
                if data_epoch > self.current_data_epoch {
                    self.current_data_epoch = data_epoch;
                }
                self.my_region = my_region;
                self.my_dilation = my_dilation;
                self.neighbor_regions = neighbors;
                if let Some(arbiter_id) = redirect_arbiter_id {
                    self.authoritative_mesh_node = self.resolve_arbiter_address(arbiter_id);
                }
            },
            DownstreamPayload::ActionFailed { proposal_id, reason } => {
                // Instantly refund cooldowns/resources and rollback prediction
                self.pending_proposals.remove(&proposal_id);
                self.rollback_specific_action(proposal_id);
                self.send_ui_alert_to_client(reason);
            }
        }
    }
}
```

---
