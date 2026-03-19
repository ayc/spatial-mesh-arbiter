# SK-120: Combo Field Matrix

## Designer Intent

When I place a fire zone on the ground and my teammate fires a projectile through it, the projectile becomes a BURNING projectile — dealing bonus fire damage on hit. If instead my teammate leaps through the fire zone, they gain a fire shield. The effect depends on the COMBINATION of zone type and ability type. Every zone and every movement/projectile ability can combo, creating emergent synergies between players.

## Primitive Composition

P-14 (Continuous Proximity Monitor) → P-64 (Combo Field × Finisher Matrix)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Player A places a COMBO FIELD (zone with an element type)
- Player B uses a COMBO FINISHER (ability classified as projectile, blast, whirl, or leap) that passes through or lands in the field
- The combination determines the resulting effect

## Observable Behavior

1. Player A places a Fire Field (e.g., SK-29 Blizzard but fire element)
2. Player B fires a projectile through the Fire Field
3. The projectile gains the combo effect: Burning (applies burn DoT on hit)
4. OR: Player B uses a Blast finisher inside the Fire Field → AoE Might buff to nearby allies
5. OR: Player C leaps through the Fire Field → gains Fire Shield (damage on nearby enemies)
6. Different field types produce different effects with the same finisher:
   - Water Field + Blast = AoE Heal
   - Smoke Field + Blast = AoE Stealth
   - Lightning Field + Blast = AoE Swiftness
7. Each combo produces a visual "Combo!" indicator
8. Any player's field + any player's finisher = valid combo (cross-player by default)

## Engine Primitives Required

### Combo Field Type Tag

Every zone ability (SK-29 Blizzard, SK-08 Aura, SK-16 Holy Ground, SK-30 Trail of Fire, etc.) can optionally be tagged with a COMBO FIELD TYPE:

```
enum ComboFieldType {
    Fire,
    Water,
    Lightning,
    Poison,
    Smoke,
    Ice,
    Light,
    Dark,
    Ethereal,
}
```

The zone entity carries `combo_field_type: Option<ComboFieldType>`. Not all zones are combo fields — only those tagged by the compiler.

### Combo Finisher Type Tag

Every ability that involves movement or projectiles can be tagged with a COMBO FINISHER TYPE:

```
enum ComboFinisherType {
    Projectile,  // Projectile passes through the field
    Blast,       // AoE ability lands inside the field
    Whirl,       // Spinning/channeled ability inside the field
    Leap,        // Movement ability that passes through the field
}
```

Abilities carry `combo_finisher_type: Option<ComboFinisherType>`. Not all abilities are finishers — only those tagged.

### Combo Resolution Matrix

The engine needs a LOOKUP TABLE mapping (field_type, finisher_type) → combo_effect:

```
struct ComboMatrix {
    entries: HashMap<(ComboFieldType, ComboFinisherType), ComboEffect>,
}

enum ComboEffect {
    ApplyConditionToTarget(ConditionDef),    // Projectile finisher: enchant the projectile
    AoEBuffToAllies(BuffDef, SimFixed),       // Blast finisher: AoE buff around the finisher
    AoEDamageToEnemies(DamageDef, SimFixed), // Blast finisher: AoE damage
    ApplyBuffToSelf(BuffDef),                 // Leap finisher: buff the leaper
    SpawnProjectiles(ProjectileDef, u8),      // Whirl finisher: spawn projectiles outward
}
```

Example entries:
- (Fire, Projectile) → ApplyConditionToTarget(Burning)
- (Fire, Blast) → AoEBuffToAllies(Might, 3 stacks)
- (Fire, Leap) → ApplyBuffToSelf(FireShield)
- (Water, Blast) → AoEHealToAllies(heal_amount)
- (Smoke, Blast) → AoEBuffToAllies(Stealth, 3s)
- (Lightning, Whirl) → SpawnProjectiles(LightningBolt, 6)

### Combo Detection

The engine must detect when a finisher interacts with a field:

**Projectile finisher**: each tick during projectile movement, check: is the projectile inside any combo field? If yes AND the projectile hasn't already comboed with this field → trigger combo.

**Blast finisher**: when an AoE ability resolves, check: is the AoE center inside any combo field? If yes → trigger combo.

