import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md', 'r') as f:
        content = f.read()

    # Update MergeWalDelta
    content = content.replace('struct MergeWalDelta {', 'struct MergeWalDelta<G: GameActions> {')
    
    # Update SplitWalDelta
    content = content.replace('struct SplitWalDelta {', 'struct SplitWalDelta<G: GameActions> {')

    # Update MergeHandoffMessage
    content = content.replace('enum MergeHandoffMessage {', 'enum MergeHandoffMessage<G: GameActions> {')
    
    # Update SplitHandoffMessage
    content = content.replace('enum SplitHandoffMessage {', 'enum SplitHandoffMessage<G: GameActions> {')

    # Replace field types
    content = content.replace('Vec<ActionProposal>,', 'Vec<ActionProposal<G>>,')
    content = content.replace('Vec<MeshInternalEvent>,', 'Vec<MeshInternalEvent<G>>,')
    
    content = content.replace('WalDelta(MergeWalDelta),', 'WalDelta(MergeWalDelta<G>),')
    content = content.replace('WalDelta(SplitWalDelta),', 'WalDelta(SplitWalDelta<G>),')

    # Fix SoftState & EntityRecord
    content = content.replace('struct SoftState {', 'struct EntityCore {\n    hp: i32,\n    max_hp: i32,\n    is_dead: bool,\n    is_invulnerable: bool,\n    position: Vec2F,\n    velocity: Vec2F,\n    rotation: SimFixed,\n    last_movement_tick: u64,\n    stats: CoreStats,\n}\n\npub trait GameEntity: Clone + Send + Sync + \'static {\n    type SoftExt: Clone + Send + Sync + serde::Serialize + serde::de::DeserializeOwned;\n    type OffenseExt: Clone + Send + Sync + serde::Serialize + serde::de::DeserializeOwned;\n}\n\n// --- ARPG Template Implementation ---\nstruct SoftState {')
    
    content = content.replace('struct EntityRecord {', 'struct EntityRecord<E: GameEntity> {\n    entity_id: EntityID,\n    core: EntityCore,\n    soft_ext: E::SoftExt,\n    offense_ext: E::OffenseExt,\n}\n\n// --- ARPG Template Implementation ---\nstruct ArpgEntityRecord {')

    # Replace inside MergeSnapshot / SplitSnapshot
    content = content.replace('entities: Vec<(EntityID, EntityRecord)>,', 'entities: Vec<(EntityID, EntityRecord<E>)>,')
    
    # Needs <E: GameEntity> in MergeSnapshot / SplitSnapshot? Or maybe <E: GameEntity, G: GameActions>?
    # Probably easiest to just do:
    # struct MergeSnapshot<E: GameEntity> 
    
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
