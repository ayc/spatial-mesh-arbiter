# SK-124: Group Sequential Combo

## Designer Intent

During combat, a combo opportunity triggers. A combo wheel appears showing a SEQUENCE of ability types that the group must perform in ORDER: first a Fighter ability, then a Scout ability, then a Mage ability, then a Priest ability. Each player contributes their step when it's their role's turn. If the group completes the full sequence within the time limit, a powerful bonus effect triggers for the entire group.

## Primitive Composition

P-54 (Group Choice Aggregator) → P-42 (Stacking Counters w/ Decay)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Trigger event (specific ability, critical hit, or boss mechanic starts the combo)
- Multiple player entities contributing abilities in sequence
- Each step requires a specific ABILITY TYPE from a specific ROLE

## Observable Behavior

1. Combo opportunity triggers — all group members see the combo wheel
2. Step 1: a Fighter must use a melee ability within 5 seconds
3. If completed: Step 2 begins — a Scout must use a ranged ability within 5 seconds
4. If completed: Step 3 begins — a Mage must use a spell ability within 5 seconds
5. If completed: Step 4 begins — a Priest must use a heal ability within 5 seconds
6. If all 4 steps completed in time: HEROIC OPPORTUNITY triggers — powerful group effect (e.g., massive AoE damage + group heal + damage buff for 10 seconds)
7. If any step times out: combo FAILS — partial reward based on steps completed, or no reward
8. Different sequences produce different rewards (offensive combo, defensive combo, balanced combo)
9. Visual: shared combo wheel UI, each step highlights the active role, completion flash

## Engine Primitives Required

### Shared Group State Machine

The combo is a STATE MACHINE shared across the entire group:

```
struct GroupComboState {
    combo_id: UUID,
    group_id: UUID,              // Which group/party this belongs to
    sequence: Vec<ComboStep>,    // Required steps in order
    current_step_index: u8,
    current_step_deadline_tick: u64,
    completed_steps: Vec<CompletedStep>,
    status: ComboStatus,
}

struct ComboStep {
    required_role: PlayerRole,        // Fighter, Scout, Mage, Priest
    required_ability_type: AbilityType, // Melee, Ranged, Spell, Heal
    time_limit_ticks: u64,
}

struct CompletedStep {
    entity_id: EntityID,
    ability_used: AbilityId,
    completed_at_tick: u64,
}

enum ComboStatus {
    Active,
    Completed,
    Failed,
    TimedOut,
}
```

### Group-Wide Event Detection

The engine must detect: "a player in this group used an ability of the required type during the current step's window."

Each time a group member uses an ability:
1. Check: is there an active GroupComboState for this entity's group?
2. Check: is this entity's role the required role for the current step?
3. Check: is this ability the required ability type for the current step?
4. Check: is the current tick within the step's deadline?
5. If all yes: ADVANCE the combo to the next step
6. If the last step is completed: TRIGGER the combo reward

```
fn on_ability_used(entity: &Entity, ability: &AbilityDef) {
    if let Some(combo) = get_active_group_combo(entity.group_id) {
        let current_step = &combo.sequence[combo.current_step_index as usize];
        if entity.role == current_step.required_role
            && ability.ability_type == current_step.required_ability_type
            && current_tick() <= combo.current_step_deadline_tick
        {
            advance_combo(combo, entity.entity_id, ability.ability_id);
        }
    }
}
```

### Group State Ownership

Where does the GroupComboState live? Options:
- **On one entity** (the group leader): simple, but requires cross-boundary checks if group members are on different Arbiters
- **On the Arbiter** (shared state alongside entity data): scales with the group being co-located
- **On the Controller** (centralized): handles cross-boundary groups but adds Controller dependency

Since group members in combat are typically on the same Arbiter (fighting the same enemies), the combo state can live on the local Arbiter. If group members are split across Arbiters, the combo state must be synchronized or centralized.

### Ability Type and Role Classification

The compiler must classify:
- Each ability with an `ability_type: AbilityType` (Melee, Ranged, Spell, Heal, etc.)
- Each entity with a `role: PlayerRole` (Fighter, Scout, Mage, Priest, etc.)

The combo sequence references these classifications. The lookup is: "did a Fighter use a Melee ability this step?"

### Combo Reward

On successful completion, the reward is applied to ALL group members:
- AoE buff centered on the combo trigger location (or on each group member)
- Damage burst to enemies near the group
- Group-wide heal
- Buff with duration

The reward is a predefined effect in SpellData, referenced by the combo sequence definition.

## Cross-Boundary Concerns

TODO: Group members might be on different Arbiters:

1. **All on same Arbiter**: Combo state is local. Ability detection is local. Simple.
2. **Split across Arbiters**: When a group member on Arbiter B uses an ability, their Arbiter must check: is there an active combo for this group? If the combo state is on Arbiter A, Arbiter B must relay "player X used ability type Y for the combo."

The simplest approach: combo state lives on the Arbiter where the combo was triggered. Ability contributions from other Arbiters are relayed. The combo-owning Arbiter manages the state machine and applies rewards when complete.

If the reward is a group-wide buff: relay buff application to all group members' Arbiters.

## Compiler Requirements

TODO: Designer specifies: combo trigger condition, sequence of steps (role + ability type per step), time limit per step, combo reward on completion, partial reward on failure, combo sequence variants (different sequences = different rewards). Compiler produces:
- GroupComboState definition
- Combo sequence definitions in SpellData (role × ability type per step)
- Ability type classification on all abilities
- Entity role classification
- On-ability-used hook: check combo advancement
- Reward definitions (group-wide buff/damage/heal)
- Timeout logic per step

The compiler needs to support **group-level state machines** — shared state across multiple entities that advances based on contributions from different group members.

## Open Questions

- Can the same player contribute to multiple steps (Mage fills both step 3 and step 4 if they have a heal)?
- Can two players of the same role compete for the same step (two Fighters both try to fill step 1)?
- Does the combo state persist if the triggering entity dies?
- Can enemies interfere with the combo (CC the player whose turn it is)?
- Can multiple combos be active simultaneously for the same group?
- Does the combo pause during SK-91 Stasis?
- How are combo sequences defined — fixed patterns or randomized per trigger?
- Can the group choose which combo sequence to attempt (offensive vs defensive)?
- Does the combo reward scale with the speed of completion (faster = better)?
- Performance: on-ability-used hook checked for every ability by every group member — bounded by group size × cast rate
