import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'r') as f:
        content = f.read()

    # In tick_status_effects
    content = content.replace("payload: ActionPayload::InternalPreparedHit", "payload: ActionPayload::Game(ArpgAction::InternalPreparedHit")
    
    # In apply_combat_math
    content = content.replace("payload: ActionPayload::InternalPreparedHit", "payload: ActionPayload::Game(ArpgAction::InternalPreparedHit")

    # In RequestGhostCorrection
    content = content.replace("payload: ActionPayload::RequestGhostCorrection", "payload: ActionPayload::Engine(EngineAction::RequestGhostCorrection")

    # In ProjectileActor.tick
    content = content.replace("payload: ActionPayload::ImpactEvent", "payload: ActionPayload::Game(ArpgAction::ImpactEvent")
    
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
