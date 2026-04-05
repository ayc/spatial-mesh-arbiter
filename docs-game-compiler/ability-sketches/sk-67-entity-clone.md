# SK-67: Entity Clone

## Designer Intent

I create a temporary clone of an allied hero. The clone spawns near me, I control it for 20
seconds, it uses a reduced snapshot of the ally's loadout, and when the clone expires or dies my
original body returns at the clone's final position. The original ally continues playing
independently the whole time.

## Primitive Composition

P-32 (Actor Spawning) → P-31 (Identity/Loadout Swap) → P-29 (Control Authority Swap)

*See `ability-primitives/` for canonical definitions.*

## Inputs

- Caster entity
- Target ally entity in range
- Clone lifetime
- Loadout/stat scaling multipliers
- Ability exclusions for the projected loadout
- Restore position / HP policy for the caster's stored body

## Observable Behavior

1. Cast on an ally and spawn a clone shell at the caster's position
2. The original ally is unaffected and keeps acting normally
3. The caster's original body is suspended while control transfers to the clone
4. The clone uses the target ally's current public loadout snapshot, but with reduced stats and HP
5. The clone omits the authored excluded abilities, such as the ultimate
6. The player controls the clone directly for up to 20 seconds
7. If the clone expires or is destroyed, the caster's stored body is restored at the clone's
   current or last position
8. Visual: a ghostly or translucent copy of the ally hero

## Engine Primitives Required

Entity Clone is now the canonical spawned-shell projection pattern built from `loadout_projection`
plus `control_projection`. It does not require a bespoke runtime "copy hero" subsystem.

### Canonical Clone Shape

The recommended lowering is one `spawn_actor` using a shell archetype plus two ability-local spawn
overlays:

- `loadout_projection = {`
  `source = { entity_current_loadout: target },`
  `max_hp_multiplier = 0.75,`
  `stat_multiplier = 0.75,`
  `excluded_abilities = [ally_ultimate]`
  `}`
- `control_projection = {`
  `controller = caster,`
  `owner_body_policy = suspend_owner,`
  `control_scope = full,`
  `on_actor_removed = restore_owner,`
  `on_expire = restore_owner,`
  `restore_position = projected_actor_position,`
  `restore_hp_policy = preserve_stored_owner`
  `}`

The clone is therefore:

1. one ordinary spawned actor
2. initialized once from the target ally's EFFECTIVE current loadout/passive/appearance snapshot
3. controlled by the caster through the existing Stage 1 routing contract
4. restored back to the caster's stored body through the explicit `restore_owner` policy

### Snapshot Semantics

`loadout_projection` snapshots the ally once at spawn commit. The projection does NOT live-update
after the clone appears. If the original ally later changes gear, form, buffs, or temporary state,
the already-spawned clone keeps the snapshot it was created with.

### Reduced-Stat Clone Policy

For this sketch:

- max HP is scaled by `0.75`
- effective combat stats are scaled by `0.75`
- the clone uses its own scaled snapshot, not the source ally's later live stats
- ultimate/heroic abilities are excluded through `excluded_abilities`

## Cross-Boundary Concerns

Entity Clone follows the canonical source-snapshot and control-projection contracts.

1. If the cloned ally is remote, the ally's owner captures the immutable projected loadout snapshot
   at spawn commit and relays it to the caster's Arbiter before the clone spawns
2. The clone always spawns where the caster is, so the live clone actor begins under the caster's
   current owner even if the copied ally is elsewhere
3. Control transfer is a normal single-actor `control_projection` overlay; if the clone later hands
   off, steering/control hand off with it through the existing `P-29` routing rules
4. If the clone expires or is destroyed on another Arbiter, `restore_owner` uses the clone's
   current or last authoritative position there and restores the caster body at that location

## Compiler Requirements

Designer specifies:

- ally target filter and cast range
- clone duration
- shell archetype / clone presentation
- projected loadout source
- HP/stat multipliers
- excluded abilities
- owner-body suspend / restore policy

Compiler emits:

- one spawned shell actor
- one `loadout_projection` snapshot from `{ entity_current_loadout: target }`
- one `control_projection` from caster to the shell
- ordinary restore-owner behavior on expiry or actor removal

Compiler validates:

1. `count = 1` because both `loadout_projection` and `control_projection` are authored
2. `max_hp_multiplier > 0`
3. `stat_multiplier > 0`
4. every `excluded_abilities` entry names a valid public ability from the projected source space
5. `owner_body_policy = suspend_owner` is used whenever expiry/removal should restore the caster

## Resolved Notes

- The original ally is copied, not replaced. Their body, loadout, and control routing are not
  modified by the clone cast
- The clone does not inherit the ally's live buffs/debuffs or other runtime status state unless a
  separate canonical surface is authored for that on top of the projected shell
- Cooldowns, charges, and other runtime combat state are not live-linked back to the source ally;
  the clone uses the state of the spawned projected shell
- Kill credit, proc attribution, and ownership follow the clone actor's ownership, which in this
  sketch remains with the caster-side spawned shell
