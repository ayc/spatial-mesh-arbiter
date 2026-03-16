# Internal Mesh Types: Edge Node Envelopes

## 2. Layer 1: The Edge Node (Proxy Actor)

The Proxy Actor maintains the client connection, manages local prediction (Soft State), and translates client intents into `ActionProposals`.

> **Canonical wire source:** The exact client->edge WebSocket envelope, auth bootstrap/resume payloads, `RawInput` contract, and immediate edge response semantics are defined in [Client-Edge Wire Protocol](../01-client-edge-wire-protocol.md). The types below are runtime-focused interface excerpts.
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

// Low-frequency, strongly consistent interactions forwarded to Tier 2.
// This is the canonical MetaRequest definition. The Client-Edge Wire Protocol
// (01-client-edge-wire-protocol.md §9.1) references this enum directly —
// the client sends the same MetaRequest variants over the wire with no
// translation or fan-out step.
enum MetaRequest {
    // --- Chat ---
    SendChatMessage { channel: String, text: String },
    JoinChannel { channel: String },        // Subscribe to a custom or zone channel
    LeaveChannel { channel: String },       // Unsubscribe from a channel

    // --- Inventory ---
    MoveInventoryItem { from_slot: u8, to_slot: u8 },
    EquipItem { bag_slot: u8, equipment_slot: String },   // Move item from bag to equipment
    UnequipItem { equipment_slot: String, bag_slot: u8 },  // Move item from equipment to bag
    InspectItem { slot: u8 },                              // Request full affix/durability detail
    RepairItem { slot: u8 },                               // Repair a specific equipped item
    RepairAllItems,                                        // Repair all equipped items

    // --- Loot ---
    LootVote { drop_id: UUID, vote: LootVoteChoice },      // Need/Greed/Pass for NeedGreed mode
    AssignLoot { drop_id: UUID, target_character_id: UUID }, // MasterLoot: leader assigns drop

    // --- Party ---
    InviteToParty { target_character_name: String },
    RespondToPartyInvite { from_character_id: UUID, accepted: bool },
    LeaveParty,
    KickFromParty { target_character_id: UUID },           // Leader only
    PromotePartyLeader { target_character_id: UUID },      // Transfer leadership
    SetPartyLootMode { mode: PartyLootMode },              // Leader only
    SetPartyRole { target_character_id: UUID, role: PartyRole }, // Leader assigns role tags

    // --- Guild ---
    CreateGuild { guild_name: String },
    InviteToGuild { target_character_name: String },
    RespondToGuildInvite { guild_id: UUID, accepted: bool },
    LeaveGuild,
    KickFromGuild { target_character_id: UUID },
    SetGuildRank { target_character_id: UUID, rank: String },
    SetGuildRankPermissions { rank: String, permissions: Vec<GuildPermission> },
    GuildBankDeposit { bag_slot: u8 },                     // Deposit item from bag to guild bank
    GuildBankWithdraw { bank_tab: u8, bank_slot: u8 },     // Withdraw item from guild bank to bag
    SetGuildMotd { text: String },
    DisbandGuild,

    // --- Friends ---
    SendFriendRequest { target_character_name: String },
    RespondToFriendRequest { from_character_id: UUID, accepted: bool },
    RemoveFriend { target_character_id: UUID },

    // --- Moderation ---
    BlockPlayer { target_character_name: String },         // Client-side + server-side filter
    UnblockPlayer { target_character_id: UUID },
    ReportPlayer { target_character_name: String, reason: ReportReason, details: String },

    // --- LFG / Matchmaking ---
    LfgEnqueue { activity: LfgActivity, role: PartyRole },
    LfgDequeue,

    // --- Session ---
    RequestLogout, // Triggers the Section 9.5 logout handshake
}

enum LootVoteChoice {
    Need,
    Greed,
    Pass,
}

enum PartyLootMode {
    FreeForAll,
    RoundRobin,
    NeedGreed,
    MasterLoot,
}

enum PartyRole {
    Tank,
    Healer,
    Damage,
    Flex,  // No role preference (default)
}

enum GuildPermission {
    Invite,             // Can invite new members
    Kick,               // Can kick members of lower rank
    Promote,            // Can promote members up to one rank below own
    Demote,             // Can demote members of lower rank
    BankDeposit,        // Can deposit items to guild bank
    BankWithdraw,       // Can withdraw items from guild bank
    BankManageTabs,     // Can purchase/rename guild bank tabs
    EditMotd,           // Can change the guild message of the day
    EditRanks,          // Can rename ranks and modify permissions (below own rank)
    StartGuildEvent,    // Can create guild-wide calendar events
    UseGuildRepair,     // Can use guild funds for repair costs
}

enum ReportReason {
    Harassment,
    Cheating,
    BotOrAutomation,
    InappropriateName,
    RealMoneyTrading,
    Spam,
    Other,
}

enum LfgActivity {
    Dungeon { dungeon_id: u16 },
    WorldBoss { boss_id: u16 },
    PvpArena,
    PvpBattleground,
    OpenWorld,          // General "looking for group" for overworld content
}

// --- Inventory Wire Types ---

