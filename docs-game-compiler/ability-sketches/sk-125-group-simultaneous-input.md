# SK-125: Group Simultaneous Input

## Designer Intent

A fellowship maneuver triggers during combat. ALL group members see a selection wheel with 4 colors: Red (damage), Blue (power restore), Green (heal), Yellow (buff). Each player SIMULTANEOUSLY and INDEPENDENTLY selects a color within a 10-second window. Once all players have selected (or the timer expires), the COMBINATION of all selections determines the outcome. All Red = maximum damage. All Green = massive heal. Specific patterns unlock special named effects with unique bonuses.

## Primitive Composition

P-54 (Group Choice Aggregator)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Trigger event (specific ability or boss mechanic)
- Each player selects one option from a set (Red, Blue, Green, Yellow)
- All selections are collected and evaluated together

## Observable Behavior

1. Fellowship maneuver triggers — all group members see the selection UI
2. Each player independently selects a color (no communication needed, but coordination helps)
3. 10-second window for all players to select
4. Players who don't select in time: assigned a default (weakest option, or random)
5. Once all selections are in (or timer expires): combination is evaluated
6. Example outcomes for a 4-player group:
   - R-R-R-R: "Might of the Shire" — massive AoE damage burst
   - G-G-G-G: "Grace of the Elves" — full group heal + HoT
   - R-G-B-Y: "Harmony" — moderate damage + moderate heal + power restore + buff
   - R-R-G-G: "Balanced Assault" — AoE damage + group heal
   - Y-Y-Y-Y: "Fellowship's Resolve" — massive group damage buff for 30 seconds
7. Specific ORDERED patterns (R-B-G-Y in that exact order by player position) unlock SPECIAL named effects more powerful than generic combinations
8. Visual: selection wheel UI, color choice per player, dramatic combined effect on resolution

## Engine Primitives Required

### Synchronous Multi-Player Input Collection

This is the first mechanic requiring the engine to COLLECT INPUT FROM MULTIPLE PLAYERS and evaluate it as a SINGLE COMBINED ACTION:

```
struct GroupInputCollection {
    collection_id: UUID,
    group_id: UUID,
    options: Vec<InputOption>,         // Available choices (Red, Blue, Green, Yellow)
    deadline_tick: u64,
    selections: HashMap<EntityID, InputOption>,  // Player → their choice
    expected_count: u8,                // How many players should select
    default_option: InputOption,       // For players who don't select
    resolved: bool,
}

enum InputOption {
    Red,    // Damage
    Blue,   // Power
    Green,  // Heal
    Yellow, // Buff
}
```

### Input Collection Flow

1. **Trigger**: A game event starts the input collection. All group members are notified.
2. **Selection**: Each player's Edge Node sends a "select option X" proposal to their Arbiter.
3. **Collection**: The combo-owning Arbiter collects all selections.
4. **Resolution**: When all selections are in (or timer expires), evaluate the combination.

```
fn on_player_selection(entity: &Entity, selection: InputOption) {
    if let Some(collection) = get_active_input_collection(entity.group_id) {
        if !collection.resolved && current_tick() <= collection.deadline_tick {
            collection.selections.insert(entity.entity_id, selection);

            if collection.selections.len() == collection.expected_count as usize {
                resolve_input_collection(collection);
            }
        }
    }
}

fn on_tick_check_deadline(collection: &mut GroupInputCollection) {
    if !collection.resolved && current_tick() > collection.deadline_tick {
        // Fill in defaults for missing selections
        for member in get_group_members(collection.group_id) {
            if !collection.selections.contains_key(&member) {
                collection.selections.insert(member, collection.default_option);
            }
        }
        resolve_input_collection(collection);
    }
}
```

### Combination Evaluation

The outcome is determined by a LOOKUP based on the combination of all selections:

```
struct CombinationMatrix {
    // Unordered evaluation (just counts)
    generic_results: HashMap<SelectionCounts, GroupEffect>,
    // Ordered evaluation (specific patterns by player position)
    special_patterns: HashMap<Vec<InputOption>, GroupEffect>,
}

struct SelectionCounts {
    red: u8,
    blue: u8,
    green: u8,
    yellow: u8,
}
```

