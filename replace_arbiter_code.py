import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'r') as f:
        content = f.read()

    # 1. Update the tick function
    # Find start of tick() and end of it
    tick_start = content.find("fn tick(&mut self) {")
    tick_end = content.find("fn integrate_ghosts_lightweight(&mut self) {", tick_start)

    new_tick = """fn tick(&mut self) {
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
        
        // --- STAGE 1: ControlAuthorityAndInputRouting ---
        // (API v2) Engine resolves routing changes before validation
        self.adapter.dispatch_stage(1, self.build_stage_context());
        self.commit_routing_state();

        // Drain external inbox into Stage 2 Validation
        let mut valid_intents = Vec::new();
        for proposal in self.external_inbox.drain(..) {
            let outcome = self.adapter.validate_intent(proposal.clone(), self.build_entity_snapshot(proposal.actor_id));
            if outcome.status == Status::OK {
                valid_intents.push(proposal);
                if let Some(stage_result) = outcome.stage_result {
                    self.apply_stage_result(stage_result); // Handle P-40 intercepts
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

            let stage_result = self.adapter.dispatch_stage(stage_id, stage_batch);
            self.apply_stage_result(stage_result);

            // Engine-owned Commit Boundaries
            match stage_id {
                5 => self.commit_kinematic_positions(), // Post-KinematicResolution
                10 => self.commit_death_and_respawn(),  // Post-DeathCheck
                12 => self.serialize_downstream_payloads(), // Post-Emission
                _ => {}
            }
        }

        // Execute scheduled Controller commands (Global Events)
        self.execute_pending_global_events();

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

    // --- Ghost Integration (Low-Cost / Anomaly-Gated) ---
    """

    content = content[:tick_start] + new_tick + content[tick_end + len("fn integrate_ghosts_lightweight(&mut self) {\n"):]

    # 2. Delete resolve_action and resolve_internal_event
    resolve_start = content.find("fn resolve_action(&mut self, payload: ActionPayload<G>")
    arpg_start = content.find("    // --- ARPG Template Reference Implementation ---", resolve_start)
    
    content = content[:resolve_start] + content[arpg_start:]
    
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
