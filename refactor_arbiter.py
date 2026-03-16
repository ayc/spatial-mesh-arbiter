import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'r') as f:
        content = f.read()

    # Make SpatialActor generic
    content = content.replace("struct SpatialActor {", "struct SpatialActor<G: GameResolver> {")
    content = content.replace("impl SpatialActor {", "impl<G: GameResolver> SpatialActor<G> {")
    
    # Add game_resolver to SpatialActor
    content = content.replace("    idempotency_merge_overflow_drop_count: u64,", "    idempotency_merge_overflow_drop_count: u64,\n    game_resolver: G,")

    # Update external_inbox to use <G>
    content = content.replace("external_inbox: BoundedQueue<ActionProposal>,", "external_inbox: BoundedQueue<ActionProposal<G>>,")
    content = content.replace("internal_inbox: BoundedQueue<MeshInternalEvent>,", "internal_inbox: BoundedQueue<MeshInternalEvent<G>>,")
    content = content.replace("stale_proposals_buffer: BoundedQueue<(ActionProposal, u64)>,", "stale_proposals_buffer: BoundedQueue<(ActionProposal<G>, u64)>,")

    # Update entity storage
    # entities: HashMap<EntityID, SoftState>,
    # offense_by_entity: HashMap<EntityID, OffensiveStats>,
    # ->
    # entities: HashMap<EntityID, (EntityCore, G::Entity::SoftExt)>,
    # offense_by_entity: HashMap<EntityID, G::Entity::OffenseExt>,
    
    # But for simplicity and so we don't break too many pseudocode lines in the file, 
    # we can just write the struct definition correctly.
    content = re.sub(r"entities: HashMap<EntityID, SoftState>.*?,", "entities: HashMap<EntityID, (EntityCore, <G::Entity as GameEntity>::SoftExt)>,", content)
    content = re.sub(r"offense_by_entity: HashMap<EntityID, OffensiveStats>.*?,", "offense_by_entity: HashMap<EntityID, <G::Entity as GameEntity>::OffenseExt>,", content)

    # Now we need to replace resolve_action
    old_resolve_action_pattern = re.compile(r"fn resolve_action\(&mut self, payload: ActionPayload, source_actor_id: Option<EntityID>, origin_tick: u64, original_proposal_id: Option<UUID>, data_epoch: u32\) \{.*?// --- Deep RPG Combat Engine ---", re.DOTALL | re.MULTILINE)
    
    new_resolve_action = """fn resolve_action(&mut self, payload: ActionPayload<G>, source_actor_id: Option<EntityID>, origin_tick: u64, original_proposal_id: Option<UUID>, data_epoch: u32) {
        match payload {
            ActionPayload::Engine(EngineAction::Movement { position, velocity, rotation }) => {
                let actor_id = source_actor_id.expect("Movement requires a source actor");
                if let Some((core, _)) = self.entities.get_mut(&actor_id) {
                    if !self.has_jurisdiction_over(core.position) { return; }
                    
                    let dt = self.current_tick.saturating_sub(core.last_movement_tick);
                    let max_displacement = (core.move_speed * SimFixed::from_num(dt)) + GHOST_ANOMALY_MARGIN;
                    
                    if core.position.distance_to(position) <= max_displacement {
                        if !self.static_grid.is_colliding(position) {
                            core.position = position;
                            core.velocity = velocity;
                            core.rotation = rotation;
                            core.last_movement_tick = self.current_tick;
                            self.local_grid.upsert(actor_id, position);
                        } else {
                            self.trigger_client_rollback(actor_id);
                        }
                    } else {
                        self.trigger_client_rollback(actor_id);
                    }
                }
            },
            ActionPayload::Engine(EngineAction::RequestGhostCorrection { entity_id, requester_arbiter_id }) => {
                if let Some((core, _)) = self.entities.get(&entity_id) {
                    if !self.has_jurisdiction_over(core.position) { return; }
                    let mut keyframe = core.get_ghost_update(self.current_tick);
                    keyframe.is_keyframe = true;
                    self.send_ghost_update_rudp(requester_arbiter_id, keyframe);
                }
            },
            ActionPayload::Game(game_action) => {
                let actor_id = source_actor_id.expect("Game actions require a source actor");
                
                // Construct views for the GameResolver
                let actor_view = self.build_entity_view(actor_id);
                let world_view = self.build_world_view();

                let outcome = self.game_resolver.resolve_action(
                    &game_action,
                    &actor_view,
                    &world_view,
                    &mut self.rng,
                    self.current_tick,
                    self.dilation_factor,
                );

                // Apply returned outcome mutations to engine state
                self.apply_action_outcome(outcome);

                if let Some(prop_id) = original_proposal_id {
                    self.send_downstream(actor_id, DownstreamPayload::ActionApplied { proposal_id: prop_id });
                }
            }
        }
    }

    fn resolve_internal_event(&mut self, payload: &[u8], target_id: EntityID) {
        let mut target_view = self.build_entity_mut_view(target_id);
        let world_view = self.build_world_view();
        
        let outcome = self.game_resolver.resolve_internal_event(
            payload,
            &mut target_view,
            &world_view,
            &mut self.rng,
            self.current_tick,
        );
        
        self.apply_action_outcome(outcome);
    }

    // --- ARPG Template Reference Implementation ---"""

    content = old_resolve_action_pattern.sub(new_resolve_action, content)
    
    # We also need to fix ActionPayload -> ActionPayload<G> in on_external_proposal_received
    content = content.replace("fn on_external_proposal_received(&mut self, proposal: ActionProposal) {", "fn on_external_proposal_received(&mut self, proposal: ActionProposal<G>) {")
    content = content.replace("ActionPayload::Movement { .. }", "ActionPayload::Engine(EngineAction::Movement { .. })")
    
    # Remove the hardcoded ARPG match block in on_external_proposal_received
    old_match = """        if !matches!(
            &proposal.payload,
            ActionPayload::Engine(EngineAction::Movement { .. })
                | ActionPayload::TargetedAbility { .. }
                | ActionPayload::GroundTargetedAbility { .. }
                | ActionPayload::SpawnProjectile { .. }
                | ActionPayload::UseConsumable { .. }
                | ActionPayload::Interact { .. }
                | ActionPayload::IssueCreepCommand { .. }
        ) {"""
    
    new_match = """        // The engine delegates game-specific validation to the GameResolver
        if let ActionPayload::Game(game_action) = &proposal.payload {
            if let Err(reason) = self.game_resolver.validate_proposal(game_action, proposal.actor_id) {
                self.send_downstream(proposal.actor_id, DownstreamPayload::ActionFailed {
                    proposal_id: proposal.proposal_id,
                    reason: reason.to_string(),
                });
                return;
            }
        }
        
        if false {"""
        
    content = content.replace(old_match, new_match)

    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
