import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'r') as f:
        content = f.read()

    # Remove the legacy header
    legacy_note = "Historical note: this file is an older internal reference sketch. Names such as `GameResolver`, `validate_proposal`, and `resolve_action` below are legacy conceptual predecessors of the current API v2 adapter boundary in `docs-core/04-1-game-adapter-contract.md` and `docs-core/04-2-game-adapter-api-contract.md` (`validate_intent`, `dispatch_stage`, `initialize_spawn_configuration`, `describe_compatibility`).\n\n"
    
    new_note = "**API v2 Note:** The `tick()` execution loop below reflects the normative 12-stage pipeline and `dispatch_stage` mechanism defined in `docs-core/04-2-game-adapter-api-contract.md`.\n\n"
    
    content = content.replace(legacy_note, new_note)
    
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