// Lightweight slot entry for bag/equipment list rendering.
// For full affix and durability details, the client sends MetaRequest::InspectItem.
struct InventorySlot {
    slot: u8,                   // Inventory slot index (bag) or equipment slot ordinal
    base_item_id: u16,          // Reference to items.json definition (for icon/name lookup)
    quantity: u32,              // Stack count (always 1 for equipment)
    instance_id: Option<u64>,   // Non-null for equipment with affixes/durability; null for stackables
    quality_tier: u8,           // 0=Common, 1=Uncommon, 2=Rare, 3=Epic, 4=Legendary (for UI color)
}

struct InventorySnapshot {
    character_id: UUID,
    bag_slots: Vec<InventorySlot>,       // Occupied bag slots; empty slots omitted
    equipment_slots: Vec<InventorySlot>, // Currently equipped items
    bag_capacity: u8,                    // Max bag slot count for this character
    primary_attributes: PrimaryAttributes, // Compiled totals for character sheet UI
}

// Full item detail returned on MetaRequest::InspectItem
struct ItemDetail {
    base_item_id: u16,
    instance_id: u64,
    quality_tier: u8,
    affixes: Vec<ResolvedAffix>,
    durability: Option<DurabilityInfo>,
}

struct ResolvedAffix {
    affix_id: u16,
    tier: u8,
    slot_type: String,            // "prefix", "suffix", "implicit", "fixed"
    display_text: String,         // Pre-resolved: "of the Bear (+12 Physical Resistance)"
}

struct DurabilityInfo {
    current: u16,
    max: u16,
}

struct RepairResult {
    items_repaired: u8,
    total_cost_gold: u64,
}

enum MetaResponse {
    // --- Chat ---
    ChatReceived { channel: String, sender: String, text: String },
    ChatError { reason: String },          // Rate limited, muted, channel not joined, etc.
    ChannelJoined { channel: String },
    ChannelLeft { channel: String },

    // --- Inventory ---
    InventorySync(InventorySnapshot),
    ItemDetailResponse(ItemDetail),
    RepairComplete(RepairResult),

    // --- Loot ---
    LootVotePrompt { drop_id: UUID, base_item_id: u16, quality_tier: u8, timeout_seconds: u8 },
    LootVoteResult { drop_id: UUID, winner_name: String, winning_vote: String },
    LootAssigned { drop_id: UUID, assigned_to_name: String },

    // --- Party ---
    PartyInviteReceived { from_name: String, from_character_id: UUID },
    PartySync(PartySnapshot),              // Full party state on any membership/setting change
    PartyDisbanded,

    // --- Guild ---
    GuildInviteReceived { guild_name: String, from_name: String, guild_id: UUID },
    GuildSync(GuildSnapshot),              // Membership roster + settings on any change
    GuildMotdUpdated { text: String },
    GuildDisbanded,

    // --- Friends ---
    FriendRequestReceived { from_name: String, from_character_id: UUID },
    FriendsSync(FriendsSnapshot),          // Full friends list with online status

    // --- LFG ---
    LfgMatchFound { activity: LfgActivity, party_id: UUID },
    LfgQueueUpdate { position: u32, estimated_wait_seconds: u32 },

    // --- Moderation ---
    PlayerMuted { until: u64, reason: String },   // Server-imposed mute notification
    ReportAcknowledged { report_id: UUID },

    // --- General ---
    SystemAlert { message: String },
}

// --- Social Wire Types ---

struct PartyMember {
    character_id: UUID,
    character_name: String,
    level: u16,
    role: PartyRole,
    is_online: bool,
    // Spatial data pushed from Arbiter → Meta for party frames
    current_hp_pct: u8,       // 0-100 for party frame health bar
    current_resource_pct: u8, // 0-100 for party frame resource bar
}

struct PartySnapshot {
    party_id: UUID,
    leader_id: UUID,
    loot_mode: PartyLootMode,
    members: Vec<PartyMember>,
}

struct GuildMemberEntry {
    character_id: UUID,
    character_name: String,
    rank: String,
    level: u16,
    is_online: bool,
    last_seen: u64,           // Unix timestamp; 0 if currently online
}

struct GuildSnapshot {
    guild_id: UUID,
    guild_name: String,
    leader_id: UUID,
    motd: String,
    member_count: u16,
    ranks: Vec<GuildRankInfo>,
    members: Vec<GuildMemberEntry>,       // Paginated for large guilds; first page on join
    bank_tabs: Vec<GuildBankTabInfo>,
}

struct GuildRankInfo {
    rank_name: String,
    ordinal: u8,              // 0 = Guild Master (immutable), 1+ = custom ranks
    permissions: Vec<GuildPermission>,
}

struct GuildBankTabInfo {
    tab_index: u8,
    tab_name: String,
    slots: Vec<InventorySlot>,            // Reuses the inventory slot wire type
}

struct FriendEntry {
    character_id: UUID,
    character_name: String,
    is_online: bool,
    current_zone: Option<String>,         // Zone display name if online; None if offline
}

struct FriendsSnapshot {
    friends: Vec<FriendEntry>,
    blocked: Vec<FriendEntry>,            // Blocked players (for UI list management)
    pending_sent: Vec<FriendEntry>,       // Outgoing requests not yet accepted
    pending_received: Vec<FriendEntry>,   // Incoming requests awaiting response
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
                payload: ActionPayload::Game(ArpgAction::TargetedAbility { 
                    target_id: aggregated_input.target_id, 
                    ability_id: aggregated_input.selected_ability,
                })
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
