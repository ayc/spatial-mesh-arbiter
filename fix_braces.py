import re

files = [
    'docs/3-gameplay-systems/02-ability-framework.md',
    'docs/1-architecture/05-ai-node-protocol.md',
    'docs/2-contracts-and-interfaces/01-client-edge-wire-protocol.md',
    'docs/2-contracts-and-interfaces/02-intent-taxonomy.md'
]

def fix_content(content):
    # This is a bit tricky, but we can look for `ActionPayload::Game(ArpgAction::X) { ... }` 
    # and `ActionPayload::Engine(EngineAction::X) { ... }` 
    
    # We will use regex to find: `ActionPayload::Game(ArpgAction::(.*?)) \{`
    # Replace with `ActionPayload::Game(ArpgAction::\1 {`
    # Then we need to find the matching closing brace.
    
    # Actually, the simplest way is to manually replace the specific instances since there are very few.
    content = content.replace("ActionPayload::Game(ArpgAction::TargetedAbility) {", "ActionPayload::Game(ArpgAction::TargetedAbility {")
    content = content.replace("ActionPayload::Game(ArpgAction::GroundTargetedAbility) {", "ActionPayload::Game(ArpgAction::GroundTargetedAbility {")
    content = content.replace("ActionPayload::Game(ArpgAction::SpawnProjectile) {", "ActionPayload::Game(ArpgAction::SpawnProjectile {")
    content = content.replace("ActionPayload::Game(ArpgAction::ImpactEvent) {", "ActionPayload::Game(ArpgAction::ImpactEvent {")
    content = content.replace("ActionPayload::Game(ArpgAction::InternalPreparedHit) {", "ActionPayload::Game(ArpgAction::InternalPreparedHit {")
    content = content.replace("ActionPayload::Game(ArpgAction::UseConsumable) {", "ActionPayload::Game(ArpgAction::UseConsumable {")
    content = content.replace("ActionPayload::Game(ArpgAction::Interact) {", "ActionPayload::Game(ArpgAction::Interact {")
    content = content.replace("ActionPayload::Game(ArpgAction::IssueCreepCommand) {", "ActionPayload::Game(ArpgAction::IssueCreepCommand {")
    content = content.replace("ActionPayload::Engine(EngineAction::Movement) {", "ActionPayload::Engine(EngineAction::Movement {")

    # The block ends with `}` usually at the same indentation level.
    # We can just write a quick bracket matcher.
    
    out = []
    lines = content.split('\n')
    open_braces = 0
    in_target = False
    
    for line in lines:
        if "ActionPayload::Game(ArpgAction::" in line and " {" in line:
            in_target = True
            open_braces += line.count('{')
            open_braces -= line.count('}')
        elif "ActionPayload::Engine(EngineAction::" in line and " {" in line:
            in_target = True
            open_braces += line.count('{')
            open_braces -= line.count('}')
        elif in_target:
            open_braces += line.count('{')
            open_braces -= line.count('}')
            
            if open_braces == 0 and "}" in line:
                # Add parenthesis after the last }
                # Note: this might be `    }` -> `    })`
                last_brace_idx = line.rfind('}')
                line = line[:last_brace_idx + 1] + ')' + line[last_brace_idx + 1:]
                in_target = False
                
        out.append(line)
        
    return '\n'.join(out)

for path in files:
    with open(path, 'r') as f:
        content = f.read()
    
    content = fix_content(content)
    
    with open(path, 'w') as f:
        f.write(content)

