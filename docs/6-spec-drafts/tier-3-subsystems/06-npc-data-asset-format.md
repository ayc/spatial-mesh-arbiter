# T3-06: NPC Data Asset Format

> **Status:** REVIEW
> **Checklist Ref:** [GAPS_CHECKLIST.md](../GAPS_CHECKLIST.md)
> **Canonical Target:** `1-architecture/02-npc-architecture.md`

## Audit Notes

Tier assignment, archetype binding, named NPC UUIDs, orphan TTL, and stats compilation are all specified. Missing: the actual file format, spawn rule definitions, and the compilation pipeline from raw assets to `compiled_state`.

## Resolution

### 1. NPC Definition Schema

NPC definitions live in the game image (`04-game-image-format.md`) as part of EntityDefinitions (section 0x11). The source format is YAML, compiled by the Game Compiler alongside ability definitions.

```yaml
npc:
  npc_type_id: "forest_wolf"
  display_name: "Dire Wolf"
  archetype: "NeutralMonster"
  runtime_tier: 1                    # T0 = full AI, T1 = Arbiter-local FSM

  stats:
    max_hp: 450
    movement_speed: 0.35
    base_stats:
      vigor: 15
      fortitude: 10
      agility: 20
    offensive:
      physical_damage: 45
      attack_speed: 1.2
    defensive:
      resistances: { physical: 10, fire: -10 }

  abilities:
    - "wolf_bite"           # References AbilityDefinition IDs
    - "wolf_howl"

  threat:
    swap_threshold_pct: 0.10
    leash_range: 30.0
    leash_return_speed_multiplier: 2.0
    aggro_range: 15.0        # Detection range for entering combat

  loot:
    loot_table_id: "forest_wolf_drops"

  lifecycle:
    orphan_ttl_ticks: 600    # 10 seconds without AI Node before passive mode
    despawn_on_owner_death: false
    corpse_duration_ticks: 1800  # 30 seconds corpse persistence
```

### 2. Spawn Rule Definition

Spawn rules define where and when NPCs appear. They are separate from NPC definitions (composition: one NPC type can have many spawn rules).

```yaml
spawn_rule:
  rule_id: "forest_wolves_zone_a"
  npc_type_id: "forest_wolf"

  location:
    zone_id: "enchanted_forest"
    spawn_points:
      - { position: [150.0, 200.0], radius: 5.0 }
      - { position: [170.0, 210.0], radius: 5.0 }
      - { position: [160.0, 190.0], radius: 5.0 }

  population:
    min_alive: 2               # Minimum wolves alive in this group
    max_alive: 3               # Maximum wolves alive
    respawn_delay_ticks: 600   # 10 seconds after death before respawn
    stagger_ticks: 60          # 1 second between individual respawns in a wave

  conditions:
    time_of_day: "night"       # Optional: only spawn at night (game-defined)
    quest_flag: null            # Optional: only spawn if quest active

  patrol:
    mode: "waypoint_loop"      # none | waypoint_loop | waypoint_bounce | random_wander
    waypoints:
      - [150.0, 200.0]
      - [165.0, 215.0]
      - [180.0, 200.0]
    pause_at_waypoint_ticks: 180  # 3 seconds pause at each waypoint
    patrol_speed_multiplier: 0.7  # Slower than combat speed
```

### 3. Compilation Pipeline

```
NPC YAML → Game Compiler → EntityDefinitions (game image §4)
Spawn YAML → Game Compiler → Static Data Tables (game image §7)
```

The compiler:
1. Validates NPC type IDs are unique
2. Validates referenced abilities exist in AbilityDefinitions
3. Validates referenced loot tables exist
4. Compiles NPC stats using the same `attribute-formulas.json` pipeline as player stats (T1-01)
5. Serializes NPC definitions into `EntityDefinition_Wire` entries
6. Serializes spawn rules into a spawn table in Static Data Tables

At runtime, the Meta Service reads spawn rules from the game image and issues spawn commands to the appropriate Arbiter. The Arbiter calls `initialize_spawn_configuration` to build the NPC's initial state from the compiled EntityDefinition.

### 4. Patrol Path Format

Patrol paths are stored as ordered point lists in the spawn rule. The Arbiter-local FSM (Tier 1 NPCs) or AI Node (Tier 0 NPCs) reads the path and drives movement.

```rust
enum PatrolMode {
    None,               // NPC stays at spawn point
    WaypointLoop,       // A → B → C → A → B → ...
    WaypointBounce,     // A → B → C → B → A → ...
    RandomWander,       // Random position within radius of spawn point
}
```

Waypoints use absolute world coordinates (`Vec2F`). The NPC moves between waypoints at `move_speed × patrol_speed_multiplier`. At each waypoint, the NPC pauses for `pause_at_waypoint_ticks`.

## References

- `docs/1-architecture/02-npc-architecture.md` — Classification mandate, tier defaults
- `docs/3-gameplay-systems/04-npc-and-world-interaction.md` — Archetype taxonomy
- `docs-game-compiler/04-game-image-format.md` — EntityDefinitions and Static Data Tables sections
- `docs-game-compiler/02-schema-and-validation.md` §7 — EntityDefinition schema
