import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md', 'r') as f:
        content = f.read()

    # EntitySnapshot
    content = content.replace('struct EntitySnapshot {', 'struct EntitySnapshot<E: GameEntity> {')
    content = content.replace('record: EntityRecord,', 'record: EntityRecord<E>,')

    # EntityHandoffMessage
    content = content.replace('enum EntityHandoffMessage {', 'enum EntityHandoffMessage<E: GameEntity> {')
    content = content.replace('snapshot: EntitySnapshot,', 'snapshot: EntitySnapshot<E>,')

    # MergeSnapshot
    content = content.replace('struct MergeSnapshot {', 'struct MergeSnapshot<E: GameEntity> {')
    
    # SplitSnapshot
    content = content.replace('struct SplitSnapshot {', 'struct SplitSnapshot<E: GameEntity> {')

    # Update SnapshotChunk messages inside enums to take <E>
    # MergeHandoffMessage
    content = content.replace('snapshot_chunk: MergeSnapshot,', 'snapshot_chunk: MergeSnapshot<E>,')
    # SplitHandoffMessage
    content = content.replace('snapshot_chunk: SplitSnapshot,', 'snapshot_chunk: SplitSnapshot<E>,')

    # Oh, wait, MergeHandoffMessage already has <G: GameActions>. Now it needs <E: GameEntity, G: GameActions>.
    content = content.replace('enum MergeHandoffMessage<G: GameActions> {', 'enum MergeHandoffMessage<E: GameEntity, G: GameActions> {')
    content = content.replace('enum SplitHandoffMessage<G: GameActions> {', 'enum SplitHandoffMessage<E: GameEntity, G: GameActions> {')

    with open('docs/2-contracts-and-interfaces/internal-mesh-types/01-core-primitives.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