Evaluation priority:
1. Check ordered patterns first (specific sequences = special effects)
2. If no ordered match: evaluate by count distribution (3R+1G = damage-heavy combo)
3. Apply the resulting group effect

### Ordered vs Unordered Patterns

Two layers of pattern matching:
- **Unordered (by count)**: "3 Red + 1 Green" = damage combo regardless of which player chose which. Simpler, more common.
- **Ordered (by player position)**: "Player 1=Red, Player 2=Blue, Player 3=Green, Player 4=Yellow" in THAT specific order = special named combo. Harder to coordinate, more powerful reward.

Player position/order must be deterministic — sorted by entity_id, group join order, or party slot index.

### Combat During Selection

While the selection window is open:
- Combat CONTINUES (unlike turn-based games, this is real-time)
- Players must fight AND make their selection
- The selection UI is an overlay — players can still move, attack, and use abilities
- The selection is a META-INPUT alongside normal combat input

This means the Edge Node must support: normal gameplay input (movement, abilities) + selection input (choose a color) simultaneously.

### Group Effect Application

The resolved combination produces a GROUP EFFECT applied to all members:
- AoE damage to enemies near the group
- Group heal (all members healed)
- Group buff (applied to all members)
- Power restore (mana/resource restored to all members)
- Or: a combination of the above, scaled by the selection distribution

The effect is broadcast to all group members' Arbiters for application.

## Cross-Boundary Concerns

TODO: Group members might be on different Arbiters:

1. **Selection relay**: Each player sends their selection to their local Arbiter. If the collection state is on Arbiter A, selections from players on Arbiter B must relay to A.

2. **Timeout synchronization**: The deadline tick must be consistent across Arbiters. Since all Arbiters use the same Shard Tick (Metronome synchronized), the deadline is deterministic.

3. **Effect application**: The resolved group effect must be relayed to all members' Arbiters. If the effect is a group heal, each member's Arbiter applies the heal locally.

4. **Missing players**: If a group member disconnected or is on a crashed Arbiter, their selection defaults. The collection continues with available players.

## Compiler Requirements

TODO: Designer specifies: trigger condition, selection options (Red/Blue/Green/Yellow), time window (10s), combination matrix (count-based generic results + ordered special patterns), default for non-selectors, group effect per combination. Compiler produces:
- GroupInputCollection state definition
- Selection options enum
- CombinationMatrix lookup table in SpellData
- Per-player selection input handling
- Deadline management + default filling
- Combination evaluation (ordered patterns first, then count-based)
- Group effect application to all members

The compiler needs to support **multi-player input collection and combination evaluation** — a new input paradigm where N players contribute to a single combined outcome.

### docs-core/ Impact

This likely requires `docs-core/` consideration:
- The messaging plane must support "meta-input" (selection choices) alongside normal gameplay input
- The Edge Node must handle overlay UI input that doesn't conflict with normal ability input
- Group state management (which Arbiter owns the collection state)

## Open Questions

- Can players change their selection before the deadline (switch from Red to Green)?
- Can players see what others have selected in real-time (coordination vs blind choice)?
- Does combat pause during the selection window, or does it continue in real-time?
- Can enemies interrupt the fellowship maneuver (CC the trigger player)?
- Can the selection window be extended by abilities or items?
- What happens if only 2 of 6 players select (the rest default)?
- Are the special ordered patterns predefined in SpellData or dynamically generated?
- Does the trigger frequency have a cooldown (prevent spamming fellowship maneuvers)?
- Can the outcome be amplified by buffs (SK-83 empowerment on the group effect)?
- Does Kinematic Dilation affect the selection window timer?
- How does the selection UI interact with SK-40 Mind Control (controlled player can't select?) or SK-24 Stun (stunned player can't select?)?
- Performance: collecting N inputs across potentially N Arbiters, evaluating combination — bounded by group size
