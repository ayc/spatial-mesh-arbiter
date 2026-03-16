import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'r') as f:
        content = f.read()

    content = content.replace("""            payload: ActionPayload::Engine(EngineAction::RequestGhostCorrection {
                entity_id,
                requester_arbiter_id: self.arbiter_id,
            },
        });""", """            payload: ActionPayload::Engine(EngineAction::RequestGhostCorrection {
                entity_id,
                requester_arbiter_id: self.arbiter_id,
            })
        });""")

    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