**Leap finisher**: when a movement ability completes, check: did the movement path pass through any combo field? If yes → trigger combo.

**Whirl finisher**: each tick during a channeled spinning ability, check: is the caster inside any combo field? If yes → trigger combo (once per field per whirl, not per tick).

```
fn check_combo(position: Vec2F, finisher_type: ComboFinisherType, caster: &Entity) -> Option<ComboEffect> {
    for field in active_combo_fields_at(position) {
        if let Some(effect) = combo_matrix.lookup(field.combo_field_type, finisher_type) {
            return Some(effect);
        }
    }
    None
}
```

### Cross-Player Combos

The combo system is DESIGNED for cross-player interaction:
- Player A places a Fire Field
- Player B uses a Blast finisher in it
- The combo effect benefits Player B's team (AoE Might to allies near the blast)

The field creator and finisher user can be DIFFERENT PLAYERS on the same team. The engine doesn't care who placed the field — it just checks "is there a combo field here?"

This is emergent: players don't explicitly "combo" — they independently place fields and use finishers, and the engine detects the intersection.

### One Combo Per Finisher Per Field

To prevent spam:
- A finisher can only combo with each field ONCE (tracking set: `comboed_fields: HashSet<EntityID>`)
- Multiple finishers CAN combo with the same field (different players using different finishers in the same field)
- A projectile that passes through TWO different fields combos with the FIRST one only

## Cross-Boundary Concerns

TODO: A combo field is a zone on one Arbiter. A finisher from a player on a neighboring Arbiter could:

1. **Projectile crosses boundary into a field**: The projectile is handed off to the field's Arbiter. On the new Arbiter, the projectile is inside the field → combo triggers locally. Standard projectile handoff handles this.

2. **Blast finisher near boundary, field on the other side**: The blast's AoE center is on Arbiter A, the field is on Arbiter B. Does the combo trigger? Only if the blast position overlaps with the field's position — which requires the blast's Arbiter to know about combo fields on neighboring Arbiters (Ghost data for zones). If zones don't have Ghost representations, cross-boundary blast combos won't work.

3. **Leap across boundary through a field**: The leap path crosses from Arbiter A through a field on Arbiter B to Arbiter C. The leaper is handed off through B, where the combo check can occur.

Simplest approach: combos only trigger when the finisher and field are on the SAME Arbiter. Cross-boundary combos are not detected. Given that fields have limited radius and finishers are used near fields, this is usually the same Arbiter.

## Compiler Requirements

TODO: Designer specifies: combo field types (enum), combo finisher types (enum), combo matrix (field × finisher → effect), per-zone ability field type tag, per-ability finisher type tag, cross-player combo detection, one-combo-per-finisher-per-field limit. Compiler produces:
- ComboFieldType tag on zone ability definitions
- ComboFinisherType tag on ability definitions
- ComboMatrix lookup table in SpellData (game-defined, not engine-defined)
- Per-tick combo detection hooks (projectile in field, blast in field, leap through field, whirl in field)
- Combo effect resolution (apply the matrix result)
- Dedup tracking (comboed_fields set per finisher)

The combo matrix is GAME DATA — different games define different field types, finisher types, and combo effects. The ENGINE provides the detection mechanism. The COMPILER validates the matrix and tags abilities. This is a clean engine/game separation.

## Open Questions

- Can enemy abilities combo with your fields (hostile combo)?
- Can a field combo with its OWN creator's finisher (self-combo)?
- If two fields overlap and a finisher lands in the overlap, which field takes priority?
- Can combo effects trigger procs (e.g., burning projectile from fire combo triggers on-hit burn which triggers SK-09 Chain Lightning)?
- Does the combo matrix live in SpellData (hot-patchable) or is it compiled into the engine?
- Can new field types and finisher types be added via the game compiler without engine changes?
- Does Kinematic Dilation affect combo detection timing?
- Can the combo system be used in PvP (enemy places field, ally uses finisher = enemy field benefits your team)?
- How many simultaneous combo fields can exist on one Arbiter before detection becomes expensive?
- Should combo detection be a per-tick check or event-driven (only check when a finisher activates)?
