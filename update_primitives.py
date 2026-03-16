import re
import sys

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md', 'r') as f:
        content = f.read()

    # Update ActionProposal
    content = content.replace(
        "struct ActionProposal {",
        "struct ActionProposal<G: GameActions> {"
    )
    content = content.replace(
        "payload: ActionPayload,",
        "payload: ActionPayload<G>,"
    )

    # Update MeshInternalEvent
    content = content.replace(
        "struct MeshInternalEvent {",
        "struct MeshInternalEvent<G: GameActions> {"
    )

    # Replace ActionPayload enum
    old_action_payload = """enum ActionPayload {
    // Continuous Inputs
    Movement { 
        position: Vec2F, 
        velocity: Vec2F, 
        rotation: SimFixed 
    },
    
    // Combat (Target-Locked / Instant)
    TargetedAbility { 
        target_id: EntityID, 
        ability_id: u16,
    },
    
    // Combat (Ground-Targeted / AoEs like Meteor or Blizzard)
    GroundTargetedAbility {
        destination: Vec2F,
        ability_id: u16,
    },
    
    // Combat (Target-Favoring Resolution / Skillshots)
    // Content note: "SpawnZone" is an asset/schema alias compiled into SpawnProjectile
    // with zero velocity + pulse/duration mechanics.
    SpawnProjectile { 
        direction: Vec2F, 
        target_id: Option<EntityID>, // Used for Homing Missiles or Attached Auras
        spell_id: u16 
    },

    // Combat (Cross-Boundary Ghost Interactions)
    ImpactEvent {
        impact_id: UUID, 
        target_ids: Vec<EntityID>, 
        epicenter: Vec2F, 
        geometry: CollisionGeometry, // Used for final, precise mathematical validation of ghost impacts
        impact_tick: u64,
        context: CombatContext, 
    },

    // Combat (Internal-Only / Already Authoritative)
    // Used for reactive procs like Thorns where combat context is already finalized.
    InternalPreparedHit {
        target_id: EntityID,
        context: CombatContext,
    },
    
    // Interactions
    UseConsumable { item_id: u16 },
    Interact { target_entity: EntityID },

    // Internal Reliability Control (Ghost Repair Path)
    RequestGhostCorrection {
        entity_id: EntityID,
        requester_arbiter_id: u32,
    },

    // Commander Pattern: Named NPC (AI Node) issues behavioral override to Arbiter-Local creeps.
    // Validated by the Arbiter against active CommanderBinding, range, and locality constraints.
    IssueCreepCommand {
        target_creeps: Vec<EntityID>,
        directive: CreepDirective,
    },
}"""

    new_action_payload = """// The Engine-owned traits for opaque game actions
pub trait GameActions: Clone + Send + Sync + 'static {
    type Action: Clone + Send + Sync + serde::Serialize + serde::de::DeserializeOwned;
}

// The generic payload separating engine routing from game logic
enum ActionPayload<G: GameActions> {
    Engine(EngineAction),
    Game(G::Action),
}

// Engine-owned actions that directly interact with spatial systems
enum EngineAction {
    // Continuous Inputs
    Movement { 
        position: Vec2F, 
        velocity: Vec2F, 
        rotation: SimFixed 
    },
    // Internal Reliability Control (Ghost Repair Path)
    RequestGhostCorrection {
        entity_id: EntityID,
        requester_arbiter_id: u32,
    },
}

// --- ARPG Template Implementation ---
// Example of the game-specific intent payload matching the GameActions trait
enum ArpgAction {
    // Combat (Target-Locked / Instant)
    TargetedAbility { 
        target_id: EntityID, 
        ability_id: u16,
    },
    // Combat (Ground-Targeted / AoEs like Meteor or Blizzard)
    GroundTargetedAbility {
        destination: Vec2F,
        ability_id: u16,
    },
    // Combat (Target-Favoring Resolution / Skillshots)
    SpawnProjectile { 
        direction: Vec2F, 
        target_id: Option<EntityID>, 
        spell_id: u16 
    },
    // Combat (Cross-Boundary Ghost Interactions)
    ImpactEvent {
        impact_id: UUID, 
        target_ids: Vec<EntityID>, 
        epicenter: Vec2F, 
        geometry: CollisionGeometry,
        impact_tick: u64,
        context: CombatContext, 
    },
    // Combat (Internal-Only / Already Authoritative)
    InternalPreparedHit {
        target_id: EntityID,
        context: CombatContext,
    },
    // Interactions
    UseConsumable { item_id: u16 },
    Interact { target_entity: EntityID },
    // Commander Pattern: Named NPC (AI Node) issues behavioral override to Arbiter-Local creeps.
    IssueCreepCommand {
        target_creeps: Vec<EntityID>,
        directive: CreepDirective,
    },
}"""
    
    content = content.replace(old_action_payload, new_action_payload)

    # Let's write the content back
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
